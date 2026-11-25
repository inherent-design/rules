#!/usr/bin/env python3
"""Pure comparison of retained previews and effects;no package-manager run."""
import copy,json,os,subprocess
from pathlib import Path
import observations as O
ROOT,HERE=O.ROOT,O.HERE
FIELDS=['left','right','copies','status','selectionChanged','placementChanged','manifestChanged']
def compare(row,result):
 values=result.lower().split('/');assert len(values)==len(FIELDS)
 for key,value in zip(FIELDS,values):assert value==str(row['observed'][key]).lower(),(row['id'],key,value,row['observed'][key])
def main():
 rows,basis=O.inspect();formal=Path((ROOT/'.build/js-dedupe-formal-current').read_text().strip());lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend');env=dict(os.environ,LEAN_PATH=str(formal),BEND_NO_TELEMETRY='1');generated=HERE/'generated';generated.mkdir(exist_ok=True);path=generated/'input.json';data=dict(schema=1,rows=[r['input']for r in rows])
 def replay(value):
  path.write_text(json.dumps(value)+'\n');return subprocess.run([lean,'--run','applications/js-dedupe/DedupeCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
 p=replay(data);assert p.returncode==0,p.stdout+p.stderr;actual=json.loads(p.stdout)
 for row,value in zip(rows,actual,strict=True):compare(row,value)
 calls=[]
 for row in rows:
  r=row['input'];n=lambda k:str(r[k])+'n';b=lambda k:'True{}'if r[k]else'False{}';xs=lambda k:'['+','.join(str(v)+'n'for v in r[k])+']';old='D.Selection{'+','.join(n(k)for k in ['left','right','copies'])+'}';target='D.Selection{'+','.join(n(k)for k in ['targetLeft','targetRight','targetCopies'])+'}';calls.append('D.render(D.run('+','.join([b('npmStyle'),b('check'),old,target,xs('allowedLeft'),xs('allowedRight')])+')) ++ "\\n"')
 # Saved-candidate arithmetic is separately model-only;it is not an execution
 # of Yarn's complete resolver,plugin system,or arbitrary semver comparator.
 calls+=['Nat.show(D.highest(1n,[1n,2n,3n],[1n,2n])) ++ "\\n"','Nat.show(D.highest(1n,[1n],[1n,2n,3n])) ++ "\\n"']
 driver=generated/'Replay.bend';driver.write_text('import Base\nimport ../Dedupe.bend as D\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n');p=subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr;lines=p.stdout.splitlines();assert [s.lower()for s in lines[:-2]]==[s.lower()for s in actual]and lines[-2:]==['2','1']
 refusals=[]
 for name,change in [('schema',lambda v:v.update(schema=2)),('count',lambda v:v.update(rows=v['rows']*10)),('empty-allowed',lambda v:v['rows'][0].update(allowedLeft=[])),('duplicate-allowed',lambda v:v['rows'][0].update(allowedLeft=[1,1])),('unsorted-allowed',lambda v:v['rows'][0].update(allowedLeft=[2,1])),('version-zero',lambda v:v['rows'][0].update(left=0)),('copies',lambda v:v['rows'][0].update(targetCopies=3)),('boolean',lambda v:v['rows'][0].update(check='true'))]:
  bad=copy.deepcopy(data);change(bad);p=replay(bad);assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);refusals.append(name)
 mutations=[]
 for key in FIELDS:
  bad=copy.deepcopy(rows[0]);bad['observed'][key]='changed'
  try:compare(bad,actual[0])
  except AssertionError:mutations.append(key)
  else:raise AssertionError('Changed observed field escaped')
 record=O.read(O.RUNS[0]/'commands.json');bad=copy.deepcopy(record);bad[0]['after']['package.json']['sha256']='0'*64
 try:O.inspect({O.RUNS[0].name:bad})
 except AssertionError:source_mutation=True
 else:raise AssertionError('Changed captured file digest escaped')
 files=[HERE/n for n in ['Dedupe.lean','DedupeCase.lean','Dedupe.bend','probe.py','observations.py','conformance.py','README.md','.gitignore']];files.append(ROOT/'applications/sources/js-dedupe-selections.json')
 for p in files:basis[str(p.relative_to(ROOT))]=O.sha(p.read_bytes())
 receipt=dict(schema=1,scope='Bounded package-manager preview→application comparison;not a shared resolver or arbitrary dedupe proof',nativeCommands=35,freshNodeReads=14,nativeBoundaries=len(rows),rows=rows,modelResults=actual,modelOnlyHighestCases=2,dtoRefusals=refusals,changedObservationFields=mutations,changedCapturedDigestDetected=source_mutation,tools={name:dict(path=str(Path(tool).resolve()),sha256=O.sha(Path(tool).read_bytes()))for name,tool in [('lean',lean),('bend',bend)]},basisSha256=basis,driverSha256=O.sha(driver.read_bytes()),formalWork=str(formal),limits=['Plans decoded from original pre-apply preview;application outcomes come from independent fresh Node/lock/file reads. No general package resolver is modeled.','Normal native npm overlap setup had already deduplicated;separate nested-seed control exercises consolidation. pnpm autoDedupe:false is explicit.','No peer/optional/workspace/alias/override/source-protocol/lock-only/configDependency coverage;current scope is ordinary registry packages,node-modules,scriptsdisabled,Macarm64.','No package-manager,registry,browser,or native collection runs during replay. Incidental cache/log/installation-metadata effects remain distinct from principal selection/placement/manifest fields.'])
 (O.RUNS[0]/'conformance.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items()if k not in ['rows','modelResults','basisSha256']},indent=2))
if __name__=='__main__':main()
