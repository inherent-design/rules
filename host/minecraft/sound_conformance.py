#!/usr/bin/env python3
"""Pure weighted-control and decoder-calibration replay;no JVM or audio startup."""
import argparse
import copy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];MASK=4294967295
CORE=['sound-1.21.1-20261125T125829545189Z','sound-1.21.4-20261125T130031789557Z','sound-1.21.5-20261125T130035057862Z','sound-1.21.11-20261125T130038220709Z','sound-26.3-20261125T130041025657Z']
DECODERS=['sound-decoder-1.21.1-20261125T130619159883Z','sound-decoder-1.21.4-20261125T130836072255Z','sound-decoder-1.21.5-20261125T130839300355Z','sound-decoder-1.21.11-20261125T130842720833Z','sound-decoder-26.3-20261125T130845461099Z']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def project(obs,plan):
    assert obs['schema']==1 and obs['observerErrors']==0 and obs['bootstrapContext']is True
    assert len(obs['cases'])==len(plan['cases'])==22
    inputs=[];measured=[]
    for raw,supplied in zip(obs['cases'],plan['cases']):
        assert raw['case']==supplied['id'] and raw['operation']==supplied['operation'] and raw['unexpected']is False
        entries=supplied['entries'];count=len(entries);op=['weight','select','preload'].index(supplied['operation'])
        assert all(1<=len(e['weights'])<=2 and all(type(v)is int and -2147483648<=v<=2147483647 for v in e['weights'])and type(e['preloadFails'])is bool for e in entries)
        assert len(raw['random'])<=1
        for field in ['weightsRead','preloadCalls']:
            assert len(raw[field])==count and all(type(v)is int and 0<=v<=2 for v in raw[field])
        occurrences=[0]*count
        for read in raw['reads']:
            i=read['entry']-1;assert 0<=i<count and read['ordinal']==occurrences[i]
            assert read['value']==entries[i]['weights'][min(occurrences[i],len(entries[i]['weights'])-1)];occurrences[i]+=1
        assert occurrences==raw['weightsRead']
        random=raw['random'];draw=0;bound=0
        if random:
            q=random[0];assert type(q['bound'])is int and -2147483648<=q['bound']<=2147483647;bound=q['bound']&MASK
            if q['error']=='NONE':assert type(q['draw'])is int and 0<=q['draw']<q['bound'];draw=q['draw']
            else:assert q['bound']<0 and q['error']=='java.lang.IllegalArgumentException'and q.get('draw')is None
        code={'NONE':0,'java.lang.IllegalArgumentException':1,'java.lang.IllegalStateException':2}[raw['error']]
        assert type(raw['returned'])is bool and raw['returned']==(code==0)
        if code==1:assert random and random[0]['bound']<0
        if code==2:assert raw['message'].startswith('authored-preload:')and op==2
        assert type(raw['selected'])is int and 0<=raw['selected']<=count and type(raw['fallback'])is bool
        assert raw['returnedNull']==(not raw['returned'] or op==2 or(op==1 and raw['selected']>0))
        row=dict(operation=op,draw=draw,entries=[dict(first=e['weights'][0]&MASK,second=e['weights'][-1]&MASK,fail=e['preloadFails'])for e in entries]);inputs.append(row)
        values={1:raw['selected'],2:int(raw['fallback']),3:code,4:bound,5:len(random)}
        if op==0:assert type(raw['weight'])is int;values[0]=raw['weight']&MASK
        elif random:values[0]=bound
        values.update({6+i:v for i,v in enumerate(raw['weightsRead']+raw['preloadCalls'])});measured.append(values)
    return inputs,measured


def decoder_expected(input):
    result=[]
    for entry in input['sounds']:
        if 'weight'not in entry:word=1
        elif type(entry['weight'])not in [int,float]:return False,[],'com.google.gson.JsonSyntaxException'
        else:word=int(Decimal(str(entry['weight'])))&MASK
        if word==0 or word>=2147483648:return False,[],'java.lang.IllegalArgumentException'
        result.append(word)
    return True,result,'NONE'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);a=p.parse_args();work=ROOT/'.build/minecraft/sound-replay';work.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=os.environ.get('LEAN_PATH',str(ROOT/'.build/formal')),BEND_NO_TELEMETRY='1')
    def lean_run(data,name):
        path=work/(name+'.json');path.write_text(json.dumps(data)+'\n')
        return subprocess.run([os.environ.get('LEAN','lean'),'--run',str(HERE/'SoundsCase.lean'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    def bend_run(rows,name):
        def linked(items):
            value='Nil{}'
            for item in reversed(items):value='Con{'+item+','+value+'}'
            return value
        calls=[]
        for r in rows:
            entries=linked(['M.SoundEntry{'+str(e['first'])+','+str(e['second'])+','+('True{}'if e['fail']else'False{}')+'}'for e in r['entries']])
            calls.append('M.sound_render(M.sound_run('+str(r['operation'])+'n,'+entries+','+str(r['draw'])+')) ++ "\\n"')
        path=work/(name+'.bend');path.write_text('import Base\nimport ../../../host/minecraft/Sounds.bend as M\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
        r=subprocess.run([os.environ.get('BEND','bend'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30);assert r.returncode==0,r.stdout+r.stderr
        return [[int(v)for v in line.split(':')]for line in r.stdout.splitlines()]
    def check(receipt,c):
        assert receipt['observerErrors']==0 and receipt['bootstrapContext']is True
        for file,h in receipt['sourcesSha256'].items():assert sha(c/file)==h
        assert sha(c/'observed.json')==receipt['observed.jsonSha256']and sha(c/'bindings.json')==receipt['bindingsSha256']
        if 'requestSha256'in receipt:assert sha(c/'request.json')==receipt['requestSha256']
        for stem,cmd in zip(['compile','execute'],receipt['commands']):
            assert cmd['exitCode']==0 and cmd['ownedGroupAbsent']and not cmd['timedOut']
            for stream in ['stdout','stderr']:assert sha(c/(stem+'.'+stream))==cmd[stream+'Sha256']
    excluded=json.loads((HERE/'evidence/sound-exclusions.json').read_text())['rows']
    assert len(excluded)==3 and [r['observerErrors']for r in excluded]==[4,4,0]
    assert not {r['capture']for r in excluded}&set(CORE+DECODERS)
    assert all(r['replacement']==CORE[0]for r in excluded)
    basis=[HERE/n for n in ['Sounds.lean','Sounds.bend','SoundsCase.lean','sound_cases.json','sound_conformance.py','evidence/sound-exclusions.json']]+[ROOT/'host/java'/n for n in ['Word32.lean','Word32.bend']]
    profiles=[];all_inputs=[];all_observed=[];all_predictions=[]
    canonical=json.loads((HERE/'sound_cases.json').read_text())
    for i,name in enumerate(CORE):
        c=HERE/'evidence'/name;receipt=json.loads((c/'receipt.json').read_text());check(receipt,c)
        plan=json.loads((c/'sound_cases.json').read_text());assert plan['cases']==canonical['cases']
        obs=json.loads((c/'observed.json').read_text());inputs,measured=project(obs,plan);data=dict(schema=1,contract='original-sound-weight-controls',cases=inputs)
        r=lean_run(data,'profile-'+str(i));assert r.returncode==0,r.stdout+r.stderr;predicted=json.loads(r.stdout);assert predicted==bend_run(inputs,'profile-'+str(i))
        for ordinal,(out,values)in enumerate(zip(predicted,measured)):
            for key,value in values.items():assert out[key]==value,(name,ordinal,key,out,value)
        all_inputs.append(inputs);all_observed.append(obs);all_predictions.append(predicted);basis += [f for f in c.iterdir()if f.is_file()]
        profiles.append(dict(target=receipt['target'],profile=receipt['profile'],weightedComparisons=22))
    calibration=[]
    for name in DECODERS:
        c=HERE/'evidence'/name;r=json.loads((c/'receipt.json').read_text());check(r,c);request=json.loads((c/'request.json').read_text());obs=json.loads((c/'observed.json').read_text())
        assert request['cases']==[]and obs['cases']==[]and request['decoderCases']==canonical['decoderCases']and len(obs['decoderCases'])==11
        for supplied,row in zip(request['decoderCases'],obs['decoderCases']):
            assert supplied['id']==row['case'];assert(row['decoded'],row['weights'],row['error'])==decoder_expected(supplied['input'])
        calibration.append(dict(target=r['target'],comparisons=11));basis += [f for f in c.iterdir()if f.is_file()]
    base=dict(schema=1,contract='original-sound-weight-controls',cases=all_inputs[0]);negatives=[dict(base,schema=2),dict(base,contract='audio-player'),dict(base,cases=base['cases']*3)]
    for field,value in [('operation',3),('draw',4294967296),('entries',[dict(first=4294967296,second=0,fail=False)]),('entries',[dict(first=0,second=0,fail=1)]),('entries',[dict(first=1,second=1,fail=False)]*17)]:
        row=copy.deepcopy(base['cases'][0]);row[field]=value;negatives.append(dict(base,cases=[row]))
    row=copy.deepcopy(base['cases'][0]);row['draw']=6;negatives.append(dict(base,cases=[row]))
    for i,bad in enumerate(negatives):assert lean_run(bad,'negative-'+str(i)).returncode==2
    changes=[]
    for case,field,value in [('static-0','selected',2),('overflow-negative','error','NONE'),('empty','fallback',False),('live-grow','selected',2),('preload-all','preloadCalls',[0,1,1])]:
        obs=copy.deepcopy(all_observed[0]);row=next(r for r in obs['cases']if r['case']==case);assert row[field]!=value;row[field]=value
        try:
            _,values=project(obs,canonical)
            for out,expected in zip(all_predictions[0],values):
                for k,v in expected.items():assert out[k]==v
        except AssertionError:changes.append(case)
        else:raise AssertionError('Changed outcome survived')
    report=dict(schema=1,status='passed-original-sound-weight-controls',profiles=profiles,weightedComparisons=110,decoderCalibrations=calibration,decoderComparisons=55,
        decoderRefusals=len(negatives),changedObservationControls=changes,leanLaws=10,bendLaws=6,basisSha256={str(f.relative_to(ROOT)):sha(f)for f in sorted(basis)},
        limits=['Source registry/bootstrap context explicit;no actual event registration,reference resolution,real leaf Sound selection,audio bytes,engine/device/playback/provider qualification.',
            'Models predict selected final fields/callback counts from authored first/second weights and observed original PRNG draws;no PRNG proof or arbitrary callback/concurrency contract.',
            'Aggregate weight is compared only when returned or observed as random bound;preload/no-draw hidden totals are excluded.',
            'Decoder calibration is an independent finite Decimal/truncation/word-conversion check,not a Lean/Bend proof of Gson or all JSON grammar.',
            'Earlier3decoder rows/profile remain retained but are not counted twice in the55extended decoder comparisons.',
            'Native macOS/JDK21/25 only;ordinary replay launches Lean/Bend and reads retained data,never a JVM or studied program.'])
    if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','weightedComparisons','decoderComparisons','decoderRefusals','changedObservationControls']}))


if __name__=='__main__':main()
