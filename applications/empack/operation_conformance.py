#!/usr/bin/env python3
"""Pure operation-state comparisons over retained source/native facts; no workers."""
import copy,json,os,subprocess
from pathlib import Path
import operation_observations as obs
ROOT=obs.ROOT;HERE=Path(__file__).resolve().parent
B=lambda v:'True{}'if v else'False{}'
N=lambda v:str(v)+'n'
def bend(r):
    k=r['kind']
    if k=='entry':return 'O.entry_text(O.run(['+','.join(N(a)for a in r['actions'])+'],O.E{1n,'+N(r['workers'])+',False{},0n},'+N(r['driver'])+','+B(r['fault'])+'))'
    if k=='admission':return 'Nat.show(O.admission('+','.join([B(r['admissionOpen']),N(r['used']),N(r['maximum'])])+'))'
    if k=='release':return 'Bool.pick(String,'+B(r['terminal'])+',"1","0")'
    if k=='outcome':return 'Nat.show(O.outcome('+N(r['driver'])+','+B(r['fault'])+'))'
    if k=='ordinary':return 'Bool.pick(String,O.ordinary('+','.join(B(r[f])for f in['accepting','cancelled','operation','owner','attempt'])+'),"1","0")'
    if k=='receipt':return 'Bool.pick(String,O.receipt('+B(r['operation'])+','+B(r['owner'])+'),"1","0")'
    if k=='progress':return 'O.progress_text('+B(r['terminal'])+','+N(r['value'])+')'
    if k=='evidence':return 'O.evidence_text('+N(r['driver'])+','+B(r['fault'])+')'
    return 'Bool.pick(String,'+B(r['terminal'])+',"hide","show")'
def main():
    native=obs.inspect();r=[x['observed']for x in native];rows=[];expected=[]
    def add(value,result):rows.append(value);expected.append(result)
    for i,actions in[(4,[0]),(5,[0,1,2]),(6,[0,1,2,3,4])]:
        add(dict(kind='entry',workers=1,actions=actions,driver=1),obs.entry_text(r[i]['state'],r[i].get('cancelled',True)))
    for i,open in[(1,True),(3,False),(5,True),(22,False)]:
        decision=r[i]['registryFull'if open else'newStartClosed'];assert decision is True
        add(dict(kind='admission',admissionOpen=open,used=1,maximum=1),'2'if open else'1')
    for i,key,terminal in[(2,'released',True),(5,'releaseAccepted',False),(13,'released',True)]:
        add(dict(kind='release',terminal=terminal),str(int(r[i][key])))
    for i,driver in[(15,0),(17,1),(19,2)]:add(dict(kind='outcome',driver=driver,fault=True),str(obs.result_tag(r[i]['result'])))
    add(dict(kind='ordinary',attempt=False,accepting=True,cancelled=False,operation=True,owner=True),'0'if r[8]['error']=='StaleResult'else'1')
    add(dict(kind='ordinary',attempt=False,accepting=True,cancelled=True,operation=True,owner=True),'0'if r[9]['ordinaryError']=='StaleResult'else'1')
    add(dict(kind='receipt',attempt=False,accepting=True,cancelled=True,operation=True,owner=True),'1'if r[9]['receiptValue']==42 else'0')
    for i,value in[(11,2),(12,3),(13,4)]:
        state=r[i].get('state',r[i]);add(dict(kind='progress',terminal=i!=11,value=value),str(int(state['phase']=='Terminal'))+'|'+str({'SavingCachedContent':2,'PublishingChanges':3,'RevalidatingInputs':4}[state['progress']]))
    assert len(rows)==19
    # Two source-only owner/operation refusals; no forged native WorkResult was
    # manufactured. Private owner tokens are not public request fields.
    for operation,owner in[(False,True),(True,False)]:add(dict(kind='receipt',operation=operation,owner=owner),'0')
    # Proposed carriers/presentation, not current runtime or product changes.
    for driver,text in[(0,'3|0|1'),(1,'2|1|1'),(2,'3|2|1')]:add(dict(kind='evidence',driver=driver,fault=True),text)
    for terminal,text in[(True,'hide'),(False,'show')]:add(dict(kind='presentation',terminal=terminal,value=3),text)
    assert len(rows)==26
    defaults=dict(actions=[],workers=0,driver=0,fault=False,admissionOpen=True,used=0,maximum=1,terminal=False,value=0,accepting=True,cancelled=False,operation=True,owner=True,attempt=True)
    for row in rows:
        for key,value in defaults.items():row.setdefault(key,copy.deepcopy(value))
    lean,bendTool=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend');env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1');gen=HERE/'generated';gen.mkdir(exist_ok=True)
    target=ROOT/'.build/formal/applications/empack/Operations.olean';target.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.run([lean,'-DwarningAsError=true','-o',str(target),'applications/empack/Operations.lean'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    v=dict(schema=1,profile='empack-operation-runtime-slice',rows=rows);path=gen/'operations.json'
    def replay(value):
        path.write_text(json.dumps(value)+'\n');return subprocess.run([lean,'--run','applications/empack/OperationsCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    p=replay(v);assert p.returncode==0,p.stdout+p.stderr;assert json.loads(p.stdout)==expected,(p.stdout,expected)
    driver=gen/'OperationsCase.bend';driver.write_text('import Base\nimport ../Operations.bend as O\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join('('+bend(row)+' ++ "\\n")'for row in rows)+')\n')
    p=subprocess.run([bendTool,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr;assert p.stdout.splitlines()==expected,(p.stdout,expected)
    refused=[]
    for name,edit in[('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='full-engine')),('empty',lambda d:d.update(rows=[])),('workers',lambda d:d['rows'][0].update(workers=3)),('action',lambda d:d['rows'][0].update(actions=[9])),('driver',lambda d:d['rows'][0].update(driver=3)),('progress',lambda d:d['rows'][0].update(value=5)),('registry',lambda d:d['rows'][0].update(maximum=3))]:
        bad=copy.deepcopy(v);edit(bad);p=replay(bad);assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);refused.append(name)
    changed=[]
    for name,i,edit in[('premature-finish',2,lambda r:r.update(actions=[0,1,2,4])),('observer-is-not-starter',0,lambda r:r.update(actions=[1])),('closed-admission',4,lambda r:r.update(admissionOpen=True,used=0)),('retirement-fault',10,lambda r:r.update(fault=False)),('attempt-current',13,lambda r:r.update(attempt=True)),('receipt-owner',15,lambda r:r.update(owner=False)),('late-progress',17,lambda r:r.update(value=4))]:
        bad=copy.deepcopy(v);edit(bad['rows'][i]);p=replay(bad);assert p.returncode==0,p.stderr;assert json.loads(p.stdout)!=expected,name;changed.append(name)
    changed_native=[]
    for name,edit in[('lost-retained-arc',lambda d:d[2]['observed'].update(sameArc=False)),('early-capacity-release',lambda d:d[5]['observed']['state'].update(reserved=[0]*4)),('invented-clean-success',lambda d:d[6]['observed']['result'].update(kind='completed')),('unreserved-retained-output',lambda d:d[9]['observed'].update(reserved=[0]*4)),('late-progress-notification',lambda d:d[12]['observed'].update(statusChanged=True)),('secondary-fault-erased-from-raw',lambda d:d[16]['observed'].update(workerError='Cancelled')),('early-shutdown-return',lambda d:d[22]['observed'].update(firstFinished=True))]:
        bad=copy.deepcopy(native);edit(bad)
        try:obs.inspect(bad)
        except AssertionError:changed_native.append(name)
        else:raise AssertionError('Accepted changed observation '+name)
    replay(v)
    report=dict(schema=1,nativeSnapshots=24,measuredComparisons=19,sourceOnlyOwnerControls=2,proposedCarrierAndPresentationCases=5,totalComparisons=26,leanLaws=18,bendLaws=12,decoderRefusals=refused,changedPremises=changed,changedObservations=changed_native,limits=['Actual copied runtime/resource modules,not full Engine/CLI/publisher/process supervisor.','Private tokens and barrier events are admitted owner/source premises,not a public serialized authority.','Panic hooks still report to stderr;structured secondary fault loss is not total diagnostic silence.'])
    (HERE/'operation-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
