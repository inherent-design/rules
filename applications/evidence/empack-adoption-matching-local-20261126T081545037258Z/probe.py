"""Discriminating two-command continuation; retains the original eleven-call cohort."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'applications/evidence/empack-adoption-flow-20261126T081334217208Z'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,indent=2)+'\n')


def main():
    receipt,setup=read(BASE/'receipt.json'),read(BASE/'setup.json');assert receipt['complete']
    binary=Path(setup['binary']);assert sha(binary)==setup['binarySha256']
    helper=ROOT/setup['snapshotHelper'];assert sha(helper)==setup['snapshotHelperSha256']
    spec=importlib.util.spec_from_file_location('snapshot_only',helper);prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    work=Path(receipt['work']);project=work/'projects/local';scopes=dict(project=project,state=work/'state/local',cache=work/'cache/local')
    def image(p):
        values=prior.image(p)
        for n,v in values.items():
            if v['kind']=='file'and n.startswith(('pack/','vendor/')):
                s=(p/n).stat();v.update(inode=s.st_ino,device=s.st_dev,ctimeNs=s.st_ctime_ns)
        return values
    last=read(BASE/'commands.json')[-1];assert last['id']=='local-missing-refusal'
    initial={k:image(p)for k,p in scopes.items()};assert initial==last['after']
    run=ROOT/'applications/evidence'/('empack-adoption-matching-local-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir();(run/'probe.py').write_bytes(Path(__file__).read_bytes())
    write(run/'setup.json',dict(base=str(BASE.relative_to(ROOT)),baseReceiptSha256=sha(BASE/'receipt.json'),baseCommandsSha256=sha(BASE/'commands.json'),work=str(work),binary=str(binary),binarySha256=sha(binary),initial=initial,producerSha256=sha(run/'probe.py')))
    payload=(BASE/'payload-B.zip').read_bytes();assert hashlib.sha256(payload).hexdigest()==setup['payloads']['B']
    for n in ['vendor/observed.zip','pack/resourcepacks/observed.zip']:(project/n).write_bytes(payload)
    write(run/'mutation.json',dict(kind='author changes both local source and destination to B',before=initial,after={k:image(p)for k,p in scopes.items()},paths=['vendor/observed.zip','pack/resourcepacks/observed.zip'],sha256=hashlib.sha256(payload).hexdigest()))
    env=dict(PATH=os.environ['PATH'],LANG='en_US.UTF-8',TMPDIR=str(work/'tmp'),NO_COLOR='1',DO_NOT_TRACK='1');commands=[]
    for label,args in [('matching-new-local-preview',['adopt','observed','--dry-run']),('matching-new-local-apply',['adopt','observed'])]:
        before={k:image(p)for k,p in scopes.items()};argv=[str(binary),'--workdir',str(project),'--state-dir',str(scopes['state']),'--cache-dir',str(scopes['cache']),'--net-timeout','3','--color','never','--yes',*args]
        t=time.monotonic();p=subprocess.Popen(argv,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);write(run/'current-process.json',dict(pid=p.pid,label=label,status='running'))
        try:out,err=p.communicate(timeout=45);timed=False
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(p.pid,signal.SIGTERM)
            try:out,err=p.communicate(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate(timeout=10)
        for name,data in [('stdout',out),('stderr',err)]:(run/(label+'.'+name)).write_bytes(data)
        try:os.killpg(p.pid,0);absent=False
        except ProcessLookupError:absent=True
        after={k:image(p)for k,p in scopes.items()};row=dict(id=label,project='local',argv=argv,pid=p.pid,exitCode=p.returncode,timedOut=timed,groupAbsent=absent,seconds=time.monotonic()-t,before=before,after=after,streams={n:sha(run/(label+'.'+n))for n in ['stdout','stderr']});commands.append(row);write(run/'commands.json',commands);write(run/'current-process.json',dict(pid=p.pid,label=label,status='terminal',exitCode=p.returncode,groupAbsent=absent));print(json.dumps(dict(id=label,exitCode=p.returncode)),flush=True)
        assert p.returncode==0 and not timed and absent,'Unexpected continuation result; preserve without retry.'
        assert {k:v for k,v in before['project'].items()if k.startswith(('pack/','vendor/'))}=={k:v for k,v in after['project'].items()if k.startswith(('pack/','vendor/'))}
        if '--dry-run'in args:assert before==after
    write(run/'receipt.json',dict(schema=1,complete=True,commands=2,allGroupsAbsent=all(c['groupAbsent']for c in commands),setupSha256=sha(run/'setup.json'),producerSha256=sha(run/'probe.py'),work=str(work)))
    print(json.dumps(dict(capture=str(run),commands=2)))


if __name__=='__main__':main()
