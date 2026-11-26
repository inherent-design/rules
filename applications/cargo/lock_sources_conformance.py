"""Pure retained lock/source comparison; never runs Cargo,Git,or a compiler."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import lock_sources_observations as observations

ROOT,HERE,CAP=observations.ROOT,observations.HERE,observations.CAP
FORMAL=ROOT/'.build/cargo-lock-formal'
write=lambda p,v:p.write_text(json.dumps(v,indent=2)+'\n')


def main():
    assert sys.argv[1:] in [[],['--public-only']]
    inputs,measured,details,basis,excluded=observations.evidence(not sys.argv[1:])
    FORMAL.mkdir(parents=True,exist_ok=True)
    for name,value in [('model-input.json',inputs),('measured.json',measured),('details.json',details)]:write(CAP/name,value)
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    env=dict(os.environ,LEAN_PATH=str(FORMAL),BEND_NO_TELEMETRY='1')
    target=FORMAL/'applications/cargo/LockSources.olean';target.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.run([lean,'-DwarningAsError=true','-o',str(target),str(HERE/'LockSources.lean')],cwd=ROOT,env=env,capture_output=True,text=True);assert p.returncode==0,p.stdout+p.stderr
    path=FORMAL/'input.json';command=[lean,'--run',str(HERE/'LockSourcesCase.lean'),str(path)]
    def replay(value):
        write(path,value);return subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True)
    p=replay(inputs);assert p.returncode==0,p.stdout+p.stderr;actual=json.loads(p.stdout);assert actual==measured,(actual,measured)
    boolean=lambda v:'True{}' if v else 'False{}'
    def request(r):
        cache='L.Cache{'+','.join([str(r['cacheHead'])+'n',boolean(r['hasA']),boolean(r['hasB'])])+'}'
        fields=[str(['path','git','patch'].index(r['source']))+'n',str(['metadata','generate','update'].index(r['operation']))+'n']
        fields += [boolean(r[k]) for k in ['locked','offline','pathV2','remoteB']]
        fields += [str(r['beforeLock'])+'n',cache]
        return 'L.Request{'+','.join(fields)+'}'
    calls=['L.render(L.run('+request(r)+'))' for r in inputs['cases']]
    driver=HERE/'_lock_sources_replay.bend';driver.write_text('import Base\nimport LockSources.bend as L\ndef main() -> IO(Unit):\n  IO.write('+' ++ "\\n" ++ '.join(calls)+')\n')
    try:p=subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True)
    finally:driver.unlink()
    assert p.returncode==0,p.stdout+p.stderr;assert [[int(v) for v in line.split('/')] for line in p.stdout.splitlines()]==measured
    controls=[]
    for name,change in [
        ('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='general-cargo-resolver')),
        ('empty',lambda d:d.update(cases=[])),('count',lambda d:d.update(cases=d['cases']*2)),
        ('source',lambda d:d['cases'][0].update(source='registry')),
        ('operation',lambda d:d['cases'][0].update(operation='build')),
        ('flag-type',lambda d:d['cases'][0].update(offline='true')),
        ('lock-identity',lambda d:d['cases'][0].update(beforeLock=9)),
        ('cache-coverage',lambda d:d['cases'][8].update(hasA=False)),
        ('lock-source-context',lambda d:d['cases'][0].update(beforeLock=3)),
        ('git-regenerate',lambda d:d['cases'][8].update(operation='generate')),
        ('cold-patch-catalog',lambda d:d['cases'][14].update(cacheHead=0,hasA=False,hasB=False))]:
        bad=copy.deepcopy(inputs);change(bad);q=replay(bad);assert q.returncode==2 and not q.stdout,(name,q.stdout,q.stderr);controls.append(dict(kind='DTO',name=name,refused=True))
    for name,index,change in [
        ('allow-lock-write',0,lambda r:r.update(locked=False)),
        ('allow-local-source-acquisition',6,lambda r:r.update(offline=False)),
        ('remove-cached-source',8,lambda r:r.update(cacheHead=0,hasA=False,hasB=False)),
        ('same-remote-head',11,lambda r:r.update(remoteB=False)),
        ('remove-compatible-patch',14,lambda r:r.update(source='git'))]:
        bad=copy.deepcopy(inputs);change(bad['cases'][index]);q=replay(bad);assert q.returncode==0 and json.loads(q.stdout)!=measured,(name,q.stderr);controls.append(dict(kind='changed-premise',name=name,refused=True))
    rows=observations.load(CAP/'receipt.json')['rows'];setup=observations.load(CAP/'setup.json')
    streams={r[k]['path']:(CAP/r[k]['path']).read_text() for r in rows for k in ['stdout','stderr']}
    def mutate_metadata(raw,index,field,value):
        key=raw[index]['stdout']['path'];data=json.loads(value['streams'][key]);pkg=next(p for p in data['packages'] if p['name']=='rules-shared')
        pkg[field]=value['value'];value['streams'][key]=json.dumps(data)
    changes=[]
    bad=copy.deepcopy(rows);bad[0]['exitCode']=0;changes.append(('false-success',bad,copy.deepcopy(streams)))
    bad=copy.deepcopy(rows);bad[7]['after']['files']['git-app/Cargo.lock']=copy.deepcopy(rows[8]['after']['files']['git-app/Cargo.lock']);changes.append(('refused-lock-write',bad,copy.deepcopy(streams)))
    bad=copy.deepcopy(rows);bad[3]['after']['files']['path-app/Cargo.lock']['mtimeNs']+=1;changes.append(('formatting-control-rewrite',bad,copy.deepcopy(streams)))
    for name,field,value in [('precise-source','source','git+'+setup['localGitUrl']+'?branch=main#'+setup['firstGit']),('opaque-key','id','wrong-package-id')]:
        altered=copy.deepcopy(streams);mutate_metadata(rows,12,field,dict(streams=altered,value=value));changes.append((name,copy.deepcopy(rows),altered))
    bad=copy.deepcopy(rows);ref=next(k for k in bad[-1]['after']['cache'] if k.startswith('git/db/') and k.endswith('/refs/remotes/origin/main'));bad[-1]['after']['cache'][ref]['sha256']='0'*64;changes.append(('unknown-cache-head',bad,copy.deepcopy(streams)))
    for name,bad,altered in changes:
        try:_,value,_=observations.observe(bad,setup,altered);refused=value!=actual
        except (AssertionError,ValueError,KeyError,TypeError):refused=True
        assert refused,name;controls.append(dict(kind='changed-raw-observation',name=name,refused=True))
    write(CAP/'basis.json',basis);write(CAP/'controls.json',controls)
    report=dict(schema=1,nativeCargoRequests=16,ownedGitScaffoldCommands=7,incidentalVersionQueries=2,
        comparedFields=['exit status','lock selection','cached branch head','retained cached commits','metadata exact selection','metadata package-key class','semantic lock-selection change'],matched=True,
        modelLaws=dict(lean=14,bend=14),controls=len(controls),basisFiles=len(basis),privateExcluded=excluded,
        tools={n:dict(path=str(Path(p).resolve()),sha256=observations.sha(Path(p))) for n,p in [('lean',lean),('bend',bend)]},
        limits=['Owned path/local-file Git and one compatible patch;no registry or general resolver qualification.',
                'Cache usability/commit coverage is an admitted controlled-fixture premise,not a Git object validator.',
                'Remote-head input is supported by the controlled Git transcript/source snapshots,not arbitrary external-writer observation.',
                'Lock selection is semantic;raw byte/mode/mtime preservation is checked separately on locked cases.',
                'Metadata ID remains opaque;selected raw fields are checked before mapping to fixture classes.',
                'Same status101 covers different failures;diagnostic phase labels are retained separately from the model.',
                'Ordinary source equality,full internal identity,and external metadata serialization are distinct source contracts.',
                'No build/check/run invocation;Cargo may query rustc information. No physical compiler-process census.',
                'Source replacement,equivalent mirrors,registry/MSRV constraints,corrupted caches,concurrency and other platforms remain open.',
                'Pure replay only;no Cargo,Git,compiler,desktop,registry,or source acquisition execution.'])
    write(CAP/'conformance.json',report);print(json.dumps(dict(nativeCargoRequests=16,matched=True,controls=len(controls),basisFiles=len(basis),privateExcluded=len(excluded))))


if __name__=='__main__':main()
