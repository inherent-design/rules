#!/usr/bin/env python3
"""Read-only source/artifact/backend observer. Never launches a studied program."""
import hashlib,json,subprocess,tomllib,zipfile
from pathlib import Path
from portable_document_observations import archive_sources
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
RUN=ROOT/'applications/evidence/empack-joined-flow-20261125T113211837178Z'
BUILD=ROOT/'applications/evidence/empack-joined-20261125T111512569488Z'
sha=lambda b:hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_text())
def image(d):
 # Rust struct serialization order, independent of serde_json::Value map order.
 def asset(a):return None if a is None else {k:a[k]for k in ['id','sha256','bytes','original_name']}
 entries=[{**{k:e[k]for k in ['source','destination','layer','permissions']},'asset':asset(e['asset'])}for e in d['entries']]
 ordered={**{k:d[k]for k in ['schema','author_hex','bindings_hex']},'entries':entries}
 return sha(b'rules.empack.joined-study.image.v1\0'+json.dumps(ordered,ensure_ascii=False,separators=(',',':')).encode())
def snapshot(wire):
 s=json.loads(wire);assert s['format']=='rules.empack.joined-study'and s['schema']==1 and s['image']==image(s['draft']);return s
def inventory(path):
 with zipfile.ZipFile(path)as z:
  assert z.testzip()is None;names=[i.filename for i in z.infolist()];assert len(names)==len(set(names));rows=[]
  for i in z.infolist():
   assert i.create_system==3 and not i.flag_bits&1
   assert (i.external_attr>>16)&0o170000 in [0o040000,0o100000]
   if i.is_dir():assert (i.external_attr>>16)&0o777==0o755;continue
   rows.append(dict(path=i.filename,bytes=i.file_size,sha256=sha(z.read(i)),mode=(i.external_attr>>16)&0o777))
  return sorted(rows,key=lambda r:r['path'])
def inspect(overrides=None):
 def record(n):return overrides[n]if overrides and n in overrides else read(RUN/n)
 build=read(BUILD/'build.json');work=Path(build['work']);repo=ROOT.parent/'empack'
 assert build['heldUnchanged']and len(build['commands'])==2
 for c in build['commands']:
  assert c['exitCode']==0 and c['groupAbsent']
  for stream in ['stdout','stderr']:assert sha((BUILD/(c['label']+'.'+stream)).read_bytes())==c[stream+'Sha256']
 for key in ['native','wasm']:
  p=Path(build[key]['path']);assert p.stat().st_size==build[key]['bytes']and sha(p.read_bytes())==build[key]['sha256']
 for p,h in build['heldArtifacts'].items():assert sha(Path(p).read_bytes())==h
 assert sha((BUILD/'build.py').read_bytes())==build['producerSha256']==sha((HERE/'portable_joined_build.py').read_bytes())
 assert (BUILD/'lib.rs').read_bytes()==(HERE/'joined-study/lib.rs').read_bytes()==(work/'src/lib.rs').read_bytes()
 assert (BUILD/'main.rs').read_text()==(HERE/'joined-study/main.rs').read_text().replace('rules_joined_study::',build['libname']+'::')
 originals={}
 for pin in build['sourcePins']:
  raw=subprocess.check_output(['git','-C',str(repo),'show',build['revision']+':'+pin['path']]);assert sha(raw)==pin['sha256'];originals[pin['path']]=raw
 for f in build['fragments']:assert sha(originals[f['path']].decode()[f['start']:f['end']].encode())==f['sha256']
 for p,raw in originals.items():
  if '/documents' in p or p.endswith('/layout.rs')or p.endswith('/runtime_versions.rs')or p.endswith('/templates/encoding.rs'):
   assert (work/'src/engine'/Path(p).relative_to('crates/empack-lib/src/engine')).read_bytes()==raw
  if p.endswith('instance.cfg.template'):assert(work/'src/engine/instance.cfg.template').read_bytes()==raw
 assert (work/'src/engine/prism.rs').read_bytes()==originals['crates/empack-lib/src/engine/prism.rs'][:build['fragments'][0]['end']]
 # Pin every selected registry archive/source; no dependency upgrade is assumed.
 selected=tomllib.loads((BUILD/'Cargo.lock').read_text())['package'];original=tomllib.loads(originals['Cargo.lock'].decode())['package'];old={(p['name'],p['version']):p for p in original};packages=[]
 cache=Path('/Users/zer0cell/.cargo/registry/cache/index.crates.io-1949cf8c6b5b557f');src=cache.parents[1]/'src/index.crates.io-1949cf8c6b5b557f'
 assert sha((BUILD/'Cargo.lock').read_bytes())==build['selectedLockSha256']==sha((work/'Cargo.lock').read_bytes())
 for p in selected:
  if 'checksum'not in p:continue
  assert p['checksum']==old[(p['name'],p['version'])]['checksum'];name=p['name']+'-'+p['version'];files=archive_sources(cache/(name+'.crate'),src/name,p['checksum']);packages.append(dict(name=name,sourceFiles=len(files),archiveSha256=p['checksum']))
 core=Path(read(ROOT/build['reusedBuild']['capture']/'build.json')['work'])/'core'
 for p in subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only',build['revision'],'crates/empack-core/src'],text=True).splitlines():
  raw=subprocess.check_output(['git','-C',str(repo),'show',build['revision']+':'+p]);assert raw==(core/Path(p).relative_to('crates/empack-core')).read_bytes()
 bindgen=read(BUILD/'bindgen.json');assert bindgen['exitCode']==0 and bindgen['rawWasmSha256']==build['wasm']['sha256']
 for item in [bindgen['archive'],*bindgen['members'],*bindgen['outputs']]:assert sha(Path(item['path']).read_bytes())==item['sha256']
 smoke=read(BUILD/'smoke.json');node=read(BUILD/'node-smoke.json');smoke_frames=read(BUILD/'native-smoke.frames.json')
 assert len(smoke_frames)==len(node['rows'])==24 and smoke['streamChunks']==7 and smoke['closed']['exitCode']==0 and smoke['closed']['groupAbsent']
 assert smoke['producerSha256']==sha((BUILD/'smoke.py').read_bytes())==sha((HERE/'portable_joined_smoke.py').read_bytes())
 for f,row in zip(smoke_frames,node['rows'],strict=True):assert sha(bytes.fromhex(f['request']))==row['requestSha256']and sha(bytes.fromhex(f['response']))==row['resultSha256']
 assert sha(Path(node['binary']).read_bytes())==node['binarySha256']and node['processedWasmSha256']==bindgen['outputs'][1]['sha256']
 native=record('native.json');browser=record('browser.json');probe=record('backend-probe.json');reference=record('installed-reference.json');frames=record('native-frames.json')
 assert not native['error']and len(native['events'])==13 and len(native['artifacts'])==4 and native['events']==read(RUN/'native-events.json')
 assert browser['processedWasmSha256']==bindgen['outputs'][1]['sha256']and browser['glueSha256']==bindgen['outputs'][0]['sha256']
 assert all(c['exitCode']==0 and c['groupAbsent']and not c['stderr']and not c['unread']for c in native['closed'])
 assert sha((RUN/'native.py').read_bytes())==native['producerSha256']==sha((HERE/'portable_joined_native.py').read_bytes())
 assert sha((RUN/'peer.py').read_bytes())==native['peerSha256']==sha((HERE/'joined-study/peer.py').read_bytes())
 for name,digest in browser['sourceHashes'].items():
  assert sha((RUN/('browser-'+name)).read_bytes())==digest
  if name!='page.html':assert sha((HERE/'joined-study'/name).read_bytes())==digest
 assert browser['producerSha256']==sha((RUN/'browser.mjs').read_bytes())and browser['serverClosed']and not browser.get('error')
 frozen=(RUN/'browser.mjs').read_text();maintained=(HERE/'portable_joined_browser.mjs').read_text();assert maintained==frozen.replace("'page.mjs','page.html']","'page.mjs','page.html','style.css']").replace("req.url==='/'?'text/html; charset=utf-8':'text/javascript; charset=utf-8'","req.url==='/'?'text/html; charset=utf-8':req.url.endsWith('.css')?'text/css; charset=utf-8':'text/javascript; charset=utf-8'")
 assert probe['complete']and probe['serverClosed']and len(probe['rows'])==2 and probe['producerSha256']==sha((RUN/'backend-probe.mjs').read_bytes())
 for name,digest in probe['hashes'].items():assert sha((RUN/('probe-'+name)).read_bytes())==digest==sha((HERE/'joined-study'/name).read_bytes())
 old=(RUN/'browser-page.html').read_text();new=(RUN/'probe-page.html').read_text();a=old.index('<style>');b=old.index('</style>');assert new==old[:a]+'<link rel="stylesheet" href="/style.css">'+old[b+8:];assert(RUN/'probe-style.css').read_text()==old[a+7:b]+'\n'
 work=Path(native['work']);all_artifacts=[];main=next(a for a in native['artifacts']if a['label']=='main')
 for a in native['artifacts']:
  p=Path(a['path']);assert sha(p.read_bytes())==a['ready']['sha256']and p.stat().st_size==a['ready']['bytes'];assert inventory(p)==sorted(a['actualInventory'],key=lambda r:r['path'])==sorted(a['ready']['inventory'],key=lambda r:r['path']);all_artifacts.append(p)
 mainbytes=Path(main['path']).read_bytes()
 native_root=read(work/'root.json');assert native_root['revision']=='2'and snapshot(native_root['wire'])['image']==main['ready']['basis']
 with zipfile.ZipFile(Path(main['path']))as z:
  assert z.read('.minecraft/config/renamed Ω 日本.json')==(work/'rules.json').read_bytes()and b'{{ NAME }}'in z.read('.minecraft/config/renamed Ω 日本.json')
  assert z.read('.minecraft/mods/Sample Ω 日本.jar')==(work/'source.jar').read_bytes()
  assert json.loads(z.read('mmc-pack.json'))==dict(formatVersion=1,components=[dict(uid='net.minecraft',version='1.21.1',important=True)])
 for p,row in zip(browser['profiles'],probe['rows'],strict=True):
  assert p['complete']and len(p['events'])==11 and p['contextClosures']==[True,True]and not p['errors'];assert sha(Path(p['executable']).read_bytes())==p['executableSha256']
  assert p['engine']==row['engine']and row['before']==row['after'];assert {k:row['before'][k]for k in ['root','history']}==p['backend'];assert row['before']['root']['revision']=='3'and len(row['before']['history'])==3
  for h in row['before']['history']:snapshot(h['wire'])
  for e in p['events']:
   v=e['state']['current'];assert v['image']==image(v['draft'])
  first=p['events'][1]['state'];assert not first['current']['interpretation']['valid']and first['current']['draft']['entries'][-1]['asset']is None and first['saved']['revision']=='1'
  later=p['events'][5]['state'];captured=p['events'][6];assert later['current']['image']!=later['saved']['image']==captured['exported']['basis'];assert captured['state']['current']['image']==later['current']['image']
  pre=p['events'][8]['state'];post=p['events'][9];assert pre['saved']['revision']=='2'and post['state']['saved']['revision']=='3'and 'may have committed'in post['lost']['error'];assert post['state']['saved']['image']==later['current']['image']
  assert p['events'][-1]['xss']==dict(images=0,executed=False)
  objects={o['name']:o for o in row['before']['objects']};assert len(objects)==2
  for h in row['before']['history']:
   for e in snapshot(h['wire'])['draft']['entries']:
    if e['asset']:
     a=e['asset'];assert objects['source-'+a['id']]['bytes']==a['bytes']and objects['source-'+a['id']]['sha256']==a['sha256']
  for d in p['downloads']:
   path=Path(d['path']);assert path.read_bytes()==mainbytes and sha(path.read_bytes())==d['sha256']and d['failure']is None;assert inventory(path)==sorted(main['actualInventory'],key=lambda r:r['path']);all_artifacts.append(path)
  for field in ['screenshot']:
   assert sha(Path(p[field]).read_bytes())==p[field+'Sha256']and sha(Path(row[field]).read_bytes())==row[field+'Sha256']
 assert reference['complete']and reference['semanticMatch']and all(c['exitCode']==0 and c['groupAbsent']for c in reference['commands'])
 assert sha(Path(reference['binary']).read_bytes())==reference['binarySha256'];assert inventory(Path(reference['artifact']['path']))==sorted(main['actualInventory'],key=lambda r:r['path']);all_artifacts.append(Path(reference['artifact']['path']))
 assert read(RUN/'browser-closure.json')['originalGroupAbsent']and not read(RUN/'browser-closure.json')['workspaceProcessHits']
 for peer in frames:
  for f in peer['frames']:
   q=json.loads(bytes.fromhex(f['request']));r=json.loads(bytes.fromhex(f['response']));assert q['schema']==1 and isinstance(r['ok'],bool)
 return dict(native=native,browser=browser,probe=probe,frames=frames,packages=packages,artifacts=all_artifacts,build=build)
if __name__=='__main__':
 d=inspect();print(json.dumps(dict(registryArchives=len(d['packages']),registryFiles=sum(p['sourceFiles']for p in d['packages']),nativeEvents=len(d['native']['events']),browserEvents=sum(len(p['events'])for p in d['browser']['profiles']),artifacts=len(d['artifacts']),readOnly=True)))
