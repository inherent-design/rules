#!/usr/bin/env python3
"""Replay retained MO2 method observations, not the Windows application."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ADAPTER=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path)
    run=parser.parse_args().run.resolve()
    receipt=json.loads((run/'receipt.json').read_text())
    original=json.loads((run/'input.json').read_text())
    observed=[json.loads(line) for line in (run/'observed.stdout').read_text().splitlines()]
    inputs=[HERE/name for name in ['Profile.lean','Profile.bend','ProfileCase.lean']]
    inputs += [run/name for name in ['receipt.json','input.json','observed.stdout','observed.stderr','probe.py','compile.stdout','compile.stderr']]
    basis={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    assert sha(run/'probe.py')==receipt['producerSha256']
    for name,key in [('input.json','inputSha256'),('observed.stdout','stdoutSha256'),('observed.stderr','stderrSha256')]:
        assert sha(run/name)==receipt[key]
    assert receipt['sourceUnchanged'] and receipt['compileExit']==receipt['executeExit']==0
    assert len(observed)==len(original['cases'])==receipt['cases']==24
    cases=[];expected=[];bend_expected=[]
    for case,row in zip(original['cases'],observed,strict=True):
        assert case['id']==row['id'] and row['independent']==case['before']
        flags={'free':[False,False],'on':[True,False],'off':[False,True]}
        assert row['catalogFlags']==[flags[p] for p in case['policies']]
        assert len(case['policies'])==len(case['before'])==len(row['state'])
        if case['mode']=='single':assert row['loggedErrors']==0
        else:assert not row['threw']
        assert len(row['signals'])<=1
        cases.append(dict(id=case['id'],mode=case['mode'],policies=case['policies'],before=case['before'],
            target=case.get('target',0),request=case.get('request',False),enable=case.get('enable',[]),disable=case.get('disable',[])))
        expected.append({k:row[k] for k in ['id','state','signals','loggedErrors','threw']})
        dirty=row['signals'][0] if row['signals'] else []
        bend_expected.append(''.join(str(int(b)) for b in row['state'])+'/'+','.join(str(i) for i in dirty)+'/'+str(int(row['threw'])+row['loggedErrors']))
    by_id={r['id']:r for r in observed}
    overlapping=by_id['batch-overlapping-requests']
    assert overlapping['state']==overlapping['independent'] and overlapping['signals']==[[0,0]]
    assert by_id['batch-ordered-changes']['signals']==[[1,0]]
    assert by_id['batch-invalid-on-prestate']['state']==[False]
    assert by_id['single-on-0-0']['state']==[True]
    generated=HERE/'generated';generated.mkdir(exist_ok=True)
    path=generated/'profile.json';path.write_text(json.dumps({'schema':1,'cases':cases},indent=2)+'\n')
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    env=dict(os.environ,LEAN_PATH=os.pathsep.join(str(ROOT/p) for p in ['.build','.build/formal']),BEND_NO_TELEMETRY='1')
    result=subprocess.run([lean,'--run','applications/mo2/ProfileCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert json.loads(result.stdout)==expected
    calls=[]
    policy={'free':'Free{}','on':'AlwaysOn{}','off':'AlwaysOff{}'}
    bit=lambda b:'True{}' if b else 'False{}'
    ids=lambda values:'['+','.join(str(i)+'n' for i in values)+']'
    for case in cases:
        entries='['+','.join(f'P.Entry{{{i}n,P.{policy[p]},{bit(b)}}}' for i,(p,b) in enumerate(zip(case['policies'],case['before'],strict=True)))+']'
        call=f'P.single({entries},{case["target"]}n,{bit(case["request"])})' if case['mode']=='single' else f'P.batch({entries},{ids(case["enable"])},{ids(case["disable"])})'
        calls.append('render('+call+') ++ "\\n"')
    runner=generated/'ProfileCase.bend'
    runner.write_text('''import Base
import ../Profile.bend as P

def bit(b: Bool) -> String:
  match b:
    case True{}: "1"
    case False{}: "0"

def bits(entries: List<&2,P.Entry>) -> String:
  match entries:
    case Nil{}: ""
    case Con{head,tail}:
      match head:
        case P.Entry{id,policy,enabled}: bit(enabled) ++ bits(tail)

def rest_ids(values: List<&2,Nat>) -> String:
  match values:
    case Nil{}: ""
    case Con{head,tail}: "," ++ Nat.show(head) ++ rest_ids(tail)

def ids(values: List<&2,Nat>) -> String:
  match values:
    case Nil{}: ""
    case Con{head,tail}: Nat.show(head) ++ rest_ids(tail)

def render(work: P.Work) -> String:
  match work:
    case P.Work{entries,dirty,errors}: bits(entries) ++ "/" ++ ids(dirty) ++ "/" ++ Nat.show(errors)

def main() -> IO(Unit):
  IO.write('''+' ++ '.join(calls)+')\n')
    result=subprocess.run([bend,str(runner)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.splitlines()==bend_expected
    invalid=json.loads(path.read_text());invalid['cases'][0]['policies'].append('free')
    bad=generated/'profile-invalid.json';bad.write_text(json.dumps(invalid))
    result=subprocess.run([lean,'--run','applications/mo2/ProfileCase.lean',str(bad)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==2 and 'Profile and catalog lengths differ' in result.stderr
    assert all(sha(ROOT/p)==digest for p,digest in basis.items()),'Inputs changed during replay.'
    report={'schema':1,'sourceMethodCases':24,'bothModelsMatch':True,'inconsistentCatalogRefused':True,
        'independentFixtureProfilesUnchanged':True,'catalogFlagsUnchanged':True,
        'rejectedInterpretations':['One dirty notification entry means one net changed mod.','Bulk setter repairs every inconsistent forced-policy prestate like the scalar setter.'],
        'unsupportedInference':'Recorded fixture callbacks do not establish Qt event delivery, completed refresh, or profile persistence.',
        'adapterSha256':ADAPTER,'basisSha256':basis,
        'limits':['Unmodified source method bodies with fixture adapters; not Windows MO2, Qt signals or filesystem effects.',
            'Lean compares full per-mode result; Bend compares enabled state, ordered dirty indices and invalid-index count, with error channel checked separately.',
            'View-readiness laws are a proposed receipt boundary, not an implemented MO2 API or evidence of a stale native view.']}
    (run/'conformance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='basisSha256'},indent=2))


if __name__=='__main__':main()
