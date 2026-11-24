#!/usr/bin/env python3
"""Capture selected installed patch help using only private configuration."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PRODUCER=Path(__file__).read_bytes();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    tools=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']
    for name in ['node','pnpm','yarn']:assert sha(Path(tools[name]['path']))==tools[name]['sha256']
    run=ROOT/'applications/evidence'/('js-patches-help-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));work=run/'work'
    for name in ['home','tmp','config','cache','project']:(work/name).mkdir(parents=True)
    (run/'probe.py').write_bytes(PRODUCER)
    env=dict(PATH=str(Path(tools['node']['path']).parent)+':/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),
        XDG_CONFIG_HOME=str(work/'config'),XDG_CACHE_HOME=str(work/'cache'),LANG='en_US.UTF-8',
        COREPACK_ENABLE_NETWORK='0',YARN_ENABLE_TELEMETRY='0',DO_NOT_TRACK='1',MISE_SKIP_RESHIM='1')
    rows=[]
    for app,commands in [('pnpm',['patch','patch-commit','patch-remove']),('yarn',['patch','patch-commit','unplug'])]:
        prefix=[tools['pnpm']['path']] if app=='pnpm' else [tools['node']['path'],tools['yarn']['path']]
        for command in commands:
            child=subprocess.Popen(prefix+[command,'--help'],cwd=work/'project',env=env,stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
            timed_out=False
            try:out,err=child.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                timed_out=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
            stem=app+'-'+command
            for stream,data in [('stdout',out),('stderr',err)]:(run/(stem+'.'+stream)).write_bytes(data)
            rows.append(dict(app=app,command=command,argv=prefix+[command,'--help'],exitCode=child.returncode,timedOut=timed_out,
                stdoutSha256=hashlib.sha256(out).hexdigest(),stderrSha256=hashlib.sha256(err).hexdigest()))
            (run/'commands.json').write_text(json.dumps(rows,indent=2)+'\n')
            assert not timed_out,'Preserve terminal timeout before a retry.'
    receipt=dict(schema=1,producerSha256=hashlib.sha256(PRODUCER).hexdigest(),tools={n:tools[n] for n in ['node','pnpm','yarn']},
        commands=len(rows),platform=platform.platform(),allOwnedProcessesRetired=True,
        scope='Installed command help only in private HOME/config/cache/project. No package preparation,patch,install or user project.')
    (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(run=str(run),outcomes=[(r['app'],r['command'],r['exitCode']) for r in rows]),indent=2))


if __name__=='__main__':main()
