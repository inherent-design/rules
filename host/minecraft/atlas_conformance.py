#!/usr/bin/env python3
"""Pure final assembly/ownership comparisons against retained original atlas calls."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CAPTURES=['atlas-1.21.1-20261125T122132816667Z','atlas-1.21.4-20261125T122944379911Z','atlas-1.21.5-20261125T122218667952Z',
          'atlas-1.21.11-20261125T122946006600Z','atlas-26.3-20261125T122947079846Z']
LABELS=['A','B','C'];ERRORS=['NONE','java.lang.IllegalStateException: authored-source-failure']+['java.lang.IllegalStateException: authored-discard:'+s for s in LABELS]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def translate(plan):
    assert plan['schema']==1 and plan['contract']=='original-atlas-list-authored-source-control'
    rows=[]
    for case in plan['cases']:
        assert len(case['throwDiscard'])<=1 and all(v in LABELS for v in case['throwDiscard'])
        sources=[]
        for source in case['sources']:
            group=[]
            for a in source:
                assert type(a.get('catch',False)) is bool
                op=['add','remove','fail'].index(a['op'])
                if op==0:
                    key=['fixture:a','fixture:b'].index(a['id']);supplier=LABELS.index(a['supplier'])+1
                elif op==1:key=['other:','fixture:','fixture:a'].index(a['prefix']);supplier=0
                else:key=supplier=0
                group.append(dict(kind=op,key=key,supplier=supplier,caught=a.get('catch',False)))
            sources.append(group)
        rows.append(dict(throwing=LABELS.index(case['throwDiscard'][0])+1 if case['throwDiscard'] else 0,sources=sources))
    return rows


def project(obs,plan):
    assert set(obs)=={'schema','observerErrors','cases'} and type(obs['schema']) is int and obs['schema']==1 and obs['observerErrors']==0
    assert len(obs['cases'])==len(plan['cases'])==16;rows=[]
    for r,p in zip(obs['cases'],plan['cases']):
        assert set(r)=={'case','returned','defaultLoaders','error','sourceRuns','retained','discards','events'} and r['case']==p['id']
        assert type(r['returned']) is bool and type(r['defaultLoaders']) is int and 0<=r['defaultLoaders']<=1
        assert type(r['sourceRuns']) is int and 0<=r['sourceRuns']<=len(p['sources'])
        assert r['error'] in ERRORS and (r['error']=='NONE')==r['returned']
        assert type(r['retained']) is list and len(r['retained'])<=2 and all(v in LABELS for v in r['retained'])
        if not r['returned']:assert not r['retained'] and r['defaultLoaders']==0
        assert type(r['discards']) is dict and set(r['discards'])<=set(LABELS)
        assert all(type(v) is int and 0<=v<=16 for v in r['discards'].values())
        assert type(r['events']) is list and all(type(v) is str for v in r['events'])
        assert [v for v in r['events']if v.startswith('source:')]==['source:'+str(i)for i in range(r['sourceRuns'])]
        assert all(r['events'].count('discard:'+label)==r['discards'].get(label,0) for label in LABELS)
        rows.append([int(r['returned']),r['defaultLoaders']]+[r['retained'].count(v)for v in LABELS]+[int(v in r['discards'])for v in LABELS]+
            [r['discards'].get(v,0)for v in LABELS]+[r['sourceRuns'],r['events'].count('caught'),ERRORS.index(r['error'])])
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);a=p.parse_args()
    work=ROOT/'.build/minecraft/atlas-replay';work.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=os.environ.get('LEAN_PATH',str(ROOT/'.build/formal')),BEND_NO_TELEMETRY='1')
    plan=json.loads((HERE/'atlas_cases.json').read_text());rows=translate(plan)
    request=dict(schema=1,contract='authored-atlas-output-controls',cases=rows)
    def lean_run(data,name):
        path=work/(name+'.json');path.write_text(json.dumps(data)+'\n')
        return subprocess.run([os.environ.get('LEAN','lean'),'--run',str(HERE/'AtlasCase.lean'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    def bend_run(data):
        def linked(items):
            out='Nil{}'
            for item in reversed(items):out='Con{'+item+','+out+'}'
            return out
        calls=[]
        for case in data:
            groups=linked([linked(['M.AtlasAction{'+','.join([str(x['kind'])+'n',str(x['key'])+'n',str(x['supplier'])+'n','True{}'if x['caught']else'False{}'])+'}' for x in group]) for group in case['sources']])
            calls.append('M.atlas_render(M.atlas_sources('+groups+',M.atlas_empty(),' +str(case['throwing'])+'n)) ++ "\\n"')
        path=work/'Cases.bend';path.write_text('import Base\nimport ../../../host/minecraft/Atlas.bend as M\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
        r=subprocess.run([os.environ.get('BEND','bend'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
        assert r.returncode==0,r.stdout+r.stderr
        return [[int(v)for v in line.split(':')]for line in r.stdout.splitlines()]
    emitted=lean_run(request,'native');assert emitted.returncode==0,emitted.stdout+emitted.stderr
    predicted=json.loads(emitted.stdout);assert bend_run(rows)==predicted
    basis=[HERE/n for n in ['Atlas.lean','Atlas.bend','AtlasCase.lean','atlas_cases.json','atlas_conformance.py']];profiles=[];raw=[]
    for name in CAPTURES:
        c=HERE/'evidence'/name;r=json.loads((c/'receipt.json').read_text())
        assert r['cases']==16 and r['observerErrors']==0
        for file,h in r['sourcesSha256'].items():assert sha(c/file)==h
        assert sha(c/'bindings.json')==r['bindingsSha256'] and sha(c/'observed.json')==r['observed.jsonSha256']
        assert (c/'atlas_cases.json').read_bytes()==(HERE/'atlas_cases.json').read_bytes()
        for stem,cmd in zip(['compile','execute'],r['commands']):
            assert cmd['exitCode']==0 and cmd['ownedGroupAbsent'] and not cmd['timedOut']
            for stream in ['stdout','stderr']:assert sha(c/(stem+'.'+stream))==cmd[stream+'Sha256']
        obs=json.loads((c/'observed.json').read_text());observed=project(obs,plan)
        assert predicted==observed,(name,[(i,x,y)for i,(x,y)in enumerate(zip(predicted,observed))if x!=y])
        profiles.append(dict(target=r['target'],profile=r['profile'],comparisons=16));raw.append(obs);basis += [f for f in c.iterdir()if f.is_file()]
    negatives=[dict(request,schema=2),dict(request,contract='gpu-atlas'),dict(request,cases=rows*5)]
    for key,value in [('throwing',4),('sources',[[]]*9),('sources',[[dict(kind=3,key=0,supplier=0,caught=False)]]),('sources',[[dict(kind=0,key=2,supplier=1,caught=False)]]),('sources',[[dict(kind=0,key=0,supplier=0,caught=False)]]),('sources',[[dict(kind=0,key=0,supplier=4,caught=False)]]),('sources',[[dict(kind=1,key=3,supplier=0,caught=False)]]),('sources',[[dict(kind=1,key=1,supplier=1,caught=False)]]),('sources',[[dict(kind=2,key=0,supplier=0,caught=1)]])]:
        row=copy.deepcopy(rows[0]);row[key]=value;negatives.append(dict(request,cases=[row]))
    ambiguous=dict(throwing=1,sources=[[dict(kind=0,key=0,supplier=1,caught=False),dict(kind=0,key=1,supplier=3,caught=False),dict(kind=1,key=1,supplier=0,caught=False)]])
    negatives.append(dict(request,cases=[ambiguous]))
    for i,bad in enumerate(negatives):assert lean_run(bad,'negative-'+str(i)).returncode==2
    changed=[]
    for case,field,value in [('replace','retained',['A']),('same-key-same-supplier','retained',[]),('caught-remove-failure','retained',['A']),('source-failure','sourceRuns',2),('single','defaultLoaders',0)]:
        obs=copy.deepcopy(raw[0]);r=next(r for r in obs['cases']if r['case']==case);assert r[field]!=value;r[field]=value;changed.append(obs)
    for obs in changed:
        try:assert project(obs,plan)==predicted
        except AssertionError:pass
        else:raise AssertionError('Changed native observation survived')
    exclusions=json.loads((HERE/'evidence/atlas-exclusions.json').read_text())
    assert len(exclusions['excluded'])==3
    for entry in exclusions['excluded']:
        c=HERE/'evidence'/entry['capture'];assert entry['capture']not in CAPTURES and entry['replacement']in CAPTURES
        assert sha(c/'receipt.json')==entry['receiptSha256']and sha(c/'observed.json')==entry['observedSha256']
        obs=json.loads((c/'observed.json').read_text());assert sum('NoClassDefFoundError'in r['error']for r in obs['cases'])==entry['unexpectedLinkageErrors']==15
        try:project(obs,plan)
        except AssertionError:pass
        else:raise AssertionError('Excluded linkage capture admitted')
        basis += [f for f in c.iterdir()if f.is_file()]
    negative=HERE/'evidence'/exclusions['negative'];guard=json.loads((negative/'receipt.json').read_text());cmd=guard['command']
    assert cmd['exitCode']==2 and cmd['ownedGroupAbsent']and not cmd['timedOut']
    for stream in ['stdout','stderr']:assert sha(negative/('execute.'+stream))==cmd[stream+'Sha256']
    assert sha(negative/'observed.json')==guard['observedSha256']
    assert json.loads((negative/'observed.json').read_text())['observerErrors']==guard['unexpectedOutcomes']==15
    assert sha(HERE/'evidence'/guard['sourceCapture']/'AtlasProbe.java')==guard['javaProducerSha256']
    basis += [f for f in negative.iterdir()if f.is_file()]+[HERE/'evidence/atlas-exclusions.json',HERE/'atlas-sources.json',HERE/'atlas_sources.py']
    report=dict(schema=1,status='passed-original-atlas-assembly-controls',profiles=profiles,comparisons=80,leanLaws=16,bendLaws=8,
        decoderRefusals=len(negatives),changedObservationControls=len(changed),excludedLinkageCaptures=3,unexpectedLinkageGuardErrors=15,basisSha256={str(f.relative_to(ROOT)):sha(f)for f in sorted(basis)},
        limits=['Whole authored-case final14field projection;not full trace refinement,real sprite source/codec/image/GPU or provider reachability.',
            'Supplier bags preserve multiplicity;native HashMap survivor/discard order is deliberately not equated with deterministic model traversal.',
            'Throwing multi-target removals refuse without actual order witness;native adverse fixtures only have a single throwing target.',
            'Caught callback failures/aliases are explicit source-adapter controls. No production leak,bug,resource release or graphics qualification.',
            'Native macOS/JDK21/25 only. Ordinary replay starts Lean/Bend and reads retained authored data,never Java or applications.'])
    if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','comparisons','decoderRefusals','changedObservationControls']}))


if __name__=='__main__':main()
