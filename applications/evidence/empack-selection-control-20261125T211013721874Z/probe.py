"""Reuse the pinned core library for value-only policy/update observations."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
REVISION='0b4462e3032b4f09230b15329722eabefb7f574c'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert sys.argv[1:] in [[],['--same-pin-control']]
    control=bool(sys.argv[1:])
    repo=ROOT.parent/'empack'
    assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==REVISION
    prior=ROOT/'applications/evidence/empack-projection-20261124T063515339963Z'
    provenance=json.loads((prior/'receipt.json').read_text())
    library=prior/'work/libempack_core.rlib'
    assert provenance['revision']==REVISION and sha(library)==provenance['librarySha256']
    for name,digest in provenance['sourceSha256'].items():
        raw=subprocess.check_output(['git','-C',str(repo),'show',REVISION+':'+name])
        assert hashlib.sha256(raw).hexdigest()==digest==sha(repo/name)
    rustc=Path(provenance['tool']['path']);assert sha(rustc)==provenance['tool']['sha256']
    fixture=ROOT/'applications/empack/removal_oracle.rs'
    fixture_raw=fixture.read_bytes()
    assert fixture_raw==subprocess.check_output(['git','show','b037859887335d6c173ed04ebef2aeafe8e36324:applications/empack/removal_oracle.rs'])
    wrappers=b'''\npub fn base() -> (ProjectIntent, ResolutionLock) { fixture() }
pub fn key_of(s:&str) -> DependencyKey { key(s) }
pub fn version_of(n:u8) -> PinSelector { version(n) }
pub fn root_of(n:u8) -> DependencyIntent { root(n) }
pub fn dependency_of(n:u8,v:u8) -> LockedDependency { dependency(n,v) }
'''
    run=ROOT/'applications/evidence'/('empack-selection-'+('control-' if control else '')+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work=run/'work';work.mkdir(parents=True)
    (run/'probe.py').write_bytes(Path(__file__).read_bytes())
    (run/'oracle.rs').write_bytes((HERE/'oracle.rs').read_bytes())
    (run/'fixture-source.rs').write_bytes(fixture_raw)
    (run/'fixture-wrappers.rs').write_bytes(wrappers)
    (work/'fixture.rs').write_bytes(fixture_raw+wrappers)
    (work/'driver.rs').write_bytes((HERE/'oracle.rs').read_bytes())
    rows=[]
    env={'PATH':str(rustc.parent)+':/usr/bin:/bin','LANG':'en_US.UTF-8','TMPDIR':str(work)}
    # No global HOME replacement, package manager, daemon or user project is involved.
    def command(label,args):
        began=time.monotonic();child=subprocess.Popen(args,cwd=work,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timed=False
        try:out,err=child.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
        (run/(label+'.stdout')).write_bytes(out);(run/(label+'.stderr')).write_bytes(err)
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        rows.append(dict(label=label,argv=args,pid=child.pid,exitCode=child.returncode,timedOut=timed,groupAbsent=absent,seconds=time.monotonic()-began,stdoutSha256=sha(run/(label+'.stdout')),stderrSha256=sha(run/(label+'.stderr'))))
        (run/'commands.json').write_text(json.dumps(rows,indent=2)+'\n')
        assert child.returncode==0 and not timed and absent,'Retain failure; do not restart on observation loss.'
        return out
    try:
        binary=work/'selection-driver'
        command('compile',[str(rustc),'--edition=2024','-Awarnings',str(work/'driver.rs'),'--extern','empack_core='+str(library),'-o',str(binary)])
        raw=command('observed',[str(binary)]+(['--same-pin-control'] if control else []))
        cases=[json.loads(line) for line in raw.decode().splitlines()]
        assert len(cases)==len({r['case'] for r in cases})==(1 if control else 19)
        assert sha(library)==provenance['librarySha256']
        for name,digest in provenance['sourceSha256'].items():assert sha(repo/name)==digest
        receipt=dict(schema=1,revision=REVISION,priorCapture=str(prior.relative_to(ROOT)),priorReceiptSha256=sha(prior/'receipt.json'),librarySha256=sha(library),compiler=provenance['tool'],sourceSha256=provenance['sourceSha256'],producerSha256=sha(run/'probe.py'),driverSha256=sha(run/'oracle.rs'),fixtureSha256=sha(run/'fixture-source.rs'),wrappersSha256=sha(run/'fixture-wrappers.rs'),generatedFixtureSha256=sha(work/'fixture.rs'),binarySha256=sha(binary),observedSha256=sha(run/'observed.stdout'),platform=platform.platform(),cases=len(cases),allRecordedGroupsAbsent=all(r['groupAbsent'] for r in rows),allocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),scope='Actual unchanged core release-policy and prepare_update_with_pins calls over the earlier fictional fixture plus appended access wrappers. No provider catalog, source metadata interpretation, codec, CLI, native writer, authorization, runtime/game, or full workflow execution. Original fixture main is included as an unused module function, not invoked.')
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps(dict(run=str(run),cases=len(cases),allocatedKiB=receipt['allocatedKiB']),indent=2))
    except BaseException as error:
        (run/'failure.json').write_text(json.dumps(dict(error=str(error),commands=len(rows)))+'\n');raise


if __name__=='__main__':main()
