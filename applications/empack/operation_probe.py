#!/usr/bin/env python3
"""Run unchanged runtime/resource modules with owned gates; no product build/store."""
from datetime import datetime,timezone
import hashlib,json,os,platform,signal,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
REV='0b4462e3032b4f09230b15329722eabefb7f574c';PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
    assert platform.system()=='Darwin'
    repo=ROOT.parent/'empack';assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==REV
    run=ROOT/'applications/evidence'/('empack-operations-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir()
    work=Path(tempfile.mkdtemp(prefix='rules-empack-operations-',dir='/private/tmp'))
    for n in['home','tmp']:(work/n).mkdir()
    (run/'probe.py').write_bytes(PRODUCER);(run/'driver.rs').write_bytes((HERE/'operation_oracle.rs').read_bytes())
    paths=['crates/empack-lib/src/engine/runtime.rs','crates/empack-lib/src/engine/resources.rs','crates/empack-lib/src/application/process_runtime.rs','crates/empack-lib/src/engine/runtime/tests.rs','crates/empack-lib/src/engine/api.rs','crates/empack-lib/src/application/engine_host.rs','Cargo.lock']
    sources={};pins=[]
    for path in paths:
        raw=subprocess.check_output(['git','-C',str(repo),'show',REV+':'+path]);assert raw==(repo/path).read_bytes();sources[path]=raw
        pins.append(dict(path=path,sha256=hashlib.sha256(raw).hexdigest()))
    for name in['runtime','resources']:(work/(name+'.rs')).write_bytes(sources['crates/empack-lib/src/engine/'+name+'.rs'])
    text=sources['crates/empack-lib/src/application/process_runtime.rs'].decode();parts=[]
    for begin,end in[('#[derive(Debug, thiserror::Error)]\n#[error("Operation interrupted")]','\n/// A completed instance runtime'),('#[derive(Clone, Default)]\npub struct Cancellation','\nconst OUTPUT_LIMIT')]:
        assert text.count(begin)==text.count(end)==1;part=text[text.index(begin):text.index(end)];parts.append(part)
    cancel='use anyhow::Result;use std::sync::{Arc,atomic::{AtomicBool,Ordering}};use std::time::Duration;\n'+'\n'.join(parts)
    (work/'cancellation.rs').write_text(cancel)
    literal=lambda p:json.dumps(str(p))
    scaffold='#![allow(dead_code,unused_imports)]\nmod application { #[path='+literal(work/'cancellation.rs')+']pub mod process_runtime; }\nmod engine {\n'
    for name in['runtime','resources']:scaffold+='#[path='+literal(work/(name+'.rs'))+']pub mod '+name+';\n'
    scaffold+='pub mod study {\n'+(run/'driver.rs').read_text()+'\n}\n}\nfn main(){let path=std::env::args().nth(1).unwrap();tokio::runtime::Builder::new_multi_thread().worker_threads(2).enable_all().build().unwrap().block_on(engine::study::run(path.into()));}\n'
    (work/'main.rs').write_text(scaffold)
    rustc=Path('/Users/zer0cell/.rustup/toolchains/1.99.1-aarch64-apple-darwin/bin/rustc');deps=repo/'target/debug/deps';links={}
    for name in['tokio','thiserror','anyhow','serde_json']:
        matches=list(deps.glob('lib'+name+'-*.rlib'));assert len(matches)==1,(name,len(matches));links[name]=matches[0]
    tool=dict(path=str(rustc),sha256=sha(rustc),version=subprocess.check_output([str(rustc),'--version','--verbose'],text=True))
    env=dict(PATH=str(rustc.parent)+':/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8')
    binary=work/'operation-driver';cmd=[str(rustc),'--edition=2024',str(work/'main.rs'),'-L','dependency='+str(deps),'-o',str(binary)]
    for name,path in links.items():cmd+=['--extern',name+'='+str(path)]
    write(run/'inputs.json',dict(schema=1,revision=REV,work=str(work),sources=pins,tool=tool,dependencies=[dict(name=n,path=str(p),sha256=sha(p))for n,p in links.items()],cancellationSelections=[dict(text=p,sha256=hashlib.sha256(p.encode()).hexdigest())for p in parts],generatedSha256=sha(work/'main.rs'),cancellationSha256=sha(work/'cancellation.rs'),producerSha256=sha(run/'probe.py'),driverSha256=sha(run/'driver.rs')))
    p=subprocess.run(cmd,env=env,capture_output=True,timeout=60);(run/'compile.stdout').write_bytes(p.stdout);(run/'compile.stderr').write_bytes(p.stderr);write(run/'compile.json',dict(argv=cmd,exitCode=p.returncode));assert p.returncode==0,p.stderr.decode()[-3000:]
    argv=[str(binary),str(work/'held-file')];start=time.monotonic()
    with(run/'native.stdout').open('wb')as out,(run/'native.stderr').open('wb')as err:
        p=subprocess.Popen(argv,env=env,stdout=out,stderr=err,start_new_session=True);pid=p.pid
        try:code=p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(pid,signal.SIGTERM)
            try:p.wait(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(pid,signal.SIGKILL);p.wait()
            raise
    write(run/'exit.json',dict(schema=1,pid=pid,exitCode=code,seconds=time.monotonic()-start,binarySha256=sha(binary),stdoutSha256=sha(run/'native.stdout'),stderrSha256=sha(run/'native.stderr')))
    assert code==0,(run/'native.stderr').read_text()[-2000:]
    try:os.killpg(pid,0);raise AssertionError('Owned process group still exists')
    except ProcessLookupError:pass
    ps=subprocess.check_output(['ps','-axo','pid=,ppid=,args='],text=True);hits=[s for s in ps.splitlines()if str(work)in s and 'python3 - <<'not in s];assert not hits,hits
    rows=[json.loads(s)for s in(run/'native.stdout').read_text().splitlines()];write(run/'observed.json',dict(schema=1,rows=rows))
    write(run/'closure.json',dict(schema=1,originalGroupAbsent=True,workspaceProcessHits=hits,retainedFileHex=(work/'held-file').read_bytes().hex(),privateKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),binarySha256=sha(binary),noProductBuild=True,limits='Selected actual source modules and native Tokio;not full Engine/CLI/publisher/process adapter. Subordinate compiler/dependency build provenance not established.'))
    print(json.dumps(dict(run=str(run.relative_to(ROOT)),rows=len(rows),seconds=time.monotonic()-start,work=str(work))))
if __name__=='__main__':main()
