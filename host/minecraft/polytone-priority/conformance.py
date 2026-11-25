#!/usr/bin/env python3
"""Pure models against the retained original-class/adapted priority observations."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def rank(priority):
    if type(priority) is not int or not -2147483648<=priority<=2147483647:raise ValueError('Priority is not a Java int32')
    return priority+2147483648


def entry(row):
    if type(row['enabled']) is not bool or any(type(row[k]) is not int or row[k]<0 for k in ['key','marker']):raise ValueError('Unmodeled identity/enablement/marker')
    return dict(key=row['key'],enabled=row['enabled'],rank=rank(row['priority']),marker=row['marker'])


def item(row):return f"{row['key']}:{int(row['enabled'])}:{row['rank']}:{row['marker']}"
def render(rows):return ','.join(item(r) for r in rows)


def project(case):
    inputs=[entry(r) for r in case['actions']];o=case['observed'];ordered=[entry(r) for r in o['iterator']]
    assert o['entrySet']==o['iterator'],'Two separately observed sorted views differ'
    by_key={r['key']:r for r in ordered};assert len(by_key)==len(ordered)
    keys=o['insertionKeys'];assert len(keys)==len(set(keys)) and set(keys)==set(by_key)
    inserted=[by_key[k] for k in keys];assert o['insertionMarkers']==[r['marker'] for r in inserted]
    zero='none' if o['selectedZeroMarker'] is None else str(o['selectedZeroMarker'])
    answer=f"{o['size']}/{o['warnings']}/{zero}/{render(inserted)}/{render(ordered)}"
    return dict(entries=inputs),answer


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);args=p.parse_args()
    capture=HERE.parent/'evidence/polytone-priority-20261125T051441802200Z';receipt=json.loads((capture/'receipt.json').read_text())
    for n,d in receipt['sourceSha256'].items():assert sha(capture/n)==d
    for stem,c in zip(['compile','execute'],receipt['commands']):
        assert c['exitCode']==0 and c['ownedGroupAbsent'] and not c['timedOut']
        for stream in ['stdout','stderr']:assert sha(capture/(stem+'.'+stream))==c[stream+'Sha256']
    native=json.loads((capture/'execute.stdout').read_text());assert native['schema']==1 and len(native['cases'])==48 and native['originalClassSha256']==receipt['classEntrySha256']
    pairs=[project(c) for c in native['cases']];rows=[p[0] for p in pairs];answers=[p[1] for p in pairs]
    work=ROOT/'.build/minecraft/polytone-priority-replay';work.mkdir(parents=True,exist_ok=True)
    data=work/'inputs.json';data.write_text(json.dumps(dict(schema=1,cases=rows),indent=2)+'\n')
    env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1');lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend')
    def lean_run(path):return subprocess.run([lean,'--run',str(HERE/'PriorityCase.lean'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True)
    result=lean_run(data);assert result.returncode==0,result.stdout+result.stderr;lean_values=json.loads(result.stdout);assert lean_values==answers
    def atom(r):return 'M.Item{'+str(r['key'])+'n,'+('True{}' if r['enabled'] else 'False{}')+','+str(r['rank'])+'n,'+str(r['marker'])+'n}'
    def items(rows):
        result='Nil{}'
        for row in reversed(rows):result='Con{'+atom(row)+','+result+'}'
        return result
    calls=['render(M.run('+items(r['entries'])+')) ++ "\\n"' for r in rows]
    runner=work/'PriorityCase.bend';runner.write_text('''import Base
import ../../../host/minecraft/polytone-priority/Priority.bend as M
def item(r: M.Item) -> String:
  match r:
    case M.Item{k,e,p,v}: Nat.show(k) ++ ":" ++ Bool.pick(String,e,"1","0") ++ ":" ++ Nat.show(p) ++ ":" ++ Nat.show(v)
def entries(rows: List<&2,M.Item>) -> String:
  match rows:
    case Nil{}: ""
    case Con{head,Nil{}}: item(head)
    case Con{head,rest}: item(head) ++ "," ++ entries(rest)
def zero(rows: List<&2,M.Item>) -> String:
  match rows:
    case Nil{}: "none"
    case Con{M.Item{k,_,_,v},rest}: Bool.pick(String,Nat.is_eq(k,0n),Nat.show(v),zero(rest))
def render(s: M.State) -> String:
  match s:
    case M.State{+rows,warnings}: Nat.show(List.length(&2,M.Item,rows)) ++ "/" ++ Nat.show(warnings) ++ "/" ++ zero(rows) ++ "/" ++ entries(rows) ++ "/" ++ entries(M.ordered(rows))
def main() -> IO(Unit):
  IO.write('''+' ++ '.join(calls)+')\n')
    result=subprocess.run([bend,str(runner)],cwd=ROOT,env=env,capture_output=True,text=True);assert result.returncode==0,result.stdout+result.stderr;bend_values=result.stdout.splitlines();assert bend_values==answers
    bad=[dict(schema=2,cases=rows)]
    for key,value in [('rank',4294967296),('rank',-1),('key',-1),('enabled','false'),('marker',1.5)]:
        row=copy.deepcopy(rows[0]);row['entries'][0][key]=value;bad.append(dict(schema=1,cases=[row]))
    for i,b in enumerate(bad):
        path=work/f'negative-{i}.json';path.write_text(json.dumps(b));assert lean_run(path).returncode==2
    adapter=0
    for value in [2147483648,-2147483649,True,0.5]:
        try:rank(value)
        except ValueError:adapter+=1
        else:raise AssertionError('Unsupported signed priority silently admitted')
    controls=0
    for key,value in [('size',4),('warnings',1),('selectedZeroMarker',999)]:
        case=copy.deepcopy(native['cases'][0]);case['observed'][key]=value;_,wrong=project(case);assert wrong!=lean_values[0] and wrong!=bend_values[0];controls+=1
    # Reject treating a first disabled entry as absence.
    changed=copy.deepcopy(native['cases'][0]);changed['observed'].update(size=0,selectedZeroMarker=None,insertionKeys=[],insertionMarkers=[],iterator=[],entrySet=[])
    _,wrong=project(changed);assert wrong!=lean_values[0] and wrong!=bend_values[0];controls+=1
    # Reject bypassing priority merely because the existing entry is disabled.
    i=next(i for i,c in enumerate(native['cases']) if c['case']=='disabled-high-stays');changed=copy.deepcopy(native['cases'][i]);o=changed['observed'];replacement=changed['actions'][-1]
    o.update(warnings=1,selectedZeroMarker=3,insertionMarkers=[3,2]);o['iterator']=[replacement,o['iterator'][0]];o['entrySet']=copy.deepcopy(o['iterator'])
    _,wrong=project(changed);assert wrong!=lean_values[i] and wrong!=bend_values[i];controls+=1
    # Reject key-sorting equal-priority entries instead of stable encounter order.
    i=next(i for i,c in enumerate(native['cases']) if c['case']=='tie-reverse');changed=copy.deepcopy(native['cases'][i]);changed['observed']['iterator'].reverse();changed['observed']['entrySet']=copy.deepcopy(changed['observed']['iterator'])
    _,wrong=project(changed);assert wrong!=lean_values[i] and wrong!=bend_values[i];controls+=1
    basis=[HERE/n for n in ['Priority.lean','Priority.bend','PriorityCase.lean','conformance.py']]+[p for p in capture.iterdir() if p.is_file()]
    report=dict(schema=1,status='passed-original-policy-class-with-adapters',comparisons=len(rows),collectionViews=['size','get','keySet','values','iterator','entrySet'],leanLaws=12,bendLaws=7,decoderRefusals=len(bad),adapterRefusals=adapter,changedObservationControls=controls,projectedInputSha256=sha(data),basisSha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(basis)},limits=receipt['limits']+['Native priorities -1,0,1;the Lean adapter theorem separately proves signed-rank order under its stated bounds.','The source-discovery map is broader than this single policy-class comparison.'])
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','comparisons','decoderRefusals','adapterRefusals','changedObservationControls']}))


if __name__=='__main__':main()
