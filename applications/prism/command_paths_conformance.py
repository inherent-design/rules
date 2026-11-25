"""Replay the retained export/INI/parser boundary; never launch a studied program."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'applications/evidence/prism-command-paths-20261125T173349259410Z'
FAILED = ROOT / 'applications/evidence/prism-command-paths-20261125T173202810392Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def units(text):
    raw = text.encode('utf-16-le')
    return [int.from_bytes(raw[i:i + 2], 'little') for i in range(0, len(raw), 2)]


def compare(actual, expected):
    assert actual == expected, 'Quoted program differs from retained parser output'


def main():
    setup, receipt = load(RUN / 'setup.json'), load(RUN / 'receipt.json')
    assert receipt['complete'] and receipt['cases'] == 6 and not receipt['workPathProcessMatches']
    assert sha(RUN / 'probe.py') == setup['producerSha256']
    assert sha(RUN / 'fixture.py') == setup['fixtureProducerSha256']
    prior = ROOT / setup['priorParserReceipt']
    assert sha(prior) == setup['priorParserReceiptSha256']
    old = load(prior)
    assert old['binaries']['release']['sha256'] == setup['parserSha256']
    ledger = ROOT / 'applications/sources/prism-command-paths-selections.json'
    assert sha(ledger) == setup['sourceLedgerSha256']
    available, unavailable = [], []
    for item in load(ledger)['prism'] + load(ledger)['empack']:
        path = ROOT / item['cache'] if 'cache' in item else None
        if path is not None and path.exists():
            raw = path.read_bytes()
        elif 'revision' in item and (ROOT.parent / 'empack/.git').exists():
            raw = subprocess.check_output(['git', '-C', str(ROOT.parent / 'empack'), 'show', item['revision'] + ':' + item['path']])
        else:
            unavailable.append(item['path'])
            continue
        assert hashlib.sha256(raw).hexdigest() == item['sha256']
        if 'gitBlob' in item:
            assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == item['gitBlob']
        available.append(item['path'])
    work = Path(receipt['work'])
    if work.exists():
        assert sha(work / 'reader.cpp') == setup['readerSourceSha256']
        for copied in setup['copiedSources']:
            assert sha(work / copied['relative']) == copied['sha256']
    artifacts = {}
    for path, digest in [(setup['binary'], setup['binarySha256']), (setup['parser'], setup['parserSha256']),
                         (str(Path(receipt['work']) / 'ini-reader'), receipt['iniReaderSha256'])]:
        p = Path(path)
        artifacts[path] = 'unavailable'
        if p.exists():
            assert sha(p) == digest
            artifacts[path] = 'identity checked, not executed'
    candidates = list((Path(receipt['work']) / 'project/dist').glob('*.zip'))
    archive = candidates[0] if len(candidates) == 1 else Path(receipt['work']) / 'reference.zip'
    # The generated archive contains a tool JAR. It remains owner-local, not a Git tool cache.
    if not archive.exists():
        archive = RUN / 'reference.zip'
    archive_status = 'unavailable; retained config and member receipt only'
    if archive.exists():
        assert sha(archive) == receipt['archiveSha256']
        with zipfile.ZipFile(archive) as z:
            members = [dict(path=i.filename, bytes=i.file_size,
                            sha256=hashlib.sha256(z.read(i)).hexdigest()) for i in z.infolist()]
            assert members == receipt['members']
            assert z.read('instance.cfg') == (RUN / 'instance.cfg').read_bytes()
        archive_status = 'all original member bytes checked, not executed'
    assert sha(RUN / 'instance.cfg') == receipt['configSha256']
    commands = load(RUN / 'commands.json')
    assert len(commands) == 12 and len({r['label'] for r in commands}) == 12
    for command in commands:
        assert command['exitCode'] == 0 and command['processGroupAbsent'] and not command['timedOut']
        for stream in ['stdout', 'stderr']:
            assert sha(RUN / (command['label'] + '.' + stream)) == command['streams'][stream]
    decoded = load(RUN / 'read-generated.stdout')
    assert decoded['loaded'] and decoded['override'] and decoded['version'] == '1.3'
    inputs, expected, reconstructed = [], [], []
    for row in load(RUN / 'observed.json')['cases']:
        request = load(RUN / (row['id'] + '-input.json'))
        native = load(RUN / (row['id'] + '.stdout'))
        assert request['mode'] == 'parse' and request['command'] == decoded[row['role']]
        assert native['phase'] == 'before' and native['mode'] == 'parse'
        assert native['raw'] == request['command'] and native['qtVersion'] == row['qtVersion']
        value = request['environment']['INST_JAVA']
        assert native['expanded'] == request['command'].replace('$INST_JAVA', value)
        args = native['wrapperArgs'] if row['role'] == 'wrapper' else native['hookArgs']
        assert len(args) == (7 if row['role'] == 'wrapper' else 6)
        assert args[1:5] == ['-Dfile.encoding=UTF-8', '-jar', '../.empack-tools/empack-bootstrap.jar', '--invocation-file']
        assert args[5] == '../.empack-tools/' + ('launch.json' if row['role'] == 'wrapper' else 'prepare.json')
        if row['role'] == 'wrapper':
            assert args[-1] == '--'
        rebuilt = dict(id=row['id'], role=row['role'], expectedProgram=value, actualProgram=args[0],
                       preserved=args[0] == value, consumerArgs=args, qtVersion=native['qtVersion'])
        assert rebuilt == row
        reconstructed.append(rebuilt)
        inputs.append(dict(id=row['id'], wrapper=row['role'] == 'wrapper', units=units(value)))
        expected.append(dict(id=row['id'], program=units(args[0]), preserved=args[0] == value))
    assert [r['id'] for r in reconstructed if not r['preserved']] == ['windows-native-wrapper']
    failure = load(FAILED / 'failure.json')
    assert failure['consumerCases'] == 0 and failure['builds'] == 0 and failure['allRecordedGroupsAbsent']
    assert '0700' in (FAILED / 'native-check.stderr').read_text()
    assert (RUN / 'incomplete.json').exists() and (RUN / 'continuation.json').exists()
    write(RUN / 'model-input.json', dict(schema=1, cases=inputs))
    write(RUN / 'observed-model-values.json', expected)
    proof = load(RUN / 'proof-gate.json')
    assert proof['observedExitCode'] == 0
    for path, digest in proof['sourceSha256'].items():
        assert sha(ROOT / path) == digest
    formal = ROOT / '.build/prism-command-paths-formal'
    formal.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'LEAN_PATH': str(formal), 'BEND_NO_TELEMETRY': '1'}
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    command = [lean, '--run', 'applications/prism/CommandPathsCase.lean']
    result = subprocess.run(command + [str(RUN / 'model-input.json')], cwd=ROOT, env=env, text=True, capture_output=True, check=True)
    actual = json.loads(result.stdout)
    compare(actual, expected)
    calls, wanted = [], []
    for row, native in zip(inputs, expected, strict=True):
        values = '[' + ','.join(str(n) + 'n' for n in row['units']) + ']'
        calls.append('P.show_units(P.program(' + ('True{}' if row['wrapper'] else 'False{}') + ',' + values + '))')
        wanted.append(''.join(str(n) + ',' for n in native['program']))
    target = formal / 'Replay.bend'
    target.write_text('import ../../applications/prism/CommandPaths.bend as P\nimport Base\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ "\\n" ++ '.join(calls) + ' ++ "\\n")\n')
    result = subprocess.run([bend, str(target)], cwd=ROOT, env=env, text=True, capture_output=True, check=True)
    compare(result.stdout.splitlines(), wanted)
    controls = []
    for label, field, value in [('loss-hidden', 'preserved', True), ('program-restored', 'program', inputs[3]['units'])]:
        changed = copy.deepcopy(expected)
        changed[3][field] = value
        try:
            compare(actual, changed)
        except AssertionError:
            controls.append(label)
        else:
            raise AssertionError('Changed observation escaped')
    for label, change in [('schema', lambda d: d.update(schema=2)),
                          ('quote', lambda d: d['cases'][0].update(units=[34])),
                          ('trailing-escape', lambda d: d['cases'][0].update(units=[92])),
                          ('empty', lambda d: d['cases'][0].update(units=[])),
                          ('non-utf16', lambda d: d['cases'][0].update(units=[65536]))]:
        changed = dict(schema=1, cases=copy.deepcopy(inputs))
        change(changed)
        path = formal / (label + '.json')
        write(path, changed)
        result = subprocess.run(command + [str(path)], cwd=ROOT, env=env, text=True, capture_output=True)
        assert result.returncode == 2 and 'research' in result.stderr
        controls.append(label)
    files = [p for directory in [RUN, FAILED] for p in directory.iterdir()
             if p.is_file() and p.suffix != '.zip' and p.name not in ['basis.json', 'conformance.json']]
    files += [ROOT / 'applications/prism' / name for name in
              ['command_paths_probe.py', 'command_paths_conformance.py', 'CommandPaths.lean', 'CommandPathsCase.lean', 'CommandPaths.bend']]
    files.append(ledger)
    write(RUN / 'basis.json', {str(p.relative_to(ROOT)): sha(p) for p in files})
    report = dict(schema=1, nativeParserCases=6, nativeCommandGroups=12, modelComparisons=6,
                  leanLaws=11, bendLaws=6, controls=controls, availableSources=available, unavailableSources=unavailable,
                  archive=archive_status, artifacts=artifacts, basisFiles=len(files),
                  limits=['Quoted program payload only, not a complete grammar.',
                          'Windows paths are data on Mac; no Windows launch or full Prism workflow.',
                          'Backslash escaping is a model-only candidate, not an implemented correction.',
                          'Installed engine/source correspondence and current upstream develop are unqualified.'])
    write(RUN / 'conformance.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
