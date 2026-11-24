#!/usr/bin/env python3
"""Compare retained manifest effects/callback inputs with scoped models."""
import copy,hashlib,json,os
from pathlib import Path
import subprocess
import observations

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
RUN=observations.RUN
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
MODES=['simple','mixed','chain','late-throw','same-object','equal-objects']


def license(value):
    if value is None:return 0
    assert value=='MIT';return 1
def image(command,phase):
    root=json.loads(command[phase]['package.json']['text']);child=json.loads(command[phase]['packages/child/package.json']['text'])
    obj=root.get('studyObject');assert obj in [None,{'mode':'plain'}]
    assert child.get('studyCounter',0)==0
    return [root['studyCounter'],license(root.get('license')),license(child.get('license')),int(obj is not None)]
def build(commands):
    result=[]
    for c in commands:
        if c['label']=='install':continue
        before=image(c,'before');mode=MODES.index(c['case']);fix='--fix'in c['argv']
        assert 'const MODE='+json.dumps(c['case'])+';'in c['before']['yarn.config.cjs']['text']
        passes=len({v['pass']for v in c['ruleVisits']})
        result.append(dict(case=c['case'],label=c['label'],input=dict(mode=mode,fix=fix,counter=before[0],rootLicense=before[1],childLicense=before[2],object=before[3]),
            expected='/'.join(map(str,[*image(c,'after'),c['outcome']['exitCode'],passes])),visits=c['ruleVisits'],presentation=observations.presentation(c)))
    assert len(result)==17;return result
def compare_current(row,value):assert row['expected']==value,(row['case'],row['label'],row['expected'],value)
def compare_guidance(row,value):assert row['presentation']['humanGuidance']==value
def compare_inputs(row,images):
    visits=row['visits'];passes=sorted({v['pass']for v in visits});assert passes==list(range(1,len(images)+1))
    for p,s in zip(passes,images):
        current=[v for v in visits if v['pass']==p];root=next(v for v in current if v['workspace']=='.')
        assert root['counter']==s[0]and license(root['license'])==s[1]
        children=[v for v in current if v['workspace']=='packages/child']
        if children:assert len(children)==1 and children[0]['counter']==0 and license(children[0]['license'])==s[2]
        else:assert row['case']=='late-throw'and p==2


def main():
    receipt,commands=observations.inspect();rows=build(commands);generated=HERE/'generated';generated.mkdir(exist_ok=True)
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend');env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1')
    target=ROOT/'.build/formal/applications/yarn-constraints/Constraints.olean';target.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.run([lean,'-DwarningAsError=true','-o',str(target),'applications/yarn-constraints/Constraints.lean'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    data=dict(schema=1,profile='owned-modern-js-rules',rows=[r['input']for r in rows]);path=generated/'constraints.json'
    def replay(value):
        path.write_text(json.dumps(value)+'\n');return subprocess.run([lean,'--run','applications/yarn-constraints/ConstraintsCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    p=replay(data);assert p.returncode==0,p.stdout+p.stderr;actual=json.loads(p.stdout);assert len(actual)==len(rows)
    for r,v in zip(rows,actual):
        compare_current(r,v['current']);compare_inputs(r,v['inputs']);compare_guidance(r,v['humanGuidance'])
    calls=[]
    for r in rows:
        i=r['input'];state='S.CImage{'+','.join(str(i[k])+'n'for k in ['counter','rootLicense','childLicense','object'])+'}'
        call='S.current('+str(i['mode'])+'n,'+('True{}'if i['fix']else'False{}')+','+state+')'
        guide='S.human_guidance('+str(i['mode'])+'n,'+('True{}'if i['fix']else'False{}')+','+state+')'
        calls.append('S.render('+call+') ++ "/" ++ Nat.show(S.proposed_status('+str(i['mode'])+'n,'+call+')) ++ "/" ++ Bool.pick(String,'+guide+',"1","0") ++ "\\n"')
    driver=generated/'ConstraintsCase.bend';driver.write_text('import Base\nimport ../Constraints.bend as S\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
    p=subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    assert p.stdout.splitlines()==[v['current']+'/'+str(v['proposal'])+'/'+str(int(v['humanGuidance']))for v in actual]
    refusals=[]
    for name,edit in [('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='all-yarn-rules')),('count',lambda d:d.update(rows=d['rows']*10)),
        ('mode',lambda d:d['rows'][0].update(mode=6)),('counter',lambda d:d['rows'][0].update(counter=13)),('license',lambda d:d['rows'][0].update(rootLicense=3)),
        ('object',lambda d:d['rows'][0].update(object=2)),('boolean',lambda d:d['rows'][0].update(fix='true'))]:
        bad=copy.deepcopy(data);edit(bad);p=replay(bad);assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);refusals.append(name)
    mutations=[]
    for i in range(6):
        row=copy.deepcopy(rows[0]);parts=row['expected'].split('/');parts[i]='999';row['expected']='/'.join(parts)
        try:compare_current(row,actual[0]['current'])
        except AssertionError:mutations.append('outcome-'+str(i))
        else:raise AssertionError('Outcome mutation escaped')
    for i in range(3):
        bad=copy.deepcopy(actual[0]['inputs']);bad[0][i]=999
        try:compare_inputs(rows[0],bad)
        except AssertionError:mutations.append('input-'+str(i))
        else:raise AssertionError('Input mutation escaped')
    bad=copy.deepcopy(rows[0]);bad['presentation']['humanGuidance']=not bad['presentation']['humanGuidance']
    try:compare_guidance(bad,actual[0]['humanGuidance'])
    except AssertionError:mutations.append('human-guidance')
    else:raise AssertionError('Guidance mutation escaped')
    ledger=json.loads((ROOT/'applications/sources/yarn-constraints-selections.json').read_text())
    for s in ledger['sources']:assert sha(ROOT/s['cache'])==s['sha256']
    files=[HERE/n for n in ['Constraints.lean','Constraints.bend','ConstraintsCase.lean','probe.py','observations.py','conformance.py']]
    files +=[ROOT/'applications/sources/yarn-constraints-selections.json']
    old=ROOT/json.loads((RUN/'setup-correction.json').read_text())['failedCapture']
    files +=[p for run in [RUN,old]for p in run.rglob('*')if p.is_file()and'work'not in p.relative_to(run).parts and p.name!='conformance.json']
    report=dict(schema=1,scope='Owned Modern JS callbacks/current command loop versus source/native effects;final-validation candidate remains proposed.',nativeCommands=23,nativeConstraintCommands=17,
        nativeOutcomeComparisons=len(rows),callbackTraceComparisons=len(rows),humanGuidanceComparisons=len(rows),callbackWorkspaceVisits=143,researchRefusals=refusals,observationMutations=mutations,
        comparisons=[{**r,'model':v}for r,v in zip(rows,actual)],basisSha256={str(p.relative_to(ROOT)):sha(p)for p in sorted(set(files))},driverSha256=sha(driver),
        tools={n:dict(path=str(Path(p).resolve()),sha256=sha(Path(p)))for n,p in [('lean',lean),('bend',bend)]},
        limits=['No new Yarn/install/constraint execution. Models cover six selected owned rules and a flat manifest projection,not the constraint language or engine/registry as a whole.',
                'Only root counter/license and visited child license are compared at callback entry. Object presence has final disk observations but no per-pass callback witness.',
                'Candidate status has pure cross-model agreement and conditional laws,not patched/native execution. It neither undoes saved effects nor qualifies arbitrary callback reexecution/concurrency.',
                'Callback visits are in-memory observations;per-pass manifest disk writes are source-derived,not syscall receipts. Final manifests/lock/config are independently captured.',
                'The initial invalid install mode is a preserved setup failure,excluded from constraint outcomes. No Prolog,dependency compatibility,publication or complete parent promotion.'])
    (RUN/'conformance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in['comparisons','basisSha256']},indent=2))


if __name__=='__main__':main()
