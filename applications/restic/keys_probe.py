#!/usr/bin/env python3
"""Private repository/key-wrapper study; passwords and raw output stay ignored."""
from datetime import datetime,timezone
import hashlib,json,os,secrets,signal,subprocess,time
from pathlib import Path
from locks_probe import redact

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    run=ROOT/'applications/evidence'/('restic-keys-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));work=run/'work'
    for name in ['home','cache','tmp','private','source']:(work/name).mkdir(parents=True)
    (run/'probe.py').write_bytes(PRODUCER);(run/'helper.py').write_bytes((HERE/'locks_probe.py').read_bytes())
    tool=ROOT/'applications/tools/restic-0.20.0/restic';pin=json.loads((ROOT/'applications/sources/restic-tool.json').read_text());assert sha(tool)==pin['binarySha256']
    passwords={}
    for name in ['a','b','wrong','empty']:
        p=work/('password-'+name);p.write_text(''if name=='empty'else secrets.token_urlsafe(32)+'\n');p.chmod(0o600);passwords[name]=p
    source=work/'source';payload=source/'payload.txt';payload.write_bytes(b'private key-custody fixture\n')
    repo=work/'repository';env=dict(PATH='/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),RESTIC_CACHE_DIR=str(work/'cache'),GOMAXPROCS='2',LANG='C.UTF-8')
    commands=[];owned=[]
    def image():return {str(p.relative_to(repo)):dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(repo.rglob('*'))if p.is_file()}
    def public_json(path,value):path.write_bytes(redact(json.dumps(value,indent=2).encode()+b'\n'))
    def command(label,password,args,expected=0,hint=None):
        argv=[str(tool),'--repo',str(repo),'--password-file',str(passwords[password]),'--json',*(['--key-hint',hint]if hint else[]),*args]
        before=image();started=time.monotonic()
        with(work/'private'/(label+'.stdout')).open('xb')as out,(work/'private'/(label+'.stderr')).open('xb')as err:
            child=subprocess.Popen(argv,cwd=source,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);owned.append(child)
            (run/'owned-processes.json').write_text(json.dumps([dict(pid=p.pid,retired=p.poll()is not None)for p in owned],indent=2)+'\n')
            timed=False
            try:child.wait(timeout=60)
            except subprocess.TimeoutExpired:timed=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
        try:os.killpg(child.pid,0)
        except ProcessLookupError:absent=True
        else:absent=False
        streams={}
        for s in ['stdout','stderr']:
            raw=work/'private'/(label+'.'+s);public=run/(label+'.'+s);public.write_bytes(redact(raw.read_bytes()))
            streams[s]=dict(rawPrivatePath=str(raw.relative_to(run)),rawSha256=sha(raw),publicSha256=sha(public))
        row=dict(case=label,passwordLabel=password,keyHint=hint,argv=argv,before=before,after=image(),streams=streams,
                 outcome=dict(exitCode=child.returncode,timedOut=timed,ownedGroupAbsent=absent),seconds=time.monotonic()-started)
        commands.append(row);(work/'private/commands.json').write_text(json.dumps(commands,indent=2)+'\n');public_json(run/'commands.json',commands)
        print(label,child.returncode,flush=True)
        assert not timed and absent and child.returncode==expected,(label,child.returncode,expected)
        assert payload.read_bytes()==b'private key-custody fixture\n'
        return row
    def key_ids():return {p.name for p in(repo/'keys').iterdir()if p.is_file()}
    def listing(label,password,hint=None):
        row=command(label,password,['key','list'],hint=hint)
        keys=json.loads((work/'private'/(label+'.stdout')).read_text());assert {k['id']for k in keys}==key_ids()
        assert sum(k['current']for k in keys)==1
        return next(k['id']for k in keys if k['current'])
    try:
        command('version','a',['version']);command('help-passwd','a',['key','passwd','--help'])
        command('init','a',['init','--repository-version','2'])
        command('backup','a',['backup','.','--host','key-fixture-host'])
        a=listing('list-initial','a');initial=key_ids()
        command('add-same-password','a',['key','add','--new-password-file',str(passwords['a']),'--user','fixture-user','--host','fixture-host'],hint=a)
        duplicate,=key_ids()-initial
        assert listing('list-duplicate','a',hint=a)==a
        command('remove-current-with-other','a',['key','remove',a],expected=1,hint=a)
        previous=key_ids()
        command('change-one-password','a',['key','passwd','--new-password-file',str(passwords['b']),'--user','fixture-user','--host','fixture-host'],hint=a)
        changed,=key_ids()-previous;assert a not in key_ids()and duplicate in key_ids()
        assert listing('list-new-password','b',hint=changed)==changed
        assert listing('list-old-password','a',hint=duplicate)==duplicate
        command('dump-old-password','a',['dump','latest','/payload.txt'],hint=duplicate)
        command('dump-new-password','b',['dump','latest','/payload.txt'],hint=changed)
        command('add-wrong-password','wrong',['key','add','--new-password-file',str(passwords['b'])],expected=12)
        command('add-empty-password','b',['key','add','--new-password-file',str(passwords['empty'])],expected=1,hint=changed)
        command('remove-other-wrapper','a',['key','remove',changed],hint=duplicate)
        command('removed-password','b',['key','list'],expected=12,hint=changed)
        assert listing('list-remaining','a',hint=duplicate)==duplicate
        command('remove-only-current','a',['key','remove',duplicate],expected=1,hint=duplicate)
        command('remove-unknown','a',['key','remove','f'*64],expected=1,hint=duplicate)
        command('dump-final','a',['dump','latest','/payload.txt'],hint=duplicate)
        for name in ['dump-old-password','dump-new-password','dump-final']:assert(work/'private'/(name+'.stdout')).read_bytes()==payload.read_bytes()
        public_json(run/'receipt.json',dict(schema=1,producerSha256=sha(run/'probe.py'),helperSha256=sha(run/'helper.py'),tool=dict(path=str(tool),sha256=sha(tool)),
            commands=len(commands),allOwnedGroupsAbsent=all(c['outcome']['ownedGroupAbsent']for c in commands),identities=dict(initial=a,duplicate=duplicate,changed=changed),
            payloadSha256=sha(payload),workAllocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),
            limits=['One new local repository,one tiny backup,random private passwords. No real backup,key export/decryption or public plaintext credentials.',
                    'Same-password duplicate makes password-change scope visible;explicit key hints pin intended access wrapper. No arbitrary ordering/race/fallback qualification.',
                    'Repository images are file hashes only;encrypted key/password files remain ignored. Public CLI streams redact actual user/host values;raw outputs remain private.',
                    'Successful native operations only except admission/current-key refusals. No interruption,failed verify/save/removal,remote backend,cryptographic proof or stolen-key revocation experiment.']))
    finally:
        for p in owned:
            if p.poll()is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
        (run/'owned-processes.json').write_text(json.dumps([dict(pid=p.pid,retired=p.poll()is not None)for p in owned],indent=2)+'\n')
        print('capture',run,flush=True)


if __name__=='__main__':main()
