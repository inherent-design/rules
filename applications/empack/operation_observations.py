#!/usr/bin/env python3
"""Read-only source/native operation observer; no compiler, Engine, or user store."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'applications/evidence/empack-operations-20261125T090212235915Z'
EXCLUDED=ROOT/'applications/evidence/empack-operations-20261125T090143715136Z'
REV='0b4462e3032b4f09230b15329722eabefb7f574c'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def inspect(native=None):
    meta=read(RUN/'inputs.json');exit=read(RUN/'exit.json');closed=read(RUN/'closure.json');work=Path(meta['work'])
    original=[json.loads(s)for s in(RUN/'native.stdout').read_text().splitlines()]
    assert original==read(RUN/'observed.json')['rows']
    rows=original if native is None else native
    assert len(rows)==24 and all(r['schema']==1 for r in rows)
    assert exit['exitCode']==0 and read(RUN/'compile.json')['exitCode']==0
    assert sha(RUN/'native.stdout')==exit['stdoutSha256'] and sha(RUN/'native.stderr')==exit['stderrSha256']
    assert closed['originalGroupAbsent'] and not closed['workspaceProcessHits']
    assert closed['retainedFileHex']=='64617461' and (work/'held-file').read_bytes()==b'data'
    assert sha(work/'operation-driver')==exit['binarySha256']==closed['binarySha256']
    assert sha(RUN/'probe.py')==meta['producerSha256']==sha(ROOT/'applications/empack/operation_probe.py')
    assert sha(RUN/'driver.rs')==meta['driverSha256']==sha(ROOT/'applications/empack/operation_oracle.rs')
    assert sha(work/'main.rs')==meta['generatedSha256'] and sha(work/'cancellation.rs')==meta['cancellationSha256']
    assert sha(Path(meta['tool']['path']))==meta['tool']['sha256'] and 'rustc 1.99.1' in meta['tool']['version']
    for p in meta['dependencies']:assert sha(Path(p['path']))==p['sha256']
    repo=ROOT.parent/'empack';pinned={}
    for p in meta['sources']:
        raw=subprocess.check_output(['git','-C',str(repo),'show',REV+':'+p['path']]);assert hashlib.sha256(raw).hexdigest()==p['sha256'];pinned[p['path']]=raw
    for n in ['runtime','resources']:assert (work/(n+'.rs')).read_bytes()==pinned['crates/empack-lib/src/engine/'+n+'.rs']
    cancellation=pinned['crates/empack-lib/src/application/process_runtime.rs'].decode()
    for p in meta['cancellationSelections']:
        assert p['text']in cancellation and hashlib.sha256(p['text'].encode()).hexdigest()==p['sha256']
    assert read(EXCLUDED/'compile.json')['exitCode']==1 and read(EXCLUDED/'unrun.json')['nativeRuns']==0
    assert 'E0514' in(EXCLUDED/'compile.stderr').read_text() and not(EXCLUDED/'exit.json').exists()
    expected=[('retention',p)for p in['completed','late-observer','release','closed']]+[('drop-custody',p)for p in['observer-drop','caller-drop-retiring','retired']]+[('acceptance',p)for p in['retained','superseded','cancelled-receipt','terminal']]+[('progress',p)for p in['coalesced','late-terminal','after-release']]+[('failure-priority',p)for p in['driver-ok','driver-ok-terminal','driver-cancelled','driver-cancelled-terminal','driver-panicked','driver-panicked-terminal']]+[('retire','child-only'),('retire','terminal'),('shutdown','pending'),('shutdown','retired')]
    assert [(r['case'],r['point'])for r in rows]==expected
    r=[r['observed']for r in rows]
    assert r[0]['terminal']=={'kind':'completed','value':42}
    assert r[1]['registryFull'] and r[1]['sameArc'] and r[1]['result']==r[0]['terminal']
    assert r[2]['released'] and not r[2]['registryPresent'] and r[2]['sameArc'] and r[2]['observerResult']==r[0]['terminal']
    assert r[3]['newStartClosed'] and r[3]['reserved']==[0]*4
    assert not r[4]['cancelled'] and r[4]['fileBytes']==list(b'data') and r[4]['state']['reserved']==[1,8,4,1]
    assert r[5]['cancelled'] and r[5]['state']['phase']=='Retiring' and r[5]['state']['terminal']is None
    assert r[5]['state']['reserved']==[1,8,4,1] and not r[5]['releaseAccepted'] and r[5]['registryFull'] and r[5]['capacityBusy']
    assert r[6]['fileBytes']==list(b'data') and r[6]['result']=={'kind':'failed','error':'Cancelled'} and r[6]['state']['reserved']==[0]*4
    assert r[7]['reserved']==[0,8,4,1] and r[8]['error']=='StaleResult' and r[8]['reserved']==[0]*4
    assert r[9]=={'ordinaryError':'StaleResult','receiptValue':42,'reserved':[0,8,4,1]}
    assert r[10]['reserved']==[0]*4 and r[10]['result']=={'kind':'completed','value':42}
    assert r[11]['progress']=='SavingCachedContent' and r[11]['phase']=='Running'
    assert r[12]['state']['progress']=='PublishingChanges' and r[12]['state']['phase']=='Terminal' and not r[12]['statusChanged'] and r[12]['sameArc']
    assert r[13]['state']['progress']=='RevalidatingInputs' and r[13]['state']['terminal']==r[12]['state']['terminal']=={'kind':'completed','value':5}
    assert r[13]['released'] and not r[13]['registryPresent']
    for i,e in[(15,'Panicked'),(17,'Cancelled'),(19,'Panicked')]:
        assert r[i-1]['workerError']=='Panicked' and r[i]['workerRan'] and r[i]['reserved']==[0]*4 and r[i]['result']=={'kind':'failed','error':e}
    stderr=(RUN/'native.stderr').read_text();assert stderr.count('rules-owned worker fault')==3 and stderr.count('rules-owned driver fault')==1
    assert not r[20]['parentCancelled'] and r[21]['result']=={'kind':'completed','value':6} and r[21]['reserved']==[0]*4
    assert not r[22]['firstFinished'] and not r[22]['secondFinished'] and r[22]['newStartClosed'] and r[22]['state']['reserved']==[1,8,4,1]
    assert r[23]['result']=={'kind':'completed','value':10} and r[23]['reserved']==[0]*4
    return rows

def result_tag(result):return 0 if result is None else 1 if result['kind']=='completed' else {'Cancelled':2,'Panicked':3}[result['error']]
def entry_text(s,cancelled):return '|'.join([str({'Preparing':0,'Running':1,'Retiring':2,'Terminal':3}[s['phase']]),str(s['reserved'][0]),str(int(cancelled)),str(result_tag(s['terminal']))])
