#!/usr/bin/env python3
"""Replay retained repository boundaries;no restic,Go,or backend execution."""
import argparse,copy,json,os,subprocess
from pathlib import Path
import repository_observations as obs

ROOT=obs.ROOT;HERE=Path(__file__).resolve().parent
OUT=ROOT/'applications/evidence/restic-repository-comparison'
WORK=ROOT/'.build/restic-repository-replay'
KINDS={'init':0,'open':1,'migrate-list':2,'migrate-apply':3}


def bend_request(r):
    values=[str(n)+'n'for n in[KINDS[r['kind']],r['requestedVersion'],r['version']]]
    values+=['True{}'if r[k]else'False{}'for k in['hasKeys','hasSnapshots','otherPassword','knownMigration','unknownMigration','strictUnknown']]
    return 'R.render(R.run(R.Request{'+','.join(values)+'}))'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--public-only',action='store_true');opts=parser.parse_args()
    request,measured,details,basis,excluded=obs.evidence(not opts.public_only)
    assert len(request['cases'])==len(measured)==18
    labels=[d['label']for d in details if d['role']=='modeled-request'];indices={n:i for i,n in enumerate(labels)}
    inputs=copy.deepcopy(request);expected=copy.deepcopy(measured);proposed=[]
    for label in['unknown-migration','migrate-with-unknown','repeat-migration']:
        i=indices[label];candidate=copy.deepcopy(request['cases'][i]);candidate['strictUnknown']=True
        outcome=copy.deepcopy(measured[i]);outcome[0]=1 if candidate['unknownMigration']else outcome[0]
        inputs['cases'].append(candidate);expected.append(outcome)
        proposed.append(dict(basisLabel=label,request=candidate,expected=outcome,evidenceStatus='proposed-model-only;no native candidate'))
    OUT.mkdir(exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=str(WORK),BEND_NO_TELEMETRY='1');lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend')
    def command(args):return subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    target=WORK/'applications/restic/Repository.olean';target.parent.mkdir(parents=True,exist_ok=True)
    p=command([lean,'-DwarningAsError=true','-o',str(target),'applications/restic/Repository.lean']);assert p.returncode==0,p.stdout+p.stderr
    path=WORK/'request.json'
    def replay(value):
        path.write_text(json.dumps(value)+'\n')
        return command([lean,'--run','applications/restic/RepositoryCase.lean',str(path)])
    p=replay(inputs);assert p.returncode==0,p.stdout+p.stderr;assert json.loads(p.stdout)==expected,(p.stdout,expected)
    driver=WORK/'RepositoryReplay.bend';driver.write_text('import Base\nimport '+str(HERE/'Repository.bend')+' as R\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join('('+bend_request(r)+' ++ "\\n")'for r in inputs['cases'])+')\n')
    p=command([bend,str(driver)]);assert p.returncode==0,p.stdout+p.stderr
    rendered=['/'.join([str(o[0]),str(o[1])]+[str(int(b))for b in o[2:]])for o in expected]
    assert p.stdout.splitlines()==rendered,p.stdout
    refused=[]
    for name,edit in[
        ('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='all-restic-backends')),
        ('empty',lambda d:d.update(cases=[])),('bound',lambda d:d.update(cases=d['cases']*2)),
        ('operation',lambda d:d['cases'][0].update(kind='repair')),
        ('stored-format',lambda d:d['cases'][0].update(version=3)),
        ('requested-format',lambda d:d['cases'][0].update(requestedVersion=3)),
        ('output-format-on-open',lambda d:d['cases'][indices['config-v1']].update(requestedVersion=1)),
        ('apply-without-name',lambda d:d['cases'][indices['unknown-migration']].update(unknownMigration=False)),
        ('names-outside-apply',lambda d:d['cases'][0].update(knownMigration=True)),
        ('strict-outside-apply',lambda d:d['cases'][0].update(strictUnknown=True)),
        ('migration-without-config',lambda d:d['cases'][indices['unknown-migration']].update(version=0)),
        ('other-password-on-init',lambda d:d['cases'][0].update(otherPassword=True)),
        ('positive-open-without-keys',lambda d:d['cases'][indices['config-v1']].update(hasKeys=False)),
        ('nonboolean',lambda d:d['cases'][0].update(hasKeys='yes')),
        ('negative-format',lambda d:d['cases'][0].update(version=-1))]:
        bad=copy.deepcopy(inputs);edit(bad);p=replay(bad)
        assert p.returncode==2 and not p.stdout,(name,p.returncode,p.stdout,p.stderr);refused.append(name)
    changed=[]
    for name,label,edit in[
        ('format-admission','unsupported-init',lambda r:r.update(requestedVersion=2)),
        ('key-guard','key-only-init',lambda r:r.update(hasKeys=False)),
        ('snapshot-guard','snapshot-only-init',lambda r:r.update(hasSnapshots=False)),
        ('credential-profile','wrong-password',lambda r:r.update(otherPassword=False)),
        ('known-request','migrate-with-unknown',lambda r:r.update(knownMigration=False)),
        ('requested-name','unknown-migration',lambda r:r.update(knownMigration=True,unknownMigration=False)),
        ('eligible-format','repeat-migration',lambda r:r.update(version=1)),
        ('list-eligibility','list-after-migration',lambda r:r.update(version=1))]:
        bad=copy.deepcopy(inputs);edit(bad['cases'][indices[label]]);p=replay(bad)
        assert p.returncode==0,p.stderr;assert json.loads(p.stdout)!=expected,name;changed.append(name)
    rows=obs.read(obs.CAP/'commands.json');edits=obs.read(obs.CAP/'interventions.json')
    streams={r['label']:{n:(obs.CAP/v['path']).read_text()for n,v in r['streams'].items()}for r in rows}
    raw_indices={r['label']:i for i,r in enumerate(rows)};raw=[]
    def changed_raw(name,edit):
        copy_rows=copy.deepcopy(rows);copy_streams=copy.deepcopy(streams);edit(copy_rows,copy_streams)
        try:_,value,_=obs.observe(copy_rows,edits,copy_streams)
        except (AssertionError,KeyError):raw.append(name);return
        assert value!=measured,name;raw.append(name)
    changed_raw('unknown-exit',lambda rs,ss:rs[raw_indices['unknown-migration']].update(exitCode=1))
    changed_raw('unknown-diagnostic',lambda rs,ss:ss['unknown-migration'].update(stderr=''))
    changed_raw('applied-notification',lambda rs,ss:ss['migrate-with-unknown'].update(stdout='checking repository integrity...\n'))
    changed_raw('skipped-status',lambda rs,ss:rs[raw_indices['repeat-migration']].update(exitCode=1))
    def false_format(rs,ss):
        cfg=json.loads(ss['config-v2']['stdout']);cfg['version']=1;ss['config-v2']['stdout']=json.dumps(cfg)
    changed_raw('persisted-format',false_format)
    changed_raw('key-guard-loss',lambda rs,ss:rs[raw_indices['key-only-init']]['after'].update(files={}))
    def changed_pack(rs,ss):
        files=rs[raw_indices['migrate-with-unknown']]['after']['files'];key=next(p for p in files if p.startswith('data/'));files[key]['mtimeNs']=0
    changed_raw('migration-pack-change',changed_pack)
    changed_raw('list-notification',lambda rs,ss:ss['list-after-migration'].update(stdout='available migrations:\n  upgrade_repo_v2\tupgrade a repository to version 2\n'))
    p=replay(inputs);assert p.returncode==0,p.stderr
    controls=dict(schema=1,nativeCommands=22,comparedNativeRequests=18,setupOrReadbackCommands=4,proposedModelOnlyCases=3,leanLaws=10,bendLaws=9,decoderRefusals=refused,changedPremises=changed,changedRawObservations=raw,privateChecksExcluded=excluded,scope='Local repository boundaries,admitted usable-key/config/IO context. No remote backend,cryptographic refinement,force/crash/reupload/concurrency qualification,or native strictUnknown candidate.')
    artifacts={'input.json':request,'measured.json':measured,'details.json':details,'proposed.json':proposed,'basis.json':basis,'controls.json':controls}
    for name,value in artifacts.items():
        if opts.public_only:
            stored=obs.read(OUT/name)
            if name=='controls.json':stored['privateChecksExcluded']=excluded
            assert stored==value,name
        else:(OUT/name).write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(dict(nativeRequests=18,proposedCases=3,decoderRefusals=len(refused),changedPremises=len(changed),changedRawObservations=len(raw),publicOnly=opts.public_only,privateChecksExcluded=len(excluded))))


if __name__=='__main__':main()
