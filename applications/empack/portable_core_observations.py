#!/usr/bin/env python3
"""Pure retained native/WASM/browser metadata-plan observer; no core execution."""
import hashlib,json,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUN=ROOT/'applications/evidence/empack-portable-core-20261125T095721300368Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
class Reader:
 def __init__(self,b):self.b=b;self.p=0
 def take(self,n):
  assert n>=0 and self.p+n<=len(self.b);r=self.b[self.p:self.p+n];self.p+=n;return r
 def byte(self):return self.take(1)[0]
 def u32(self):return struct.unpack('<I',self.take(4))[0]
 def u64(self):return struct.unpack('<Q',self.take(8))[0]
 def text(self):
  n=self.u32();assert n<=1024;return self.take(n).decode('utf-8')
 def requirement(self):
  n=self.byte();assert n<=2
  if n==2:
   key=self.text();default=self.byte();assert default<=1;return dict(code=3 if default else 2,key=key,default=bool(default))
  return dict(code=n)
def decode(row):
 if row['status']:
  assert row['status']==1;return dict(error=bytes.fromhex(row['hex']).decode('utf-8'))
 r=Reader(bytes.fromhex(row['hex']));assert r.take(4)==b'RPO1';count,precedence,choices=r.u32(),r.u32(),r.u32();assert count<=32 and precedence<=128 and choices<=32;entries=[]
 for _ in range(count):
  e=dict(owner=r.u32(),path=r.text(),layer=r.byte(),bytes=r.u64(),sha256=r.take(32).hex(),permissions=r.byte());e['client']=r.requirement();e['server']=r.requirement();assert e['owner']<32 and e['layer']<=3 and e['permissions']<=3;entries.append(e)
 previous=[dict(path=r.text(),replaced=r.u32(),replacement=r.u32())for _ in range(precedence)];decisions=[]
 for _ in range(choices):
  key=r.text();bits=[r.byte()for _ in range(3)];assert all(b<=1 for b in bits);decisions.append(dict(key=key,default=bool(bits[0]),enabled=bool(bits[1]),usedDefault=bool(bits[2])))
 assert r.p==len(r.b);return dict(entries=entries,precedence=previous,choices=decisions)
def request(case):
 r=Reader(bytes.fromhex(case['packetHex']));assert r.take(4)==b'RPI1';recipe,policy,count=r.byte(),r.byte(),r.u32();records=[]
 assert count<=32
 for _ in range(count):
  row=dict(path=r.text(),layer=r.byte(),client=r.byte(),server=r.byte(),representation=r.byte(),permissions=r.byte(),bytes=r.u64(),sha256=r.take(32).hex());records.append(row)
 assert r.p==len(r.b)
 assert (recipe,policy,records)==(case['recipe'],case['policy'],case['records'])
def inspect(overrides=None):
 def record(name):return overrides[name] if overrides and name in overrides else read(RUN/name)
 build=record('build.json');work=Path(build['work']);assert len(build['commands'])==4 and all(c['exitCode']==0 for c in build['commands'])
 for name in['native','wasm']:
  assert sha(Path(build[name]['path']))==build[name]['sha256']
  assert sha(work/('libempack_core_'+name+'.rlib'))==build[name]['coreRlibSha256']
 assert sha(Path(build['tool']['path']))==build['tool']['sha256']
 assert sha(RUN/'build.py')==build['producerSha256']==sha(ROOT/'applications/empack/portable_core_build.py')
 assert sha(RUN/'engine.rs')==build['adapterSha256']==sha(ROOT/'applications/empack/portable-core/engine.rs')
 repo=ROOT.parent/'empack'
 for pin in build['sourcePins']:
  raw=subprocess.check_output(['git','-C',str(repo),'show',build['revision']+':'+pin['path']]);assert hashlib.sha256(raw).hexdigest()==pin['sha256'];relative=Path(pin['path']).relative_to('crates/empack-core/src');assert (work/'core'/relative).read_bytes()==raw
 cases=record('cases.json');native=record('native-cases.json');node=record('node-cases.json');browser=record('browser.json');closed=record('browser-closure.json')
 assert native['producerSha256']==sha(RUN/'cases.py')==sha(ROOT/'applications/empack/portable_core_cases.py')
 assert len(cases)==len(native['rows'])==len(node['rows'])==32 and not node['imports']
 assert closed['exitCode']==0 and closed['originalGroupAbsent'] and not closed['workspaceProcessHits']
 assert browser['serverClosed'] and not browser.get('error') and len(browser['profiles'])==2
 assert browser['wasmSha256']==build['wasm']['sha256'] and browser['producerSha256']==sha(RUN/'browser-probe.mjs')==sha(ROOT/'applications/empack/portable_core_browser.mjs')
 for name,hash in browser['sourceHashes'].items():assert sha(ROOT/'applications/empack/portable-core'/name)==hash==sha(RUN/('browser-'+name))
 assert sha(Path(browser['package']['path']))==browser['package']['sha256']
 collections=[node['rows']]
 for p in browser['profiles']:
  assert p['contextClosed'] and not p['errors'] and not p['imports'] and p['overLimitRefused'] and len(p['rows'])==32
  assert sha(Path(p['executable']))==p['executableSha256'];collections.append(p['rows'])
 reference=[(r['id'],r['status'],r['hex'])for r in native['rows']]
 for rows in collections:assert [(r['id'],r['status'],r['hex'])for r in rows]==reference
 outputs={}
 for case,row in zip(cases,native['rows'],strict=True):
  assert row['exitCode']==0 and not (RUN/(row['id']+'.native.stderr')).read_bytes()
  if case['records']:request(case)
  assert case['id']==row['id'] and hashlib.sha256(bytes.fromhex(case['packetHex'])).hexdigest()==case['packetSha256'];raw=(RUN/(row['id']+'.native.stdout')).read_bytes();status,length=struct.unpack('<II',raw[:8]);assert status==row['status'] and len(raw)-8==length and raw[8:].hex()==row['hex'] and sha(RUN/(row['id']+'.native.stdout'))==row['stdoutSha256']
  result=decode(row);outputs[row['id']]=result
  if case['expected']=='ok':assert row['status']==0
  else:assert row['status']==1 and case['expected']in result['error']
  if 'entries'in result:
   for e in result['entries']:
    source=case['records'][e['owner']];assert (e['path'],e['bytes'],e['sha256'],e['permissions'])==(source['path'],source['bytes'],source['sha256'],source['permissions'])
 inputs=record('inputs.json');assert sha(work/'inputs/sample.jar')==inputs['jar']['sha256'] and sha(work/'inputs/rules.json')==inputs['config']['sha256']
 base=outputs['local-jar-config'];assert {e['path']for e in base['entries']}=={'mods/Sample Ω 日本.jar','config/rules.json'}
 assert all(e['client']['code']==1 and e['server']['code']==0 for e in base['entries'])
 for name in['case-alias-core-only','unicode-alias-core-only']:assert len(outputs[name]['entries'])==2
 assert next(e for e in outputs['forged-observation-core-only']['entries']if e['path'].startswith('mods/'))['sha256']=='00'*32
 for fail in['empack-portable-core-20261125T095419598124Z','empack-portable-core-20261125T095506142124Z']:
  d=ROOT/'applications/evidence'/fail;assert read(d/'unrun.json')['nativeCases']==0
 return cases,outputs,build,browser
