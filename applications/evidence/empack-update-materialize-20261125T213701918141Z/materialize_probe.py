"""Continue the exact disposable update fixture through verification/materialization."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from probe import image,sha,write,BINARY,EXPECTED,ROOT


def main():
    base_run=ROOT/'applications/evidence/empack-update-flow-20261125T213429298820Z'
    prior=json.loads((base_run/'receipt.json').read_text());setup=json.loads((base_run/'setup.json').read_text());previous=json.loads((base_run/'commands.json').read_text())
    assert prior['complete'] and prior['commands']==10 and prior['allRecordedGroupsAbsent']
    assert sha(BINARY)==EXPECTED and sha(Path(__file__).with_name('probe.py'))==setup['producerSha256']
    work=Path(setup['work']);assert str(work).startswith('/private/tmp/rules-empack-update-flow-')
    project=work/'project';assert image(project)==previous[-1]['after']
    run=ROOT/'applications/evidence'/('empack-update-materialize-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir();(run/'materialize_probe.py').write_bytes(Path(__file__).read_bytes());(run/'probe.py').write_bytes(Path(__file__).with_name('probe.py').read_bytes())
    write(run/'setup.json',dict(schema=1,basisCapture=str(base_run.relative_to(ROOT)),basisCommandsSha256=sha(base_run/'commands.json'),basisReceiptSha256=sha(base_run/'receipt.json'),work=str(work),producerSha256=sha(run/'materialize_probe.py'),helperSha256=sha(run/'probe.py'),binarySha256=EXPECTED,scope='Same owned fixture with exact prior postimage guard; default/local check is plain check, not a --local flag. No game/build/runtime or personal project.'))
    env=dict(PATH=os.environ['PATH'],LANG='en_US.UTF-8',TMPDIR=str(work/'tmp'),NO_COLOR='1',DO_NOT_TRACK='1')
    base=[str(BINARY),'--state-dir',str(work/'state'),'--cache-dir',str(work/'cache'),'--workdir',str(project),'--net-timeout','45','--color','never','--yes']
    rows=[]
    def command(label,args,read_only=False,structured=False,checks=False):
        before=image(project);began=time.monotonic();child=subprocess.Popen(base+args,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timed=False;print(json.dumps(dict(start=label,pid=child.pid)),flush=True)
        try:out,err=child.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
        (run/(label+'.stdout')).write_bytes(out);(run/(label+'.stderr')).write_bytes(err)
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        after=image(project);rows.append(dict(id=label,argv=base+args,pid=child.pid,exitCode=child.returncode,timedOut=timed,groupAbsent=absent,seconds=time.monotonic()-began,before=before,after=after,streams={name:sha(run/(label+'.'+name)) for name in ['stdout','stderr']}));write(run/'commands.json',rows)
        print(json.dumps(dict(finish=label,exitCode=child.returncode,seconds=rows[-1]['seconds'])),flush=True)
        assert not timed and absent and child.returncode in ([0,1] if checks else [0])
        if read_only:assert before==after
        if structured:write(run/(label+'.json'),json.loads(out))
    try:
        command('check-reference',['check','--json','--quiet'],True,True,True)
        command('materialize',['sync','--materialize'])
        command('check-local-materialized',['check','--json','--quiet'],True,True,True)
        command('check-online-materialized',['check','--online','--json','--quiet'],True,True,True)
        command('inspect-materialized',['manifest','diff','--json'],True,True)
        assert sha(BINARY)==EXPECTED
        write(run/'receipt.json',dict(schema=1,complete=True,commands=len(rows),allRecordedGroupsAbsent=all(r['groupAbsent'] for r in rows),producerSha256=sha(run/'materialize_probe.py'),helperSha256=sha(run/'probe.py'),setupSha256=sha(run/'setup.json'),allocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),scope='Five real CLI commands after guarded prior update. Local and online check exits recorded as observations, not assumed success. No consumer/game/runtime execution.'))
        print(json.dumps(dict(run=str(run),complete=True)),flush=True)
    except BaseException as error:
        write(run/'failure.json',dict(error=str(error),commands=len(rows),allRecordedGroupsAbsent=all(r['groupAbsent'] for r in rows)));print(json.dumps(dict(run=str(run),complete=False)),flush=True);raise


if __name__=='__main__':main()
