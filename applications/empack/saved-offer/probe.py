"""Test authored saved-state mismatches through the real CLI in a FRESH root.

Reuse public signed inputs and verified public staged assets only; never read a
key, edit an original fixture, or claim crash-produced/remote corruption.
"""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[3]
PRIOR=ROOT/'applications/evidence/empack-subscribed-flow-20261125T222928929810Z'
BINARY=Path('/Users/zer0cell/.local/bin/empack')
EXPECTED='99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,x:p.write_text(json.dumps(x,indent=2)+'\n')


def image(root):
    values={}
    for directory,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            p=Path(directory)/name;s=p.lstat();rel=p.relative_to(root).as_posix()
            assert not stat.S_ISLNK(s.st_mode)
            if stat.S_ISDIR(s.st_mode):values[rel]=dict(kind='directory',mode=s.st_mode)
            else:
                assert stat.S_ISREG(s.st_mode);raw=p.read_bytes()
                v=dict(kind='file',bytes=len(raw),mode=s.st_mode,mtimeNs=s.st_mtime_ns,sha256=hashlib.sha256(raw).hexdigest())
                if p.suffix in ['.json','.txt']:v['bytesHex']=raw.hex()
                values[rel]=v
    return values


def main():
    assert sha(BINARY)==EXPECTED
    parent=json.loads((PRIOR/'setup.json').read_text());context=json.loads((PRIOR/'public-context.json').read_text())
    receipt=json.loads((PRIOR/'receipt.json').read_text());assert receipt['complete'] and receipt['allRecordedGroupsAbsent']
    source=Path(parent['work'])/'publisher/dist/releases'/parent['exports']['b']['digest']
    envelope=(PRIOR/'release-b.envelope.json').read_bytes();assert envelope==(source/'release.json').read_bytes()
    payload=bytes.fromhex(json.loads(envelope)['payload']);assert hashlib.sha256(payload).hexdigest()==parent['exports']['b']['digest']
    release=json.loads(payload);assert release['files']==parent['exports']['b']['files']
    for file in release['files']:
        p=source/file['source']['path'];assert not p.is_symlink() and sha(p)==file['sha256'] and p.stat().st_size==file['bytes']
    work=Path(tempfile.mkdtemp(prefix='rules-empack-saved-offer-',dir='/private/tmp'))
    for n in ['recipient','state','cache','tmp','signed']:(work/n).mkdir(mode=0o700)
    (work/'signed/assets').mkdir()
    (work/'signed/release.json').write_bytes(envelope)
    for file in release['files']:shutil.copyfile(source/file['source']['path'],work/'signed'/file['source']['path'])
    for n in ['channel-a.json','channel-b.json']:(work/'signed'/n).write_bytes((PRIOR/n).read_bytes())
    run=ROOT/'applications/evidence'/('empack-saved-offer-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir();(run/'probe.py').write_bytes(Path(__file__).read_bytes())
    setup=dict(schema=1,work=str(work),binary=str(BINARY),binarySha256=EXPECTED,producerSha256=sha(run/'probe.py'),
        priorCapture=str(PRIOR.relative_to(ROOT)),priorReceiptSha256=sha(PRIOR/'receipt.json'),
        publicContextSha256=sha(PRIOR/'public-context.json'),selectedRelease=parent['exports']['b']['digest'],
        signedInputs={n:sha(PRIOR/n) for n in ['channel-a.json','channel-b.json','release-b.envelope.json']},
        scope='Fresh own recipient; explicit enrollment and validB observation, consistent local preview, authored mismatched floor mutations, actual preview/apply/check and explicit valid observation repair. NOT crash/producer-generated corruption or remote attacker. Prior public staged inputs are read only; no prior recipient/key reads or prior fixture writes,HTTP,enginebuild,Java,game or public deployment.')
    write(run/'setup.json',setup)
    root=work/'recipient';env=dict(PATH=os.environ['PATH'],LANG='en_US.UTF-8',TMPDIR=str(work/'tmp'),NO_COLOR='1',DO_NOT_TRACK='1')
    base=[str(BINARY),'--state-dir',str(work/'state'),'--cache-dir',str(work/'cache'),'--workdir',str(root),'--net-timeout','10','--color','never','--yes'];rows=[]
    def command(label,args,expected=None):
        before=image(root);started=time.monotonic();child=subprocess.Popen(base+args,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timed=False;print(json.dumps(dict(start=label,pid=child.pid)),flush=True)
        try:out,err=child.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
        (run/(label+'.stdout')).write_bytes(out);(run/(label+'.stderr')).write_bytes(err)
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        row=dict(id=label,argv=base+args,pid=child.pid,exitCode=child.returncode,timedOut=timed,groupAbsent=absent,seconds=time.monotonic()-started,before=before,after=image(root),streams={n:sha(run/(label+'.'+n)) for n in ['stdout','stderr']})
        rows.append(row);write(run/'commands.json',rows);print(json.dumps(dict(finish=label,exitCode=child.returncode,seconds=row['seconds'])),flush=True)
        assert not timed and absent and (expected is None or child.returncode==expected),'Preserve unexpected result; no automatic rerun'
        assert child.returncode in [0,1]
        return row
    edits=[]
    def forensic(label,floor):
        path=root/'.empack/subscription.json';before=image(root);value=json.loads(path.read_text())
        original=dict(value);value['floor']=floor
        assert {k:v for k,v in value.items() if k!='floor'}=={k:v for k,v in original.items() if k!='floor'}
        write(path,value);after=image(root)
        edits.append(dict(id=label,before=before,after=after,authored=True,scope='Own saved floor only; root,keys,url,observed envelope unchanged. Not natural interruption evidence.'));write(run/'authored-edits.json',edits)
    try:
        pack=release['pack'];pub=context['publicKey']
        command('enroll', ['instance','subscribe','--pack',pack,'--channel','stable','https://publisher.invalid/channels/stable.json','--key',pub],0)
        command('observe-valid-b',['instance','check-updates',str(work/'signed/channel-b.json')],0)
        record=json.loads((root/'.empack/subscription.json').read_text());floorB=record['floor']
        channelA=bytes.fromhex(json.loads((PRIOR/'channel-a.json').read_text())['payload'])
        floorA={**floorB,'sequence':1,'payload':hashlib.sha256(channelA).hexdigest()}
        command('consistent-preview',['instance','update',str(work/'signed/release.json')],0)
        forensic('newer-observation-older-floor',floorA)
        preview=command('mismatched-preview',['instance','update',str(work/'signed/release.json')])
        if preview['exitCode']==0:
            apply=command('mismatched-apply',['instance','update',str(work/'signed/release.json'),'--apply'])
            if apply['exitCode']==0:
                check=command('mismatched-check',['instance','check','--json','--quiet'])
                if check['exitCode']==0:write(run/'mismatched-check.json',json.loads((run/'mismatched-check.stdout').read_text()))
        # Same sequence but wrong payload is a discriminating refusal control.
        forensic('same-sequence-wrong-payload',{**floorB,'payload':floorA['payload']})
        command('same-sequence-preview',['instance','update',str(work/'signed/release.json')])
        forensic('restore-authored-older-floor',floorA)
        command('explicit-valid-observation-repair',['instance','check-updates',str(work/'signed/channel-b.json')],0)
        command('repaired-preview',['instance','update',str(work/'signed/release.json')],0)
        write(run/'receipt.json',dict(schema=1,complete=True,commands=len(rows),authoredEdits=len(edits),allRecordedGroupsAbsent=all(r['groupAbsent'] for r in rows),setupSha256=sha(run/'setup.json'),producerSha256=sha(run/'probe.py'),allocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),scope='Actual CLI reader/preparation/publication behavior under explicitly authored forensic saved-state inputs; outcomes must be read independently. No natural corruption,HTTP,crypto implementation,patchedengine,concurrency/crash/runtime/game or prior fixture mutation qualification.'))
        print(json.dumps(dict(run=str(run),work=str(work),complete=True)),flush=True)
    except BaseException as error:
        write(run/'failure.json',dict(error=str(error),commands=len(rows),allRecordedGroupsAbsent=all(r['groupAbsent'] for r in rows)));print(json.dumps(dict(run=str(run),work=str(work),complete=False)),flush=True);raise


if __name__=='__main__':main()
