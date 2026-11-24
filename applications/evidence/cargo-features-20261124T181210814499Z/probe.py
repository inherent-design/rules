#!/usr/bin/env python3
"""Owner-run offline feature contexts with one private target directory."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import tempfile
import time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
FLAGS=['normal','build','dev','platform','extra','explicit','defaulted','sibling','default']


def main():
    pin=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']['cargo'];cargo=Path(pin['path']);bins=cargo.parent;assert sha(cargo)==pin['sha256']
    run=ROOT/'applications/evidence'/('cargo-features-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir();(run/'probe.py').write_bytes(PRODUCER)
    work=Path(tempfile.mkdtemp(prefix='rules-cargo-features-',dir='/private/tmp'));project=work/'project'
    for p in [work,*work.parents]:assert not any((p/'.cargo'/n).exists() for n in ['config','config.toml']),p
    for name in ['project','home','cargo-home','tmp']:(work/name).mkdir()
    env=dict(PATH=str(bins)+':/usr/bin:/bin',HOME=str(work/'home'),CARGO_HOME=str(work/'cargo-home'),CARGO_TARGET_DIR=str(work/'target'),RUSTC=str(bins/'rustc'),RUSTDOC=str(bins/'rustdoc'),TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8',CARGO_BUILD_JOBS='2',CARGO_INCREMENTAL='0',CARGO_NET_OFFLINE='true',CARGO_TERM_COLOR='never')
    tools={name:dict(path=str(bins/name),sha256=sha(bins/name),version=subprocess.check_output([str(bins/name),'--version','--verbose'],env=env,text=True)) for name in ['cargo','rustc']}
    assert '344c4567c634a25837e3c3476aac08af84cf9203' in tools['cargo']['version']
    host=next(line.split(': ',1)[1] for line in tools['rustc']['version'].splitlines() if line.startswith('host: '));assert 'apple-darwin' in host
    for name in ['app','flags','defaults']:(project/name/'src').mkdir(parents=True)
    (project/'flags/Cargo.toml').write_text('[package]\nname="fixture-flags"\nversion="0.1.0"\nedition="2021"\n[features]\ndefault=["defaulted"]\n'+''.join(n+'=[]\n' for n in FLAGS if n!='default'))
    (project/'flags/src/lib.rs').write_text('pub fn flags()->u16{'+ '+'.join(f'(cfg!(feature="{name}") as u16)*{1<<i}' for i,name in enumerate(FLAGS))+'}\n')
    (project/'app/Cargo.toml').write_text('''[package]
name="fixture-app"
version="0.1.0"
edition="2021"
[features]
default=["fixture-flags/extra"]
explicit=["fixture-flags/explicit"]
[dependencies]
fixture-flags={path="../flags",default-features=false,features=["normal"]}
[build-dependencies]
fixture-flags={path="../flags",default-features=false,features=["build"]}
[dev-dependencies]
fixture-flags={path="../flags",default-features=false,features=["dev"]}
[target.'cfg(windows)'.dependencies]
fixture-flags={path="../flags",default-features=false,features=["platform"]}
''')
    (project/'app/build.rs').write_text('fn main(){println!("cargo:rerun-if-changed=build.rs");println!("cargo:rustc-env=FIXTURE_BUILD_MASK={}",fixture_flags::flags());}\n')
    (project/'app/src/main.rs').write_text('fn main(){println!("FIXTURE_APP:{{\\"normal\\":{},\\"build\\":{}}}",fixture_flags::flags(),env!("FIXTURE_BUILD_MASK"));}\n#[test]\nfn report(){println!("FIXTURE_TEST:{{\\"normal\\":{},\\"build\\":{}}}",fixture_flags::flags(),env!("FIXTURE_BUILD_MASK"));}\n'.replace('\\"','\\"'))
    (project/'defaults/Cargo.toml').write_text('''[package]
name="fixture-defaults"
version="0.1.0"
edition="2021"
[features]
default=["fixture-flags/sibling"]
[dependencies]
fixture-flags={path="../flags"}
''')
    (project/'defaults/src/main.rs').write_text('fn main(){println!("FIXTURE_DEFAULTS:{}",fixture_flags::flags());}\n')
    rows=[];configurations={};binaries=[];edits=[]

    def image():
        sources={str(p.relative_to(project)):sha(p) for p in sorted(project.rglob('*')) if p.is_file() and p.name!='Cargo.lock'}
        return dict(sourceSha256=sources,lockSha256=sha(project/'Cargo.lock'),targetPresent=(work/'target').exists())

    def command(resolver,label,argv,cwd,expected=0):
        before=image();started=time.monotonic();child=subprocess.Popen(argv,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);timed_out=False
        try:out,err=child.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            timed_out=True
            try:os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            out,err=child.communicate()
        stem='r'+str(resolver)+'-'+label
        for stream,data in [('stdout',out),('stderr',err)]:(run/(stem+'.'+stream)).write_bytes(data)
        row=dict(resolver=resolver,case=label,argv=argv,cwd=str(cwd),observed=dict(before=before,after=image(),stdoutSha256=hashlib.sha256(out).hexdigest(),stderrSha256=hashlib.sha256(err).hexdigest(),seconds=time.monotonic()-started),outcome=dict(exitCode=child.returncode,timedOut=timed_out));rows.append(row)
        (run/'trace.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(dict(resolver=resolver,case=label,exitCode=child.returncode)),flush=True)
        assert not timed_out and child.returncode==expected,'Retain failed source/command before changing the fixture.'
        return out

    def build_and_run(resolver,label,args,test=False):
        raw=command(resolver,label,[str(cargo),*args,'--offline','--message-format=json'],project/'app')
        records=[json.loads(line) for line in raw.splitlines()];artifacts=[r for r in records if r.get('reason')=='compiler-artifact' and r['target']['name']=='fixture-app' and r.get('executable')]
        assert len(artifacts)==1 and bool(artifacts[0]['profile']['test'])==test
        executable=Path(artifacts[0]['executable']);assert executable.resolve().is_relative_to(work/'target')
        binaries.append(dict(resolver=resolver,case=label,path=str(executable),sha256=sha(executable),bytes=executable.stat().st_size,artifact=artifacts[0]))
        (run/'binaries.json').write_text(json.dumps(binaries,indent=2)+'\n')
        command(resolver,label+'-runtime',[str(executable)]+(['--nocapture'] if test else []),project/'app')

    try:
        for resolver in [1,2,3]:
            manifest=project/'Cargo.toml';before=sha(manifest);manifest.write_text('[workspace]\nmembers=["app","flags","defaults"]\ndefault-members=["app"]\nresolver="'+str(resolver)+'"\n[profile.dev]\ndebug=0\n[profile.test]\ndebug=0\n');edits.append(dict(resolver=resolver,action='select-explicit-resolver',beforeSha256=before,afterSha256=sha(manifest)))
            configurations[str(resolver)]={str(p.relative_to(project)):p.read_text() for p in sorted(project.rglob('*')) if p.is_file() and p.name!='Cargo.lock'};(run/'configuration.json').write_text(json.dumps(configurations,indent=2)+'\n')
            for label,extra in [('metadata-all',[]),('metadata-host',['--filter-platform',host]),('metadata-windows',['--filter-platform','x86_64-pc-windows-msvc'])]:command(resolver,label,[str(cargo),'metadata','--offline','--format-version=1',*extra],project/'app')
            for label,args in [('default',['build','-p','fixture-app']),('no-default',['build','-p','fixture-app','--no-default-features']),('explicit',['build','-p','fixture-app','--no-default-features','--features','fixture-app/explicit']),('all-features',['build','-p','fixture-app','--all-features']),('workspace-no-default',['build','--workspace','--no-default-features'])]:build_and_run(resolver,label,args)
            build_and_run(resolver,'tests-no-default',['test','-p','fixture-app','--no-default-features','--no-run'],test=True)
        peak=int(subprocess.check_output(['du','-sk',str(work/'target')],text=True).split()[0]);command(3,'clean',[str(cargo),'clean','--offline'],project)
        assert not (work/'target').exists();assert all(sha(Path(v['path']))==v['sha256'] for v in tools.values())
        receipt=dict(schema=1,producerSha256=hashlib.sha256(PRODUCER).hexdigest(),tools=tools,host=host,platform=platform.platform(),environment=env,originalWork=str(work),commands=len(rows),profiles=3,ownerEdits=edits,flags=FLAGS,peakTargetAllocatedKiB=peak,targetCleaned=True,allOwnedCommandsReaped=True,scope='Three generated path-only workspace packages;resolver1/2/3,same native Mac host,target-filtered metadata,selected build/test contexts. Metadata for Windows is not Windows compilation. No registry,external scripts,user project,full resolver/MSRV/cross-platform/fingerprint qualification.')
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');shutil.move(str(work),run/'work');print(json.dumps(dict(run=str(run),commands=len(rows),peakTargetAllocatedKiB=peak),indent=2))
    except BaseException as error:
        (run/'failure.json').write_text(json.dumps(dict(error=str(error),originalWork=str(work),commands=len(rows)),indent=2)+'\n');raise


if __name__=='__main__':main()
