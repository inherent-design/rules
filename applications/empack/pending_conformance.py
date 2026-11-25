#!/usr/bin/env python3
"""Compare frozen pending observations with Lean/Bend; never execute empack."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile
from pending_observations import project, sha
from pending_continue_probe import snapshot

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path)
    run=p.parse_args().run.resolve()
    assert run.parent==ROOT/'applications/evidence'
    rows=project(run)
    # Original executed producers remain separate, including the failed
    # collector. Its assertion failure is not native product failure.
    for current,frozen in [('pending_probe.py','probe.py'),('pending_continue_probe.py','continuation-probe.py'),('pending_retained_probe.py','retained-probe.py')]:
        assert sha(HERE/current)==sha(run/frozen)
    assert json.loads((run/'collector-correction.json').read_text())['nativeFailure'] is False
    counts=[]
    for phase in ['','partial-','retained-','finish-']:
        commands=json.loads((run/(phase+'commands.json')).read_text());counts.append(len(commands))
        processes=json.loads((run/('owned-processes.json' if not phase else phase+'processes.json')).read_text())
        assert all(x['retired']for x in processes)
        for c in commands:
            assert c['ownedGroupAbsent'] and not c['timedOut']
            for stream in ['stdout','stderr']:
                assert sha(run/(c['case']+'.'+stream))==c['streams'][stream]
    assert counts==[4,8,5,3]
    final=json.loads((run/'finish-completed-list-after.json').read_text())
    assert {n:snapshot(run/'work'/n)for n in final}==final
    for name in ['empack.yml','empack.lock']:
        assert (run/('initial-'+name)).read_bytes()==(run/'work/project'/name).read_bytes()
    assets=json.loads((run/'assets.json').read_text())
    assert (run/'retained-original.bin').read_bytes()==assets['first']['text'].encode()
    restored=json.loads((run/'retained-restoration.json').read_text())
    assert restored['originalBytesModeInodeMtimeRestored'] and restored['ctimeNotPreserved']
    assert sha(run/'work'/restored['path'])==restored['sha256']==assets['first']['sha256']
    product=json.loads((run/'finish-result.json').read_text())['artifact'];archive=run/'work'/product['path']
    assert archive.stat().st_size==product['bytes'] and sha(archive)==product['sha256']
    with zipfile.ZipFile(archive)as z:
        members={n:dict(bytes=len(z.read(n)),sha256=hashlib.sha256(z.read(n)).hexdigest())for n in z.namelist()}
        assert members==product['members']
        for n in ['first','second']:assert z.read('overrides/resourcepacks/'+n+'.zip')==assets[n]['text'].encode()
    ledger=ROOT/'applications/sources/empack-pending-selections.json'
    source=json.loads(ledger.read_text())
    for pin in source['sources']:
        b=subprocess.check_output(['git','-C',str(ROOT.parent/'empack'),'show',source['revision']+':'+pin['path']])
        assert hashlib.sha256(b).hexdigest()==pin['sha256']
    files=[p for p in run.iterdir()if p.is_file()]
    files += [HERE/n for n in ['Pending.lean','Pending.bend','PendingCase.lean','pending_probe.py','pending_continue_probe.py',
        'pending_retained_probe.py','pending_observations.py','pending_conformance.py']]+[ledger]
    basis={str(f.relative_to(ROOT)):sha(f)for f in sorted(files)}
    generated=HERE/'generated';formal=generated/'pending-formal'
    artifact=formal/'applications/empack/Pending.olean';artifact.parent.mkdir(parents=True,exist_ok=True)
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    env=dict(os.environ,LEAN_PATH=str(formal),BEND_NO_TELEMETRY='1')
    def call(argv):return subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
    result=call([lean,'-DwarningAsError=true','-o',str(artifact),'applications/empack/Pending.lean'])
    assert result.returncode==0,result.stdout+result.stderr
    path=generated/'pending-cases.json'
    def lean_replay(data):
        path.write_text(json.dumps(data)+'\n')
        return call([lean,'--run','applications/empack/PendingCase.lean',str(path)])
    data=dict(schema=1,cases=[r['input']for r in rows]);expected=[r['expected']for r in rows]
    result=lean_replay(data)
    assert result.returncode==0,result.stdout+result.stderr
    assert json.loads(result.stdout)==expected,[(r['case'],a,b)for r,a,b in zip(rows,json.loads(result.stdout),expected)if a!=b]
    bit=lambda b:'True{}'if b else'False{}'
    def bend_call(r):
        s=r['state'];state='P.PState{'+','.join([str(s['record'])+'n',bit(s['first']),bit(s['second']),str(s['firstBacking'])+'n',str(s['secondBacking'])+'n',bit(s['published'])])+'}'
        supplies='['+','.join('P.PSupply{'+str(f['key'])+'n,'+str(f['content'])+'n}'for f in r['files'])+']'
        found='['+','.join(str(v)+'n'for v in r['discovered'])+']'
        return 'P.render(P.evaluate('+','.join([state,str(r['action'])+'n',str(r['selected'])+'n',supplies,found])+'))'
    driver=generated/'PendingReplay.bend'
    driver.write_text('import Base\nimport ../Pending.bend as P\n\ndef main() -> IO(Unit):\n  IO.write('+ ' ++ '.join(bend_call(r)+' ++ "\\n"'for r in data['cases'])+')\n')
    result=call([bend,str(driver)])
    assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.splitlines()==expected
    invalids=[dict(data,schema=2),dict(schema=1,cases=[dict(data['cases'][0],action=4)]),
        dict(schema=1,cases=[dict(data['cases'][0],state=dict(data['cases'][0]['state'],record=3))])]
    for field in ['selected','files','discovered']:
        row=copy.deepcopy(data['cases'][0]);row.pop(field);invalids.append(dict(schema=1,cases=[row]))
    for invalid in invalids:
        result=lean_replay(invalid);assert result.returncode==2 and result.stderr
    # Falsify meaning-bearing premises, rather than only rechecking labels.
    controls=[]
    mutations=[('partial-wrong-bytes',lambda r:r['files'][0].update(content=1)),
        ('partial-first',lambda r:r['files'][0].update(key=9)),
        ('retained-corrupt-resume',lambda r:r['state'].update(firstBacking=1)),
        ('retained-old-id',lambda r:r.update(selected=2)),
        ('finish-discover',lambda r:r.update(discovered=[]))]
    for name,mutate in mutations:
        original=next(r for r in rows if r['case']==name);changed=copy.deepcopy(original['input']);mutate(changed)
        result=lean_replay(dict(schema=1,cases=[changed]));assert result.returncode==0,result.stderr
        observed=json.loads(result.stdout)[0];assert observed!=original['expected']
        controls.append(dict(case=name,original=original['expected'],changed=observed))
    adapter_controls=[]
    def adapter_control(label, filename, mutate):
        value=json.loads((run/filename).read_text())
        mutate(value)
        try:
            changed=project(run,{filename:value})
        except (AssertionError,KeyError):
            adapter_controls.append(dict(case=label,rejected=True));return
        result=lean_replay(dict(schema=1,cases=[r['input']for r in changed]))
        assert result.returncode==0,result.stderr
        assert json.loads(result.stdout)!=[r['expected']for r in changed],label
        adapter_controls.append(dict(case=label,detectedMismatch=True))
    adapter_control('retained-label','partial-retained-list.stdout',
        lambda v:v['operations'][0]['inputs'][0].update(verification='not supplied; verification required'))
    def change_record(v):
        before=json.loads((run/'partial-first-before.json').read_text())
        for k in v['state']:
            if k.startswith('pending-builds/') and k.endswith('.json'):
                v['state'][k]['sha256']=before['state'][k]['sha256']
    adapter_control('partial-recipe-not-replaced','partial-first-after.json',change_record)
    def hide_corruption(v):
        key='pending-content/'+assets['first']['sha256']+'.blob'
        v['state'][key]['sha256']=assets['first']['sha256']
    adapter_control('corrupt-byte-image','retained-corrupt-list-after.json',hide_corruption)
    def remove_product(v):
        for k in list(v['project']):
            if k.endswith('.mrpack'):del v['project'][k]
    adapter_control('published-file-image','finish-discover-after.json',remove_product)
    output=dict(schema=1,scope='17 frozen installed0.8.8 pending commands; 3 earlier fixture/build commands checked separately.',
        capture=str(run.relative_to(ROOT)),nativeCommands=20,modeledCommands=len(rows),sourcePins=len(source['sources']),
        leanMatches=len(rows),bendMatches=len(rows),schemaRefusals=len(invalids),changedPremises=controls,
        changedNativeObservations=adapter_controls,
        artifact=dict(bytes=product['bytes'],sha256=product['sha256']),basisSha256=basis,
        limits=['No native CLI invocation by this replay.','No whole cache/lease, wait/browser, import/sync/instance pending, interrupted-save, concurrent writer, weak-hash ambiguity or platform qualification.','Read-only inspection is not retained-byte verification; preview still reconstructs/restores before suppressing discovery/publication.','Opaque selectors and byte tokens are finite observations, not cryptographic proofs or a production state encoder.'])
    (ROOT/'applications/evidence/empack-pending-conformance.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(leanMatches=len(rows),bendMatches=len(rows),schemaRefusals=len(invalids),changedPremises=len(controls),changedNativeObservations=len(adapter_controls),basisFiles=len(basis),sourcePins=len(source['sources']))))

if __name__=='__main__':main()
