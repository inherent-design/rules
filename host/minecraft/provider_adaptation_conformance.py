#!/usr/bin/env python3
"""Retained adapter/model/matrix checks; no Java, game, loader, or native compiler launch."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
BASE='provider-policy-20261125T174555987623Z';MATRIX='provider-matrix-20261125T180956818393Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def finite32(value):
    if type(value)not in [int,float]:return False
    try:return math.isfinite(struct.unpack('>f',struct.pack('>f',value))[0])
    except (OverflowError,struct.error):return False


def euler(element):
    return isinstance(element,dict)and isinstance(element.get('rotation'),dict)and not any(k in element['rotation']for k in ['axis','angle'])and any(k in element['rotation']for k in ['x','y','z'])


def project(value):
    ready=isinstance(value,dict)and isinstance(value.get('elements'),list)and not any(k in value for k in ['loader','parent','transform'])
    if not ready:return dict(ready=False,elements=None)
    assert len(value['elements'])<=132,'Outside selected research array.'
    result=[]
    for element in value['elements']:
        r=dict.fromkeys(['scale','cull','origin','numeric']);r['kind']=0 if not isinstance(element,dict)else 2 if euler(element)else 1
        if r['kind']==2:
            rotation=element['rotation'];scale=rotation.get('rescale')
            r['scale']=0 if'rescale'not in rotation else 1 if scale is False else 2 if scale is True else 3
            faces=element.get('faces',{});assert isinstance(faces,dict),'Unmodeled faces form.'
            r['cull']=any(isinstance(face,dict)and'cullface'in face for face in faces.values())
            origin=rotation.get('origin');r['origin']=0 if not isinstance(origin,list)or len(origin)!=3 else 2 if all(finite32(v)for v in origin)else 1
            angles=[rotation.get(k,0)for k in ['x','y','z']];r['numeric']=all(finite32(v)for v in angles)
            if r['origin']==2 and r['numeric']:
                assert all(abs(v)<=64 for v in origin)and all(abs(v)<=360 for v in angles),'Outside selected bounded matrix inputs.'
        result.append(r)
    return dict(ready=True,elements=result)


ERRORS={'Multi-axis model exceeds 128 elements':2,'Expected model element object':3,
    'Expected boolean multi-axis rescale':4,'Multi-axis rescale needs explicit qualification':5,
    'Multi-axis cull faces need explicit qualification':6,'Expected three finite rotation-origin coordinates':7,
    'Expected finite numeric model rotation':8}


def observe(spec,raw):
    assert raw['id']==spec['id']and raw['inputBytesUnchanged']is True
    if raw['status']=='threw':
        assert raw['errorClass']=='JsonParseException'and raw['message']in ERRORS
        return [ERRORS[raw['message']],0,0]
    assert raw['status']=='returned'and type(raw['sameObject'])is bool
    if raw['sameObject']:
        # The frozen producer's default Gson serializer omits JsonNull object members.
        # Only this selected null input has no output field; the identity flag remains observed.
        if spec['input']is None:assert 'output'not in raw
        else:assert raw['output']==spec['input']
        return [0,0,0]
    output=raw['output'];assert output['loader']=='neoforge:composite'
    children=output['children'];rotated=[k for k in children if k.startswith('rotated_')]
    assert rotated==['rotated_'+str(i)for i in range(len(rotated))]
    assert set(children)==set(rotated)|({'legacy'}if'legacy'in children else set())
    legacy=len(children['legacy']['elements'])if'legacy'in children else 0
    return [1,len(rotated),legacy]


def check_output(spec,raw):
    if raw['status']!='returned'or raw['sameObject']:return 0,0
    source=spec['input'];output=raw['output'];expected=copy.deepcopy(source)
    expected.pop('elements');expected.pop('groups',None);expected['loader']='neoforge:composite';expected['children']=output['children']
    assert output==expected,'Root fields differ.'
    copied={k:v for k,v in source.items()if k in ['textures','ambientocclusion','gui_light','render_type']}
    rotating=[e for e in source['elements']if euler(e)];legacy=[e for e in source['elements']if not euler(e)]
    matrix_count=point_count=0
    for i,element in enumerate(rotating):
        child=output['children']['rotated_'+str(i)];body=copy.deepcopy(element);body.pop('rotation')
        assert set(child)==set(copied)|{'elements','transform'}and child['elements']==[body]
        assert all(child[k]==v for k,v in copied.items())
        matrix=child['transform']['matrix'];assert len(matrix)==3 and all(len(r)==4 for r in matrix)
        assert all(type(v)in [int,float]and math.isfinite(v)for row in matrix for v in row)
        rotation=element['rotation'];pivot=[v/16 for v in rotation['origin']];rx,ry,rz=[math.radians(rotation.get(k,0))for k in ['x','y','z']]
        # Independent double point rotations X then Y then Z,not JOML or copied matrix code.
        for point in [(0,0,0),(1,0,0),(0,1,0),(0,0,1),tuple(pivot)]:
            x,y,z=[point[j]-pivot[j]for j in range(3)]
            y,z=y*math.cos(rx)-z*math.sin(rx),y*math.sin(rx)+z*math.cos(rx)
            x,z=x*math.cos(ry)+z*math.sin(ry),-x*math.sin(ry)+z*math.cos(ry)
            x,y=x*math.cos(rz)-y*math.sin(rz),x*math.sin(rz)+y*math.cos(rz)
            wanted=[x+pivot[0],y+pivot[1],z+pivot[2]]
            actual=[sum(matrix[j][k]*point[k]for k in range(3))+matrix[j][3]for j in range(3)]
            assert all(abs(a-b)<=2e-6 for a,b in zip(actual,wanted,strict=True)),'Matrix point transform differs.'
            point_count+=1
        matrix_count+=1
    if legacy:assert output['children']['legacy']==copied|dict(elements=legacy)
    return matrix_count,point_count


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private',action='store_true',help='Compare original owner-local captures instead of their public exports.')
    args=parser.parse_args()
    captures=[(ROOT/'.build/minecraft'if args.private else HERE/'evidence')/n for n in [BASE,MATRIX]];specs=[];observed=[]
    for cap in captures:
        r=json.loads((cap/'receipt.json').read_text());request=json.loads((cap/'request.json').read_text());raw=json.loads((cap/'observed.json').read_text())
        assert sha(cap/'request.json')==r['requestSha256']and sha(cap/'observed.json')==r['observed.jsonSha256']and raw['observerErrors']==0
        for n,h in r['sourcesSha256'].items():assert sha(cap/n)==h
        stems=['compile','execute']if cap.name==BASE else['execute']
        for stem,c in zip(stems,r['commands'],strict=True):
            assert c['exitCode']==0 and c['ownedGroupAbsent']and not c['timedOut']
            for channel in ['stdout','stderr']:assert sha(cap/(stem+'.'+channel))==c[channel+'Sha256']
        assert [s['id']for s in request['adaptation']]==[s['id']for s in raw['adaptation']]
        specs+=request['adaptation'];observed+=raw['adaptation']
    inputs=[project(s['input'])for s in specs];wanted=[observe(s,r)for s,r in zip(specs,observed,strict=True)]
    work=ROOT/'.build/minecraft/provider-adaptation-replay';work.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=os.environ.get('LEAN_PATH',str(ROOT/'.build/formal')),BEND_NO_TELEMETRY='1')
    def lean(data,label):
        p=work/(label+'.json');p.write_text(json.dumps(data)+'\n')
        return subprocess.run([os.environ.get('LEAN','lean'),'--run',str(HERE/'ProviderAdaptationCase.lean'),str(p)],cwd=ROOT,env=env,text=True,capture_output=True,timeout=30)
    def bend(rows,label):
        calls=[]
        for row in rows:
            es=[]
            for e in row['elements']or[]:
                es.append('M.PAElement{'+','.join([str(e['kind'])+'n',str(e['scale']or 0)+'n','True{}'if e['cull']else'False{}',str(e['origin']or 0)+'n','True{}'if e['numeric']else'False{}'])+'}')
            calls.append('show(M.pa_evaluate('+('True{}'if row['ready']else'False{}')+',['+','.join(es)+'])) ++ "\\n"')
        p=work/(label+'.bend');p.write_text('import Base\nimport ../../../host/minecraft/ProviderAdaptation.bend as M\ndef show(xs: List<&2,Nat>) -> String:\n  match xs:\n    case Nil{}: ""\n    case Con{h,t}: Nat.show(h) ++ "," ++ show(t)\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
        result=subprocess.run([os.environ.get('BEND','bend'),str(p)],cwd=ROOT,env=env,text=True,capture_output=True,timeout=30);assert result.returncode==0,result.stdout+result.stderr
        return [[int(v)for v in line.rstrip(',').split(',')]for line in result.stdout.splitlines()]
    dto=dict(schema=1,contract='bounded-compat-euler-adaptation-v1',rows=inputs)
    result=lean(dto,'plan');assert result.returncode==0,result.stdout+result.stderr
    assert json.loads(result.stdout)==wanted==bend(inputs,'plan')
    matrix_count=point_count=0
    for s,r in zip(specs,observed,strict=True):
        m,p=check_output(s,r);matrix_count+=m;point_count+=p
    good=inputs[next(i for i,s in enumerate(specs)if s['id']=='zero-euler')]
    bad=[dict(dto,schema=2),dict(dto,contract='rendered-parity'),dict(dto,rows=[good]*65),dict(dto,rows=[dict(ready=None,elements=None)]),dict(dto,rows=[dict(ready=True,elements=None)])]
    for field,value in [('kind',None),('kind',3),('scale',None),('scale',4),('cull',None),('origin',None),('origin',3),('numeric',None),('cull',1)]:
        changed=copy.deepcopy(good);changed['elements'][0][field]=value;bad.append(dict(dto,rows=[changed]))
    bad.append(dict(dto,rows=[dict(ready=True,elements=[good['elements'][0]]*133)]))
    for i,data in enumerate(bad):assert lean(data,'bad-'+str(i)).returncode==2
    unused=[dict(ready=False,elements=None),dict(ready=True,elements=[dict.fromkeys(['kind','scale','cull','origin','numeric'])|dict(kind=1)]),dict(ready=True,elements=[dict.fromkeys(['kind','scale','cull','origin','numeric'])|dict(kind=2,scale=3)])]
    result=lean(dict(dto,rows=unused),'unused');assert result.returncode==0 and json.loads(result.stdout)==bend(unused,'unused')
    controls=[]
    for identity,kind in [('gated-parent','output'),('zero-euler','input-preservation'),('rescale-true','message'),('mixed-modern-legacy','legacy'),('mixed-positive','matrix')]:
        index=next(i for i,s in enumerate(specs)if s['id']==identity);changed=copy.deepcopy(observed[index])
        if kind=='output':changed['output']['parent']='study:forged'
        elif kind=='input-preservation':changed['inputBytesUnchanged']=False
        elif kind=='message':changed['message']='unqualified error'
        elif kind=='legacy':changed['output']['children']['legacy']['elements']=[]
        else:changed['output']['children']['rotated_0']['transform']['matrix'][0][0]+=.01
        try:
            assert observe(specs[index],changed)==wanted[index];check_output(specs[index],changed)
        except AssertionError:controls.append(identity+'/'+kind)
        else:raise AssertionError('Changed adapter observation admitted.')
    report=dict(schema=1,status='passed-retained-original-adaptation',privateCapture=args.private,nativeComparisons=len(specs),leanLaws=14,bendLaws=8,decoderRefusals=len(bad),unneededUnknownExamples=3,changedObservationControls=controls,matrices=matrix_count,pointComparisons=point_count,tolerance=2e-6,
        basisSha256={str(p.relative_to(ROOT)):sha(p)for p in [*[cap/n for cap in captures for n in ['receipt.json','request.json','observed.json']],*[HERE/n for n in ['ProviderAdaptation.lean','ProviderAdaptation.bend','ProviderAdaptationCase.lean','provider_adaptation_conformance.py']]]},
        limits=['Selected bounded primitive facts from raw requests;shared projection fidelity is not proved.',
            'Numeric-success projection admits finite angles within360degrees/origin within64units;nonfinite constructed-matrix branch remains source-only.',
            'Matrix comparisons use independent double point rotations with tolerance;not formal geometry/render/culling/normal equivalence.',
            'Noop is unchanged by this helper,not validated or accepted downstream;error count slots mean no returned conversion counts,not zero allocation.',
            'inputBytesUnchanged is Gson serialization before/after,not raw file bytes or no intervening mutation.'])
    (work/'conformance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in ['basisSha256','limits']}))


if __name__=='__main__':main()
