#!/usr/bin/env python3
"""Compare retained backup observations; runs Lean/Bend only, never restic."""
import argparse
import copy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from locks_probe import redact

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def ns(text):
    value = datetime.fromisoformat(text)
    seconds = int(value.replace(microsecond=0).timestamp())
    fraction = re.search(r':\d\d\.(\d+)', text)
    return seconds * 1000000000 + (int(fraction[1].ljust(9, '0')) if fraction else 0)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    a = p.parse_args()
    capture = a.capture.resolve()
    assert capture.is_relative_to(ROOT / 'applications/evidence')
    receipt = json.loads((capture / 'receipt.json').read_text())
    assert receipt['commands'] == 38 and receipt['backupCases'] == 14
    assert receipt['allOwnedProcessesRetired'] and not receipt['finalLocks']
    assert sha(capture / 'probe.py') == receipt['producerSha256']
    assert sha(capture / 'helper.py') == receipt['helperSha256'] == sha(HERE / 'locks_probe.py')
    if (capture / 'disposition.json').exists():
        disposition = json.loads((capture / 'disposition.json').read_text())
        raw = capture / disposition['originalPrivatePath']
        assert sha(raw) == disposition['originalSha256']
        assert sha(capture / 'observations.json') == disposition['publicSha256']
    else:
        raw = capture / 'work/private/observations.json'
        assert sha(raw) == receipt['rawObservationSha256']
        assert sha(capture / 'observations.json') == receipt['publicObservationSha256']
    assert redact(raw.read_bytes()) == (capture / 'observations.json').read_bytes()
    models = [HERE / name for name in ['Backup.lean', 'BackupCase.lean', 'Backup.bend']]
    ledger = ROOT / 'applications/sources/restic-backup-selections.json'
    inputs = models + [ledger] + [p for p in capture.iterdir() if p.is_file() and p.name != 'conformance.json']
    basis = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    for row in json.loads(ledger.read_text())['sources']:
        assert sha(ROOT / row['cache']) == row['sha256']
    trace = json.loads((capture / 'trace.json').read_text())
    for row in trace:
        assert not row['outcome']['timedOut']
        for stream in ['stdout', 'stderr']:
            paths = row['streams'][stream]
            raw_path = capture / paths['rawPrivatePath']
            assert sha(raw_path) == paths['rawSha256']
            public = capture / (row['case'] + '.' + stream)
            assert sha(public) == paths['publicSha256']
            assert redact(raw_path.read_bytes()) == public.read_bytes()
    observations = json.loads((capture / 'observations.json').read_text())
    assert len(observations) == 14
    by_snapshot = {r['newSnapshots'][0]: r for r in observations if r['newSnapshots']}
    identities = {hashlib.sha256(b'original bytes\n').hexdigest(): 1,
                  hashlib.sha256(b'modified bytes\n').hexdigest(): 2}
    cases, native = [], []
    metadata_checks = 0
    for row in observations:
        assert row['sourceBefore'] == row['sourceAfter']
        before, after = set(row['snapshotIdsBefore']), set(row['snapshotIdsAfter'])
        assert before <= after and sorted(after - before) == row['newSnapshots']
        assert next(t for t in trace if t['case'] == row['case'])['outcome']['exitCode'] == row['exitCode']
        r = row['request']
        assert set(r['flags']) <= {'--ignore-ctime','--ignore-inode','--force','--exclude','unreadable.txt','--dry-run','--skip-if-unchanged'}
        main = row['sourceBefore']['main.txt']
        parent = by_snapshot.get(r['parent']) if '--force' not in r['flags'] else None
        old = parent['sourceBefore']['main.txt'] if parent else main
        parent_tree = next(n['tree'] for n in parent['nodes'] if n.get('message_type') == 'snapshot') if parent else None
        if row['newSnapshots']:
            tree = next(n['tree'] for n in row['nodes'] if n.get('message_type') == 'snapshot')
            same_tree = tree == parent_tree
        else:
            # In this no-publication profile the only skip case has exactly
            # the same generated file metadata/content as its captured parent.
            same_tree = parent is not None and row['sourceBefore'] == parent['sourceBefore']
        root_available = r['target'] == '.'
        stderr = []
        for line in (capture / (row['case'] + '.stderr')).read_text().splitlines():
            try:
                stderr.append(json.loads(line))
            except json.JSONDecodeError:
                # This source version emits a plain missing-target warning
                # before its structured exit error. Preserve the raw stream.
                assert not root_available and line.startswith('absent-root does not exist, skipping')
        errors = [e for e in stderr if e.get('message_type') == 'error']
        c = dict(parent=parent is not None, force='--force' in r['flags'], ignoreCtime='--ignore-ctime' in r['flags'],
            ignoreInode='--ignore-inode' in r['flags'], sizeEqual=old['bytes']==main['bytes'],
            mtimeEqual=old['mtimeNs']==main['mtimeNs'], ctimeEqual=old['ctimeNs']==main['ctimeNs'],
            inodeEqual=old['inode']==main['inode'], blobsIndexed=True, readable=True,
            priorContent=identities[hashlib.sha256(bytes.fromhex(parent['mainBytesHex'])).hexdigest()] if parent else 1,
            liveContent=identities[main['sha256']], rootAvailable=root_available, fatal=False,
            dryRun='--dry-run' in r['flags'], skipUnchanged='--skip-if-unchanged' in r['flags'],
            sameTree=same_tree, itemErrors=bool(errors))
        if row['newSnapshots']:
            content = identities[hashlib.sha256(bytes.fromhex(row['mainBytesHex'])).hexdigest()]
            expected_effect = 'published'
            node = next(n for n in row['nodes'] if n.get('message_type')=='node' and n.get('name')=='main.txt')
            assert node['size'] == main['bytes'] and node['mode'] == main['mode'] and node['inode'] == main['inode']
            assert ns(node['mtime']) == main['mtimeNs'] and ns(node['ctime']) == main['ctimeNs']
            metadata_checks += 1
            assert all(n.get('name') != 'unreadable.txt' for n in row['nodes'])
        elif c['dryRun']:
            assert row['summary']['dry_run']
            expected_effect, content = 'planned', None
        elif not root_available:
            assert row['summary'] is None
            expected_effect, content = 'refused', 0
        else:
            assert c['skipUnchanged'] and c['sameTree']
            expected_effect, content = 'unchanged', None
        if errors:
            assert len(errors) == 1 and errors[0]['during'] == 'archival'
            assert 'unreadable.txt' in errors[0]['item'] and row['exitCode'] == 3
        token = bool(row['summary'] and row['summary'].get('snapshot_id'))
        native.append(dict(case=row['case'], content=content, effect=expected_effect, code=row['exitCode'], reportedId=token))
        cases.append(c)
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)
    path = generated / 'backup.json'
    data = dict(schema=1, cases=cases)
    path.write_text(json.dumps(data, indent=2)+'\n')
    formal = generated / 'backup-formal'
    artifact = formal / 'applications/restic/Backup.olean'
    artifact.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LEAN_PATH=str(formal), BEND_NO_TELEMETRY='1')
    lean = os.environ.get('LEAN', 'lean')
    compiled = subprocess.run([lean,'-DwarningAsError=true','-o',str(artifact),str(models[0])],cwd=ROOT,env=env,capture_output=True,text=True)
    assert compiled.returncode == 0, compiled.stdout+compiled.stderr

    def lean_run(value):
        return subprocess.run([lean,'--run','applications/restic/BackupCase.lean',str(value)],cwd=ROOT,env=env,capture_output=True,text=True)
    result = lean_run(path)
    assert result.returncode == 0, result.stdout+result.stderr
    actual = json.loads(result.stdout)
    assert len(actual) == len(native)
    for value, expected in zip(actual, native):
        reused, content, phase, code, token = value.split('/')
        assert phase == expected['effect'] and int(code) == expected['code'] and bool(int(token)) == expected['reportedId']
        if expected['content'] is not None:
            assert int(content) == expected['content']
        expected['modelReuseDecision'] = bool(int(reused))
    bit = lambda v: 'True{}' if v else 'False{}'
    calls=[]
    for c in cases:
        metadata = 'B.Metadata{' + ','.join(bit(c[k]) for k in ['sizeEqual','mtimeEqual','ctimeEqual','inodeEqual']) + '}'
        capture_text = 'B.Capture{' + ','.join([*[bit(c[k]) for k in ['parent','force','ignoreCtime','ignoreInode']], metadata,
            bit(c['blobsIndexed']),bit(c['readable']),str(c['priorContent'])+'n',str(c['liveContent'])+'n']) + '}'
        publication = 'B.Publication{' + ','.join(bit(c[k]) for k in ['rootAvailable','fatal','dryRun','skipUnchanged','sameTree','itemErrors']) + '}'
        calls.append('row('+capture_text+','+publication+','+bit(c['rootAvailable'])+') ++ "\\n"')
    runner=generated/'BackupCase.bend'
    runner.write_text('''import Base
import ../Backup.bend as B

def bit(b: Bool) -> String:
  match b:
    case True{}: "1"
    case False{}: "0"

def row(+c: B.Capture, +p: B.Publication, root: Bool) -> String:
  bit(B.reuse(c)) ++ "/" ++ Nat.show(Bool.pick(Nat,root,B.captured(c),0n)) ++ "/" ++ B.effect_name(B.effect(p)) ++ "/" ++ Nat.show(B.exit_code(p)) ++ "/" ++ bit(B.has_reported_id(p))

def main() -> IO(Unit):
  IO.write('''+' ++ '.join(calls)+')\n')
    result=subprocess.run([os.environ.get('BEND','bend'),str(runner)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.splitlines()==actual
    negatives=[dict(data,schema=2),dict(data,cases=[dict(cases[0],priorContent=0)]),dict(data,cases=[dict(cases[0],liveContent=3)])]
    for n,value in enumerate(negatives):
        file=generated/f'backup-negative-{n}.json';file.write_text(json.dumps(value));result=lean_run(file)
        assert result.returncode==2 and result.stderr
    assert all(sha(ROOT/name)==digest for name,digest in basis.items())
    report=dict(schema=1,cases=len(cases),commands=len(trace),modelRows=actual,observations=native,
        leanMatches=True,bendMatches=True,metadataNodeChecks=metadata_checks,invalidResearchInputsRefused=len(negatives),
        basisSha256=basis,adapterSha256=sha(Path(__file__)),formalArtifactSha256=sha(artifact),
        limits=['Reuse decisions are source/model interpretations, not measured syscall counts; snapshot content and metadata are independently observed.',
                'One regular-file parent profile with known indexed content; missing blobs, source races, arbitrary unreadable/metadata/selection cases are not native-qualified.',
                'No saved snapshot content claim for dry-run or skip; returned dry-run ID is not a repository entry.',
                'Raw/public equivalence requires owner-local originals; the observation projection correction is preserved in disposition.json.'])
    (capture/'conformance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['basisSha256','observations','modelRows']},indent=2))


if __name__ == '__main__':
    main()
