#!/usr/bin/env python3
"""Replay the headless Qt launch record; never build Prism or start a game."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ADAPTER=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path)
    run=parser.parse_args().run.resolve()
    receipt=json.loads((run/'receipt.json').read_text())
    observed=[json.loads(line) for line in (run/'observed.stdout').read_text().splitlines()]
    inputs=[HERE/name for name in ['Launch.lean','Launch.bend','LaunchCase.lean']]
    inputs += [run/name for name in ['receipt.json','probe.py','observed.stdout','observed.stderr','compile.stdout','compile.stderr']]
    basis={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    assert sha(run/'probe.py')==receipt['producerSha256']
    assert sha(run/'observed.stdout')==receipt['stdoutSha256'] and sha(run/'observed.stderr')==receipt['stderrSha256']
    assert receipt['compileExit']==receipt['executeExit']==0 and receipt['executableUnchanged']
    assert len(observed)==receipt['cases']==10
    by_id={r['id']:r for r in observed};assert len(by_id)==10
    assert all(not r['afterFixtureCleanup']['running'] for r in observed)
    queued=by_id['abort-queued']
    assert queued['abortAccepted'] and queued['afterAction']['phase']==4
    assert queued['afterAction']['running'] and not queued['afterAction']['finished'] and queued['afterAction']['instanceRunning']
    assert queued['afterDrain']['baseState']==3 and queued['afterDrain']['reason']=='Aborted'
    assert by_id['success-three']['afterDrain']['phase']==1 and by_id['success-three']['afterDrain']['successful']
    assert by_id['ready-proceed']['afterDrain']['phase']==by_id['progress-proceed']['afterDrain']['phase']==2
    assert 'ready-request' in by_id['ready-proceed']['events'] and 'progress-request' in by_id['progress-proceed']['events']
    generated=HERE/'generated';generated.mkdir(exist_ok=True)
    path=generated/'launch.json'
    cases=[{k:r[k] for k in ['id','modes','action']} for r in observed]
    path.write_text(json.dumps({'schema':1,'cases':cases},indent=2)+'\n')
    env=dict(os.environ,LEAN_PATH=os.pathsep.join(str(ROOT/p) for p in ['.build','.build/formal']),BEND_NO_TELEMETRY='1')
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    result=subprocess.run([lean,'--run','applications/prism/LaunchCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    modeled=json.loads(result.stdout)
    fields=['id','initial','afterStart','abortAccepted','afterAction','actionEvents','afterDrain','events']
    assert modeled==[{k:r[k] for k in fields} for r in observed]
    calls=[];expected=[]
    for row in observed:
        started=[int(e.split(':')[1]) for e in row['events'] if e.startswith('start:')]
        finalized=[int(e.split(':')[1]) for e in row['events'] if e.startswith('finalize:')]
        terminal=row['afterDrain']['finished']
        bit='True{}' if terminal else 'False{}'
        ids='['+','.join(str(i)+'n' for i in started)+']'
        calls.append(f'ids(L.finalized({bit},{ids})) ++ "\\n"')
        expected.append(','.join(str(i) for i in finalized))
    abort_points=0
    for row in observed:
        if row['action']!='abort':continue
        mode=row['modes'][row['afterStart']['stepIndex']]
        policy={'hold-no-abort':'Disabled','hold-refuse':'Refused','hold-sync':'Synchronous','hold-queued':'Queued'}[mode]
        for stage,delivered in [('afterAction',False),('afterDrain',True)]:
            pending=row[stage]['running'] and row['abortAccepted']
            failed=row[stage]['baseState']==3
            calls.append(f'abort_bits(L.abort_projection(L.{policy}{{}},'+('True{}' if delivered else 'False{}')+')) ++ "\\n"')
            expected.append(''.join(str(int(x)) for x in [row['abortAccepted'],pending,failed]));abort_points+=1
    runner=generated/'LaunchCase.bend'
    runner.write_text('''import Base
import ../Launch.bend as L

def bit(b: Bool) -> String:
  match b:
    case True{}: "1"
    case False{}: "0"

def rest_ids(values: List<&2,Nat>) -> String:
  match values:
    case Nil{}: ""
    case Con{head,tail}: "," ++ Nat.show(head) ++ rest_ids(tail)

def ids(values: List<&2,Nat>) -> String:
  match values:
    case Nil{}: ""
    case Con{head,tail}: Nat.show(head) ++ rest_ids(tail)

def abort_bits(result: L.AbortResult) -> String:
  match result:
    case L.AbortResult{accepted,pending,failed}: bit(accepted) ++ bit(pending) ++ bit(failed)

def main() -> IO(Unit):
  IO.write('''+' ++ '.join(calls)+')\n')
    result=subprocess.run([bend,str(runner)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.splitlines()==expected
    invalid=json.loads(path.read_text());invalid['cases'][0]['modes']=['unknown']
    bad=generated/'launch-unknown.json';bad.write_text(json.dumps(invalid))
    result=subprocess.run([lean,'--run','applications/prism/LaunchCase.lean',str(bad)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==2 and 'Unknown controlled launch step' in result.stderr
    assert all(sha(ROOT/p)==digest for p,digest in basis.items()),'Inputs changed during replay.'
    report={'schema':1,'leanFullControlledTracesMatch':10,'bendConditionalFinalizationProjections':10,
        'bendAbortAdmissionDeliveryPoints':abort_points,'unknownStepRefused':True,
        'rejectedInterpretations':['Accepted queued abort means the base task has already finished.',
            'Controller Running/Waiting phase alone identifies the base task outcome.',
            'Source parent abort necessarily emits the parent Task::aborted outcome rather than failed.'],
        'adapterSha256':ADAPTER,'basisSha256':basis,
        'limits':['Bend finalization consumes independently observed started prefix and base completion; it does not predict every sequence event.',
            'Lean predicts selected same-thread controlled step traces, not all launch steps or real OS retirement.',
            'Instance flags and logging handlers are adapters; no native GUI, accounts, Java or complete LaunchController acceptance.']}
    (run/'conformance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='basisSha256'},indent=2))


if __name__=='__main__':main()
