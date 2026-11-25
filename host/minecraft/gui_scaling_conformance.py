#!/usr/bin/env python3
"""Pure retained GUI codec/model comparisons; no Java, GUI, texture or renderer."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CAPTURES=['gui-scaling-1.21.1-20261125T152702235201Z','gui-scaling-1.21.4-20261125T152725323923Z',
          'gui-scaling-1.21.5-20261125T152726713563Z','gui-scaling-1.21.11-20261125T152728176661Z','gui-scaling-26.3-20261125T152729064759Z']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def project(cases,modern):
    rows=[]
    for item in cases:
        d=item['input'];kind=['stretch','tile','nine_slice'].index(d['type'])
        w=d.get('width',0);h=d.get('height',0);border=d.get('border',dict(left=0,top=0,right=0,bottom=0))
        sides=[border]*4 if type(border)is int else [border[k]for k in ['left','top','right','bottom']]
        assert all(type(n)is int and -2147483648<=n<=2147483647 for n in [w,h,*sides])
        flag=d.get('stretch_inner',False);assert type(flag)is bool
        # The admitted scalar negative in a stretch-only extra field is ignored;
        # all selected tile/nine-slice dimensions are nonnegative integer tokens.
        assert kind==0 or w>=0 and h>=0
        rows.append(dict(kind=kind,width=abs(w),height=abs(h),left=abs(sides[0]),top=abs(sides[1]),right=abs(sides[2]),bottom=abs(sides[3]),
                         nonnegative=all(n>=0 for n in sides),scalar=type(border)is int,modern=modern,stretch=flag))
    return dict(schema=1,contract='selected-gui-scaling-integers',rows=rows)


def observed(cases,raw,modern):
    assert len(cases)==len(raw)==14
    outcomes=[];dimension_pairs=0
    for item,row in zip(cases,raw):
        assert item['id']==row['id']and not row.get('observerError')and type(row['accepted'])is bool
        assert row['partial']is False
        if not row['accepted']:
            assert 'fields'not in row;outcomes.append(0);continue
        d=item['input'];fields=row['fields'];kind=d['type']
        if kind=='stretch':assert fields=={};outcomes.append(1);continue
        expected_keys={'width','height'}|({'stretchInner'}if modern and kind=='nine_slice'else set())
        assert set(fields)==expected_keys
        assert type(fields['width'])is int and type(fields['height'])is int
        assert(fields['width'],fields['height'])==(d['width'],d['height']);dimension_pairs+=1
        if kind=='tile':outcomes.append(2)
        elif not modern:outcomes.append(3)
        else:
            assert type(fields['stretchInner'])is bool
            outcomes.append(5 if fields['stretchInner']else 4)
    return outcomes,dimension_pairs


def main():
    work=ROOT/'.build/minecraft/gui-scaling-replay';work.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=os.environ.get('LEAN_PATH',str(ROOT/'.build/formal')),BEND_NO_TELEMETRY='1')
    def lean(data,label):
        p=work/(label+'.json');p.write_text(json.dumps(data)+'\n')
        return subprocess.run([os.environ.get('LEAN','lean'),'--run',str(HERE/'GuiScalingCase.lean'),str(p)],env=env,cwd=ROOT,capture_output=True,text=True,timeout=30)
    def bend(rows,label):
        calls=[]
        for r in rows:
            args=[str(r['kind'])+'n']+[str(r[k])for k in ['width','height','left','top','right','bottom']]+['True{}'if r[k]else'False{}'for k in ['nonnegative','scalar','modern','stretch']]
            calls.append('Nat.show(M.gui_scaling_eval('+','.join(args)+')) ++ "\\n"')
        p=work/(label+'.bend');p.write_text('import Base\nimport ../../../host/minecraft/GuiScaling.bend as M\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
        r=subprocess.run([os.environ.get('BEND','bend'),str(p)],env=env,cwd=ROOT,capture_output=True,text=True,timeout=30);assert r.returncode==0,r.stdout+r.stderr
        return [int(x)for x in r.stdout.splitlines()]
    basis=[HERE/n for n in ['GuiScaling.lean','GuiScaling.bend','GuiScalingCase.lean','gui_scaling_conformance.py']]+[ROOT/'host/java/Word32.lean',ROOT/'host/java/Word32.bend']
    profiles=[];requests=[];observations=[];all_cases=[];predictions=[];dimensions=0;counterexamples=[]
    for i,name in enumerate(CAPTURES):
        cap=HERE/'evidence'/name;receipt=json.loads((cap/'receipt.json').read_text());document=json.loads((cap/'cases.json').read_text());cases=document['cases'];raw=json.loads((cap/'observed.json').read_text());modern=i!=0
        assert receipt['rows']==14 and receipt['observerErrors']==0 and document['target']==receipt['target']
        assert sha(cap/'cases.json')==receipt['casesSha256']and sha(cap/'observed.json')==receipt['observed.jsonSha256']
        for n,h in receipt['sourcesSha256'].items():assert sha(cap/n)==h
        for stem,c in zip(['compile','execute'],receipt['commands']):
            assert c['exitCode']==0 and c['ownedGroupAbsent']and not c['timedOut']
            for channel in ['stdout','stderr']:assert sha(cap/(stem+'.'+channel))==c[channel+'Sha256']
        data=project(cases,modern);expected,pairs=observed(cases,raw,modern);r=lean(data,str(i));assert r.returncode==0,r.stdout+r.stderr
        actual=json.loads(r.stdout);assert actual==expected==bend(data['rows'],str(i))
        for item,row,code in zip(cases,data['rows'],expected):
            if row['kind']==2 and code and(row['left']+row['right']>=row['width']or row['top']+row['bottom']>=row['height']):counterexamples.append(dict(target=receipt['target'],case=item['id']))
        dimensions+=pairs;profiles.append(dict(target=receipt['target'],codecOutcomes=14,dimensionPairs=pairs))
        requests.append(data);observations.append(raw);all_cases.append(cases);predictions.append(actual);basis.extend(p for p in cap.iterdir()if p.is_file())
    base=requests[0];row=base['rows'][4];negatives=[dict(base,schema=2),dict(base,contract='renderer'),dict(base,rows=base['rows']*10)]
    for change in [dict(kind=3),dict(width=2147483648),dict(left=-1),dict(nonnegative=1),dict(modern=1),dict(stretch=None),dict(right=2)]:negatives.append(dict(base,rows=[row|change]))
    for i,bad in enumerate(negatives):assert lean(bad,'negative-'+str(i)).returncode==2
    changed=[]
    for profile,index,key in [(0,9,'accepted'),(4,13,'stretchInner'),(0,1,'width'),(0,7,'id'),(0,6,'partial')]:
        raw=copy.deepcopy(observations[profile]);r=raw[index]
        if key=='accepted':r[key]=not r[key]
        elif key=='stretchInner':r['fields'][key]=not r['fields'][key]
        elif key=='width':r['fields'][key]+=1
        elif key=='id':r[key]='changed-id'
        else:r[key]=not r[key]
        try:assert observed(all_cases[profile],raw,profile!=0)[0]==predictions[profile]
        except AssertionError:changed.append(str(profile)+':'+str(index)+':'+key)
        else:raise AssertionError('Changed native GUI observation admitted')
    assert len(counterexamples)==15
    report=dict(schema=1,status='passed-original-gui-scaling-selected-integers',profiles=profiles,codecComparisons=70,dimensionPairs=dimensions,
        leanLaws=15,bendLaws=8,decoderRefusals=len(negatives),changedObservationControls=changed,naturalAdditionCounterexamples=counterexamples,
        basisSha256={str(p.relative_to(ROOT)):sha(p)for p in sorted(basis)},
        limits=['Original codec corpus only;no actual GUI/texture/provider/renderer or full JSON/numeric codec proof.',
                'Old natural-dimension model remains scoped to its non-overflow fixtures;this model adds signedJava32 guard arithmetic.',
                'Border clamping,UV selection,destination and submission/lifetime are source-only;accepted overflow is not proof of a rendered defect.',
                'Dimension-pair identities are independent retained checks;model codes predict variant/admission/observed stretch flag only.',
                'Native macOS/JDK21/25 only;unbounded constructors,malformed full grammar,all hosts and provider coexistence remain open.'])
    (HERE/'evidence/gui-scaling-conformance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','codecComparisons','dimensionPairs','decoderRefusals','changedObservationControls']}))


if __name__=='__main__':main()
