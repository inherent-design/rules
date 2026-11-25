#!/usr/bin/env python3
"""Pure replay of frozen install/catalog/removal images; no native tool runs."""
import copy,hashlib,json,os,subprocess
from pathlib import Path
import observations

ROOT=observations.ROOT
HERE=Path(__file__).resolve().parent
RUN=observations.RUN
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def build(commands,controls,follow,state):
    rows=[]
    installs={'untracked-collision':1,'force-initial':1,'path-refresh':1,'compile-refusal':1,'partial-replacement':2,'complete-replacement':2,'new-bin-replace-failure':2}
    actions={c['case']:i for i,c in enumerate(controls)}
    def emit(c,kind,source,action=0):
        name=c['case'];before=state(c['before']);after=state(c['after'])
        value=dict(kind=kind,**before,force=name in ['force-initial','new-bin-replace-failure'],compileOk=name!='compile-refusal',version=installs.get(name,1),
                   selectA=name in ['uninstall-a-with-missing-b','uninstall-manual-a']or(name=='uninstall-rest'and before['aOwner']!=0),
                   selectB=name in ['uninstall-rest','new-bin-uninstall'],action=action)
        expected='/'.join(str(int(after[k]))for k in ['aBody','aOwner','bBody','bOwner','metadata'])+'/'+str(c['outcome']['exitCode']if source=='command'else 0)
        rows.append(dict(case=name,sourceKind=source,input=value,expected=expected,measuredFields=list(range(6))if source=='command'else list(range(5))))
    for c in commands+follow['commands']:
        kind=0 if c['case']in installs else 1 if c['case'].startswith('uninstall-')or c['case']=='new-bin-uninstall'else 2
        emit(c,kind,'command')
    for c in controls:emit(c,3,'intervention',actions[c['case']])
    assert len(rows)==36 and sum(r['input']['kind']==0 for r in rows)==7
    return rows


def compare(row,value):
    a,e=value.split('/'),row['expected'].split('/');assert len(a)==len(e)==6
    for i in row['measuredFields']:assert a[i]==e[i],(row['case'],i,a,e)


def main():
    receipt,commands,controls,follow,state=observations.inspect();rows=build(commands,controls,follow,state)
    generated=HERE/'generated';generated.mkdir(exist_ok=True)
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend');env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1')
    target=ROOT/'.build/formal/applications/cargo-install/Install.olean';target.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.run([lean,'-DwarningAsError=true','-o',str(target),'applications/cargo-install/Install.lean'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    path=generated/'install.json';data=dict(schema=1,profile='owned-two-bin-path-install',rows=[r['input']for r in rows])
    def replay(value):
        path.write_text(json.dumps(value)+'\n');return subprocess.run([lean,'--run','applications/cargo-install/InstallCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    p=replay(data);assert p.returncode==0,p.stdout+p.stderr;actual=json.loads(p.stdout);assert len(actual)==len(rows)
    for row,value in zip(rows,actual):compare(row,value['current'])
    calls=[]
    for row in rows:
        r=row['input'];b=lambda k:'True{}'if r[k]else'False{}'
        s='S.State{S.Slot{'+str(r['aBody'])+'n,'+str(r['aOwner'])+'n},S.Slot{'+str(r['bBody'])+'n,'+str(r['bOwner'])+'n},'+b('metadata')+'}'
        args=[str(r['kind'])+'n',s,b('force'),b('compileOk'),str(r['version'])+'n',b('selectA'),b('selectB'),str(r['action'])+'n']
        current='S.render(S.current('+','.join(args+['False{}'])+'))'
        proposal='S.render(S.current('+','.join(args+['True{}'])+'))'if r['kind']==0 else'"-"'
        calls.append(current+' ++ "/" ++ '+proposal+' ++ "\\n"')
    driver=generated/'InstallCase.bend';driver.write_text('import Base\nimport ../Install.bend as S\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
    p=subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    assert p.stdout.splitlines()==[v['current']+'/'+(v['proposal']or'-')for v in actual]
    refusals=[]
    for name,edit in [('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='any-install')),('count',lambda d:d.update(rows=d['rows']*4)),
        ('operation',lambda d:d['rows'][0].update(kind=4)),('body',lambda d:d['rows'][0].update(aBody=6)),('owner',lambda d:d['rows'][0].update(bOwner=3)),
        ('version',lambda d:d['rows'][0].update(version=0)),('action',lambda d:d['rows'][0].update(action=6)),('boolean',lambda d:d['rows'][0].update(force='true')),
        ('directory-unlink',lambda d:d['rows'][0].update(kind=1,aBody=5,aOwner=1,selectA=True)),
        ('mixed-owner-removal',lambda d:d['rows'][0].update(kind=1,aBody=1,aOwner=1,bBody=2,bOwner=2,selectA=True)),
        ('unregistered-removal',lambda d:d['rows'][0].update(kind=1,aBody=4,aOwner=0,selectA=True)),
        ('empty-removal',lambda d:d['rows'][0].update(kind=1,selectA=False,selectB=False))]:
        bad=copy.deepcopy(data);edit(bad);p=replay(bad);assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);refusals.append(name)
    mutations=[];n=next(i for i,r in enumerate(rows)if r['case']=='new-bin-replace-failure')
    for i in range(6):
        bad=copy.deepcopy(rows[n]);parts=bad['expected'].split('/');parts[i]='999';bad['expected']='/'.join(parts)
        try:compare(bad,actual[n]['current'])
        except AssertionError:mutations.append('outcome-'+str(i))
        else:raise AssertionError('Changed outcome escaped')
    proposalDifferences=[r['case']for r,v in zip(rows,actual)if v['proposal']is not None and v['proposal']!=v['current']]
    assert proposalDifferences==['new-bin-replace-failure']
    files=[HERE/n for n in ['Install.lean','Install.bend','InstallCase.lean','conformance.py','observations.py','probe.py']]
    files +=[ROOT/'applications/sources/cargo-install-selections.json']
    for capture in [RUN,ROOT/'applications/evidence/cargo-install-20261125T003303650622Z']:
        files +=[p for p in capture.rglob('*')if p.is_file()and'work'not in p.relative_to(capture).parts and p.name!='conformance.json']
    report=dict(schema=1,scope='Two-bin path install on selected Cargo1.92/macOS;successful compilation/staging/tracker saves except explicit compile/rename controls.',
        nativeCommands=30,controlledInterventions=6,transitionComparisons=len(rows),researchRefusals=refusals,observationMutations=mutations,proposalDifferences=proposalDifferences,
        comparisons=[{**r,'model':v}for r,v in zip(rows,actual)],basisSha256={str(p.relative_to(ROOT)):sha(p)for p in sorted(set(files))},driverSha256=sha(driver),
        tools={n:dict(path=str(Path(p).resolve()),sha256=sha(Path(p)))for n,p in [('lean',lean),('bend',bend)]},
        limits=['No Cargo/rustc/runtime invocation in replay. Native version/lock/runtime commands compare root state as read-only;runtime stdout is independently checked,not predicted by a CPU model.',
            'Exact fixture hashes classify bodies and exact package IDs classify registration;unknown bodies/owners refuse interpretation. No universal executable,manifest,tracking-file or path codec.',
            'Only owned blocking directories fail renames;all new-file publications,other replacement actions and tracking writes are admitted successes. No crash,durability,orphan-removal,concurrency,Windows or registry/Git freshness proof.',
            'The new-bin rollback inconsistency is observed in pinned Cargo1.92. No latest-upstream status,upstream issue or production patch is claimed.',
            'Keeping confirmed new files after saved partial ownership is a pure candidate only. Metadata-write failure,earlier new-bin failure,orphan removal and other unwind paths require their own design/qualification.',
            'Initial collector refused an ancestor-config guard before Cargo execution;failed source is preserved after refusal. Follow-up producer uses a fresh root and the existing compiled target.'])
    (RUN/'conformance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k not in ['comparisons','basisSha256']},indent=2))


if __name__=='__main__':main()
