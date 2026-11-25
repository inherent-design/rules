#!/usr/bin/env python3
"""Retained codec parity plus explicitly model-only raw/semantic basis examples."""
import copy,hashlib,json,os,subprocess
from pathlib import Path
from portable_document_observations import ROOT,RUN,inspect,read,sha
HERE=Path(__file__).resolve().parent

def main():
 cases,out,build,browser,packages=inspect();prior=ROOT/read(RUN/'reused-build.json')['capture']
 files=[p for folder in [RUN,prior]for p in folder.iterdir()if p.is_file()and p.name not in ['conformance.json']]
 files += [HERE/p for p in ['portable_document_observations.py','portable_document_conformance.py','portable_document_build.py','portable_document_cases.py','portable_document_browser.mjs','Documents.lean','DocumentsCase.lean','Documents.bend']]
 files += list((HERE/'document-portable').iterdir());ledger=ROOT/'applications/sources/empack-portable-documents-selections.json';files.append(ledger)
 basis={str(p.relative_to(ROOT)):sha(p)for p in files}
 for pin in read(ledger)['sources']:
  raw=subprocess.check_output(['git','-C',str(ROOT.parent/'empack'),'show',build['revision']+':'+pin['path']]);assert hashlib.sha256(raw).hexdigest()==pin['sha256']
 # Meaning is deliberately limited to name and options.txt seed policy. No
 # parser, fingerprint algorithm, writer or actual lock is modeled here.
 selected=['minimal','comment-only','binding-empty','binding-seed','inline-seed'];views={}
 for name in selected:
  v=out[name];views[name]=dict(basis=dict(author=v['raw'],bindings=v['bindingsRevision'],lock=None),meaning=dict(name=0,seedPayload=name in ['binding-seed','inline-seed']),semantic=v['semantic'])
 for name in ['rename','rename-preserve-comment']:
  v=out[name]['prepared'];views[name]=dict(basis=dict(author=hashlib.sha256(bytes.fromhex(v['authorHex'])).hexdigest(),bindings=None if v['bindingsHex']is None else hashlib.sha256(bytes.fromhex(v['bindingsHex'])).hexdigest(),lock=None),meaning=dict(name=1,seedPayload=False),semantic=v['semantic'])
 pairs=[('minimal','minimal'),('minimal','comment-only'),('minimal','binding-empty'),('minimal','binding-seed'),('binding-seed','inline-seed'),('minimal','rename'),('comment-only','rename-preserve-comment'),('binding-seed','binding-seed')]
 rows=[];expected=[];calls=[];wanted=[];labels=[]
 bit=lambda b:'True{}'if b else'False{}'
 for origin,target in pairs:
  a,b=views[origin],views[target];same_meaning=a['semantic']==b['semantic'];same_raw=a['basis']==b['basis']
  # The symbolic lock is a model-only premise, not an observed installed lock.
  common=dict(prepared=a['basis'],current=b['basis'],meaning=b['meaning'],locked=a['meaning'],valid=True,approved=True,otherChecks=True,writtenLock='modeled-write-only')
  rows.extend([dict(common,action=0),dict(common,action=1)]);expected.extend(['current'if same_meaning else'stale','recorded'if same_raw else'refused']);labels.append(origin+'->'+target)
  calls.extend(['Bool.show(D.current(True{},'+bit(a['meaning']==b['meaning'])+')) ++ "\\n"','Bool.show(D.may_record(True{},True{},True{},'+bit(a['basis']['author']==b['basis']['author'])+','+bit(a['basis']['bindings']==b['basis']['bindings'])+',True{})) ++ "\\n"']);wanted.extend([str(same_meaning),str(same_raw)])
 generated=HERE/'generated';generated.mkdir(exist_ok=True);packet=generated/'portable-documents.json';formal=Path(os.environ.get('STUDY_FORMAL_DIR',str(ROOT/'.build/formal')));env=dict(os.environ,LEAN_PATH=str(formal),BEND_NO_TELEMETRY='1');lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend')
 def replay(value):
  packet.write_text(json.dumps(value)+'\n');return subprocess.run([lean,'--run','applications/empack/DocumentsCase.lean',str(packet)],cwd=ROOT,env=env,capture_output=True,text=True)
 p=replay(dict(schema=1,cases=rows));assert p.returncode==0,p.stdout+p.stderr;actual=json.loads(p.stdout);assert [r['label']for r in actual]==expected
 for r,value in zip(rows,actual,strict=True):assert value['author']==r['current']['author']and value['bindings']==r['current']['bindings']
 runner=generated/'PortableDocumentsCase.bend';runner.write_text('import Base\nimport ../Documents.bend as D\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n');p=subprocess.run([bend,str(runner)],cwd=ROOT,env=env,capture_output=True,text=True);assert p.returncode==0 and p.stdout.splitlines()==wanted,p.stdout+p.stderr
 refused=[]
 for label,value,message in [('schema',dict(schema=2,cases=rows),'Unsupported document research schema'),('action',dict(schema=1,cases=[dict(rows[0],action=9)]),'Unsupported document action'),('meaning',dict(schema=1,cases=[dict(rows[0],meaning=dict(name=4,seedPayload=False))]),'Meaning outside controlled document fixture')]:
  p=replay(value);assert p.returncode==2 and message in p.stderr;refused.append(label)
 packet.write_text(json.dumps(dict(schema=1,cases=rows),indent=2)+'\n')
 controls=[]
 for label,file,change in [
  ('native-not-complete','native-cases.json',lambda d:d.update(complete=False)),
  ('native-group-live','native-cases.json',lambda d:d['rows'][0].update(groupAbsent=False)),
  ('native-bytes','native-cases.json',lambda d:d['rows'][0].update(hex='00')),
  ('wrong-declared-request','cases.json',lambda d:d[0]['request'].update(action='unknown')),
  ('browser-result','browser.json',lambda d:d['profiles'][0]['rows'][0].update(status=1)),
  ('worker-error','browser.json',lambda d:d['profiles'][1]['errors'].append('failed')),
  ('node-identity','browser.json',lambda d:d['node'].update(sha256='00'*32)),
  ('browser-live','browser-closure.json',lambda d:d.update(originalGroupAbsent=False))]:
  d=copy.deepcopy(read(RUN/file));change(d)
  try:inspect({file:d})
  except AssertionError:controls.append(label)
  else:raise AssertionError('Changed observation accepted: '+label)
 assert all(sha(ROOT/p)==h for p,h in basis.items())
 receipt=dict(schema=1,basisSha256=basis,actualCalls=34,successful=12,refused=22,exactRuntimeTargets=['native','Node WASM','Chromium worker','WebKit worker'],exactParity=True,sourceFiles=28,registryPackages=packages,registrySourceFiles=sum(p['sourceFiles']for p in packages),modelOnlyPairs=labels,modelOnlyLeanProjections=len(rows),modelOnlyBendPredicates=len(calls),decoderRefusals=refused,observationControls=controls,limits=['Existing10Lean/4Bend document laws reused unchanged.16 projections illustrate necessary raw preconditions and semantic currency with actual codec basis labels and a hypothetical lock;no actual writer,grant or saved lock is exercised.', 'Full actual DocumentCodec preserves its current input/encoding/inspection/prepared-edit rules in each target;no claim about every source function,unbounded inputs,lossless fullproject format or consumer exporter.', 'Registry archives match original Cargo.lock;all3151 packaged source files match unpacked cache. Generated compiler outputs and entire ambient Cargo configuration are not reproducibility-qualified.', 'No actual storage,asset capture,network acquisition,publication,recovery or full browser authoring join. Native research ABI exits0 with an explicit ok field;this is not empackCLI exit-policy evidence.'])
 (RUN/'conformance.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items()if k not in ['basisSha256','registryPackages','limits']},indent=2))
if __name__=='__main__':main()
