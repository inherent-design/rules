"""Exercise the generated snapshot's native prepare command in an owned recipient."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import signal
import stat
import subprocess
import time
import zipfile
from probe import image,sha,write,BINARY,EXPECTED,ROOT


def main():
    prior=ROOT/'applications/evidence/empack-update-build-20261125T214901703343Z'
    receipt=json.loads((prior/'receipt.json').read_text());setup=json.loads((prior/'setup.json').read_text());artifacts=json.loads((prior/'artifacts.json').read_text())
    assert receipt['complete'] and receipt['artifacts']==2 and receipt['allRecordedGroupsAbsent'] and sha(BINARY)==EXPECTED
    assert sha(Path(__file__).with_name('probe.py'))==setup['helperSha256']
    artifact=next(a for a in artifacts if a['command']=='prism-references');archive=Path(artifact['retained']);assert sha(archive)==artifact['sha256']
    work=Path(setup['work']);assert str(work).startswith('/private/tmp/rules-empack-update-flow-')
    recipient=work/'recipient';recipient.mkdir(mode=0o700)
    entries={e['path']:e for e in artifact['entries']}
    with zipfile.ZipFile(archive) as z:
        assert {i.filename for i in z.infolist()}==set(entries) and len(z.infolist())==len(entries)
        assert sum(i.file_size for i in z.infolist())<10_000_000
        for info in z.infolist():
            rel=PurePosixPath(info.filename)
            assert not rel.is_absolute() and '..' not in rel.parts and '\\' not in info.filename and '\0' not in info.filename
            assert not stat.S_ISLNK(info.external_attr>>16)
            p=recipient.joinpath(*rel.parts)
            if info.is_dir():p.mkdir(parents=True,exist_ok=True)
            else:
                p.parent.mkdir(parents=True,exist_ok=True)
                data=z.read(info);assert hashlib.sha256(data).hexdigest()==entries[info.filename]['sha256']
                with p.open('xb') as out:out.write(data)
    rel='.minecraft/.empack-consumer/release.json';digest=sha(recipient/rel)
    prepare=json.loads((recipient/'.empack-tools/prepare.json').read_text())
    approved=['--workdir','.','--yes','instance','ensure',rel,'--sha256',digest,'--layout','prism','--side','client']
    assert prepare==dict(schema='empack-bootstrap-invocation/1',engine_version='0.8.8-beta',append_arguments=False,arguments=approved)
    # A fixture-owned unowned setting, not a personal or manifest-managed seed.
    option=b'resourcePacks:[]\n';(recipient/'.minecraft/options.txt').write_bytes(option)
    state=work/'recipient-state';state.mkdir(mode=0o700)
    run=ROOT/'applications/evidence'/('empack-update-recipient-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir()
    (run/'instance_probe.py').write_bytes(Path(__file__).read_bytes());(run/'probe.py').write_bytes(Path(__file__).with_name('probe.py').read_bytes())
    write(run/'setup.json',dict(schema=1,basisCapture=str(prior.relative_to(ROOT)),basisArtifactsSha256=sha(prior/'artifacts.json'),work=str(work),recipient=str(recipient),producerSha256=sha(run/'instance_probe.py'),helperSha256=sha(run/'probe.py'),binarySha256=EXPECTED,sourceArchiveSha256=artifact['sha256'],releaseSha256=digest,approvedArguments=approved,unownedSetting={'path':'.minecraft/options.txt','bytesHex':option.hex()},initialImage=image(recipient),scope='Strictly reviewed own snapshot entries and exact generated native instance ensure arguments; no JAR execution,Prism GUI,Java/game,personal instances,subscription or remote publication. Native context state is separate from the author root.'))
    env=dict(PATH=os.environ['PATH'],LANG='en_US.UTF-8',TMPDIR=str(work/'tmp'),NO_COLOR='1',DO_NOT_TRACK='1')
    base=[str(BINARY),'--state-dir',str(state),'--cache-dir',str(work/'cache'),'--net-timeout','45','--color','never']
    rows=[]
    def command(label,args):
        before=image(recipient);began=time.monotonic();child=subprocess.Popen(base+args,cwd=recipient,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timed=False;print(json.dumps(dict(start=label,pid=child.pid)),flush=True)
        try:out,err=child.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
        (run/(label+'.stdout')).write_bytes(out);(run/(label+'.stderr')).write_bytes(err)
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        after=image(recipient);rows.append(dict(id=label,argv=base+args,pid=child.pid,exitCode=child.returncode,timedOut=timed,groupAbsent=absent,seconds=time.monotonic()-began,before=before,after=after,streams={n:sha(run/(label+'.'+n)) for n in ['stdout','stderr']}));write(run/'commands.json',rows)
        print(json.dumps(dict(finish=label,exitCode=child.returncode,seconds=rows[-1]['seconds'])),flush=True)
        assert not timed and absent and child.returncode==0
        assert (recipient/'.minecraft/options.txt').read_bytes()==option
        return out
    try:
        command('ensure-first',approved)
        command('ensure-repeat',approved)
        out=command('check-recipient',['--workdir','.','--yes','instance','check','--json','--quiet']);write(run/'check-recipient.json',json.loads(out))
        assert sha(BINARY)==EXPECTED
        write(run/'receipt.json',dict(schema=1,complete=True,commands=len(rows),allRecordedGroupsAbsent=all(r['groupAbsent'] for r in rows),producerSha256=sha(run/'instance_probe.py'),helperSha256=sha(run/'probe.py'),setupSha256=sha(run/'setup.json'),allocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),scope='Three native recipient commands, preserving unowned fixture settings. Native installed state/bytes need independent readback; no bootstrap JAR/Prism/runtime/game,subscription,update channel or broad conflict/recovery qualification.'))
        print(json.dumps(dict(run=str(run),complete=True)),flush=True)
    except BaseException as error:
        write(run/'failure.json',dict(error=str(error),commands=len(rows),allRecordedGroupsAbsent=all(r['groupAbsent'] for r in rows)));print(json.dumps(dict(run=str(run),complete=False)),flush=True);raise


if __name__=='__main__':main()
