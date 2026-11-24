#!/usr/bin/env python3
"""Replay retained workspace command effects; no package-manager execution."""
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


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path);run=parser.parse_args().run.resolve()
    receipt=json.loads((run/'receipt.json').read_text());trace=json.loads((run/'trace.json').read_text());configs=json.loads((run/'configuration.json').read_text())
    assert receipt['schema']==1 and receipt['commands']==len(trace)==27
    assert sha(run/'probe.py')==receipt['producerSha256']
    ledger=ROOT/'applications/sources/js-workspaces-selections.json';sources=json.loads(ledger.read_text())['sources']
    for source in sources:assert sha(ROOT/source['cache'])==source['sha256']
    inputs=[HERE/p for p in ['Workspaces.lean','WorkspacesCase.lean','Workspaces.bend','workspaces_probe.py','workspaces_conformance.py']]
    inputs += [ledger,*[run/p for p in ['receipt.json','trace.json','configuration.json','probe.py','retention.json']]]
    for row in trace:
        assert not row['outcome']['timedOut']
        for stream in ['stdout','stderr']:
            path=run/(row['app']+'-'+row['case']+'.'+stream);inputs.append(path);assert sha(path)==row['observed'][stream+'Sha256']
    basis={str(p.relative_to(ROOT)):sha(p)for p in inputs}
    rows=[];expected=[];names=[];native_failures=[]
    ids={'fixture-root':0,'fixture-a':1,'fixture-b':2,'fixture-c':3,'fixture-d':4}
    for row in trace:
        manager=row['app'];after=row['observed']['after'];before=row['observed']['before']
        if row['case']=='install':
            assert row['outcome']['exitCode']==0 and not row['observed']['effects']
            continue
        assert before['projectFiles']==after['projectFiles'],'A workspace run changed selected source/lock files.'
        for path,text in configs[manager].items():
            assert hashlib.sha256(text.encode()).hexdigest()==before['projectFiles'][path]
        args=row['argv'][2 if manager=='yarn'else 1:]
        prefix=row['argv'][:2 if manager=='yarn'else 1]
        assert prefix==([receipt['tools']['node']['path'],receipt['tools']['yarn']['path']]if manager=='yarn'else[receipt['tools'][manager]['path']])
        mode=0
        if manager=='npm':
            if '--workspace'in args:
                selected=args[args.index('--workspace')+1];assert selected in ['fixture-a','not-a-workspace'];mode=3 if selected=='fixture-a'else 6
            elif '--workspaces'in args:mode=2 if '--include-workspace-root'in args else 1
            topological=False;bail=False;if_present='--if-present'in args
        elif manager=='pnpm':
            if '--filter'in args:
                selected=args[args.index('--filter')+1];selectors={'fixture-a':3,'fixture-a...':4,'...fixture-b':5,'not-a-workspace':6};assert selected in selectors;mode=selectors[selected]
                if mode==6:assert '--fail-if-no-match'in args
            elif '-r'in args:mode=2 if '--include-workspace-root'in args else 1
            topological=mode!=0;bail='--no-bail'not in args;if_present=True
        else:
            if args[:2]==['workspaces','foreach']:
                if '--all'in args:mode=2
                else:assert args[args.index('--from')+1]=='fixture-a'and'--recursive'in args;mode=4
            elif args[0]=='workspace':
                assert args[1]in ['fixture-a','not-a-workspace'];mode=3 if args[1]=='fixture-a'else 6
            topological='--topological'in args;bail=True;if_present=True
        command=args[args.index('run')+1];assert command in ['probe','absent']
        packages=[]
        for path in ['package.json',*[f'packages/{name}/package.json'for name in ['a','b','c','d']]]:
            package=json.loads(configs[manager][path]);dependencies=[]
            for name,value in package.get('dependencies',{}).items():
                assert name=='fixture-b'and value==('1.0.0'if manager=='npm'else'workspace:*');dependencies.append(ids[name])
            packages.append(dict(id=ids[package['name']],name=package['name'],dependencies=dependencies,script=command in package.get('scripts',{})))
        projected=dict(app=['npm','pnpm','yarn'].index(manager),mode=mode,topological=topological,bail=bail,ifPresent=if_present,failB=row['fail']=='fixture-b',packages=packages)
        events=row['observed']['effects'];started=[];failed=[]
        assert len(events)%2==0
        for start,end in zip(events[::2],events[1::2],strict=True):
            assert start['phase']=='start'and end['phase']in ['succeeded','failed']and start['actor']==end['actor']
            actor=start['actor'];assert actor in ids
            original=Path(receipt['originalWork'])/manager/'project';expected_cwd=original if actor=='fixture-root'else original/'packages'/actor[-1]
            assert start['cwd']==end['cwd']==str(expected_cwd)
            started.append(ids[actor])
            if end['phase']=='failed':assert row['fail']==actor;failed.append(ids[actor])
        assert len(set(started))==len(started)
        rows.append(projected);names.append(manager+'/'+row['case']);expected.append(dict(started=started,failed=failed,code=row['outcome']['exitCode']))
        if row['fail']:native_failures.append((manager,bail,started,failed))
    assert len(rows)==24 and len(native_failures)==4
    generated=HERE/'generated';generated.mkdir(exist_ok=True);path=generated/'workspaces.json'
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    env=dict(os.environ,LEAN_PATH=os.pathsep.join(str(ROOT/p)for p in ['.build/formal','.build']),BEND_NO_TELEMETRY='1')
    def replay(value):
        path.write_text(json.dumps(value)+'\n');return subprocess.run([lean,'--run','applications/js-scripts/WorkspacesCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True)
    result=replay(dict(schema=1,cases=rows));assert result.returncode==0,result.stdout+result.stderr;actual=json.loads(result.stdout)
    assert [{k:r[k]for k in ['started','failed','code']}for r in actual]==expected,[(n,a,e)for n,a,e in zip(names,actual,expected,strict=True)if {k:a[k]for k in e}!=e]
    # The native script log establishes actual dispatch and completion. Selected
    # membership and blocked reasons are source/model interpretations,not an
    # invented native JSON API.
    by_name=dict(zip(names,actual,strict=True))
    assert by_name['pnpm/failed-b-no-bail']['blocked']==[1]
    assert by_name['npm/members']['started']==[1,2,3] and by_name['yarn/members']['started']==[1,2,3,0]
    assert by_name['pnpm/selected-a']['started']==[1] and by_name['pnpm/a-and-dependencies']['started']==[2,1]
    assert by_name['npm/members-missing']['code']!=0 and by_name['npm/members-missing']['started']==[1,2,3]
    calls=[];decisions=[]
    for manager,bail,started,failed in native_failures:
        assert failed==[2]
        policy='W.NpmSequential{}'if manager=='npm'else'W.YarnSerial{}'if manager=='yarn'else'W.PnpmGraph{'+('True{}'if bail else'False{}')+'}'
        calls.append('Bool.show(W.independent_after_failure('+policy+')) ++ "\\n"');decisions.append(3 in started)
        if manager!='npm':
            calls.append('Bool.show(W.dependent_after_failure('+policy+')) ++ "\\n"');decisions.append(1 in started)
        else:assert started.index(1)<started.index(2),'npm A ran before B failed;not evidence of a later dependent admission.'
    runner=generated/'WorkspacesCase.bend';runner.write_text('import Base\nimport ../Workspaces.bend as W\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
    result=subprocess.run([bend,str(runner)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr;assert result.stdout.splitlines()==[str(value)for value in decisions]
    invalids=[('schema',dict(schema=2,cases=[]),'Unsupported workspace schema'),
        ('manager',dict(schema=1,cases=[dict(rows[0],app=3)]),'Unknown workspace manager'),
        ('selector',dict(schema=1,cases=[dict(rows[0],mode=7)]),'Unknown workspace selector')]
    changed=copy.deepcopy(rows[0]);changed['packages'][1]['dependencies']=[3]
    invalids.append(('graph',dict(schema=1,cases=[changed]),'dependency graph is outside'))
    changed=copy.deepcopy(rows[0]);changed['packages'].reverse()
    invalids.append(('order',dict(schema=1,cases=[changed]),'package order is outside'))
    for label,value,message in invalids:
        result=replay(value);assert result.returncode==2 and message in result.stderr,(label,result.stdout,result.stderr)
    path.write_text(json.dumps(dict(schema=1,cases=rows),indent=2)+'\n')
    assert all(sha(ROOT/p)==h for p,h in basis.items()),'Replay inputs changed while consumed.'
    report=dict(schema=1,basisSha256=basis,nativeCommands=27,nativeWorkspaceRuns=24,leanObservableTracesMatch=24,
        bendLocalContinuationDecisions=len(decisions),refusedResearchInputs=[r[0]for r in invalids],
        inferredBlockedReason='pnpm no-bail leaves A undispatched because B failed;source scheduler propagates failed dependency blocking. Native script log independently establishes A did not run.',
        rejectedInterpretations=['Every recursive workspace command includes the root.','Selecting A necessarily runs its dependencies.',
            'Workspace dependency declarations force npm script iteration to run dependencies first.','No-bail runs failed dependencies\' dependents.',
            'Any missing member script makes the whole operation refuse before effects.','Nonzero aggregate status means no workspace succeeded.'],
        limits=['Root and four generated members,one normal A-to-B workspace edge,no cycles/dev/optional/peer edges,one ordinary script and serial execution.',
            'Model selection/parser adapter admits only captured exact-name/closure profiles;not general globs,workspace discovery,semver or complete task graph construction.',
            'Native script events establish execution/status;selected membership and blocked reasons are separately attributed source/model interpretations.',
            'Bend compares seven local continuation decisions after a failed B,not the complete ordered scheduler. npm A ran before B;no later-dependent comparison is claimed.',
            'Only selected source/lock hashes and generated effect log were observed;cache/log/global effects not exhaustively measured. No rollback,signal/concurrent-job/native retirement proof.',
            'npm installed run source matches selected npm pin;Rust pnpm/Yarn source refs are independently attributed,not proved reproducible builds.'])
    (run/'conformance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='basisSha256'},indent=2))


if __name__=='__main__':main()
