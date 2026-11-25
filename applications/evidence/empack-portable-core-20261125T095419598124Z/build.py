#!/usr/bin/env python3
"""Freeze unchanged core and compile the same small wire adapter native/WASM."""
from datetime import datetime,timezone
import hashlib,json,os,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;REV='0b4462e3032b4f09230b15329722eabefb7f574c';PRODUCER=Path(__file__).read_bytes();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def main():
 repo=ROOT.parent/'empack';assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==REV
 rustc=Path('/Users/zer0cell/.rustup/toolchains/1.100.0-aarch64-apple-darwin/bin/rustc');target=rustc.parents[1]/'lib/rustlib/wasm32-unknown-unknown/lib';assert target.is_dir()
 run=ROOT/'applications/evidence'/('empack-portable-core-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir();work=Path(tempfile.mkdtemp(prefix='rules-portable-core-',dir='/private/tmp'))
 for d in['home','tmp','core']:(work/d).mkdir()
 (run/'build.py').write_bytes(PRODUCER);(run/'engine.rs').write_bytes((HERE/'portable-core/engine.rs').read_bytes());pins=[]
 files=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only',REV,'crates/empack-core/src'],text=True).splitlines()
 for name in files:
  raw=subprocess.check_output(['git','-C',str(repo),'show',REV+':'+name]);assert raw==(repo/name).read_bytes();relative=Path(name).relative_to('crates/empack-core/src');p=work/'core'/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);pins.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest()))
 env=dict(PATH=str(rustc.parent)+':/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8');commands=[]
 receipt=dict(schema=1,revision=REV,run=str(run.relative_to(ROOT)),work=str(work),sourcePins=pins,producerSha256=sha(run/'build.py'),adapterSha256=sha(run/'engine.rs'),tool=dict(path=str(rustc),sha256=sha(rustc),version=subprocess.check_output([str(rustc),'--version','--verbose'],text=True)),commands=commands,limits=['Unchanged pure core and common research wire adapter,not portable empack engine/project codec/consumer exporter.','WASM ABI is single-host serialized and bounded;raw pointers exist only in WASM memory,not native entry points.','Digest/length fields are host observations;this adapter does not verify source bytes or grant native authority.'])
 def save():write(run/'build.json',receipt)
 save()
 for name,targetName in[('native',None),('wasm','wasm32-unknown-unknown')]:
  suffix=[]if targetName is None else['--target',targetName];core=work/('libempack_core_'+name+'.rlib');artifact=work/('core-native'if name=='native'else'core.wasm')
  for label,argv in[(name+'-core',[str(rustc),'--edition=2024','--crate-name','empack_core','--crate-type','rlib',str(work/'core/lib.rs'),'-C','opt-level=1','-o',str(core),*suffix]),(name+'-adapter',[str(rustc),'--edition=2024','--crate-name','portable_core_study',*(['--crate-type','cdylib']if targetName else[]),str(run/'engine.rs'),'--extern','empack_core='+str(core),'-C','opt-level=1','-C','panic=abort','-C','strip=symbols','-o',str(artifact),*suffix])]:
   start=time.monotonic();p=subprocess.run(argv,env=env,capture_output=True,timeout=90);(run/(label+'.stdout')).write_bytes(p.stdout);(run/(label+'.stderr')).write_bytes(p.stderr);commands.append(dict(label=label,argv=argv,exitCode=p.returncode,seconds=time.monotonic()-start));save();assert p.returncode==0,p.stderr.decode()[-2500:]
  receipt[name]=dict(path=str(artifact),sha256=sha(artifact),bytes=artifact.stat().st_size,coreRlibSha256=sha(core));save()
 receipt['privateKiB']=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]);save();print(json.dumps(dict(run=str(run.relative_to(ROOT)),work=str(work),native=receipt['native']['bytes'],wasm=receipt['wasm']['bytes'])))
if __name__=='__main__':main()
