"""Compare retained Cargo target/harness/body observations without running Cargo."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'applications/evidence/cargo-testing-20261125T175749444083Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())
BODY = ['unit:a', 'unit:b', 'unit:ignored', 'integration:a', 'integration:b', 'custom:main', 'doc:run']


def write(p, value):
    p.write_text(json.dumps(value, indent=2) + '\n')


def compare(actual, expected):
    assert actual == expected, 'Test execution differs from retained observation'


def invoked(stderr):
    result = []
    prefixes = [('fixture_test_contract-', 0), ('a_api-', 1), ('b_api-', 2), ('custom-', 3), ('demo-', 4)]
    for line in stderr.splitlines():
        if 'Running ' in line:
            match = re.search(r'\(([^)]+)\)$', line)
            assert match, line
            name = Path(match[1]).name
            matches = [n for prefix, n in prefixes if name.startswith(prefix)]
            assert len(matches) == 1, name
            result += matches
        elif line.strip().startswith('Doc-tests '):
            assert line.strip() == 'Doc-tests fixture_test_contract'
            result.append(5)
    return result


def main():
    setup, receipt = load(RUN / 'setup.json'), load(RUN / 'receipt.json')
    assert receipt['complete'] and receipt['targetCleaned'] and receipt['commands'] == 13
    assert receipt['allRecordedGroupsAbsent'] and not receipt['workPathProcessMatches']
    assert sha(RUN / 'probe.py') == setup['producerSha256']
    ledger = ROOT / 'applications/sources/cargo-testing-selections.json'
    assert sha(ledger) == setup['sourceLedgerSha256'] == receipt['sourceLedgerSha256']
    sources_available, sources_unavailable = [], []
    for item in load(ledger):
        p = ROOT / item['cache']
        if not p.exists():
            sources_unavailable.append(item['path'])
            continue
        raw = p.read_bytes()
        assert sha(p) == item['sha256']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == item['gitBlob']
        sources_available.append(item['path'])
    work = Path(receipt['work'])
    authored = load(RUN / 'sources.json')
    hashes = {p: hashlib.sha256(text.encode()).hexdigest() for p, text in authored.items()}
    if work.exists():
        assert not (work / 'target').exists()
        for p, digest in hashes.items():
            assert sha(work / 'project' / p) == digest
    tool_status = {}
    for name, item in setup['tools'].items():
        p = Path(item['path'])
        tool_status[name] = 'unavailable'
        if p.exists():
            assert sha(p) == item['sha256']
            tool_status[name] = 'identity checked, not executed'
    inputs, expected = [], []
    rows = load(RUN / 'commands.json')
    assert len(rows) == 13 and len({r['id'] for r in rows}) == 13
    for row in rows:
        assert row['processGroupAbsent'] and not row['timedOut']
        assert row['exitCode'] == row['expectedExit']
        assert row['authoredBefore'] == row['authoredAfter'] == hashes
        for stream in ['stdout', 'stderr']:
            assert sha(RUN / (row['id'] + '.' + stream)) == row[stream + 'Sha256']
        assert load(RUN / (row['id'] + '-bodies.json')) == row['bodyTrace']
        trace = work / 'traces' / (row['id'] + '.txt')
        if trace.exists():
            assert trace.read_text().splitlines() == row['bodyTrace']
        args = row['argv'][1:]
        assert args[0] == '--offline'
        if args[1] != 'test':
            assert not row['bodyTrace']
            continue
        # The profile admits only these known request shapes, not arbitrary CLI text.
        scope = 1 if '--lib' in args else 2 if '--test' in args else 3 if '--doc' in args else 4 if '--all-targets' in args else 0
        selection = 3 if '--ignored' in args else 2 if 'nothing_matches' in args else 1 if 'tests::b_public' in args else 0
        inputs.append(dict(id=row['id'], scope=scope, filter=selection, noRun='--no-run' in args,
                           keepGoing='--no-fail-fast' in args, failUnit=row['failUnit']))
        stderr = (RUN / (row['id'] + '.stderr')).read_text()
        expected.append(dict(id=row['id'], invoked=invoked(stderr), bodies=[BODY.index(v) for v in row['bodyTrace']],
                             successful=row['exitCode'] == 0,
                             refused="Can't skip running doc tests with --no-run" in stderr))
    assert len(inputs) == 11
    compile_records = [json.loads(line) for line in (RUN / 'compile-only.stdout').read_text().splitlines()]
    exes = [r for r in compile_records if r.get('reason') == 'compiler-artifact' and r.get('executable')]
    artifacts = load(RUN / 'compiled-artifacts.json')
    assert [a['record'] for a in artifacts] == exes
    assert {r['target']['name'] for r in exes} == {'demo', 'fixture_test_contract', 'a_api', 'b_api', 'custom'}
    assert 'harness = false' in authored['Cargo.toml']
    assert 'nothing_matches' in (RUN / 'custom-filter.stdout').read_text()
    assert '3 passed; 0 failed; 1 ignored' in (RUN / 'doctest.stdout').read_text()
    assert 'compile fail ... ok' in (RUN / 'doctest.stdout').read_text()
    write(RUN / 'model-input.json', dict(schema=1, cases=inputs))
    write(RUN / 'observed-model-values.json', expected)
    proof = load(RUN / 'proof-gate.json')
    assert proof['observedExitCode'] == 0
    for p, digest in proof['sourceSha256'].items():
        assert sha(ROOT / p) == digest
    formal = ROOT / '.build/cargo-testing-formal'
    formal.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LEAN_PATH=str(formal), BEND_NO_TELEMETRY='1')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    command = [lean, '--run', 'applications/cargo/TestingCase.lean']
    actual = json.loads(subprocess.check_output(command + [str(RUN / 'model-input.json')], cwd=ROOT, env=env, text=True))
    compare(actual, expected)
    calls, wanted = [], []
    bo = lambda value: 'True{}' if value else 'False{}'
    for row, native in zip(inputs, expected, strict=True):
        args = ','.join([str(row['scope']) + 'n', str(row['filter']) + 'n', bo(row['noRun']), bo(row['failUnit']), bo(row['keepGoing'])])
        calls += ['P.show_units(P.run_invoked(' + args + '))', 'P.show_units(P.run_bodies(' + args + '))',
                  'Bool.show(P.success(' + ','.join(args.split(',')[:4]) + '))',
                  'Bool.show(P.refused(' + str(row['scope']) + 'n,' + bo(row['noRun']) + '))']
        wanted += [''.join(str(n) + ',' for n in native['invoked']), ''.join(str(n) + ',' for n in native['bodies']),
                   str(native['successful']), str(native['refused'])]
    target = formal / 'Replay.bend'
    target.write_text('import ../../applications/cargo/Testing.bend as P\nimport Base\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ "\\n" ++ '.join(calls) + ' ++ "\\n")\n')
    result = subprocess.run([bend, str(target)], cwd=ROOT, env=env, text=True, capture_output=True, check=True)
    compare(result.stdout.splitlines(), wanted)
    controls = []
    for label, name, field, value in [
        ('compile-is-run', 'compile-only', 'invoked', [0]),
        ('empty-filter-tests-body', 'empty-filter', 'bodies', [0]),
        ('custom-obeys-libtest-filter', 'custom-filter', 'bodies', []),
        ('fail-fast-stops-inside-harness', 'fail-fast', 'bodies', [0]),
        ('continue-makes-success', 'continue', 'successful', True),
        ('all-targets-runs-docs', 'all-targets', 'invoked', [0,1,2,3,4,5]),
        ('no-run-doc-body-executed', 'doctest', 'bodies', [6,7]),
        ('doc-no-run-succeeds', 'doctest-no-run-refusal', 'successful', True),
    ]:
        changed = copy.deepcopy(expected)
        next(r for r in changed if r['id'] == name)[field] = value
        try:
            compare(actual, changed)
        except AssertionError:
            controls.append(label)
        else:
            raise AssertionError('Changed observation escaped')
    for label, change in [('schema', lambda d: d.update(schema=2)), ('scope', lambda d: d['cases'][0].update(scope=5)),
                          ('filter', lambda d: d['cases'][0].update(filter=4)),
                          ('unsupported-filter-context', lambda d: d['cases'][0].update(filter=1))]:
        changed = dict(schema=1, cases=copy.deepcopy(inputs))
        change(changed)
        path = formal / (label + '.json')
        write(path, changed)
        result = subprocess.run(command + [str(path)], cwd=ROOT, env=env, text=True, capture_output=True)
        assert result.returncode == 2 and 'research' in result.stderr
        controls.append(label)
    files = [p for p in RUN.iterdir() if p.is_file() and p.name not in ['basis.json', 'conformance.json']]
    files += [ROOT / 'applications/cargo' / name for name in ['testing_probe.py', 'testing_conformance.py', 'Testing.lean', 'TestingCase.lean', 'Testing.bend']]
    files.append(ledger)
    write(RUN / 'basis.json', {str(p.relative_to(ROOT)): sha(p) for p in files})
    report = dict(schema=1, nativeCommands=13, testRequests=11, observedInvocations=sum(len(r['invoked']) for r in expected),
                  bodyEvents=sum(len(r['bodies']) for r in expected), bendFields=len(calls), leanLaws=14, bendLaws=8,
                  negativeControls=controls, availableSources=sources_available, unavailableSources=sources_unavailable,
                  artifacts=tool_status, basisFiles=len(files), peakTargetAllocatedKiB=receipt['peakTargetAllocatedKiB'],
                  limits=['One std-only fixture, captured compiler/target order, and closed request profile.',
                          'Target category and successful harness status do not establish test intent, API fidelity, or complete flow coverage.',
                          'No benchmarks, custom runner failure, parallel scheduling, Windows, or empack test execution.'])
    write(RUN / 'conformance.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
