#!/usr/bin/env python3
"""Owner-run installed-CLI reference, using only a fresh study project/state/cache."""
import hashlib,json,os,signal,subprocess,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'applications/evidence/empack-joined-flow-20261125T113211837178Z'
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
 native=json.loads((RUN/'native.json').read_text());work=Path(native['work'])/'installed-reference';work.mkdir()
 binary=Path('/Users/zer0cell/.local/bin/empack');assert sha(binary.read_bytes())=='99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
 project=work/'project';project.mkdir();record=json.loads((Path(native['work'])/'root.json').read_text());snapshot=json.loads(record['wire']);draft=snapshot['draft'];assert record['revision']=='2'
 (project/'empack.yml').write_bytes(bytes.fromhex(draft['author_hex']))
 if draft['bindings_hex']is not None:(project/'empack.bindings.yml').write_bytes(bytes.fromhex(draft['bindings_hex']))
 for e in draft['entries']:
  assert e['layer']==0 and e['source']=='pack/'+e['destination'];p=project/e['source'];p.parent.mkdir(parents=True,exist_ok=True);b=(Path(native['work'])/'objects'/e['asset']['id']).read_bytes();assert sha(b)==e['asset']['sha256'];p.write_bytes(b)
 (RUN/'installed-reference.py').write_bytes(Path(__file__).read_bytes());rows=[];receipt=dict(schema=1,binary=str(binary),binarySha256=sha(binary.read_bytes()),work=str(work),sourceImage=snapshot['image'],commands=rows)
 try:
  base=[str(binary),'--state-dir',str(work/'state'),'--cache-dir',str(work/'cache'),'--workdir',str(project),'--color','never','--yes']
  for args in [['--version'],['sync'],['build','--ad-hoc','prism','--delivery','bundled','--environment','client','--updates','snapshot','--format','zip']]:
   command=base+args;start=time.monotonic();p=subprocess.Popen(command,cwd=project,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
   try:out,err=p.communicate(timeout=120)
   except subprocess.TimeoutExpired:
    os.killpg(p.pid,signal.SIGTERM)
    try:out,err=p.communicate(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate()
   try:os.killpg(p.pid,0);absent=False
   except ProcessLookupError:absent=True
   rows.append(dict(argv=command,exitCode=p.returncode,seconds=time.monotonic()-start,stdout=out.decode(errors='replace'),stderr=err.decode(errors='replace'),groupAbsent=absent));assert p.returncode==0 and absent,rows[-1]
  outputs=list(project.rglob('*.zip'));assert len(outputs)==1,outputs;p=outputs[0];raw=p.read_bytes()
  with zipfile.ZipFile(p)as z:
   assert z.testzip()is None;inventory=[dict(path=i.filename,bytes=i.file_size,sha256=sha(z.read(i)),mode=(i.external_attr>>16)&0o777)for i in z.infolist()if not i.is_dir()]
  expected=next(a for a in native['artifacts']if a['label']=='main')['actualInventory'];receipt['artifact']=dict(path=str(p),bytes=len(raw),sha256=sha(raw),inventory=inventory)
  receipt['semanticMatch']=sorted(inventory,key=lambda r:r['path'])==sorted(expected,key=lambda r:r['path']);assert receipt['semanticMatch'],(inventory,expected)
  receipt['complete']=True
 except BaseException as e:receipt['error']=dict(type=type(e).__name__,message=str(e));raise
 finally:(RUN/'installed-reference.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(complete=True,semanticMatch=True,commands=len(rows),work=str(work))))
if __name__=='__main__':main()
