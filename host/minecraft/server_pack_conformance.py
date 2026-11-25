#!/usr/bin/env python3
"""Pure branch models against retained original-manager traces; never starts Java/game."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CAPTURES=['server-packs-1.21.1-20261125T115753954514Z','server-packs-1.21.4-20261125T115826313359Z',
    'server-packs-1.21.5-20261125T115827718729Z','server-packs-1.21.11-20261125T115829152106Z','server-packs-26.3-20261125T115830049218Z']
OPS=['remote','local','allow','reject','reset','tick','download-ok','download-fail','success','failure','recovery-failure','pop','popAll']
PROMPTS=['PENDING','ALLOWED','DECLINED'];DOWNLOADS=['REQUESTED','PENDING','DONE'];ACTIVATIONS=['INACTIVE','PENDING','ACTIVE']
REASONS=['NONE','DECLINED','DOWNLOAD_FAILED','ACTIVATION_FAILED','DISCARDED','SERVER_REMOVED']
FEEDBACK=set(REASONS[1:5]+['ACCEPTED','DOWNLOADED','APPLIED'])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def view(s):
    assert set(s)=={'prompt','records','schedules','downloads','reloads','downloadCallbackHeld','reloadCallbackHeld','toLoad','feedback'}
    assert s['prompt'] in PROMPTS and type(s['records']) is list and len(s['records'])<=1
    for n in ['schedules','downloads','reloads']:assert type(s[n]) is int and 0<=s[n]<=64
    for n in ['downloadCallbackHeld','reloadCallbackHeld']:assert type(s[n]) is bool
    assert type(s['toLoad']) is list and len(s['toLoad'])<=1 and all(v in ['owned-placeholder.zip','download-placeholder.zip'] for v in s['toLoad'])
    assert type(s['feedback']) is list and all(type(x) is str and x in FEEDBACK for x in s['feedback'])
    if s['records']:
        r=s['records'][0]
        assert set(r)=={'downloadStatus','activationStatus','removalReason','accepted','path'}
        assert r['downloadStatus'] in DOWNLOADS and r['activationStatus'] in ACTIVATIONS and r['removalReason'] in REASONS
        assert type(r['accepted']) is bool and r['path'] in ['NONE','owned-placeholder.zip','download-placeholder.zip']
        return [PROMPTS.index(s['prompt']),1,int(r['accepted']),DOWNLOADS.index(r['downloadStatus']),ACTIVATIONS.index(r['activationStatus']),REASONS.index(r['removalReason']),int(bool(s['toLoad']))]
    return [PROMPTS.index(s['prompt']),0,0,0,0,0,int(bool(s['toLoad']))]


def project(raw,plan):
    assert raw['schema']==1 and type(raw['schema']) is int and raw['observerErrors']==0
    assert len(raw['rows'])==sum(len(c['actions']) for c in plan['cases'])==77
    inputs=[];answers=[];cursor=0
    for case in plan['cases']:
        previous=None
        for index,action in enumerate(case['actions']):
            r=raw['rows'][cursor];cursor+=1
            assert set(r)=={'case','index','action','before','after'} and r['case']==case['id'] and type(r['index']) is int and r['index']==index and r['action']==action
            before=r['before'];after=r['after'];v=view(before);w=view(after)
            if previous is not None:assert before==previous
            else:assert v==[0,0,0,0,0,0,0] and before['schedules']==before['downloads']==before['reloads']==0 and not before['feedback']
            previous=after
            assert after['feedback'][:len(before['feedback'])]==before['feedback']
            feedback=after['feedback'][len(before['feedback']):]
            update=after['schedules']-before['schedules'];downloads=after['downloads']-before['downloads'];reloads=after['reloads']-before['reloads']
            assert all(type(x) is int and 0<=x<=1 for x in [update,downloads,reloads])
            op=OPS.index(action);inputs.append([op]+v)
            if op in [0,1]:
                assert not before['records'],'Repeated IDs/additional records unselected'
                answer=[int(feedback==['DECLINED']),w[2],w[3],update]
            elif op==2:answer=[w[0],w[2],feedback.count('ACCEPTED'),update]
            elif op==3:answer=[w[0],w[2],w[5],w[1]]
            elif op==4:answer=[w[0],w[2],w[5],update]
            elif op==5:answer=[downloads,reloads,w[4],v[1]-w[1]]
            elif op==6:answer=[w[3],feedback.count('DOWNLOADED'),update,int(after['downloadCallbackHeld'])]
            elif op==7:answer=[w[5],update,int(after['downloadCallbackHeld']),reloads]
            elif op==8:answer=[w[4],feedback.count('APPLIED'),update,int(after['reloadCallbackHeld'])]
            elif op==9:answer=[w[4],w[5],update,len(after['toLoad'])]
            elif op==10:answer=[w[4],w[5],update,int(after['reloadCallbackHeld'])]
            else:answer=[w[5],update,w[4],len(feedback)]
            answers.append(answer)
    return inputs,answers


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);a=p.parse_args()
    work=ROOT/'.build/minecraft/server-pack-replay';work.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=os.environ.get('LEAN_PATH',str(ROOT/'.build/formal')),BEND_NO_TELEMETRY='1')
    contract='java-server-pack-single-record-branches'
    def envelope(rows):return dict(schema=1,contract=contract,rows=rows)
    def lean_run(request,name):
        path=work/(name+'.json');path.write_text(json.dumps(request)+'\n')
        return subprocess.run([os.environ.get('LEAN','lean'),'--run',str(HERE/'ServerPacksCase.lean'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    def bend_run(rows,name):
        values='Nil{}'
        for row in reversed(rows):values='Con{M.SPRow{'+','.join(str(n)+'n' for n in row)+'},'+values+'}'
        path=work/(name+'.bend');path.write_text('import Base\nimport ../../../host/minecraft/ServerPacks.bend as M\ndef main() -> IO(Unit):\n  IO.write(M.sp_trace('+values+'))\n')
        result=subprocess.run([os.environ.get('BEND','bend'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
        assert result.returncode==0,result.stdout+result.stderr
        return [[int(v) for v in line.split(':')] for line in result.stdout.splitlines()]
    plan=json.loads((HERE/'server_pack_cases.json').read_text());basis=[HERE/n for n in ['ServerPacks.lean','ServerPacks.bend','ServerPacksCase.lean','server_pack_cases.json','server_pack_conformance.py']]
    raw=[];profiles=[];answers=None
    for name in CAPTURES:
        c=HERE/'evidence'/name;r=json.loads((c/'receipt.json').read_text())
        assert r['actions']==77 and r['observerErrors']==0
        for file,digest in r['sourcesSha256'].items():assert sha(c/file)==digest
        assert sha(c/'bindings.json')==r['bindingsSha256'] and sha(c/'observed.json')==r['observed.jsonSha256']
        assert (c/'server_pack_cases.json').read_bytes()==(HERE/'server_pack_cases.json').read_bytes()
        for stem,cmd in zip(['compile','execute'],r['commands']):
            assert cmd['exitCode']==0 and cmd['ownedGroupAbsent'] and not cmd['timedOut']
            for stream in ['stdout','stderr']:assert sha(c/(stem+'.'+stream))==cmd[stream+'Sha256']
        obs=json.loads((c/'observed.json').read_text());rows,expected=project(obs,plan)
        result=lean_run(envelope(rows),name);assert result.returncode==0,result.stdout+result.stderr
        emitted=json.loads(result.stdout);assert emitted==expected,(name,[(i,x,y) for i,(x,y) in enumerate(zip(emitted,expected)) if x!=y])
        assert bend_run(rows,name)==expected
        if answers is None:answers=expected
        else:assert answers==expected
        raw.append(obs);profiles.append(dict(target=r['target'],profile=r['profile'],actions=77));basis += [f for f in c.iterdir() if f.is_file()]
    assert all(obs==raw[0] for obs in raw),'Native trace parity changed'
    rows,expected=project(raw[0],plan)
    negatives=[dict(envelope(rows),schema=2),dict(envelope(rows),contract='multi-record'),envelope(rows*7),envelope([[13]+rows[0][1:]]),envelope([rows[0][:-1]]),envelope([[True]+rows[0][1:]])]
    for index,limit in enumerate([2,1,1,2,2,5,1],1):
        changed=rows[0].copy();changed[index]=limit+1;negatives.append(envelope([changed]))
    for i,request in enumerate(negatives):assert lean_run(request,'negative-'+str(i)).returncode==2
    mutations=[]
    for action,field,value in [('tick','activationStatus','ACTIVE'),('reject','accepted',False),('success','removalReason','NONE'),('download-ok','downloadStatus','PENDING')]:
        changed=copy.deepcopy(raw[0]);r=next(r for r in changed['rows'] if r['action']==action and r['after']['records'] and r['after']['records'][0][field]!=value and (field!='accepted' or r['before']['records'][0]['accepted']))
        r['after']['records'][0][field]=value
        at=changed['rows'].index(r)
        if at+1<len(changed['rows']) and changed['rows'][at+1]['case']==r['case']:changed['rows'][at+1]['before']=copy.deepcopy(r['after'])
        mutations.append(changed)
    # Record retirement must not erase the still-held callback observation.
    changed=copy.deepcopy(raw[0]);r=next(r for r in changed['rows'] if r['case']=='remove-during-download' and r['action']=='download-ok');r['after']['schedules']-=1
    changed['rows'][changed['rows'].index(r)+1]['before']=copy.deepcopy(r['after']);mutations.append(changed)
    rejected=0
    for obs in mutations:
        try:
            ins,ans=project(obs,plan)
            result=lean_run(envelope(ins),'mutated-'+str(rejected));assert result.returncode==0
            assert json.loads(result.stdout)==ans
        except AssertionError:rejected+=1
        else:raise AssertionError('Changed observation survived')
    report=dict(schema=1,status='passed-selected-original-server-pack-branches',profiles=profiles,comparisons=385,leanLaws=17,bendLaws=12,
        decoderRefusals=len(negatives),changedObservationControls=rejected,basisSha256={str(f.relative_to(ROOT)):sha(f) for f in sorted(basis)},
        limits=['Each comparison predicts four selected branch observations from independently captured prestate;not full trace/state-machine refinement.',
        'All77 retained actions/profile have selected projections,not every field/effect. Native traces retain additional evidence.',
        'Single-record serial callbacks and opaque paths only;not HTTP,bytes,full resource reload,packet delivery,GUI,renderer or mod coexistence.',
        'Controlled updater/reload/download adapters are explicit;native Windows/Linux and adverse callback behavior remain unqualified.'])
    if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','comparisons','decoderRefusals','changedObservationControls']}))


if __name__=='__main__':main()
