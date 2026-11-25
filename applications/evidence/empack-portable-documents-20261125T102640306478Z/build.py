#!/usr/bin/env python3
"""Owner-run isolated unchanged DocumentCodec build, never the full product."""
from datetime import datetime,timezone
import hashlib,json,os,signal,subprocess,tempfile,time,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;REV='0b4462e3032b4f09230b15329722eabefb7f574c'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
 repo=ROOT.parent/'empack';assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==REV
 run=ROOT/'applications/evidence'/('empack-portable-documents-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir();work=Path(tempfile.mkdtemp(prefix='rules-portable-documents-',dir='/private/tmp'))
 for d in ['src/engine/documents','core/src','home','tmp']:(work/d).mkdir(parents=True)
 (run/'build.py').write_bytes(Path(__file__).read_bytes())
 sourcepaths=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only',REV,'crates/empack-core/src','crates/empack-lib/src/engine/documents.rs','crates/empack-lib/src/engine/documents'],text=True).splitlines();pins=[]
 for path in sourcepaths:
  raw=subprocess.check_output(['git','-C',str(repo),'show',REV+':'+path]);assert raw==(repo/path).read_bytes()
  if path.startswith('crates/empack-core/src/'):
   target=work/'core/src'/Path(path).relative_to('crates/empack-core/src')
  else:target=work/'src/engine'/Path(path).relative_to('crates/empack-lib/src/engine')
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);pins.append(dict(path=path,sha256=sha(target),frozen=str(target.relative_to(work))))
 for name in ['lib.rs','main.rs']:
  raw=(HERE/'document-portable'/name).read_bytes();(run/name).write_bytes(raw);(work/'src'/name).write_bytes(raw)
 lockraw=subprocess.check_output(['git','-C',str(repo),'show',REV+':Cargo.lock']);(work/'Cargo.lock').write_bytes(lockraw);lock=tomllib.loads(lockraw.decode())
 names=['anyhow','serde','serde_json','serde-saphyr','sha2','thiserror']
 deps={name:next(p['version']for p in lock['package']if p['name']==name)for name in names}
 toml='[package]\nname="rules-document-study"\nversion="0.0.0"\nedition="2024"\n[lib]\ncrate-type=["cdylib","rlib"]\n[dependencies]\nempack-core={path="core"}\n'
 for name,version in deps.items():toml+=name+'={version="='+version+'"'+(',features=["derive"]'if name=='serde'else'')+'}\n'
 # reqwest re-exports this exact URL type. No HTTP code is copied or linked.
 url=next(p['version']for p in lock['package']if p['name']=='url');toml+='reqwest={package="url",version="='+url+'"}\n'
 toml+='[profile.dev]\ndebug=0\nopt-level=0\nincremental=false\nstrip="symbols"\npanic="abort"\n';(work/'Cargo.toml').write_text(toml);(work/'core/Cargo.toml').write_text('[package]\nname="empack-core"\nversion="0.0.0"\nedition="2024"\n');(run/'Cargo.toml').write_text(toml)
 cargo=Path('/Users/zer0cell/.rustup/toolchains/1.100.0-aarch64-apple-darwin/bin/cargo');rustc=cargo.with_name('rustc');env=dict(os.environ,PATH=str(cargo.parent)+':/usr/bin:/bin',CARGO_BUILD_JOBS='2',CARGO_INCREMENTAL='0',CARGO_TARGET_DIR=str(work/'target'),CARGO_NET_OFFLINE='true',TMPDIR=str(work/'tmp'))
 receipt=dict(schema=1,revision=REV,run=str(run.relative_to(ROOT)),work=str(work),sourcePins=pins,producerSha256=sha(run/'build.py'),adapterSha256={n:sha(run/n)for n in ['lib.rs','main.rs']},originalCargoLockSha256=hashlib.sha256(lockraw).hexdigest(),tools={n:dict(path=str(p),sha256=sha(p),version=subprocess.check_output([str(p),'--version','--verbose'],text=True))for n,p in [('cargo',cargo),('rustc',rustc)]},dependencies=deps,urlAlias=dict(alias='reqwest',actualPackage='url',version=url,reason='Current codec uses only reqwest::Url;reqwest re-exports url::Url. Alias preserves the source call and parser,not HTTP capability.'),commands=[],limits=['Full unchanged document module+submodules and core;selected public calls only. Not a complete portable engine/project store/consumer exporter.','Synthesis changes crate metadata and aliases URL package;no production source edits. Compilation does not exercise every function.','No full product,Cargo workspace,network,GUI or native state access. Offline compiler dependencies are local host inputs.'])
 def save():write(run/'build.json',receipt)
 save();print(json.dumps(dict(run=str(run.relative_to(ROOT)),work=str(work))),flush=True)
 for label,args in [('native',['build','--offline','--bin','rules-document-study']),('wasm',['build','--offline','--lib','--target','wasm32-unknown-unknown'])]:
  argv=[str(cargo),*args,'--manifest-path',str(work/'Cargo.toml')];started=time.monotonic();p=subprocess.Popen(argv,cwd=work,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  try:out,err=p.communicate(timeout=240)
  except BaseException:
   if p.poll()is None:os.killpg(p.pid,signal.SIGKILL);p.communicate(timeout=10)
   raise
  for suffix,b in [('stdout',out),('stderr',err)]:(run/(label+'.'+suffix)).write_bytes(b)
  try:os.killpg(p.pid,0)
  except ProcessLookupError:absent=True
  else:absent=False
  receipt['commands'].append(dict(label=label,argv=argv,exitCode=p.returncode,seconds=time.monotonic()-started,pid=p.pid,groupAbsent=absent,stdoutSha256=sha(run/(label+'.stdout')),stderrSha256=sha(run/(label+'.stderr'))));save();print(json.dumps(dict(label=label,exitCode=p.returncode,groupAbsent=absent,seconds=receipt['commands'][-1]['seconds'])),flush=True)
  if p.returncode:raise RuntimeError(err.decode()[-2400:])
  artifact=work/'target'/('debug/rules-document-study'if label=='native'else'wasm32-unknown-unknown/debug/rules_document_study.wasm');receipt[label]=dict(path=str(artifact),sha256=sha(artifact),bytes=artifact.stat().st_size);save()
 (run/'Cargo.lock').write_bytes((work/'Cargo.lock').read_bytes());receipt['selectedCargoLockSha256']=sha(run/'Cargo.lock');receipt['privateKiB']=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]);save()
 print(json.dumps(dict(complete=True,native=receipt['native']['bytes'],wasm=receipt['wasm']['bytes'],privateKiB=receipt['privateKiB'])),flush=True)
if __name__=='__main__':main()
