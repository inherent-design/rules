#!/usr/bin/env python3
"""Execute current native core over owned metadata vectors; write exact packets."""
import copy,hashlib,json,os,struct,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def packet(records,recipe=0,policy=2):
 out=bytearray(b'RPI1'+bytes([recipe,policy])+struct.pack('<I',len(records)))
 for r in records:
  path=r['path'].encode();out+=struct.pack('<I',len(path))+path+bytes([r['layer'],r['client'],r['server'],r['representation'],r['permissions']])+struct.pack('<Q',r['bytes'])+bytes.fromhex(r['sha256'])
 return bytes(out)
def main():
 run=Path(sys.argv[1]).resolve();assert run.parent==ROOT/'applications/evidence';build=json.loads((run/'build.json').read_text());work=Path(build['work']);assert 'wasm'in build
 (run/'cases.py').write_bytes(Path(__file__).read_bytes());src=ROOT/'applications/evidence/empack-portable-storage-20261124T222835992Z/work/inputs/Sample Ω 日本.jar';jar=src.read_bytes();config='{"message":"local Ω 日本"}\n'.encode();(work/'inputs').mkdir();(work/'inputs/sample.jar').write_bytes(jar);(work/'inputs/rules.json').write_bytes(config)
 inputs=dict(jar=dict(priorPath=str(src),sha256=sha(jar),bytes=len(jar)),config=dict(sha256=sha(config),bytes=len(config)))
 def entry(path,body=config,layer=0,client=1,server=1,representation=0,permissions=0):return dict(path=path,layer=layer,client=client,server=server,representation=representation,permissions=permissions,bytes=len(body),sha256=sha(body))
 base=[entry('mods/Sample Ω 日本.jar',jar),entry('config/rules.json')];cases=[]
 def add(id,records,recipe=0,policy=2,expected='ok',note=''):
  p=packet(records,recipe,policy);cases.append(dict(id=id,records=records,recipe=recipe,policy=policy,expected=expected,note=note,packetHex=p.hex(),packetSha256=sha(p)))
 add('local-jar-config',base);add('server-view',base,1);add('native-layers',base,2,0)
 layers=[entry('config/rules.json',b'base'),entry('config/rules.json',b'override',1),entry('config/rules.json',b'client',2,1,0),entry('config/rules.json',b'server',3,0,1)]
 add('client-precedence',layers);add('server-precedence',layers,1);add('preserved-layers',layers,2,0)
 add('duplicate-layer',[base[1],base[1]],expected='DuplicateDestination')
 add('invalid-client-environment',[entry('config/x',layer=2,server=1)],expected='InvalidEnvironment')
 add('missing-known-size',[entry('mods/missing.jar',representation=1)],expected='MaterializationRequired',note='Explicit known expected length,not an unknown size encoded as zero.')
 for default in[False,True]:
  add('optional-default-'+str(default).lower(),[entry('mods/extra.jar',client=3 if default else 2,server=0)],policy=1)
 add('optional-needs-choice',[entry('mods/extra.jar',client=2,server=0)],expected='ChoiceRequired')
 add('side-disabled-fallback',[entry('config/fallback.cfg'),entry('config/fallback.cfg',layer=2,client=2,server=0)],policy=1)
 add('hidden-missing-fallback',[entry('config/fallback.cfg',representation=1),entry('config/fallback.cfg',layer=2,client=1,server=0)])
 add('permissions',[entry('config/read-only.cfg',permissions=1),entry('tools/runner',permissions=2)])
 add('empty-file',[entry('config/empty',b'')])
 add('case-alias-core-only',[entry('config/Rules.json'),entry('config/rules.json')],note='Core succeeds;native layout has an additional portable collision gate. Not export authority.')
 add('unicode-alias-core-only',[entry('config/é.cfg'),entry('config/e\u0301.cfg')],note='Core succeeds;native collision_key canonical Unicode caseless comparison is a separate engine obligation.')
 forged=copy.deepcopy(base);forged[0]['sha256']='00'*32;add('forged-observation-core-only',forged,note='Core accepts caller observations;not verification of actual source bytes.')
 for n,path in enumerate(['../escape','/absolute','C:/drive','config/NUL.txt','config/x.','config//x','config/bad\x00name','config/back\\slash']):add('bad-path-'+str(n),[entry(path)],expected='path:')
 for id,mut in[('bad-version',lambda p:b'RPI2'+p[4:]),('truncated',lambda p:p[:-1]),('trailing',lambda p:p+b'x'),('bad-recipe',lambda p:p[:4]+b'\x09'+p[5:]),('bad-utf8',lambda p:p[:14]+b'\xff'+p[15:])]:
  p=mut(packet(base));cases.append(dict(id=id,records=[],recipe=0,policy=2,expected='wire:',note='Malformed research wire;not an empack schema/API input.',packetHex=p.hex(),packetSha256=sha(p)))
 write(run/'cases.json',cases);write(run/'inputs.json',inputs);rows=[];env=dict(PATH='/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8')
 for c in cases:
  start=time.monotonic();p=subprocess.run([build['native']['path']],input=bytes.fromhex(c['packetHex']),env=env,capture_output=True,timeout=5);assert p.returncode==0,p.stderr.decode();status,length=struct.unpack('<II',p.stdout[:8]);body=p.stdout[8:];assert len(body)==length
  (run/(c['id']+'.native.stdout')).write_bytes(p.stdout);(run/(c['id']+'.native.stderr')).write_bytes(p.stderr)
  if c['expected']=='ok':assert status==0,(c['id'],body)
  else:assert status==1 and c['expected']in body.decode(),(c['id'],body)
  rows.append(dict(id=c['id'],status=status,hex=body.hex(),seconds=time.monotonic()-start,exitCode=p.returncode,stdoutSha256=sha(p.stdout)))
 write(run/'native-cases.json',dict(schema=1,rows=rows,producerSha256=sha((run/'cases.py').read_bytes()),sourceInputSha256=sha(src.read_bytes()),limits='Metadata selection only;no project interpretation,byte verification,consumer codec or publication.'))
 print(json.dumps(dict(cases=len(cases),run=str(run))))
if __name__=='__main__':main()
