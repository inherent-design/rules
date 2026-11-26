#!/usr/bin/env python3
"""Own new local repositories for init/open/format-migration comparisons."""
from datetime import datetime,timezone
import hashlib,json,os,secrets,shutil,signal,subprocess,tempfile,time
from pathlib import Path
from locks_probe import redact

ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,indent=2)+'\n')


def main():
    cap=ROOT/'applications/evidence'/('restic-repository-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));cap.mkdir()
    work=Path(tempfile.mkdtemp(prefix='rules-restic-repository-',dir='/private/tmp'))
    for name in ['home','cache','tmp','private','source']:(work/name).mkdir()
    (cap/'probe.py').write_bytes(Path(__file__).read_bytes());helper=Path(__file__).with_name('locks_probe.py');(cap/'helper.py').write_bytes(helper.read_bytes())
    password=work/'password';password.write_text(secrets.token_urlsafe(32)+'\n');password.chmod(0o600)
    wrong=work/'wrong-password';wrong.write_text(secrets.token_urlsafe(32)+'\n');wrong.chmod(0o600)
    payload=work/'source/payload.txt';payload.write_bytes(b'owned repository-format fixture\n')
    tool=ROOT/'applications/tools/restic-0.20.0/restic';pin=json.loads((ROOT/'applications/sources/restic-tool.json').read_text());assert sha(tool)==pin['binarySha256']
    env=dict(PATH='/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),RESTIC_CACHE_DIR=str(work/'cache'),GOMAXPROCS='2',LANG='C.UTF-8')
    write(cap/'setup.json',dict(schema=1,work=str(work),producerSha256=sha(cap/'probe.py'),helperSha256=sha(cap/'helper.py'),binarySha256=sha(tool),binary=str(tool),environment=env,payloadSha256=sha(payload),scope='Owned local repositories only;authored missing-config derivatives are not crash-generated states. No remote backend,live repository,cryptographic proof,or recovery claim.'))
    commands=[];interventions=[];owned=[]
    def image(repo):
        files={}
        for p in sorted(repo.rglob('*')):
            if p.is_file():
                assert not p.is_symlink();s=p.stat();files[str(p.relative_to(repo))]=dict(bytes=s.st_size,sha256=sha(p),mode=s.st_mode&0o777,mtimeNs=s.st_mtime_ns)
        return dict(exists=repo.is_dir(),files=files)
    def public(name,value):(cap/name).write_bytes(redact(json.dumps(value,indent=2).encode()+b'\n'))
    def command(label,repo,args,expected,password_path=password):
        argv=[str(tool),'--repo',str(repo),'--password-file',str(password_path),'--json',*args];before=image(repo)
        out=work/'private'/(label+'.stdout');err=work/'private'/(label+'.stderr');started=time.monotonic()
        with out.open('xb')as stdout,err.open('xb')as stderr:
            child=subprocess.Popen(argv,cwd=work/'source',env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True);owned.append(child)
            write(cap/'current-process.json',dict(label=label,pid=child.pid,status='running'))
            timed=False
            try:code=child.wait(timeout=60)
            except subprocess.TimeoutExpired:
                timed=True;child.send_signal(signal.SIGTERM)
                try:code=child.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);code=child.wait()
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        write(cap/'current-process.json',dict(label=label,pid=child.pid,status='terminal',exitCode=code,groupAbsent=absent,timedOut=timed))
        streams={}
        for key,p in [('stdout',out),('stderr',err)]:
            dest=cap/(label+'.'+key);dest.write_bytes(redact(p.read_bytes()));streams[key]=dict(path=dest.name,publicSha256=sha(dest),rawPrivatePath=str(p),rawSha256=sha(p))
        row=dict(label=label,repo=str(repo),argv=argv,before=before,after=image(repo),pid=child.pid,seconds=time.monotonic()-started,exitCode=code,groupAbsent=absent,timedOut=timed,streams=streams)
        commands.append(row);write(work/'private/commands.json',commands);public('commands.json',commands);print(json.dumps(dict(label=label,exitCode=code,groupAbsent=absent)),flush=True)
        assert not timed and absent and code==expected,(label,code,expected)
        assert sha(payload)==json.loads((cap/'setup.json').read_text())['payloadSha256']
        return row
    def derived(label,source,remove):
        target=work/label;shutil.copytree(source,target,copy_function=shutil.copy2)
        before=image(target)
        for name in remove:
            p=target/name
            if p.is_dir():shutil.rmtree(p)
            else:p.unlink()
        interventions.append(dict(label=label,source=str(source),target=str(target),remove=remove,before=before,after=image(target),scope='Explicitly authored derivative;not an observed failed initialization or crash.'))
        write(work/'private/interventions.json',interventions);public('interventions.json',interventions);return target
    print(json.dumps(dict(capture=str(cap),work=str(work))),flush=True)
    command('version',work/'absent',['version'],0)
    command('unsupported-init',work/'unsupported',['init','--repository-version','99'],1)
    command('missing-open',work/'missing',['cat','config'],10)
    repo=work/'repository'
    command('init-v1',repo,['init','--repository-version','1'],0)
    command('config-v1',repo,['cat','config'],0)
    command('backup-v1',repo,['backup','.','--host','fixture-host'],0)
    command('existing-init',repo,['init','--repository-version','2'],1)
    command('wrong-password',repo,['cat','config'],12,password_path=wrong)
    partial=derived('key-only',repo,['config','snapshots','data','index'])
    command('key-only-init',partial,['init','--repository-version','2'],1)
    command('key-only-open',partial,['cat','config'],10)
    snapshot=derived('snapshot-only',repo,['config','keys'])
    command('snapshot-only-init',snapshot,['init','--repository-version','2'],1)
    command('list-migrations',repo,['migrate'],0)
    command('unknown-migration',repo,['migrate','not_a_fixture_migration'],0)
    command('config-after-unknown',repo,['cat','config'],0)
    command('migrate-with-unknown',repo,['migrate','not_a_fixture_migration','upgrade_repo_v2'],0)
    command('config-v2',repo,['cat','config'],0)
    command('repeat-migration',repo,['migrate','upgrade_repo_v2'],0)
    command('list-after-migration',repo,['migrate'],0)
    command('dump-after-migration',repo,['dump','latest','/payload.txt'],0)
    assert(work/'private/dump-after-migration.stdout').read_bytes()==payload.read_bytes()
    command('check-after-migration',repo,['check','--read-data'],0)
    command('init-default',work/'default-repository',['init'],0)
    command('config-default',work/'default-repository',['cat','config'],0)
    assert sha(tool)==pin['binarySha256']
    public('receipt.json',dict(schema=1,commands=len(commands),allGroupsAbsent=all(c['groupAbsent']for c in commands),sourcePayloadSha256=sha(payload),toolSha256=sha(tool),rawCommandsSha256=sha(work/'private/commands.json'),rawInterventionsSha256=sha(work/'private/interventions.json'),scope='Local full CLI invocations;unknown migration and repeated inapplicable migration retain exit0. No interrupted writer,force migration,remote backend,or recovery qualification.'))
    public('final-images.json',{name:image(work/name)for name in ['repository','default-repository','key-only','snapshot-only','unsupported','missing','absent']})
    write(cap/'collection-basis.json',{p.name:sha(p)for p in sorted(cap.iterdir())if p.is_file()})
    print(json.dumps(dict(capture=str(cap),commands=len(commands),allGroupsAbsent=True)),flush=True)


if __name__=='__main__':main()
