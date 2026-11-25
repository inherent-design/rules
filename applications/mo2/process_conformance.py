"""Compare retained controlled-source observations without running a child fixture."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUN = ROOT / 'applications/evidence/mo2-process-20261125T161939910466Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())


def write(p, value):
    p.write_text(json.dumps(value, indent=2) + '\n')


def observations(text):
    rows = []
    for line in text.splitlines():
        name, *values = line.split()
        assert len(values) == 9, 'Malformed process-policy observation'
        numbers = [int(n) for n in values]
        assert all(n in [0, 1] for n in numbers[2:]), 'Non-Boolean callback observation'
        rows.append(dict(id=name, values=numbers))
    assert len({r['id'] for r in rows}) == len(rows), 'Duplicate observation identity'
    return rows


def compare(actual, expected):
    assert actual == expected, 'Process-policy projection differs from retained observation'


def main():
    receipt = load(RUN / 'receipt.json')
    assert receipt['complete'] and receipt['cases'] == 20
    assert sha(RUN / 'probe.py') == receipt['producerSha256']
    assert sha(RUN / 'driver.cpp') == receipt['driverSha256']
    assert sha(RUN / 'input.json') == receipt['inputSha256']
    for r in receipt['commands']:
        assert r['exitCode'] == 0 and r['processGroupAbsent']
        for stream in ['stdout', 'stderr']:
            assert sha(RUN / (r['name'] + '.' + stream)) == r[stream + 'Sha256']
    ledger = load(ROOT / 'applications/sources/mo2-process-selections.json')
    available, unavailable = [], []
    reconstructed = False
    for row in ledger['sources']:
        p = ROOT / row['cache']
        if not p.exists():
            unavailable.append(row['path'])
            continue
        b = p.read_bytes()
        assert sha(p) == row['sha256']
        assert hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest() == row['gitBlob']
        available.append(row['path'])
        if row['path'] == 'src/processrunner.cpp':
            assert row == receipt['source']
            text, bodies = b.decode(), []
            for cut in receipt['cuts']:
                body = text[cut['textOffset']:cut['textOffset'] + cut['textLength']]
                assert body.startswith(cut['start']) and hashlib.sha256(body.encode()).hexdigest() == cut['sha256']
                assert text[cut['textOffset'] + cut['textLength']:].startswith(cut['end'])
                bodies.append(body)
            generated = (RUN / 'driver.cpp').read_text().replace('// @@SELECTED_METHODS@@', '\n'.join(bodies))
            assert hashlib.sha256(generated.encode()).hexdigest() == receipt['generatedSha256']
            reconstructed = True
    work = Path(receipt['work'])
    artifacts = {}
    for path, digest in [(work / 'main.cpp', receipt['generatedSha256']),
                         (work / 'probe', receipt['binarySha256']),
                         (Path('/usr/bin/clang++'), receipt['compilerSha256'])]:
        artifacts[str(path)] = 'unavailable'
        if path.exists():
            assert sha(path) == digest
            artifacts[str(path)] = 'identity checked, not executed'
    proof = load(RUN / 'proof-gate.json')
    assert proof['observedExitCode'] == 0
    for tool in proof['tools'].values():
        p = Path(tool['path'])
        if p.exists():
            assert sha(p) == tool['sha256'], 'Formal tool identity changed since recorded gate'
    for path, digest in proof['sourceSha256'].items():
        assert sha(ROOT / path) == digest, 'Formal input changed since recorded gate'
    inputs = load(RUN / 'input.json')
    expected = observations((RUN / 'observed.stdout').read_text())
    assert [r['id'] for r in inputs['cases']] == [r['id'] for r in expected]
    formal = ROOT / '.build/mo2-process-formal'
    formal.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'LEAN_PATH': str(formal), 'BEND_NO_TELEMETRY': '1'}
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    command = [lean, '--run', 'applications/mo2/ProcessCase.lean']
    result = subprocess.run(command, input=json.dumps(inputs), cwd=ROOT, env=env,
                            capture_output=True, text=True, check=True)
    actual = json.loads(result.stdout)
    compare(actual, expected)
    calls, wanted = [], []
    bo = lambda b: 'True{}' if b else 'False{}'
    number = lambda e: 'Nat.show(' + e + ')'
    boolean = lambda e: number('Bool.pick(Nat,' + e + ',1n,0n)')
    for row, measured in zip(inputs['cases'], expected, strict=True):
        hooked, force, trigger, locking = [bo(b) for b in [row['hooked'] == 1,
            bool(row['flags'] & 2), bool(row['flags'] & 1), row['lockEnabled'] == 1]]
        reason, result = str(row['reason']) + 'n', str(row['waitResult']) + 'n'
        args = ','.join([hooked, force, reason, locking])
        early = 'P.early(' + args + ')'
        waited = 'Bool.not(' + early + ')'
        background = 'P.background(' + ','.join([force, reason, locking]) + ')'
        after = 'P.after(' + args + ',' + trigger + ',' + result + ')'
        refresh_wait = 'Bool.and(' + after + ',' + bo(bool(row['flags'] & 4)) + ')'
        expressions = [number('P.returned(' + args + ',' + result + ')'),
            number('P.reason_after(' + force + ',' + reason + ')'), boolean(waited),
            boolean('Bool.and(' + waited + ',Bool.not(' + background + '))'),
            boolean('Bool.and(' + waited + ',' + background + ')'),
            boolean(after), boolean(refresh_wait), boolean(refresh_wait),
            boolean('P.refresh(' + trigger + ',' + result + ')')]
        calls.extend(expressions)
        wanted.extend(str(n) for n in measured['values'])
    case = formal / 'Replay.bend'
    case.write_text('import ../../applications/mo2/Process.bend as P\nimport Base\ndef main() -> IO(Unit):\n  IO.write(' +
                    ' ++ "\\n" ++ '.join(calls) + ' ++ "\\n")\n')
    result = subprocess.run([bend, str(case)], cwd=ROOT, env=env, capture_output=True, text=True, check=True)
    compare(result.stdout.splitlines(), wanted)
    controls = []
    for label, name, index, value in [('early-unlock-refresh', 'disabled-gui', 5, 1),
            ('background-ui', 'forced-background', 3, 1),
            ('cancel-as-completed', 'ordinary-cancelled', 0, 2),
            ('unhooked-wait', 'unhooked', 2, 1),
            ('ignored-refresh-flag', 'wait-bit-without-trigger', 7, 1)]:
        changed = copy.deepcopy(expected)
        next(r for r in changed if r['id'] == name)['values'][index] = value
        try:
            compare(actual, changed)
        except AssertionError as error:
            assert 'projection differs' in str(error)
            controls.append(label)
        else:
            raise AssertionError('Changed measured outcome escaped')
    for label, change, cause in [('schema', lambda d: d.update(schema=2), 'research schema'),
            ('flags', lambda d: d['cases'][0].update(flags=8), 'research input'),
            ('reason', lambda d: d['cases'][0].update(reason=4), 'research input'),
            ('wait-result', lambda d: d['cases'][0].update(waitResult=0), 'research input'),
            ('boolean', lambda d: d['cases'][0].update(hooked=2), 'research input')]:
        changed = copy.deepcopy(inputs)
        change(changed)
        result = subprocess.run(command, input=json.dumps(changed), cwd=ROOT, env=env,
                                capture_output=True, text=True)
        assert result.returncode != 0 and cause in result.stderr, (label, result.stderr)
        controls.append(label)
    files = [p for p in RUN.iterdir() if p.is_file() and p.name not in ['basis.json', 'conformance.json']]
    files += [HERE / name for name in ['process_driver.cpp', 'process_probe.py', 'process_conformance.py',
                                      'Process.lean', 'ProcessCase.lean', 'Process.bend']]
    files.append(ROOT / 'applications/sources/mo2-process-selections.json')
    write(RUN / 'basis.json', {str(p.relative_to(ROOT)): sha(p) for p in files})
    report = dict(schema=1, sourceMethods=2, controlledCases=20, leanOutcomeMatch=True,
        bendScalarComparisons=len(calls), leanLaws=15, bendLaws=7, negativeControls=controls,
        sourceCachesChecked=available, sourceCachesUnavailable=unavailable,
        selectedBodiesReconstructed=reconstructed, artifacts=artifacts, basisFiles=len(files),
        limits=['Only selected postRun/shouldRefresh bodies execute; all host/lifecycle APIs are controlled adapters.',
                'Running is an injected typed outcome, not proof the real wait loop returns it.',
                'Source-only callers/profile guards/handle transfer are not full Windows MO2 qualification.',
                'Wait return, lock release, requested refresh and event-loop adapter are not child retirement, saved output or durable refresh acknowledgement.'])
    write(RUN / 'conformance.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
