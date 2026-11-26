"""Retained Cargo config/build/run replay. Never invokes Cargo, Rust, or a runner."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
CAPS=[ROOT/'applications/evidence'/('cargo-run-config-'+s) for s in ['20261126T001855041022Z','20261126T002203646988Z']]
CAP=CAPS[-1]
FORMAL=ROOT/'.build/cargo-run-config-formal'
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda b:hashlib.sha256(b).hexdigest()
write=lambda p,x:p.write_text(json.dumps(x,indent=2)+'\n')

def evidence(owner_local):
    packets=[];observed=[];basis={};unavailable=[];proposed=[];details=[]
    for cap in CAPS:
        setup=load(cap/'setup.json');receipt=load(cap/'receipt.json');rows=load(cap/'commands.json');work=Path(setup['work']);project=work/'project'
        assert receipt['complete'] and receipt['commands']==len(rows)==(10 if cap==CAPS[0] else 4)
        assert receipt['runRequests']==len(rows)-1 and receipt['cleanupCommands']==1 and receipt['allRecordedGroupsAbsent']
        assert sha(cap/'setup.json')==receipt['setupSha256'] and sha(cap/'probe.py')==receipt['producerSha256']==setup['producerSha256']
        spec=importlib.util.spec_from_file_location('frozen_cargo_run',cap/'probe.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        good=digest(m.MAIN.encode());bad=digest(b'fn main() { controlled_invalid_rust }\n')
        cmd=lambda label:setup['python']['path']+' '+str(work/'runner.py')+' '+label
        config=digest(('[target.aarch64-apple-darwin]\nrunner='+json.dumps(cmd('project'))+'\n').encode())
        edits=load(cap/'authored-edits.json') if (cap/'authored-edits.json').exists() else []
        assert len(edits)==receipt['authoredEdits']==(2 if cap==CAPS[0] else 0)
        for edit in edits:
            assert {p for p in edit['before']['project'].keys()|edit['after']['project'].keys() if edit['before']['project'].get(p)!=edit['after']['project'].get(p)}=={'src/main.rs'}
            assert {k:v for k,v in edit['before'].items() if k!='project'}=={k:v for k,v in edit['after'].items() if k!='project'}
        for index,r in enumerate(rows):
            assert r['groupAbsent'] and not r['timedOut'] and r['argv'][0]==setup['tools']['cargo']['path']
            for stream,h in r['streams'].items():assert sha(cap/(r['id']+'.'+stream))==h
            for image in [r['before'],r['after']]:assert image['project']['.cargo/config.toml']['sha256']==config
            # Exact lineage, with the two separately recorded source edits.
            if index:
                previous=rows[index-1]['after'];matches=[e for e in edits if e['before']==previous and e['after']==r['before']]
                assert previous==r['before'] or len(matches)==1
            assert r['after']['runner'][:len(r['before']['runner'])]==r['before']['runner']
            assert r['after']['app'][:len(r['before']['app'])]==r['before']['app']
            runner_events=r['after']['runner'][len(r['before']['runner']):];app_events=r['after']['app'][len(r['before']['app']):]
            if r['id']=='owned-target-clean':
                assert r['argv'][1:]==['clean','--offline'] and r['exitCode']==0 and not runner_events and not app_events
                assert r['before']['binary'] is not None and r['after']['binary'] is None
                assert r['before']['binary']['sha256']==receipt['retainedBinary']['sha256'];continue
            assert r['before']['project']==r['after']['project'] or r['id'] in ['project-config','cli-runner-only']
            argv=r['argv'][1:];override=None
            if argv[:1]==['--config']:override=argv[1];argv=argv[2:]
            assert argv[:3]==['run','--offline','--message-format=json'];tail=argv[3:]
            package_cwd=r['cwd']==str(project)
            if not package_cwd:assert r['cwd']==str(work) and tail[:2]==['--manifest-path',str(project/'Cargo.toml')];tail=tail[2:]
            assert tail==['--','space argument','Ω日本','--literal-flag']
            explicit=override==str(project/'.cargo/config.toml')
            cli=override is not None and override.startswith('target.aarch64-apple-darwin.runner=')
            if cli:assert json.loads(override.split('=',1)[1])==cmd('cli')
            cli_jobs=override=='build.jobs=1'
            assert override is None or explicit or cli or cli_jobs
            env=r['environmentOverrides'];env_key='CARGO_TARGET_AARCH64_APPLE_DARWIN_RUNNER'
            assert env_key not in env or env[env_key]==cmd('environment')
            assert set(env)<={env_key,'RULES_RUNNER_STATUS','RULES_APP_STATUS','CARGO_BUILD_JOBS'}
            values=[json.loads(line) for line in (cap/(r['id']+'.stdout')).read_text().splitlines()]
            finish=[v['success'] for v in values if v.get('reason')=='build-finished'];assert len(finish)<=1
            build=finish[0] if finish else None
            invalid=env.get('CARGO_BUILD_JOBS')=='0'
            if invalid and not cli_jobs:
                assert build is None and 'jobs may not be 0' in (cap/(r['id']+'.stderr')).read_text();stage=1
            elif build is False:
                assert any(v.get('reason')=='compiler-message' and v['message']['level']=='error' for v in values);stage=2
            elif runner_events and not app_events:stage=3
            elif app_events and app_events[0]['code']!=0:stage=4
            else:assert build is True;stage=0
            source_hash=r['before']['project']['src/main.rs']['sha256'];assert source_hash in [good,bad]
            if build is not None:assert build==(source_hash==good)
            assert len(runner_events)<=1 and len(app_events)<=1
            for event in runner_events:
                assert event['args']==tail[1:] and event['cwd']==r['cwd']
                selected=Path(event['binary']);assert (Path(r['cwd'])/selected).resolve()==(work/'target/debug/rules-run-profile').resolve()
            for event in app_events:assert event['args']==tail[1:] and event['cwd']==r['cwd'] and event['code']==int(env.get('RULES_APP_STATUS','0'))
            assert [v for v in values if 'cwd' in v and 'args' in v]==app_events
            if app_events:assert values.index(app_events[0])>next(i for i,v in enumerate(values) if v.get('reason')=='build-finished')
            artifacts=[v for v in values if v.get('reason')=='compiler-artifact'];assert len(artifacts)==int(build is True)
            if artifacts:
                assert artifacts[0]['executable']==str(work/'target/debug/rules-run-profile')
                assert r['after']['binary'] is not None
            if r['id'] in ['failed-build','runner-refuses','application-fails','invalid-environment-jobs']:
                assert r['before']['binary']==r['after']['binary']
            if r['id']=='source-repaired':assert r['after']['binary']==rows[0]['after']['binary']
            packet=dict(packageCwd=package_cwd,explicitFile=explicit,environmentRunner=env_key in env,cliRunner=cli,invalidEnvironmentJobs=invalid,cliJobs=cli_jobs,build=build,oldArtifact=r['before']['binary'] is not None,runnerStatus=int(env.get('RULES_RUNNER_STATUS','0')),applicationStatus=int(env.get('RULES_APP_STATUS','0')))
            choice={'project':1,'environment':2,'cli':3}[runner_events[0]['label']] if runner_events else 0
            observed.append([int(bool(runner_events)),int(bool(app_events)),choice,stage,r['exitCode'],(0 if package_cwd else 1) if app_events else 2]);packets.append(packet)
            proposed.append(3 if cli else 2 if env_key in env else 1 if package_cwd or explicit else 0)
            details.append(dict(id=r['id'],buildWitness=build,artifactReportedFresh=[v['fresh'] for v in artifacts],binarySha256=r['after']['binary']['sha256'] if r['after']['binary'] else None))
        if owner_local:
            for tool in setup['tools'].values():assert sha(Path(tool['path']))==tool['sha256']
            assert sha(Path(setup['python']['path']))==setup['python']['sha256']
            assert m.item(Path(receipt['retainedBinary']['path']))['sha256']==receipt['retainedBinary']['sha256']
            assert not (work/'target').exists()
            assert m.events(work/'runner.jsonl')==rows[-1]['after']['runner'] and m.events(work/'app.jsonl')==rows[-1]['after']['app']
            assert {p.relative_to(project).as_posix():m.item(p) for p in sorted(project.rglob('*')) if p.is_file()}==rows[-1]['after']['project']
        else:unavailable+=[str(work),'installed Cargo/Rust/Python identities']
        for p in cap.iterdir():
            if p.is_file() and p.name not in ['model-input.json','observed.json','basis.json','conformance.json','controls.json','phase-details.json']:basis[str(p.relative_to(ROOT))]=sha(p)
    assert len(packets)==12
    selections=ROOT/'applications/sources/cargo-run-config-selections.json';basis[str(selections.relative_to(ROOT))]=sha(selections)
    for source in load(selections)['sources']:
        if owner_local and (ROOT/source['cache']).exists():assert sha(ROOT/source['cache'])==source['sha256']
        else:unavailable.append(source['cache'])
    proof=load(CAP/'proof-gate.json');assert proof['exitCode']==0 and 'Checked 2 Lean modules and 1 Bend files.' in proof['stdout']
    for p,h in proof['sourceSha256'].items():
        if p!='scripts/check-rules.py':assert sha(ROOT/p)==h
    return dict(schema=1,cases=packets),observed,proposed,details,basis,unavailable

def main():
    assert sys.argv[1:] in [[],['--public-only']]
    inputs,observed,proposed,details,basis,unavailable=evidence(not sys.argv[1:]);FORMAL.mkdir(parents=True,exist_ok=True)
    write(CAP/'model-input.json',inputs);write(CAP/'observed.json',observed);write(CAP/'phase-details.json',details)
    lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend');env={**os.environ,'LEAN_PATH':str(FORMAL),'BEND_NO_TELEMETRY':'1'}
    p=HERE/'RunConfig.lean';dest=FORMAL/'applications/cargo/RunConfig.olean';dest.parent.mkdir(parents=True,exist_ok=True);subprocess.run([lean,'-DwarningAsError=true','-o',str(dest),str(p)],env=env,capture_output=True,check=True)
    command=[lean,'--run',str(HERE/'RunConfigCase.lean'),str(CAP/'model-input.json')];r=subprocess.run(command,env=env,capture_output=True,text=True,check=True);result=json.loads(r.stdout);assert [o[0] for o in result]==observed and [o[1] for o in result]==proposed
    def boolean(b):return 'True{}' if b else 'False{}'
    def request(r):return 'R.RR{'+','.join([*[boolean(r[k]) for k in ['packageCwd','explicitFile','environmentRunner','cliRunner','invalidEnvironmentJobs','cliJobs']],('None{}' if r['build'] is None else 'Some{'+boolean(r['build'])+'}'),boolean(r['oldArtifact']),str(r['runnerStatus'])+'n',str(r['applicationStatus'])+'n'])+'}'
    calls=['R.render(R.run('+request(r)+')) ++ "/" ++ Nat.show(R.proposed_runner('+','.join(boolean(r[k]) for k in ['packageCwd','explicitFile','environmentRunner','cliRunner'])+'))' for r in inputs['cases']];driver=HERE/'_run_config_replay.bend';driver.write_text('import Base\nimport RunConfig.bend as R\ndef main() -> IO(Unit):\n  IO.print('+(' ++ "\\n" ++ '.join(calls))+')\n')
    try:b=subprocess.run([bend,str(driver)],env=env,capture_output=True,text=True,check=True)
    finally:driver.unlink()
    bvalues=[[int(v) for v in line.split('/')] for line in b.stdout.strip().splitlines()]
    assert [r[:6] for r in bvalues]==observed and [r[6] for r in bvalues]==proposed
    controls=[]
    for field in range(6):
        changed=copy.deepcopy(observed);changed[0][field]+=1;assert changed!=observed;controls.append(dict(kind='changed-observation',field=field,refused=True))
    for name,mutation in [('schema',lambda x:x.update(schema=2)),('unobserved-build',lambda x:x['cases'][0].update(build=None)),('unsupported-runner-status',lambda x:x['cases'][0].update(runnerStatus=12)),('unsupported-app-status',lambda x:x['cases'][0].update(applicationStatus=12))]:
        bad=copy.deepcopy(inputs);mutation(bad);path=FORMAL/(name+'.json');write(path,bad);q=subprocess.run(command[:-1]+[str(path)],env=env,capture_output=True);assert q.returncode==2;controls.append(dict(kind='DTO',field=name,refused=True))
    for p in [Path(__file__),HERE/'RunConfig.lean',HERE/'RunConfigCase.lean',HERE/'RunConfig.bend']:basis[str(p.relative_to(ROOT))]=sha(p)
    write(CAP/'basis.json',basis);write(CAP/'controls.json',controls)
    value=dict(schema=1,nativeCommands=14,runRequests=12,incidentalOwnedCleanCommands=2,launchStatusCwdValues=60,derivedStageLabels=12,modelOnlyProposedChoices=12,matched=True,controls=len(controls),basisFiles=len(basis),ownerLocalUnavailable=unavailable,
      scope='Pinned scalar config and generated runner/app;compiler phase results are admitted witnesses,not predicted compiler conformance. Independent journals/status/cwd are compared;derived phase labels are separately counted. No Cargo/Rust/runner/native execution,patched priority or arbitrary source/freshness proof.')
    write(CAP/'conformance.json',value);print(json.dumps({k:v for k,v in value.items() if k not in ['scope','ownerLocalUnavailable']}))

if __name__=='__main__':main()
