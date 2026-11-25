#!/usr/bin/env python3
"""Record two display-only probes of the pinned native engine, separately."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
ENGINE=Path('/Users/zer0cell/.local/bin/empack')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    run=Path(sys.argv[1]).resolve();assert run.parent==ROOT/'applications/evidence'
    assert sha(ENGINE)=='99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
    with (run/'native-identity-started.json').open('x')as f:json.dump(dict(producerSha256=sha(Path(__file__))),f)
    (run/'identity-probe.py').write_bytes(Path(__file__).read_bytes())
    env=dict(PATH='/usr/bin:/bin',HOME=str(run/'work/cases/native-check-25/home'),LANG='en_US.UTF-8')
    results=[]
    for name,arg in [('version','--version'),('protocol','--bootstrap-protocol')]:
        child=subprocess.Popen([str(ENGINE),arg],cwd=run/'work',env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        try:out,err=child.communicate(timeout=10)
        finally:
            if child.poll()is None:os.killpg(child.pid,9);child.wait()
        try:os.killpg(child.pid,0)
        except ProcessLookupError:absent=True
        else:absent=False
        assert absent and child.returncode==0
        for stream,data in [('stdout',out),('stderr',err)]:
            with (run/('native-identity-'+name+'.'+stream)).open('xb')as f:f.write(data)
        results.append(dict(argument=arg,exitCode=child.returncode,ownedGroupAbsent=absent,
            stdoutSha256=hashlib.sha256(out).hexdigest(),stderrSha256=hashlib.sha256(err).hexdigest()))
    (run/'native-identity.json').write_text(json.dumps(dict(schema=1,commands=results),indent=2)+'\n')
    print(json.dumps(dict(displayProbes=2,allOwnedGroupsRetired=True)))
if __name__=='__main__':main()
