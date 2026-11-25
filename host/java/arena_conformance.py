#!/usr/bin/env python3
"""Pure retained Java25 scope comparison. Does not invoke java or javac."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def project(events):
    schedule=[('confined-owner-read','read',False,True,42),('confined-other-read','read',False,False,42),('confined-other-close','close',False,False,42),('confined-owner-read-after-refusal','read',False,True,42),('confined-owner-close','close',False,True,42),('confined-owner-read-closed','read',False,True,42),('confined-owner-close-again','close',False,True,42),('shared-other-write','write',True,False,42),('shared-owner-read-after-join','read',True,True,99),('shared-other-close','close',True,False,99),('shared-owner-read-closed','read',True,True,99)]
    if len(events)!=len(schedule):raise ValueError('Incomplete arena trace')
    rows=[];answers=[]
    for event,(name,operation,shared,owner,historical) in zip(events,schedule):
        if (event['case'],event['operation'],event['shared'],event['actorOwner'])!=(name,operation,shared,owner):raise ValueError('Unsupported arena fixture schedule')
        for k in ['beforeAlive','afterAlive','shared','actorOwner','success']:
            if type(event[k]) is not bool:raise ValueError('Invalid observed Boolean')
        if event['value'] is not None and (type(event['value']) is not int or event['value']<0):raise ValueError('Invalid observed value')
        error=event['exception']
        reasons={'':0,'java.lang.IllegalStateException':1,'java.lang.WrongThreadException':2}.get(error)
        if reasons is None:raise ValueError('Unmodeled exception')
        if event['success']!=(reasons==0):raise ValueError('Inconsistent exception/result observation')
        # Only measured pre-state and fixture inputs enter the executable models.
        # The last stored value is historical evidence,not a post-close memory read.
        rows.append(dict(alive=event['beforeAlive'],historicalValue=historical,shared=shared,owner=owner,operation=operation))
        value='none' if event['value'] is None else str(event['value'])
        answers.append(f"{int(event['success'])}/{int(event['afterAlive'])}/{value}/{reasons}")
    return rows,answers


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);args=p.parse_args()
    capture=HERE/'evidence/java25-arena-20261125T043213057721Z'
    receipt=json.loads((capture/'receipt.json').read_text())
    assert receipt['schema']==1 and len(receipt['commands'])==2
    for n,d in receipt['sourceSha256'].items():assert sha(capture/n)==d
    for stem,c in zip(['compile','execute'],receipt['commands']):
        assert c['exitCode']==0 and not c['timedOut'] and c['ownedGroupAbsent']
        for stream in ['stdout','stderr']:assert sha(capture/(stem+'.'+stream))==c[stream+'Sha256']
    observed=json.loads((capture/'execute.stdout').read_text());assert observed['schema']==1
    rows,answers=project(observed['events'])
    work=ROOT/'.build/java25/arena-replay';work.mkdir(parents=True,exist_ok=True)
    data=work/'input.json';data.write_text(json.dumps(dict(schema=1,cases=rows),indent=2)+'\n')
    env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1');lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend')
    def lean_run(path):return subprocess.run([lean,'--run',str(HERE/'ArenaAccessCase.lean'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True)
    result=lean_run(data);assert result.returncode==0,result.stdout+result.stderr
    actual_lean=json.loads(result.stdout);assert actual_lean==answers
    def boolean(v):return 'True{}' if v else 'False{}'
    calls=[]
    for r in rows:
        s='M.State{'+boolean(r['alive'])+','+str(r['historicalValue'])+'n}'
        c='M.Context{'+boolean(r['shared'])+','+boolean(r['owner'])+'}'
        op='M.'+dict(read='ReadArena',write='WriteArena',close='CloseArena')[r['operation']]+'{}'
        calls.append('render('+s+','+c+','+op+') ++ "\\n"')
    runner=work/'ArenaCase.bend';runner.write_text('''import Base
import ../../../host/java/ArenaAccess.bend as M
def flag(v: Bool) -> String:
  Bool.pick(String,v,"1","0")
def value(v: Maybe<&2,Nat>) -> String:
  match v:
    case Some{n}: Nat.show(n)
    case None{}: "none"
def live(s: M.State) -> Bool:
  match s:
    case M.State{a,_}: a
def render(+s: M.State,+c: M.Context,+op: M.Operation) -> String:
  flag(M.allowed(s,c)) ++ "/" ++ flag(live(M.after(s,c,op))) ++ "/" ++ value(M.returned_value(s,c,op)) ++ "/" ++ Nat.show(M.reasons(s,c))
def main() -> IO(Unit):
  IO.write('''+' ++ '.join(calls)+')\n')
    result=subprocess.run([bend,str(runner)],cwd=ROOT,env=env,capture_output=True,text=True);assert result.returncode==0,result.stdout+result.stderr
    actual_bend=result.stdout.splitlines();assert actual_bend==answers
    negatives=[dict(schema=2,cases=rows)]
    for key,value in [('operation','allocate'),('alive','true'),('historicalValue',-1),('historicalValue',42.5),('shared',None)]:
        row=dict(rows[0]);row[key]=value;negatives.append(dict(schema=1,cases=[row]))
    for i,n in enumerate(negatives):
        path=work/f'negative-{i}.json';path.write_text(json.dumps(n));assert lean_run(path).returncode==2
    adapter=0
    for modify in [lambda e:e.pop(),lambda e:e[0].update(exception='java.lang.OutOfMemoryError'),lambda e:e[0].update(success=False),lambda e:e[7].update(operation='allocate')]:
        events=copy.deepcopy(observed['events']);modify(events)
        try:project(events)
        except ValueError:adapter+=1
        else:raise AssertionError('Unmodeled native observation silently projected')
    for index,wrong in [(2,'1/0/none/0'),(5,'1/0/42/0'),(8,'1/1/42/0'),(9,'0/1/none/2')]:
        mutated=list(answers);mutated[index]=wrong;assert actual_lean!=mutated and actual_bend!=mutated
    basis=[HERE/n for n in ['ArenaAccess.lean','ArenaAccess.bend','ArenaAccessCase.lean','arena_conformance.py']]+[p for p in capture.iterdir() if p.is_file()]
    report=dict(schema=1,status='passed',nativeComparisons=len(rows),decoderRefusals=len(negatives),adapterRefusals=adapter,changedObservationControls=4,profile=receipt['profile'],projectedInputSha256=sha(data),basisSha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(basis)},limits=receipt['limits']+['A valid aligned long and completed thread joins are premises. Historical value is not readable storage after closure.','The simultaneous closed/wrong-thread combination is a model-only reason set;exception precedence is not observed.','No native comparisons on Windows or GNU/Linux for this new API band.'])
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','nativeComparisons','decoderRefusals','adapterRefusals','changedObservationControls']}))


if __name__=='__main__':main()
