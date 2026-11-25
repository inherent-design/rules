"""Check retained type/placement evidence; execute only finite Lean/Bend models."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import zipfile

from observations import packets

ROOT=Path(__file__).resolve().parents[3]
PRIMARY=ROOT/'applications/evidence/empack-content-kinds-20261125T200444932279Z'
SYNC=ROOT/'applications/evidence/empack-content-kinds-sync-20261125T200904777793Z'
LAYOUT=ROOT/'applications/evidence/empack-content-kinds-layout-20261125T201053173979Z'
RUNS=[PRIMARY,SYNC,LAYOUT]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())


def write(p,data):p.write_text(json.dumps(data,indent=2)+'\n')
def compare(a,b):assert a==b,'Typed content differs from the retained observation'


def image(values):
    for path,item in values.items():
        assert not Path(path).is_absolute() and '..' not in Path(path).parts
        if item['kind']=='file':
            assert hashlib.sha256(bytes.fromhex(item['bytesHex'])).hexdigest()==item['sha256']
        else:assert item['kind'] in ['directory','link']


def evidence():
    available=[];unavailable=[]
    ledger=ROOT/'applications/sources/empack-content-kinds-selections.json'
    source_rows=load(ledger)+load(ROOT/'applications/sources/empack-content-kinds-policy-context.json')
    for row in source_rows:
        p=ROOT/row['cache']
        if p.exists():
            raw=p.read_bytes();assert sha(p)==row['sha256']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['gitBlob']
            available.append(row['path'])
        else:unavailable.append(row['cache'])
    for row in load(ROOT/'applications/sources/empack-content-kinds-host-context.json')['rows']:
        p=ROOT/row['sourceCache']
        if p.exists():
            assert sha(p)==row['sourceSha256']
            assert 'endsWith(".zip")' in p.read_text()
            available.append(row['sourceCache'])
        else:unavailable.append(row['sourceCache'])
    setup=load(PRIMARY/'setup.json');binary=Path(setup['binary'])
    binary_available=binary.exists()
    if binary_available:assert sha(binary)==setup['binarySha256']
    assert sha(ledger)==setup['sourceLedgerSha256'] and sha(PRIMARY/'probe.py')==setup['producerSha256']
    continuation=load(PRIMARY/'continuation.json')
    assert sha(PRIMARY/'continue-probe.py')==continuation['producerSha256']
    assert sha(PRIMARY/'setup.json')==continuation['preservedSetupSha256']
    assert sha(PRIMARY/'initial-receipt.json')==continuation['initialReceiptSha256']
    assert load(PRIMARY/'initial-receipt.json')['complete'] is False
    rows_by_run=[]
    for run,count in zip(RUNS,[17,3,2],strict=True):
        receipt=load(run/'receipt.json');assert receipt['complete'] and receipt['commands']==count and receipt['allRecordedGroupsAbsent']
        if receipt['workPathProcessMatches']:
            review=load(run/'closure-review.json')
            assert review['receiptSha256']==sha(run/'receipt.json') and not review['currentWorkRootMatches']
            assert [hashlib.sha256(m.encode()).hexdigest() for m in receipt['workPathProcessMatches']]==[m['commandSha256'] for m in review['originalMatches']]
            assert review['allRecordedCliGroupsAbsent']
            for text in receipt['workPathProcessMatches']:
                assert text.split(None,1)[1].startswith('/opt/homebrew/bin/bash -lc ')
        else:
            assert not receipt['workPathProcessMatches']
        rows=load(run/'commands.json');assert len(rows)==count and len({r['id'] for r in rows})==count
        for row in rows:
            assert row['processGroupAbsent'] and not row['timedOut']
            assert row['exitCode'] in [0,1,2]
            assert '--state-dir' in row['argv'] and '--cache-dir' in row['argv']
            assert row['argv'][row['argv'].index('--state-dir')+1]==setup['work']+'/state'
            assert row['argv'][row['argv'].index('--cache-dir')+1]==setup['work']+'/cache'
            assert not any(a in row['argv'] for a in ['build','launch','release','instance','--online'])
            for stream in ['stdout','stderr']:assert sha(run/(row['id']+'.'+stream))==row['streams'][stream]
            image(row['before']);image(row['after'])
        rows_by_run.append(rows)
    original=rows_by_run[0]
    assert [r['id'] for r in original[:2]]==['initialize','implicit-module']
    assert original[1]['exitCode']==1 and original[1]['before']==original[1]['after']
    assert 'Cannot read direct dependency input' in (PRIMARY/'implicit-module.stderr').read_text()
    assert all(r['id'].startswith('continued-') for r in original[2:])
    for run,previous,rows in zip([SYNC,LAYOUT],rows_by_run[:2],rows_by_run[1:],strict=True):
        current=load(run/'setup.json')
        assert current['basisCapture']==str((PRIMARY if run==SYNC else SYNC).relative_to(ROOT))
        assert current['basisCommandsSha256']==sha((PRIMARY if run==SYNC else SYNC)/'commands.json')
        assert current['producerSha256']==sha(run/'sync_probe.py') and current['fixtureSha256']==sha(run/'probe.py')
        edit,=load(run/'owner-edits.json');image(edit['before']);image(edit['after'])
        assert edit['before']==previous[-1]['after'] and edit['after']==rows[0]['before']
        assert [p for p in edit['before'] if edit['before'][p]!=edit['after'][p]]==['empack.yml']
    first_edit,=load(SYNC/'owner-edits.json')
    old=bytes.fromhex(first_edit['before']['empack.yml']['bytesHex']).decode()
    new=bytes.fromhex(first_edit['after']['empack.yml']['bytesHex']).decode()
    assert new==old.replace('\nbuild:\n','\n  unknown:\n    path: vendor/unknown.jar\n    type: mod\nbuild:\n')
    before=load(SYNC/'before-manifest.json');after=load(SYNC/'after-manifest.json')
    a=next(r for r in before['dependencies'] if r['key']=='unknown');b=next(r for r in after['dependencies'] if r['key']=='unknown')
    assert before['lock_status']=='stale' and a['selection_satisfied'] is False and a['reason']=='No recorded selection'
    assert after['lock_status']=='current' and b['selection_satisfied'] is True and b['reason'] is None
    assert a['effective']==b['effective']
    for artifact in setup['artifacts']:
        path=PRIMARY/'inputs'/artifact['filename'];assert sha(path)==artifact['sha256'] and path.stat().st_size==artifact['bytes']
        with zipfile.ZipFile(io.BytesIO(path.read_bytes())) as z:
            assert z.testzip() is None and len(z.infolist())==len(artifact['members'])
            for member in artifact['members']:
                raw=z.read(member['path']);assert raw==bytes.fromhex(member['bytesHex']) and hashlib.sha256(raw).hexdigest()==member['sha256']
        for rows in rows_by_run:
            for row in rows:
                item=row['after']['vendor/'+artifact['filename']]
                assert item['sha256']==artifact['sha256']
    # Only the latest postimage describes the live fixture after the explicit edit chains.
    project=Path(setup['work'])/'project'
    if project.exists():
        for relative,item in rows_by_run[-1][-1]['after'].items():
            p=project/relative
            if item['kind']=='file':
                assert not p.is_symlink() and sha(p)==item['sha256']
                assert p.stat().st_mode==item['mode'] and p.stat().st_mtime_ns==item['mtimeNs']
            elif item['kind']=='directory':assert p.is_dir() and not p.is_symlink()
            else:assert p.is_symlink() and os.readlink(p)==item['target']
    else:unavailable.append(str(project))
    return dict(availableSourceFiles=available,unavailableArtifacts=unavailable,binaryReadback=binary_available)


def main():
    identities=evidence();inputs,expected=packets(PRIMARY,SYNC,LAYOUT)
    assert [len(expected[k]) for k in ['admissions','metadata','placements','suffixes']]==[15,8,2,3]
    write(PRIMARY/'model-input.json',inputs);write(PRIMARY/'observed-model-values.json',expected)
    proof=load(PRIMARY/'proof-gate.json');assert proof['observedExitCode']==0
    for p,digest in proof['sourceSha256'].items():assert sha(ROOT/p)==digest
    formal=ROOT/'.build/empack-content-kinds-formal';formal.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=str(formal),BEND_NO_TELEMETRY='1')
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    command=[lean,'--run','applications/empack/content-kinds/ContentKindsCase.lean']
    actual=json.loads(subprocess.check_output(command+[str(PRIMARY/'model-input.json')],cwd=ROOT,env=env,text=True))
    compare(actual,expected)
    calls=[];wanted=[]
    b=lambda v:'True{}' if v else 'False{}'
    n=lambda v:str(v)+'n'
    s=lambda v:json.dumps(v,ensure_ascii=True)
    def add(expr,value,kind='Bool'):
        calls.append(kind+'.show(P.'+expr+')' if kind!='String' else 'P.'+expr)
        wanted.append(str(value))
    for r,out in zip(inputs['admissions'],actual['admissions'],strict=True):
        k=r['explicit'] if r['explicit'] is not None else 0
        chosen=r['explicit'] is not None or r['jar']
        folder=r['override'] is not None or k in [0,1,2]
        m=r['markers']
        recognize=f'P.recognized({n(k)},'+','.join(b(m[a]) for a in ['module','pack','assets','data','shaders'])+')'
        code=f'reason({b(chosen)},{n(k)},{b(folder)},{b(r["validArchive"])},{b(m["projectRoot"] or m["worldRoot"])},{recognize},{b(r["acceptUnknown"])},{n(r["worldRoots"])},{b(r["worldNonempty"] is True)},{b(r["worldInside"] is True)})'
        add(f'admitted(P.{code})',out['admitted']);add(code,out['reason'],'Nat')
        add(f'materialized(P.{code},{b(r["dryRun"])})',out['materialized'])
        add(f'outputs(P.{code},{b(r["dryRun"])},{n(k)},{n(r["worldMembers"])})',out['outputs'],'Nat')
    for r,out in zip(inputs['metadata'],actual['metadata'],strict=True):
        add(f'canonical({n(r["kind"])})',out['content'],'String');add(f'server({n(r["kind"])})',out['serverRequired'])
        add(f'source_kind({n(r["kind"])})',out['sourceKind'],'String')
        for dest,member in zip(out['destinations'],r['members'] if r['kind']==4 else [None],strict=True):
            expr=f'world_member({s(r["base"])},{s(r["key"])},{s(member)})' if member is not None else f'ordinary({s(r["base"])},{s(r["filename"])})'
            add(expr,dest,'String')
    for r,out in zip(inputs['placements'],actual['placements'],strict=True):
        add(f'placement({b(r["automatic"])},{s(r["fixed"])},{s(r["base"])},{s(r["filename"])})',out['destination'],'String')
    for r,out in zip(inputs['suffixes'],actual['suffixes'],strict=True):
        add(f'suffix({b(r["regular"])},{b(r["filename"].endswith(".zip"))})',out['candidate'])
    path=formal/'Replay.bend'
    path.write_text('import ../../applications/empack/content-kinds/ContentKinds.bend as P\nimport Base\ndef main() -> IO(Unit):\n  IO.write('+' ++ "\\n" ++ '.join(calls)+' ++ "\\n")\n')
    result=subprocess.run([bend,str(path)],cwd=ROOT,env=env,text=True,capture_output=True,check=True)
    compare(result.stdout.splitlines(),wanted);assert len(wanted)==98
    controls=[]
    mutations=[('unknown-cli-admitted','admissions','admitted'),('world-as-one-container','admissions','outputs'),
               ('preview-materializes','admissions','materialized'),('fixed-binding-follows-new-layout','placements','destination'),
               ('uppercase-zip-candidate','suffixes','candidate'),('requested-resource-kind-ignored','metadata','content'),
               ('resource-incorrectly-required-on-server','metadata','serverRequired')]
    # Locate cases by identity; array offsets do not define the tested operation.
    ids={'unknown-cli-admitted':'continued-unknown-module','world-as-one-container':'continued-interpreted-world',
         'preview-materializes':'continued-preview-resource','fixed-binding-follows-new-layout':'layout:module','uppercase-zip-candidate':'vanilla-source:resource-upper','requested-resource-kind-ignored':'stored:resource','resource-incorrectly-required-on-server':'stored:resource'}
    for label,kind,key in mutations:
        changed=copy.deepcopy(expected);r=next(x for x in changed[kind] if x['id']==ids[label])
        if key=='content':r[key]='data-pack'
        elif key=='destination':r[key]='custom-mods/module.jar'
        elif key=='outputs':r[key]=1
        else:r[key]=not r[key]
        try:compare(actual,changed)
        except AssertionError:controls.append(label)
        else:raise AssertionError('Changed interpretation escaped')
    for label,change in [('schema',lambda d:d.update(schema=2)),('kind',lambda d:d['admissions'][0].update(explicit=5)),
                         ('world-observation',lambda d:d['admissions'][9].update(explicit=4,override='saves',worldRoots=1,worldNonempty=None)),
                         ('world-members',lambda d:d['admissions'][8].update(worldMembers=0))]:
        altered=copy.deepcopy(inputs);change(altered);p=formal/(label+'.json');write(p,altered)
        r=subprocess.run(command+[str(p)],cwd=ROOT,env=env,text=True,capture_output=True)
        assert r.returncode==2 and 'research' in r.stderr
        controls.append(label)
    files=[p for run in RUNS for p in run.rglob('*') if p.is_file() and p.name not in ['basis.json','conformance.json']]
    files += [p for p in (ROOT/'applications/empack/content-kinds').iterdir() if p.is_file()]
    files += [ROOT/'applications/sources'/name for name in ['empack-content-kinds-selections.json','empack-content-kinds-host-context.json','empack-content-kinds-policy-context.json']]
    write(PRIMARY/'basis.json',{str(p.relative_to(ROOT)):sha(p) for p in files})
    report=dict(schema=1,**identities,nativeCommands=22,admissionFrames=15,storedRootFrames=8,placementFrames=2,
                sourceOnlySuffixFrames=3,dualScalarComparisons=98,nativeProjections=95,sourceOnlyProjections=3,
                leanLaws=29,bendLaws=14,controls=controls,basisFiles=len(files),
                limits=['Original wrong-cwd file error is retained/excluded; guarded absolute-input continuation preserves originals.',
                        'Marker/input/layout/route premises are independently interpreted, not exported native planner states or a full ZIP/path/YAML proof.',
                        'Default-side profile only; authored environment/choice overrides remain separate.',
                        'Three vanilla suffix predicates are static source comparisons, not native game/distribution acceptance.',
                        'Synthetic metadata/world bytes are not playable; no build,Java,game,network/provider workflow,crash or concurrency qualification.',
                        'Proposed compatibility reporting is a separate logical contract, not a production validator.'])
    write(PRIMARY/'conformance.json',report);print(json.dumps(report,indent=2))


if __name__=='__main__':main()
