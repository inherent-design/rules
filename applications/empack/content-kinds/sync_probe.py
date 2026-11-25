"""Explicit author edit followed by inspection and sync, using the retained own fixture."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from probe import image, sha, write

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'applications/evidence/empack-content-kinds-20261125T200444932279Z'


def main():
    assert sys.argv[1:] in [[], ['--layout']]
    layout = sys.argv[1:] == ['--layout']
    basis=ROOT/'applications/evidence/empack-content-kinds-sync-20261125T200904777793Z' if layout else BASE
    prior=json.loads((basis/'receipt.json').read_text());setup=json.loads((BASE/'setup.json').read_text())
    assert prior['complete'] and prior['commands']==(3 if layout else 17) and prior['allRecordedGroupsAbsent']
    work=Path(prior['work']);project=work/'project';binary=Path(setup['binary'])
    assert work==Path('/private/tmp/rules-empack-content-kinds-karvnecw') and sha(binary)==setup['binarySha256']
    rows=json.loads((basis/'commands.json').read_text())
    assert image(project)==rows[-1]['after']
    run=ROOT/'applications/evidence'/(('empack-content-kinds-layout-' if layout else 'empack-content-kinds-sync-')+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir();shutil.copyfile(__file__,run/'sync_probe.py');shutil.copyfile(Path(__file__).with_name('probe.py'),run/'probe.py')
    write(run/'setup.json',dict(schema=1,mode='layout' if layout else 'explicit-source',basisCapture=str(basis.relative_to(ROOT)),basisCommandsSha256=sha(basis/'commands.json'),
          work=str(work),binary=str(binary),binarySha256=sha(binary),producerSha256=sha(run/'sync_probe.py'),fixtureSha256=sha(run/'probe.py'),
          environment=setup['environment'],scope='One explicit literal author edit and local inspection/sync; no new archive inputs,provider/network/build/game/global state or tool update.'))
    before=image(project);author=project/'empack.yml';text=author.read_text()
    if layout:
        assert text.count('layout: {data-pack:')==1 and '\n  unknown:' in text
        text=text.replace('layout: {data-pack:','layout: {mod: custom-mods, data-pack:')
        action='Owner changes only the automatic mod layout to custom-mods; existing explicit file bindings remain untouched.'
    else:
        assert text.count('\nbuild:\n')==1 and '\n  unknown:' not in text
        text=text.replace('\nbuild:\n','\n  unknown:\n    path: vendor/unknown.jar\n    type: mod\nbuild:\n')
        action='Owner explicitly declares existing unknown.jar as a local mod; payload and all other author files remain unchanged.'
    author.write_text(text)
    write(run/'owner-edits.json',[dict(action=action,before=before,after=image(project))])
    recorded=[]
    def command(label,args,preserve=False):
        before=image(project)
        argv=[str(binary),'--state-dir',str(work/'state'),'--cache-dir',str(work/'cache'),'--workdir',str(project),'--color','never','--yes',*args]
        start=time.monotonic();child=subprocess.Popen(argv,cwd=work,env=setup['environment'],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timed=False
        try:out,err=child.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(child.pid,signal.SIGTERM)
            try:out,err=child.communicate(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        for stream,raw in [('stdout',out),('stderr',err)]:(run/(label+'.'+stream)).write_bytes(raw)
        row=dict(id=label,argv=argv,exitCode=child.returncode,timedOut=timed,processGroupAbsent=absent,seconds=time.monotonic()-start,
                 before=before,after=image(project),streams={s:sha(run/(label+'.'+s)) for s in ['stdout','stderr']})
        recorded.append(row);write(run/'commands.json',recorded);print(label,child.returncode,flush=True)
        assert absent and not timed and child.returncode==0,(label,out[-1500:],err[-1500:])
        if preserve:assert before==row['after'],label
        return out
    complete=False
    try:
        if layout:
            command('sync-layout',['sync'])
            write(run/'after-manifest.json',json.loads(command('inspect-layout',['manifest','diff','--json'],preserve=True)))
            assert (project/'pack/custom-mods/unknown.jar').read_bytes()==(project/'vendor/unknown.jar').read_bytes()
            assert not (project/'pack/mods/unknown.jar').exists()
            assert (project/'pack/mods/module.jar').read_bytes()==(project/'vendor/module.jar').read_bytes()
        else:
            write(run/'before-manifest.json',json.loads(command('inspect-edited',['manifest','diff','--json'],preserve=True)))
            command('sync-declared-unknown',['sync'])
            write(run/'after-manifest.json',json.loads(command('inspect-synced',['manifest','diff','--json'],preserve=True)))
            assert (project/'pack/mods/unknown.jar').read_bytes()==(project/'vendor/unknown.jar').read_bytes()
        complete=True
    finally:
        matches=[s.strip() for s in subprocess.check_output(['ps','-axo','pid=,args='],text=True).splitlines() if str(work) in s]
        write(run/'receipt.json',dict(schema=1,complete=complete,commands=len(recorded),work=str(work),workPathProcessMatches=matches,
              allRecordedGroupsAbsent=all(r['processGroupAbsent'] for r in recorded),privateAllocatedKiB=int(subprocess.check_output(['/usr/bin/du','-sk',str(work)],text=True).split()[0]),
              scope='Existing direct CLI refused the unknown layout; this explicit author-source+sync path has separate acceptance policy. No gameplay, bypassed import interpretation or broad unknown-content safety claim.'))
        print(json.dumps(dict(capture=str(run.relative_to(ROOT)),complete=complete,commands=len(recorded))))


if __name__=='__main__':main()
