#!/usr/bin/env python3
"""Owner-local replay of lock evidence and redactions;never execute restic."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def redact(raw,mapping):
    text=raw.decode('utf-8')
    for value,label in [(mapping['hostname'],'[fixture-host]'),(mapping['username'],'[fixture-user]')]:text=text.replace(value,label)
    text=re.sub(r'\(UID \d+, GID \d+\)','(UID [redacted], GID [redacted])',text)
    return re.sub(r'"(uid|gid)"\s*:\s*\d+',r'"\1": null',text).encode()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path);parser.add_argument('wait',type=Path);args=parser.parse_args();run=args.run.resolve();wait=args.wait.resolve()
    receipt=json.loads((run/'receipt.json').read_text());follow=json.loads((wait/'receipt.json').read_text());trace=json.loads((run/'trace.json').read_text());wait_trace=json.loads((wait/'trace.json').read_text())
    assert receipt['commands']==len(trace)==21 and follow['commands']==len(wait_trace)==3
    assert receipt['allOwnedProcessesRetired']and follow['allOwnedProcessesRetired']and receipt['finalLocks']==follow['finalLocks']==[]
    assert sha(run/'probe.py')==receipt['producerSha256']==sha(HERE/'locks_probe.py')
    assert sha(wait/'probe.py')==follow['producerSha256']==sha(HERE/'lock_wait_probe.py')
    assert sha(wait/'helper.py')==follow['helperSha256']==sha(run/'probe.py')
    assert sha(run/'receipt.json')==follow['sourceReceiptSha256'] and (ROOT/follow['sourceCapture']).resolve()==run
    assert follow['copyBytesVerified']and follow['copyUsesDistinctInode']and follow['sourceRepoUnchanged']
    original=run/'work/repository';image={p.relative_to(original).as_posix():sha(p)for p in original.rglob('*')if p.is_file()};assert image==follow['sourceRepositoryImage']
    ledger=ROOT/'applications/sources/restic-locks-selections.json';sources=json.loads(ledger.read_text());assert sources['revision']=='9c88ff768f10c192dc6a87619a65a16374080e33'
    for source in sources['sources']:assert sha(ROOT/source['cache'])==source['sha256']
    files=[HERE/p for p in ['Locks.lean','LocksCase.lean','Locks.bend','locks_probe.py','lock_wait_probe.py','locks_conformance.py']]+[ledger]
    for directory,rows in [(run,trace),(wait,wait_trace)]:
        mapping_path=directory/'work/private/redaction-inputs.json';mapping=json.loads(mapping_path.read_text());files.append(mapping_path)
        for row in rows:
            if directory==run:
                assert not row['control']['timedOut'];streams=row['observed']['streams']
            else:streams=row['streams']
            for stream,record in streams.items():
                raw=directory/record['rawPrivatePath'];public=directory/(row['case']+'.'+stream);files += [raw,public]
                assert sha(raw)==record['rawSha256']and sha(public)==record['publicSha256']
                assert redact(raw.read_bytes(),mapping)==public.read_bytes()
                assert record['redacted']==(raw.read_bytes()!=public.read_bytes())
        files += [directory/name for name in ['receipt.json','trace.json','probe.py']]
    files += [run/'observations.json',run/'qualification.json',run/'owned-processes.json',wait/'helper.py']
    # Private file paths/digests are evidence references,not a public copy of
    # their secret/identity-bearing contents. Fresh public checkout replay is
    # deliberately insufficient for the owner-local redaction verification.
    basis={str(p.relative_to(ROOT)):sha(p)for p in files}
    rows={r['case']:r for r in trace};wait_rows={r['case']:r for r in wait_trace}
    views={}
    for observation in json.loads((run/'observations.json').read_text()):
        for lock in observation['locks']:
            assert lock['sameHost']
            views[lock['id']]=dict(token=lock['id'],owner=lock['pid'],exclusive=lock['exclusive'],readable=True,emptyUpload=False,old=False,sameHost=True,reachable=True)
    # Public diagnostic cat output is a redacted native document. Its source
    # role is explicitly no-lock/read-only;it is not an admitted normal reader.
    for row in trace:
        if row['role']=='diagnostic-no-lock-observer':
            assert '--no-lock'in row['argv'] and row['outcome']['exitCode']==0
            lock=json.loads((run/(row['case']+'.stdout')).read_text());identity=row['argv'][-1]
            assert lock['pid']==views[identity]['owner']and lock['exclusive']==views[identity]['exclusive']
    def lock_set(names,dead=False):return [dict(views[name],reachable=False if dead else views[name]['reachable'])for name in names]
    projected=[];expected=[];names=[];labels=[]
    def add(label,mode,locks,outcome,exclusive=False,owner=0,cleanup=False):
        projected.append(dict(mode=mode,exclusive=exclusive,owner=owner,cleanup=cleanup,locks=locks));expected.append(outcome);names.append(label)
    for label in ['seed-backup','held-a','held-b','held-c','append-blocked-by-exclusive','check-blocked','prune-blocked','retry-expired','dead-lock-check-refused','check-after-unlock','exclusive-paused']:
        row=rows[label];exclusive=label in ['check-blocked','prune-blocked','retry-expired','dead-lock-check-refused','check-after-unlock','exclusive-paused']
        before=row['observed']['before']['locks'];allowed=row['outcome']['exitCode']!=11
        if label in ['held-b','held-c']:labels.append(dict(case=label,evidence='Published compatible candidate observed;final successful admission not separately established by the interrupted/killed outcome.'))
        add(label,0,lock_set(before,dead=label=='dead-lock-check-refused'),dict(allowed=allowed),exclusive)
        if not allowed:assert row['outcome']['exitCode']==11 and row['observed']['before']['locks']==row['observed']['after']['locks']
    # The primary release-before-completion control did not establish a wait:
    # its process lifetime is shorter than the configured2s retry sleep.
    assert rows['retry-after-release']['outcome']['exitCode']==0
    add('primary-retry/post-release',0,[],dict(allowed=True),True)
    assert follow['markerObservedWhileBothLive']and wait_rows['observed-wait']['exitCode']==0
    assert wait_rows['holder']['exitCode']==0 and wait_rows['observed-wait']['beforeLocks']==[follow['heldLock']['id']]
    marker=follow['marker'].encode();assert marker in(wait/'work/private/observed-wait.stdout').read_bytes()+(wait/'work/private/observed-wait.stderr').read_bytes()
    assert follow['markerSeconds']<wait_rows['holder']['seconds'] and follow['markerSeconds']<wait_rows['observed-wait']['seconds']
    follow_lock=dict(token=follow['heldLock']['id'],owner=follow['heldLock']['pid'],exclusive=follow['heldLock']['exclusive'],readable=True,emptyUpload=False,old=False,sameHost=True,reachable=True)
    add('observed-retry/initial-conflict',0,[follow_lock],dict(allowed=False),True)
    add('observed-retry/after-release',0,[],dict(allowed=True),True)
    for label,dead in [('unlock-live',False),('unlock-dead',True)]:
        row=rows[label];assert row['outcome']['exitCode']==0
        add(label,1,lock_set(row['observed']['before']['locks'],dead),dict(locks=row['observed']['after']['locks']))
    for label,cleanup in [('held-a',True),('held-b',True),('held-c',False)]:
        row=rows[label];owner=row['pid'];published=next(v for v in views.values()if v['owner']==owner)
        before=lock_set([published['token']])
        add(label+'/retirement',2,before,dict(locks=[]if cleanup else[published['token']]),owner=owner,cleanup=cleanup)
        if cleanup:assert published['token']not in row['observed']['after']['locks']
        else:assert published['token']in row['observed']['after']['locks']and row['outcome']['exitCode']==-9
    assert receipt['interruptedExitCode']==130 and receipt['interruptedNeededEOF']
    assert rows['held-b']['control']['neededEOFToRetire']and rows['held-b']['observed']['seconds']>=3
    assert rows['held-b']['observed']['before']['snapshots']==rows['held-b']['observed']['after']['snapshots']
    assert rows['held-c']['observed']['before']['snapshots']==rows['held-c']['observed']['after']['snapshots']
    assert receipt['finalSnapshots']==sorted(receipt['seedSnapshots']+[receipt['completedASnapshot']])
    assert (run/'work/private/dump-completed-a.stdout').read_bytes()==b'Completed held A input.\n'
    assert rows['exclusive-paused']['control']['publishedStoppedObserved']and rows['exclusive-paused']['control']['admissionAtStop']=='not established'
    generated=HERE/'generated';generated.mkdir(exist_ok=True);path=generated/'locks.json'
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    env=dict(os.environ,LEAN_PATH=os.pathsep.join(str(ROOT/p)for p in ['.build/formal','.build']),BEND_NO_TELEMETRY='1')
    def replay(value):
        path.write_text(json.dumps(value)+'\n');return subprocess.run([lean,'--run','applications/restic/LocksCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True)
    result=replay(dict(schema=1,cases=projected));assert result.returncode==0,result.stdout+result.stderr;assert json.loads(result.stdout)==expected,[(n,a,e)for n,a,e in zip(names,json.loads(result.stdout),expected,strict=True)if a!=e]
    # Only normal compatibility and ordinary cleanup are Bend's projection.
    calls=[];bend_expected=[];bit=lambda b:'True{}'if b else'False{}'
    for row,outcome in zip(projected,expected,strict=True):
        if row['mode']==0:
            terms=['L.compatible('+','.join(map(bit,[row['exclusive'],v['exclusive'],v['readable'],v['emptyUpload']]))+')'for v in row['locks']]
            expression='True{}'
            for term in terms:expression='Bool.and('+expression+','+term+')'
            calls.append('Bool.show('+expression+') ++ "\\n"');bend_expected.append(str(outcome['allowed']))
        elif row['mode']==1:
            for view in row['locks']:
                expression='L.remove_stale('+','.join(map(bit,[view[k]for k in ['readable','emptyUpload','old','sameHost','reachable']]))+')'
                calls.append('Bool.show('+expression+') ++ "\\n"');bend_expected.append(str(view['token']not in outcome['locks']))
    calls+=['Bool.show(L.candidate_stale(False{},True{},L.Unknown{})) ++ "\\n"','Bool.show(L.stale(False{},True{},False{})) ++ "\\n"'];bend_expected+=['False','True']
    runner=generated/'LocksCase.bend';runner.write_text('import Base\nimport ../Locks.bend as L\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
    result=subprocess.run([bend,str(runner)],cwd=ROOT,env=env,capture_output=True,text=True);assert result.returncode==0,result.stdout+result.stderr;assert result.stdout.splitlines()==bend_expected
    invalids=[('schema',dict(schema=2,cases=[]),'Unsupported lock observation schema'),('mode',dict(schema=1,cases=[dict(projected[0],mode=3)]),'Unknown lock observation operation')]
    duplicate=copy.deepcopy(next(r for r in projected if r['locks']));duplicate['locks']*=2
    invalids.append(('duplicate',dict(schema=1,cases=[duplicate]),'Duplicate lock observation identity'))
    for label,value,message in invalids:
        result=replay(value);assert result.returncode==2 and message in result.stderr,label
    path.write_text(json.dumps(dict(schema=1,cases=projected),indent=2)+'\n')
    assert all(sha(ROOT/p)==h for p,h in basis.items()),'Evidence changed while consumed.'
    report=dict(schema=1,basisSha256=basis,primaryNativeCommands=21,followupNativeCommands=3,leanObservationCases=len(projected),bendDecisions=len(bend_expected),invalidResearchInputsRefused=[x[0]for x in invalids],
        candidateEvidenceLimits=labels,primaryRetryWaitWasNotEstablished=True,followupExplicitWaitEstablished=True,
        redactionsVerifiedAgainstPrivateOriginals=True,interruptionEOFWasSuppliedAfterThreeSecondWait=True,
        rejectedInterpretations=['Every repository writer needs an exclusive lock.','Every logical reader uses a shared lock.',
            'A visible backend temporary file is a published lock.','A published candidate proves admission completed.',
            'A dead owner makes its lock automatically absent.','SIGINT necessarily retires stdin backup before EOF.',
            'A live process with retry options proves it reached the retry-wait stage.','Failed PID reachability proves absence or creator identity.'],
        limits=['Normal local same-host short-lived locks;no age expiry,heartbeat failure,remote consistency,permission-denied or PID-reuse experiment.',
            'Source PID probe conflates signal errors;unknown-versus-absent refinement is proposed/source-modeled,not native patched behavior.',
            'No-lock cat calls only inspect controlled immutable lock records and are excluded from ordinary reader admission evidence.',
            'B/C had empty open stdin and no snapshot publication;this is not partial-source-read or exit3 incomplete-backup qualification.',
            'Public streams are redacted. Full owner-local replay requires ignored private originals/mapping and selected source cache;fresh public checkout cannot establish raw redaction equivalence.',
            'Current predicate projections assume complete relevant lock observations;not a distributed mutual-exclusion or arbitrary process-containment proof.'])
    (run/'conformance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='basisSha256'},indent=2))


if __name__=='__main__':main()
