#!/usr/bin/env python3
"""Owner-run copy study: three new tiny repositories; no existing backups."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import signal
import subprocess
import time
from locks_probe import redact

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    run=ROOT/'applications/evidence'/('restic-copy-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work=run/'work'
    for name in ['home','cache','tmp','private','source']:(work/name).mkdir(parents=True)
    (run/'probe.py').write_bytes(Path(__file__).read_bytes())
    (run/'helper.py').write_bytes((HERE/'locks_probe.py').read_bytes())
    tool=ROOT/'applications/tools/restic-0.20.0/restic'
    pin=json.loads((ROOT/'applications/sources/restic-tool.json').read_text());assert sha(tool)==pin['binarySha256']
    repos={n:work/('repo-'+n)for n in ['a','b','c']};passwords={}
    for n in repos:
        p=work/('password-'+n);p.write_text(secrets.token_urlsafe(32)+'\n');p.chmod(0o600);passwords[n]=p
    env=dict(PATH='/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),RESTIC_CACHE_DIR=str(work/'cache'),GOMAXPROCS='2',LANG='C.UTF-8')
    source=work/'source';(source/'shared.txt').write_bytes(b'shared copy fixture\n');(source/'mutable.txt').write_bytes(b'first copy image\n')
    commands=[];observations=[];owned=[]
    def public_json(path,value):path.write_bytes(redact(json.dumps(value,indent=2).encode()+b'\n'))
    def repo_images():
        return {n:{str(p.relative_to(repo)):dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(repo.rglob('*'))if p.is_file()}for n,repo in repos.items()}
    def source_image():return {p.name:dict(bytes=p.stat().st_size,sha256=sha(p),mtimeNs=p.stat().st_mtime_ns,inode=p.stat().st_ino)for p in sorted(source.iterdir())}
    def save():
        (work/'private/commands.json').write_text(json.dumps(commands,indent=2)+'\n');public_json(run/'commands.json',commands)
        (work/'private/observations.json').write_text(json.dumps(observations,indent=2)+'\n');public_json(run/'observations.json',observations)
    def command(label,target,args,expected=0):
        argv=[str(tool),'--repo',str(repos[target]),'--password-file',str(passwords[target]),'--json',*args]
        before=repo_images();source_before=source_image();started=time.monotonic()
        with (work/'private'/(label+'.stdout')).open('wb')as out,(work/'private'/(label+'.stderr')).open('wb')as err:
            child=subprocess.Popen(argv,cwd=source,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);owned.append(child)
            (run/'owned-processes.json').write_text(json.dumps([dict(pid=p.pid,retired=p.poll()is not None)for p in owned],indent=2)+'\n')
            timeout=False
            try:child.wait(timeout=45)
            except subprocess.TimeoutExpired:
                timeout=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
        streams={}
        for stream in ['stdout','stderr']:
            raw=work/'private'/(label+'.'+stream);p=run/(label+'.'+stream);p.write_bytes(redact(raw.read_bytes()))
            streams[stream]=dict(rawPrivatePath=str(raw.relative_to(run)),rawSha256=sha(raw),publicSha256=sha(p))
        try:os.killpg(child.pid,0)
        except ProcessLookupError:absent=True
        else:absent=False
        row=dict(case=label,target=target,argv=argv,before=before,after=repo_images(),sourceBefore=source_before,sourceAfter=source_image(),streams=streams,
                 outcome=dict(exitCode=child.returncode,timedOut=timeout,ownedGroupAbsent=absent),seconds=time.monotonic()-started)
        commands.append(row);save();print(label,child.returncode,flush=True)
        assert not timeout and absent and source_before==row['sourceAfter']
        assert child.returncode==expected,(label,child.returncode)
        return (work/'private'/(label+'.stdout')).read_bytes(),row
    def snapshots(label,n):
        raw,_=command(label,n,['snapshots']);result=json.loads(raw);assert isinstance(result,list);return result
    def copy(label,src,dst,extra=(),password=None,expected=0):
        before=snapshots(label+'-before',dst);source_state=snapshots(label+'-source',src)
        _,cmd=command(label,dst,['copy','--from-repo',str(repos[src]),'--from-password-file',str(password or passwords[src]),'--verbose',*extra],expected)
        after=snapshots(label+'-after',dst)
        observations.append(dict(case=label,source=src,destination=dst,selection=list(extra),sourceSnapshots=source_state,before=before,after=after,exitCode=cmd['outcome']['exitCode'],
            newIds=sorted({s['id']for s in after}-{s['id']for s in before}),sourceRepositoryUnchanged=cmd['before'][src]==cmd['after'][src],
            destinationUnchanged=cmd['before'][dst]==cmd['after'][dst]));save();return after
    try:
        command('help-copy','a',['copy','--help']);command('help-tag','a',['tag','--help'])
        command('init-a','a',['init','--repository-version','2'])
        command('init-b','b',['init','--repository-version','2','--from-repo',str(repos['a']),'--from-password-file',str(passwords['a']),'--copy-chunker-params'])
        command('init-c','c',['init','--repository-version','2'])
        command('backup-first','a',['backup','.','--host','copy-fixture-host','--tag','baseline'])
        first=snapshots('first-snapshot','a')[0]
        copy('explicit-first','a','b',[first['id']])
        (source/'mutable.txt').write_bytes(b'second copy image\n')
        command('backup-second','a',['backup','.','--host','copy-fixture-host','--tag','baseline','--parent',first['id']])
        original=snapshots('two-source-snapshots','a');assert len(original)==2
        copy('all-source','a','b');copy('repeat-source','a','b');copy('transitive','b','c')
        b=snapshots('b-before-tag','b');selected=next(s for s in b if s.get('original')==first['id'])
        command('tag-copy','b',['tag','--add','review',selected['id']])
        snapshots('b-after-tag','b')
        copy('restore-baseline-copy','a','b');copy('transitive-variant','b','c')
        copy('empty-tag-selection','a','c',['--tag','no-such-study-tag'])
        copy('wrong-source-password','a','c',password=passwords['b'],expected=12)
        final=snapshots('final-c','c');assert len(final)==3
        command('verify-c','c',['check','--read-data'])
        for i,s in enumerate(final):
            raw,_=command('dump-c-'+str(i),'c',['dump',s['id'],str(source/'mutable.txt')])
            observations.append(dict(case='dump-c-'+str(i),snapshot=s,payloadHex=raw.hex()));save()
        configs={}
        for n in repos:
            raw,_=command('config-'+n,n,['cat','config']);configs[n]=json.loads(raw)
        assert not any(list((r/'locks').glob('*'))for r in repos.values())
        receipt=dict(schema=1,tool=pin,platform=platform.platform(),architecture=platform.machine(),producerSha256=sha(run/'probe.py'),helperSha256=sha(run/'helper.py'),
                     rawObservationSha256=sha(work/'private/observations.json'),publicObservationSha256=sha(run/'observations.json'),commands=len(commands),copyCases=8,configs=configs,
                     allOwnedProcessesRetired=all(p.poll()is not None for p in owned),allOwnedGroupsAbsent=all(c['outcome']['ownedGroupAbsent']for c in commands),
                     allocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),
                     limits=['Three generated local repositories and two tiny files only. No real backup,remote backend,destructive maintenance or global install.',
                             'Copy selects actual snapshots;IDs,metadata,encrypted repository files and dump bytes are independently observed. No interrupted copy,concurrent writer,encryption or durability proof.',
                             'Raw user-bearing output and generated passwords remain ignored/private. Public output uses frozen helper redaction;semantic comparison must preserve the resulting information limits.'])
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');save()
    finally:
        for child in owned:
            if child.poll()is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
        (run/'owned-processes.json').write_text(json.dumps([dict(pid=p.pid,retired=p.poll()is not None)for p in owned],indent=2)+'\n')
        print('capture',run,flush=True)


if __name__=='__main__':main()
