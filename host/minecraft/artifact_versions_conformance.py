#!/usr/bin/env python3
"""Pure declared-artifact-version replay, not a game or pack compatibility test."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def project(fact,available):
    fields=fact['packVersionFields']
    if set(fields)=={'resource','data'}:
        result=dict(resource=fields['resource'],data=fields['data'],resourceMinor=0,dataMinor=0,encoding='legacy-integer')
    elif set(fields)=={'resource_major','resource_minor','data_major','data_minor'}:
        result=dict(resource=fields['resource_major'],data=fields['data_major'],resourceMinor=fields['resource_minor'],dataMinor=fields['data_minor'],encoding='major-minor-fields')
    else:raise ValueError('Incomplete,mixed or unknown declared format fields')
    if any(type(result[k]) is not int or result[k]<0 for k in ['resource','data','resourceMinor','dataMinor']):raise ValueError('Invalid declared format integer')
    return dict(edition='java',declaredJava=fact['declaredJavaMajor'],availableJava=available,**result)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    facts=json.loads((HERE/'artifact-format-facts.json').read_text());targets=json.loads((HERE/'targets.json').read_text())
    assert facts['schema']==targets['schema']==1 and len(facts['facts'])==5
    by_id={t['id']:t for t in targets['javaReferences']}
    rows=[];answers=[];refs=[]
    for f in facts['facts']:
        target=by_id[f['target']]
        assert target['source']['versionJsonSha256']==f['versionJsonSha256']
        assert target['declaredPackFormats']==f['expectedFormats']
        assert target['declaredLauncherJavaMajor']==f['declaredJavaMajor']
        for available in [17,21,25]:
            rows.append(project(f,available));e=f['expectedFormats'];answers.append(f"{e['resource']['major']}.{e['resource']['minor']}/{e['data']['major']}.{e['data']['minor']}/{int(f['declaredJavaMajor']<=available)}")
            refs.append(dict(target=f['target'],availableJava=available))
    work=ROOT/'.build/minecraft/artifact-version-replay';work.mkdir(parents=True,exist_ok=True)
    data=work/'inputs.json';data.write_text(json.dumps(dict(schema=1,cases=rows),indent=2)+'\n')
    env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1');lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend')
    def lean_run(p):return subprocess.run([lean,'--run',str(HERE/'ArtifactVersionsCase.lean'),str(p)],cwd=ROOT,env=env,capture_output=True,text=True)
    result=lean_run(data);assert result.returncode==0,result.stdout+result.stderr
    lean_values=json.loads(result.stdout);assert lean_values==answers
    calls=[]
    for r in rows:
        def encoding(which):return ('M.Legacy{'+str(r[which])+'n}' if r['encoding']=='legacy-integer' else 'M.MajorMinor{'+str(r[which])+'n,'+str(r[which+'Minor'])+'n}')
        calls.append('render('+encoding('resource')+','+encoding('data')+','+str(r['declaredJava'])+'n,'+str(r['availableJava'])+'n) ++ "\\n"')
    runner=work/'ArtifactCase.bend';runner.write_text('''import Base
import ../../../host/minecraft/ArtifactVersions.bend as M
def version(v: M.Version) -> String:
  match v:
    case M.Version{a,b}: Nat.show(a) ++ "." ++ Nat.show(b)
def render(r: M.Encoding, d: M.Encoding, required: Nat, available: Nat) -> String:
  version(M.normalize(r)) ++ "/" ++ version(M.normalize(d)) ++ "/" ++ Bool.pick(String,M.declared_java_satisfied(required,available),"1","0")
def main() -> IO(Unit):
  IO.write('''+' ++ '.join(calls)+')\n')
    result=subprocess.run([bend,str(runner)],cwd=ROOT,env=env,capture_output=True,text=True);assert result.returncode==0,result.stdout+result.stderr
    bend_values=result.stdout.splitlines();assert bend_values==answers
    negative=[dict(schema=2,cases=rows)]
    for key,value in [('edition','bedrock'),('encoding','unknown'),('declaredJava',0),('availableJava',0),('resource',-1),('resource',34.75),('resourceMinor',1)]:
        r=dict(rows[0]);r[key]=value;negative.append(dict(schema=1,cases=[r]))
    for i,r in enumerate(negative):
        p=work/f'negative-{i}.json';p.write_text(json.dumps(r));assert lean_run(p).returncode==2
    adapter=[]
    for fields in [{'resource':75,'data':94,'data_minor':1},{'resource_major':75,'resource_minor':0,'data_major':94},{'resource':'34','data':48}]:
        f=copy.deepcopy(facts['facts'][0]);f['packVersionFields']=fields
        try:project(f,21)
        except ValueError:adapter.append('refused')
        else:raise AssertionError('Invalid artifact field shape silently projected')
    # Deliberate loss of each real nonzero minor and a prerequisite-bit error.
    i=next(i for i,r in enumerate(rows) if r['dataMinor']==1);wrong=list(answers);wrong[i]=wrong[i].replace('94.1','94.0');assert lean_values!=wrong and bend_values!=wrong
    i=next(i for i,r in enumerate(rows) if r['resourceMinor']==1);wrong=list(answers);wrong[i]=wrong[i].replace('97.1','97.0');assert lean_values!=wrong and bend_values!=wrong
    i=next(i for i,r in enumerate(rows) if r['declaredJava']==25 and r['availableJava']==21);wrong=list(answers);wrong[i]=wrong[i][:-1]+'1';assert lean_values!=wrong and bend_values!=wrong
    basis=[HERE/n for n in ['ArtifactVersions.lean','ArtifactVersions.bend','ArtifactVersionsCase.lean','artifact_versions_conformance.py','artifact-format-facts.json','targets.json']]
    report=dict(schema=1,status='passed',artifactMetadataRecords=5,normalizedAndPrerequisiteDecisions=len(rows),references=refs,decoderRefusals=len(negative),adapterRefusals=len(adapter),changedObservationControls=3,projectedInputSha256=sha(data),basisSha256={str(p.relative_to(ROOT)):sha(p) for p in basis},limits=['Declared original-client version.json metadata only,not arbitrary pack.mcmeta or compatibility semantics.','15 prerequisite calculations are not 15 JVM/application executions.','Satisfying a declared Java major does not qualify APIs,library ABI,native code,OS/backend,providers or rendering.','Bedrock uses a separate edition contract;this decoder refusing its input does not mean Bedrock lacks the capability.'])
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','artifactMetadataRecords','normalizedAndPrerequisiteDecisions','decoderRefusals','adapterRefusals','changedObservationControls']}))


if __name__=='__main__':main()
