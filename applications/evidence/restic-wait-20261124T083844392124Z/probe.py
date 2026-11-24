#!/usr/bin/env python3
"""One observed-wait continuation on a private byte copy of the completed fixture."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
from locks_probe import redact

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    source_run=ROOT/'applications/evidence/restic-locks-20261124T082746005710Z'
    source_receipt=json.loads((source_run/'receipt.json').read_text());assert source_receipt['allOwnedProcessesRetired']and not source_receipt['finalLocks']
    original=source_run/'work/repository'
    def image(root):return {p.relative_to(root).as_posix():sha(p)for p in root.rglob('*')if p.is_file()}
    original_image=image(original);assert not any(name.startswith('locks/')for name in original_image)
    run=ROOT/'applications/evidence'/('restic-wait-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));work=run/'work'
    for name in ['home','cache','tmp','private']:(work/name).mkdir(parents=True)
    shutil.copytree(original,work/'repository');shutil.copyfile(source_run/'work/password',work/'password');(work/'password').chmod(0o600)
    assert image(work/'repository')==original_image
    assert (original/'config').stat().st_ino!=(work/'repository/config').stat().st_ino
    (run/'probe.py').write_bytes(PRODUCER);(run/'helper.py').write_bytes((HERE/'locks_probe.py').read_bytes())
    tool=ROOT/'applications/tools/restic-0.20.0/restic';assert sha(tool)==source_receipt['tool']['binarySha256']
    base=[str(tool),'--repo',str(work/'repository'),'--password-file',str(work/'password')]
    env={'PATH':'/usr/bin:/bin','HOME':str(work/'home'),'TMPDIR':str(work/'tmp'),'RESTIC_CACHE_DIR':str(work/'cache'),'GOMAXPROCS':'2','LANG':'C.UTF-8'}
    entries=[];rows=[]
    def locks():return sorted(p.name for p in(work/'repository/locks').glob('*')if p.is_file()and len(p.name)==64 and all(c in'0123456789abcdef'for c in p.name))
    def start(label,args):
        out=(work/'private'/(label+'.stdout')).open('wb');err=(work/'private'/(label+'.stderr')).open('wb');before=locks();began=time.monotonic()
        child=subprocess.Popen(base+args,cwd=work,env=env,stdin=subprocess.PIPE,stdout=out,stderr=err,start_new_session=True)
        entry=dict(case=label,argv=base+args,child=child,handles=[out,err],began=began,before=before);entries.append(entry);return entry
    def finish(entry,payload=b''):
        child=entry['child'];child.communicate(input=payload,timeout=10)
        for h in entry['handles']:h.close()
        streams={}
        for stream in ['stdout','stderr']:
            path=work/'private'/(entry['case']+'.'+stream);raw=path.read_bytes();public=redact(raw);(run/(entry['case']+'.'+stream)).write_bytes(public)
            streams[stream]={'rawSha256':hashlib.sha256(raw).hexdigest(),'publicSha256':hashlib.sha256(public).hexdigest(),'redacted':raw!=public,'rawPrivatePath':str(path.relative_to(run))}
        row={'case':entry['case'],'argv':entry['argv'],'pid':child.pid,'beforeLocks':entry['before'],'afterLocks':locks(),'seconds':time.monotonic()-entry['began'],'streams':streams,'exitCode':child.returncode}
        rows.append(row);(run/'trace.json').write_text(json.dumps(rows,indent=2)+'\n');return row
    try:
        holder=start('holder',['--json','backup','--stdin','--stdin-filename','observed-wait.txt','--host','rules-lock-fixture'])
        deadline=time.monotonic()+5
        while not locks()and time.monotonic()<deadline:assert holder['child'].poll()is None;time.sleep(.01)
        assert len(locks())==1;identity=locks()[0];time.sleep(.3)
        meta=finish(start('holder-metadata',['--json','--no-lock','cat','lock',identity]));assert meta['exitCode']==0
        lock=json.loads((work/'private/holder-metadata.stdout').read_text());assert lock['pid']==holder['child'].pid and not lock['exclusive']
        (work/'private/redaction-inputs.json').write_text(json.dumps({'hostname':lock['hostname'],'username':lock['username']},indent=2)+'\n')
        # Human output is deliberate: this pinned JSON path suppresses the
        # retry message,so mere process liveness cannot establish the stage.
        waiter=start('observed-wait',['--retry-lock','3s','check','--read-data'])
        marker=b'repo already locked, waiting up to 3s for the lock'
        deadline=time.monotonic()+5;found=False
        while time.monotonic()<deadline:
            output=b''.join((work/'private'/('observed-wait.'+s)).read_bytes()for s in ['stdout','stderr'])
            if marker in output:
                assert waiter['child'].poll()is None and holder['child'].poll()is None and locks()==[identity]
                found=True;break
            if waiter['child'].poll()is not None:raise RuntimeError('Waiter retired without a live observed-wait stage.')
            time.sleep(.01)
        if not found:raise RuntimeError('Explicit retry-wait marker was not observed;do not infer the phase from liveness.')
        marker_seconds=time.monotonic()-waiter['began']
        held=finish(holder,b'After an explicit conflict/wait observation.\n');assert held['exitCode']==0
        waited=finish(waiter);assert waited['exitCode']==0 and not locks()
        assert image(original)==original_image
        receipt={'schema':1,'producerSha256':hashlib.sha256(PRODUCER).hexdigest(),'helperSha256':sha(run/'helper.py'),'sourceCapture':str(source_run.relative_to(ROOT)),
            'sourceReceiptSha256':sha(source_run/'receipt.json'),'sourceRepositoryImage':original_image,'sourceRepoUnchanged':True,'copyBytesVerified':True,'copyUsesDistinctInode':True,
            'markerObservedWhileBothLive':True,'markerSeconds':marker_seconds,'marker':'repo already locked, waiting up to 3s for the lock','heldLock':{'id':identity,'pid':lock['pid'],'exclusive':lock['exclusive']},
            'commands':len(rows),'allOwnedProcessesRetired':all(e['child'].poll()is not None for e in entries),'finalLocks':locks(),'allocatedKiB':int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),
            'scope':'One real retry-wait followed by release/success,using explicit human-output marker. Private independent byte copy,not shared backend/distributed locking. Raw user/host streams and keys stay ignored;public copies use frozen helper redaction.'}
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'run':str(run),'commands':len(rows),'markerSeconds':marker_seconds,'waitSeconds':waited['seconds'],'exitCode':waited['exitCode']}),flush=True)
    except BaseException as error:
        (run/'failure.json').write_text(json.dumps({'error':str(error),'producerSha256':hashlib.sha256(PRODUCER).hexdigest(),'commands':len(rows)},indent=2)+'\n');raise
    finally:
        for e in entries:
            child=e['child']
            if child.poll()is None:
                try:os.killpg(child.pid,signal.SIGCONT);os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                child.communicate()
            for h in e['handles']:
                if not h.closed:h.close()


if __name__=='__main__':main()
