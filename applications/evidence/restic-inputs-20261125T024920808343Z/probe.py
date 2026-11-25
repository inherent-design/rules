#!/usr/bin/env python3
"""Own generated source/list files and a fresh local repository; no live data."""
from datetime import datetime,timezone
import hashlib,json,os,platform,secrets,signal,subprocess,time
from pathlib import Path
from locks_probe import redact

ROOT=Path(__file__).resolve().parents[2]
PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    run=ROOT/'applications/evidence'/('restic-inputs-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work=run/'work'
    for name in ['home','cache','tmp','private','source','lists']:(work/name).mkdir(parents=True)
    source=work/'source';(run/'probe.py').write_bytes(PRODUCER)
    (run/'helper.py').write_bytes((Path(__file__).parent/'locks_probe.py').read_bytes())
    pin=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']['restic'];tool=Path(pin['path'])
    assert sha(tool)==pin['sha256']
    payloads={name:('generated '+name+'\n').encode()for name in ['keep.txt','secret.tmp','nested/keep.txt','nested/secret.tmp',
        'pruned/keep.txt','#literal.txt','space name.txt','Ω 日本.txt','[literal].txt','line\nbreak.txt']}
    for name,data in payloads.items():
        p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    lists=dict(normal=b'keep.txt\n#literal.txt\nspace name.txt\n',verbatim=b'keep.txt\n#literal.txt\nspace name.txt\n',
        glob=b'*.tmp\n',literal=b'[literal].txt\n',raw=b'line\nbreak.txt\0#literal.txt\0',
        raw_unterminated=b'keep.txt',raw_empty=b'\0',partial=b'keep.txt\nabsent.txt\n')
    for name,data in lists.items():(work/'lists'/name).write_bytes(data)
    password=work/'password';password.write_text(secrets.token_urlsafe(32)+'\n');password.chmod(0o600)
    repo=work/'repository';env=dict(PATH='/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),RESTIC_CACHE_DIR=str(work/'cache'),GOMAXPROCS='2',LANG='C.UTF-8')
    prefix=[str(tool),'--repo',str(repo),'--password-file',str(password),'--json']
    commands=[];cases=[];owned=[]
    def snapshot_ids():return sorted(p.name for p in(repo/'snapshots').glob('*')if p.is_file())
    def image():
        return {str(p.relative_to(source)):dict(sha256=sha(p),size=p.stat().st_size,mtimeNs=p.stat().st_mtime_ns,inode=p.stat().st_ino)
            for p in sorted(source.rglob('*'))if p.is_file()}
    original=image()
    def command(label,args):
        assert not any(c['case']==label for c in commands)
        started=time.monotonic()
        with(work/'private'/(label+'.stdout')).open('xb')as out,(work/'private'/(label+'.stderr')).open('xb')as err:
            p=subprocess.Popen(prefix+args,cwd=source,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
            owned.append(p);timeout=False
            (run/'owned-processes.json').write_text(json.dumps([dict(pid=c.pid,retired=c.poll()is not None)for c in owned],indent=2)+'\n')
            try:p.wait(timeout=30)
            except subprocess.TimeoutExpired:
                timeout=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
        try:os.killpg(p.pid,0)
        except ProcessLookupError:absent=True
        else:absent=False
        streams={}
        for stream in ['stdout','stderr']:
            raw=work/'private'/(label+'.'+stream);public=run/(label+'.'+stream);public.write_bytes(redact(raw.read_bytes()))
            streams[stream]=dict(rawSha256=sha(raw),publicSha256=sha(public),rawPrivatePath=str(raw.relative_to(run)))
        commands.append(dict(case=label,argv=prefix+args,seconds=time.monotonic()-started,streams=streams,
            outcome=dict(exitCode=p.returncode,timedOut=timeout,ownedGroupAbsent=absent)))
        (run/'commands.json').write_bytes(redact((json.dumps(commands,indent=2)+'\n').encode()))
        (run/'owned-processes.json').write_text(json.dumps([dict(pid=c.pid,retired=c.poll()is not None)for c in owned],indent=2)+'\n')
        assert not timeout and absent,(label,'unconfirmed retirement');print(label,p.returncode,flush=True)
        return p.returncode
    def raw_json(label):return [json.loads(line)for line in(work/'private'/(label+'.stdout')).read_text().splitlines()]
    def backup(label,args,expected):
        before=snapshot_ids();code=command(label,['backup',*args,'--host','input-fixture-host']);after=snapshot_ids()
        assert image()==original,'Backup changed its generated sources'
        new=sorted(set(after)-set(before));assert set(before)<=set(after)
        row=dict(case=label,request=args,exitCode=code,newSnapshots=new,files=[],nodes=[])
        if new:
            assert len(new)==1;assert command(label+'-ls',['ls',new[0]])==0
            nodes=raw_json(label+'-ls')
            for n in nodes:
                if 'path'not in n or n.get('struct_type')!='node':continue
                p=Path(n['path']);assert p==source or p.is_relative_to(source)or source.is_relative_to(p),(label,n)
                if p.is_relative_to(source):
                    relative=str(p.relative_to(source));row['nodes'].append(dict(path=relative,type=n['type']))
                    if n['type']=='file':row['files'].append(relative)
            row['files'].sort();row['nodes'].sort(key=lambda n:n['path'])
            assert set(row['files'])<=set(payloads)
        cases.append(row);(run/'observations.json').write_text(json.dumps(cases,indent=2)+'\n')
        assert code==expected,(label,code,expected)
    try:
        assert command('init',['init','--repository-version','2'])==0
        specifications=[
            ('directory',['.'],0),('exclude-descendants',['.','--exclude','*.tmp'],0),
            ('explicit-file',['secret.tmp','--exclude','*.tmp'],0),('explicit-directory',['nested','--exclude','nested'],0),
            ('ordered-reinclude',['.','--exclude','*.tmp','--exclude','!secret.tmp'],0),
            ('ordered-reexclude',['.','--exclude','!secret.tmp','--exclude','*.tmp'],0),
            ('pruned-parent',['.','--exclude','pruned','--exclude','!pruned/keep.txt'],0),
            ('reopened-parent',['.','--exclude','pruned','--exclude','!pruned','--exclude','!pruned/keep.txt'],0),
            ('insensitive',['.','--iexclude','*.TMP'],0),('sensitive',['.','--exclude','*.TMP'],0),
            ('normal-list',['--files-from',str(work/'lists/normal')],0),
            ('verbatim-list',['--files-from-verbatim',str(work/'lists/verbatim')],0),
            ('glob-list',['--files-from',str(work/'lists/glob'),'--exclude','*.tmp'],0),
            ('verbatim-glob',['--files-from-verbatim',str(work/'lists/glob')],1),
            ('normal-brackets',['--files-from',str(work/'lists/literal')],1),
            ('verbatim-brackets',['--files-from-verbatim',str(work/'lists/literal')],0),
            ('raw-newline',['--files-from-raw',str(work/'lists/raw')],0),
            ('raw-unterminated',['--files-from-raw',str(work/'lists/raw_unterminated')],1),
            ('raw-empty',['--files-from-raw',str(work/'lists/raw_empty')],1),
            ('partial-list',['--files-from-verbatim',str(work/'lists/partial')],3)]
        for label,args,expected in specifications:backup(label,args,expected)
        assert not list((repo/'locks').glob('*'))
        (run/'receipt.json').write_text(json.dumps(dict(schema=1,tool=pin,platform=platform.platform(),architecture=platform.machine(),
            producerSha256=hashlib.sha256(PRODUCER).hexdigest(),helperSha256=sha(run/'helper.py'),cases=len(cases),commands=len(commands),
            sourceBefore=original,sourceAfter=image(),listSha256={n:sha(work/'lists'/n)for n in lists},
            allOwnedProcessesRetired=all(p.poll()is not None for p in owned),finalLocks=[],
            scope='Generated regular files/list inputs and fresh local v2 repository only;real restic backup/ls,not dry-run selection. No user repository or file read.',
            limits=['One macOS filesystem;no remote backend,race,special file,symlink,cloud,device boundary or restore/content-read proof.',
                'Saved paths/types observed by ls;this cohort does not dump each saved payload or validate repository chunking/encryption.',
                'Exclusion/order/list semantics remain selected-case evidence;general pattern language and UI/shell parsing unqualified.']),indent=2)+'\n')
    finally:
        for p in owned:
            if p.poll()is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
        (run/'owned-processes.json').write_text(json.dumps([dict(pid=c.pid,retired=c.poll()is not None)for c in owned],indent=2)+'\n')
        print('capture',run,flush=True)


if __name__=='__main__':main()
