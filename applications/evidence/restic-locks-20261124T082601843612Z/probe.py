#!/usr/bin/env python3
"""Own a new local restic repository and its disposable interrupted processes.

Passwords, encrypted repo, and raw user/host-bearing output stay in ignored work.
Public stream copies are explicitly redacted; no existing repository is opened.
"""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import pwd
import re
import secrets
import signal
import socket
import subprocess
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def redact(raw):
    text=raw.decode('utf-8',errors='strict')
    for value,label in [(socket.gethostname(),'[fixture-host]'),(pwd.getpwuid(os.getuid()).pw_name,'[fixture-user]')]:
        assert value and value not in ['pid','time','exclusive','username','hostname']
        text=text.replace(value,label)
    text=re.sub(r'\(UID \d+, GID \d+\)','(UID [redacted], GID [redacted])',text)
    text=re.sub(r'"(uid|gid)"\s*:\s*\d+',r'"\1": null',text)
    return text.encode()


def main():
    run=ROOT/'applications/evidence'/('restic-locks-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));work=run/'work'
    for name in ['home','cache','tmp','private','source']:(work/name).mkdir(parents=True)
    (run/'probe.py').write_bytes(PRODUCER)
    password=work/'password';password.write_text(secrets.token_urlsafe(32)+'\n');password.chmod(0o600)
    executable=ROOT/'applications/tools/restic-0.20.0/restic';pin=json.loads((ROOT/'applications/sources/restic-tool.json').read_text());assert sha(executable)==pin['binarySha256']
    repo=work/'repository';env={'PATH':'/usr/bin:/bin','HOME':str(work/'home'),'TMPDIR':str(work/'tmp'),'RESTIC_CACHE_DIR':str(work/'cache'),'GOMAXPROCS':'2','LANG':'C.UTF-8'}
    prefix=[str(executable),'--repo',str(repo),'--password-file',str(password),'--json']
    rows=[];observations=[];owned=[]
    def state():
        return {'locks':sorted(p.name for p in(repo/'locks').glob('*')if p.is_file()),'snapshots':sorted(p.name for p in(repo/'snapshots').glob('*')if p.is_file())}
    def save():
        (run/'trace.json').write_text(json.dumps(rows,indent=2)+'\n');(run/'observations.json').write_text(json.dumps(observations,indent=2)+'\n')
    def finish(label,child,before,started,args,role,extra=None):
        streams={}
        for stream in ['stdout','stderr']:
            path=work/'private'/(label+'.'+stream);raw=path.read_bytes();public=redact(raw);(run/(label+'.'+stream)).write_bytes(public)
            streams[stream]={'rawSha256':hashlib.sha256(raw).hexdigest(),'publicSha256':hashlib.sha256(public).hexdigest(),'redacted':raw!=public,'rawPrivatePath':str(path.relative_to(run))}
        row={'case':label,'role':role,'argv':prefix+args,'pid':child.pid,'observed':{'before':before,'after':state(),'seconds':time.monotonic()-started,'streams':streams},'outcome':{'exitCode':child.returncode},'control':extra or {}}
        rows.append(row);save();print(json.dumps({'case':label,'exitCode':child.returncode,'locks':len(row['observed']['after']['locks']),'snapshots':len(row['observed']['after']['snapshots'])}),flush=True);return row
    def start(label,args,role):
        before=state();started=time.monotonic();out=(work/'private'/(label+'.stdout')).open('wb');err=(work/'private'/(label+'.stderr')).open('wb')
        child=subprocess.Popen(prefix+args,cwd=work,env=env,stdin=subprocess.PIPE,stdout=out,stderr=err,start_new_session=True)
        entry={'child':child,'label':label,'before':before,'started':started,'args':args,'role':role,'handles':[out,err]};owned.append(entry)
        (run/'owned-processes.json').write_text(json.dumps([{'case':e['label'],'pid':e['child'].pid,'argv':prefix+e['args']}for e in owned],indent=2)+'\n');return entry
    def reap(entry,payload=b'',extra=None):
        child=entry['child'];timed_out=False
        try:child.communicate(input=payload,timeout=30)
        except subprocess.TimeoutExpired:
            timed_out=True
            if child.poll()is None:os.killpg(child.pid,signal.SIGKILL)
            child.communicate()
        for handle in entry['handles']:handle.close()
        row=finish(entry['label'],child,entry['before'],entry['started'],entry['args'],entry['role'],dict(extra or {},timedOut=timed_out))
        if timed_out:raise RuntimeError('Owned operation exceeded deadline and was killed;preserve this failure before retry.')
        return row
    def command(label,args,role='operation',expected=0):
        row=reap(start(label,args,role))
        if expected is not None and row['outcome']['exitCode']!=expected:raise RuntimeError('Unexpected status in '+label+';inspect private/public retained evidence.')
        return row
    def held(label):
        return start(label,['backup','--stdin','--stdin-filename',label+'.txt','--host','rules-lock-fixture','--tag',label],'held-append')
    def wait_locks(count,entries):
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            if any(e['child'].poll()is not None for e in entries):raise RuntimeError('Owned holder exited before lock observation.')
            if len(state()['locks'])==count:return
            time.sleep(.01)
        raise RuntimeError('Lock observation deadline expired;do not restart live holders.')
    def lock_metadata(label,expected_pids):
        seen=[]
        for index,identity in enumerate(state()['locks']):
            row=command(label+'-'+str(index),['--no-lock','cat','lock',identity],role='diagnostic-no-lock-observer')
            raw=json.loads((work/'private'/(row['case']+'.stdout')).read_text());assert raw['pid']in expected_pids
            item={'id':identity,'pid':raw['pid'],'exclusive':raw['exclusive'],'time':raw['time'],'sameHost':raw['hostname']==socket.gethostname()};seen.append(item)
        assert {x['pid']for x in seen}==set(expected_pids)
        observations.append({'phase':label,'locks':seen,'pids':[{'pid':pid,'owned':True}for pid in expected_pids]});save();return seen
    try:
        command('init',['init'])
        source=work/'source/seed.txt';source.write_bytes(b'Private generated seed.\n')
        command('seed-backup',['backup','--host','rules-lock-fixture','--tag','seed',str(source)])
        seed_snapshots=state()['snapshots'];assert len(seed_snapshots)==1
        a=held('held-a');wait_locks(1,[a]);time.sleep(.3);assert a['child'].poll()is None
        locks_a=lock_metadata('shared-a',[a['child'].pid]);assert not locks_a[0]['exclusive']
        b=held('held-b');wait_locks(2,[a,b]);time.sleep(.3)
        shared=lock_metadata('shared-ab',[a['child'].pid,b['child'].pid]);assert all(not x['exclusive']for x in shared)
        active_ids=state()['locks'];command('unlock-live',['unlock']);assert state()['locks']==active_ids
        command('check-blocked',['check','--read-data'],expected=11)
        command('prune-blocked',['prune','--max-unused','0'],expected=11)
        command('retry-expired',['--retry-lock','1s','check','--read-data'],expected=11)
        assert a['child'].poll()is None and b['child'].poll()is None and len(state()['locks'])==2
        # Interrupt B without EOF first. If EOF is needed to finish retirement,
        # retain that distinction rather than calling it signal-only success.
        os.killpg(b['child'].pid,signal.SIGINT);needed_eof=False
        try:b['child'].wait(timeout=3)
        except subprocess.TimeoutExpired:
            needed_eof=True;b['child'].stdin.close();b['child'].stdin=None
        interrupted=reap(b,payload=None,extra={'signal':'SIGINT','neededEOFToRetire':needed_eof})
        assert a['child'].poll()is None and len(state()['locks'])==1
        retry=start('retry-after-release',['--retry-lock','2s','check','--read-data'],'waiting-exclusive')
        time.sleep(.2);assert retry['child'].poll()is None and state()['locks']==active_ids[:0]+[locks_a[0]['id']]
        completed=reap(a,payload=b'Completed held A input.\n');assert completed['outcome']['exitCode']==0
        waited=reap(retry);assert waited['outcome']['exitCode']==0 and not state()['locks']
        after_a=state()['snapshots'];added_a=sorted(set(after_a)-set(seed_snapshots));assert len(added_a)==1
        # Abrupt retirement leaves native recovery evidence, unlike SIGINT.
        c=held('held-c');wait_locks(1,[c]);time.sleep(.3);dead_lock=lock_metadata('before-kill-c',[c['child'].pid])[0]
        os.killpg(c['child'].pid,signal.SIGKILL);killed=reap(c,payload=None,extra={'signal':'SIGKILL'})
        assert killed['outcome']['exitCode']==-signal.SIGKILL and state()['locks']==[dead_lock['id']]
        command('dead-lock-check-refused',['check','--read-data'],expected=11)
        try:os.kill(c['child'].pid,0);raise RuntimeError('Former holder PID exists again;hold before native stale-lock probe.')
        except ProcessLookupError:pass
        command('unlock-dead',['unlock']);assert not state()['locks']
        command('check-after-unlock',['check','--read-data'])
        # Freeze our own exclusive candidate while it is still published. This
        # is not a claim that admission had finished at the freeze point.
        exclusive=start('exclusive-paused',['check','--read-data'],'controlled-exclusive-candidate')
        wait_locks(1,[exclusive]);os.killpg(exclusive['child'].pid,signal.SIGSTOP)
        stopped=False;deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            pid,status=os.waitpid(exclusive['child'].pid,os.WUNTRACED|os.WNOHANG)
            if pid:
                if not os.WIFSTOPPED(status):raise RuntimeError('Exclusive operation retired before the controlled stop.')
                stopped=True;break
            time.sleep(.005)
        if not stopped:raise RuntimeError('Did not establish the owned stopped state.')
        exclusive_metadata=lock_metadata('exclusive-published-stopped',[exclusive['child'].pid]);assert exclusive_metadata[0]['exclusive']
        command('append-blocked-by-exclusive',['backup','--stdin','--stdin-filename','refused.txt','--host','rules-lock-fixture'],expected=11)
        os.killpg(exclusive['child'].pid,signal.SIGCONT);done=reap(exclusive,payload=None,extra={'publishedStoppedObserved':True,'admissionAtStop':'not established','resumed':True})
        assert done['outcome']['exitCode']==0 and not state()['locks']
        dump=command('dump-completed-a',['dump',added_a[0],'held-a.txt'])
        assert (work/'private/dump-completed-a.stdout').read_bytes()==b'Completed held A input.\n'
        assert state()['snapshots']==after_a
        for e in owned:assert e['child'].poll()is not None
        receipt={'schema':1,'producerSha256':hashlib.sha256(PRODUCER).hexdigest(),'tool':pin,'platform':platform.platform(),'architecture':platform.machine(),'commands':len(rows),'seedSnapshots':seed_snapshots,'completedASnapshot':added_a[0],
            'interruptedExitCode':interrupted['outcome']['exitCode'],'interruptedNeededEOF':needed_eof,'allOwnedProcessesRetired':True,'finalLocks':state()['locks'],'finalSnapshots':state()['snapshots'],
            'redaction':'Public stream copies replace OS user/host names and UID/GID details. Original bytes stay at each rawPrivatePath;raw and public hashes are distinct. Diagnostic no-lock cat calls are observers,not coordination-qualified operations.',
            'allocatedKiB':int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),'scope':'Local generated repo,short live same-host locks,controlled stdin,SIGINT,SIGKILL and one stopped published-exclusive candidate. No age expiry,remote/backend faults,corruption/repair or arbitrary process containment proof.'}
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'run':str(run),'commands':len(rows),'interruptedExitCode':receipt['interruptedExitCode'],'neededEOF':needed_eof,'allocatedKiB':receipt['allocatedKiB']}),flush=True)
    except BaseException as error:
        (run/'failure.json').write_text(json.dumps({'error':str(error),'commands':len(rows),'producerSha256':hashlib.sha256(PRODUCER).hexdigest()},indent=2)+'\n');raise
    finally:
        # Only this collector's unreaped owned groups can be resumed/killed.
        for e in owned:
            child=e['child']
            if child.poll()is None:
                try:os.killpg(child.pid,signal.SIGCONT);os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                child.communicate()
            for handle in e['handles']:
                if not handle.closed:handle.close()


if __name__=='__main__':main()
