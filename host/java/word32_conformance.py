#!/usr/bin/env python3
"""Pure32bit models against retained Java17/21/25 arithmetic;no JVM launch."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];MASK=4294967295
CAPTURES=['word32-17-20261125T130032560461Z','word32-21-20261125T130032934409Z','word32-25-20261125T130033274429Z']
PAIRS=[(2147483647,1),(2147483647,2147483647),(0,1),(-2147483648,1),(0,-2147483648),(1073741824,1073741824),(-1,-1),(1,2),(-2,4),(-2147483648,2147483647)]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def project(obs):
    assert obs['schema']==1 and len(obs['rows'])==10;inputs=[];expected=[]
    for index,(r,pair)in enumerate(zip(obs['rows'],PAIRS)):
        assert type(r['index'])is int and r['index']==index and(r['a'],r['b'])==pair
        assert all(type(r[k])is int and -2147483648<=r[k]<=2147483647 for k in ['a','b','sum','difference'])
        assert all(type(r[k])is int and 0<=r[k]<=MASK for k in ['sumBits','differenceBits'])
        assert r['sumBits']==r['sum']&MASK and r['differenceBits']==r['difference']&MASK
        assert type(r['negative'])is bool and type(r['positive'])is bool
        inputs.append(dict(a=r['a']&MASK,b=r['b']&MASK));expected.append([r['sumBits'],r['differenceBits'],int(r['negative']),int(r['positive'])])
    return inputs,expected


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);a=p.parse_args();work=ROOT/'.build/java-word32/replay';work.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=os.environ.get('LEAN_PATH',str(ROOT/'.build/formal')),BEND_NO_TELEMETRY='1')
    def lean_run(data,name):
        path=work/(name+'.json');path.write_text(json.dumps(data)+'\n');return subprocess.run([os.environ.get('LEAN','lean'),'--run',str(HERE/'Word32Case.lean'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    def bend_run(rows):
        calls=[]
        for r in rows:
            x=str(r['a']);y=str(r['b']);total='U32.add('+x+','+y+')';calls.append('U32.show('+total+') ++ ":" ++ U32.show(U32.sub('+x+','+y+')) ++ ":" ++ Nat.show(Bool.pick(Nat,J.jw_negative('+total+'),1n,0n)) ++ ":" ++ Nat.show(Bool.pick(Nat,J.jw_positive('+total+'),1n,0n)) ++ "\\n"')
        path=work/'Cases.bend';path.write_text('import Base\nimport ../../../host/java/Word32.bend as J\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
        r=subprocess.run([os.environ.get('BEND','bend'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30);assert r.returncode==0,r.stdout+r.stderr
        return [[int(v)for v in line.split(':')]for line in r.stdout.splitlines()]
    basis=[HERE/n for n in ['Word32.lean','Word32.bend','Word32Case.lean','word32_conformance.py']];profiles=[];raw=[];results=[]
    for name,feature in zip(CAPTURES,[17,21,25]):
        c=HERE/'evidence'/name;r=json.loads((c/'receipt.json').read_text());assert r['cases']==10 and r['feature']==feature and r['profile']['JAVA_VERSION'].startswith(str(feature)+'.')
        for f,h in r['sourcesSha256'].items():assert sha(c/f)==h
        for stem,cmd in zip(['compile','execute'],r['commands']):
            assert cmd['exitCode']==0 and cmd['ownedGroupAbsent']and not cmd['timedOut']
            for stream in ['stdout','stderr']:assert sha(c/(stem+'.'+stream))==cmd[stream+'Sha256']
        assert sha(c/'execute.stdout')==r['observedSha256'];obs=json.loads((c/'execute.stdout').read_text());inputs,expected=project(obs)
        out=lean_run(dict(schema=1,rows=inputs),str(feature));assert out.returncode==0,out.stdout+out.stderr;predicted=json.loads(out.stdout);assert predicted==expected==bend_run(inputs)
        profiles.append(dict(feature=feature,profile=r['profile'],comparisons=10));raw.append(obs);results.append(predicted);basis += [f for f in c.iterdir()if f.is_file()]
    assert raw[0]==raw[1]==raw[2]
    rows,_=project(raw[0]);bad=[dict(schema=2,rows=rows),dict(schema=1,rows=rows*7),dict(schema=1,rows=[dict(a=4294967296,b=0)]),dict(schema=1,rows=[dict(a=True,b=0)]),dict(schema=1,rows=[dict(a=-1,b=0)])]
    for i,v in enumerate(bad):assert lean_run(v,'negative-'+str(i)).returncode==2
    mutations=[]
    for key in ['sumBits','differenceBits','negative','positive']:
        obs=copy.deepcopy(raw[0]);r=obs['rows'][0];r[key]=(not r[key])if type(r[key])is bool else 7
        try:assert project(obs)[1]==results[0]
        except AssertionError:mutations.append(key)
        else:raise AssertionError('Changed arithmetic observation admitted')
    report=dict(schema=1,status='passed-authored-java-word32',profiles=profiles,comparisons=30,leanLaws=8,bendLaws=6,decoderRefusals=len(bad),changedObservationControls=mutations,
        basisSha256={str(f.relative_to(ROOT)):sha(f)for f in sorted(basis)},limits=['Selected runtime add/subtract and signed/bit interpretations only;not arbitrary numeric parser,multiplication,checked arithmetic,PRNG or JVM proof.',
        'Native macOS/JDK17/21/25 observations;source-language portability and native Windows/Linux evidence remain distinct.',
        'The public receipt qualifies incidental JVM/stream/native effects rather than asserting process-wide absence of JNI.'])
    if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','comparisons','decoderRefusals','changedObservationControls']}))


if __name__=='__main__':main()
