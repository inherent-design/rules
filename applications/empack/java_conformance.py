#!/usr/bin/env python3
"""Compare retained actual-core policy calls and private JVM observations.

No compiler, JVM, empack executable, package, or game is launched by this replay.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    receipt = json.loads((run / 'receipt.json').read_text())
    commands = json.loads((run / 'commands.json').read_text())
    assert receipt['commands'] == len(commands) == 4 and receipt['allOwnedProcessesRetired']
    assert sha(run / 'probe.py') == sha(HERE / 'java_probe.py') == receipt['producerSha256']
    assert sha(run / 'driver.rs') == sha(HERE / 'java_oracle.rs') == receipt['driverSha256']
    assert sha(run / 'profiles.csv') == receipt['profilesSha256']
    assert sha(run / 'observed-core.stdout') == receipt['observedSha256']
    prior = ROOT / receipt['priorCoreCapture']
    assert sha(prior / 'receipt.json') == receipt['priorCoreReceiptSha256']
    assert sha(prior / 'work/libempack_core.rlib') == receipt['librarySha256']
    files = [run / name for name in ['receipt.json', 'commands.json', 'probe.py', 'driver.rs', 'profiles.csv']]
    files += [HERE / name for name in ['Java.lean', 'Java.bend', 'JavaCase.lean', 'java_probe.py', 'java_oracle.rs', 'java_conformance.py']]
    files += [prior / 'receipt.json']
    ledger = ROOT / 'applications/sources/empack-java-selections.json'; files.append(ledger)
    repo = ROOT.parent / 'empack'; revision = receipt['revision']
    pins = dict(receipt['sourceSha256'])
    for record in json.loads(ledger.read_text())['sources']:
        if record['path'] in pins:
            assert pins[record['path']] == record['sha256']
        pins[record['path']] = record['sha256']
    for name, digest in pins.items():
        data = subprocess.check_output(['git', '-C', str(repo), 'show', revision + ':' + name])
        assert hashlib.sha256(data).hexdigest() == digest, name
    for command in commands:
        assert command['exitCode'] == 0 and not command['timedOut']
        for stream in command['streams'].values():
            path = run / stream['path']; files.append(path)
            assert sha(path) == stream['sha256'] and path.stat().st_size == stream['bytes']
    profiles = []
    for line in (run / 'profiles.csv').read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        game, historical, values, metadata_digest = line.split('|')
        assert len(metadata_digest) == 64
        profiles.append(dict(game=game, historical=int(historical), supported=list(map(int, values.split(',')))))
    assert len(profiles) == len({p['game'] for p in profiles}) == 112
    option = lambda value: None if value == '-' else int(value)
    cases, expected, names, calls, bend_expected = [], [], [], [], []
    bit = lambda b: 'True{}' if b else 'False{}'
    for line in (run / 'observed-core.stdout').read_text().splitlines():
        name, game, bounds, preferred, observed, historical, minimum, supported, recommendation, stage, selected, diagnostic = line.split('\t')
        bounds = [dict(minimum=int(b.split(':')[0]), maximum=option(b.split(':')[1])) for b in bounds.split(',') if b]
        preferred, observed = option(preferred), option(observed)
        row = dict(game=game, bounds=bounds, preferred=preferred, actual=observed)
        result = dict(historical=option(historical), minimum=int(minimum), supported=None if supported == '-' else list(map(int, supported.split(','))),
                      recommended=option(recommendation), stage=stage, selected=option(selected))
        assert (stage == 'ok') == (not diagnostic) == (result['selected'] is not None)
        cases.append(row); expected.append(result); names.append(name)
        if bounds or preferred is None:
            continue
        # This narrower Bend projection covers explicit selection/actual
        # admission. Lean separately compares recommendations and constraints.
        profile = next((p for p in profiles if p['game'] == game), None)
        known = profile is not None
        floor = max(8, profile['historical']) if known else 8
        allowed = lambda major: f'J.admitted({major}n,{floor}n,{bit(known)},{bit(known and major in profile["supported"])})'
        expression = allowed(preferred)
        if observed is not None:
            expression = f'J.actual_admitted({expression},{allowed(observed)},{bit(known)},{bit(preferred == observed)})'
        calls.append('Bool.show(' + expression + ') ++ "\\n"')
        bend_expected.append(str(stage == 'ok'))
    assert len(cases) == len(set(names)) == receipt['cases'] == 343
    # Keep raw Java properties private; verify the small public observation
    # against the original bytes without treating our decoder as engine code.
    for observation in receipt['jdkObservations']:
        label = 'jdk-' + str(observation['requested'])
        command = next(c for c in commands if c['case'] == label)
        assert command['private'] and all(s['path'].startswith('work/private/') for s in command['streams'].values())
        values = []
        for stream in command['streams'].values():
            for line in (run / stream['path']).read_text().splitlines():
                key, separator, value = line.partition('=')
                if separator and key.strip() == 'java.specification.version':
                    values.append(value.strip())
        assert len(values) == 1 and int(values[0].removeprefix('1.')) == observation['actualMajor']
    basis = {str(p.relative_to(ROOT)): sha(p) for p in files}
    generated = HERE / 'generated'; generated.mkdir(exist_ok=True)
    path = generated / 'java.json'
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    env = dict(os.environ, LEAN_PATH='.build/formal:.build', BEND_NO_TELEMETRY='1')

    def replay(value):
        path.write_text(json.dumps(value) + '\n')
        return subprocess.run([lean, '--run', str(HERE / 'JavaCase.lean'), str(path)],
                              cwd=ROOT, env=env, capture_output=True, text=True)

    value = dict(schema=1, profiles=profiles, cases=cases)
    result = replay(value)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == expected
    driver = generated / 'JavaCase.bend'
    driver.write_text('import Base\nimport ../Java.bend as J\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(calls) + ')\n')
    result = subprocess.run([bend, str(driver)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == bend_expected
    invalids = [('schema', dict(value, schema=2), 'Unsupported Java research schema'),
                ('duplicate-game', dict(value, profiles=profiles + profiles[:1]), 'Duplicate exact game identity'),
                ('unsorted-majors', dict(value, profiles=[dict(profiles[0], supported=[17,16])]), 'ordered finite admitted set'),
                ('empty-majors', dict(value, profiles=[dict(profiles[0], supported=[])]), 'ordered finite admitted set'),
                ('missing-preference', dict(value, cases=[dict(cases[0], actual=17)]), 'Actual check needs'),
                ('major-domain', dict(value, cases=[dict(cases[0], preferred=65536)]), 'exceeds the source u16 domain')]
    for label, invalid, message in invalids:
        result = replay(invalid)
        assert result.returncode == 2 and message in result.stderr, label
    path.write_text(json.dumps(value, indent=2) + '\n')
    assert all(sha(ROOT / p) == h for p, h in basis.items()), 'Evidence changed while consumed.'
    report = dict(schema=1, basisSha256=basis, sourcePins=len(pins), sourceRevision=revision,
        profiles=112, coreCases=343, leanCases=len(cases), bendExplicitAdmissionDecisions=len(calls),
        constraintCases=sum(bool(c['bounds']) for c in cases), invalidResearchInputsRefused=[i[0] for i in invalids],
        nativeJdkMajors=[p['actualMajor'] for p in receipt['jdkObservations']],
        rejectedInterpretations=['A preferred major is always an exact execution requirement.',
            'A Java major newer than the minimum is automatically admitted.',
            'An unlisted game can inherit a known prefix profile.',
            'An unknown game admits any newer actual major once an explicit preference is saved.',
            'The host highest installed Java changes the recommendation.',
            'The core constraint API proves all loader/mod constraints are wired into production resolution.'],
        limits=['Actual unchanged core library reused from the attributed prior compile,one new caller compilation;not installed empack binary or engine execution.',
            '112checked-in profiles,selected explicit/actual majors and15constraint sequences;not every u16 combination or external metadata validity.',
            'Two native JVM properties are fixture-decoded;the engine parser/probe/approval/lease are source-only here.',
            'ReleaseJava serialization,verified server metadata minimums andinteractive UX are source-inspected,not executed by these core cases.',
            'No complete mod graph,loader runtime,JNI/vendor/architecture/flags,gameplay orfuture JVM compatibility proof.',
            'Private JVM output andattributed library remain owner-local;public checkout cannot verify withheld byte identities alone.'])
    (run / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'basisSha256'}, indent=2))


if __name__ == '__main__':
    main()
