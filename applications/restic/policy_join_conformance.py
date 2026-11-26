"""Retained policy/deletion/prune/restore comparison; no restic or credential reads."""
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
CAPS=[ROOT/'applications/evidence'/('restic-policy-join-'+s) for s in ['20261125T235000202024Z','20261125T235101268551Z']]
CAP=CAPS[-1]
FORMAL=ROOT/'.build/restic-policy-join-formal'
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,x:p.write_text(json.dumps(x,indent=2)+'\n')

def json_values(raw):
    decoder=json.JSONDecoder();values=[];rest=raw.strip()
    while rest:
        value,end=decoder.raw_decode(rest);values.append(value);rest=rest[end:].strip()
    return values

def snapshot_ids(image):return sorted(p.split('/')[1] for p,v in image.items() if p.startswith('snapshots/') and v['kind']=='file')

def evidence(owner_local):
    basis={};rows=[];unavailable=[]
    setups=[load(c/'setup.json') for c in CAPS]
    for cap,setup in zip(CAPS,setups,strict=True):
        assert sha(cap/'probe.py')==setup['producerSha256']
        terminal=load(cap/'termination.json');assert terminal=={'recordedGroupsAbsent':True,'snapshotDirectoryMode':0o700}
        batch=load(cap/'commands.json');assert len(batch)==(13 if cap==CAPS[0] else 10)
        for r in batch:
            assert r['groupAbsent'] and not r['timedOut']
            assert r['argv'][:8]==[setup['binary'],'-r',setup['work']+'/repository','--password-file',setup['work']+'/password','--cache-dir',setup['work']+'/cache','--json']
            expected=3 if r['id']=='policy-remove-refused' else 1 if r['id'] in ['blob-after-a0','blob-after-b0'] else 0
            assert r['exitCode']==expected
            for stream,h in r['streams'].items():assert sha(cap/(r['id']+'.'+stream))==h
            rows.append((cap,r))
        for p in cap.iterdir():
            if p.is_file() and p.name not in ['model-input.json','observed.json','basis.json','conformance.json','controls.json']:
                basis[str(p.relative_to(ROOT))]=sha(p)
    prior=CAPS[0];continuation=setups[1]['continuation']
    assert continuation['capture']==str(prior.relative_to(ROOT))
    for key,name in [('setupSha256','setup.json'),('editsSha256','authored-edits.json'),('commandsSha256','commands.json')]:assert continuation[key]==sha(prior/name)
    assert load(CAP/'receipt.json')['complete'] and load(prior/'failure.json')['commands']==13
    edits=load(prior/'authored-edits.json');assert len(edits)==2
    assert [e['mode'] for e in edits]==[0o500,0o700] and all(e['authored'] for e in edits)
    for e in edits:
        assert e['path']==setups[0]['work']+'/repository/snapshots'
        changed=[(scope,p) for scope in e['before'] for p in e['before'][scope].keys()|e['after'][scope].keys() if e['before'][scope].get(p)!=e['after'][scope].get(p)]
        assert changed==[('repository','snapshots')]
    by_id={r['id']:(c,r) for c,r in rows};assert len(by_id)==len(rows)==23
    assert by_id['policy-preview'][1]['after']==edits[0]['before']
    assert by_id['policy-remove-refused'][1]['before']==edits[0]['after']
    assert by_id['policy-remove-refused'][1]['after']==edits[1]['before']
    assert by_id['policy-apply'][1]['before']==edits[1]['after']
    for name in ['policy-preview','policy-remove-refused']:
        c,r=by_id[name];assert r['before']==r['after']
    refused=by_id['policy-remove-refused'];assert refused[1]['exitCode']==3
    errors=json_values((refused[0]/'policy-remove-refused.stderr').read_text()[(refused[0]/'policy-remove-refused.stderr').read_text().index('{"message_type"'):])
    assert errors[-1]['message_type']=='exit_error' and errors[-1]['code']==3
    inputs=load(prior/'inputs.json');assert inputs==load(CAP/'inputs.json')
    snapshots=load(prior/'snapshots-before.stdout');assert {s['id'] for s in snapshots}==set(inputs['snapshots'].values())
    values=inputs['versions'];metadata=[]
    for label,sid in inputs['snapshots'].items():
        v=values[label];s=next(s for s in snapshots if s['id']==sid)
        assert s['hostname']=='rules-policy-'+v['group'] and s['paths']==[v['source']]
        assert s['time'].startswith('2020-01-0'+str(v['rank']+1)+'T00:00:00')
        assert s.get('parent')==(inputs['snapshots'][label[0]+'0'] if label.endswith('1') else None)
        backup=by_id['backup-'+label][1];assert backup['argv'][8:]==['backup','--host',s['hostname'],'--time','2020-01-0'+str(v['rank']+1)+' 00:00:00',v['source']]
        summary=next(v for v in json_values((prior/('backup-'+label+'.stdout')).read_text()) if v.get('message_type')=='summary')
        assert summary['snapshot_id']==sid and summary['total_files_processed']==2
        source=backup['before']['source-'+v['group']];assert source['state.txt']['sha256']==v['stateSha256'] and source['shared.txt']['sha256']==v['sharedSha256']==inputs['shared']
        metadata.append(dict(id=sid,host=s['hostname'],paths=s['paths'],rank=v['rank'],parent=s.get('parent'),reachable=[inputs['shared'],v['stateSha256']]))
    available=sorted({b for s in metadata for b in s['reachable']});assert len(available)==5
    blob_names=dict(shared=inputs['shared'],**{label:v['stateSha256'] for label,v in values.items()})
    actual_available=[]
    for label,identity in blob_names.items():
        c,r=by_id['blob-before-'+label];assert r['argv'][8:]==['cat','blob',identity] and r['exitCode']==0 and sha(c/(r['id']+'.stdout'))==identity
        c,r=by_id['blob-after-'+label];assert r['argv'][8:]==['cat','blob',identity]
        if r['exitCode']==0:assert sha(c/(r['id']+'.stdout'))==identity;actual_available.append(identity)
        else:assert r['exitCode']==1 and label in ['a0','b0']
    expected_keep=sorted(inputs['snapshots'][g+'1'] for g in ['a','b']);expected_remove=sorted(inputs['snapshots'][g+'0'] for g in ['a','b'])
    cases=[];observed=[]
    for name in ['policy-preview','policy-remove-refused','policy-apply']:
        c,r=by_id[name];stream=json_values((c/(name+'.stdout')).read_text());groups=stream[0]
        assert isinstance(groups,list) and len(groups)==2
        assert sorted(s['id'] for g in groups for s in g.get('keep') or [])==expected_keep
        planned=sorted(s['id'] for g in groups for s in g.get('remove') or []);assert planned==expected_remove
        for g in groups:
            for s in (g.get('keep') or [])+(g.get('remove') or []):assert s['hostname']==g['host'] and s['paths']==g['paths']
        phase=len(stream)==2
        if phase:assert stream[1]['message_type']=='summary' and 'blobs' in stream[1]
        dry=name=='policy-preview';failed=name=='policy-remove-refused'
        assert r['argv'][8:]==['forget','--keep-last','1','--prune','--max-unused','0']+(['--dry-run'] if dry else [])
        before=snapshot_ids(r['before']['repository']);after=snapshot_ids(r['after']['repository']);assert before==sorted(inputs['snapshots'].values())
        removed=sorted(set(before)-set(after))
        cases.append(dict(dry=dry,refused=expected_remove if failed else []))
        observed.append(dict(planned=planned,removed=removed,snapshots=after,available=available if dry or failed else sorted(actual_available),prunePhase=phase,code=r['exitCode']))
    assert snapshot_ids(by_id['snapshots-after'][1]['after']['repository'])==expected_keep
    assert sorted(s['id'] for s in load(CAP/'snapshots-after.stdout'))==expected_keep
    assert load(CAP/'full-check.stdout')['num_errors']==0 and by_id['full-check'][1]['exitCode']==0
    for group in ['a','b']:
        c,r=by_id['restore-'+group];assert r['exitCode']==0
        assert r['argv'][8:]==['restore',inputs['snapshots'][group+'1'],'--target',setups[0]['work']+'/targets/'+group,'--verify']
        source=r['after']['source-'+group];target_prefix=group+'/'+values[group+'1']['source'].lstrip('/')+'/'
        target={p.removeprefix(target_prefix):v for p,v in r['after']['targets'].items() if p.startswith(target_prefix)}
        assert target==source
    if owner_local:
        binary=Path(setups[0]['binary']);assert sha(binary)==setups[0]['binarySha256']
        spec=importlib.util.spec_from_file_location('frozen_policy_join',CAP/'probe.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        work=Path(setups[0]['work']);assert {n:m.image(work/n) for n in ['repository','source-a','source-b','targets']}==rows[-1][1]['after']
    else:unavailable+=['installed restic identity','latest private repository/source/target images']
    selections=ROOT/'applications/sources/restic-policy-join-selections.json';basis[str(selections.relative_to(ROOT))]=sha(selections)
    for source in load(selections)['sources']:
        p=ROOT/source['cache']
        if owner_local and p.exists():assert sha(p)==source['sha256']
        else:unavailable.append(str(p))
    proof=load(CAP/'proof-gate.json');assert proof['exitCode']==0 and 'Checked 4 Lean modules and 3 Bend files.' in proof['stdout']
    for p,h in proof['sourceSha256'].items():
        if p!='scripts/check-rules.py':assert sha(ROOT/p)==h
    return dict(schema=1,snapshots=metadata,available=available,cases=cases),observed,basis,unavailable

def main():
    assert sys.argv[1:] in [[],['--public-only']]
    inputs,observed,basis,unavailable=evidence(not sys.argv[1:]);FORMAL.mkdir(parents=True,exist_ok=True);write(CAP/'model-input.json',inputs);write(CAP/'observed.json',observed)
    lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend');env={**os.environ,'LEAN_PATH':str(FORMAL),'BEND_NO_TELEMETRY':'1'}
    for name in ['Selection','Retention','PolicyJoin']:
        p='applications/restic/'+name+'.lean';dest=FORMAL/Path(p).with_suffix('.olean');dest.parent.mkdir(parents=True,exist_ok=True);subprocess.run([lean,'-DwarningAsError=true','-o',str(dest),p],env=env,capture_output=True,check=True)
    cmd=[lean,'--run','applications/restic/PolicyJoinCase.lean',str(CAP/'model-input.json')];r=subprocess.run(cmd,env=env,capture_output=True,text=True,check=True);assert json.loads(r.stdout)==observed
    def strings(xs):return '['+','.join(json.dumps(x) for x in xs)+']'
    candidates=[];snaps=[]
    for s in inputs['snapshots']:
        newer=any(t['host']==s['host'] and t['paths']==s['paths'] and t['rank']>s['rank'] for t in inputs['snapshots'])
        candidates.append('P.Candidate{'+json.dumps(s['id'])+','+('True{}' if newer else 'False{}')+'}')
        snaps.append('R.Snap{'+json.dumps(s['id'])+','+('Some{'+json.dumps(s['parent'])+'}' if s['parent'] else 'None{}')+','+strings(s['reachable'])+'}')
    expressions=['P.render(P.run(['+','.join(candidates)+'],R.Repo{['+','.join(snaps)+'],'+strings(inputs['available'])+'},'+('True{}' if c['dry'] else 'False{}')+','+strings(c['refused'])+'))' for c in inputs['cases']]
    driver=HERE/'_policy_replay.bend';driver.write_text('import Base\nimport PolicyJoin.bend as P\nimport Retention.bend as R\ndef main() -> IO(Unit):\n  IO.print('+(' ++ "\\n" ++ '.join(expressions))+')\n')
    try:b=subprocess.run([bend,str(driver)],env=env,capture_output=True,text=True,check=True)
    finally:driver.unlink()
    bvalues=[]
    for line in b.stdout.strip().splitlines():
        a,c,d,e,f,g=line.split('|');split=lambda v:sorted(x for x in v.split(':') if x)
        bvalues.append(dict(planned=split(a),removed=split(c),snapshots=split(d),available=split(e),prunePhase=f=='1',code=int(g)))
    assert bvalues==observed
    controls=[]
    for key in observed[0]:
        changed=copy.deepcopy(observed);changed[0][key]=not changed[0][key] if key=='prunePhase' else changed[0][key]+1 if key=='code' else changed[0][key]+['unobserved']
        assert changed!=observed;controls.append(dict(kind='changed-observation',field=key,refused=True))
    for name,mutation in [('schema',lambda x:x.update(schema=2)),('duplicate-id',lambda x:x['snapshots'][0].update(id=x['snapshots'][1]['id'])),('missing-reachability',lambda x:x['snapshots'][0].update(reachable=[])),('unknown-refusal',lambda x:x['cases'][1].update(refused=['unknown']))]:
        bad=copy.deepcopy(inputs);mutation(bad);path=FORMAL/(name+'.json');write(path,bad);q=subprocess.run(cmd[:-1]+[str(path)],env=env,capture_output=True);assert q.returncode==2;controls.append(dict(kind='DTO',field=name,refused=True))
    for p in [Path(__file__),*[HERE/(n+ext) for n in ['Selection','Retention','PolicyJoin'] for ext in ['.lean','.bend']],HERE/'PolicyJoinCase.lean']:basis[str(p.relative_to(ROOT))]=sha(p)
    write(CAP/'basis.json',basis);write(CAP/'controls.json',controls)
    result=dict(schema=1,nativeCommands=23,boundaries=3,membershipAndPhaseScalars=57,matched=True,lean=observed,bend=bvalues,controls=len(controls),basisFiles=len(basis),ownerLocalUnavailable=unavailable,
      scope='Owned two-group local fixture;four snapshot IDs,five file-data blobs. Reachability input from controlled backup sources,not complete native tree traversal. Preview/total-refusal/success observed;partial-subset refusal is model-only. No native execution or password access in replay.')
    write(CAP/'conformance.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['lean','bend','scope','ownerLocalUnavailable']}))

if __name__=='__main__':main()
