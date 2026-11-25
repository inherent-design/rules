#!/usr/bin/env python3
"""Replay retained original element/controlled consumer observations in both models."""
import argparse
import copy
from decimal import Decimal
import hashlib
import gzip
import json
import math
import os
from pathlib import Path
import subprocess
from later_codec_conformance import project as rotation_input

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
DIRECTIONS={'east':0,'west':0,'up':1,'down':1,'north':2,'south':2}


def number(n):
    return type(n) in (int,float) and math.isfinite(n)


def project_element(row):
    raw=row['input']
    if type(raw) is not dict or set(raw)-{'from','to','faces','rotation','shade','light_emission','shade_direction_override','unselected_later_field'}:
        raise ValueError('Unselected element fields')
    def vector(name):
        v=raw.get(name)
        return type(v) is list and len(v)==3 and all(number(x) and -16<=x<=32 for x in v)
    light=raw.get('light_emission',0);numeric=number(light);whole=0;fraction=0;negative=False
    if numeric:
        n=Decimal(str(light));negative=n<0;n=abs(n);whole=int(n);f=(n-whole)*10
        if whole>1000 or f!=int(f):raise ValueError('Unselected light decimal profile')
        fraction=int(f)
    elif light!='5':raise ValueError('Unselected malformed light profile')
    rawfaces=raw.get('faces');present=type(rawfaces) is dict;faces=[]
    if present:
        if len(rawfaces)>6:raise ValueError('Unselected face count')
        for key,f in rawfaces.items():
            if type(key) is not str:raise ValueError('Non-string face key')
            if f is None:
                faces.append(dict(known=key in DIRECTIONS,isNull=True,texture=False,uv=False,quadrant=False,cull=False));continue
            if type(f) is not dict or set(f)-{'texture','uv','rotation','tintindex','cullface'}:raise ValueError('Unselected face shape')
            uv=f.get('uv');angle=f.get('rotation',0)
            faces.append(dict(known=key in DIRECTIONS,isNull=False,texture=type(f.get('texture')) is str,
                uv='uv' not in f or (type(uv) is list and len(uv)==4 and all(number(x) for x in uv)),
                quadrant=type(angle) is int and angle in [0,90,180,270],cull=f.get('cullface') in DIRECTIONS))
    shade=raw.get('shade',True)
    if type(shade) is not bool and shade!='false':raise ValueError('Unselected shade shape')
    r=rotation_input(dict(action='rotation',input={'rotation':raw['rotation']} if 'rotation' in raw else {}))['data']
    return dict(kind='element',data=dict(vectors=vector('from') and vector('to'),shadeValid=type(shade) is bool,shade=shade if type(shade) is bool else False,
        lightNumeric=numeric,lightNegative=negative,lightWhole=whole,lightFraction=fraction,facesPresent=present,faces=faces,rotation=r))


def project_consumer(row):
    r=row['input']
    if set(r)!={'from','to','faces'} or r['from']!=[0,0,0] or len(r['to'])!=3 or any(type(x) is not int or x not in [0,16] for x in r['to']):raise ValueError('Unselected consumer extents')
    if type(r['faces']) is not dict or len(r['faces'])!=1:raise ValueError('Unselected consumer face count')
    name,f=next(iter(r['faces'].items()))
    if name not in DIRECTIONS or (f is not None and f!={'texture':'#a'}):raise ValueError('Unselected consumer face')
    return dict(kind='consumer',data=dict(axis=DIRECTIONS[name],dx=r['to'][0]!=0,dy=r['to'][1]!=0,dz=r['to'][2]!=0,isNull=f is None))


def native_rotation(v):
    if v['kind']=='absent':return '0/0/0/0/0/0/0'
    assert v['origin']==[0.5,0.5,0.5] and type(v['rescale']) is bool
    matrix=v['jomlComponents_m00_m01_m02_m03_m10_through_m33'];assert len(matrix)==16 and all(number(x) for x in matrix)
    if v['kind']=='euler':
        a=v['angles'];assert len(a)==3 and all(number(x) and int(x)==x for x in a)
        parts=[1,0,0,*map(int,a),int(v['rescale'])]
    else:
        assert v['kind']=='scalar' and int(v['angle'])==v['angle']
        parts=[2,{'X':1,'Y':2,'Z':3}[v['axis']],int(v['angle']),0,0,0,int(v['rescale'])]
    return '/'.join(map(str,parts))


def observed_element(row):
    assert not row.get('observerError') and type(row['accepted']) is bool
    if not row['accepted']:
        assert row['exception'].startswith('com.google.gson.')
        return 'refused'
    v=row['value'];r=row['input'];assert v['from']==r['from'] and v['to']==r['to']
    faces=v['faces'];assert set(faces)=={k.upper() for k in r['faces']}
    for name,f in r['faces'].items():
        value=faces[name.upper()]
        if f is None:assert value is None;continue
        assert value['texture']==f['texture'] and value['tint']==int(f.get('tintindex',-1))
        assert value['uv']==f.get('uv')
        expected_cull=f['cullface'].upper() if f.get('cullface') in DIRECTIONS else None
        assert value['cull']==expected_cull
    assert type(v['shade']) is bool and type(v['light']) is int
    fields=[int(v['shade']),v['light'],len(faces),sum(f is None for f in faces.values()),sum(f is not None and f['cull'] is not None for f in faces.values())]
    return 'ok:'+'/'.join(map(str,fields))+'|'+native_rotation(v['rotation'])


def observed_consumer(row,bindings):
    assert row['decoded'] is True and not row.get('observerError')
    if row['outcome']=='returned':assert row['quads']==0;stage=0
    elif row['outcome']=='lookup-intercepted':stage=2
    else:
        assert row['outcome']=='consumer-exception' and row['exception']=='java.lang.NullPointerException'
        assert row['topClass']==bindings['geometry']['class'];stage=1
    return str(stage)+':'+','.join(row['adapterCalls'])


def bend_row(row):
    d=row['data'];b=lambda x:'True{}' if x else 'False{}';n=lambda x:str(x)+'n'
    if row['kind']=='consumer':return 'consumer(E.er_consume('+','.join([n(d['axis']),*(b(d[k]) for k in ['dx','dy','dz','isNull'])])+'))'
    faces='Nil{}'
    for f in reversed(d['faces']):faces='Con{E.ERFace{'+','.join(b(f[k]) for k in ['known','isNull','texture','uv','quadrant','cull'])+'},'+faces+'}'
    r=d['rotation'];rotation='L.LDRotationInput{'+','.join(b(r[k]) if type(r[k]) is bool else n(r[k]) for k in ['present','originValid','axisPresent','anglePresent','xyzPresent','axis','angle','x','y','z','rescale'])+'}'
    fields=[b(d[k]) for k in ['vectors','shadeValid','shade','lightNumeric','lightNegative']]+[n(d['lightWhole']),n(d['lightFraction']),b(d['facesPresent']),faces,rotation]
    return 'element(E.er_decode(E.ERInput{'+','.join(fields)+'}))'


RENDER='''import Base
import ../../../host/minecraft/Elements.bend as E
import ../../../host/minecraft/LaterDecode.bend as L
def bit(v: Bool) -> String:
  Bool.pick(String,v,"1","0")
def rotation(v: L.LDRotation) -> String:
  match v:
    case L.LDRotation{m,a,b,x,y,z,r}: Nat.show(m) ++ "/" ++ Nat.show(a) ++ "/" ++ Nat.show(b) ++ "/" ++ Nat.show(x) ++ "/" ++ Nat.show(y) ++ "/" ++ Nat.show(z) ++ "/" ++ bit(r)
def element(v: Maybe<&2,E.EROutput>) -> String:
  match v:
    case None{}: "refused"
    case Some{E.EROutput{s,l,f,n,c,r}}: "ok:" ++ bit(s) ++ "/" ++ Nat.show(l) ++ "/" ++ Nat.show(f) ++ "/" ++ Nat.show(n) ++ "/" ++ Nat.show(c) ++ "|" ++ rotation(r)
def consumer(n: Nat) -> String:
  match n:
    case 0n: "0:"
    case 1n: "1:sprites"
    case _: "2:sprites,resolveSlot"
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);args=p.parse_args()
    captures=['elements-1.21.11-20261125T075852035159Z','element-consumer-1.21.11-20261125T080334688422Z']
    rows=[];answers=[];references=[];basis=[];original=[];bindings_all=[]
    targets=json.loads((HERE/'targets.json').read_text());target=next(t for t in targets['javaReferences'] if t['id']=='java-1.21.11-vanilla')
    static=json.loads((HERE/'host-api-1.21.11.json').read_text());static_capture=HERE/static['capture'];sr=json.loads((static_capture/'receipt.json').read_text());assert sr['clientSha256']==target['source']['clientSha256']
    artifact=static_capture/'invoke-facts.jsonl.gz';assert sha(artifact)==sr['compressedFactsSha256']
    static_records=[json.loads(line) for line in gzip.decompress(artifact.read_bytes()).splitlines()];class_hashes={r['entry']:r['sha256'] for r in static_records if r['kind']=='class'}
    for index,name in enumerate(captures):
        c=HERE/'evidence'/name;r=json.loads((c/'receipt.json').read_text());d=json.loads((c/'observed.json').read_text());bindings=json.loads((c/'bindings.json').read_text())
        assert r['target']=='java-1.21.11-vanilla' and r['observerErrors']==d['observerErrors']==0
        assert r['clientSha256']==target['source']['clientSha256'] and r['profile']['JAVA_VERSION'].startswith('21.')
        assert all(class_hashes[n]==digest for n,digest in r['selectedClassMembersSha256'].items())
        assert sha(c/'observed.json')==r['observedSha256'] and sha(c/'bindings.json')==r['bindingsSha256']
        assert all(v['exitCode']==0 and v['ownedGroupAbsent'] and not v['timedOut'] for v in r['commands'])
        for n,digest in r['sourcesSha256'].items():assert sha(c/n)==digest
        for stem,command in zip(['compile','execute'],r['commands']):
            for stream in ['stdout','stderr']:assert sha(c/(stem+'.'+stream))==command[stream+'Sha256']
        request_name='element12111_cases.json' if index==0 else 'element12111_consumer_cases.json'
        request=json.loads((c/request_name).read_text());assert [dict(id=v['case'],input=v['input']) for v in d['cases']]==request['cases']
        assert len(d['cases'])==(40 if index==0 else 51)
        for v in d['cases']:
            rows.append(project_element(v) if index==0 else project_consumer(v));answers.append(observed_element(v) if index==0 else observed_consumer(v,bindings));references.append(dict(capture=name,case=v['case']));original.append(v);bindings_all.append(bindings)
        basis+=sorted(c.iterdir())
    work=ROOT/'.build/minecraft/element12111-replay';work.mkdir(parents=True,exist_ok=True)
    data=work/'input.json';envelope=lambda rs:dict(schema=1,profile='java-1.21.11-vanilla',cases=rs)
    data.write_text(json.dumps(envelope(rows),indent=2)+'\n');env=dict(os.environ,LEAN_PATH=os.environ.get('LEAN_PATH',str(ROOT/'.build/formal')),BEND_NO_TELEMETRY='1')
    def lean_run(path):return subprocess.run([os.environ.get('LEAN','lean'),'--run',str(HERE/'ElementsCase.lean'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
    result=lean_run(data);assert result.returncode==0,result.stdout+result.stderr;lean_values=json.loads(result.stdout);assert lean_values==answers,list(zip(references,lean_values,answers))
    runner=work/'ElementsRun.bend';runner.write_text(RENDER+'def main() -> IO(Unit):\n  IO.write('+' ++ '.join(bend_row(r)+' ++ "\\n"' for r in rows)+')\n')
    result=subprocess.run([os.environ.get('BEND','bend'),str(runner)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60);assert result.returncode==0,result.stdout+result.stderr;bend_values=result.stdout.splitlines();assert bend_values==answers,list(zip(references,bend_values,answers))
    negatives=[dict(schema=2,profile='java-1.21.11-vanilla',cases=rows),dict(schema=1,profile='java-26.3-vanilla',cases=rows),envelope([dict(kind='other',data={})])]
    for i,k,v in [(0,'lightWhole',1001),(0,'lightFraction',10),(40,'axis',3),(0,'vectors','true')]:
        r=copy.deepcopy(rows[i]);r['data'][k]=v;negatives.append(envelope([r]))
    r=copy.deepcopy(rows[0]);r['data']['rotation']['angle']=361;negatives.append(envelope([r]))
    for i,request in enumerate(negatives):
        path=work/f'negative-{i}.json';path.write_text(json.dumps(request));assert lean_run(path).returncode==2
    changed=[]
    for case,field,value in [('reversed-extents','vectors',False),('null-face','faces',[]),('light-negative-fractional','lightWhole',1)]:
        index=next(i for i,ref in enumerate(references) if ref['case']==case);variant=copy.deepcopy(rows);variant[index]['data'][field]=value;changed.append((index,variant))
    index=next(i for i,r in enumerate(references) if r['case']=='unknown-cull');variant=copy.deepcopy(rows);variant[index]['data']['faces'][0]['cull']=True;changed.append((index,variant))
    index=next(i for i,r in enumerate(references) if r['case']=='null-111-north');variant=copy.deepcopy(rows);variant[index]['data']['dx']=False;changed.append((index,variant))
    for i,(_,variant) in enumerate(changed):
        path=work/f'premise-{i}.json';path.write_text(json.dumps(envelope(variant)));result=lean_run(path);assert result.returncode==0 and json.loads(result.stdout)!=answers
        path=work/f'Premise{i}.bend';path.write_text(RENDER+'def main() -> IO(Unit):\n  IO.write('+' ++ '.join(bend_row(r)+' ++ "\\n"' for r in variant)+')\n')
        result=subprocess.run([os.environ.get('BEND','bend'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60);assert result.returncode==0 and result.stdout.splitlines()!=answers
    observations=[('light-fractional',lambda r:r['value'].__setitem__('light',2)),('shade-false',lambda r:r['value'].__setitem__('shade',True)),('null-face',lambda r:r['value']['faces'].pop('NORTH')),('null-111-north',lambda r:r.update(outcome='returned',quads=0,adapterCalls=[])),('real-full',lambda r:r.update(adapterCalls=['sprites']))]
    for case,mutate in observations:
        i=next(i for i,r in enumerate(references) if r['case']==case);r=copy.deepcopy(original[i]);mutate(r)
        try:value=observed_element(r) if i<40 else observed_consumer(r,bindings_all[i])
        except (AssertionError,KeyError,ValueError):continue
        assert value!=answers[i]
    adapter_refusals=[dict(input={'unselected':0}),dict(input={'light_emission':1.99}),dict(input={'rotation':{'origin':[1,2,3],'x':20}})]
    for bad in adapter_refusals:
        try:project_element(bad)
        except ValueError:continue
        raise AssertionError('Unselected element profile silently projected')
    basis += [HERE/n for n in ['Elements.lean','Elements.bend','ElementsCase.lean','element_conformance.py','LaterDecode.lean','LaterDecode.bend','later_codec_conformance.py','targets.json','host-api-1.21.11.json']]+[artifact,static_capture/'receipt.json']
    report=dict(schema=1,status='passed',elementComparisons=40,controlledConsumerComparisons=51,decoderRefusals=len(negatives),adapterRefusals=len(adapter_refusals),changedPremises=len(changed),changedNativeFields=len(observations),
        projectedInputSha256=sha(data),comparisons=[dict(**r,result=a) for r,a in zip(references,answers)],basisSha256={str(p.relative_to(ROOT)):sha(p) for p in basis if p.is_file()},
        limits=['Element codec decisions/selected decoded fields,not complete JSON grammar,texture references or every face payload field.','Closed coordinate/number/rotation profiles;matrices retained,not predicted floating-point geometry.','Consumer uses one face and controlled ModelBaker/SpriteGetter;intercepts before texture resolution,not complete baking or rendering.','Null-face exception is conditional on selected area;not a full-game failure or provider/render defect claim.','No native client runtime,driver,other-platform or modded-provider qualification.'])
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','elementComparisons','controlledConsumerComparisons','decoderRefusals','changedPremises','changedNativeFields']}))


if __name__=='__main__':main()
