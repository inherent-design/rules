"""Verify original selection captures and execute only finite Lean/Bend models."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from observations import packets

ROOT=Path(__file__).resolve().parents[3]
CAP=ROOT/'applications/evidence'
PRIMARY=CAP/'empack-selection-20261125T210902424596Z'
CONTROL=CAP/'empack-selection-control-20261125T211013721874Z'
FAILED=[CAP/'empack-selection-20261125T210710572931Z',CAP/'empack-selection-20261125T210753254393Z']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
write=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
FAILURES={None:0,'runtime-mismatch':1,'occupied-key':2,'retained-evidence':3,'not-installed':4,'invalid-pin':5,'invalid-project':6}


def evidence():
    unavailable=[]
    for row in load(ROOT/'applications/sources/empack-selection-policy-selections.json'):
        p=ROOT/row['cache']
        if p.exists():
            raw=p.read_bytes();assert sha(p)==row['sha256']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['gitBlob']
        else:unavailable.append(str(p))
    for run in [*FAILED,PRIMARY,CONTROL]:
        rows=load(run/'commands.json')
        for r in rows:
            assert r['groupAbsent'] and not r['timedOut']
            for stream in ['stdout','stderr']:assert sha(run/(r['label']+'.'+stream))==r[stream+'Sha256']
        if run in FAILED:
            review=load(run/'disposition.json')
            for n,h in review['originalFiles'].items():assert sha(run/n)==h
            assert review['allRecordedGroupsAbsent']
            assert rows[-1]['exitCode']==(1 if run==FAILED[0] else 101)
            continue
        receipt=load(run/'receipt.json');assert receipt['cases']==(19 if run==PRIMARY else 1) and receipt['allRecordedGroupsAbsent']
        assert len(rows)==2 and all(r['exitCode']==0 for r in rows)
        for file,field in [('probe.py','producerSha256'),('oracle.rs','driverSha256'),('fixture-source.rs','fixtureSha256'),('fixture-wrappers.rs','wrappersSha256'),('observed.stdout','observedSha256')]:assert sha(run/file)==receipt[field]
        prior=ROOT/receipt['priorCapture'];assert sha(prior/'receipt.json')==receipt['priorReceiptSha256']
        previous=load(prior/'receipt.json');assert previous['revision']==receipt['revision']=='0b4462e3032b4f09230b15329722eabefb7f574c'
        assert previous['librarySha256']==receipt['librarySha256'] and previous['sourceSha256']==receipt['sourceSha256']
        library=prior/'work/libempack_core.rlib'
        if library.exists():assert sha(library)==receipt['librarySha256']
        else:unavailable.append(str(library))
        compiler=Path(receipt['compiler']['path'])
        if compiler.exists():assert sha(compiler)==receipt['compiler']['sha256']
        else:unavailable.append(str(compiler))
        generated=run/'work/fixture.rs';binary=run/'work/selection-driver'
        for p,h in [(generated,receipt['generatedFixtureSha256']),(binary,receipt['binarySha256'])]:
            if p.exists():assert sha(p)==h
            else:unavailable.append(str(p))
        assert hashlib.sha256((run/'fixture-source.rs').read_bytes()+(run/'fixture-wrappers.rs').read_bytes()).hexdigest()==receipt['generatedFixtureSha256']
        repo=ROOT.parent/'empack'
        for p,h in receipt['sourceSha256'].items():
            if (repo/p).exists():assert sha(repo/p)==h
            else:unavailable.append(str(repo/p))
    prefix=[json.loads(s) for s in (FAILED[1]/'observed.stdout').read_text().splitlines()]
    main=[json.loads(s) for s in (PRIMARY/'observed.stdout').read_text().splitlines()]
    assert prefix==main[:6] and len(prefix)==6
    assert 'no method named `lock`' in (FAILED[0]/'compile.stderr').read_text()
    assert 'Release preference requires an unpinned provider request' in (FAILED[1]/'observed.stderr').read_text()
    return unavailable


def compare(a,b):assert a==b,'Selection research projection disagrees with native fields'


def main():
    unavailable=evidence();inputs,expected=packets(PRIMARY,CONTROL)
    write(PRIMARY/'model-input.json',inputs);write(PRIMARY/'observed-model-values.json',expected)
    proof=load(PRIMARY/'proof-gate.json');assert proof['observedExitCode']==0
    for p,h in proof['sourceSha256'].items():assert sha(ROOT/p)==h
    formal=ROOT/'.build/empack-selection-formal';formal.mkdir(parents=True,exist_ok=True)
    env={**os.environ,'LEAN_PATH':str(formal),'BEND_NO_TELEMETRY':'1'}
    lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend')
    command=[lean,'--run','applications/empack/selection/SelectionPolicyCase.lean']
    actual=json.loads(subprocess.check_output(command+[str(PRIMARY/'model-input.json')],cwd=ROOT,env=env,text=True));compare(actual,expected)
    b=lambda x:'True{}' if x else 'False{}'
    n=lambda x:str(x)+'n'
    s=lambda x:json.dumps(x)
    fields=[];wanted=[]
    def add(expr,value,kind='String'):
        fields.append(expr if kind=='String' else kind+'.show('+expr+')');wanted.append(str(value))
    for r,out in zip(inputs['preferences'],expected['preferences'],strict=True):
        add('P.effective('+','.join([s(r['project']),s(r['root'] or ''),s(r['operation'] or ''),b(r['root'] is not None),b(r['operation'] is not None),b(r['rootApplies'])])+')',out['actual'])
    for r,out in zip(inputs['admissions'],expected['admissions'],strict=True):add(f'P.valid_pin_preference({b(r["pinned"])},{b(r["preferencePresent"])})',out['accepted'],'Bool')
    keys={'a':0,'b':1,'c':2,'d':3}
    for r,out in zip(inputs['updates'],expected['updates'],strict=True):
        req=r['request'];args=','.join([n(keys[r['key']]),b(r['held']),n(r['version']),b(req is not None),n(keys[req['key']] if req else 0),n(req['version'] if req else 0),b(r['runtimeMismatch']),b(r['foreignIdentity']),b(r['evidenceMatches'])]);code='P.failure('+args+')'
        pinargs=','.join([b(r['held']),b(req is not None),n(keys[req['key']] if req else 0),n(req['version'] if req else 0)])
        prefargs=','.join(pinargs.split(',')[:3])
        add('P.accepted('+code+')',out['accepted'],'Bool');add(code,FAILURES[out['failure']],'Nat')
        add('P.optional_pin('+code+','+pinargs+')','none' if out['afterAuthorPin'] is None else 'some:'+out['afterAuthorPin'])
        add('P.optional_preference('+code+','+prefargs+')','none' if out['afterPreference'] is None else 'some:'+out['afterPreference'])
        add('P.selected('+code+','+n(r['version'])+')','none' if out['selected'] is None else 'some:'+str(out['selected']))
        for name,expr in [('changed',f'P.changed({code},{n(keys[r["key"]])},{n(r["version"])})'),('existing',f'P.existing({code},{n(keys[r["key"]])})'),('afterRoots',f'P.author_roots({code})')]:add(expr,json.dumps(out[name],separators=(',',':')))
        add('True{}',out['inputUnchanged'],'Bool');add('P.other_intent_preserved('+code+')',json.dumps(out['otherIntentPreserved']))
    replay=formal/'Replay.bend';replay.write_text('import ../../applications/empack/selection/SelectionPolicy.bend as P\nimport Base\ndef main() -> IO(Unit):\n  IO.write('+' ++ "\\n" ++ '.join(fields)+' ++ "\\n")\n')
    result=subprocess.run([bend,str(replay)],cwd=ROOT,env=env,text=True,capture_output=True,check=True);compare(result.stdout.splitlines(),wanted)
    assert len(wanted)==137
    controls=[]
    changes=[('operation-override-lost','preferences','operation-override','actual','stable-only'),('pin-preference-invalid-admitted','admissions','pin-and-preference-invalid','accepted',True),('automatic-minted-pin','updates','automatic-keeps-author-policy','afterAuthorPin','Version2'),('pin-kept-automatic-preference','updates','explicit-pin-replaces-root-preference','afterPreference','stable-only'),('held-silently-updated','updates','held-without-reviewed-pin','accepted',True),('equality-ignored-evidence','updates','same-held-pin','accepted',True),('matching-evidence-refused','updates','same-held-pin-matching-evidence','accepted',False),('retained-promoted','updates','retained-without-promotion','afterRoots',['a','c']),('input-mutated','updates','automatic-keeps-author-policy','inputUnchanged',False),('unrelated-author-fields-lost','updates','held-reviewed-pin','otherIntentPreserved',False)]
    for label,section,identity,key,value in changes:
        changed=copy.deepcopy(expected);r=next(x for x in changed[section] if x['id']==identity);r[key]=value
        try:compare(actual,changed)
        except AssertionError:controls.append(label)
        else:raise AssertionError(label)
    for label,change in [('schema',lambda x:x.update(schema=2)),('preference',lambda x:x['preferences'][0].update(project='unknown')),('key',lambda x:x['updates'][0].update(key='b')),('version',lambda x:x['updates'][0].update(version=4)),('exact-request',lambda x:x['updates'][1]['request'].update(version=0)),('evidence-profile',lambda x:x['updates'][0].update(evidenceMatches=True))]:
        changed=copy.deepcopy(inputs);change(changed);path=formal/(label+'.json');write(path,changed)
        result=subprocess.run(command+[str(path)],cwd=ROOT,env=env,text=True,capture_output=True)
        assert result.returncode==2 and 'research' in result.stderr
        controls.append(label)
    runs=[*FAILED,PRIMARY,CONTROL]
    files=[p for run in runs for p in run.rglob('*') if p.is_file() and 'work' not in p.relative_to(run).parts and p.name not in ['basis.json','conformance.json']]
    files += [p for p in (ROOT/'applications/empack/selection').iterdir() if p.is_file()]
    files += [ROOT/'applications/empack/SELECTION.md',ROOT/'applications/sources/empack-selection-policy-selections.json']
    write(PRIMARY/'basis.json',{str(p.relative_to(ROOT)):sha(p) for p in files})
    report=dict(schema=1,nativeCaseFrames=20,rawRowsIncludingRepeatedPrefix=26,preferenceFrames=6,admissionFrames=1,updateFrames=13,dualFieldComparisons=len(wanted),leanLaws=26,bendLaws=18,controls=controls,basisFiles=len(files),unavailableArtifacts=unavailable,limits=['Actual unchanged-core value calls; fictional pins/digests and synthetic caller revision. No catalog/codec/CLI/native publication or game test.','Initial getter compile failure contributes zero cases; partial driver contributes six repeated preference rows, not six extra cases.','Complete graph and one-root fixture profile are frozen caller premises, not a general graph decoder or closure proof.','After-preference parsing is a bounded Rust Debug witness, not a stable public codec.','Four Lean/two Bend assessment-completeness laws are source-only, not native assessment observations.'])
    write(PRIMARY/'conformance.json',report);print(json.dumps(report,indent=2))


if __name__=='__main__':main()
