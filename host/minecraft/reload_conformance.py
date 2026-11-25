#!/usr/bin/env python3
"""Pure retained original-orchestrator comparisons;no JVM,game,listener or worker launch."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CAPTURES=[('1.21.1','reload-native-1.21.1-20261125T171404982601Z'),
    ('1.21.4','reload-native-1.21.4-20261125T171406555515Z'),
    ('1.21.5','reload-native-1.21.5-20261125T171408073404Z'),
    ('1.21.11','reload-native-1.21.11-20261125T171409740934Z'),
    ('26.3','reload-native-26.3-20261125T171347033489Z')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
FIELDS=['hasShared','sharedFailure','initial','p0','p1','barrier0','fail0']


def row(count=2,**values):return dict(count=count,**dict.fromkeys(FIELDS))|values


def projection(raw,count):
    assert raw['factory']in ['returned','threw-FixtureFailure']
    futures=raw['listenerFutures'];assert len(futures)==count
    assert all(type(n)is int and 0<=n<=3 for n in futures)
    assert type(raw['overall'])is int and 0<=raw['overall']<=3
    assert raw['effects']in [[],[0],[0,1]],'Effect presence/order differs.'
    assert raw['sameSharedContext']is True,'Shared-state context differs.'
    a,b=futures if count else (3,3)
    return [int(raw['factory']!='returned'),a,b,raw['overall'],int(0 in raw['effects']),int(1 in raw['effects']),len(raw['shared']),len(raw['invoked'])]


def plan(request,observed):
    assert request['schema']==observed['schema']==1 and observed['observerErrors']==0
    assert [c['id']for c in request['cases']]==[c['id']for c in observed['cases']]
    selected=[];skipped=[]
    for spec,native in zip(request['cases'],observed['cases'],strict=True):
        if spec['requiresSharedState']and not request['hasSharedState']:
            assert native==dict(id=spec['id'],skipped='selected listener interface lacks this hook')
            skipped.append(spec['id']);continue
        assert 'skipped'not in native
        count=spec['count'];assert count in [0,2]
        states=[spec['initial'],0,0];snapshots=native['snapshots'];assert len(snapshots)==1+len(spec['actions'])
        arrivals=[]
        for number,raw in enumerate(snapshots):
            phase='created'
            if number:
                action=spec['actions'][number-1];target=action['target'];value=action['value']
                assert target in [-1,0,1]and value in [1,2]and states[target+1]==0
                states[target+1]=value;phase=f'complete-{target}-{value}'
                if target>=0 and value==1 and(target!=0 or spec['barrier0']):arrivals.append(target)
            assert raw['phase']==phase and raw['initial']==states[0]
            assert raw['preparations']==(states[1:]if count else [])
            facts=row(count,hasShared=request['hasSharedState'],sharedFailure=spec['sharedFails']==1,
                initial=states[0],p0=states[1],p1=states[2],barrier0=spec['barrier0'],fail0=spec['applyFails0'])
            selected.append(dict(case=spec['id'],step=number,input=facts,raw=raw,arrivals=arrivals.copy()))
    return selected,skipped


def compare(entries,predicted):
    assert len(entries)==len(predicted)
    history={}
    for entry,wanted in zip(entries,predicted,strict=True):
        raw=entry['raw'];assert projection(raw,entry['input']['count'])==wanted,'Reload result differs.'
        assert raw['shared']==list(range(wanted[6]))and raw['invoked']==list(range(wanted[7]))
        assert raw['barriers']==entry['arrivals']
        previous=history.get(entry['case']);events=[]if previous is None else previous['events'].copy()
        if previous is None:events=['shared'+str(n)for n in raw['shared']]+['invoke'+str(n)for n in raw['invoked']]
        else:
            for n in raw['barriers'][len(previous['barriers']):]:events.append('barrier'+str(n))
        before=[]if previous is None else previous['effects']
        assert raw['effects'][:len(before)]==before
        for n in raw['effects'][len(before):]:events.append('effect'+str(n))
        assert raw['events']==events,'Controlled callback order differs.'
        history[entry['case']]=raw


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--captures',type=Path,default=HERE/'evidence');a=p.parse_args();a.captures=a.captures.resolve()
    work=ROOT/'.build/minecraft/reload-replay';work.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=os.environ.get('LEAN_PATH',str(ROOT/'.build/formal')),BEND_NO_TELEMETRY='1')
    def lean(data,label):
        path=work/(label+'.json');path.write_text(json.dumps(data)+'\n')
        return subprocess.run([os.environ.get('LEAN','lean'),'--run',str(HERE/'ReloadScheduleCase.lean'),str(path)],cwd=ROOT,env=env,text=True,capture_output=True,timeout=30)
    def bend(rows,label):
        calls=[]
        for r in rows:
            args=[str(r['count'])+'n']+['True{}'if r[k]else'False{}'for k in FIELDS[:2]]+[str(r[k]or 0)+'n'for k in FIELDS[2:5]]+['True{}'if r[k]else'False{}'for k in FIELDS[5:]]
            calls.append('show(M.reload_evaluate('+','.join(args)+')) ++ "\\n"')
        text='import Base\nimport ../../../host/minecraft/ReloadSchedule.bend as M\ndef show(xs: List<&2, Nat>) -> String:\n  match xs:\n    case Nil{}: ""\n    case Con{h,t}: Nat.show(h) ++ "," ++ show(t)\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n'
        path=work/(label+'.bend');path.write_text(text)
        result=subprocess.run([os.environ.get('BEND','bend'),str(path)],cwd=ROOT,env=env,text=True,capture_output=True,timeout=30);assert result.returncode==0,result.stdout+result.stderr
        lines=result.stdout.splitlines();assert all(line.endswith(',')for line in lines)
        return [[int(n)for n in line[:-1].split(',')]for line in lines]
    all_entries=[];profiles=[];basis=[HERE/n for n in ['ReloadProbe.java','ReloadSchedule.lean','ReloadSchedule.bend','ReloadScheduleCase.lean','reload_conformance.py','reload-cases.json','reload-sources.json','targets.json']]
    cases=json.loads((HERE/'reload-cases.json').read_text());targets=json.loads((HERE/'targets.json').read_text())['javaReferences']
    for version,name in CAPTURES:
        cap=a.captures/name;r=json.loads((cap/'receipt.json').read_text());request=json.loads((cap/'request.json').read_text());raw=json.loads((cap/'observed.json').read_text())
        target=next(t for t in targets if t['release']==version)
        assert r['target']==target['id']and r['clientSha256']==target['source']['clientSha256']and r['metadataSha256']==target['source']['metadataSha256']
        assert request==cases|dict(hasSharedState=version in ['1.21.11','26.3'])
        assert sha(cap/'request.json')==r['requestSha256']and sha(cap/'observed.json')==r['observed.jsonSha256']and sha(cap/'bindings.json')==r['bindingsSha256']
        for n,h in r['sourcesSha256'].items():assert sha(cap/n)==h
        assert (cap/'ReloadProbe.java').read_bytes()==(HERE/'ReloadProbe.java').read_bytes()
        for stem,c in zip(['compile','execute'],r['commands'],strict=True):
            assert c['exitCode']==0 and c['ownedGroupAbsent']and not c['timedOut']
            for channel in ['stdout','stderr']:assert sha(cap/(stem+'.'+channel))==c[channel+'Sha256']
        entries,skipped=plan(request,raw);dto=dict(schema=1,contract='direct-two-listener-reload-v1',rows=[e['input']for e in entries])
        result=lean(dto,'plan-'+version);assert result.returncode==0,result.stdout+result.stderr;predicted=json.loads(result.stdout)
        assert predicted==bend(dto['rows'],'plan-'+version);compare(entries,predicted)
        profiles.append(dict(target=r['target'],snapshots=len(entries),executedCases=len(raw['cases'])-len(skipped),profileHookSkips=skipped))
        all_entries.append((request,raw,predicted));basis.extend(cap/n for n in [*r['sourcesSha256'],'request.json','observed.json','bindings.json','receipt.json','compile.stdout','compile.stderr','execute.stdout','execute.stderr'])
    valid=row(hasShared=False,sharedFailure=False,initial=1,p0=1,p1=1,barrier0=True,fail0=False)
    dto=dict(schema=1,contract='direct-two-listener-reload-v1',rows=[valid]);bad=[dict(dto,schema=2),dict(dto,contract='all-workers-retired'),dict(dto,rows=[valid]*129)]
    for change in [dict(count=1),dict(hasShared=None),dict(hasShared=True,sharedFailure=None),dict(initial=None),dict(initial=3),dict(p0=3),dict(p1=None),dict(barrier0=None),dict(fail0=None),dict(sharedFailure=True),dict(hasShared=1)]:bad.append(dict(dto,rows=[valid|change]))
    for i,data in enumerate(bad):assert lean(data,'invalid-'+str(i)).returncode==2
    unneeded=[row(0),row(hasShared=True,sharedFailure=True),valid|dict(sharedFailure=None)]
    result=lean(dict(dto,rows=unneeded),'unneeded');assert result.returncode==0
    assert json.loads(result.stdout)==bend(unneeded,'unneeded')
    request,raw,predicted=all_entries[-1];changed=[]
    changes=[('prepare-failure',1,'overall',1),('prepare-failure',1,'listenerFutures',[2,1]),('apply-failure',2,'effects',[]),
        ('ordered',3,'effects',[1,0]),('initial-failure',1,'overall',2),('empty-listeners',0,'overall',0),
        ('shared-hook-failure',0,'invoked',[0]),('bypassed-barrier',1,'effects',[]),('shared-hooks',0,'sameSharedContext',False)]
    for name,step,field,value in changes:
        mutated=copy.deepcopy(raw);next(c for c in mutated['cases']if c['id']==name)['snapshots'][step][field]=value
        try:entries,_=plan(request,mutated);compare(entries,predicted)
        except AssertionError:changed.append(name+'/'+field)
        else:raise AssertionError('Changed reload observation admitted.')
    report=dict(schema=1,status='passed-controlled-original-reload',profiles=profiles,executedCases=sum(p['executedCases']for p in profiles),snapshots=sum(p['snapshots']for p in profiles),leanLaws=14,bendLaws=8,decoderRefusals=len(bad),unneededUnknownExamples=3,changedObservationControls=changed,
        basisSha256={str(p.relative_to(ROOT)):sha(p)for p in sorted(set(basis))},limits=['Original orchestration with authored listener proxies,manual gates,direct executors;not real worker scheduling or physical resource retirement.',
            'Zero/two listeners,barrier1 always used,no apply1 failure,one completion per gate;not arbitrary listener graphs,duplicates,profiling or parallel races.',
            'Both models use the same inspected request projection;adapter/JVM/source translation fidelity is not formally proved.',
            'Future exception causes,progress counters and physical worker liveness were not captured;factory error class and selected completion states are separate.',
            'Callback trace checks supplement selected model states;no ResourceManager IO/game/pack/renderer or native other-host qualification.'])
    destination=HERE/'evidence/reload-conformance.json';destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','executedCases','snapshots','decoderRefusals','unneededUnknownExamples','changedObservationControls']}))


if __name__=='__main__':main()
