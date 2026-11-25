"""Read retained Yarn workspace effects; run only the two finite research models."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

from observations import NAMES, packets, version_tuple

ROOT=Path(__file__).resolve().parents[2]
RUNS=[ROOT/'applications/evidence'/name for name in ['yarn-version-20261125T193018678360Z',
      'yarn-version-20261125T193101756734Z','yarn-version-20261125T193206031858Z']]
RUN=RUNS[0]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())


def write(p,value):
    p.write_text(json.dumps(value,indent=2)+'\n')


def compare(actual,expected):
    assert actual==expected,'Version decision differs from retained observation'


def images(values):
    for path,row in values.items():
        assert not Path(path).is_absolute() and '..' not in Path(path).parts
        if row['kind']=='link':
            assert stat.S_ISLNK(row['mode'])
        else:
            assert row['kind']=='file' and stat.S_ISREG(row['mode'])
            assert hashlib.sha256(bytes.fromhex(row['bytesHex'])).hexdigest()==row['sha256']


def evidence():
    sources,unavailable,tools=[],[],{}
    tree=ROOT/'applications/tools/source-cache/js-scripts/yarn-tree.json'
    objects={r['path']:r['sha'] for r in load(tree)['tree'] if r['type']=='blob'} if tree.exists() else None
    for ledger in ['yarn-version-selections.json','yarn-version-scope-context.json']:
        for item in load(ROOT/'applications/sources'/ledger):
            p=ROOT/item['cache']
            if p.exists():
                assert sha(p)==item['sha256']
                raw=p.read_bytes()
                assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==item['gitBlob']
                if objects is not None:
                    assert objects[item['path']]==item['gitBlob']
                sources.append(item['path'])
            else:
                unavailable.append(item['cache'])
    last={}
    for run,count,complete in zip(RUNS,[18,6,4],[False,True,True],strict=True):
        setup,receipt=load(run/'setup.json'),load(run/'receipt.json')
        assert sha(run/'probe.py')==setup['producerSha256']
        assert sha(ROOT/'applications/sources/yarn-version-selections.json')==setup['sourceLedgerSha256']
        assert receipt['complete']==complete and receipt['commands']==count and receipt['allRecordedGroupsAbsent']
        assert receipt['workPathProcessMatches']==[]
        for name,item in setup['tools'].items():
            p=Path(item['path'])
            if p.exists():
                if str(p) not in tools:
                    assert sha(p)==item['sha256'];tools[str(p)]=item['sha256']
                else:
                    assert tools[str(p)]==item['sha256']
            else:
                unavailable.append(item['path'])
        rows=load(run/'commands.json');assert len(rows)==count
        for row in rows:
            assert not row['timedOut'] and row['processGroupAbsent'] and row['exitCode'] in [0,1]
            assert not any(s in row['argv'] for s in ['publish','npm','run','exec'])
            for stream in ['stdout','stderr']:
                assert sha(run/(row['id']+'.'+stream))==row['streams'][stream]
            images(row['before']);images(row['after'])
            if row['gitBefore'] is not None:
                assert row['gitBefore']['head']==row['gitAfter']['head']
                assert row['gitBefore']['indexSha256']==row['gitAfter']['indexSha256']
            last[row['project']]=row['after']
    for project,values in last.items():
        for rel,item in values.items():
            p=Path(project)/rel
            if item['kind']=='link':
                if p.is_symlink():
                    assert os.readlink(p)==item['target'] and p.lstat().st_mode==item['mode']
                else:
                    unavailable.append(str(p))
            elif p.exists():
                assert not p.is_symlink() and sha(p)==item['sha256']
                assert p.stat().st_mode==item['mode'] and p.stat().st_mtime_ns==item['mtimeNs']
            else:
                unavailable.append(str(p))
    qualification=load(RUN/'scope-qualification.json')
    assert qualification['preservedSetupSha256']==sha(RUN/'setup.json') and qualification['preservedProducerSha256']==sha(RUN/'probe.py')
    rows=load(RUNS[2]/'commands.json');repair,=load(RUNS[2]/'owner-edits.json')
    images(repair['before']);images(repair['after'])
    assert repair['before']==rows[2]['after'] and repair['after']==rows[3]['before']
    changed=[p for p in repair['before'] if repair['before'][p]!=repair['after'][p]]
    assert changed==['packages/alpha/package.json']
    a=json.loads(bytes.fromhex(repair['before'][changed[0]]['bytesHex']));b=json.loads(bytes.fromhex(repair['after'][changed[0]]['bytesHex']))
    assert a.pop('devDependencies')=={'rules-version-missing':'file:../../missing.tgz'} and a==b
    upstream=load(RUNS[2]/'upstream-status.json')
    assert upstream['version']=='4.19.0' and upstream['dist']['integrity']==load(RUNS[2]/'setup.json')['tools']['yarn']['registryIntegrity']
    return dict(availableSourceFiles=sources,unavailableArtifacts=unavailable,availableTools=len(tools),privateLastProjects=len(last))


def main():
    identities=evidence();inputs,expected,facts=packets(RUNS)
    assert [len(expected[k]) for k in ['scopes','records','applies','checks','ranges']]==[3,9,27,3,18]
    assert len(facts)==28
    for name,value in [('model-input.json',inputs),('observed-model-values.json',expected),('effect-facts.json',facts)]:
        write(RUN/name,value)
    proof=load(RUN/'proof-gate.json');assert proof['observedExitCode']==0
    for p,digest in proof['sourceSha256'].items():
        assert sha(ROOT/p)==digest
    formal=ROOT/'.build/yarn-version-formal';formal.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=str(formal),BEND_NO_TELEMETRY='1')
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    command=[lean,'--run','applications/yarn-version/VersionsCase.lean']
    actual=json.loads(subprocess.check_output(command+[str(RUN/'model-input.json')],cwd=ROOT,env=env,text=True))
    compare(actual,expected)
    calls,wanted=[],[]
    b=lambda v:'True{}' if v else 'False{}'
    n=lambda v:str(v)+'n'
    def add(expr,value,number=False):
        calls.append(('Nat' if number else 'Bool')+'.show(P.'+expr+')');wanted.append(str(value))
    for r,out in zip(inputs['scopes'],actual['scopes'],strict=True):
        for candidate in [2,1,0]:
            add(f'scope({n(r["root"])},{n(candidate)},{b(r["recursive"])})',candidate in out['selected'])
    for r,out in zip(inputs['records'],actual['records'],strict=True):
        lower=version_tuple(r['target'])<version_tuple(r['current'])
        allowed=f'record_allowed({b(r["decline"])},{b(lower)},{b(r["force"])})'
        add(allowed,out['accepted'])
        add(f'record_decision(P.{allowed},{b(r["dryRun"])},{b(r["priorDecision"])})',out['decision'])
        add(f'record_bump(P.{allowed},{b(r["dryRun"])},{b(r["decline"])},{b(r["priorBump"])})',out['bump'])
    for r,out in zip(inputs['applies'],actual['applies'],strict=True):
        allowed=f'P.allowed({b(r["anySelectedLower"])},{b(r["force"])})'
        saved=f'P.saved({allowed},{b(r["hasRelease"])},{b(r["dryRun"])},{b(r["inputAvailable"])},{b(r["selected"])})'
        for part in ['major','minor','patch']:
            add(f'selected_number({n(r["current"][part])},{n(r["target"][part])},{saved})',out['version'][part],True)
        add(f'retained({allowed},{b(r["hasRelease"])},{b(r["dryRun"])},{b(r["selected"])})',out['retained'])
        add(f'announced({allowed},{b(r["hasRelease"])},{b(r["selected"])})',out['announced'])
        add(saved[2:],out['saved'])
        add(f'successful({allowed},{b(r["dryRun"])},{b(r["inputAvailable"])})',out['successful'])
    for r,out in zip(inputs['checks'],actual['checks'],strict=True):
        add('check('+','.join(b(r[k]) for k in ['changedA','changedB','changedC','decidedA','decidedB','decidedC','bumpA','bumpB'])+')',out['successful'])
    for r,out in zip(inputs['ranges'],actual['ranges'],strict=True):
        for part in ['major','minor','patch']:
            add(f'selected_number({n(r["old"][part])},{n(r["target"][part])},{b(r["saved"])})',out['target'][part],True)
    target=formal/'Replay.bend'
    target.write_text('import ../../applications/yarn-version/Versions.bend as P\nimport Base\ndef main() -> IO(Unit):\n  IO.write('+' ++ "\\n" ++ '.join(calls)+' ++ "\\n")\n')
    result=subprocess.run([bend,str(target)],cwd=ROOT,env=env,text=True,capture_output=True,check=True)
    compare(result.stdout.splitlines(),wanted);assert len(wanted)==282
    controls=[]
    for label,kind,index,key in [('documented-dependent-direction','scopes',0,'selected'),('valid-record-was-refused','records',0,'accepted'),
                                ('failed-apply-keeps-record','applies',21,'retained'),('reported-target-is-saved','applies',21,'saved'),
                                ('failure-is-success','applies',21,'successful'),('undecided-check-is-valid','checks',0,'successful'),
                                ('decline-not-a-decision','checks',2,'successful')]:
        changed=copy.deepcopy(expected)
        row=changed[kind][index]
        row[key]=[0,1,2] if key=='selected' else not row[key]
        try:compare(actual,changed)
        except AssertionError:controls.append(label)
        else:raise AssertionError('Changed native interpretation escaped')
    for label,change in [('schema',lambda d:d.update(schema=2)),('scope',lambda d:d['scopes'][0].update(root=3)),
                         ('lower-witness',lambda d:d['applies'][0].update(hasRelease=True,target={'major':0,'minor':0,'patch':0},anySelectedLower=False))]:
        changed=copy.deepcopy(inputs);change(changed);p=formal/(label+'.json');write(p,changed)
        r=subprocess.run(command+[str(p)],cwd=ROOT,env=env,text=True,capture_output=True)
        assert r.returncode==2 and 'research' in r.stderr
        controls.append(label)
    # A lower record outside the selected scope is retained, not an authority failure.
    changed=copy.deepcopy(inputs)
    changed['applies']=[dict(changed['applies'][0],selected=False,hasRelease=True,target={'major':0,'minor':0,'patch':0},anySelectedLower=False)]
    p=formal/'unselected-lower.json';write(p,changed)
    projected=json.loads(subprocess.check_output(command+[str(p)],cwd=ROOT,env=env,text=True))['applies'][0]
    assert projected['successful'] and projected['retained'] and not projected['saved'] and not projected['announced']
    model_controls=['unselected-lower-is-not-selected-authority']
    files=[p for run in RUNS for p in run.iterdir() if p.is_file() and p.name not in ['basis.json','conformance.json']]
    files += [p for p in (ROOT/'applications/yarn-version').iterdir() if p.is_file()]
    files += [ROOT/'applications/sources'/n for n in ['yarn-version-selections.json','yarn-version-scope-context.json']]
    write(RUN/'basis.json',{str(p.relative_to(ROOT)):sha(p) for p in files})
    report=dict(schema=1,**identities,nativeCommands=28,qualifiedVersionCommands=24,earlierLockGuardChecksExcluded=3,fixtureInstallCommands=1,
                scopeFrames=3,recordFrames=9,workspaceApplyFrames=27,checkFrames=3,rangeFrames=18,dualScalarComparisons=282,
                leanLaws=26,bendLaws=16,negativeControls=controls,modelOnlyControls=model_controls,basisFiles=len(files),
                limits=['Three-workspace acyclic fixture and stable numeric versions; no general graph, semver, YAML or range-parser conformance.',
                        'Installation is workspace-only; controlled failure is a deliberately missing own local archive. No registry/hooks/game/global tool updates.',
                        'Initial lock-guard failure is preserved and excluded from decision-check claims; reason-qualified checks use a fresh initialized fixture.',
                        'Proposed resolved-target retention/acknowledgement laws are not a native patch or a qualified crash/recovery protocol.',
                        'No interruption, concurrent writers, full Git staging, I/O fault matrix, prerelease or cross-platform qualification.'])
    write(RUN/'conformance.json',report);print(json.dumps(report,indent=2))


if __name__=='__main__':main()
