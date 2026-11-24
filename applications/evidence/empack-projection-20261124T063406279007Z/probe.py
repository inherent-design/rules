#!/usr/bin/env python3
"""Compile unchanged dependency-free core and a small pure projection driver."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = Path(__file__).read_bytes()
REVISION = '0b4462e3032b4f09230b15329722eabefb7f574c'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    repo = ROOT.parent / 'empack'
    assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip() == REVISION
    run = ROOT / 'applications/evidence' / ('empack-projection-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir(); (run / 'probe.py').write_bytes(PRODUCER)
    driver = HERE / 'projection_oracle.rs'; (run / 'driver.rs').write_bytes(driver.read_bytes())
    work = run / 'work'; source = work / 'core'; source.mkdir(parents=True)
    paths = subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only',REVISION,'crates/empack-core/src'],text=True).splitlines()
    copied = {}
    for path in paths:
        data = subprocess.check_output(['git','-C',str(repo),'show',REVISION+':'+path])
        assert (repo / path).read_bytes() == data, path
        dst = source / Path(path).relative_to('crates/empack-core/src'); dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data)
        copied[path] = hashlib.sha256(data).hexdigest()
    rustc = Path('/Users/zer0cell/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
    for name in ['home','tmp']:(work/name).mkdir()
    env={'PATH':str(rustc.parent)+':/usr/bin:/bin','HOME':str(work/'home'),'TMPDIR':str(work/'tmp'),'LANG':'en_US.UTF-8'}
    tool={'path':str(rustc),'sha256':sha(rustc),'version':subprocess.check_output([str(rustc),'--version','--verbose'],env=env,text=True)}
    rows=[]
    def command(label,argv):
        began=time.monotonic();result=subprocess.run(argv,cwd=work,env=env,stdin=subprocess.DEVNULL,capture_output=True,timeout=90)
        (run/(label+'.stdout')).write_bytes(result.stdout);(run/(label+'.stderr')).write_bytes(result.stderr)
        rows.append({'label':label,'argv':argv,'seconds':time.monotonic()-began,'exitCode':result.returncode,'stdoutSha256':hashlib.sha256(result.stdout).hexdigest(),'stderrSha256':hashlib.sha256(result.stderr).hexdigest()})
        (run/'commands.json').write_text(json.dumps(rows,indent=2)+'\n')
        assert result.returncode==0,(label,result.stderr.decode(errors='replace'))
        return result.stdout
    library=work/'libempack_core.rlib';binary=work/'projection-driver'
    command('compile-core',[str(rustc),'--edition=2024','--crate-name','empack_core','--crate-type','rlib',str(source/'lib.rs'),'-o',str(library)])
    command('compile-driver',[str(rustc),'--edition=2024',str(run/'driver.rs'),'--extern','empack_core='+str(library),'-o',str(binary)])
    output=command('observed',[str(binary)])
    lines=output.decode().splitlines();assert len(lines)==32 and len({line.split('\t')[0]for line in lines})==32
    for path,h in copied.items():assert sha(repo/path)==h and sha(source/Path(path).relative_to('crates/empack-core/src'))==h
    assert sha(driver)==sha(run/'driver.rs')
    receipt={'schema':1,'revision':REVISION,'platform':platform.platform(),'architecture':platform.machine(),'tool':tool,'cases':len(lines),'sourceSha256':copied,'producerSha256':hashlib.sha256(PRODUCER).hexdigest(),'driverSha256':sha(run/'driver.rs'),'librarySha256':sha(library),'binarySha256':sha(binary),'observedSha256':hashlib.sha256(output).hexdigest(),
        'scope':'Actual unchanged pure core APIs and fictional content labels; no installed CLI, source capture, byte acquisition, filesystem publication, browser, consumer launch or real content verification.',
        'limits':['Source matches checked-out Git revision; installed0.8.8 binary correspondence is not proved.','Hand-selected valid portable destinations and supported recipes; not generic path/codec/provider/template or full core qualification.','Embedded/download labels are constructed test values; successful planning does not authenticate bytes or mint host execution authority.']}
    (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'run':str(run),'cases':len(lines),'sourceFiles':len(copied),'nativeCoreOnly':True},indent=2))


if __name__=='__main__':main()
