"""Owner-run offline Cargo configuration/build/run fixture. Generated code only."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
BIN=Path('/Users/zer0cell/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,x:p.write_text(json.dumps(x,indent=2)+'\n')
MAIN='''use std::{env,fs,io::Write};
fn main() {
    let code:i32=env::var("RULES_APP_STATUS").unwrap_or_else(|_|"0".into()).parse().unwrap();
    let line=format!("{{\\\"cwd\\\":{:?},\\\"args\\\":{:?},\\\"code\\\":{}}}",env::current_dir().unwrap().to_str().unwrap(),env::args().skip(1).collect::<Vec<_>>(),code);
    let mut file=fs::OpenOptions::new().create(true).append(true).open(env::var_os("RULES_APP_JOURNAL").unwrap()).unwrap();
    writeln!(file,"{}",line).unwrap();println!("{}",line);
    std::process::exit(code);
}
'''
RUNNER='''import json,os,sys
label,binary,*args=sys.argv[1:]
with open(os.environ['RULES_RUNNER_JOURNAL'],'a') as f:
    f.write(json.dumps(dict(label=label,binary=binary,args=args,cwd=os.getcwd()))+'\\n')
status=int(os.environ.get('RULES_RUNNER_STATUS','0'))
if status:sys.exit(status)
os.execv(binary,[binary,*args])
'''

def item(p):return None if not p.exists() else dict(bytes=p.stat().st_size,sha256=sha(p),mode=p.stat().st_mode&0o777)
def events(p):return [] if not p.exists() else [json.loads(s) for s in p.read_text().splitlines()]
def main():
    pins=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']
    assert platform.system()=='Darwin' and platform.machine()=='arm64'
    assert sha(BIN/'cargo')==pins['cargo']['sha256'] and sha(BIN/'rustc')=='12cab30aa9890d54445e29149a1e82d18fbe457de12801bd11bbe7e5e7fe33a0'
    work=Path(tempfile.mkdtemp(prefix='rules-cargo-run-',dir='/private/tmp'))
    for parent in [work,*work.parents]:assert not any((parent/'.cargo'/n).exists() for n in ['config','config.toml'])
    for name in ['project/src','project/.cargo','home','cargo-home','tmp']:(work/name).mkdir(parents=True)
    project=work/'project';manifest=project/'Cargo.toml';source=project/'src/main.rs';config=project/'.cargo/config.toml';runner=work/'runner.py'
    manifest.write_text('[package]\nname="rules-run-profile"\nversion="0.1.0"\nedition="2021"\n[profile.dev]\ndebug=0\nincremental=false\n')
    source.write_text(MAIN);runner.write_text(RUNNER)
    command_string=lambda label:sys.executable+' '+str(runner)+' '+label
    config.write_text('[target.aarch64-apple-darwin]\nrunner='+json.dumps(command_string('project'))+'\n')
    executable=work/'target/debug/rules-run-profile';runner_log=work/'runner.jsonl';app_log=work/'app.jsonl'
    env=dict(PATH=str(BIN)+':/usr/bin:/bin',HOME=str(work/'home'),CARGO_HOME=str(work/'cargo-home'),CARGO_TARGET_DIR=str(work/'target'),RUSTC=str(BIN/'rustc'),RUSTDOC=str(BIN/'rustdoc'),TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8',CARGO_BUILD_JOBS='1',CARGO_NET_OFFLINE='true',CARGO_TERM_COLOR='never',CARGO_INCREMENTAL='0',RULES_RUNNER_JOURNAL=str(runner_log),RULES_APP_JOURNAL=str(app_log),RULES_RUNNER_STATUS='0',RULES_APP_STATUS='0')
    run=ROOT/'applications/evidence'/('cargo-run-config-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir();(run/'probe.py').write_bytes(Path(__file__).read_bytes())
    setup=dict(schema=1,work=str(work),producerSha256=sha(run/'probe.py'),environment=env,tools={n:dict(path=str(BIN/n),sha256=sha(BIN/n)) for n in ['cargo','rustc']},python=dict(path=sys.executable,sha256=sha(Path(sys.executable))),runnerSha256=sha(runner),platform=platform.platform(),host='aarch64-apple-darwin',scope='Generated offline dependency-free package and owned Python runner;private child HOME/CARGO_HOME/target;scalar runner strings,known host only. No user configs/projects/registry,arbitrary argv serialization,foreign target or process containment proof.')
    write(run/'setup.json',setup);rows=[];edits=[]
    def state():return dict(project={p.relative_to(project).as_posix():item(p) for p in sorted(project.rglob('*')) if p.is_file()},binary=item(executable),runner=events(runner_log),app=events(app_log))
    def call(label,cwd,args,extra=None,expected=0):
        before=state();child_env={**env,**(extra or {})};started=time.monotonic();argv=[str(BIN/'cargo'),*args];child=subprocess.Popen(argv,cwd=cwd,env=child_env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        print(json.dumps(dict(start=label,pid=child.pid)),flush=True);timed=False
        try:out,err=child.communicate(timeout=90)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
        for n,b in [('stdout',out),('stderr',err)]:(run/(label+'.'+n)).write_bytes(b)
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        rows.append(dict(id=label,argv=argv,cwd=str(cwd),environmentOverrides=extra or {},pid=child.pid,exitCode=child.returncode,timedOut=timed,groupAbsent=absent,seconds=time.monotonic()-started,before=before,after=state(),streams={n:sha(run/(label+'.'+n)) for n in ['stdout','stderr']}));write(run/'commands.json',rows)
        print(json.dumps(dict(finish=label,exitCode=child.returncode,seconds=rows[-1]['seconds'])),flush=True)
        assert not timed and absent and child.returncode==expected,'Preserve unexpected outcome;do not automatically repeat.'
    args=['space argument','Ω日本','--literal-flag'];base=['run','--offline','--message-format=json'];target_env='CARGO_TARGET_AARCH64_APPLE_DARWIN_RUNNER'
    try:
        call('project-config',project,[*base,'--',*args])
        call('environment-runner',project,[*base,'--',*args],{target_env:command_string('environment')})
        override='target.aarch64-apple-darwin.runner='+json.dumps(command_string('cli'))
        call('cli-runner',project,['--config',override,*base,'--',*args],{target_env:command_string('environment')})
        from_parent=[*base,'--manifest-path',str(manifest),'--',*args]
        call('manifest-from-parent',work,from_parent)
        call('explicit-config-from-parent',work,['--config',str(config),*from_parent])
        call('runner-refuses',project,[*base,'--',*args],{'RULES_RUNNER_STATUS':'9'},expected=9)
        before=state();source.write_text('fn main() { controlled_invalid_rust }\n');edits.append(dict(id='break-source',before=before,after=state()));write(run/'authored-edits.json',edits)
        call('failed-build',project,[*base,'--',*args],expected=101)
        before=state();source.write_text(MAIN);edits.append(dict(id='restore-source',before=before,after=state()));write(run/'authored-edits.json',edits)
        call('source-repaired',project,[*base,'--',*args])
        call('application-fails',project,[*base,'--',*args],{'RULES_APP_STATUS':'7'},expected=7)
        retained=work/'retained-binary';shutil.copy2(executable,retained);assert sha(retained)==sha(executable)
        call('owned-target-clean',project,['clean','--offline'])
        assert not (work/'target').exists()
        write(run/'receipt.json',dict(schema=1,complete=True,commands=len(rows),runRequests=9,cleanupCommands=1,allRecordedGroupsAbsent=all(r['groupAbsent'] for r in rows),authoredEdits=len(edits),producerSha256=sha(run/'probe.py'),setupSha256=sha(run/'setup.json'),retainedBinary=dict(path=str(retained),sha256=sha(retained)),workAllocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),scope='Native collection only;independent config/build/run phase and artifact/journal review pending. Cleanup is confined to the newly generated CARGO_TARGET_DIR;source/journals/retained binary remain.'))
        print(json.dumps(dict(run=str(run),work=str(work),complete=True)),flush=True)
    except BaseException as e:
        write(run/'failure.json',dict(type=type(e).__name__,message=str(e),commands=len(rows)));print(json.dumps(dict(run=str(run),work=str(work),complete=False)),flush=True);raise

if __name__=='__main__':main()
