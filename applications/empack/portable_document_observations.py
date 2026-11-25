#!/usr/bin/env python3
"""Read-only retained document-codec/source/artifact observer; no application runs."""
import hashlib,json,subprocess,tarfile,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUN=ROOT/'applications/evidence/empack-portable-documents-20261125T102919154918Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def archive_sources(archive,directory,expected):
 assert sha(archive)==expected
 files={}
 with tarfile.open(archive,'r:gz')as tar:
  for member in tar:
   parts=Path(member.name).parts;assert parts and parts[0]==directory.name and '..'not in parts and not Path(member.name).is_absolute()
   if member.isdir():continue
   assert member.isfile()and member.size<=32*1024*1024
   relative=Path(*parts[1:]);p=directory/relative;assert not p.is_symlink()and p.resolve().is_relative_to(directory.resolve())
   digest=hashlib.sha256(tar.extractfile(member).read()).hexdigest();assert sha(p)==digest;files[str(relative)]=digest
 return files
def inspect(overrides=None):
 def record(name):return overrides[name]if overrides and name in overrides else read(RUN/name)
 reuse=record('reused-build.json');prior=ROOT/reuse['capture'];assert sha(prior/'build.json')==reuse['buildReceiptSha256'];build=read(prior/'build.json');work=Path(build['work'])
 assert len(build['commands'])==2 and all(c['exitCode']==0 and c['groupAbsent']for c in build['commands'])
 for c in build['commands']:
  for stream in ['stdout','stderr']:assert sha(prior/(c['label']+'.'+stream))==c[stream+'Sha256']
 for name in ['native','wasm']:assert sha(Path(build[name]['path']))==build[name]['sha256']
 for name,tool in build['tools'].items():assert sha(Path(tool['path']))==tool['sha256']
 assert sha(prior/'build.py')==build['producerSha256']==sha(ROOT/'applications/empack/portable_document_build.py')
 for name,digest in build['adapterSha256'].items():assert sha(prior/name)==digest==sha(ROOT/'applications/empack/document-portable'/name)==sha(work/'src'/name)
 for pin in build['sourcePins']:
  raw=subprocess.check_output(['git','-C',str(ROOT.parent/'empack'),'show',build['revision']+':'+pin['path']]);assert hashlib.sha256(raw).hexdigest()==pin['sha256']==sha(work/pin['frozen'])
 assert sha(prior/'Cargo.lock')==build['selectedCargoLockSha256']==sha(work/'Cargo.lock')
 original=subprocess.check_output(['git','-C',str(ROOT.parent/'empack'),'show',build['revision']+':Cargo.lock']);assert hashlib.sha256(original).hexdigest()==build['originalCargoLockSha256']
 selected=tomllib.loads((prior/'Cargo.lock').read_text())['package'];original=tomllib.loads(original.decode())['package'];original_by_key={(p['name'],p['version']):p for p in original};packages=[]
 cache=Path('/Users/zer0cell/.cargo/registry/cache/index.crates.io-1949cf8c6b5b557f');src=cache.parents[1]/'src/index.crates.io-1949cf8c6b5b557f'
 for p in selected:
  if 'checksum'not in p:continue
  assert original_by_key[(p['name'],p['version'])]['checksum']==p['checksum']
  archive=cache/(p['name']+'-'+p['version']+'.crate');directory=src/(p['name']+'-'+p['version']);files=archive_sources(archive,directory,p['checksum'])
  packages.append(dict(name=p['name'],version=p['version'],archiveSha256=p['checksum'],sourceFiles=len(files),sourceManifestSha256=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()))
 reqwest=next(p for p in original if p['name']=='reqwest');directory=src/('reqwest-'+reqwest['version']);line=(directory/'src/lib.rs').read_text().splitlines()[281];assert line=='pub use url::Url;'
 archive_sources(cache/('reqwest-'+reqwest['version']+'.crate'),directory,reqwest['checksum'])
 cases=record('cases.json');native=record('native-cases.json');browser=record('browser.json');closed=record('browser-closure.json')
 assert native['complete'] and len(cases)==len(native['rows'])==34
 assert native['producerSha256']==sha(RUN/'cases.py')and native['binarySha256']==build['native']['sha256']
 guarded=(ROOT/'applications/empack/portable_document_cases.py').read_text();guard=" assert not (run/'native-cases.json').exists(),'Existing capture is immutable; use a new continuation capture.'\n";assert guarded.count(guard)==1 and guarded.replace(guard,'')==(RUN/'cases.py').read_text()
 assert sha(RUN/'browser-probe.mjs')==browser['producerSha256']
 guarded=(ROOT/'applications/empack/portable_document_browser.mjs').read_text();guard="assert(!existsSync(join(run,'browser.json')),'Existing browser capture is immutable; use a new continuation capture.');\n";assert guarded.count(guard)==1 and guarded.replace(guard,'')==(RUN/'browser-probe.mjs').read_text()
 assert browser['wasmSha256']==build['wasm']['sha256']and browser['serverClosed']and not browser.get('error')
 for name,digest in browser['sourceHashes'].items():
  live=ROOT/'applications/empack'/('document-portable'if name=='page.html'else'portable-core')/name;assert sha(live)==sha(RUN/('browser-'+name))==digest
 assert sha(Path(browser['package']['path']))==browser['package']['sha256']and sha(Path(browser['node']['path']))==browser['node']['sha256']
 assert not browser['node']['imports']and len(browser['profiles'])==2
 collections=[browser['node']['rows']]
 for p in browser['profiles']:
  assert p['contextClosed']and not p['errors']and not p['imports']and p['overLimitRefused']and len(p['rows'])==34;assert sha(Path(p['executable']))==p['executableSha256'];collections.append(p['rows'])
 reference=[(r['id'],r['status'],r['hex'])for r in native['rows']]
 for rows in collections:assert [(r['id'],r['status'],r['hex'])for r in rows]==reference
 assert closed['exitCode']==0 and closed['originalGroupAbsent']and not closed['workspaceProcessHits']
 out={}
 for c,r in zip(cases,native['rows'],strict=True):
  assert c['id']==r['id']and r['exitCode']==0 and r['groupAbsent']and r['status']==0
  packet=bytes.fromhex(c['packetHex']);assert hashlib.sha256(packet).hexdigest()==c['packetSha256']and json.loads(packet)==c['request']
  raw=(RUN/(c['id']+'.native.stdout')).read_bytes();assert raw.hex()==r['hex']and sha(RUN/(c['id']+'.native.stdout'))==r['stdoutSha256']and not (RUN/(c['id']+'.native.stderr')).read_bytes()
  v=json.loads(raw);out[c['id']]=v;assert v['ok']is c['expectedOk']
  if v['ok']:
   request=c['request'];assert v['raw']==hashlib.sha256(bytes.fromhex(request['author_hex'])).hexdigest();binding=request.get('bindings_hex');assert v['bindingsRevision']==(None if binding is None else hashlib.sha256(bytes.fromhex(binding)).hexdigest())
   assert v['inspection']['lock_status']=='missing'and v['inspection']['runtime_satisfied']is None
   if 'prepared'in v:
    p=v['prepared'];assert p['expectedRaw']==v['raw']and p['bindingsExpected']==v['bindingsRevision']and p['name']==request['rename']
    if p['edit']=='Unchanged':assert p['authorHex']==request['author_hex']and p['bindingsHex']==binding and p['semantic']==v['semantic']
    else:assert p['edit']=='Preserved'and p['semantic']!=v['semantic']
 baseline=out['minimal'];assert all(out[n]['semantic']==baseline['semantic']for n in ['comment-only','binding-empty','rename-noop'])
 assert out['comment-only']['raw']!=baseline['raw']and out['binding-empty']['bindingsRevision']is not None
 assert out['binding-seed']['semantic']==out['inline-seed']['semantic']!=baseline['semantic']
 assert bytes.fromhex(out['rename-preserve-comment']['prepared']['authorHex']).startswith(b'# keep me\n')
 assert out['local-missing-is-intent']['inspection']['dependencies'][0]['key']=='sample'
 # Preserve the initial prediction failure, not a rewritten successful run.
 partial=read(prior/'native-cases.json');assert not partial['complete']and len(partial['rows'])==22
 assert partial['producerSha256']==sha(prior/'cases.py')and partial['binarySha256']==build['native']['sha256']
 for row in partial['rows']:
  assert row['groupAbsent']and row['exitCode']==0 and sha(prior/(row['id']+'.native.stdout'))==row['stdoutSha256']
  assert (prior/(row['id']+'.native.stdout')).read_bytes().hex()==row['hex']and not (prior/(row['id']+'.native.stderr')).read_bytes()
 old=partial['rows'][-1];assert old['id']=='provider-pin'and not json.loads(bytes.fromhex(old['hex']))['ok']
 guard_review=record('collector-guard-review.json');assert guard_review['originalFilesUnchanged']and guard_review['noRecollection']and len(guard_review['guardChecks'])==2
 for name,digest in guard_review['originalFileHashes'].items():
  if name!='conformance.json':assert sha(RUN/name)==digest
 return cases,out,build,browser,packages
