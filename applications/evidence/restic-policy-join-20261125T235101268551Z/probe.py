"""Owner-run generated retention-policy -> prune -> restore fixture; local only."""
from datetime import datetime,timezone
import hashlib
import argparse
import json
import os
from pathlib import Path
import platform
import secrets
import signal
import stat
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,x:p.write_text(json.dumps(x,indent=2)+'\n')

def image(root):
    result={}
    if not root.exists():return result
    for directory,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            p=Path(directory)/name;s=p.lstat();rel=p.relative_to(root).as_posix()
            assert not stat.S_ISLNK(s.st_mode)
            result[rel]=dict(kind='directory',mode=stat.S_IMODE(s.st_mode)) if p.is_dir() else dict(kind='file',bytes=s.st_size,sha256=sha(p),mode=stat.S_IMODE(s.st_mode))
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--complete-prior-capture",action="store_true");selection=parser.parse_args()
    prior=ROOT/"applications/evidence/restic-policy-join-20261125T235000202024Z" if selection.complete_prior_capture else None
    assert os.geteuid()!=0
    tool=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']['restic'];binary=Path(tool['path']);assert sha(binary)==tool['sha256']
    if prior is None:
        work=Path(tempfile.mkdtemp(prefix='rules-restic-policy-join-',dir='/private/tmp'))
        for name in ['home','cache','tmp','source-a','source-b','targets']:(work/name).mkdir()
        password=work/'password';password.write_text(secrets.token_urlsafe(32)+'\n');password.chmod(0o600)
    else:
        original=json.loads((prior/"setup.json").read_text());work=Path(original["work"])
        assert work.parent==Path("/private/tmp") and work.name.startswith("rules-restic-policy-join-")
        assert original["binarySha256"]==tool["sha256"] and original["producerSha256"]==sha(prior/"probe.py")
        password=work/"password";assert password.is_file() and stat.S_IMODE(password.stat().st_mode)==0o600
    repo=work/'repository';run=ROOT/'applications/evidence'/('restic-policy-join-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir();(run/'probe.py').write_bytes(Path(__file__).read_bytes())
    setup=dict(schema=1,work=str(work),binary=str(binary),binarySha256=tool['sha256'],platform=platform.platform(),architecture=platform.machine(),producerSha256=sha(run/'probe.py'),
      scope='Fresh generated local repository and two host/path groups,two versions each. Private child HOME/cache/password. Selected keep-last-one/default grouping,owned permissions refusal,combined forget/prune,full check and restore. No personal/remote repo,arbitrary cleanup,concurrent-owner/back-end/crash/platform qualification. Password bytes and hashes are never captured.')
    if prior is not None:setup["continuation"]={"capture":str(prior.relative_to(ROOT)),"setupSha256":sha(prior/"setup.json"),"editsSha256":sha(prior/"authored-edits.json"),"commandsSha256":sha(prior/"commands.json")}
    write(run/"setup.json",setup);rows=[];edits=[];modes=None
    prefix=[str(binary),'-r',str(repo),'--password-file',str(password),'--cache-dir',str(work/'cache'),'--json']
    env=dict(PATH='/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8',RESTIC_PROGRESS_FPS='0')
    def state():return {name:image(work/name) for name in ['repository','source-a','source-b','targets']}
    def command(label,args,expected=0):
        before=state();start=time.monotonic();child=subprocess.Popen(prefix+args,cwd=work,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        print(json.dumps(dict(start=label,pid=child.pid)),flush=True);timed=False
        try:out,err=child.communicate(timeout=90)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
        for n,b in [('stdout',out),('stderr',err)]:(run/(label+'.'+n)).write_bytes(b)
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        row=dict(id=label,argv=prefix+args,pid=child.pid,exitCode=child.returncode,timedOut=timed,groupAbsent=absent,seconds=time.monotonic()-start,before=before,after=state(),streams={n:sha(run/(label+'.'+n)) for n in ['stdout','stderr']})
        rows.append(row);write(run/'commands.json',rows);print(json.dumps(dict(finish=label,exitCode=child.returncode,seconds=row['seconds'])),flush=True)
        assert not timed and absent and child.returncode==expected,'Preserve this failure before changing or repeating the fixture.'
        return row
    def edit_mode(mode,label):
        before=state();(repo/'snapshots').chmod(mode);edits.append(dict(id=label,authored=True,path=str(repo/'snapshots'),mode=mode,before=before,after=state()));write(run/'authored-edits.json',edits)
    try:
        if prior is None:
            command('init',['init'])
            versions={};snapshots={};shared=b'Generated shared file across both groups.\n'
            for group in ['a','b']:
                source=work/('source-'+group);(source/'shared.txt').write_bytes(shared)
                for version in [0,1]:
                    data=('Generated '+group+' version '+str(version)+'.\n').encode();(source/'state.txt').write_bytes(data)
                    label=group+str(version);versions[label]=dict(group=group,rank=(0 if group=='a' else 2)+version,source=str(source),stateSha256=sha(source/'state.txt'),sharedSha256=sha(source/'shared.txt'))
                    command('backup-'+label,['backup','--host','rules-policy-'+group,'--time','2020-01-0'+str(versions[label]['rank']+1)+' 00:00:00',str(source)])
                    lines=[json.loads(s) for s in (run/('backup-'+label+'.stdout')).read_text().splitlines()];summary=next(s for s in lines if s.get('message_type')=='summary');snapshots[label]=summary['snapshot_id']
            write(run/'inputs.json',dict(versions=versions,snapshots=snapshots,shared=hashlib.sha256(shared).hexdigest()))
            command('snapshots-before',['snapshots'])
            blobs=dict(shared=hashlib.sha256(shared).hexdigest(),**{label:v['stateSha256'] for label,v in versions.items()})
            for label,identity in blobs.items():command('blob-before-'+label,['cat','blob',identity])
            policy=['forget','--keep-last','1','--prune','--max-unused','0']
            command('policy-preview',policy+['--dry-run'])
            modes=stat.S_IMODE((repo/'snapshots').stat().st_mode);edit_mode(0o500,'make-own-snapshot-directory-read-only')
            assert not os.access(repo/'snapshots',os.W_OK)
            try:command('policy-remove-refused',policy,expected=3)
            finally:edit_mode(modes,'restore-own-snapshot-directory-mode');modes=None
        else:
            assert state()==json.loads((prior/"authored-edits.json").read_text())[-1]["after"]
            inputs=json.loads((prior/"inputs.json").read_text());versions=inputs["versions"];snapshots=inputs["snapshots"]
            write(run/"inputs.json",inputs)
            blobs=dict(shared=inputs["shared"],**{label:v["stateSha256"] for label,v in versions.items()})
            policy=["forget","--keep-last","1","--prune","--max-unused","0"]
        command('policy-apply',policy)
        command('snapshots-after',['snapshots'])
        command('full-check',['check','--read-data'])
        for label,identity in blobs.items():command('blob-after-'+label,['cat','blob',identity],expected=1 if label in ['a0','b0'] else 0)
        for group in ['a','b']:
            target=work/'targets'/group;command('restore-'+group,['restore',snapshots[group+'1'],'--target',str(target),'--verify'])
            source=work/('source-'+group);restored=target/str(source).lstrip('/')
            assert image(source)==image(restored)
        write(run/'receipt.json',dict(schema=1,complete=True,commands=len(rows),authoredModeChanges=len(edits),allRecordedGroupsAbsent=all(r['groupAbsent'] for r in rows),setupSha256=sha(run/'setup.json'),producerSha256=sha(run/'probe.py'),workAllocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),
          scope='Native collection only; policy selection/effect,JSON phase semantics,blob/readback and models require independent replay. Five selected file-data blobs,not complete repository reachability decoder. No concurrency/backend/crash claim.'))
        print(json.dumps(dict(run=str(run),work=str(work),complete=True)),flush=True)
    except BaseException as e:
        write(run/'failure.json',dict(type=type(e).__name__,message=str(e),commands=len(rows)));print(json.dumps(dict(run=str(run),work=str(work),complete=False)),flush=True);raise
    finally:
        if modes is not None:edit_mode(modes,'finally-restore-own-snapshot-directory-mode')
        write(run/'termination.json',dict(recordedGroupsAbsent=all(r['groupAbsent'] for r in rows),snapshotDirectoryMode=stat.S_IMODE((repo/'snapshots').stat().st_mode) if (repo/'snapshots').exists() else None))

if __name__=='__main__':main()
