"""Replay retained migration observations through models; no empack or network execution."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import observations as O

ROOT, RUN = O.ROOT, O.RUN
HERE = Path(__file__).resolve().parent
read = O.read
sha = O.sha
write = lambda p, value: p.write_text(json.dumps(value, indent=2) + '\n')
FAILED = ['empack-migration-flow-20261126T054252648792Z', 'empack-migration-flow-20261126T054326094647Z']


def evidence(public_only=False):
    files = [HERE / 'probe.py', HERE / 'observations.py', HERE / 'conformance.py',
             O.helper, ROOT / 'applications/empack/update-flow/probe.py']
    receipt, setup = read(RUN / 'receipt.json'), read(RUN / 'setup.json')
    assert receipt['complete'] and receipt['commands'] == 12 and receipt['allRecordedGroupsAbsent']
    assert receipt['binarySha256'] == setup['binarySha256'] == '99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
    assert sha(RUN / 'setup.json') == receipt['setupSha256']
    assert sha(RUN / 'metadata.json') == receipt['metadataSha256']
    assert sha(RUN / 'probe.py') == receipt['producerSha256'] == sha(HERE / 'probe.py')
    assert sha(ROOT / setup['snapshotHelper']) == setup['snapshotHelperSha256']
    for name in FAILED:
        path = ROOT / 'applications/evidence' / name
        disposition = read(path / 'disposition.json'); files.append(path / 'disposition.json')
        for f, digest in disposition['originalFiles'].items():
            assert sha(path / f) == digest; files.append(path / f)
        assert all(r['groupAbsent'] and not r['timedOut'] for r in read(path / 'commands.json'))
    files.extend(p for p in RUN.iterdir() if p.is_file() and p.name != 'conformance.json')
    unavailable = []
    def inspect(path, test):
        if public_only or not path.exists(): unavailable.append(str(path))
        else: test(path)
    inspect(Path(setup['binary']), lambda p: check(sha(p), setup['binarySha256']))
    work = Path(setup['work'])
    for name, digest in setup['privateMetadataSha256'].items():
        inspect(work / 'independent-api' / name, lambda p, h=digest: check(sha(p), h))
    spec = importlib.util.spec_from_file_location('snapshot_only', ROOT / setup['snapshotHelper'])
    snapshot = importlib.util.module_from_spec(spec); spec.loader.exec_module(snapshot)
    latest = {r['project']: r['after'] for r in read(RUN / 'commands.json')}
    for project, images in latest.items():
        for scope, image in images.items():
            path = work / ('projects' if scope == 'project' else scope) / project
            inspect(path, lambda p, expected=image: check(snapshot.image(p), expected))
    ledger = ROOT / 'applications/sources/empack-migration-flow-selections.json'; files.append(ledger)
    for row in read(ledger)['sources']:
        def source(path, row=row):
            raw = path.read_bytes(); check(hashlib.sha256(raw).hexdigest(), row['sha256'])
            check(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest(), row['gitBlob'])
            for region in row['ranges']:
                selected = b''.join(raw.splitlines(keepends=True)[region['firstLine']-1:region['lastLine']])
                check(hashlib.sha256(selected).hexdigest(), region['sha256'])
        inspect(ROOT / row['cache'], source)
    gate = read(RUN / 'proof-gate.json'); assert gate['observedExitCode'] == 0
    assert sha(RUN / 'proof-gate.log') == gate['logSha256']
    for name, digest in gate['sourceSha256'].items(): check(sha(ROOT / name), digest)
    files += [HERE / 'MigrationFlow.lean', HERE / 'MigrationFlowCase.lean', HERE / 'MigrationFlow.bend']
    return sorted(set(files)), unavailable


def check(actual, expected):
    assert actual == expected, 'Migration evidence or modeled observation differs.'


def main():
    assert sys.argv[1:] in [[], ['--public-only']]
    files, unavailable = evidence(bool(sys.argv[1:]))
    packet, expected = O.packets()
    formal = ROOT / '.build/empack-migration-flow-replay'; formal.mkdir(parents=True, exist_ok=True)
    lean = os.environ.get('LEAN', 'lean'); bend = os.environ.get('BEND', 'bend')
    env = {**os.environ, 'LEAN_PATH': str(formal), 'BEND_NO_TELEMETRY': '1'}
    target = formal / 'applications/empack/migration-flow/MigrationFlow.olean'; target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([lean, '-DwarningAsError=true', '-o', str(target), 'applications/empack/migration-flow/MigrationFlow.lean'], cwd=ROOT, env=env, check=True, timeout=60)
    path = formal / 'input.json'
    def replay(data):
        write(path, data)
        return subprocess.run([lean, '--run', 'applications/empack/migration-flow/MigrationFlowCase.lean', str(path)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    result = replay(packet); assert result.returncode == 0, result.stdout + result.stderr
    lean_values = json.loads(result.stdout); check(lean_values, expected)
    ops = {'sync':0, 'prefix-preview':1, 'preview':2, 'apply':3, 'unpin':4, 'check':5}
    state = {'compatible':'M.State{1n,0n,1n,0n}', 'incompatible':'M.State{2n,0n,1n,0n}'}
    calls = []
    for row in packet['steps']:
        before = state[row['project']]; op = str(ops[row['action']]) + 'n'
        calls.append('M.render(' + ','.join([json.dumps(row['id']), json.dumps(row['project']), before, op]) + ')')
        state[row['project']] = 'M.step(' + before + ',' + op + ')'
    driver = formal / 'Replay.bend'
    driver.write_text('import Base\nimport ../../applications/empack/migration-flow/MigrationFlow.bend as M\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ "\\n" ++ '.join(calls) + ' ++ "\\n")\n')
    result = subprocess.run([bend, str(driver)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    bend_values = [json.loads(s) for s in result.stdout.splitlines()]; check(bend_values, expected)
    refused = []
    for label, change, message in [
        ('schema', lambda v:v.update(schema=2), 'Unsupported migration research profile'),
        ('profile', lambda v:v.update(profile='all-migrations'), 'Unsupported migration research profile'),
        ('step-count', lambda v:v['steps'].pop(), 'Unsupported migration research step count'),
        ('action', lambda v:v['steps'][0].update(action='latest'), 'Unsupported migration research action'),
        ('project-order', lambda v:v['steps'][0].update(project='incompatible'), 'Unsupported migration research project order'),
        ('operation-order', lambda v:v['steps'][1].update(action='preview'), 'Unsupported migration research operation order'),
    ]:
        bad = copy.deepcopy(packet); change(bad); result = replay(bad)
        assert result.returncode == 2 and not result.stdout and message in result.stderr, (label, result.stdout, result.stderr)
        refused.append(label)
    mutations = []
    for label, i, field, value in [
        ('held-pin-lost',3,'pin',0), ('wrong-target',3,'game',1), ('incompatible-admitted',7,'exit',0),
        ('unpin-is-selection-change',8,'selected',1), ('payload-materialized',10,'payload',1),
        ('preview-writes-project',2,'projectChanges',['empack.lock']),
        ('refusal-writes-state',7,'stateChanged',True), ('prefix-bug-hidden',1,'exit',0),
        ('reference-mistaken-for-verified',4,'facet',[1,1,0]),
    ]:
        bad = copy.deepcopy(expected)
        target = bad[i]['after'] if field in ['pin','game','selected','payload'] else bad[i]
        target[field] = value
        for actual in [lean_values, bend_values]:
            try: check(actual, bad)
            except AssertionError: pass
            else: raise AssertionError('Changed observation accepted: ' + label)
        mutations.append(label)
    raw_controls = []
    for label in ['command-mode', 'document-bytes', 'state-continuity', 'native-exit']:
        commands = copy.deepcopy(read(RUN / 'commands.json'))
        if label == 'command-mode': commands[1]['argv'].remove('--dry-run')
        elif label == 'document-bytes': commands[0]['after']['project']['empack.lock']['bytesHex'] = '00'
        elif label == 'state-continuity': commands[1]['before']['state'] = {}
        else: commands[6]['exitCode'] = 0
        try: O.packets(commands)
        except AssertionError: raw_controls.append(label)
        else: raise AssertionError('Changed native capture accepted: ' + label)
    write(path, packet)
    receipt = dict(schema=1, nativeSteps=12, workflowBranches=2, leanComparisons=len(lean_values), bendComparisons=len(bend_values),
                   decoderRefusals=refused, changedObservationControls=mutations, rawObserverControls=raw_controls,
                   privateInputsUnavailable=unavailable, basisSha256={str(p.relative_to(ROOT)):sha(p) for p in files},
                   limits='Frozen two-project released-CLI trace. Models start with fixture requests/actions, not observed after-state. Eligibility is a sampled metadata premise; no catalog, YAML, cryptographic, native publisher or game refinement proof. Proposed global-flag equivalence is not a production patch. Public replay cannot revalidate excluded binary, source caches or latest private fixtures.')
    write(RUN / 'conformance.json', receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['basisSha256','privateInputsUnavailable']}, indent=2))


if __name__ == '__main__': main()
