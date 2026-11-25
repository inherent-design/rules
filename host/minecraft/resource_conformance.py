#!/usr/bin/env python3
"""Pure replay of original folder-resource observations, never game execution."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def metadata(text):
    if text is None:return 0
    if text=='{malformed':return 3
    x=json.loads(text)
    if set(x)!={'texture'} or not set(x['texture'])<= {'blur','clamp'}:raise ValueError('Other metadata outside fixture')
    x=x['texture']
    if any(type(v) is not bool for v in x.values()):raise ValueError('Nonboolean metadata outside this band')
    bits=int(x.get('blur',False))+2*int(x.get('clamp',False))
    if bits not in [1,2]:raise ValueError('Other valid flag combination outside this band')
    return bits


def decode(row,files):
    if len(row['order'])!=2:raise ValueError('Only two generated folder packs in native band')
    if row['query'] not in ['fixture:defs/entry.txt','fixture:defs/../canary.txt','fixture:']:raise ValueError('Other query outside physical-path fixtures')
    packs=[];source_ids={}
    for name in row['order']:
        key=1 if name.endswith('-low') else 2 if name.endswith('-high') else 0
        if key==0:raise ValueError('Other generated source')
        source_ids[name]=key
        body=files.get(name+'/assets/fixture/defs/entry.txt')
        if body not in [None,'LOW','HIGH','{malformed']:raise ValueError('Other body identity')
        meta=metadata(files.get(name+'/assets/fixture/defs/entry.txt.mcmeta'))
        root=json.loads(files[name+'/pack.mcmeta'])
        rules=root.get('filter',{}).get('block',[])
        if len(rules)>1:raise ValueError('Multiple filter entries require separate namespace/path existential semantics;not this native fixture')
        def blocks(path):
            return any(re.fullmatch(r.get('namespace','.*'),'fixture') is not None and re.fullmatch(r.get('path','.*'),path) is not None for r in rules)
        packs.append(dict(id=key,body=[None,'LOW','HIGH','{malformed'].index(body),metadata=meta,
            blocksBody=blocks('defs/entry.txt'),blocksMetadata=blocks('defs/entry.txt.mcmeta')))
    return dict(packs=packs,pathAdmitted=row['query']=='fixture:defs/entry.txt'),source_ids


def observed(row,ids):
    def resource(r):
        if r is None:return 'none'
        source=ids[r['source']];body=['LOW','HIGH','{malformed'].index(r['content'])+1
        if 'metadataError' in r:
            assert r['metadataError']['exception']=='com.google.gson.JsonParseException' and not r['metadataError']['observerError']
            meta=3
        elif not r['textureMetadata']:meta=0
        else:
            meta=int(r['blur'])+2*int(r['clamp']);assert meta in [1,2]
        return f'{source}:{body}:{meta}'
    assert 'error' not in row
    return resource(row['single'])+'|'+','.join(resource(x) for x in row['stack'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    work=ROOT/'.build/minecraft/resource-replay';work.mkdir(parents=True,exist_ok=True)
    basis=[HERE/x for x in ['ResourceSelection.lean','ResourceSelection.bend','ResourceSelectionCase.lean','resource_conformance.py','resource-selections.json']]
    rows=[];answers=[];references=[];native=[]
    for capture in sorted((HERE/'evidence').glob('resources-*')):
        receipt=json.loads((capture/'receipt.json').read_text());cases=json.loads((capture/'cases.json').read_text());files=json.loads((capture/'files.json').read_text());observations=json.loads((capture/'observed.json').read_text())
        for name,key in [('cases.json','publicCasesSha256'),('files.json','publicFilesSha256'),('observed.json','observedSha256')]:assert sha(capture/name)==receipt[key]
        assert receipt['fixturesUnchanged'] and receipt['fixturesBefore']==receipt['fixturesAfter']
        assert set(files)==set(receipt['fixturesBefore'])
        for p,text in files.items():assert hashlib.sha256(text.encode()).hexdigest()==receipt['fixturesBefore'][p]
        for n,h in receipt['sourceSha256'].items():assert sha(capture/n)==h
        for name,command in zip(['compile','execute'],receipt['commands']):
            for stream in ['stdout','stderr']:assert sha(capture/(name+'.'+stream))==command[stream+'Sha256']
        assert all(x['exitCode']==0 and x['ownedGroupAbsent'] and not x['timedOut'] for x in receipt['commands'])
        assert [x['id'] for x in cases]==[x['id'] for x in observations]
        native.append(dict(capture=capture.name,scenarios=len(cases)))
        basis+=sorted(x for x in capture.iterdir() if x.is_file())
        for c,o in zip(cases,observations):
            r,ids=decode(c,files);rows.append(r);answers.append(observed(o,ids));references.append(dict(capture=capture.name,case=c['id']))
    assert len(rows)==36
    env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1');lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend')
    path=work/'inputs.json';path.write_text(json.dumps(dict(schema=1,cases=rows),indent=2)+'\n')
    def lean_run(p):return subprocess.run([lean,'--run',str(HERE/'ResourceSelectionCase.lean'),str(p)],cwd=ROOT,env=env,capture_output=True,text=True)
    result=lean_run(path);assert result.returncode==0,result.stdout+result.stderr
    lean_actual=json.loads(result.stdout);assert lean_actual==answers,[(references[i],a,b) for i,(a,b) in enumerate(zip(lean_actual,answers)) if a!=b]
    bit=lambda x:'True{}' if x else 'False{}'
    def pack(p):return 'M.Pack{'+','.join([str(p[k])+'n' for k in ['id','body','metadata']]+[bit(p[k]) for k in ['blocksBody','blocksMetadata']])+'}'
    calls=[]
    for r in rows:
        ps='Nil{}'
        for p in reversed(r['packs']):ps='Con{'+pack(p)+','+ps+'}'
        calls.append('render('+ps+','+bit(r['pathAdmitted'])+') ++ "\\n"')
    runner=work/'ResourceCase.bend'
    runner.write_text('''import Base
import ../../../host/minecraft/ResourceSelection.bend as M
def item(r: M.Resource) -> String:
  match r:
    case M.Resource{s,b,m}: Nat.show(s) ++ ":" ++ Nat.show(b) ++ ":" ++ Nat.show(m)
def optional(r: Maybe<&2,M.Resource>) -> String:
  match r:
    case None{}: "none"
    case Some{r}: item(r)
def items(xs: List<&2,M.Resource>) -> String:
  match xs:
    case Nil{}: ""
    case Con{r,rest}:
      match rest:
        case Nil{}: item(r)
        case Con{next,tail}: item(r) ++ "," ++ items(Con{next,tail})
def render(+packs: List<&2,M.Pack>, +admitted: Bool) -> String:
  optional(M.single(packs,admitted)) ++ "|" ++ items(M.stack(packs,admitted))
def main() -> IO(Unit):
  IO.write('''+' ++ '.join(calls)+')\n')
    result=subprocess.run([bend,str(runner)],cwd=ROOT,env=env,capture_output=True,text=True);assert result.returncode==0,result.stdout+result.stderr
    bend_actual=result.stdout.splitlines();assert bend_actual==answers
    negative=[dict(schema=2,cases=rows),dict(schema=1,cases=[dict(rows[0],pathAdmitted='true')])]
    for field,value in [('id',0),('id',3),('body',4),('metadata',4)]:
        bad=copy.deepcopy(rows[0]);bad['packs'][0][field]=value;negative.append(dict(schema=1,cases=[bad]))
    bad=copy.deepcopy(rows[0]);bad['packs']=bad['packs']*5;negative.append(dict(schema=1,cases=[bad]))
    for i,n in enumerate(negative):
        p=work/f'negative-{i}.json';p.write_text(json.dumps(n));assert lean_run(p).returncode==2
    unsupported=[]
    unsupported.append((dict(cases[0],query='fixture:other'),files))
    multi=copy.deepcopy(files);high=cases[0]['order'][1];root=json.loads(multi[high+'/pack.mcmeta'])
    root['filter']={'block':[{'namespace':'fixture','path':'defs/other.txt'},{'namespace':'other','path':'defs/entry.txt'}]}
    multi[high+'/pack.mcmeta']=json.dumps(root);unsupported.append((cases[0],multi))
    other_flags=copy.deepcopy(files);other_flags[high+'/assets/fixture/defs/entry.txt.mcmeta']='{"texture":{"blur":false}}'
    unsupported.append((cases[0],other_flags))
    for c,fs in unsupported:
        try:decode(c,fs)
        except ValueError:pass
        else:raise AssertionError('Unsupported adapter extension silently admitted')
    for i in [0,1,3,5,9,10,11,14]:
        wrong=list(answers);wrong[i]='none|' if wrong[i]!='none|' else '1:1:1|1:1:1'
        assert lean_actual!=wrong and bend_actual!=wrong
    report=dict(schema=1,status='passed',native=native,comparisons=len(rows),references=references,
        decoderRefusals=len(negative),adapterRefusals=len(unsupported),changedObservationControls=8,projectedInputSha256=sha(path),
        basisSha256={str(p.relative_to(ROOT)):sha(p) for p in basis},
        limits=['36 original-folder scenarios compare single/stack source,opened-byte identity,metadata absence/flags/failure and stack order.',
            'Listing observations are retained but not compared by these models.',
            'Two-pack generated profile only;matched filter predicates and physical-path admission are explicit authored projection premises,not a Java regex/filesystem implementation proof.',
            'No ZIP,repositories,selection UI,overlays,reload,application or rendering execution.'])
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','comparisons','decoderRefusals','changedObservationControls']}))


if __name__=='__main__':main()
