#!/usr/bin/env python3
"""Pure models against retained authored Java17/21/25 initialization traces; no JVM launch."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CONTRACT='java17-21-25-authored-serial-class-init'
CAPTURES=['class-init-17-20261125T110836234813Z','class-init-21-20261125T110911696411Z','class-init-25-20261125T110912140164Z']
CALLER='host/minecraft/evidence/polytone-class-target-invoke-20261125T111850323262Z'
TARGETS=['Good','Bad','HardBad','ArrayElement','Missing']
OPERATIONS=['literal','default','explicit']
ERRORS=['none','java.lang.ClassNotFoundException','java.lang.ExceptionInInitializerError','java.lang.NoClassDefFoundError','java.lang.AssertionError']
PLAN=[
    ('good-literal',0,0,False,False,0),('good-no-init',0,0,False,False,2),
    ('good-default',0,0,True,False,1),('good-repeat',0,0,True,False,2),
    ('bad-no-init',1,0,False,False,2),('bad-default',1,0,True,False,1),
    ('bad-retry',1,0,True,False,2),('bad-metadata-after-failure',1,0,False,False,2),
    ('loader-a-no-init',0,1,False,False,2),('loader-a-init',0,1,True,False,2),
    ('loader-b-init',0,2,True,False,2),('loader-a-missing',4,1,False,False,2),
    ('array-literal',3,0,False,True,0),('array-default',3,0,True,True,1),
    ('array-element-init',3,0,True,False,2),('error-default',2,0,True,False,1),
    ('error-retry',2,0,True,False,2),('error-metadata-after-failure',2,0,False,False,2),
    ('system-missing',4,0,True,False,1)]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def project(rows):
    assert len(rows)==len(PLAN)
    actions=[];answers=[];previous=[0]*6
    for index,(row,plan) in enumerate(zip(rows,PLAN)):
        name,target,loader,request,array,operation=plan
        assert type(row['schema']) is int and row['schema']==1 and type(row['index']) is int and row['index']==index and row['case']==name
        assert row['target']==TARGETS[target] and row['operation']==OPERATIONS[operation]
        assert type(row['requestedLoader']) is int and row['requestedLoader']==loader
        assert type(row['initialize']) is bool and row['initialize']==request
        assert type(row['array']) is bool and row['array']==array
        for field in ['before','after']:
            assert type(row[field]) is list and len(row[field])==6
            assert all(type(v) is int and 0<=v<=64 for v in row[field])
        assert row['before']==previous;previous=row['after']
        assert all(type(row[k]) is bool for k in ['returnedClass','caughtByClassNotFound','caughtByException'])
        assert type(row['actualLoader']) is int and -1<=row['actualLoader']<=2
        assert type(row['classIdentity']) is int and 0<=row['classIdentity']<=32
        assert row['error'] in ERRORS and type(row['cause']) is str
        if row['returnedClass']:
            expected='study.host.ClassInitProbe$'+TARGETS[target]
            if array:expected='[L'+expected+';'
            assert row['className']==expected and row['actualLoader']>=0 and row['classIdentity']>0
        else:assert row['className']=='' and row['actualLoader']==-1 and row['classIdentity']==0
        actions.append(dict(target=target,loader=loader,request=request,array=array,operation=operation))
        answers.append([ERRORS.index(row['error']),int(row['returnedClass']),row['classIdentity'],row['actualLoader']+1,
            int(row['caughtByClassNotFound']),int(row['caughtByException'])]+row['after'])
    return actions,answers


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);args=p.parse_args()
    work=ROOT/'.build/java-class-init/replay';work.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=os.environ.get('LEAN_PATH',str(ROOT/'.build/formal')),BEND_NO_TELEMETRY='1')
    def envelope(rows):return dict(schema=1,contract=CONTRACT,cases=rows)
    def lean_run(request,name):
        path=work/(name+'.json');path.write_text(json.dumps(request)+'\n')
        return subprocess.run([os.environ.get('LEAN','lean'),'--run',str(HERE/'ClassInitCase.lean'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    def bend_run(rows,name):
        values='Nil{}'
        b=lambda v:'True{}' if v else 'False{}'
        for row in reversed(rows):values='Con{M.CIAction{'+str(row['target'])+'n,'+str(row['loader'])+'n,'+b(row['request'])+','+b(row['array'])+'},'+values+'}'
        path=work/(name+'.bend');path.write_text('import Base\nimport ../../../host/java/ClassInit.bend as M\ndef main() -> IO(Unit):\n  IO.write(M.ci_trace('+values+',M.ci_empty()))\n')
        result=subprocess.run([os.environ.get('BEND','bend'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
        assert result.returncode==0,result.stdout+result.stderr
        return [[int(v) for v in line.split(':')] for line in result.stdout.splitlines()]
    basis=[HERE/n for n in ['ClassInit.lean','ClassInit.bend','ClassInitCase.lean','class_init_conformance.py']]
    all_raw=[];profiles=[];source_identity=None
    for name,major in zip(CAPTURES,[17,21,25]):
        capture=HERE/'evidence'/name;receipt=json.loads((capture/'receipt.json').read_text())
        assert receipt['cases']==19 and receipt['profile']['JAVA_VERSION'].split('.')[0]==str(major)
        assert receipt['scope'].startswith('Authored class literals,Class.forName')
        for file,digest in receipt['sourcesSha256'].items():assert sha(capture/file)==digest
        if source_identity is None:source_identity=receipt['sourcesSha256']
        else:assert receipt['sourcesSha256']==source_identity
        for stem,command in zip(['compile','execute'],receipt['commands']):
            assert command['exitCode']==0 and command['ownedGroupAbsent'] and not command['timedOut']
            for stream in ['stdout','stderr']:assert sha(capture/(stem+'.'+stream))==command[stream+'Sha256']
        assert sha(capture/'execute.stdout')==receipt['observedSha256']
        records=[json.loads(l) for l in (capture/'execute.stdout').read_text().splitlines()]
        assert len(records)==21 and all(('case' in r)^('runtimeClass' in r) for r in records)
        assert {r['runtimeClass']:r['sha256'] for r in records if 'runtimeClass' in r}==receipt['runtimeClassesSha256']
        assert set(receipt['runtimeClassesSha256'])=={'java/lang/Class.class','java/lang/ClassLoader.class'}
        rows=[r for r in records if 'case' in r];actions,answers=project(rows)
        result=lean_run(envelope(actions),str(major));assert result.returncode==0,result.stdout+result.stderr
        assert json.loads(result.stdout)==answers and bend_run(actions,'Cases'+str(major))==answers
        all_raw.append(rows);profiles.append(dict(java=major,profile=receipt['profile'],comparisons=len(rows)))
        basis += [f for f in capture.iterdir() if f.is_file()]
    assert all_raw[0]==all_raw[1]==all_raw[2],'Recorded cross-JDK parity changed'
    actions,answers=project(all_raw[0])
    negatives=[dict(envelope(actions),schema=2),dict(envelope(actions),contract='java18'),
        envelope([dict(actions[0],target=5)]),envelope([dict(actions[0],loader=3)]),envelope([dict(actions[0],operation=3)]),
        envelope([dict(actions[0],request=True)]),envelope([dict(actions[2],request=False)]),
        envelope([dict(actions[0],array=True)]),envelope([dict(actions[0],request=1)]),
        envelope([dict(actions[4],loader=1)]),envelope([actions[0]]*65)]
    for i,request in enumerate(negatives):assert lean_run(request,'negative-'+str(i)).returncode==2
    variants=[]
    def counted(index,counter,delta):
        changed=copy.deepcopy(all_raw[0]);changed[index]['after'][counter]+=delta
        for row in changed[index+1:]:row['before'][counter]+=delta;row['after'][counter]+=delta
        variants.append(changed)
    counted(1,0,1)   # Claim false lookup initialized the target.
    counted(5,1,-1)  # Claim failure rolled back the initializer effect.
    counted(13,3,1)  # Claim array lookup initialized its component.
    counted(11,4,-1) # Claim missing lookup had no custom-loader effect.
    for index,changes in [(5,dict(error=ERRORS[1],caughtByClassNotFound=True,caughtByException=True)),
            (6,dict(error=ERRORS[2])),(5,dict(caughtByException=True)),(8,dict(actualLoader=0))]:
        changed=copy.deepcopy(all_raw[0]);changed[index].update(changes);variants.append(changed)
    changed=copy.deepcopy(all_raw[0]);changed[8]['classIdentity']=1;changed[9]['classIdentity']=1;variants.append(changed)
    changed=copy.deepcopy(all_raw[0]);changed[7].update(returnedClass=False,className='',actualLoader=-1,classIdentity=0,error=ERRORS[3]);variants.append(changed)
    for changed in variants:
        a,wrong=project(changed);assert a==actions and any(x!=y for x,y in zip(answers,wrong))
    # Both models already produced the entire reference trace. Each mutation must
    # contradict those same predictions; there is no native recollection.
    refusals=0
    for index,field,value in [(0,'initialize',1),(0,'index',True),(2,'initialize',False),
            (0,'className','other.Class'),(0,'actualLoader',3),(0,'caughtByException','false')]:
        changed=copy.deepcopy(all_raw[0]);changed[index][field]=value
        try:project(changed)
        except AssertionError:refusals+=1
        else:raise AssertionError('Unselected observation admitted')
    changed=copy.deepcopy(all_raw[0]);changed[0]['after'][0]=True
    try:project(changed)
    except AssertionError:refusals+=1
    else:raise AssertionError('Boolean is not a measured counter')
    caller=ROOT/CALLER;receipt=json.loads((caller/'receipt.json').read_text())
    assert receipt['command']['exitCode']==0 and receipt['command']['ownedGroupAbsent'] and not receipt['command']['timedOut']
    for file,digest in receipt['sourceSha256'].items():assert sha(caller/file)==digest
    for stream in ['stdout','stderr']:assert sha(caller/('inspect.'+stream))==receipt['command'][stream+'Sha256']
    facts=[json.loads(l) for l in (caller/'inspect.stdout').read_text().splitlines()]
    calls=[r for r in facts if r['kind']=='invoke' and r['owner']=='java/lang/Class' and r['name']=='forName']
    assert calls==receipt['confirmedClassForNameCalls'] and len(calls)==1 and calls[0]['type']=='(Ljava/lang/String;)Ljava/lang/Class;'
    lifecycles=json.loads((ROOT/'host/minecraft/polytone-lifecycles.json').read_text())
    anchor=next(m for m in lifecycles['managers'] if m['id']=='polytone.slotify')['methodAnchors']['parseWithLevel']
    assert lifecycles['artifactSha256']==receipt['artifactSha256']
    assert lifecycles['sources'][anchor['source']]['originalClassSha256']==receipt['originalClassSha256']
    basis += [f for f in caller.iterdir() if f.is_file()]+[ROOT/'host/minecraft/polytone-lifecycles.json']
    report=dict(schema=1,status='passed-authored-serial-class-lookup-host-comparison',profiles=profiles,comparisons=57,
        leanLaws=22,bendLaws=14,decoderRefusals=len(negatives),observationAdapterRefusals=refusals,changedObservationControls=len(variants),
        originalProviderCaller=dict(artifactSha256=receipt['artifactSha256'],call=calls[0],qualification='original static instruction;not provider runtime execution'),
        basisSha256={str(f.relative_to(ROOT)):sha(f) for f in sorted(basis)},
        limits=['Serial authored targets,controlled loaders and named JDK/macOS profiles only;no general VM/concurrency/loader/effect-closure proof.',
            'Initialization state is an abstract model predicting measured calls/effects,not a private-JVM-state readback.',
            'Class identity labels are first-seen ordinals of actual Class references in this fixture;not stable identifiers across processes.',
            'The Polytone call is confirmed statically. No pack,target class,GUI,provider hook or actual application failure was executed.',
            'No native Windows/Linux class-initialization observation;ordinary CI runs these retained models without Java.'])
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','comparisons','decoderRefusals','observationAdapterRefusals','changedObservationControls']}))


if __name__=='__main__':main()
