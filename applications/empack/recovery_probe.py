#!/usr/bin/env python3
"""Owner-run installed-CLI recovery on tiny authored forensic journals.

No live state or actual crash. A copied-source helper supplies real private root
associations/object witnesses; all recover/preview/approval actions use the pinned
installed executable. Stop on a failed positive setup control and retain evidence.
"""
from datetime import datetime,timezone
import errno
import fcntl
import hashlib
import inspect
import json
import os
from pathlib import Path
import platform
import pty
import select
import signal
import struct
import subprocess
import termios
import time

from initializer_probe import retire_owned
from root_state_observations import image

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
REV='0b4462e3032b4f09230b15329722eabefb7f574c'
PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert platform.system()=='Darwin'
    repo=ROOT.parent/'empack';assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==REV
    prior=ROOT/'applications/evidence/empack-initializer-20261124T205241728563Z';r=json.loads((prior/'receipt.json').read_text())
    scaffold=prior/'work/current.rs';assert sha(scaffold)==r['generatedSha256']['current.rs']
    program=Path('/Users/zer0cell/.local/bin/empack');assert sha(program)=='99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
    pins={}
    paths=['crates/empack-lib/src/'+p for p in ['engine/api/recovery.rs','engine/publication/recovery.rs','engine/publication.rs','engine/publication/journal_identity.rs','application/engine_host.rs','application/cli.rs','engine/snapshot.rs']]
    for path in paths:
        raw=subprocess.check_output(['git','-C',str(repo),'show',REV+':'+path]);assert raw==(repo/path).read_bytes();pins[path]=hashlib.sha256(raw).hexdigest()
        assert subprocess.check_output(['git','-C',str(repo),'show','v0.8.8-beta:'+path])==raw
    run=ROOT/'applications/evidence'/('empack-recovery-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work=run/'work'
    for n in ['home','tmp','config','fixtures']:(work/n).mkdir(parents=True,mode=0o700)
    (run/'images').mkdir();(run/'probe.py').write_bytes(PRODUCER);(run/'driver.rs').write_bytes((HERE/'recovery_fixture_oracle.rs').read_bytes())
    source=scaffold.read_text();old='include!("'+str(prior/'driver.rs')+'");';assert source.count(old)==1
    source=source.replace(old,'include!("'+str(run/'driver.rs')+'");');(work/'main.rs').write_text(source)
    env=dict(PATH='/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),XDG_CONFIG_HOME=str(work/'config'),LANG='en_US.UTF-8',TERM='xterm-256color',NO_COLOR='1')
    receipt=dict(schema=1,sourceRevision=REV,sourceSha256=pins,releaseTag='v0.8.8-beta',selectedSourceMatchesTag=True,
        platform=platform.platform(),binary=str(program),binarySha256=sha(program),scaffold=str(scaffold.relative_to(ROOT)),scaffoldSha256=sha(scaffold),
        priorReceipt=str((prior/'receipt.json').relative_to(ROOT)),priorReceiptSha256=sha(prior/'receipt.json'),
        compiler=r['compiler'],libraries=r['libraries'],producerSha256=sha(run/'probe.py'),driverSha256=sha(run/'driver.rs'),
        generatedSha256=sha(work/'main.rs'),retireHelperSha256=hashlib.sha256(inspect.getsource(retire_owned).encode()).hexdigest(),
        limits=['Authored forensic schema5 journals on disposable roots,not actual interrupted publisher output or power-loss recovery.',
            'Recovery runs through installed0.8.8CLI;source excerpts match selected tag but no full reproducible build correspondence is claimed.',
            'One small copied-source setup helper,real root/file identity and initializer;not a recovery oracle or Engine preparation implementation.',
            'No live operation store,personal project,game,network,global cache or Moment recovery accessed. No Cargo/full-engine build.'])
    commands=[];cases=[];active={}
    def save():
        receipt.update(commands=commands,cases=cases)
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    def snap(name,base):
        p=run/'images'/(name+'.json');p.write_text(json.dumps(image(base),sort_keys=True,separators=(',',':')))
        return dict(image=str(p.relative_to(run)),sha256=sha(p))
    def record(label,argv,code,out,err,base=None,extra=None):
        for stream,data in [('stdout',out),('stderr',err)]:(run/(label+'.'+stream)).write_bytes(data)
        row=dict(label=label,argv=list(map(str,argv)),exitCode=code,stdoutSha256=sha(run/(label+'.stdout')),stderrSha256=sha(run/(label+'.stderr')))
        if extra:row.update(extra)
        commands.append(row);save();print(label,code,flush=True);return row
    def command(label,argv,base=None):
        before=snap(label+'-before',base)if base else None
        proc=subprocess.Popen(list(map(str,argv)),cwd=work,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        active[label]=proc
        try:out,err=proc.communicate(timeout=30)
        except BaseException:
            retire_owned(proc);raise
        else:active.pop(label,None)
        try:os.killpg(proc.pid,0)
        except ProcessLookupError:absent=True
        else:absent=False
        assert absent
        return record(label,argv,proc.returncode,out,err,extra=dict(pid=proc.pid,ownedGroupAbsent=absent,before=before,after=snap(label+'-after',base)if base else None))
    def cli(base,action,operation=None,preview=False,yes=True):
        a=[program,'--state-dir',base/'host','--cache-dir',base/'cache','--workdir',base/'project','--color','never']
        if yes:a+=['--yes']
        if preview:a+=['--dry-run']
        a+=['recover',action]
        if operation:a+=['--operation',operation]
        return a
    def fp(data):return dict(sha256=list(hashlib.sha256(data).digest()),bytes=len(data),readonly=False,executable=False)
    def write(path,data,mode=0o600):path.write_bytes(data);path.chmod(mode)
    def fixture(name,restoring=False,current='before',candidate='valid',before_image='valid',schema=5,committed=False):
        base=work/'fixtures'/name
        for n in ['project/pack','host','cache','originals']:(base/n).mkdir(parents=True,mode=0o700)
        target=base/'project/pack/rules.txt';before=b'old\n';after=b'new\n'
        if restoring:before,after=after,before
        write(target,before,0o644)
        c=command(name+'-setup',[helper,base,'setup'],base);assert c['exitCode']==0,'Retain failed helper.'
        evidence=json.loads((run/(name+'-setup.stdout')).read_text());key=evidence['key'];state=base/'host'/key;operation='op-study-'+name
        retained=state/operation;retained.mkdir(mode=0o700)
        write(retained/'before-0',before if before_image=='valid'else b'bad\n')
        candidate_name=('restore-'if restoring else 'after-')+'0'
        if candidate!='missing':write(retained/candidate_name,after if candidate=='valid'else b'bad\n')
        saved=dict(persistent=evidence['file']['persistent']);assert saved['persistent']is not None
        if current!='before':
            os.rename(target,base/'originals/original-before')
            if current!='absent':write(target,after if current=='after'else before if current=='replacement'else b'usr\n',0o644)
        journal=dict(schema=schema,root=dict(persistent=evidence['root']['persistent']),operation=operation,
            changes=[dict(target='pack/rules.txt',before=fp(before),before_object=saved,after=fp(after),sibling='.empack-publish-'+operation+'-0',unix_mode=0o644,applied=current=='after')],
            groups=[dict(scopes=['pack'],limits=dict(entries=100,depth=8,file_bytes=1024,total_bytes=4096),filter=None)],
            expected={'pack/rules.txt':fp(after)},restoring=restoring,retained_files=sorted(['before-0',candidate_name]),committed=committed)
        write(state/'journal.json',json.dumps(journal,separators=(',',':')).encode())
        row=dict(id=name,fixture=str(base.relative_to(work)),input=dict(restoring=restoring,current=current,candidate=candidate,beforeImage=before_image,schema=schema,committed=committed),
            evidence=evidence,operation=operation,journal=journal,commands=[],initial=snap(name+'-authored',base));cases.append(row);save()
        return base,row,state
    def ordinary(name,action='finish',**kwargs):
        base,row,state=fixture(name,**kwargs)
        row['action']=action
        for label,a in [('inspect',cli(base,'inspect')),('preview',cli(base,action,row['operation'],preview=True)),('apply',cli(base,action,row['operation']))]:
            c=command(name+'-'+label,a,base);row['commands'].append(c['label']);save()
        row['final']=snap(name+'-final',base);save();return row
    def prompted(name,edit,answer=b'y'):
        base,row,state=fixture(name);row.update(action='finish',control=edit)
        argv=list(map(str,cli(base,'finish',row['operation'],yes=False)));label=name+'-prompt';before=snap(label+'-before',base)
        pid,master=pty.fork()
        if pid==0:
            os.chdir(work);os.execve(program,argv,env)
        fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',30,120,0,0));data=bytearray();status=None;observed=False;edited=None
        marker=b'Apply this recovery plan?';deadline=time.monotonic()+30
        try:
            while time.monotonic()<deadline:
                if select.select([master],[],[],.05)[0]:
                    try:chunk=os.read(master,65536)
                    except OSError as e:
                        if e.errno!=errno.EIO:raise
                        chunk=b''
                    data.extend(chunk)
                if not observed and marker in data:
                    done,s=os.waitpid(pid,os.WNOHANG)
                    if done:status=s
                    assert not done,'Prompt must be live before edit.'
                    observed=True;target=base/'project/pack/rules.txt';journal=state/'journal.json'
                    if edit=='target':write(target,b'usr\n',0o644)
                    elif edit=='object':os.rename(target,base/'originals/approval-original');write(target,b'old\n',0o644)
                    elif edit=='journal':v=json.loads(journal.read_text());v['changes'][0]['applied']=True;write(journal,json.dumps(v).encode())
                    elif edit=='format':write(journal,json.dumps(json.loads(journal.read_text()),indent=2).encode())
                    elif edit=='candidate':write(state/row['operation']/'after-0',b'bad\n')
                    else:assert edit=='decline'
                    edited=snap(label+'-edited',base);os.write(master,answer)
                done,s=os.waitpid(pid,os.WNOHANG)
                if done:
                    status=s
                    while select.select([master],[],[],0)[0]:
                        try:chunk=os.read(master,65536)
                        except OSError as e:
                            if e.errno!=errno.EIO:raise
                            break
                        if not chunk:break
                        data.extend(chunk)
                    break
            assert status is not None,'Retain timed-out approval fixture.'
        finally:
            if status is None:
                try:os.killpg(pid,signal.SIGKILL)
                except ProcessLookupError:pass
                os.waitpid(pid,0)
            os.close(master)
        try:os.killpg(pid,0)
        except ProcessLookupError:absent=True
        else:absent=False
        assert absent and observed and edited
        c=record(label,argv,os.waitstatus_to_exitcode(status),bytes(data),b'',extra=dict(pid=pid,ownedGroupAbsent=absent,privateControllingPTY=True,mergedOutput=True,
            promptObservedLive=True,answer=answer.decode(),before=before,afterExplicitEdit=edited,after=snap(label+'-after',base)))
        row['commands']=[c['label']];row['final']=snap(name+'-final',base);save()
    helper=work/'association-identity'
    try:
        compiler=Path(r['compiler']['path']);assert sha(compiler)==r['compiler']['sha256']
        args=[compiler,'--edition=2024','-Cdebuginfo=0','-Cstrip=debuginfo',work/'main.rs','-Ldependency='+str(repo/'target/debug/deps')]
        for lib,a in r['libraries'].items():
            assert sha(Path(a['path']))==a['sha256'];args+=['--extern',lib+'='+a['path']]
        args+=['-o',helper];c=command('compile-helper',args);assert c['exitCode']==0,'Retain failed compilation.'
        receipt['helper']=dict(path=str(helper.relative_to(ROOT)),sha256=sha(helper),bytes=helper.stat().st_size);save()
        control=ordinary('finish-before')
        assert all(next(c['exitCode']for c in commands if c['label']==label)==0 for label in control['commands']),'Stop after failed positive control;inspect retained evidence.'
        assert (work/control['fixture']/'project/pack/rules.txt').read_bytes()==b'new\n'
        ordinary('restore-after',action='restore',current='after')
        ordinary('finish-restoring-before',restoring=True)
        ordinary('restore-restoring-before',action='restore',restoring=True)
        ordinary('finish-already-after',current='after',candidate='missing')
        ordinary('finish-bad-candidate',candidate='corrupt')
        ordinary('restore-bad-candidate',action='restore',current='after',candidate='corrupt')
        ordinary('restore-bad-before',action='restore',current='after',before_image='corrupt')
        ordinary('restore-noop-bad-before',action='restore',before_image='corrupt')
        ordinary('finish-foreign-target',current='foreign')
        ordinary('finish-same-byte-object',current='replacement')
        ordinary('unsupported-journal',schema=4)
        ordinary('committed-journal',committed=True,current='after')
        for name,edit in [('late-target','target'),('late-object','object'),('late-journal','journal'),('late-format','format'),('late-candidate','candidate'),('declined','decline')]:
            prompted(name,edit,b'n'if edit=='decline'else b'y')
        receipt['allOwnedGroupsRetired']=all(c.get('ownedGroupAbsent',False)for c in commands)
        receipt['allocatedKiB']=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]);save()
    finally:
        # Never kill a historical PID; Popen handles here are still-owned groups.
        for proc in active.values():retire_owned(proc)
    print(json.dumps(dict(run=str(run),cases=len(cases),commands=len(commands),allocatedKiB=receipt.get('allocatedKiB')),indent=2))


if __name__=='__main__':main()
