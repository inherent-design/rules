#!/usr/bin/env python3
"""Owner-run first complete streaming-export protocol control, no user state."""
import hashlib,importlib.util,json,subprocess,uuid,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE="schema: 6\npack:\n  id: joined-study\n  name: Original Ω 日本\n  version: alpha\nruntime:\n  minecraft: '1.21.1'\n  loader: vanilla\n  java: {preferred: 21}\n"
def main():
 run=Path((ROOT/'.build/empack-joined-current').read_text().strip());build=json.loads((run/'build.json').read_text());assert not (run/'smoke.json').exists()
 module=importlib.util.spec_from_file_location('peer',ROOT/'applications/empack/joined-study/peer.py');peer=importlib.util.module_from_spec(module);module.loader.exec_module(peer);p=peer.Peer(build['native']['path']);(run/'smoke.py').write_bytes(Path(__file__).read_bytes());(run/'peer.py').write_bytes((ROOT/'applications/empack/joined-study/peer.py').read_bytes());events=[]
 def call(action,**args):
  v=p.call(dict(action=action,**args));assert v['ok'],v;return v['value']
 try:
  view=call('create',author_hex=BASE.encode().hex());body=(bytes(range(256))*400);asset_id=str(uuid.uuid4());call('observe-begin',id=asset_id,original_name='stream.bin');offset=0
  while offset<len(body):
   b=body[offset:offset+16384];call('observe-feed',id=asset_id,offset=offset,hex=b.hex());offset+=len(b)
  asset=call('observe-end',id=asset_id);assert asset['sha256']==hashlib.sha256(body).hexdigest();view=call('import',draft=view['draft'],assets=[asset]);op=str(uuid.uuid4());next=call('export-begin',id=op,draft=view['draft'],expected_image=view['image']);events.append(next);chunks=0
  while next['phase']=='needs-content':
   offset=next['offset'];b=body[offset:offset+next['count']];next=call('export-feed',id=op,asset_id=asset_id,offset=offset,hex=b.hex());events.append(next);chunks+=1
  assert next['phase']=='needs-verification'and chunks==7
  before=p.call(dict(action='artifact-read',id=op,offset=0));assert not before['ok']
  ready=call('export-verify',id=op,fault=None);artifact=bytearray();offset=0
  while True:
   r=call('artifact-read',id=op,offset=offset);artifact.extend(bytes.fromhex(r['hex']));offset=r['next']
   if r['done']:break
  assert len(artifact)==ready['bytes']and hashlib.sha256(artifact).hexdigest()==ready['sha256'];path=Path(build['work'])/'smoke.zip';path.write_bytes(artifact)
  with zipfile.ZipFile(path)as z:assert z.read('.minecraft/config/stream.bin')==body;assert set(f['path']for f in ready['inventory'])=={n for n in z.namelist()if not n.endswith('/')}
  assert call('cancel',id=op)['removed'];assert call('status',id=op)['export']=='absent'
 finally:closed=p.close();(run/'native-smoke.frames.json').write_text(json.dumps(p.frames,indent=2)+'\n')
 receipt=dict(schema=1,events=events,artifact=ready,path=str(path),inputBytes=len(body),inputSha256=asset['sha256'],streamChunks=chunks,closed=closed,producerSha256=hashlib.sha256((run/'smoke.py').read_bytes()).hexdigest());(run/'smoke.json').write_text(json.dumps(receipt,indent=2)+'\n');assert closed['exitCode']==0 and closed['groupAbsent']and not closed['stderr'];print(json.dumps(dict(chunks=chunks,artifactBytes=len(artifact),files=len(ready['inventory']),closed=closed)))
if __name__=='__main__':main()
