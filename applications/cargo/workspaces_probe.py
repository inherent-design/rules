#!/usr/bin/env python3
"""Small offline Cargo default-member/selection checks; no registry or user project."""
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

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()if p.is_file()else None


def main():
    pin=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']['cargo'];cargo=Path(pin['path']);bins=cargo.parent
    assert sha(cargo)==pin['sha256']
    run=ROOT/'applications/evidence'/('cargo-workspaces-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir();(run/'probe.py').write_bytes(PRODUCER)
    work=Path(tempfile.mkdtemp(prefix='rules-cargo-workspaces-',dir='/private/tmp'))
    for parent in [work,*work.parents]:assert not any((parent/'.cargo'/name).exists()for name in ['config','config.toml']),parent
    rows=[];configurations={};environments={};tool_versions={}
    try:
        for profile,root_package,explicit_a in [('root-default',True,False),('virtual-default',False,False),('virtual-a',False,True),('root-a',True,True)]:
            base=work/profile;project=base/'project'
            for p in [project,base/'home',base/'cargo-home',base/'tmp']:p.mkdir(parents=True)
            env={'PATH':str(bins)+':/usr/bin:/bin','HOME':str(base/'home'),'CARGO_HOME':str(base/'cargo-home'),'CARGO_TARGET_DIR':str(base/'target'),'RUSTC':str(bins/'rustc'),'RUSTDOC':str(bins/'rustdoc'),'TMPDIR':str(base/'tmp'),'LANG':'en_US.UTF-8','CARGO_BUILD_JOBS':'2','CARGO_INCREMENTAL':'0','CARGO_NET_OFFLINE':'true','CARGO_TERM_COLOR':'never'}
            environments[profile]=env
            if not tool_versions:
                for name in ['cargo','rustc']:tool_versions[name]={'sha256':sha(bins/name),'version':subprocess.check_output([str(bins/name),'--version','--verbose'],env=env,text=True)}
                assert '344c4567c634a25837e3c3476aac08af84cf9203'in tool_versions['cargo']['version']
            manifest='[package]\nname="fixture-root"\nversion="0.1.0"\nedition="2021"\n'if root_package else''
            manifest+='[workspace]\nmembers=["a","b"]\nresolver="2"\n'+('default-members=["a"]\n'if explicit_a else'')
            (project/'Cargo.toml').write_text(manifest)
            if root_package:
                (project/'src').mkdir();(project/'src/main.rs').write_text('fn main(){println!("root");}\n')
            for name in ['a','b']:
                folder=project/name;(folder/'src').mkdir(parents=True)
                manifest=f'[package]\nname="fixture-{name}"\nversion="0.1.0"\nedition="2021"\n'
                if name=='a':manifest+='[dependencies]\nfixture-b={path="../b"}\n'
                (folder/'Cargo.toml').write_text(manifest)
                (folder/('src/main.rs'if name=='a'else'src/lib.rs')).write_text('fn main(){println!("{}",fixture_b::value());}\n'if name=='a'else'pub fn value()->u8{7}\n')
            configurations[profile]={str(p.relative_to(project)):p.read_text()for p in sorted(project.rglob('*'))if p.is_file()}
            def state():
                return {'sourceSha256':{name:sha(project/name)for name in configurations[profile]},'lockSha256':sha(project/'Cargo.lock'),'targetPresent':(base/'target').exists()}
            def command(label,args,cwd=None,expected_error=False):
                argv=[str(cargo),*args,'--offline'];before=state();started=time.monotonic();child=subprocess.Popen(argv,cwd=cwd or project,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
                timeout=False
                try:stdout,stderr=child.communicate(input=b'',timeout=60)
                except subprocess.TimeoutExpired:
                    timeout=True
                    try:os.killpg(child.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    stdout,stderr=child.communicate()
                stem=profile+'-'+label;(run/(stem+'.stdout')).write_bytes(stdout);(run/(stem+'.stderr')).write_bytes(stderr)
                row={'profile':profile,'case':label,'argv':argv,'cwd':str(cwd or project),'observed':{'before':before,'after':state(),'seconds':time.monotonic()-started,'stdoutSha256':hashlib.sha256(stdout).hexdigest(),'stderrSha256':hashlib.sha256(stderr).hexdigest()},'outcome':{'exitCode':child.returncode,'timedOut':timeout}}
                rows.append(row);(run/'trace.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps({'profile':profile,'case':label,'exitCode':child.returncode,'seconds':round(row['observed']['seconds'],3)}),flush=True)
                if timeout:raise RuntimeError('Owned Cargo group timed out and was killed;preserve before retry.')
                if child.returncode!=0 and not expected_error:raise RuntimeError('Unexpected Cargo failure;inspect retained output.')
                return row
            command('metadata-root',['metadata','--format-version=1','--no-deps'])
            command('default',['check','--message-format=json'])
            command('workspace-exclude-b',['check','--workspace','--exclude','fixture-b','--message-format=json'])
            command('member-b',['check','--message-format=json'],project/'b')
            command('metadata-member-b',['metadata','--format-version=1','--no-deps'],project/'b')
            command('root-manifest-from-b',['check','--manifest-path',str(project/'Cargo.toml'),'--message-format=json'],project/'b')
            command('explicit-a',['check','-p','fixture-a','--message-format=json'])
            command('exclude-without-workspace',['check','--exclude','fixture-b','--message-format=json'],expected_error=True)
            command('clean',['clean'])
            assert not(base/'target').exists()
        processes=subprocess.check_output(['ps','-axo','pid=,command='],text=True);assert not any(str(work)in line for line in processes.splitlines())
        allocated=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]);shutil.move(str(work),run/'work')
        receipt={'schema':1,'producerSha256':hashlib.sha256(PRODUCER).hexdigest(),'tools':tool_versions,'platform':platform.platform(),'architecture':platform.machine(),'originalWork':str(work),'environments':environments,'profiles':4,'commands':len(rows),'targetDirectoriesCleaned':True,'noMatchingProcessAtMove':True,'retainedAllocatedKiB':allocated,'scope':'Generated path-only Cargo metadata/check requests. Check artifacts are not linked executable/runtime evidence;selected source hashes and lock/target state observed. No user project or registry.'}
        (run/'configuration.json').write_text(json.dumps(configurations,indent=2)+'\n');(run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'run':str(run),'commands':len(rows),'retainedAllocatedKiB':allocated}),flush=True)
    except BaseException as error:
        (run/'failure.json').write_text(json.dumps({'error':str(error),'originalWork':str(work),'commands':len(rows),'producerSha256':hashlib.sha256(PRODUCER).hexdigest()},indent=2)+'\n');raise


if __name__=='__main__':main()
