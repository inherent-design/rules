"""Replay frozen discovery evidence through formal policies; never run empack."""
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

from discovery_observations import packets

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUN = ROOT / 'applications/evidence/empack-discovery-cli-20261125T163044602818Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())


def write(p, value):
    p.write_text(json.dumps(value, indent=2) + '\n')


def compare(actual, expected):
    assert actual == expected, 'Discovery policy differs from retained native outcome'


def main():
    setup = load(RUN / 'setup.json')
    assert sha(RUN / 'probe.py') == setup['producerSha256']
    assert sha(RUN / 'fixture.py') == setup['fixtureProducerSha256']
    assert sha(RUN / 'vectors.json') == setup['vectorsSha256']
    correction = load(RUN / 'continuation.json')
    assert sha(RUN / 'continuation-probe.py') == correction['producerSha256']
    assert load(RUN / 'incomplete.json')['commandsCompleted'] == 4
    assert not (RUN / 'continuation-incomplete.json').exists()
    source_checks = []
    repo = ROOT.parent / 'empack'
    for row in setup['sources']:
        raw = subprocess.check_output(['git', '-C', str(repo), 'show', row['revision'] + ':' + row['path']])
        assert hashlib.sha256(raw).hexdigest() == row['sha256']
        source_checks.append(row['path'])
    binary = Path(setup['binary'])
    binary_checked = False
    if binary.exists():
        assert sha(binary) == setup['binarySha256']
        binary_checked = True
    commands = load(RUN / 'commands.json')
    assert len(commands) == 18 and len({r['label'] for r in commands}) == 18
    for row in commands:
        assert row['processGroupAbsent'] and not row['timedOut']
        for stream in ['stdout', 'stderr']:
            assert sha(RUN / (row['label'] + '.' + stream)) == row['streams'][stream]
        for phase in ['before', 'after']:
            image = RUN / row[phase]['file']
            assert sha(image) == row[phase]['sha256']
            decoded = gzip.decompress(image.read_bytes())
            assert hashlib.sha256(decoded).hexdigest() == row[phase]['decodedSha256']
        before = json.loads(gzip.decompress((RUN / row['before']['file']).read_bytes()))
        after = json.loads(gzip.decompress((RUN / row['after']['file']).read_bytes()))
        assert set(row['changedScopes']) == {s for s in before if before[s] != after[s]}
    closure = load(RUN / 'closure.json')
    assert not closure['workPathProcessMatches'] and all(r['absent'] for r in closure['groups'])
    products_checked = []
    for row in load(RUN / 'results.json')['cases']:
        product = row['product']
        if product:
            root = 'ambiguous' if row['id'] == 'explicit-b' else 'entries' if row['id'] == 'entries-explicit' else row['id']
            path = Path(setup['work']) / root / product['path']
            if path.exists():
                assert sha(path) == product['sha256']
                with zipfile.ZipFile(path) as z:
                    assert z.namelist() == product['members']
                    b = z.read('overrides/resourcepacks/first.zip')
                    assert b.hex() == product['payloadHex'] and hashlib.sha256(b).hexdigest() == product['payloadSha256']
                products_checked.append(row['id'])
    inputs, expected = packets(RUN)
    write(RUN / 'model-input.json', inputs)
    write(RUN / 'observed-model-values.json', expected)
    proof = load(RUN / 'proof-gate.json')
    assert proof['observedExitCode'] == 0
    for p, h in proof['sourceSha256'].items():
        assert sha(ROOT / p) == h
    formal = ROOT / '.build/empack-discovery-formal'
    formal.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'LEAN_PATH': str(formal), 'BEND_NO_TELEMETRY': '1'}
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    command = [lean, '--run', 'applications/empack/DiscoveryCase.lean']
    result = subprocess.run(command + [str(RUN / 'model-input.json')], cwd=ROOT, env=env,
                            capture_output=True, text=True, check=True)
    actual = json.loads(result.stdout)
    compare(actual, expected)
    calls, wanted = [], []
    bo = lambda value: 'True{}' if value else 'False{}'
    li = lambda values: '[' + ','.join(str(v) + 'n' for v in values) + ']'
    for row, native in zip(inputs['cases'], expected, strict=True):
        explicit = 'None{}' if row['explicit'] is None else 'Some{' + str(row['explicit']) + 'n}'
        decision = 'P.decision(' + ','.join([str(row['entries']) + 'n', str(row['limit']) + 'n',
            li(row['matching']), bo(row['explicit'] is not None), bo(row['explicitMatches'])]) + ')'
        expressions = ['Nat.show(' + decision + ')',
            'P.show_selected(P.selected(' + decision + ',' + li(row['matching']) + ',' + explicit + '))',
            'Bool.show(P.published(' + decision + '))',
            'Nat.show(Bool.pick(Nat,P.published(' + decision + '),0n,1n))']
        calls.extend(expressions)
        wanted.extend([str(native['kind']), 'none' if native['selected'] is None else str(native['selected']),
                       str(native['published']), str(native['exitCode'])])
    target = formal / 'Replay.bend'
    target.write_text('import ../../applications/empack/Discovery.bend as P\nimport Base\ndef main() -> IO(Unit):\n  IO.write(' +
                      ' ++ "\\n" ++ '.join(calls) + ' ++ "\\n")\n')
    result = subprocess.run([bend, str(target)], cwd=ROOT, env=env, capture_output=True, text=True, check=True)
    compare(result.stdout.splitlines(), wanted)
    controls = []
    for label, name, field, value in [('ambiguity-as-success', 'ambiguous', 'published', True),
            ('explicit-wrong-bytes', 'explicit-b', 'selected', 0),
            ('limit-returns-subset', 'entries', 'kind', 3),
            ('strong-loses-selection', 'strong', 'selected', 1)]:
        changed = copy.deepcopy(expected)
        next(r for r in changed if r['id'] == name)[field] = value
        try:
            compare(actual, changed)
        except AssertionError as error:
            assert 'differs from retained' in str(error)
            controls.append(label)
        else:
            raise AssertionError('Changed observation escaped')
    for label, change, cause in [('schema', lambda d: d.update(schema=2), 'research schema'),
            ('limit', lambda d: d['cases'][0].update(limit=5), 'research profile'),
            ('content', lambda d: d['cases'][0].update(matching=[2]), 'research profile'),
            ('entries', lambda d: d['cases'][0].update(entries=10002), 'research profile')]:
        changed = copy.deepcopy(inputs)
        change(changed)
        path = formal / (label + '.json')
        write(path, changed)
        result = subprocess.run(command + [str(path)], cwd=ROOT, env=env, capture_output=True, text=True)
        assert result.returncode == 2 and cause in result.stderr
        controls.append(label)
    files = [p for p in RUN.iterdir() if p.is_file() and p.name not in ['basis.json', 'conformance.json']]
    files += [HERE / name for name in ['Discovery.lean', 'DiscoveryCase.lean', 'Discovery.bend',
                                      'discovery_cli_probe.py', 'discovery_observations.py', 'discovery_conformance.py']]
    files.append(ROOT / 'applications/sources/md5-collision-inputs.json')
    write(RUN / 'basis.json', {str(p.relative_to(ROOT)): sha(p) for p in files})
    report = dict(schema=1, nativeCommands=18, decisionCases=6, bendScalarComparisons=len(calls),
        leanLaws=15, bendLaws=7, negativeControls=controls, sourcePinsChecked=source_checks,
        installedBinaryIdentityChecked=binary_checked, privateProductsChecked=products_checked,
        basisFiles=len(files), scope='Closed installed-CLI build continuation controls, not general scanner or host qualification.',
        limits=['No source/binary equivalence claim; installed0.8.8 and current0b source are separate evidence.',
                'Matching-address packet is interpreted from known test bytes and captured author assertions; no crypto proof.',
                'Only entry-count limit is exercised; byte/deadline/root/requirement bounds, races and other continuation kinds remain open.',
                'One original producer assertion failed after command4; separate correction continued without repeating native commands.'])
    write(RUN / 'conformance.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
