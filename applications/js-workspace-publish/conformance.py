"""Retained-data/model replay. No registry, package-manager, or generated JS execution."""
import base64
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
CAPS=[ROOT/'applications/evidence'/('js-workspace-publish-'+s) for s in ['20261125T232855329056Z','20261125T232922743988Z','20261125T232953513250Z']]
CAP=CAPS[-1]
FORMAL=ROOT/'.build/js-workspace-publish-formal'
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda b:hashlib.sha256(b).hexdigest()
write=lambda p,x:p.write_text(json.dumps(x,indent=2)+'\n')

def decoded(item):
    raw=bytes.fromhex(item['bytesHex']);assert len(raw)==item['bytes'] and digest(raw)==item['sha256']
    return json.loads(raw)

def evidence(owner_local):
    selected=[];all_rows=[];unavailable=[];basis={};archives={}
    for cap in CAPS:
        setup=load(cap/'setup.json');rows=load(cap/'commands.json');retired=load(cap/'server-retired.json')
        assert retired==dict(threadJoined=True,listeningSocketClosed=True)
        assert setup['producerSha256']==sha(cap/'probe.py')
        if cap!=CAP:assert (cap/'failure.json').exists()
        else:assert load(cap/'receipt.json')['complete'] and load(cap/'receipt.json')['commands']==len(rows)==13
        for r in rows:
            assert r['groupAbsent'] and not r['timedOut']
            assert all(e['path'].startswith('/') for e in r['serverEvents'])
            for n,h in r['streams'].items():assert sha(cap/(r['id']+'.'+n))==h
            for image in [r['before'],r['after']]:
                for item in image.values():
                    if 'bytesHex' in item:
                        raw=bytes.fromhex(item['bytesHex']);assert len(raw)==item['bytes'] and digest(raw)==item['sha256']
            # The one excluded attempt stopped during pnpm's config dependency
            # resolution, before any workspace script or publication PUT.
            excluded=cap==CAPS[1] and r['id']=='pnpm-success'
            if excluded:
                assert r['exitCode']==1 and not any(e['method']=='PUT' for e in r['serverEvents'])
                assert b'ERR_PNPM_BAD_CONFIG_DEP' in (cap/'pnpm-success.stderr').read_bytes()
            else:selected.append((cap,r))
            all_rows.append((cap,r))
            if r['kind']=='publish' and not excluded:
                req=r['request'];names=req['sourceNames'];version=req['version']
                assert req['workspaceDirs']==['packages/0-private','packages/a-consumer','packages/z-producer']
                assert decoded(r['before']['package.json'])['workspaces']==req['workspaceDirs']
                manager=r['manager'];prefix=[setup['tools']['node']['path'],setup['tools']['yarn']['path']] if manager=='yarn' else [setup['tools'][manager]['path']]
                if manager=='npm':arguments=['publish','--workspaces','--json','--fetch-retries=0','--no-audit','--no-fund']
                elif manager=='pnpm':arguments=['--recursive','publish','--no-git-checks','--json','--registry',setup['registry'],'--npmrc-auth-file',str(Path(r['root']).parent/'config/user.npmrc'),'--report-summary']
                else:arguments=['workspaces','foreach','-A','-t','--no-private','npm','publish','--json']
                assert r['argv']==prefix+arguments
                for role,relative in zip(['private','consumer','producer'],req['workspaceDirs'],strict=True):
                    path=relative+'/package.json';assert r['before'][path]==r['after'][path]
                    m=decoded(r['before'][path]);assert m['name']==names[role] and m['version']==version and m.get('private',False)==(role=='private')
                authored=decoded(r['before'][req['workspaceDirs'][1]+'/package.json'])
                assert authored['dependencies']=={names['producer']:req['dependency']}
                for e in r['serverEvents']:
                    if e['method']!='PUT':continue
                    assert e['accepted'] and e['status']==201 and e['name'] in [names['consumer'],names['producer']]
                    idx=load(cap/'server-events.json').index(e);raw=cap/('received-'+str(idx)+'.tgz');document=load(cap/('received-'+str(idx)+'.json'))
                    assert sha(cap/('received-'+str(idx)+'.json'))==e['requestSha256']
                    a=next(iter(document['_attachments'].values()));b=base64.b64decode(a['data'],validate=True)
                    assert b==raw.read_bytes() and digest(b)==e['archiveSha256'] and len(b)==e['archiveBytes']==a['length']
                    manifest=document['versions'][version];assert manifest['dist']['shasum']==hashlib.sha1(b).hexdigest()
                    assert manifest['dist']['integrity']=='sha512-'+base64.b64encode(hashlib.sha512(b).digest()).decode()
                    with tarfile.open(fileobj=io.BytesIO(b),mode='r:gz') as tar:
                        members=tar.getmembers();assert all(m.isdir() or m.isfile() for m in members)
                        assert len({m.name for m in members})==len(members)
                        files={m.name:tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
                    assert set(files)=={'package/package.json','package/index.js'}
                    assert {p:digest(v) for p,v in files.items()}==e['files']
                    assert json.loads(files['package/package.json'])==e['packagedManifest']
                    role='consumer' if e['name']==names['consumer'] else 'producer'
                    source=next(p for p in req['workspaceDirs'] if decoded(r['before'][p+'/package.json'])['name']==e['name'])
                    assert digest(files['package/index.js'])==r['before'][source+'/index.js']['sha256']
                    if role=='consumer':assert e['packagedManifest']['dependencies']=={names['producer']:version}
                    archives[(r['manager'],version,role)]=(e,manifest)
        for n,pin in setup['tools'].items():
            if owner_local and Path(pin['path']).exists():assert sha(Path(pin['path']))==pin['sha256']
            else:unavailable.append(pin['path'])
        if owner_local:
            spec=importlib.util.spec_from_file_location('workspace_frozen',cap/'probe.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            final={r['root']:r['after'] for r in rows}
            for root,image in final.items():
                if Path(root).exists():assert module.image(Path(root))==image
                else:unavailable.append(root)
        else:unavailable.append(setup['work'])
        for p in cap.iterdir():
            if p.is_file() and p.suffix in ['.json','.stdout','.stderr','.py','.tgz'] and p.name not in ['model-input.json','observed.json','conformance.json','basis.json','controls.json']:
                basis[str(p.relative_to(ROOT))]=sha(p)
    assert len(all_rows)==19 and len(selected)==18
    publications=[(c,r) for c,r in selected if r['kind']=='publish'];assert len(publications)==9
    assert len({r['id'] for c,r in publications})==9
    for manager in ['npm','pnpm','yarn']:
        cap,r=next((c,r) for c,r in selected if r['manager']==manager and r['kind']=='consume')
        lock_path=cap/(manager+'-consumer-lock.json')
        if not lock_path.exists():
            assert owner_local,'Freeze the independently verified consumer lock before public replay.'
            original=Path(r['root'])/'package-lock.json';assert sha(original)==r['after']['package-lock.json']['sha256'];lock_path.write_bytes(original.read_bytes())
        assert sha(lock_path)==r['after']['package-lock.json']['sha256'];lock=load(lock_path)
        for role in ['consumer','producer']:
            e,manifest=archives[(manager,'1.0.0',role)];p='node_modules/'+e['name'];item=lock['packages'][p]
            assert item['version']=='1.0.0' and item['integrity']==manifest['dist']['integrity']
            assert item['resolved']==load(cap/'setup.json')['registry']+'tarballs/'+e['archiveSha256']+'.tgz'
            assert r['after'][p+'/index.js']['sha256']==e['files']['package/index.js']
        execute=next(x for c,x in selected if x['manager']==manager and x['kind']=='execute');result=load(cap/(execute['id']+'.stdout'))
        assert result=={'value':'producer:1.0.0','resolved':r['root']+'/node_modules/rules-workspace-fixture-'+manager+'-consumer/index.js'}
        assert execute['before']==execute['after']==r['after'] and execute['exitCode']==r['exitCode']==0
        basis[str(lock_path.relative_to(ROOT))]=sha(lock_path)
    for source in load(ROOT/'applications/sources/js-workspace-publish-selections.json'):
        p=ROOT/source['cache']
        if owner_local and p.exists():assert sha(p)==source['sha256']
        else:unavailable.append(str(p))
    proof=load(CAP/'proof-gate.json');assert proof['exitCode']==0 and 'Checked 3 Lean modules and 2 Bend files.' in proof['stdout']
    for p,h in proof['sourceSha256'].items():
        if p!='scripts/check-rules.py':assert sha(ROOT/p)==h
    return publications,basis,sorted(set(unavailable))

def packets(rows):
    inputs=[];observed=[]
    for cap,r in rows:
        manager=r['manager'];req=r['request'];case=req['case'];names=req['sourceNames']
        inputs.append(dict(profile=manager,failure={'success':'none','producer-late-failure':'producerLate','private-pre-hook-failure':'privateEarly'}[case]))
        raw=r['after'].get('hooks.jsonl');hooks=[] if raw is None else [json.loads(l) for l in bytes.fromhex(raw['bytesHex']).decode().splitlines()]
        phases={'npm':['prepublishOnly','prepack','postpack','publish','postpublish'],
          'pnpm':['prepublishOnly','prepublish','prepack','postpack','publish','postpublish'],
          'yarn':['prepublish','prepack','postpack']}[manager]
        if manager=='npm' and case=='private-pre-hook-failure':expected_hooks=[('private','prepublishOnly')]
        elif manager=='npm':expected_hooks=[('private',h) for h in phases[:3]]+[(role,h) for role in ['consumer','producer'] for h in phases]
        else:expected_hooks=[(role,h) for role in (['producer'] if case=='producer-late-failure' else ['producer','consumer']) for h in phases]
        assert [(h['role'],h['event']) for h in hooks]==expected_hooks
        for h in hooks:
            role_index=['private','consumer','producer'].index(h['role']);assert h['cwd']==r['root']+'/'+req['workspaceDirs'][role_index]
        puts=[e for e in r['serverEvents'] if e['method']=='PUT'];roles=[1 if e['name']==names['consumer'] else 2 for e in puts]
        producer=2 in roles;consumer=1 in roles;private=any(h['role']=='private' for h in hooks)
        # This column observes non-start after the failing prerequisite. The
        # interpretation as scheduler blocking is supported by selected source.
        blocked=case=='producer-late-failure' and not any(h['role']=='consumer' for h in hooks)
        order=int(''.join(str(i) for i in roles)) if roles else 0
        rewritten=consumer and req['dependency']=='workspace:*' and next(e for e in puts if e['name']==names['consumer'])['packagedManifest']['dependencies'][names['producer']]==req['version']
        summary=r['after'].get('pnpm-publish-summary.json');summaries=[] if summary is None else decoded(summary)['publishedPackages']
        if manager=='pnpm':assert [s['name'] for s in summaries]==[e['name'] for e in puts]
        observed.append([int(private),int(producer),int(consumer),int(blocked),order,int(rewritten),len(summaries),r['exitCode']])
    return dict(schema=1,cases=inputs),observed

def main():
    assert sys.argv[1:] in [[],['--public-only']]
    rows,basis,unavailable=evidence(not sys.argv[1:]);inputs,observed=packets(rows);FORMAL.mkdir(parents=True,exist_ok=True)
    write(CAP/'model-input.json',inputs);write(CAP/'observed.json',observed)
    env={**os.environ,'LEAN_PATH':str(FORMAL),'BEND_NO_TELEMETRY':'1'};lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend')
    for p in ['applications/js-peers/Publication.lean','applications/js-workspace-publish/WorkspacePublication.lean']:
        dest=FORMAL/Path(p).with_suffix('.olean');dest.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run([lean,'-DwarningAsError=true','-o',str(dest),p],env=env,check=True,capture_output=True)
    command=[lean,'--run','applications/js-workspace-publish/WorkspacePublicationCase.lean',str(CAP/'model-input.json')]
    lr=subprocess.run(command,env=env,check=True,capture_output=True,text=True);lvalues=json.loads(lr.stdout);assert lvalues==observed
    calls=[]
    for r in inputs['cases']:
        p={'npm':'Npm','pnpm':'Pnpm','yarn':'Yarn'}[r['profile']];f={'none':0,'producerLate':1,'privateEarly':2}[r['failure']]
        calls.append('W.render(W.run(P.'+p+'{},'+str(f)+'n))')
    driver=HERE/'_replay.bend';driver.write_text('import Base\nimport ../js-peers/Publication.bend as P\nimport WorkspacePublication.bend as W\ndef main() -> IO(Unit):\n  IO.print('+(' ++ "\\n" ++ '.join(calls))+')\n')
    try:
        br=subprocess.run([bend,str(driver)],env=env,capture_output=True,text=True)
        if br.returncode:raise RuntimeError(br.stdout+br.stderr)
    finally:driver.unlink()
    bvalues=[[int(n) for n in line.split('/')] for line in br.stdout.strip().splitlines()];assert bvalues==observed
    controls=[]
    for field in range(8):
        altered=copy.deepcopy(observed);altered[0][field]+=1;assert altered!=lvalues and altered!=bvalues;controls.append(dict(kind='changed-observation',field=field,refused=True))
    for label,mutate in [('schema',lambda x:x.update(schema=2)),('profile',lambda x:x['cases'][0].update(profile='unknown')),('failure',lambda x:x['cases'][0].update(failure='unknown'))]:
        bad=copy.deepcopy(inputs);mutate(bad);path=FORMAL/(label+'.json');write(path,bad)
        result=subprocess.run(command[:-1]+[str(path)],env=env,capture_output=True,text=True);assert result.returncode==2;controls.append(dict(kind='DTO',field=label,refused=True))
    for p in [HERE/'conformance.py',ROOT/'applications/sources/js-workspace-publish-selections.json',HERE/'WorkspacePublication.lean',HERE/'WorkspacePublicationCase.lean',HERE/'WorkspacePublication.bend',ROOT/'applications/js-peers/Publication.lean',ROOT/'applications/js-peers/Publication.bend']:basis[str(p.relative_to(ROOT))]=sha(p)
    write(CAP/'basis.json',basis);write(CAP/'controls.json',controls)
    result=dict(schema=1,cases=9,scalars=72,lean=lvalues,bend=bvalues,matched=True,controls=len(controls),basisFiles=len(basis),ownerLocalUnavailable=unavailable,
      scope='Fixed generated private/consumer->producer graph and three explicit CLI profiles. Nine publication outcomes; three npm installs/Node consumers; one excluded pnpm config-resolution failure. Retained-data replay, no native collection. Order/acceptance/ranges are observed; scheduler blocking cause is source-qualified. No actual registry durability,arbitrary resolver,concurrency,or general platform qualification.')
    write(CAP/'conformance.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['lean','bend','scope','ownerLocalUnavailable']}))

if __name__=='__main__':main()
