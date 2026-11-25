#!/usr/bin/env python3
"""Owner-run shared-engine research build, preserving prior artifacts/cache."""
from datetime import datetime,timezone
import hashlib,json,os,signal,subprocess,tempfile,time,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;REV='0b4462e3032b4f09230b15329722eabefb7f574c';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
 repo=ROOT.parent/'empack';prior=ROOT/'applications/evidence/empack-portable-documents-20261125T102640306478Z';old=json.loads((prior/'build.json').read_text());target=Path(old['work'])/'target';assert target.is_dir()
 held={v['path']:v['sha256']for v in [old['native'],old['wasm']]};assert all(sha(Path(p))==h for p,h in held.items())
 run=ROOT/'applications/evidence'/('empack-joined-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir();work=Path(tempfile.mkdtemp(prefix='rules-joined-',dir='/private/tmp'))
 for d in ['src/engine/documents','src/engine/templates','tmp']:(work/d).mkdir(parents=True)
 (run/'build.py').write_bytes(Path(__file__).read_bytes());pins=[];fragments=[]
 def source(p):
  raw=subprocess.check_output(['git','-C',str(repo),'show',REV+':'+p]);assert raw==(repo/p).read_bytes();pins.append(dict(path=p,sha256=hashlib.sha256(raw).hexdigest()));return raw
 paths=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only',REV,'crates/empack-lib/src/engine/documents.rs','crates/empack-lib/src/engine/documents'],text=True).splitlines()
 for p in paths:(work/'src/engine'/Path(p).relative_to('crates/empack-lib/src/engine')).write_bytes(source(p))
 for name in ['layout.rs','runtime_versions.rs']:(work/'src/engine'/name).write_bytes(source('crates/empack-lib/src/engine/'+name))
 (work/'src/engine/instance.cfg.template').write_bytes(source('crates/empack-lib/templates/client/instance.cfg.template'))
 (work/'src/engine/templates/encoding.rs').write_bytes(source('crates/empack-lib/src/engine/templates/encoding.rs'))
 def fragment(path,raw,start,end):
  text=raw.decode();a=text.index(start);b=text.index(end,a);body=text[a:b];fragments.append(dict(path=path,start=a,end=b,sha256=hashlib.sha256(body.encode()).hexdigest()));return body
 p='crates/empack-lib/src/engine/prism.rs';raw=source(p);(work/'src/engine/prism.rs').write_text(fragment(p,raw,'//! Shared Prism','/// Read-only launcher input'))
 p='crates/empack-lib/src/engine/templates.rs';raw=source(p);helpers=fragment(p,raw,'mod encoding;','use super::{');tail=fragment(p,raw,'fn template_values(','#[cfg(test)]');template='use anyhow::{Result,ensure};\nuse empack_core::model::LoaderKind;\nuse std::{collections::BTreeMap,io::{self,Write}};\nuse crate::cancellation::Cancellation;\n'+helpers+tail;(work/'src/engine/templates.rs').write_text(template)
 p='crates/empack-lib/src/application/process_runtime.rs';raw=source(p);interrupted=fragment(p,raw,'#[derive(Debug, thiserror::Error)]\n#[error("Operation interrupted")]','/// A completed instance');sync=fragment(p,raw,'#[derive(Clone, Default)]\npub struct Cancellation','    pub(crate) async fn cancelled');(work/'src/cancellation.rs').write_text('use anyhow::Result;\nuse std::sync::{Arc,atomic::{AtomicBool,Ordering}};\n'+interrupted+sync+'}\n')
 for name in ['lib.rs','main.rs']:(work/'src'/name).write_bytes((HERE/'joined-study'/name).read_bytes());(run/name).write_bytes((HERE/'joined-study'/name).read_bytes())
 lockraw=source('Cargo.lock');lock=tomllib.loads(lockraw.decode());(work/'Cargo.lock').write_bytes(lockraw);names=['anyhow','serde','serde_json','serde-saphyr','sha2','thiserror','caseless','unicode-normalization','semver','handlebars','zip'];versions={n:next(p['version']for p in lock['package']if p['name']==n)for n in names}
 toml='[package]\nname="rules-joined-study"\nversion="0.0.0"\nedition="2024"\n[lib]\ncrate-type=["cdylib","rlib"]\n[dependencies]\nempack-core={path='+json.dumps(str(Path(old['work'])/'core'))+'}\n'
 for n,v in versions.items():toml+=n+'={version="='+v+'"'+(',features=["derive"]'if n=='serde'else',default-features=false,features=["deflate"]'if n=='zip'else'')+'}\n'
 toml+='reqwest={package="url",version="=2.5.8"}\n[profile.dev]\ndebug=0\nopt-level=0\nincremental=false\nstrip="symbols"\npanic="abort"\n';(work/'Cargo.toml').write_text(toml);(run/'Cargo.toml').write_text(toml)
 cargo=Path('/Users/zer0cell/.rustup/toolchains/1.100.0-aarch64-apple-darwin/bin/cargo');env=dict(os.environ,PATH=str(cargo.parent)+':/usr/bin:/bin',RUSTC=str(cargo.with_name('rustc')),CARGO_BUILD_JOBS='2',CARGO_INCREMENTAL='0',CARGO_TARGET_DIR=str(target),CARGO_NET_OFFLINE='true',TMPDIR=str(work/'tmp'))
 receipt=dict(schema=1,revision=REV,run=str(run.relative_to(ROOT)),work=str(work),target=str(target),reusedBuild=dict(capture=str(prior.relative_to(ROOT)),sha256=sha(prior/'build.json')),heldArtifacts=held,sourcePins=pins,fragments=fragments,producerSha256=sha(run/'build.py'),adapterSha256={n:sha(run/n)for n in ['lib.rs','main.rs']},dependencies=versions,commands=[],limits=['Research project schema,stream protocol and ZIP adapter are proposed code;DocumentCodec/core/Prism/layout/INI/template selected source remains attributed.','Synchronous cancellation source excludes its Tokio wait method;this does not qualify native process supervision.','Original prior binaries/source/locks remain immutable;only private dependency target cache is reused.'])
 def save():write(run/'build.json',receipt)
 save();Path(ROOT/'.build/empack-joined-current').write_text(str(run)+'\n');print(json.dumps(dict(run=str(run.relative_to(ROOT)),work=str(work))),flush=True)
 for label,args in [('native',['build','--offline','--bin','rules-joined-study']),('wasm',['build','--offline','--lib','--target','wasm32-unknown-unknown'])]:
  argv=[str(cargo),*args,'--manifest-path',str(work/'Cargo.toml')];start=time.monotonic();p=subprocess.Popen(argv,cwd=work,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  try:out,err=p.communicate(timeout=240)
  except BaseException:
   if p.poll()is None:os.killpg(p.pid,signal.SIGKILL);p.communicate(timeout=10)
   raise
  for suffix,b in [('stdout',out),('stderr',err)]:(run/(label+'.'+suffix)).write_bytes(b)
  try:os.killpg(p.pid,0)
  except ProcessLookupError:absent=True
  else:absent=False
  receipt['commands'].append(dict(label=label,argv=argv,exitCode=p.returncode,seconds=time.monotonic()-start,groupAbsent=absent,stdoutSha256=sha(run/(label+'.stdout')),stderrSha256=sha(run/(label+'.stderr'))));receipt['heldUnchanged']=all(sha(Path(q))==h for q,h in held.items());save();print(json.dumps(receipt['commands'][-1]),flush=True)
  if p.returncode:raise RuntimeError(err.decode()[-3500:])
  artifact=target/('debug/rules-joined-study'if label=='native'else'wasm32-unknown-unknown/debug/rules_joined_study.wasm');receipt[label]=dict(path=str(artifact),sha256=sha(artifact),bytes=artifact.stat().st_size);save()
 (run/'Cargo.lock').write_bytes((work/'Cargo.lock').read_bytes());receipt['selectedLockSha256']=sha(run/'Cargo.lock');receipt['workKiB']=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]);receipt['targetKiB']=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0]);save();print(json.dumps(dict(complete=True,native=receipt['native']['bytes'],wasm=receipt['wasm']['bytes'],workKiB=receipt['workKiB'],targetKiB=receipt['targetKiB'])),flush=True)
if __name__=='__main__':main()
