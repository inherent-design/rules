#!/usr/bin/env python3
"""Independent retained bytes, preview, lock, and fresh-runtime observations."""
import base64,copy,gzip,hashlib,io,json,re,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
RUNS=[ROOT/'applications/evidence'/name for name in ['js-dedupe-20261125T120841191141Z','js-dedupe-20261125T121049582647Z']]
LEAF='rules-dedupe-leaf';FLEX='rules-dedupe-flex';FIXED='rules-dedupe-fixed';B='rules-dedupe-later'
sha=lambda b:hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_text())
def version(v):assert v in ['1.0.0','1.1.0','1.2.0'];return ['1.0.0','1.1.0','1.2.0'].index(v)+1
def selected(values,first):return dict(left=version(values[first]['value']['version']),right=version(values[B]['value']['version']),copies=len({values[first]['leaf'],values[B]['leaf']}))
def preview(manager,text,before,first):
 target={name:dict(version=v['value']['version'],path=str(Path(v['leaf']).parent))for name,v in before.items()}
 if manager=='npm':
  report=json.loads(text)
  for change in report['change']:
   assert change['from']['name']==change['to']['name']==LEAF
   matched=[n for n,v in target.items()if v['path']==change['from']['path']];assert matched
   for n in matched:assert target[n]['version']==change['from']['version'];target[n]=dict(version=change['to']['version'],path=change['to']['path'])
  if report['add']or report['remove']:
   assert len(report['add'])==1 and report['add'][0]['name']==LEAF;addition=report['add'][0];removed={v['path']:v for v in report['remove']};assert set(removed)=={v['path']for v in target.values()}
   for n,v in target.items():assert v['version']==removed[v['path']]['version'];target[n]=dict(version=addition['version'],path=addition['path'])
 elif manager=='yarn':
  pattern=re.escape(LEAF)+r'@npm:(\S+) can be deduped from '+re.escape(LEAF)+r'@npm:(\S+) to '+re.escape(LEAF)+r'@npm:(\S+)'
  for constraint,old,new in re.findall(pattern,text):
   name=first if constraint==('1.0.0'if first==FIXED else'^1.0.0')else B;assert constraint==('^1.1.0'if name==B else'1.0.0'if first==FIXED else'^1.0.0');assert target[name]['version']==old;target[name]=dict(version=new,path='proposed:'+new)
 else:
  pattern=r'(rules-dedupe-(?:flex|fixed|later))@1\.0\.0\n└── '+re.escape(LEAF)+r' (\S+) → (\S+)'
  for name,old,new in re.findall(pattern,text):assert target[name]['version']==old;target[name]=dict(version=new,path='proposed:'+new)
 # For the controlled two-parent profiles, same version means one ordinary
 # context after linking. No peers, aliases, overrides, or virtual contexts.
 return dict(left=version(target[first]['version']),right=version(target[B]['version']),copies=1 if target[first]['version']==target[B]['version']else 2)
def lock_versions(manager,body,values,first,project):
 if manager=='npm':
  d=json.loads(body)
  return {name:version(d['packages'][str(Path(v['leaf']).parent.relative_to(project))]['version'])for name,v in values.items()}
 if manager=='pnpm':
  text=body.decode().split('snapshots:\n',1)[1];out={}
  for name in [first,B]:
   m=re.search(r'^  '+re.escape(name)+r'@1\.0\.0:\n    dependencies:\n      '+LEAF+r': ([^\n]+)',text,re.M);assert m;out[name]=version(m[1])
  return out
 text=body.decode();resolved={}
 for descriptors,v in re.findall(r'^"([^\n]+)":\n  version: ([^\n]+)',text,re.M):
  for descriptor in descriptors.split(', '):
   if descriptor.startswith(LEAF+'@npm:'):resolved[descriptor.split('@npm:',1)[1]]=version(v)
 return {first:resolved['1.0.0'if first==FIXED else'^1.0.0'],B:resolved['^1.1.0']}
def inspect(overrides=None):
 rows=[];basis={};source_rows=read(ROOT/'applications/sources/js-dedupe-selections.json')
 for source in source_rows:
  p=ROOT/source['cache'];raw=p.read_bytes();assert sha(raw)==source['sha256']
  if 'installed'in source:assert Path(source['installed']).read_bytes()==raw
 for run in RUNS:
  receipt=read(run/'receipt.json');commands=overrides[run.name]if overrides and run.name in overrides else read(run/'commands.json');assert receipt['error']is None and receipt['serverClosed']and receipt['allChildrenTerminal']and receipt['commands']==len(commands)
  assert receipt['producerSha256']==sha((run/'probe.py').read_bytes())
  for name,pin in receipt['pins'].items():assert sha(Path(pin['path']).read_bytes())==pin['sha256']
  for filename,p in receipt['archives'].items():
   payload=(run/'archives'/filename).read_bytes();assert sha(payload)==p['sha256']and p['integrity']=='sha512-'+base64.b64encode(hashlib.sha512(payload).digest()).decode();assert hashlib.sha1(payload).hexdigest()==p['shasum']
   with tarfile.open(fileobj=io.BytesIO(payload),mode='r:gz')as t:
    files={}
    for member in t:
     assert member.isfile()and member.mode==0o644 and member.mtime==0 and member.name.startswith('package/');body=t.extractfile(member).read();files[member.name.removeprefix('package/')]=dict(bytes=len(body),sha256=sha(body))
    assert files==p['files']
  for request in read(run/'requests.json'):
   body=(run/request['response']).read_bytes();assert sha(body)==request['sha256']and not request['authorizationPresent']
   if request['status']!=200:
    assert request['status']==404 and request['path']=='/pnpm'and request['case'].startswith('pnpm-')and request['case'].endswith(('seed','add-later'))and json.loads(body)==dict(error='owned_fixture_not_found');continue
   if request['response'].endswith('.json'):
    metadata=json.loads(body)
    for v,p in metadata['versions'].items():assert p['dist']['integrity']==receipt['archives'][metadata['name']+'-'+v+'.tgz']['integrity']and p['dist']['tarball'].startswith(receipt['origin']+'/')
  for c in commands:
   assert c['exitCode']in [0,1]and c['groupAbsent']and not c['timedOut']
   for stream in c['streams'].values():assert sha((run/stream['path']).read_bytes())==stream['sha256']
   for image in [c['before'],c['after']]:
    for p,info in image.items():
     if 'link'in info:continue
     body=(run/info['captured']).read_bytes();assert sha(body)==info['sha256']and len(body)==info['bytes']
   if c['kind']=='fresh-node-observer':assert c['before']==c['after']and not c['requests']
  groups={(c['manager'],c['profile'])for c in commands}
  for manager,profile in sorted(groups):
   group={c['case']:c for c in commands if c['manager']==manager and c['profile']==profile};assert len(group)==7
   first=FLEX if profile=='overlap'else FIXED;before=json.loads((run/group['before']['streams']['stdout']['path']).read_text());after=json.loads((run/group['after']['streams']['stdout']['path']).read_text());old=selected(before,first);new=selected(after,first);project=Path(receipt['work'])/(manager+'-'+profile)/'project';key={'npm':'package-lock.json','pnpm':'pnpm-lock.yaml','yarn':'yarn.lock'}[manager]
   for values,image in [(before,group['before']['before']),(after,group['after']['before'])]:
    for name,v in values.items():assert v['manifest']['name']==LEAF and v['manifest']['version']==v['value']['version'];assert sha(v['source'].encode())==receipt['archives'][LEAF+'-'+v['value']['version']+'.tgz']['files']['index.js']['sha256']
    locked=lock_versions(manager,(run/image[key]['captured']).read_bytes(),values,first,project);assert locked=={name:version(v['value']['version'])for name,v in values.items()}
   before_plan=preview(manager,(run/group['check-before']['streams']['stdout']['path']).read_text(),before,first);assert before_plan==new,(manager,profile,before_plan,new)
   for case in ['check-before','apply','check-after']:
    c=group[case];check=case!='apply';current=old if case!='check-after'else new;proposed=before_plan if case!='check-after'else preview(manager,(run/c['streams']['stdout']['path']).read_text(),after,first);assert c['before']['package.json']==c['after']['package.json'];assert c['registryStage']==2
    if check:assert c['before']==c['after']
    selection_changed=(old['left'],old['right'])!=(new['left'],new['right']);placement_changed=old['copies']!=new['copies'];manifest_changed=c['before']['package.json']!=c['after']['package.json']
    if case=='apply':assert (c['before'][key]!=c['after'][key])==selection_changed
    observed={**(current if check else new),'status':c['exitCode'],'selectionChanged':False if check else selection_changed,'placementChanged':False if check else placement_changed,'manifestChanged':manifest_changed}
    rows.append(dict(id=run.name+'/'+manager+'/'+profile+'/'+case,input=dict(npmStyle=manager=='npm',check=check,**current,targetLeft=proposed['left'],targetRight=proposed['right'],targetCopies=proposed['copies'],allowedLeft=[1]if first==FIXED else[1,2,3],allowedRight=[2,3]),observed=observed,source=dict(run=str(run.relative_to(ROOT)),case=case,manager=manager,profile=profile,preview='check-before'if case!='check-after'else case),changedFiles=[p for p in set(c['before'])|set(c['after'])if c['before'].get(p)!=c['after'].get(p)]))
  for p in run.rglob('*'):
   if p.is_file()and p.name not in ['conformance.json','qualification.json']:basis[str(p.relative_to(ROOT))]=sha(p.read_bytes())
 assert len(rows)==21
 return rows,basis
if __name__=='__main__':
 rows,basis=inspect();print(json.dumps(dict(nativeBoundaries=len(rows),basisFiles=len(basis),readOnly=True)))
