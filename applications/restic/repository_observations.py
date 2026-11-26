"""Observe retained local repository requests and effects;no restic execution."""
import hashlib,json
from pathlib import Path
from locks_probe import redact

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
CAP=ROOT/'applications/evidence/restic-repository-20261126T024414054889Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())


def observe(rows,interventions,streams):
    configs={}
    for r in rows:
        if r['argv'][6:]==['cat','config']and r['exitCode']==0:
            cfg=json.loads(streams[r['label']]['stdout']);assert cfg['version']in[1,2]and len(cfg['id'])==64
            assert r['before']==r['after']
            identity=(r['repo'],r['before']['files']['config']['sha256'])
            assert identity not in configs or configs[identity]==cfg;configs[identity]=cfg
    def version(repo,image):
        cfg=image['files'].get('config')
        return configs[(repo,cfg['sha256'])]['version']if cfg else 0
    history={};inputs=[];measured=[];details=[];edits={r['target']:r for r in interventions}
    for r in rows:
        args=r['argv'][6:];repo=r['repo'];before=r['before'];after=r['after'];files=before['files'];new=after['files'];text=streams[r['label']]
        for name in files:
            if name.startswith(('keys/','snapshots/')):
                token=Path(name).name
                assert len(token)==64 and all(c in'0123456789abcdef'for c in token)
        if repo not in history and repo in edits:
            edit=edits[repo];assert edit['before']==history[edit['source']]
            retained={p:v for p,v in edit['before']['files'].items()if not any(p==gone or p.startswith(gone+'/')for gone in edit['remove'])}
            assert edit['after']==dict(exists=True,files=retained)
            history[repo]=edit['after']
        if repo in history:assert before==history[repo],r['label']
        history[repo]=after
        if args[0]in['version','backup','dump','check']:
            details.append(dict(label=r['label'],role='setup-or-independent-readback',exitCode=r['exitCode']));continue
        assert args[0]in['init','cat','migrate']
        requested=2
        if args[0]=='init'and'--repository-version'in args:requested=int(args[args.index('--repository-version')+1])
        if args[0]=='cat':assert args==['cat','config'];kind='open'
        elif args[0]=='init':kind='init'
        else:kind='migrate-list'if len(args)==1 else'migrate-apply'
        known=kind=='migrate-apply'and'upgrade_repo_v2'in args[1:]
        unknown=kind=='migrate-apply'and any(a!='upgrade_repo_v2'for a in args[1:])
        prior=version(repo,before);later=version(repo,after)
        changed=files.get('config')!=new.get('config')
        wrong=Path(r['argv'][4]).name=='wrong-password'
        inputs.append(dict(kind=kind,requestedVersion=requested,version=prior,hasKeys=any(p.startswith('keys/')for p in files),hasSnapshots=any(p.startswith('snapshots/')for p in files),otherPassword=wrong,knownMigration=known,unknownMigration=unknown,strictUnknown=False))
        measured.append([r['exitCode'],later,changed,'unknown migration 'in text['stderr'],'cannot be applied:'in text['stderr'],'migration upgrade_repo_v2: success'in text['stdout'],kind=='migrate-list'and'  upgrade_repo_v2\t'in text['stdout']])
        if changed and kind=='migrate-apply':
            assert set(files)==set(new)
            assert all(v==new[p]for p,v in files.items()if p!='config')
            a=configs[(repo,files['config']['sha256'])];b=configs[(repo,new['config']['sha256'])]
            assert a['version']==1 and b['version']==2
            assert {k:v for k,v in a.items()if k!='version'}=={k:v for k,v in b.items()if k!='version'}
        elif kind!='init'or r['exitCode']!=0:assert before==after,r['label']
        if kind=='init'and r['exitCode']==0:
            assert not files and set(p.split('/')[0]for p in new)=={'config','keys'}
            initialization=json.loads(text['stdout']);assert initialization['message_type']=='initialized'
            assert initialization['id']==configs[(repo,new['config']['sha256'])]['id']
        nonempty=[value for value in text.values()if value.strip()];structured=bool(nonempty)
        for value in nonempty:
            try:json.loads(value)
            except json.JSONDecodeError:structured=False
        details.append(dict(label=r['label'],role='modeled-request',beforeVersion=prior,afterVersion=later,configChanged=changed,priorFileNamespacePreserved=all(p in new and v==new[p]for p,v in files.items()if p!='config'),structuredOutput=structured,versionEvidence='Independent authenticated config read keyed by exact encrypted config bytes;not knowledge disclosed by a failed request.'))
    assert len(rows)==22 and len(inputs)==18
    return dict(schema=1,profile='restic-local-repository-lifecycle',cases=inputs),measured,details


def evidence(owner_local=True):
    basis={str(p.relative_to(ROOT)):sha(p)for p in CAP.iterdir()if p.is_file()};excluded=[]
    for name,digest in read(CAP/'collection-basis.json').items():assert sha(CAP/name)==digest
    setup=read(CAP/'setup.json');receipt=read(CAP/'receipt.json');rows=read(CAP/'commands.json');edits=read(CAP/'interventions.json')
    assert sha(CAP/'probe.py')==setup['producerSha256']==sha(HERE/'repository_probe.py')
    assert sha(CAP/'helper.py')==setup['helperSha256']==sha(HERE/'locks_probe.py')
    assert setup['binarySha256']==receipt['toolSha256']==read(ROOT/'applications/sources/restic-tool.json')['binarySha256']
    assert receipt['commands']==22 and receipt['allGroupsAbsent']
    assert read(CAP/'current-process.json')['status']=='terminal'
    streams={}
    for r in rows:
        assert r['groupAbsent']and not r['timedOut']
        streams[r['label']]={}
        for name,info in r['streams'].items():
            p=CAP/info['path'];assert sha(p)==info['publicSha256'];streams[r['label']][name]=p.read_text()
            if owner_local:
                raw=Path(info['rawPrivatePath']);assert sha(raw)==info['rawSha256']and redact(raw.read_bytes())==p.read_bytes()
    if owner_local:
        work=Path(setup['work']);assert sha(Path(setup['binary']))==setup['binarySha256']
        for name in ['commands','interventions']:
            raw=work/'private'/(name+'.json');assert sha(raw)==receipt['raw'+name.title()+'Sha256']
            assert redact(raw.read_bytes())==(CAP/(name+'.json')).read_bytes()
        assert(work/'password').read_bytes()!=(work/'wrong-password').read_bytes()
        assert(work/'password').stat().st_mode&0o777==(work/'wrong-password').stat().st_mode&0o777==0o600
        assert sha(work/'source/payload.txt')==setup['payloadSha256']==receipt['sourcePayloadSha256']
        assert(work/'private/dump-after-migration.stdout').read_bytes()==(work/'source/payload.txt').read_bytes()
        for repo,image in read(CAP/'final-images.json').items():
            root=work/repo;assert root.is_dir()==image['exists']
            current={str(p.relative_to(root)):dict(bytes=p.stat().st_size,sha256=sha(p),mode=p.stat().st_mode&0o777,mtimeNs=p.stat().st_mtime_ns)for p in root.rglob('*')if p.is_file()}
            assert current==image['files']
    else:excluded=['Private raw streams and JSON correspondence','Current binary','Current private repository images and credential-profile comparison','Source/dump private byte readbacks']
    result,measured,details=observe(rows,edits,streams)
    selections=ROOT/'applications/sources/restic-repository-selections.json'
    for source in read(selections)['sources']:
        if owner_local:
            data=(ROOT/source['cache']).read_bytes()
            assert len(data)==source['bytes']and hashlib.sha256(data).hexdigest()==source['sha256']
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==source['gitBlob']
        else:excluded.append('Private selected source: '+source['path'])
    gate=read(CAP/'proof-gate.json');assert gate['exitCode']==0 and'Checked 2 Lean modules and 1 Bend files.'in gate['stdout']
    for name,digest in gate['sourceSha256'].items():assert sha(ROOT/name)==digest
    for p in [HERE/'repository_probe.py',HERE/'repository_observations.py',HERE/'repository_conformance.py',HERE/'Repository.lean',HERE/'Repository.bend',HERE/'RepositoryCase.lean',HERE/'locks_probe.py',selections,ROOT/'applications/sources/restic-tool.json']:basis[str(p.relative_to(ROOT))]=sha(p)
    return result,measured,details,basis,excluded


if __name__=='__main__':
    value,measured,details,basis,excluded=evidence()
    out=ROOT/'.build/restic-repository-preread/observations.json';out.write_text(json.dumps(dict(input=value,measured=measured,details=details,basis=basis,privateChecksExcluded=excluded),indent=2)+'\n')
    print(json.dumps(dict(commands=22,modeledRequests=len(value['cases']),basisFiles=len(basis),configTransitions=[d for d in details if d.get('configChanged')],privateChecksExcluded=excluded)))
