"""Inspect frozen Cargo lock/source records; no Cargo, Git, build, or GUI run."""
import hashlib
import json
from pathlib import Path
import tomllib

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
CAP=ROOT/'applications/evidence/cargo-lock-sources-20261126T012306815691Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
IDS=['path-missing-frozen','path-generate-offline','path-locked-offline','path-format-only-frozen',
     'path-changed-locked','path-changed-offline','git-cold-offline','git-cold-locked-local-fetch',
     'git-warm-offline','git-locked-after-source-advance','git-update-offline','git-update-local-fetch',
     'git-after-update-frozen','patch-source-locked','patch-source-offline','patch-source-frozen']


def captured_bytes(info):
    data=info['text'].encode()
    if hashlib.sha256(data).hexdigest()!=info['sha256']:
        # read_text in the frozen collector normalizes CRLF. Reconstruct only
        # its explicit formatting control,then check the raw digest/length.
        first,rest=info['text'].split('\n',1)
        assert first=='# owned formatting control'
        data=(first+'\n'+rest.replace('\n','\r\n')).encode()
    assert hashlib.sha256(data).hexdigest()==info['sha256'] and len(data)==info['bytes']
    return data


def cache_state(state,setup):
    commits=[setup['firstGit'],setup['secondGit']]
    hashes=[hashlib.sha256((c+'\n').encode()).hexdigest() for c in commits]
    heads=[v for p,v in state['cache'].items() if p.startswith('git/db/') and p.endswith('/refs/remotes/origin/main')]
    assert len(heads)<=1
    head=hashes.index(heads[0]['sha256'])+1 if heads else 0
    present=[]
    for commit,digest in zip(commits,hashes):
        refs=[p for p,v in state['cache'].items() if p.startswith('git/checkouts/') and p.endswith('/.git/refs/heads/master') and v['sha256']==digest]
        assert len(refs)<=1
        if refs:
            prefix=refs[0].removesuffix('/.git/refs/heads/master')
            assert Path(prefix).name==commit[:7]
            version=commits.index(commit)+1
            assert state['cache'][prefix+'/src/lib.rs']['sha256']==hashlib.sha256(f'pub const VALUE:u8={version};\n'.encode()).hexdigest()
            assert state['cache'][prefix+'/Cargo.toml']['sha256']==state['files']['git-lib/Cargo.toml']['sha256']
        present.append(bool(refs))
    assert (head,present) in [(0,[False,False]),(1,[True,False]),(2,[True,True])]
    return head,present[0],present[1]


def lock_selection(state,project,setup):
    item=state['files'].get(project+'/Cargo.lock')
    if not item:return 0
    lock=tomllib.loads(item['text']);assert lock['version']==4 and len(lock['package'])==2
    root=next(p for p in lock['package'] if p['name']!='rules-shared')
    assert root['name']==('rules-path-app' if project=='path-app' else 'rules-git-app')
    assert root['version']=='1.0.0'
    p=next(p for p in lock['package'] if p['name']=='rules-shared')
    assert p['version'] in ['1.0.0','1.1.0']
    if 'source' in p:
        assert project=='git-app' and p['version']=='1.0.0'
        prefix='git+'+setup['localGitUrl']+'?branch=main#';assert p['source'].startswith(prefix)
        return 3+[setup['firstGit'],setup['secondGit']].index(p['source'][len(prefix):])
    if project=='path-app':return 1 if p['version']=='1.0.0' else 2
    assert p['version']=='1.0.0';return 5


def observe(rows,setup,streams):
    assert [r['id'] for r in rows]==IDS
    packets,observed,details=[],[],[]
    intentional={3:{'path-app/Cargo.lock'},4:{'path-lib/Cargo.toml'},9:{'git-lib/src/lib.rs'},13:{'git-app/Cargo.toml'}}
    for i,r in enumerate(rows):
        before,after=r['before'],r['after'];project=Path(r['cwd']).name
        assert r['cwd']==setup['work']+'/'+project and project in ['path-app','git-app']
        assert r['groupAbsent'] is True and r['exitCode'] in [0,101]
        assert r['argv'][0]==setup['cargo']['path']
        args=r['argv'][1:];command=args[0]
        if command=='metadata':
            assert args[1:3]==['--format-version','1'];flags=args[3:];operation='metadata'
        elif command=='generate-lockfile':flags=args[1:];operation='generate'
        else:
            assert command=='update' and args[1:3]==['-p','rules-shared'];flags=args[3:];operation='update'
        assert set(flags)<={'--offline','--locked','--frozen'} and len(flags)==len(set(flags))
        manifest=tomllib.loads(before['files'][project+'/Cargo.toml']['text'])
        assert set(manifest['dependencies'])=={'rules-shared'}
        dep=manifest['dependencies']['rules-shared']
        source='path' if 'path' in dep else 'git'
        if source=='path':assert dep=={'path':'../path-lib','version':'>=1.0,<2'}
        else:
            assert dep=={'git':setup['localGitUrl'],'branch':'main'}
            if 'patch' in manifest:
                assert manifest['patch']=={setup['localGitUrl']:{'rules-shared':{'path':'../patch-lib'}}}
                source='patch'
        assert setup['localGitUrl']==Path(setup['work']+'/git-lib').as_uri()
        path_version=tomllib.loads(before['files']['path-lib/Cargo.toml']['text'])['package']['version']
        assert path_version in ['1.0.0','1.1.0']
        remote_text=before['files']['git-lib/src/lib.rs']['text'];assert remote_text in ['pub const VALUE:u8=1;\n','pub const VALUE:u8=2;\n']
        if i:
            prev=rows[i-1]['after'];assert prev['cache']==before['cache'] and prev['target']==before['target']
            differences={p for p in set(prev['files'])|set(before['files']) if prev['files'].get(p)!=before['files'].get(p)}
            assert differences==intentional.get(i,set()),(r['id'],differences)
        lock=project+'/Cargo.lock'
        assert {p:v for p,v in before['files'].items() if p!=lock}=={p:v for p,v in after['files'].items() if p!=lock}
        old=lock_selection(before,project,setup);new=lock_selection(after,project,setup)
        head,hasA,hasB=cache_state(before,setup);newhead,newA,newB=cache_state(after,setup)
        packet=dict(source=source,operation=operation,locked=bool(set(flags)&{'--locked','--frozen'}),
                    offline=bool(set(flags)&{'--offline','--frozen'}),pathV2=source=='path' and path_version=='1.1.0',
                    remoteB=project=='git-app' and remote_text=='pub const VALUE:u8=2;\n',beforeLock=old,
                    cacheHead=head,hasA=hasA,hasB=hasB)
        stdout=streams[r['stdout']['path']];stderr=streams[r['stderr']['path']]
        metadata=0;key=0
        if command=='metadata' and r['exitCode']==0:
            data=json.loads(stdout);assert len(data['packages'])==2
            pkg=next(p for p in data['packages'] if p['name']=='rules-shared');assert pkg['version'] in ['1.0.0','1.1.0']
            if pkg['source'] is None:
                if project=='path-app':metadata=1 if pkg['version']=='1.0.0' else 2;path='path-lib'
                else:metadata=5;path='patch-lib';assert pkg['version']=='1.0.0'
                assert pkg['manifest_path']==setup['work']+'/'+path+'/Cargo.toml'
                assert pkg['id']=='path+'+Path(setup['work']+'/'+path).as_uri()+'#rules-shared@'+pkg['version']
                key=metadata if metadata<3 else 4
            else:
                assert pkg['version']=='1.0.0'
                prefix='git+'+setup['localGitUrl']+'?branch=main#';assert pkg['source'].startswith(prefix)
                metadata=3+[setup['firstGit'],setup['secondGit']].index(pkg['source'][len(prefix):]);key=3
                assert pkg['id']==prefix+'rules-shared@1.0.0'
                relative=Path(pkg['manifest_path']).relative_to(Path(setup['work'])/'cargo-home')
                assert str(relative) in after['cache']
            root=next(p for p in data['packages'] if p['name']==manifest['package']['name'])
            assert data['resolve']['root']==root['id']
            node=next(n for n in data['resolve']['nodes'] if n['id']==root['id'])
            assert node['dependencies']==[pkg['id']] and len(node['deps'])==1 and node['deps'][0]['pkg']==pkg['id']
        else:assert not stdout.strip()
        failure=None
        if r['exitCode']:
            if 'offline mode' in stderr:failure='source-unavailable'
            else:assert 'needs to be updated' in stderr and 'lock file' in stderr;failure='lock-change-refused'
            assert before['files'].get(lock)==after['files'].get(lock)
        if packet['locked']:assert before['files'].get(lock)==after['files'].get(lock)
        packets.append(packet);observed.append([r['exitCode'],new,newhead,int(newA)+2*int(newB),metadata,key,int(old!=new)])
        details.append(dict(id=r['id'],failure=failure,exactLockRecordUnchanged=before['files'].get(lock)==after['files'].get(lock),
                            cacheAdded=sorted(set(after['cache'])-set(before['cache'])),
                            cacheChanged=sorted(p for p in set(after['cache'])&set(before['cache']) if after['cache'][p]!=before['cache'][p])))
    assert rows[3]['before']['files']['path-app/Cargo.lock']['text'].startswith('# owned formatting control\n')
    assert b'\r\n' in captured_bytes(rows[3]['before']['files']['path-app/Cargo.lock'])
    return dict(schema=1,profile='cargo-1.92-owned-lock-sources',cases=packets),observed,details


def evidence(owner_local=True):
    setup=load(CAP/'setup.json');receipt=load(CAP/'receipt.json');rows=receipt['rows']
    assert receipt['schema']==setup['schema']==1
    assert sha(CAP/'probe.py')==setup['producerSha256']==sha(HERE/'lock_sources_probe.py')
    for path,digest in load(CAP/'collection-basis.json').items():assert sha(CAP/path)==digest
    streams={}
    for r in rows:
        for name in ['stdout','stderr']:
            p=CAP/r[name]['path'];assert p.parent==CAP and sha(p)==r[name]['sha256'];streams[p.name]=p.read_text()
        for state in [r['before'],r['after']]:
            for info in state['files'].values():
                captured_bytes(info)
    closure=load(CAP/'closure.json');host=load(CAP/'host-closure.json')
    assert closure['allGroupsAbsent'] and closure['commands']==16 and host['remainingExactWorkArguments']==[]
    assert load(CAP/'current-process.json')['status']=='terminal'
    assert load(CAP/'initial.json')==rows[0]['before'] and load(CAP/'final.json')==rows[-1]['after']
    scaff=load(CAP/'git-scaffold.json');assert len(scaff)==7 and all(r['exitCode']==0 for r in scaff)
    assert scaff[3]['stdout'].strip()==setup['firstGit'] and scaff[-1]['stdout'].strip()==setup['secondGit']
    inputs,measured,details=observe(rows,setup,streams)
    excluded=[]
    if owner_local:
        for name in ['cargo','rustc','git']:assert sha(Path(setup[name]['path']))==setup[name]['sha256']
        work=Path(setup['work'])
        for path,info in rows[-1]['after']['files'].items():
            p=work/path;s=p.stat();assert sha(p)==info['sha256'] and s.st_size==info['bytes'] and s.st_mode&0o777==info['mode'] and s.st_mtime_ns==info['mtimeNs']
        for path,info in rows[-1]['after']['cache'].items():assert sha(work/'cargo-home'/path)==info['sha256']
        assert (work/'git-lib/.git/refs/heads/main').read_text().strip()==setup['secondGit']
    else:excluded+=['current Cargo/Rust/Git executables','private final project files','private final Cargo cache','private current Git ref']
    sources=ROOT/'applications/sources/cargo-lock-sources-selections.json'
    for s in load(sources)['sources']:
        if owner_local:assert sha(ROOT/s['cache'])==s['sha256']
        else:excluded.append(s['cache'])
    gate=load(CAP/'proof-gate.json');assert gate['exitCode']==0 and 'Checked 2 Lean modules and 1 Bend files.' in gate['stdout']
    for p,h in gate['sourceSha256'].items():assert sha(ROOT/p)==h
    files=[CAP/p for p in load(CAP/'collection-basis.json')]+[CAP/'collection-basis.json',CAP/'proof-gate.json',sources]
    files+=[HERE/n for n in ['LockSources.lean','LockSources.bend','LockSourcesCase.lean','lock_sources_probe.py','lock_sources_observations.py','lock_sources_conformance.py']]
    return inputs,measured,details,{str(p.relative_to(ROOT)):sha(p) for p in sorted(files)},excluded
