#!/usr/bin/env python3
"""Owner-run native half of the joined study; no host empack/state/project edits."""
from datetime import datetime,timezone
import copy,hashlib,importlib.util,json,os,sys,uuid,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
BASE="schema: 6\npack:\n  id: joined-study\n  name: Original Ω 日本\n  version: alpha\nruntime:\n  minecraft: '1.21.1'\n  loader: vanilla\n  java: {preferred: 21}\n"
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def main():
 build_run=Path((ROOT/'.build/empack-joined-current').read_text().strip());build=json.loads((build_run/'build.json').read_text());assert 'wasm'in build and build['heldUnchanged']
 run=ROOT/'applications/evidence'/('empack-joined-flow-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir();work=Path(build['work'])/run.name;objects=work/'objects';objects.mkdir(parents=True);root=work/'root.json'
 (run/'native.py').write_bytes(Path(__file__).read_bytes());(run/'peer.py').write_bytes((HERE/'joined-study/peer.py').read_bytes());spec=importlib.util.spec_from_file_location('peer',HERE/'joined-study/peer.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);peers=[];events=[];artifacts=[]
 def start():
  p=module.Peer(build['native']['path']);peers.append(p);return p
 peer=start()
 def raw(action,**args):return peer.call(dict(action=action,**args))
 def call(action,**args):
  r=raw(action,**args);assert r['ok'],r;return r['value']
 def event(name,**data):events.append(dict(event=name,**data));write(run/'native-events.json',events)
 def observe(name,body,keep=True):
  id=str(uuid.uuid4());call('observe-begin',id=id,original_name=name)
  for offset in range(0,len(body),16384):call('observe-feed',id=id,offset=offset,hex=body[offset:offset+16384].hex())
  ref=call('observe-end',id=id);assert ref['sha256']==sha(body)and ref['bytes']==len(body)
  if keep:
   with (objects/id).open('xb')as f:f.write(body);f.flush();os.fsync(f.fileno())
  return ref
 def verify_refs(draft):
  for e in draft['entries']:
   if not e['asset']:continue
   ref=e['asset'];b=(objects/ref['id']).read_bytes();actual=observe(ref['original_name'],b,False);assert (actual['sha256'],actual['bytes'])==(ref['sha256'],ref['bytes'])
 def save(expected,view):
  verify_refs(view['draft']);record=json.loads(root.read_text())if root.exists()else dict(revision='0',history=[])
  if record['revision']!=expected:return dict(ok=False,reason='stale-storage-revision',current=record['revision'])
  snapshot=call('snapshot',draft=view['draft']);next=dict(revision=str(int(expected)+1),wire=snapshot['wire'],attempt=str(uuid.uuid4()),history=record['history']+[dict(revision=str(int(expected)+1),wire=snapshot['wire'])]);temp=work/('root-'+str(uuid.uuid4())+'.tmp')
  with temp.open('x')as f:json.dump(next,f,ensure_ascii=False);f.flush();os.fsync(f.fileno())
  os.replace(temp,root);fd=os.open(work,os.O_RDONLY);os.fsync(fd);os.close(fd);return dict(ok=True,revision=next['revision'],image=snapshot['image'])
 def reopen():return call('reopen',wire=json.loads(root.read_text())['wire'])
 def export(view,label,edit_after=None,cancel_after=None,fault=None):
  id=str(uuid.uuid4());r=raw('export-begin',id=id,draft=view['draft'],expected_image=view['image']);trace=[r]
  if not r['ok']:return dict(ok=False,result=r,phase='prepare')
  if edit_after:edit_after()
  next=r['value'];chunks=0;refs={e['asset']['id']:e['asset']for e in view['draft']['entries']if e['asset']}
  while next['phase']=='needs-content':
   ref=refs[next['asset']['id']];assert ref==next['asset']and next['count']<=16384;path=objects/ref['id']
   with path.open('rb')as f:f.seek(next['offset']);b=f.read(next['count'])
   r=raw('export-feed',id=id,asset_id=ref['id'],offset=next['offset'],hex=b.hex());trace.append(r);chunks+=1
   if not r['ok']:assert call('status',id=id)['export']=='absent';return dict(ok=False,result=r,phase='input',chunks=chunks)
   next=r['value']
   if cancel_after==chunks:
    cancelled=call('cancel',id=id);assert cancelled['removed'];assert not raw('artifact-read',id=id,offset=0)['ok'];return dict(ok=False,phase='cancelled',chunks=chunks,cancelled=cancelled)
  assert next['phase']=='needs-verification';assert not raw('artifact-read',id=id,offset=0)['ok'];r=raw('export-verify',id=id,fault=fault);trace.append(r)
  if not r['ok']:assert call('status',id=id)['export']=='absent';return dict(ok=False,result=r,phase='verification')
  ready=r['value'];parts=[];offset=0
  while True:
   part=call('artifact-read',id=id,offset=offset);assert part['basis']==view['image']and part['offset']==offset;parts.append(bytes.fromhex(part['hex']));offset=part['next']
   if part['done']:break
  payload=b''.join(parts);assert sha(payload)==ready['sha256']and len(payload)==ready['bytes'];output=work/(label+'.zip');output.write_bytes(payload)
  with zipfile.ZipFile(output)as z:
   actual=[dict(path=i.filename,bytes=i.file_size,sha256=sha(z.read(i)),mode=(i.external_attr>>16)&0o777)for i in z.infolist()if not i.is_dir()];assert sorted(actual,key=lambda x:x['path'])==sorted(ready['inventory'],key=lambda x:x['path'])
  assert call('cancel',id=id)['removed'];artifacts.append(dict(label=label,path=str(output),ready=ready,actualInventory=actual,sourceChunks=chunks,artifactChunks=len(parts)));return dict(ok=True,ready=ready,sourceChunks=chunks,artifactChunks=len(parts))
 error=None;closed=[]
 try:
  jar=(ROOT/'applications/evidence/empack-portable-storage-20261124T222835992Z/work/inputs/Sample Ω 日本.jar').read_bytes();config='{"message":"local Ω 日本","literal":"{{ NAME }}"}\n'.encode();(work/'source.jar').write_bytes(jar);(work/'rules.json').write_bytes(config);write(run/'inputs.json',dict(jar=dict(bytes=len(jar),sha256=sha(jar)),config=dict(bytes=len(config),sha256=sha(config)),baseAuthorHex=BASE.encode().hex()))
  view=call('create',author_hex=BASE.encode().hex());refs=[observe('Sample Ω 日本.jar',jar),observe('rules.json',config)];view=call('import',draft=view['draft'],assets=refs);view=call('author',draft=view['draft'],author_hex=b'schema: [\n'.hex());view=call('missing',draft=view['draft'],destination='config/not-supplied.cfg');saved=save('0',view);assert saved['ok']and saved['revision']=='1';view=reopen();assert not view['interpretation']['valid']and view['draft']['entries'][-1]['asset']is None;event('incomplete-save-reopen',saved=saved,view=view)
  view=call('author',draft=view['draft'],author_hex=BASE.encode().hex());view=call('remove',draft=view['draft'],index=2);view=call('rename',draft=view['draft'],name='Edited Δ 日本');view=call('place',draft=view['draft'],index=1,destination='config/renamed Ω 日本.json');saved=save('1',view);assert saved['ok']and saved['revision']=='2';stale=save('0',view);assert not stale['ok'];event('valid-save-stale-refusal',saved=saved,stale=stale)
  peer.close();peer=start();view=reopen();assert view['interpretation']['name']=='Edited Δ 日本';captured=copy.deepcopy(view);current=view
  def later_edit():
   nonlocal current
   current=call('rename',draft=current['draft'],name='Later draft');event('edit-after-export-capture',capturedImage=captured['image'],current=current)
  result=export(captured,'main',later_edit);assert result['ok']and result['ready']['basis']==captured['image']!=current['image'];event('captured-export',result=result,currentImage=current['image'],savedImage=saved['image'])
  missing=call('missing',draft=captured['draft'],destination='config/missing.cfg');assert not export(missing,'missing')['ok'];event('missing-input-refused')
  omitted=copy.deepcopy(missing['draft']);omitted['entries'][-1]['layer']=3;omitted=call('inspect',draft=omitted);assert export(omitted,'unselected-missing')['ok'];event('opposite-side-missing-not-demanded')
  corrupt=objects/refs[0]['id'];original=corrupt.read_bytes();corrupt.write_bytes(original[:-1]+bytes([original[-1]^1]));bad=export(captured,'corrupt');assert not bad['ok']and bad['phase']=='input';corrupt.write_bytes(original);assert sha(corrupt.read_bytes())==refs[0]['sha256'];event('corrupt-input-refused-explicitly-restored',result=bad)
  alias=copy.deepcopy(captured['draft']);e=copy.deepcopy(alias['entries'][1]);e['destination']='config/RENAMED Ω 日本.json';alias['entries'].append(e);alias=call('inspect',draft=alias);bad=export(alias,'alias');assert not bad['ok']and bad['phase']=='prepare';event('portable-alias-refused',result=bad)
  bad=export(captured,'truncated',fault='truncate-archive');assert not bad['ok']and bad['phase']=='verification';event('truncated-output-refused',result=bad)
  big=hashlib.shake_256(b'owned joined stream fixture').digest(102400);bigref=observe('stream.bin',big);large=call('import',draft=captured['draft'],assets=[bigref]);result=export(large,'streamed');assert result['ok']and result['sourceChunks']>2 and result['artifactChunks']>1;event('bounded-source-and-artifact-stream',result=result)
  bad=export(large,'cancelled',cancel_after=1);assert not bad['ok']and bad['phase']=='cancelled';event('midstream-cancellation',result=bad)
  empty=observe('empty.cfg',b'');zero=call('import',draft=captured['draft'],assets=[empty]);assert export(zero,'empty')['ok'];event('known-empty-input-exported')
  wire=json.loads(root.read_text())['wire'];damaged=json.loads(wire);damaged['draft']['author_hex']='00';bad=raw('reopen',wire=json.dumps(damaged));assert not bad['ok'];assert reopen()['image']==captured['image'];event('tampered-image-refused',result=bad)
  record=json.loads(root.read_text());assert record['revision']=='2'and len(record['history'])==2
 except BaseException as e:error=dict(type=type(e).__name__,message=str(e));raise
 finally:
  for p in peers:closed.append(p.close())
  write(run/'native-frames.json',[dict(index=i,frames=p.frames,closed=p.closed)for i,p in enumerate(peers)]);receipt=dict(schema=1,buildCapture=str(build_run.relative_to(ROOT)),buildSha256=sha((build_run/'build.json').read_bytes()),work=str(work),producerSha256=sha((run/'native.py').read_bytes()),peerSha256=sha((run/'peer.py').read_bytes()),events=events,artifacts=artifacts,closed=closed,error=error);write(run/'native.json',receipt);(ROOT/'.build/empack-joined-flow-current').write_text(str(run)+'\n')
 assert all(c['exitCode']==0 and c['groupAbsent']and not c['stderr']and not c['unread']for c in closed);print(json.dumps(dict(run=str(run.relative_to(ROOT)),events=len(events),artifacts=len(artifacts),allOwnedGroupsAbsent=True)))
if __name__=='__main__':main()
