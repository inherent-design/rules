#!/usr/bin/env python3
"""Private native API study. Launch/request require current re:desktop access."""
import argparse,hashlib,json,os,plistlib,subprocess,tempfile,time
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];APP=Path('/Applications/Visual Studio Code.app/Contents')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','launch','request']);parser.add_argument('run',nargs='?',type=Path);parser.add_argument('operation',nargs='?');args=parser.parse_args();product=json.loads((APP/'Resources/app/product.json').read_text())['commit'];assert product==json.loads((ROOT/'applications/sources/vscode-source.json').read_text())['commit']
 if args.action=='prepare':
  run=ROOT/'applications/evidence'/('vscode-filesystem-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir();work=Path(tempfile.mkdtemp(prefix='rules-vfs-',dir='/private/tmp'));assert len(str(work/'user-data/1.14-main.sock').encode())<=103
  for name in ['project','extension','extensions','user-data/User','tmp']:(work/name).mkdir(parents=True)
  extension=HERE/'filesystem-extension.cjs';(work/'extension/extension.cjs').write_bytes(extension.read_bytes());(run/'extension.cjs').write_bytes(extension.read_bytes());(run/'probe.py').write_bytes(Path(__file__).read_bytes());package=dict(name='rules-private-filesystem-study',publisher='rules-study',version='0.0.1',engines=dict(vscode='^1.147.0'),main='./extension.cjs',activationEvents=['onStartupFinished']);write(work/'extension/package.json',package);write(run/'extension-package.json',package)
  settings={'workbench.startupEditor':'none','files.autoSave':'off','files.hotExit':'off','telemetry.telemetryLevel':'off','update.mode':'none','extensions.autoUpdate':False,'extensions.autoCheckUpdates':False,'security.workspace.trust.enabled':False,'git.enabled':False,'chat.disableAIFeatures':True};write(work/'user-data/User/settings.json',settings);write(run/'settings.json',settings)
  binary=APP/'MacOS'/plistlib.loads((APP/'Info.plist').read_bytes())['CFBundleExecutable'];meta=dict(schema=1,work=str(work),output=str(run/'observed.json'),product=product,version=json.loads((APP/'Resources/app/package.json').read_text())['version'],binary=dict(path=str(binary),sha256=sha(binary)),producerSha256=sha(run/'probe.py'),extensionSha256=sha(extension));write(run/'meta.json',meta);(ROOT/'.build/vscode-filesystem-current').write_text(str(run)+'\n');print(json.dumps(dict(run=str(run),work=str(work))));return
 assert args.run;run=args.run.resolve();meta=json.loads((run/'meta.json').read_text());work=Path(meta['work']);assert work.parent==Path('/private/tmp')and work.name.startswith('rules-vfs-')and product==meta['product']
 if args.action=='launch':
  assert not(run/'process.json').exists(),'Preserve earlier launch;prepare a new capture';binary=Path(meta['binary']['path']);assert sha(binary)==meta['binary']['sha256'];command=[str(binary),'--new-window','--skip-welcome','--skip-release-notes','--use-inmemory-secretstorage','--user-data-dir',str(work/'user-data'),'--extensions-dir',str(work/'extensions'),'--extensionDevelopmentPath='+str(work/'extension'),str(work/'project')]
  env=dict(PATH='/usr/bin:/bin',TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8',SHELL='/bin/bash',RULES_VFS_FIXTURE=str(run/'meta.json'))
  with(work/'app.stdout').open('xb')as out,(work/'app.stderr').open('xb')as err:
   p=subprocess.Popen(command,env=env,stdout=out,stderr=err,start_new_session=True);write(run/'process.json',dict(pid=p.pid,argv=command,environmentKeys=sorted(env)));print(json.dumps(dict(pid=p.pid,run=str(run))),flush=True);code=p.wait()
  try:os.killpg(p.pid,0);absent=False
  except ProcessLookupError:absent=True
  write(run/'exit.json',dict(exitCode=code,groupAbsent=absent));print(json.dumps(dict(exitCode=code,groupAbsent=absent)));return
 assert args.operation in ['baseline','readonly','queued','queued-copy','partial','incarnation','watch','detached','quit'];current=json.loads(Path(meta['output']).read_text());assert current['status']=='ready' or args.operation=='quit';sequence=current['handled']+1;temporary=work/'control.tmp';write(temporary,dict(sequence=sequence,action=args.operation));temporary.replace(work/'control.json');deadline=time.monotonic()+20
 while time.monotonic()<deadline:
  if args.operation=='quit'and(run/'exit.json').exists():print((run/'exit.json').read_text());return
  current=json.loads(Path(meta['output']).read_text())
  if current['handled']==sequence:print(json.dumps(dict(status=current['status'],rows=len(current['rows']),events=current['events'][-2:])));return
  time.sleep(.08)
 raise RuntimeError('Fixture did not acknowledge;inspect state before retrying')
if __name__=='__main__':main()
