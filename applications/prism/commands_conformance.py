"""Replay retained command/child observations; never compile or launch Prism/processes."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

from commands_observations import packets

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUN = ROOT / 'applications/evidence/prism-commands-20261125T165137028675Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())


def write(p, value):
    p.write_text(json.dumps(value, indent=2) + '\n')


def compare(actual, expected):
    assert actual == expected, 'Prism command boundary differs from retained observation'


def main():
    receipt = load(RUN / 'receipt.json')
    assert receipt['complete'] and receipt['cases'] == 22 and not receipt['workPathProcessMatches']
    for name, field in [('probe.py', 'producerSha256'), ('driver.cpp', 'driverSha256'), ('adapter.h', 'adapterSha256')]:
        assert sha(RUN / name) == receipt[field]
    ledger_path = ROOT / 'applications/sources/prism-command-selections.json'
    assert sha(ledger_path) == receipt['sourceLedgerSha256']
    ledger = load(ledger_path)
    context_path = ROOT / 'applications/sources/prism-command-context.json'
    context_checks = []
    for row in load(context_path)['sources']:
        repo = ROOT.parent / row['application']
        if (repo / '.git').exists():
            raw = subprocess.check_output(['git', '-C', str(repo), 'show', row['revision'] + ':' + row['path']])
            assert hashlib.sha256(raw).hexdigest() == row['sha256']
            assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['gitBlob']
            context_checks.append(row['path'])
    sources, unavailable = {}, []
    for row in ledger['sources']:
        p = ROOT / row['cache']
        if not p.exists():
            unavailable.append(row['path'])
            continue
        b = p.read_bytes()
        assert sha(p) == row['sha256']
        assert hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest() == row['gitBlob']
        sources[row['path']] = b
    reconstructed = False
    if 'launcher/launch/LaunchTask.cpp' in sources and 'launcher/minecraft/launch/LauncherPartLaunch.cpp' in sources:
        task = sources['launcher/launch/LaunchTask.cpp'].decode()
        variables = task[task.index('QString expandVariables('):]
        text = sources['launcher/minecraft/launch/LauncherPartLaunch.cpp'].decode()
        begin = text.index('    QString wrapperCommandStr =')
        block = text[begin:text.index('\n#ifdef Q_OS_LINUX', begin)]
        assert hashlib.sha256(variables.encode()).hexdigest() == receipt['variableFunctionsSha256']
        assert hashlib.sha256(block.encode()).hexdigest() == receipt['wrapperBlockSha256']
        generated = (RUN / 'driver.cpp').read_text().replace('// @@VARIABLE_FUNCTIONS@@', variables).replace('// @@WRAPPER_BLOCK@@', block)
        assert hashlib.sha256(generated.encode()).hexdigest() == receipt['generatedSha256']
        reconstructed = True
    artifact_checks = {}
    artifacts = [(receipt['compiler']['path'], receipt['compiler']['sha256']),
                 (receipt['moc']['path'], receipt['moc']['sha256']),
                 (receipt['qt']['framework'], receipt['qt']['sha256'])]
    artifacts += [(r['path'], r['sha256']) for r in receipt['binaries'].values()]
    artifacts.append((str(Path(receipt['work']) / 'main.cpp'), receipt['generatedSha256']))
    for path, digest in artifacts:
        p = Path(path)
        artifact_checks[path] = 'unavailable'
        if p.exists():
            assert sha(p) == digest
            artifact_checks[path] = 'identity checked, not executed'
    commands = load(RUN / 'commands.json')
    assert len(commands) == 31 and len({r['label'] for r in commands}) == 31
    for row in commands:
        assert row['processGroupAbsent'] and not row['timedOut']
        for stream in ['stdout', 'stderr']:
            assert sha(RUN / (row['label'] + '.' + stream)) == row['streams'][stream]
    observed = load(RUN / 'observed.json')['cases']
    abrupt = []
    for row in observed:
        command = next(c for c in commands if c['label'] == row['id'])
        assert row['helperExitCode'] == command['exitCode']
        parsed = [json.loads(s) for s in (RUN / (row['id'] + '.stdout')).read_text().splitlines()]
        assert parsed == row['packets']
        if row['child']:
            assert row['childAbsent']
            p = Path(receipt['work']) / (row['id'] + '-child.json')
            if p.exists():
                assert load(p) == row['child']
        if row['helperExitCode'] < 0:
            assert row['helperExitCode'] == (-6 if row['variant'] == 'checked' else -11)
            assert len(parsed) == 1 and parsed[0]['phase'] == 'before'
            abrupt.append(row['id'])
    # The original compiler refusal is retained separately, not counted as native cases.
    failed = ROOT / 'applications/evidence/prism-commands-20261125T165058035388Z'
    failure = load(failed / 'failure.json')
    assert failure['nativeCases'] == 0 and failure['status'] == 'excluded-before-native-cases'
    assert 'm_instance' in (failed / 'compile-release.stderr').read_text()
    inputs, expected, parser = packets(RUN)
    assert len(inputs['cases']) == 17 and len(parser) == 5 and len(abrupt) == 5
    write(RUN / 'model-input.json', inputs)
    write(RUN / 'observed-model-values.json', expected)
    write(RUN / 'parser-observations.json', parser)
    proof = load(RUN / 'proof-gate.json')
    assert proof['observedExitCode'] == 0
    for p, h in proof['sourceSha256'].items():
        assert sha(ROOT / p) == h
    formal = ROOT / '.build/prism-commands-formal'
    formal.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'LEAN_PATH': str(formal), 'BEND_NO_TELEMETRY': '1'}
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    command = [lean, '--run', 'applications/prism/CommandsCase.lean']
    result = subprocess.run(command + [str(RUN / 'model-input.json')], cwd=ROOT, env=env,
                            text=True, capture_output=True, check=True)
    actual = json.loads(result.stdout)
    compare(actual, expected)
    bo = lambda b: 'True{}' if b else 'False{}'
    li = lambda values: '[' + ','.join(str(v) + 'n' for v in values) + ']'
    calls, wanted = [], []
    for row, native in zip(inputs['cases'], expected, strict=True):
        kind = 'P.disposition(' + ','.join([str(row['mode']) + 'n', bo(row['rawNonempty']), bo(row['trimmedEmpty']),
                                           li(row['tokens']), bo(row['programExists'])]) + ')'
        process = str(row['processResult']) + 'n'
        calls += ['Nat.show(' + kind + ')', 'Bool.show(P.terminal(' + kind + '))',
                  'Bool.show(P.successful(' + kind + ',' + process + '))',
                  'Bool.show(P.child(' + kind + ',' + process + '))',
                  'Bool.show(P.abort_accepted(' + kind + ',' + bo(row['abortRequested']) + '))',
                  'P.show_args(P.child_args(' + kind + ',' + process + ',' + li(row['tokens']) + ',' + li(row['gameArgs']) + '))']
        wanted += [str(native['disposition']), str(native['terminal']), str(native['successful']),
                   str(native['child']), str(native['abortAccepted']), ''.join(str(n) + ',' for n in native['childArgs'])]
    target = formal / 'Replay.bend'
    target.write_text('import ../../applications/prism/Commands.bend as P\nimport Base\ndef main() -> IO(Unit):\n  IO.write(' +
                      ' ++ "\\n" ++ '.join(calls) + ' ++ "\\n")\n')
    result = subprocess.run([bend, str(target)], cwd=ROOT, env=env, text=True, capture_output=True, check=True)
    compare(result.stdout.splitlines(), wanted)
    controls = []
    for label, name, field, value in [('empty-as-safe-refusal', 'pre-space-release', 'terminal', True),
            ('missing-as-success', 'pre-missing-release', 'successful', True),
            ('abort-not-accepted', 'pre-abort-release', 'abortAccepted', False),
            ('wrapper-loses-java', 'wrapper-ok-release', 'childArgs', [7,8,1,2,9,4])]:
        changed = copy.deepcopy(expected)
        next(r for r in changed if r['id'] == name)[field] = value
        try:
            compare(actual, changed)
        except AssertionError as error:
            assert 'differs from retained' in str(error)
            controls.append(label)
        else:
            raise AssertionError('Changed native projection escaped')
    for label, change, cause in [('schema', lambda d: d.update(schema=2), 'research schema'),
            ('mode', lambda d: d['cases'][0].update(mode=3), 'research profile'),
            ('result', lambda d: d['cases'][0].update(processResult=4), 'research profile'),
            ('token', lambda d: d['cases'][0].update(tokens=[32]), 'research profile')]:
        changed = copy.deepcopy(inputs)
        change(changed)
        path = formal / (label + '.json')
        write(path, changed)
        result = subprocess.run(command + [str(path)], cwd=ROOT, env=env, text=True, capture_output=True)
        assert result.returncode == 2 and cause in result.stderr
        controls.append(label)
    files = [p for p in RUN.iterdir() if p.is_file() and p.name not in ['basis.json', 'conformance.json']]
    files += [p for p in failed.iterdir() if p.is_file()]
    files += [HERE / n for n in ['commands_adapter.h', 'commands_driver.cpp', 'commands_probe.py',
                                'commands_observations.py', 'commands_conformance.py',
                                'Commands.lean', 'CommandsCase.lean', 'Commands.bend']]
    files.append(ledger_path)
    files.append(context_path)
    write(RUN / 'basis.json', {str(p.relative_to(ROOT)): sha(p) for p in files})
    report = dict(schema=1, nativeCases=22, definedExecutionCases=12, parsedBoundaryCases=5, literalParserObservations=5,
        interpretedModelCases=17, bendFieldComparisons=len(calls), leanLaws=15, bendLaws=7,
        negativeControls=controls, ownedCommandGroups=31, ownChildWitnesses=sum(r['child'] is not None for r in observed),
        availableSourcePins=len(sources), unavailableSourcePins=unavailable, generatedSourceReconstructed=reconstructed,
        availableContextPins=context_checks,
        artifactChecks=artifact_checks, basisFiles=len(files),
        limits=['Parsed tokens are observed premises; no complete parser conformance claim.',
                'Five abrupt empty-token helpers classify an unmet source precondition,not a defined API refusal or a predicted general signal.',
                'Wrapper completion and Java-data invocation are adapters; the same helper fills both program roles.',
                'Instance/environment/Task declarations are adapters;no Prism GUI/game/Java/Windows/account qualification.',
                'Whole process-tree retirement,detachment,post-after-crash behavior and settings persistence remain unqualified.'])
    write(RUN / 'conformance.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
