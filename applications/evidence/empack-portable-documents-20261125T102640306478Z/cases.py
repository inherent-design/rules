#!/usr/bin/env python3
"""Owner-run controlled actual document calls, preserving inputs and partial runs."""
import copy,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
BASE='''schema: 6
pack:
  id: portable-study
  name: Original Ω 日本
  version: alpha
runtime:
  minecraft: '1.21.1'
  loader: vanilla
  java: {preferred: 21}
'''
def main():
 run=Path(sys.argv[1]).resolve();assert run.parent==ROOT/'applications/evidence'and run.name.startswith('empack-portable-documents-');build=json.loads((run/'build.json').read_text());work=Path(build['work']);assert 'wasm'in build
 (run/'cases.py').write_bytes(Path(__file__).read_bytes());cases=[]
 def add(id,author=BASE,bindings=None,rename=None,expect=True):
  raw=author.encode()if isinstance(author,str)else author
  request=dict(schema=1,action='rename'if rename is not None else'decode',author_hex=raw.hex(),bindings_hex=None if bindings is None else bindings.encode().hex(),rename=rename)
  packet=json.dumps(request,ensure_ascii=False,separators=(',',':')).encode();cases.append(dict(id=id,request=request,packetHex=packet.hex(),packetSha256=hashlib.sha256(packet).hexdigest(),expectedOk=expect))
 add('minimal');add('comment-only','# retained comment\n'+BASE);add('binding-empty',bindings='schema: 1\nbindings: {}\n');add('binding-seed',bindings='schema: 1\nbindings: {}\npolicies:\n  options.txt: seed\n');add('inline-seed',BASE+'installation-policies:\n  options.txt: seed\n')
 add('rename',rename='Edited Δ 日本');add('rename-noop',rename='Original Ω 日本');add('rename-preserve-comment','# keep me\n'+BASE,rename='Edited Δ 日本');add('rename-empty',rename='',expect=False)
 add('unsupported-author-schema',BASE.replace('schema: 6','schema: 5'),expect=False);add('schema-bool',BASE.replace('schema: 6','schema: true'),expect=False);add('schema-string',BASE.replace('schema: 6',"schema: '6'"),expect=False)
 add('unknown-author-field',BASE+'surprise: true\n',expect=False);add('unknown-pack-field',BASE.replace('  version: alpha','  version: alpha\n  ignored: true'),expect=False)
 add('invalid-yaml','schema: [\n',expect=False);add('invalid-utf8',b'\xff\xfe',expect=False)
 add('old-bindings',bindings='schema: 0\nbindings: {}\n',expect=False);add('unknown-binding-root',bindings='schema: 1\nbindings:\n  absent:\n    placement: automatic\n',expect=False)
 add('conflicting-policy',BASE+'installation-policies:\n  options.txt: seed\n',bindings='schema: 1\nbindings: {}\npolicies:\n  options.txt: managed\n',expect=False)
 add('local-missing-is-intent',BASE+'dependencies:\n  sample:\n    path: inputs/Sample Ω 日本.jar\n');add('invalid-local-path',BASE+'dependencies:\n  sample:\n    path: ../escape.jar\n',expect=False)
 add('provider-pin',BASE+'dependencies:\n  sample:\n    source: modrinth:fixture-project\n    pin: exact-id\n')
 add('url-no-evidence',BASE+'dependencies:\n  sample:\n    url: https://example.invalid/sample.jar\n',expect=False)
 add('url-observed',BASE+'dependencies:\n  sample:\n    url: https://example.invalid/sample.jar\n    accept-observed: true\n')
 add('url-http',BASE+'dependencies:\n  sample:\n    url: http://example.invalid/sample.jar\n    accept-observed: true\n',expect=False)
 add('url-credential',BASE+'dependencies:\n  sample:\n    url: https://example.invalid/sample.jar?token=fixture\n    accept-observed: true\n',expect=False)
 add('bad-build-recipe',BASE+'build:\n  profiles:\n    test: {target: prism, environment: server}\n',expect=False)
 add('prism-profile',BASE+'build:\n  profiles:\n    test: prism\n  default: [test]\n')
 # The decoded raw author must reject duplicate keys rather than silently lose input.
 add('duplicate-author-key',BASE+'schema: 6\n',expect=False)
 for id,changes in [('wrong-wire-schema',dict(schema=2)),('unknown-wire-field',dict(extra=True)),('unknown-action',dict(action='unknown')),('invalid-hex',dict(author_hex='xy'))]:
  r=copy.deepcopy(cases[0]['request']);r.update(changes);p=json.dumps(r,separators=(',',':')).encode();cases.append(dict(id=id,request=r,packetHex=p.hex(),packetSha256=hashlib.sha256(p).hexdigest(),expectedOk=False))
 write(run/'cases.json',cases);rows=[];receipt=dict(schema=1,producerSha256=sha(run/'cases.py'),binarySha256=sha(Path(build['native']['path'])),rows=rows,complete=False)
 def save():write(run/'native-cases.json',receipt)
 save()
 for case in cases:
  started=time.monotonic();p=subprocess.Popen([build['native']['path']],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  try:out,err=p.communicate(bytes.fromhex(case['packetHex']),timeout=8)
  except BaseException:
   if p.poll()is None:os.killpg(p.pid,signal.SIGKILL);p.communicate(timeout=5)
   raise
  for name,data in [('stdout',out),('stderr',err)]:(run/(case['id']+'.native.'+name)).write_bytes(data)
  try:os.killpg(p.pid,0)
  except ProcessLookupError:absent=True
  else:absent=False
  value=json.loads(out);rows.append(dict(id=case['id'],status=0,hex=out.hex(),exitCode=p.returncode,groupAbsent=absent,seconds=time.monotonic()-started,stdoutSha256=sha(run/(case['id']+'.native.stdout'))));save()
  assert p.returncode==0 and not err and absent,(case['id'],p.returncode,err)
  assert value['ok']==case['expectedOk'],(case['id'],value)
 receipt['complete']=True;save();print(json.dumps(dict(cases=len(cases),complete=True)))
if __name__=='__main__':main()
