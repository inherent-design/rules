#!/usr/bin/env python3
"""Read-only packaged-bootstrap evidence replay; no JVM/native engine invocation."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import zipfile
from bootstrap_observations import project,sha
from bootstrap_probe import snapshot

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path)
    run=p.parse_args().run.resolve();assert run.parent==ROOT/'applications/evidence'
    setup=json.loads((run/'setup.json').read_text());receipt=json.loads((run/'receipt.json').read_text())
    assert receipt['status']=='complete'and receipt['commands']==29 and receipt['allOwnedGroupsRetired']
    for a,b in [('bootstrap_probe.py','probe.py'),('bootstrap_fixture_engine.py','fixture-engine.py'),('bootstrap_identity_probe.py','identity-probe.py')]:
        assert sha(HERE/a)==sha(run/b)
    amendment=json.loads((run/'precollection-amendment.json').read_text())
    assert sha(run/'preparation-probe.py')==amendment['preparationProducerSha256']
    assert sha(run/'probe.py')==amendment['collectionProducerSha256']==receipt['producerSha256']
    jar=run/'work/distribution/empack-bootstrap.jar';assert sha(jar)==setup['jar']['sha256']==receipt['jarSha256']
    assert sha(run/'work/fixture-engine.py')==setup['executableFixtureSha256']
    metadata=json.loads((run/'jar-build.json').read_text())
    assert metadata['jar_sha256']==sha(jar)
    for path,digest in metadata['sources'].items():
        b=subprocess.check_output(['git','-C',str(ROOT.parent/'empack'),'show',setup['sourceRevision']+':'+path])
        assert hashlib.sha256(b).hexdigest()==digest
    base_classes={}
    with zipfile.ZipFile(jar)as archive:
        for name in archive.namelist():
            if name.startswith('design/inherent/empack/bootstrap/')and name.endswith('.class'):
                data=archive.read(name);assert data[:4]==b'\xca\xfe\xba\xbe'
                major=struct.unpack('>H',data[6:8])[0];assert major==52
                base_classes[name]=dict(major=major,sha256=hashlib.sha256(data).hexdigest())
    assert base_classes
    processes=json.loads((run/'processes.json').read_text());assert len(processes)==29 and all(p['retired']for p in processes)
    commands=json.loads((run/'commands.json').read_text())
    for row in commands:
        case=run/'work/cases'/row['case']
        assert {n:snapshot(case/n)for n in row['after']}==row['after']
        for stream in ['stdout','stderr']:assert sha(run/(row['case']+'.'+stream))==row['streams'][stream]
    exports=json.loads((run/'event-export.json').read_text())['files']
    for entry in exports:
        frozen=run/entry['path'];native=run/'work/cases'/entry['case']/'engine-events.jsonl'
        assert frozen.read_bytes()==native.read_bytes() and sha(frozen)==entry['sha256']
        row=next(r for r in commands if r['case']==entry['case'])
        assert [json.loads(s)for s in frozen.read_text().splitlines()]==row['events']
    identities=json.loads((run/'native-identity.json').read_text())['commands'];assert len(identities)==2
    for c,name in zip(identities,['version','protocol']):
        assert c['exitCode']==0 and c['ownedGroupAbsent']
        for stream in ['stdout','stderr']:assert sha(run/('native-identity-'+name+'.'+stream))==c[stream+'Sha256']
    rows=project(run)
    ledger=ROOT/'applications/sources/empack-bootstrap-selections.json';sources=json.loads(ledger.read_text())
    for pin in sources['sources']:
        b=subprocess.check_output(['git','-C',str(ROOT.parent/'empack'),'show',sources['revision']+':'+pin['path']])
        assert hashlib.sha256(b).hexdigest()==pin['sha256']
    files=[p for p in run.iterdir()if p.is_file()]+list((run/'events').glob('*.jsonl'))+[ledger]
    files += [HERE/n for n in ['Bootstrap.lean','Bootstrap.bend','BootstrapCase.lean','bootstrap_probe.py',
        'bootstrap_fixture_engine.py','bootstrap_identity_probe.py','bootstrap_observations.py','bootstrap_conformance.py']]
    basis={str(p.relative_to(ROOT)):sha(p)for p in sorted(files)}
    gen=HERE/'generated';formal=gen/'bootstrap-formal';artifact=formal/'applications/empack/Bootstrap.olean';artifact.parent.mkdir(parents=True,exist_ok=True)
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    env=dict(os.environ,LEAN_PATH=str(formal),BEND_NO_TELEMETRY='1')
    def call(argv):return subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
    result=call([lean,'-DwarningAsError=true','-o',str(artifact),'applications/empack/Bootstrap.lean']);assert result.returncode==0,result.stdout+result.stderr
    dto=gen/'bootstrap-cases.json'
    def replay(data):
        dto.write_text(json.dumps(data)+'\n')
        return call([lean,'--run','applications/empack/BootstrapCase.lean',str(dto)])
    data=dict(schema=1,cases=[r['input']for r in rows]);expected=[r['expected']for r in rows]
    result=replay(data);assert result.returncode==0,result.stdout+result.stderr
    assert json.loads(result.stdout)==expected,[(r['case'],a,b)for r,a,b in zip(rows,json.loads(result.stdout),expected)if a!=b]
    bit=lambda b:'True{}'if b else'False{}'
    def bend_call(r):
        args=[bit(r[k])for k in ['recordOk','optionsOk','explicit']]+[str(r[k])+'n'for k in ['localState','cache']]+[bit(r[k])for k in ['versionOk','protocolOk']]+[str(r[k])+'n'for k in ['termination','childResult']]
        return 'B.render(B.evaluate('+','.join(args)+'))'
    driver=gen/'BootstrapReplay.bend';driver.write_text('import Base\nimport ../Bootstrap.bend as B\n\ndef main() -> IO(Unit):\n  IO.write('+ ' ++ '.join(bend_call(r)+' ++ "\\n"'for r in data['cases'])+')\n')
    result=call([bend,str(driver)]);assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.splitlines()==expected
    invalids=[dict(data,schema=2)]
    for field,value in [('localState',3),('cache',3),('termination',3),('childResult',130)]:
        row=copy.deepcopy(data['cases'][0]);row[field]=value;invalids.append(dict(schema=1,cases=[row]))
    row=copy.deepcopy(data['cases'][0]);row.pop('protocolOk');invalids.append(dict(schema=1,cases=[row]))
    for invalid in invalids:
        result=replay(invalid);assert result.returncode==2 and result.stderr
    controls=[]
    mutations=[('append-refused',lambda r:r.update(optionsOk=True)),('wrong-explicit-version',lambda r:r.update(versionOk=True)),
        ('wrong-protocol',lambda r:r.update(protocolOk=True)),('empty-offline',lambda r:r.update(cache=1)),
        ('cancel-result',lambda r:r.update(childResult=0)),('parent-loss',lambda r:r.update(termination=1,childResult=7))]
    for name,mutate in mutations:
        old=next(r for r in rows if r['case']==name);changed=copy.deepcopy(old['input']);mutate(changed)
        result=replay(dict(schema=1,cases=[changed]));assert result.returncode==0,result.stderr
        new=json.loads(result.stdout)[0];assert new!=old['expected']
        controls.append(dict(case=name,original=old['expected'],changed=new))
    raw_controls=[]
    def change_raw(name,mutate):
        changed=copy.deepcopy(commands);row=next(r for r in changed if r['case']==name);mutate(row)
        try:projected=project(run,{'commands.json':changed})
        except(AssertionError,KeyError):raw_controls.append(dict(case=name,rejected=True));return
        result=replay(dict(schema=1,cases=[r['input']for r in projected]));assert result.returncode==0,result.stderr
        assert json.loads(result.stdout)!=[r['expected']for r in projected]
        raw_controls.append(dict(case=name,detectedMismatch=True))
    change_raw('wrong-protocol',lambda r:r.update(exitCode=0))
    change_raw('warm-cache',lambda r:r['after'].update(cache=None))
    change_raw('parent-loss',lambda r:next(e for e in r['events']if e['kind']=='cancellation').update(explicit=True,parentLoss=False))
    change_raw('static-append',lambda r:next(e for e in r['events']if e['kind']=='started').update(authenticated=False))
    output=dict(schema=1,capture=str(run.relative_to(ROOT)),nativeCommands=31,modeledJarCommands=len(rows),
        sourcePins=len(sources['sources']),jarSourcePins=len(metadata['sources']),baseClasses=base_classes,
        leanMatches=len(rows),bendMatches=len(rows),schemaRefusals=len(invalids),changedPremises=controls,
        changedNativeObservations=raw_controls,basisSha256=basis,
        limits=['No JVM/native engine invocation by this replay.','Script fixtures model selected probes/control/exit behavior; they do not establish native game/runtime retirement.','Four read-only real-engine checks on macOSarm64:Java17/21/25 andJava25C;noJava8/cross-platform/full-locale claim.','Cache records are authored private state;official acquisition/download/extraction/atomic recovery/concurrent writers untested.','Killed-parent outcome is distinct from observed child EOF/result;no Java finalization claim for SIGKILL.','Source/build manifest correspondence is not dependency reproducibility.'])
    (ROOT/'applications/evidence/empack-bootstrap-conformance.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(leanMatches=len(rows),bendMatches=len(rows),schemaRefusals=len(invalids),changedPremises=len(controls),changedNativeObservations=len(raw_controls),basisFiles=len(basis),sourcePins=len(sources['sources']),baseClasses=len(base_classes))))
if __name__=='__main__':main()
