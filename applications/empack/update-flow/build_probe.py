"""Build two snapshot Prism delivery modes from the guarded updated fixture."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import zipfile
from probe import image,sha,write,BINARY,EXPECTED,ROOT


def main():
    prior=ROOT/'applications/evidence/empack-update-materialize-20261125T213701918141Z'
    previous=json.loads((prior/'commands.json').read_text());setup=json.loads((prior/'setup.json').read_text());receipt=json.loads((prior/'receipt.json').read_text())
    assert receipt['complete'] and receipt['commands']==5 and receipt['allRecordedGroupsAbsent'] and sha(BINARY)==EXPECTED
    assert sha(Path(__file__).with_name('probe.py'))==setup['helperSha256']
    work=Path(setup['work']);assert str(work).startswith('/private/tmp/rules-empack-update-flow-')
    project=work/'project';assert image(project)==previous[-1]['after']
    run=ROOT/'applications/evidence'/('empack-update-build-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir()
    (run/'build_probe.py').write_bytes(Path(__file__).read_bytes());(run/'probe.py').write_bytes(Path(__file__).with_name('probe.py').read_bytes())
    retained=work/'retained-artifacts';retained.mkdir(mode=0o700)
    write(run/'setup.json',dict(schema=1,basisCapture=str(prior.relative_to(ROOT)),basisCommandsSha256=sha(prior/'commands.json'),basisReceiptSha256=sha(prior/'receipt.json'),work=str(work),producerSha256=sha(run/'build_probe.py'),helperSha256=sha(run/'probe.py'),binarySha256=EXPECTED,scope='Two own snapshot Prism archives, bundled versus references, from the exact materialized parent. No launcher import,Java/game,server,channel,GitHub mutation or engine compilation.'))
    env=dict(PATH=os.environ['PATH'],LANG='en_US.UTF-8',TMPDIR=str(work/'tmp'),NO_COLOR='1',DO_NOT_TRACK='1')
    base=[str(BINARY),'--state-dir',str(work/'state'),'--cache-dir',str(work/'cache'),'--workdir',str(project),'--net-timeout','45','--color','never','--yes']
    rows=[];artifacts=[]
    def command(label,args):
        before=image(project);began=time.monotonic();child=subprocess.Popen(base+args,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timed=False;print(json.dumps(dict(start=label,pid=child.pid)),flush=True)
        try:out,err=child.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
        (run/(label+'.stdout')).write_bytes(out);(run/(label+'.stderr')).write_bytes(err)
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        after=image(project);rows.append(dict(id=label,argv=base+args,pid=child.pid,exitCode=child.returncode,timedOut=timed,groupAbsent=absent,seconds=time.monotonic()-began,before=before,after=after,streams={n:sha(run/(label+'.'+n)) for n in ['stdout','stderr']}));write(run/'commands.json',rows)
        print(json.dumps(dict(finish=label,exitCode=child.returncode,seconds=rows[-1]['seconds'])),flush=True)
        assert not timed and absent and child.returncode==0
        for n in ['empack.yml','empack.lock']:assert before[n]==after[n]
        changed=[p for p,r in after.items() if r['kind']=='file' and p.startswith('dist/') and p.endswith('.zip') and before.get(p)!=r]
        assert len(changed)==1
        path=project/changed[0];raw=path.read_bytes();assert len(raw)<100_000_000
        copy=retained/(label+'-'+path.name);copy.write_bytes(raw)
        entries=[]
        with zipfile.ZipFile(copy) as archive:
            infos=archive.infolist();assert sum(i.file_size for i in infos)<100_000_000
            assert len({i.filename for i in infos})==len(infos)
            for info in infos:
                data=archive.read(info)
                row=dict(path=info.filename,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),sha512=hashlib.sha512(data).hexdigest())
                if len(data)<32768 and info.filename.endswith(('.json','.cfg','.txt','.sh','.bat','.ps1')):
                    try:row['text']=data.decode('utf-8')
                    except UnicodeDecodeError:pass
                entries.append(row)
        artifacts.append(dict(command=label,path=changed[0],retained=str(copy),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),entries=entries));write(run/'artifacts.json',artifacts)
    try:
        command('prism-bundled',['build','--profile','client'])
        command('prism-references',['build','--ad-hoc','prism','--environment','client','--delivery','references','--updates','snapshot'])
        assert sha(BINARY)==EXPECTED
        write(run/'receipt.json',dict(schema=1,complete=True,commands=len(rows),artifacts=len(artifacts),allRecordedGroupsAbsent=all(r['groupAbsent'] for r in rows),producerSha256=sha(run/'build_probe.py'),helperSha256=sha(run/'probe.py'),setupSha256=sha(run/'setup.json'),artifactsSha256=sha(run/'artifacts.json'),allocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),scope='Native generation and byte inventory of two snapshot archives only; no Prism import,startup,instance update,channel or gameplay qualification. Private artifact copies retained before any later output changes.'))
        print(json.dumps(dict(run=str(run),complete=True,artifacts=len(artifacts))),flush=True)
    except BaseException as error:
        write(run/'failure.json',dict(error=str(error),commands=len(rows),allRecordedGroupsAbsent=all(r['groupAbsent'] for r in rows)));print(json.dumps(dict(run=str(run),complete=False)),flush=True);raise


if __name__=='__main__':main()
