#!/usr/bin/env python3
"""Replay frozen Cargo freshness/partial-output evidence;never invoke Cargo/rustc."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from freshness_observations import project,sha
from freshness_probe import image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);run=p.parse_args().run.resolve()
    assert run.parent==ROOT/'applications/evidence'
    receipt=json.loads((run/'receipt.json').read_text());setup=json.loads((run/'setup.json').read_text());work=Path(receipt['work'])
    assert receipt['status']=='complete'and receipt['commands']==31 and receipt['builds']==15 and receipt['allOwnedGroupsRetired']
    assert sha(HERE/'freshness_probe.py')==sha(run/'probe.py')==receipt['producerSha256']
    assert image(work/'project')==receipt['sourceAfter']and not(work/'target').exists()
    assert (run/'script-invocations.log').read_bytes()==(work/'script-invocations.log').read_bytes()
    assert sha(Path(receipt['retainedProduct']['path']))==receipt['retainedProduct']['sha256']
    assert all(p['retired']for p in json.loads((run/'processes.json').read_text()))
    commands=json.loads((run/'commands.json').read_text())
    for c in commands:
        assert c['ownedGroupAbsent']and not c['timedOut']
        for stream in ['stdout','stderr']:assert sha(run/(c['case']+'.'+stream))==c['streams'][stream]
    for edit in json.loads((run/'edits.json').read_text()):
        if edit['action']['file'] is not None:
            a,b=edit['before']['project']['input.txt'],edit['after']['project']['input.txt']
            assert int(b['mtimeNs'])>int(a['mtimeNs'])and a['sha256']!=b['sha256']
    projected=project(run);rows=projected['cases'];assert len(rows)==16
    # The compiled result is independently run after every attempt, including
    # script/compiler failures. Byte equality is not a successful job verdict.
    recover=next(c for c in commands if c['case']=='recover')
    assert recover['before']['binary']==recover['after']['binary']
    assert any(m['reason']=='compiler-artifact'and m['target']['kind']==['bin']and not m['fresh']for m in recover['messages'])
    ledger=ROOT/'applications/sources/cargo-freshness-selections.json';source=json.loads(ledger.read_text())
    for pin in source['sources']:assert sha(ROOT/pin['localCache'])==pin['sha256']
    files=[p for p in run.rglob('*')if p.is_file()]+[ledger]
    files += [HERE/n for n in ['Freshness.lean','Freshness.bend','FreshnessCase.lean','freshness_probe.py','freshness_observations.py','freshness_conformance.py']]
    basis={str(p.relative_to(ROOT)):sha(p)for p in sorted(files)}
    gen=HERE/'generated';formal=gen/'freshness-formal';artifact=formal/'applications/cargo/Freshness.olean';artifact.parent.mkdir(parents=True,exist_ok=True)
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend');env=dict(os.environ,LEAN_PATH=str(formal),BEND_NO_TELEMETRY='1')
    def call(argv):return subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
    result=call([lean,'-DwarningAsError=true','-o',str(artifact),'applications/cargo/Freshness.lean']);assert result.returncode==0,result.stdout+result.stderr
    path=gen/'freshness-cases.json'
    def replay(data):
        path.write_text(json.dumps(data)+'\n');return call([lean,'--run','applications/cargo/FreshnessCase.lean',str(path)])
    data=dict(schema=1,cases=[r['input']for r in rows]);expected=[r['expected']for r in rows]
    result=replay(data);assert result.returncode==0,result.stdout+result.stderr
    assert json.loads(result.stdout)==expected,[(r['case'],a,b)for r,a,b in zip(rows,json.loads(result.stdout),expected)if a!=b]
    bit=lambda b:'True{}'if b else'False{}'
    def bend_call(r):
        s=r['state'];state='F.FState{'+','.join([bit(s['scriptValid']),str(s['basis'])+'n',str(s['generated'])+'n',bit(s['rustValid']),str(s['binary'])+'n',str(s['macroValue'])+'n',str(s['runs'])+'n'])+'}'
        return 'F.render(F.evaluate('+','.join([state,str(r['action'])+'n',str(r['basis'])+'n',str(r['dataValue'])+'n',str(r['macroValue'])+'n',bit(r['fail'])])+'))'
    driver=gen/'FreshnessReplay.bend';driver.write_text('import Base\nimport ../Freshness.bend as F\n\ndef main() -> IO(Unit):\n  IO.write('+ ' ++ '.join(bend_call(r)+' ++ "\\n"'for r in data['cases'])+')\n')
    result=call([bend,str(driver)]);assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.splitlines()==expected
    invalids=[dict(data,schema=2)]
    for field,value in [('action',2),('basis',17),('dataValue',0),('macroValue',0)]:
        row=copy.deepcopy(data['cases'][0]);row[field]=value;invalids.append(dict(schema=1,cases=[row]))
    row=copy.deepcopy(data['cases'][0]);row.pop('fail');invalids.append(dict(schema=1,cases=[row]))
    for d in invalids:
        result=replay(d);assert result.returncode==2 and result.stderr
    controls=[]
    mutations=[('same',lambda r:r['state'].update(scriptValid=False)),('macro-env',lambda r:r.update(macroValue=1)),
        ('fail',lambda r:r.update(fail=False)),('recover',lambda r:r['state'].update(scriptValid=True)),
        ('missing-output',lambda r:r['state'].update(generated=r['state']['binary']))]
    for name,mutate in mutations:
        old=next(r for r in rows if r['case']==name);changed=copy.deepcopy(old['input']);mutate(changed)
        result=replay(dict(schema=1,cases=[changed]));assert result.returncode==0,result.stderr
        after=json.loads(result.stdout)[0];assert after!=old['expected'];controls.append(dict(case=name,original=old['expected'],changed=after))
    raw=[]
    def raw_control(name,mutate):
        changed=copy.deepcopy(commands);row=next(r for r in changed if r['case']==name);mutate(row)
        try:other=project(run,{'commands.json':changed})['cases']
        except(AssertionError,KeyError):raw.append(dict(case=name,rejected=True));return
        result=replay(dict(schema=1,cases=[r['input']for r in other]));assert result.returncode==0,result.stderr
        assert json.loads(result.stdout)!=[r['expected']for r in other];raw.append(dict(case=name,detectedMismatch=True))
    raw_control('same',lambda r:r.update(messages=[]))
    raw_control('fail',lambda r:r['after'].update(binary=None))
    raw_control('tracked-empty',lambda r:r['after'].update(generated=r['before']['generated']))
    raw_control('cold',lambda r:r['after'].update(journal=''))
    output=dict(schema=1,capture=str(run.relative_to(ROOT)),nativeCommands=31,modeledAttempts=len(rows),runtimeChecks=15,
        leanMatches=len(rows),bendMatches=len(rows),schemaRefusals=len(invalids),changedPremises=controls,
        changedNativeObservations=raw,sourcePins=len(source['sources']),catalog=dict(bases=projected['bases'],values=projected['values']),
        runtimeIdentities=projected['runtimeIdentities'],basisSha256=basis,
        limits=['No Cargo/rustc/runtime execution by replay.','One small Cargo 1.92 context on macOS arm64; no general mtime/hash/feature/dependency graph decoder.','Labels distinguish observed optional environment, file, and failed-input meanings; not production fingerprint serialization.','Fresh JSON can replay cached script output; actual runs come from a separate owned journal.','Target cleaned; one small final product, source, and journal retained; interrupted work, concurrency, registry, and proc macros unqualified.'])
    (ROOT/'applications/evidence/cargo-freshness-conformance.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(leanMatches=len(rows),bendMatches=len(rows),schemaRefusals=len(invalids),changedPremises=len(controls),changedNativeObservations=len(raw),basisFiles=len(basis),sourcePins=len(source['sources']))))
if __name__=='__main__':main()
