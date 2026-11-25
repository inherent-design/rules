#!/usr/bin/env python3
"""Pure retained-data replay; never compiles Rust or launches an application."""
import copy,hashlib,json,os,subprocess
from pathlib import Path
import portable_joined_observations as O
ROOT,HERE,RUN=O.ROOT,O.HERE,O.RUN
def main():
 d=O.inspect();labels={}
 def label(v):
  if v is None:return 0
  if v not in labels:labels[v]=len(labels)+1
  return labels[v]
 rows=[];states={};views={};rawbytes={a['ready']['sha256']:Path(a['path']).read_bytes()for a in d['native']['artifacts']}
 for peer in d['frames']:
  for index,f in enumerate(peer['frames']):
   q=json.loads(bytes.fromhex(f['request']));out=json.loads(bytes.fromhex(f['response']));action=q['action'];value=out.get('value',{})
   if out['ok']and 'draft'in value:views[value['image']]=value['interpretation']['valid']
   if action=='status':
    s=states.get(q['id'],dict(phase=0));assert value['export']=={0:'absent',1:'writing',2:'writing',3:'ready'}[s['phase']];continue
   if action not in ['export-begin','export-feed','export-verify','artifact-read','cancel']:continue
   s=states.setdefault(q['id'],dict(phase=0,basis=0,files=[],offset=0,index=0,data=b''));before=copy.deepcopy(s);a=['export-begin','export-feed','export-verify','artifact-read','cancel'].index(action);gate=True;finished=False;capture=0;measured=[3];observed={3:out['ok']}
   if a==0:
    draft=q['draft'];capture=label(O.image(draft));selected=sorted([e for e in draft['entries']if e['layer']!=3],key=lambda e:e['destination']);paths=[e['destination'].casefold()for e in selected];gate=views[O.image(draft)]and O.image(draft)==q['expected_image']and all(e['asset']is not None for e in selected)and len(paths)==len(set(paths))
    s['files']=[e['asset']for e in selected if e['asset']and e['asset']['bytes']];s.update(offset=0,index=0,data=b'');finished=not s['files']
   elif a==1:
    ref=s['files'][s['index']];body=bytes.fromhex(q['hex']);gate=q['asset_id']==ref['id']and q['offset']==s['offset']and 0<len(body)<=16384 and len(body)+s['offset']<=ref['bytes'];s['data']+=body;s['offset']+=len(body)
    if s['offset']==ref['bytes']:
     gate=gate and O.sha(s['data'])==ref['sha256'];s.update(index=s['index']+1,offset=0,data=b'')
    finished=s['index']==len(s['files'])
   elif a==2:gate=q.get('fault')is None
   elif a==3:
    gate=before['phase']==3 and q['offset']<=s['bytes'];measured.append(4);observed[4]=out['ok']
    if out['ok']:
     actual=rawbytes[s['sha']];assert bytes.fromhex(value['hex'])==actual[q['offset']:q['offset']+16384];assert value['basis']==s['image']and value['offset']==q['offset']and value['next']==min(q['offset']+16384,len(actual))and value['done']==(value['next']==len(actual));measured.append(1);observed[1]=label(value['basis'])
   else:measured.extend([5,6]);observed.update({5:value['artifactMayHaveBeenCopied'],6:value['removed']})
   # Expected source-control transitions are compared only where the protocol
   # actually exposes the field. No unobserved editor or retirement is invented.
   if a==0 and gate:s.update(phase=2 if finished else 1,basis=capture,image=q['expected_image'])
   elif a==1 and before['phase']in [1,2]:s.update(phase=(2 if finished else 1)if gate else 0,basis=before['basis']if gate else 0)
   elif a==2 and before['phase']in [1,2]:s.update(phase=3 if before['phase']==2 and gate else 0,basis=before['basis']if before['phase']==2 and gate else 0)
   elif a==4:s.update(phase=0,basis=0)
   if out['ok']and 'phase'in value:
    observed[0]={'needs-content':1,'needs-verification':2,'artifact-ready':3}[value['phase']];observed[1]=label(value['basis']);measured.extend([0,1])
    if a==2:s.update(bytes=value['bytes'],sha=value['sha256']);assert value['sha256']in rawbytes and len(rawbytes[value['sha256']])==value['bytes']
   row=dict(phase=before['phase'],basis=before['basis'],current=0,action=a,capture=capture,admitted=gate,finished=finished)
   rows.append(dict(id=str(len(rows))+'-'+action,input=row,observed={str(k):str(v).lower()for k,v in observed.items()},measured=sorted(set(measured)),sourceFrame=index))
 assert len(rows)>40
 formal=Path((ROOT/'.build/empack-joined-formal-current').read_text().strip());env=dict(os.environ,LEAN_PATH=str(formal),BEND_NO_TELEMETRY='1');lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend');generated=HERE/'generated';generated.mkdir(exist_ok=True)
 path=generated/'joined-export.json';data=dict(schema=1,profile='joined-research-export',rows=[r['input']for r in rows])
 def replay(v,case='JoinedExportCase'):
  path.write_text(json.dumps(v)+'\n');return subprocess.run([lean,'--run','applications/empack/'+case+'.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
 p=replay(data);assert p.returncode==0,p.stdout+p.stderr;actual=json.loads(p.stdout)
 def compare(row,result):
  fields=result.lower().split('/');assert len(fields)==7
  for key in row['measured']:assert fields[key]==row['observed'][str(key)],(row['id'],key,fields,row['observed'])
 for row,result in zip(rows,actual,strict=True):compare(row,result)
 calls=[]
 for r in data['rows']:
  n=lambda k:str(r[k])+'n';b=lambda k:'True{}'if r[k]else'False{}';calls.append('J.render(J.step(J.State{'+n('phase')+','+n('basis')+'},'+','.join([n('current'),n('action'),n('capture'),b('admitted'),b('finished')])+')) ++ "\\n"')
 driver=generated/'JoinedExportCase.bend';driver.write_text('import Base\nimport ../JoinedExport.bend as J\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n');p=subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr;assert [x.lower()for x in p.stdout.splitlines()]==[x.lower()for x in actual]
 # Reuse the existing save/reopen model. Only storage/image/result fields were
 # captured; editor epochs are synthetic and excluded from conformance claims.
 store_rows=[]
 def editor(state):return dict(epoch=0,current=label(state['current']['image']),saved=label(state['saved']['image'])or None,savedRevision=int(state['saved']['revision']))
 for profile in d['browser']['profiles']:
  ev=profile['events'];history=profile['backend']['history'];images=[snapshot['image']for snapshot in map(lambda h:O.snapshot(h['wire']),history)]
  for name,i,previous,expected,boundary,kind,status in [('invalid-save',1,0,0,3,1,1),('valid-save',2,1,1,3,1,1),('stale-save',3,2,0,3,1,3),('relaunch',4,2,2,3,2,5),('lost-ack',8,2,2,2,1,2),('reconcile',9,3,3,3,2,5)]:
   state=ev[i]['state'];current=label(state['current']['image']);prior_image=None if previous==0 else label(images[previous-1]);e=editor(state)
   if name in ['invalid-save','valid-save']:e.update(saved=None if previous==0 else label(images[previous-1]),savedRevision=previous)
   refs=state['current']['draft']['entries'];available=sorted(label(a['asset']['id'])for a in refs if a['asset']);missing=sorted(label('missing:'+a['source'])for a in refs if not a['asset']);image=current
   r=dict(kind=kind,stored=dict(revision=previous,image=prior_image),editor=e,expected=expected,image=image,validAuthoring=state['current']['interpretation']['valid'],available=available,missing=missing,verified=available,boundary=boundary,backing=True,finalized=True)
   # Post-commit/no-ack backend fact comes from the phase barrier + later raw
   # IDB inspection; the UI still names its earlier save.
   out_revision=3 if name=='lost-ack'else int(state['saved']['revision']);out_image=label(images[2])if name=='lost-ack'else label(state['saved']['image']);observed={0:str(out_revision),1:str(out_image),3:str(current),4:str(label(state['saved']['image'])),5:state['saved']['revision'],6:str(status)}
   store_rows.append(dict(id=profile['engine']+'/'+name,input=r,observed=observed))
 p=replay(dict(schema=1,profile='captured-browser-study-save',rows=[r['input']for r in store_rows]),'PortableStoreCase');assert p.returncode==0,p.stdout+p.stderr;stored_actual=json.loads(p.stdout)
 for row,result in zip(store_rows,stored_actual,strict=True):
  for key,value in row['observed'].items():assert result.split('/')[key]==value,(row['id'],key,result,row['observed'])
 from portable_store_conformance import bend_result
 store_driver=generated/'JoinedStoreCase.bend';store_driver.write_text('import Base\nimport ../PortableStore.bend as S\nimport ../Authoring.bend as A\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join('S.render('+bend_result(r['input'])+') ++ "\\n"'for r in store_rows)+')\n')
 p=subprocess.run([bend,str(store_driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr;assert p.stdout.splitlines()==stored_actual
 refusals=[]
 for name,change in [('schema',lambda v:v.update(schema=2)),('profile',lambda v:v.update(profile='production')),('count',lambda v:v.update(rows=v['rows']*10)),('phase',lambda v:v['rows'][0].update(phase=4)),('action',lambda v:v['rows'][0].update(action=5)),('basis',lambda v:v['rows'][0].update(phase=1,basis=0)),('capture',lambda v:v['rows'][0].update(capture=0)),('bool',lambda v:v['rows'][0].update(admitted='true'))]:
  bad=copy.deepcopy(data);change(bad);p=replay(bad);assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);refusals.append(name)
 mutations=[]
 for key in [0,1,3,4,5,6]:
  index=next(i for i,r in enumerate(rows)if key in r['measured']);r=copy.deepcopy(rows[index]);r['observed'][str(key)]='changed'
  try:compare(r,actual[index])
  except AssertionError:mutations.append(key)
  else:raise AssertionError('Changed observation escaped')
 controls=[]
 for name,filename,change in [('download','browser.json',lambda v:v['profiles'][0]['downloads'][0].update(sha256='0'*64)),('backend-bytes','backend-probe.json',lambda v:v['rows'][0]['before']['objects'][0].update(sha256='0'*64)),('saved-image','browser.json',lambda v:v['profiles'][0]['backend']['history'][0].update(wire='{}')),('source-hash','browser.json',lambda v:v['sourceHashes'].update(**{'store.mjs':'0'*64}))]:
  bad=copy.deepcopy(O.read(RUN/filename));change(bad)
  try:O.inspect({filename:bad})
  except (AssertionError,KeyError):controls.append(name)
  else:raise AssertionError('Changed retained evidence escaped')
 files=[p for directory in [RUN,O.BUILD]for p in directory.rglob('*')if p.is_file()and p.name!='conformance.json'];files += [p for p in (HERE/'joined-study').glob('*')if p.is_file()];files += [HERE/n for n in ['JoinedExport.lean','JoinedExportCase.lean','JoinedExport.bend','Authoring.lean','PortableStore.lean','PortableStoreCase.lean','PortableStore.bend','Authoring.bend','portable_store_conformance.py','portable_joined_observations.py','portable_joined_conformance.py']]
 receipt=dict(schema=1,scope='Bounded executed research join,not whole production engine or full app conformance',protocolComparisons=len(rows),storageComparisons=len(store_rows),protocol=rows,protocolModelResults=actual,storage=store_rows,storageModelResults=stored_actual,researchRefusals=refusals,changedProtocolFields=mutations,changedRetainedEvidence=controls,imageLabels=labels,registryArchives=d['packages'],basisSha256={str(p.relative_to(ROOT)):O.sha(p.read_bytes())for p in sorted(set(files))},formalWork=str(formal),limits=['Input admission/digest/completion witnesses are independently decoded from retained requests,source-controlled fixtures and artifacts;no parser/cryptographic proof.','Protocol rows compare only fields actually returned;unobserved editor/retirement state excluded. Raw status confirms two failed-output removals.','Existing storage model reused;epochs synthetic/not compared. Captured export/current-editor divergence checked directly in browser event and artifact receipts.','No studied application,compiler,browser,JVM,or registry ran during this replay;production0.9engine,Prism import/game,full crash/concurrency/quota/security remain unqualified.'])
 (RUN/'conformance.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items()if k not in ['protocol','protocolModelResults','storage','storageModelResults','basisSha256','imageLabels','registryArchives']},indent=2))
if __name__=='__main__':main()
