#!/usr/bin/env python3
"""Pure task API/source-policy replay over retained native evidence; no app runs."""
import copy,itertools,json,os,subprocess
from pathlib import Path
import task_observations as obs
ROOT=obs.ROOT;HERE=Path(__file__).resolve().parent
B=lambda v:'True{}'if v else'False{}'
N=lambda v:str(v)+'n'
def bend(row):
    k=row['kind']
    if k=='trace':return 'T.trace_text(['+','.join('T.E{'+N(e['kind'])+','+N(e['task'])+'}'for e in row['events'])+'])'
    if k=='admit':return 'Bool.pick(String,T.admits('+','.join([B(row['worker']),N(row['execution']),B(row['preserved'])])+'),"1","0")'
    if k=='discovery':return 'Nat.show(T.discover('+','.join([B(row['enabled']),B(row['registered']),N(row['count'])])+'))'
    if k=='dependency':return 'Bool.pick(String,T.dependency_ready('+','.join(B(row[f])for f in['background','watching','inactive','exited'])+'),"1","0")'
    return 'Bool.pick(String,T.may_signal('+B(row['pid']>0)+','+B(row['bound'])+'),"1","0")'

def main():
    a,b,children=obs.inspect();rows=[obs.trace_input(a),obs.trace_input(b)];expected=[obs.trace_observed(a),obs.trace_observed(b)]
    # Three native provider discovery observations, under independently checked
    # definition/trust/support/settings premises. No provider callback count law.
    for enabled,registered,index in [(False,True,1),(True,True,5),(True,False,14)]:
        rows.append(dict(kind='discovery',enabled=enabled,registered=registered,count=1));expected.append(str(len(b['rows'][index]['names'])))
    native_count=len(rows)
    # Source-selected host admission table. These sixteen rows are NOT native
    # worker-host execution observations; DTO/validation checks are premises.
    for worker in [False,True]:
        for execution in range(4):
            for preserved in [False,True]:rows.append(dict(kind='admit',worker=worker,execution=execution,preserved=preserved))
    expected.extend(list('0111111100000011'))
    # Source gate projections, not direct watcher-event measurements. The native
    # joined flow separately demonstrates readiness before producer retirement.
    for background,watching,inactive,exited in itertools.product([False,True],repeat=4):
        rows.append(dict(kind='dependency',background=background,watching=watching,inactive=inactive,exited=exited))
    expected.extend(list('0101010101010111'))
    # Proposed consumer guard. PID1 is a normalized positive witness, never an
    # actual process selection or permission to send a signal.
    for pid in [-1,0,1]:
        for bound in [False,True]:rows.append(dict(kind='pid',pid=pid,bound=bound))
    expected.extend(list('000001'))
    for row in rows:
        for key,default in dict(events=[],worker=False,execution=0,preserved=False,enabled=False,registered=False,count=0,background=False,watching=False,inactive=False,exited=False,pid=0,bound=False).items():row.setdefault(key,copy.deepcopy(default))
    assert len(rows)==len(expected)==43
    generated=HERE/'generated';generated.mkdir(exist_ok=True)
    lean,bendTool=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1')
    target=ROOT/'.build/formal/applications/vscode/Tasks.olean';target.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.run([lean,'-DwarningAsError=true','-o',str(target),'applications/vscode/Tasks.lean'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    value=dict(schema=1,profile='vscode-task-api-slice',rows=rows);path=generated/'tasks.json'
    def replay(v):
        path.write_text(json.dumps(v)+'\n');return subprocess.run([lean,'--run','applications/vscode/TasksCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    p=replay(value);assert p.returncode==0,p.stdout+p.stderr
    assert json.loads(p.stdout)==expected,(json.loads(p.stdout),expected)
    driver=generated/'TasksCase.bend';driver.write_text('import Base\nimport ../Tasks.bend as T\n\ndef main() -> IO(Unit):\n  IO.write('+ ' ++ '.join('('+bend(r)+' ++ "\\n")'for r in rows)+')\n')
    p=subprocess.run([bendTool,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    assert p.stdout.splitlines()==expected,(p.stdout,expected)
    refused=[]
    for name,edit in[
      ('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='full-task-engine')),('empty',lambda d:d.update(rows=[])),
      ('event',lambda d:d['rows'][0]['events'][0].update(kind=7)),('task-id',lambda d:d['rows'][0]['events'][0].update(task=6)),
      ('missing-task',lambda d:d['rows'][0]['events'][0].update(kind=1,task=0)),('execution',lambda d:d['rows'][5].update(execution=4)),
      ('provider-bound',lambda d:d['rows'][2].update(count=2)),('pid-witness',lambda d:d['rows'][-1].update(pid=42))]:
        bad=copy.deepcopy(value);edit(bad);p=replay(bad);assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);refused.append(name)
    changed=[]
    for name,index,edit in[
      ('early-handle-removal',1,lambda r:r['events'][17].update(kind=6)),
      ('missing-task-removal',1,lambda r:r['events'][18].update(kind=0)),
      ('disabled-provider',3,lambda r:r.update(enabled=False)),
      ('worker-vs-node',6,lambda r:r.update(worker=True)),
      ('background-not-ready',35,lambda r:r.update(inactive=False)),
      ('unbound-positive-pid',42,lambda r:r.update(bound=False))]:
        bad=copy.deepcopy(value);edit(bad['rows'][index]);p=replay(bad);assert p.returncode==0,p.stderr
        assert json.loads(p.stdout)!=expected,name;changed.append(name)
    changed_observations=[]
    for name,edit in[
      ('virtual-pid',lambda aa,bb,cc:aa['rows'][7].update(pid=123)),
      ('provider-disposal',lambda aa,bb,cc:bb['rows'][14].update(names=['rules-provider-hold'])),
      ('invented-stop-status',lambda aa,bb,cc:bb['rows'][30].update(exitCode=11)),
      ('premature-provider-cleanup',lambda aa,bb,cc:bb['rows'][19].update(workerAlive=False)),
      ('literal-argument',lambda aa,bb,cc:cc[0]['argv'].pop()),
      ('child-exit-code',lambda aa,bb,cc:cc[-1].update(code=0))]:
        aa,bb,cc=copy.deepcopy((a,b,children));edit(aa,bb,cc)
        try:obs.inspect(aa,bb,cc)
        except AssertionError:changed_observations.append(name)
        else:raise AssertionError('Accepted changed observation: '+name)
    replay(value)
    report=dict(schema=1,nativeTraceSnapshots=58,nativeTraceComparisons=2,nativeDiscoveryComparisons=3,sourceAdmissionComparisons=16,
      sourceDependencyComparisons=16,proposedSignalGuardComparisons=6,totalComparisons=43,decoderRefusals=refused,
      changedPremises=changed,changedObservations=changed_observations,leanLaws=15,bendLaws=11,
      limits=['Source/proposed rows are not native executions.','Active task list is not process liveness.','Background matcher state is source-inferred,not a direct API callback.'])
    (HERE/'task-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
