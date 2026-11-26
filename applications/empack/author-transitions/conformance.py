"""Read retained core results and run only bounded Lean/Bend models."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN = ROOT / 'applications/evidence/empack-author-transitions-20261126T052842353539Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
write = lambda p, value: p.write_text(json.dumps(value, indent=2) + '\n')


def evidence(public_only=False):
    receipt = read(RUN / 'receipt.json')
    assert receipt['revision'] == '0b4462e3032b4f09230b15329722eabefb7f574c'
    assert receipt['cases'] == 15 and receipt['allRecordedGroupsAbsent']
    commands = read(RUN / 'commands.json')
    assert len(commands) == 2
    files = [RUN / 'receipt.json', RUN / 'commands.json']
    for item in commands:
        assert item['exitCode'] == 0 and not item['timedOut'] and item['groupAbsent']
        for stream in ['stdout', 'stderr']:
            path = RUN / (item['label'] + '.' + stream)
            assert sha(path) == item[stream + 'Sha256']; files.append(path)
    for name, field in [('probe.py', 'producerSha256'), ('oracle.rs', 'driverSha256'),
                        ('fixture-source.rs', 'fixtureSha256'), ('fixture-wrappers.rs', 'wrappersSha256'),
                        ('observed.stdout', 'observedSha256')]:
        path = RUN / name; assert sha(path) == receipt[field]; files.append(path)
    assert sha(HERE / 'probe.py') == receipt['producerSha256']
    assert sha(HERE / 'oracle.rs') == receipt['driverSha256']
    assert hashlib.sha256((RUN / 'fixture-source.rs').read_bytes() + (RUN / 'fixture-wrappers.rs').read_bytes()).hexdigest() == receipt['generatedFixtureSha256']
    prior = ROOT / receipt['priorCapture']; previous = read(prior / 'receipt.json')
    assert sha(prior / 'receipt.json') == receipt['priorReceiptSha256']; files.append(prior / 'receipt.json')
    assert previous['librarySha256'] == receipt['librarySha256'] and previous['sourceSha256'] == receipt['sourceSha256']
    private = [(prior / 'work/libempack_core.rlib', receipt['librarySha256']),
               (Path(receipt['compiler']['path']), receipt['compiler']['sha256']),
               (RUN / 'work/author-transitions', receipt['binarySha256']),
               (RUN / 'work/fixture.rs', receipt['generatedFixtureSha256'])]
    private += [(ROOT.parent / 'empack' / p, h) for p, h in receipt['sourceSha256'].items()]
    unavailable = []
    for path, digest in private:
        if public_only or not path.exists(): unavailable.append(str(path))
        else: assert sha(path) == digest
    return receipt, sorted(set(files)), unavailable


def observed(raw):
    rows = [json.loads(line) for line in raw.decode().splitlines()]
    assert len(rows) == len({r['case'] for r in rows}) == 15
    inputs, outputs = [], []
    for row in rows:
        inputs.append(dict(id=row['case'], **{k: row[k] for k in ['phase', 'held', 'version', 'requestPinned', 'missingRoot', 'runtimeMatches']}))
        outputs.append(dict(id=row['case'], **{k: row[k] for k in ['accepted', 'error', 'after', 'changed', 'bindings', 'inputUnchanged']}))
    return dict(schema=1, profile='fictional-core-author-admission', rows=inputs), outputs


def compare(actual, native):
    assert actual == native, 'Core author-admission projection differs from retained output.'


def main():
    assert sys.argv[1:] in [[], ['--public-only']]
    receipt, files, unavailable = evidence(bool(sys.argv[1:]))
    packet, expected = observed((RUN / 'observed.stdout').read_bytes())
    formal = ROOT / '.build/empack-author-admission-replay'
    formal.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'LEAN_PATH': str(formal), 'BEND_NO_TELEMETRY': '1'}
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    target = formal / 'applications/empack/author-transitions/Admission.olean'
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([lean, '-DwarningAsError=true', '-o', str(target), 'applications/empack/author-transitions/Admission.lean'], cwd=ROOT, env=env, check=True, timeout=60)
    path = formal / 'input.json'; write(path, packet)
    command = [lean, '--run', 'applications/empack/author-transitions/AdmissionCase.lean', str(path)]
    def replay(data):
        write(path, data)
        return subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    result = replay(packet); assert result.returncode == 0, result.stderr + result.stdout
    lean_rows = json.loads(result.stdout); compare(lean_rows, expected)
    b = lambda v: 'True{}' if v else 'False{}'
    phases = {'existing-adopt': 0, 'initial-adopt': 1, 'validate-target': 2}
    calls = ['A.result(' + ','.join([json.dumps(r['id']), str(phases[r['phase']]) + 'n', b(r['held']), str(r['version']) + 'n', b(r['missingRoot']), b(r['runtimeMatches'])]) + ')' for r in packet['rows']]
    driver = formal / 'Replay.bend'
    driver.write_text('import Base\nimport ../../applications/empack/author-transitions/Admission.bend as A\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ "\\n" ++ '.join(calls) + ' ++ "\\n")\n')
    result = subprocess.run([bend, str(driver)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr + result.stdout
    bend_rows = [json.loads(line) for line in result.stdout.splitlines()]; compare(bend_rows, expected)
    refusals = []
    controls = [
        ('schema', lambda x: x.update(schema=2), 'Unsupported research packet'),
        ('profile', lambda x: x.update(profile='production'), 'Unsupported research packet'),
        ('empty', lambda x: x.update(rows=[]), 'Unsupported research row count'),
        ('excessive', lambda x: x.update(rows=x['rows'] * 3), 'Unsupported research row count'),
        ('repeated', lambda x: x['rows'].append(copy.deepcopy(x['rows'][0])), 'Repeated research identity'),
        ('phase', lambda x: x['rows'][0].update(phase='migrate'), 'Unsupported research phase'),
        ('version', lambda x: x['rows'][0].update(version=3), 'Unsupported research selection'),
        ('missing-root-profile', lambda x: x['rows'][0].update(missingRoot=True), 'Unsupported missing-root profile'),
        ('initial-runtime', lambda x: x['rows'][7].update(runtimeMatches=False), 'Unsupported initial runtime profile'),
        ('target-pin', lambda x: x['rows'][11].update(requestPinned=True), 'Target validation does not consume a group pin'),
    ]
    for label, change, message in controls:
        bad = copy.deepcopy(packet); change(bad); result = replay(bad)
        assert result.returncode == 2 and not result.stdout and message in result.stderr, (label, result.stdout, result.stderr)
        refusals.append(label)
    mutations = []
    edits = [('held-bypassed', 4, 'accepted', True), ('wrong-error', 6, 'error', 'invalid-project'),
             ('automatic-minted-pin', 1, 'rootPin', 'Version2'), ('retained-record-lost', 1, 'locked', ['a', 'b']),
             ('selection-not-refreshed', 1, 'selected', 1), ('target-runtime-lost', 12, 'runtime', '1.21.1'),
             ('required-edge-lost', 1, 'edges', []), ('author-policy-rewritten', 1, 'intentPreserved', False),
             ('input-mutated', 1, 'inputUnchanged', False), ('unchanged-marked-changed', 0, 'changed', ['a'])]
    for label, index, field, value in edits:
        bad = copy.deepcopy(expected)
        target = bad[index]['after'] if field in ['rootPin', 'locked', 'selected', 'runtime', 'edges', 'intentPreserved'] else bad[index]
        target[field] = value
        for model in [lean_rows, bend_rows]:
            try: compare(model, bad)
            except AssertionError: pass
            else: raise AssertionError('Mutation was not detected: ' + label)
        mutations.append(label)
    write(path, packet)
    proof = read(RUN / 'proof-gate.json'); assert proof['observedExitCode'] == 0
    assert sha(RUN / 'proof-gate.log') == proof['logSha256']
    for p, h in proof['sourceSha256'].items(): assert sha(ROOT / p) == h
    files += [RUN / 'proof-gate.json', RUN / 'proof-gate.log', HERE / 'Admission.lean', HERE / 'AdmissionCase.lean', HERE / 'Admission.bend', HERE / 'conformance.py', HERE / 'probe.py', HERE / 'oracle.rs']
    out = dict(schema=1, cases=15, leanComparisons=len(lean_rows), bendComparisons=len(bend_rows),
               decoderRefusals=refusals, changedObservationControls=mutations,
               privateInputsUnavailable=unavailable, basisSha256={str(p.relative_to(ROOT)): sha(p) for p in sorted(set(files))},
               limits='Supplied fictional core values; no provider metadata or observed-file compatibility, migration composition, native publication or game execution. Public replay cannot revalidate excluded original core/compiler/binary artifacts.')
    write(RUN / 'conformance.json', out)
    print(json.dumps({k: v for k, v in out.items() if k not in ['basisSha256', 'privateInputsUnavailable']}, indent=2))


if __name__ == '__main__':
    main()
