#!/usr/bin/env python3
"""Compare captured Cargo metadata and check artifacts; never execute Cargo."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tomllib

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path);run=parser.parse_args().run.resolve()
    receipt=json.loads((run/'receipt.json').read_text());trace=json.loads((run/'trace.json').read_text());configs=json.loads((run/'configuration.json').read_text())
    assert receipt['schema']==1 and receipt['profiles']==4 and receipt['commands']==len(trace)==36
    assert receipt['targetDirectoriesCleaned'] and receipt['noMatchingProcessAtMove']
    assert sha(run/'probe.py')==receipt['producerSha256']==sha(HERE/'workspaces_probe.py')
    assert '344c4567c634a25837e3c3476aac08af84cf9203'in receipt['tools']['cargo']['version']
    ledger=ROOT/'applications/sources/cargo-workspaces-selections.json';selection=json.loads(ledger.read_text())
    assert selection['revision']=='344c4567c634a25837e3c3476aac08af84cf9203'
    for source in selection['sources']:assert sha(ROOT/source['cache'])==source['sha256']
    files=[HERE/p for p in ['Workspaces.lean','WorkspacesCase.lean','Workspaces.bend','workspaces_probe.py','workspaces_conformance.py']]
    files += [ledger,*[run/p for p in ['receipt.json','trace.json','configuration.json','probe.py']]]
    for row in trace:
        assert not row['outcome']['timedOut']
        for stream in ['stdout','stderr']:
            path=run/(row['profile']+'-'+row['case']+'.'+stream);files.append(path);assert sha(path)==row['observed'][stream+'Sha256']
    basis={str(p.relative_to(ROOT)):sha(p)for p in files}
    inputs=[];expected=[];names=[];kinds=[];metadata_default_pairs={};excluded_cold_b=False
    profile_facts={};profile_names={}
    for profile,texts in configs.items():
        root=tomllib.loads(texts['Cargo.toml']);workspace=root['workspace'];assert workspace['members']==['a','b']and workspace['resolver']=='2'
        defaults=workspace.get('default-members');assert defaults in [None,['a']]
        package_a=tomllib.loads(texts['a/Cargo.toml']);package_b=tomllib.loads(texts['b/Cargo.toml'])
        assert package_a['dependencies']=={'fixture-b':{'path':'../b'}} and not package_b.get('dependencies')
        assert package_a['package']['name']=='fixture-a'and package_b['package']['name']=='fixture-b'
        if 'package'in root:assert root['package']['name']=='fixture-root'
        profile_facts[profile]=(bool(root.get('package')),defaults is not None)
        metadata=json.loads((run/(profile+'-metadata-root.stdout')).read_text());by_id={p['id']:p['name']for p in metadata['packages']}
        assert set(by_id.values())==({'fixture-a','fixture-b','fixture-root'}if profile_facts[profile][0]else{'fixture-a','fixture-b'})
        profile_names[profile]=by_id
    codes={'fixture-root':0,'fixture-a':1,'fixture-b':2}
    for row in trace:
        profile,case=row['profile'],row['case'];root_package,explicit=profile_facts[profile];before=row['observed']['before'];after=row['observed']['after']
        assert before['sourceSha256']==after['sourceSha256']
        for name,text in configs[profile].items():assert hashlib.sha256(text.encode()).hexdigest()==before['sourceSha256'][name]
        original=Path(receipt['originalWork'])/profile;project=original/'project';argv=row['argv'];assert argv[-1]=='--offline'
        assert row['cwd']in [str(project),str(project/'b')]
        if case=='clean':
            assert row['outcome']['exitCode']==0 and not after['targetPresent']and before['lockSha256']==after['lockSha256'];continue
        args=argv[1:];metadata_request=args[0]=='metadata';member=row['cwd']==str(project/'b')and'--manifest-path'not in args
        if '--manifest-path'in args:assert args[args.index('--manifest-path')+1]==str(project/'Cargo.toml')
        mode=0
        if '--exclude'in args:
            assert args[args.index('--exclude')+1]=='fixture-b';mode=1 if '--workspace'in args else 3
        elif '-p'in args:assert args[args.index('-p')+1]=='fixture-a';mode=2
        inputs.append(dict(rootPackage=root_package,explicitA=explicit,memberB=member,mode=mode));names.append(profile+'/'+case)
        stdout=(run/(profile+'-'+case+'.stdout')).read_text()
        if metadata_request:
            data=json.loads(stdout);by_id=profile_names[profile]
            assert data['resolve']is None and data['workspace_root']==str(project)and data['target_directory']==str(original/'target')
            assert data['version']==1 and {p['id']:p['name']for p in data['packages']}==by_id
            result=dict(members=sorted(codes[by_id[x]]for x in data['workspace_members']),defaults=sorted(codes[by_id[x]]for x in data['workspace_default_members']),code=row['outcome']['exitCode'])
            metadata_default_pairs.setdefault(profile,{})[member]=result['defaults']
            assert before['lockSha256']==after['lockSha256']
            if case=='metadata-root':assert before['lockSha256']is None and not before['targetPresent']and not after['targetPresent']
            kinds.append('metadata')
        else:
            events=[json.loads(line)for line in stdout.splitlines()];artifacts=[e for e in events if e['reason']=='compiler-artifact'];by_id=profile_names[profile]
            if row['outcome']['exitCode']==0:assert any(e['reason']=='build-finished'and e['success']for e in events)
            else:assert mode==3 and not artifacts and '--exclude can only be used together with --workspace'in(run/(profile+'-'+case+'.stderr')).read_text();assert before==after
            for event in artifacts:
                name=by_id[event['package_id']];assert event['target']['kind']==(['lib']if name=='fixture-b'else['bin'])
                assert event['executable']is None and isinstance(event['fresh'],bool)
                if case=='workspace-exclude-b'and name=='fixture-b'and not event['fresh']:excluded_cold_b=True
            result=dict(checked=sorted({codes[by_id[e['package_id']]]for e in artifacts}),code=row['outcome']['exitCode']);kinds.append('check')
        expected.append(result)
    assert len(inputs)==32 and kinds.count('metadata')==8 and kinds.count('check')==24 and excluded_cold_b
    assert all(pair[True]==[2]for pair in metadata_default_pairs.values())
    assert metadata_default_pairs['root-a'][False]==[1]and metadata_default_pairs['root-a'][True]==[2]
    generated=HERE/'generated';generated.mkdir(exist_ok=True);path=generated/'workspaces.json'
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    env=dict(os.environ,LEAN_PATH=os.pathsep.join(str(ROOT/p)for p in ['.build/formal','.build']),BEND_NO_TELEMETRY='1')
    def replay(value):
        path.write_text(json.dumps(value)+'\n');return subprocess.run([lean,'--run','applications/cargo/WorkspacesCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True)
    result=replay(dict(schema=1,cases=inputs));assert result.returncode==0,result.stdout+result.stderr;actual=json.loads(result.stdout)
    assert [{k:r[k]for k in e}for r,e in zip(actual,expected,strict=True)]==expected,[(n,a,e)for n,a,e in zip(names,actual,expected,strict=True)if {k:a[k]for k in e}!=e]
    calls=[];bend_expected=[];bit=lambda b:'True{}'if b else'False{}';modes=['Default','WorkspaceExcludeB','ExplicitA','InvalidExclude']
    for row,result,kind in zip(inputs,expected,kinds,strict=True):
        arguments=','.join(bit(row[k])for k in ['rootPackage','explicitA','memberB'])
        if kind=='metadata':expression='C.defaults('+arguments+')';values=result['defaults']
        else:expression='C.checked(C.selected('+arguments+',C.'+modes[row['mode']]+'{}))';values=result['checked']
        calls.append('C.label('+expression+') ++ "\\n"');bend_expected.append(','.join(map(str,values)))
    runner=generated/'WorkspacesCase.bend';runner.write_text('import Base\nimport ../Workspaces.bend as C\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
    result=subprocess.run([bend,str(runner)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr;assert result.stdout.splitlines()==bend_expected
    for value,message in [(dict(schema=2,cases=[]),'Unsupported Cargo workspace schema'),(dict(schema=1,cases=[dict(inputs[0],mode=4)]),'Unknown Cargo workspace request')]:
        result=replay(value);assert result.returncode==2 and message in result.stderr
    path.write_text(json.dumps(dict(schema=1,cases=inputs),indent=2)+'\n');assert all(sha(ROOT/p)==h for p,h in basis.items()),'Input changed during replay.'
    report=dict(schema=1,basisSha256=basis,nativeCommands=36,metadataContextsMatchBothModels=8,checkMembershipAndStatusLeanCases=24,checkMembershipBendCases=24,targetsCleaned=4,invalidFlagRefusals=4,invalidResearchInputsRefused=2,
        coldExcludedDependencyReported=True,metadataDefaultMembersChangeWithContext=True,noDepsColdMetadataCreatedNoLock=True,
        rejectedInterpretations=['Workspace defaults are invariant under the effective manifest context.','Root default-members controls an ordinary invocation from every member.',
            'Excluding a workspace root prevents it from being checked as a dependency.','Cargo check reports are linked executable or runtime evidence.',
            'All metadata invocations necessarily create a lock or resolve dependency details.'],
        limits=['Four generated root/virtual/default-member profiles,normal A-to-B path dependency,two members,host default check profile only.',
            'Compiler-artifact membership and kind are observed;artifact bytes,full target/feature graphs,host/build/test splits and runtime are not independently verified.',
            'Selected roots for check requests are source/model interpretations;metadata default/member fields and compiler-reported packages are directly observed.',
            'Package IDs are opaque foreign keys mapped through actual metadata,not parsed as paths or names. Ordering and freshness machinery are not qualified.',
            'General globs,exclude patterns,workspace discovery,invalid manifests,dependencies outside members,alternate targets,concurrent/interrupted builds and other platforms remain open.'])
    (run/'conformance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='basisSha256'},indent=2))


if __name__=='__main__':main()
