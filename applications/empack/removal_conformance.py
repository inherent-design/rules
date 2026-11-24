#!/usr/bin/env python3
"""Replay retained actual-core values through bounded models; no engine/compiler collection."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
KEY={'a':1,'b':2,'c':3,'d':4}
COVERAGE={'CompleteForSelection':0,'Partial':1,'Unknown':2}
CODES={'unknown':1,'duplicate':2,'not-root':3,'required':4,'incomplete':5}


def state(value):
    return dict(roots=[KEY[k] for k in value['roots']],nodes=[dict(n,key=KEY[n['key']],
        coverage=COVERAGE[n['coverage']],edges=[KEY[k] for k in n['edges']]) for n in value['nodes']])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);args=p.parse_args();capture=args.capture.resolve()
    assert capture.is_relative_to(ROOT/'applications/evidence')
    r=json.loads((capture/'receipt.json').read_text());assert r['cases']==25 and r['allOwnedProcessesRetired']
    prior=ROOT/r['priorCoreCapture'];core=json.loads((prior/'receipt.json').read_text());repo=ROOT.parent/'empack'
    assert sha(prior/'receipt.json')==r['priorCoreReceiptSha256'] and sha(prior/'work/libempack_core.rlib')==r['librarySha256']==core['librarySha256']
    for source,digest in r['sourceSha256'].items():
        assert sha(repo/source)==digest
        assert hashlib.sha256(subprocess.check_output(['git','-C',str(repo),'show',r['revision']+':'+source])).hexdigest()==digest
    for name,key in [('probe.py','producerSha256'),('driver.rs','driverSha256'),('observed.stdout','observedSha256')]:assert sha(capture/name)==r[key]
    assert sha(capture/'work/removal-driver')==r['binarySha256'] and sha(Path(r['compiler']['path']))==r['compiler']['sha256']
    commands=json.loads((capture/'commands.json').read_text());assert len(commands)==2
    for command in commands:
        assert command['exitCode']==0 and not command['timedOut']
        for stream in ['stdout','stderr']:assert sha(capture/(command['case']+'.'+stream))==command[stream+'Sha256']
    ledger=ROOT/'applications/sources/empack-removal-selections.json'
    for source in json.loads(ledger.read_text())['sources']:assert sha(repo/source['path'])==source['sha256']
    original=ROOT/'applications/evidence/empack-removal-20261124T152143364201Z'
    old=[json.loads(line) for line in (original/'observed.stdout').read_text().splitlines()]
    rows=[json.loads(line) for line in (capture/'observed.stdout').read_text().splitlines()]
    assert len(rows)==len({row['case'] for row in rows})==25
    for a,b in zip(old,rows):
        b=dict(b);b.pop('request',None);assert a==b
    models=[HERE/name for name in ['Removal.lean','RemovalCase.lean','Removal.bend']]
    inputs=models+[ledger]+[p for p in capture.iterdir() if p.is_file() and p.name!='conformance.json']+[original/'observed.stdout',original/'disposition.json',prior/'receipt.json']
    basis={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    cases=[];expected=[]
    for row in rows:
        c=dict(operation=row['operation'],before=state(row['before']),mode='content',acknowledge=False,selection=[],request=None)
        result=copy.deepcopy(row['result'])
        if row['operation']=='remove':
            assert row['inputUnchanged'];c.update(mode=row['mode'],acknowledge=row['acknowledge'],selection=[KEY[k] for k in row['selection']])
            if result['error']:
                e=result['error'];result['error']=dict(kind=e['kind'],keys=[KEY[k] for k in e['keys']])
            else:
                for k in ['selected','removed','incomplete']:result[k]=[KEY[v] for v in result[k]]
        else:
            c['request']=state(row['request'])
            if result['error']:
                assert result['error']=='Cannot update an uninstalled identity: a';result['error']='update-missing'
            else:
                for k in ['existingRequests','changedRecords']:result[k]=[KEY[v] for v in result[k]]
        if result['after'] is not None:result['after']=state(result['after'])
        cases.append(c);expected.append(result)
    generated=HERE/'generated';generated.mkdir(exist_ok=True);formal=generated/'removal-formal'
    artifact=formal/'applications/empack/Removal.olean';artifact.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=str(formal),BEND_NO_TELEMETRY='1');lean=os.environ.get('LEAN','lean')
    compiled=subprocess.run([lean,'-DwarningAsError=true','-o',str(artifact),str(models[0])],cwd=ROOT,env=env,capture_output=True,text=True)
    assert compiled.returncode==0,compiled.stdout+compiled.stderr
    path=generated/'removal.json';data=dict(schema=1,cases=cases);path.write_text(json.dumps(data,indent=2)+'\n')
    def run(q):return subprocess.run([lean,'--run','applications/empack/RemovalCase.lean',str(q)],cwd=ROOT,env=env,capture_output=True,text=True)
    result=run(path);assert result.returncode==0,result.stdout+result.stderr
    actual=json.loads(result.stdout);assert actual==expected
    def listing(values):
        result='Nil{}'
        for value in reversed(values):result='Con{'+value+','+result+'}'
        return result
    bit=lambda b:'True{}' if b else 'False{}'
    calls=[];bend_expected=[]
    for c,e in zip(cases,expected):
        if c['operation']=='remove':
            nodes=listing(['C.EvidenceNode{'+str(n['key'])+'n,'+bit(n['coverage']==0)+','+listing([str(k)+'n' for k in n['edges']])+'}' for n in c['before']['nodes']])
            roots=listing([str(k)+'n' for k in c['before']['roots']]);selection=listing([str(k)+'n' for k in c['selection']])
            calls.append('Nat.show(C.decide('+','.join([nodes,roots,selection,bit(c['mode']=='forget'),bit(c['acknowledge'])])+')) ++ "\\n"')
            bend_expected.append(str(CODES[e['error']['kind']] if e['error'] else 0))
        else:
            exists=any(n['key']==1 for n in c['before']['nodes']);operation={'add':0,'adopt':1,'update':2}[c['operation']]
            calls.append('Nat.show(C.merge_error('+bit(exists)+','+str(operation)+'n)) ++ "/" ++ flag(C.merge_root('+bit(exists)+','+str(operation)+'n)) ++ "\\n"')
            bend_expected.append(('6' if e['error'] else '0')+'/'+str(int(bool(e['after'] and 1 in e['after']['roots']))))
    runner=generated/'RemovalCase.bend';runner.write_text('import Base\nimport ../Removal.bend as C\n\ndef flag(b: Bool) -> String:\n  match b:\n    case True{}: "1"\n    case False{}: "0"\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
    result=subprocess.run([os.environ.get('BEND','bend'),str(runner)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.splitlines()==bend_expected
    negatives=[dict(data,schema=2)]
    for change in [dict(selection=[]),dict(selection=[5])]:negatives.append(dict(data,cases=[dict(cases[0],**change)]))
    for field,value in [('coverage',3),('edges',[4])]:
        bad=copy.deepcopy(cases[0]);bad['before']['nodes'][0][field]=value;negatives.append(dict(data,cases=[bad]))
    bad=copy.deepcopy(cases[0]);bad['before']['nodes'].append(bad['before']['nodes'][0]);negatives.append(dict(data,cases=[bad]))
    bad=copy.deepcopy(cases[-6]);bad['request']['nodes'][0]['record']='different';negatives.append(dict(data,cases=[bad]))
    bad=copy.deepcopy(cases[-6]);bad.pop('request');negatives.append(dict(data,cases=[bad]))
    for i,bad in enumerate(negatives):
        q=generated/f'removal-negative-{i}.json';q.write_text(json.dumps(bad));result=run(q);assert result.returncode==2 and result.stderr
    assert all(sha(ROOT/p)==digest for p,digest in basis.items())
    report=dict(schema=1,records=25,leanFullValueMatches=True,bendAdmissionAndPromotionMatches=True,researchInputsRefused=len(negatives),
        adapterSha256=sha(Path(__file__)),basisSha256=basis,modelResults=actual,
        limits=['Actual unchanged core API over fixed fictional provider/value profile. No engine,codec,acquisition,physical files or CLI execution.',
          'Reject-existing predicate is source-interpreted and needs actual caller-policy/materialization/publication qualification.',
          'Bend compares admission/error priority and re-addition promotion only; exact retained record/graph/value comparison belongs to Lean.',
          'Addition profile is identical A->B request with retained B and no alias/version/runtime/content edits; not general addition/replacement modeling.',
          'First observation omitted request snapshots; corrected capture retains them and verifies all25 previous outcomes unchanged.'])
    (capture/'conformance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['basisSha256','modelResults']},indent=2))


if __name__=='__main__':main()
