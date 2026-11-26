"""Prepare and supervise an owner-operated isolated native Prism export study.

Desktop coordination and UI actions belong to the native agent. Importing or
preparing this module does not launch an application. Never run it in CI.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
EXE=Path('/Applications/Prism Launcher.app/Contents/MacOS/prismlauncher')
EXPECTED='590fad2e7feaed261ff5f772addd0670ce2a653218023e3fb4dca5bb3b10e489'
sha=lambda b:hashlib.sha256(b).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,indent=2)+'\n')
now=lambda:datetime.now(timezone.utc).isoformat()


def image(run,root):
    result={}
    for directory,dirs,names in os.walk(root,followlinks=False):
        for name in sorted(dirs+names):
            p=Path(directory)/name;s=p.lstat();key=p.relative_to(root).as_posix()
            if stat.S_ISLNK(s.st_mode):result[key]=dict(kind='link',target=os.readlink(p))
            elif stat.S_ISDIR(s.st_mode):result[key]=dict(kind='directory',mode=stat.S_IMODE(s.st_mode))
            else:
                assert stat.S_ISREG(s.st_mode);body=p.read_bytes();digest=sha(body);target=run/'states'/(digest+'.bin')
                if not target.exists():target.write_bytes(body)
                result[key]=dict(kind='file',mode=stat.S_IMODE(s.st_mode),bytes=len(body),sha256=digest,captured=str(target.relative_to(run)))
    return result


def prepare():
    assert sha(EXE.read_bytes())==EXPECTED
    run=ROOT/'applications/evidence'/('prism-export-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir()
    for name in ['states','actions','screenshots']:(run/name).mkdir()
    (run/'probe.py').write_bytes(Path(__file__).read_bytes())
    work=Path(tempfile.mkdtemp(prefix='rules-prism-export-',dir='/private/tmp'));profile=work/'profile';instance=profile/'instances/fixture'
    instance.mkdir(parents=True);(work/'outputs').mkdir();(work/'external').mkdir()
    (work/'external/outside.txt').write_text('Generated outside-instance backing.\n')
    (profile/'prismlauncher.cfg').write_text('[General]\nLanguage=en_US\nIgnoreJavaWizard=true\nAutomaticJavaDownload=false\nAutomaticJavaSwitch=false\nUserAskedAboutAutomaticJavaDownload=true\nPastebinURL=\nSelectedInstance=fixture\n')
    (instance/'instance.cfg').write_text('[General]\nConfigVersion=1.2\nInstanceType=OneSix\nname=Rules export study Ω\niconKey=default\nExportName=Rules export study Ω\nExportVersion=1.0.0\n')
    write(instance/'mmc-pack.json',dict(formatVersion=1,components=[dict(uid='net.minecraft',version='1.21.1',important=True)]))
    files={
        'notes.txt':'Generated instance-root note.\n',
        '.hidden-root.txt':'Generated hidden root file.\n',
        '.minecraft/config/visible.txt':'Generated configuration Ω 日本.\n',
        '.minecraft/config/.hidden-file.txt':'Generated hidden regular file.\n',
        '.minecraft/config/.hidden-folder/inside.txt':'Generated ordinary file inside hidden directory.\n',
        '.minecraft/config/pack-rule.pw.toml':'Generated packing-rule sentinel.\n',
        '.minecraft/logs/latest.log':'Generated log sentinel.\n',
        '.minecraft/crash-reports/example.txt':'Generated crash sentinel.\n',
        '.minecraft/saves/Study World/README.txt':'Generated world-like content;no real world or gameplay.\n',
        '.minecraft/thumbs.db':'Generated ignored basename sentinel.\n',
    }
    for name,body in files.items():
        p=instance/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_text(body)
    (instance/'.minecraft/config/linked.txt').symlink_to(work/'external/outside.txt')
    receipt=dict(schema=1,preparedAt=now(),work=str(work),profile=str(profile),instance=str(instance),executable=str(EXE),executableSha256=EXPECTED,producerSha256=sha((run/'probe.py').read_bytes()),prepared=True,launched=False,complete=False,limits=['Generated fixture;no account/world/personal profile copied.','Desktop lease must be acquired independently before launch/UI.','No process or GUI has run during preparation.'])
    write(run/'prepared.json',receipt);write(run/'prepared-image.json',image(run,work));print(run)


def alive(pgid):
    try:os.killpg(pgid,0);return True
    except ProcessLookupError:return False


def launch(run):
    prepared=json.loads((run/'prepared.json').read_text());work=Path(prepared['work']);profile=Path(prepared['profile'])
    assert sha(EXE.read_bytes())==EXPECTED
    stdout=(run/'launcher.stdout').open('wb');stderr=(run/'launcher.stderr').open('wb')
    process=subprocess.Popen([str(EXE),'--dir',str(profile)],cwd=work,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
    events=[];write(run/'live.json',dict(pid=process.pid,argv=[str(EXE),'--dir',str(profile)],startedAt=now(),work=str(work)))
    print(json.dumps(dict(pid=process.pid,run=str(run))),flush=True)
    try:
        for line in sys.stdin:
            request=json.loads(line);label=request['label'];assert label and len(label)<100 and all(c.isalnum()or c in '-_'for c in label)
            event=dict(label=label,at=now(),exitCode=process.poll(),image=image(run,work));events.append(event);write(run/'events.json',events)
            print(json.dumps(dict(label=label,pid=process.pid,exitCode=process.poll())),flush=True)
            if request.get('finish'):
                if process.poll()is None:print('Owned launcher is still running;finish not admitted.',flush=True);continue
                break
    finally:
        teardown=False
        if process.poll()is None:
            teardown=True;process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=10)
        stdout.close();stderr.close()
        write(run/'receipt.json',dict(**{k:v for k,v in prepared.items()if k not in ['complete','launched','limits']},launched=True,complete=True,exitCode=process.returncode,forcedTeardown=teardown,groupAbsent=not alive(process.pid),finishedAt=now(),events=len(events),executableAfterSha256=sha(EXE.read_bytes()),streams={n:sha((run/n).read_bytes())for n in ['launcher.stdout','launcher.stderr']},limits=['UI actions and desktop grants recorded separately by the operator.','Profile/outputs/images retained;not a game launch or complete privacy/global-effect qualification.']))
        print(json.dumps(dict(terminal=True,exitCode=process.returncode,groupAbsent=not alive(process.pid),forcedTeardown=teardown)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','launch']);p.add_argument('--run');a=p.parse_args()
    if a.mode=='prepare':prepare()
    else:
        assert a.run;launch(Path(a.run).resolve())
