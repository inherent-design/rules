#!/usr/bin/env python3
"""Pure replay of selected cache/CI effects,interventions and observer reports."""
import copy,hashlib,json,os
from pathlib import Path
import subprocess
import observations

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
RUN=observations.RUN
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def build(receipt,commands,corrupt,edit):
    target=corrupt['target'].removeprefix('cache/_cacache/');authors={}
    def state(s):
        backing=s['cache'].get(target);backing=0 if backing is None else 1 if backing['sha256']==receipt['fixtureSha256']else 2 if backing['sha256']==corrupt['mutatedSha256']else None
        assert backing is not None,'Unknown backing is not absent.'
        installed=s['installed'].get('fixture-cache/index.js')
        if installed is None:installed=0
        else:
            assert 'fixture-cache/package.json'in s['installed']
            installed=1 if installed['sha256']==edit['originalSha256']else 2 if installed['sha256']==edit['editedSha256']else None
            assert installed is not None,'Unknown installed bytes are not a known edit.'
        # Install supplied the baseline. This model does not generate its lock.
        assert set(s['authored'])=={'package.json','package-lock.json','.npmrc'}
        value=tuple((k,v['sha256'])for k,v in sorted(s['authored'].items()))
        if value not in authors:authors[value]=len(authors)+1
        return dict(backing=backing,installed=installed,author=authors[value])
    rows=[]
    def emit(label,kind,source_kind,before,after,exit=0,requests=0,availability=None):
        prior=state(before);expected=state(after)
        matching=label=='ci-offline-valid'
        if matching:
            witness=json.loads((RUN/'cache-index-witness.json').read_text());record=next(r for r in witness['records']if r['key'].endswith('.tgz'))
            assert before['cache'][record['indexPath']]['sha256']==record['sha256']and prior['backing']==1
        data=dict(kind=kind,**prior,referenced=True,lockAdmitted=True,matchingIndex=matching,originReady=label=='ci-origin-recovery')
        measured=list(range(5))if source_kind=='npm'else[0,1,2]
        premise=('Historical referenced-object premise from initial HTTP cache population and closed cooperating history;not a recovered index record for every earlier boundary.'if kind==0 else
            'Matching request/index/SRI witness only for offline-valid CI;other CI payload absence is observed,or successful own-origin bytes are a controlled premise.'if kind==1 else
            'Owned intervention/availability-observer protocol,not a public npm operation.')
        rows.append(dict(case=label,sourceKind=source_kind,input=data,expected='/'.join(map(str,[expected['backing'],expected['installed'],expected['author'],exit,requests])),measuredFields=measured,availability=availability,premise=premise))
    for c in commands:
        label=c['case']
        if label=='install':continue
        if label=='runtime-after-cache-corruption':emit('owned-cache-corruption',2,'intervention',corrupt['before'],corrupt['after'])
        if label=='verify-with-installed-edit':emit('owned-installed-edit',3,'intervention',edit['before'],edit['after'])
        if c['kind']=='observer':
            value=json.loads((RUN/c['streams']['stdout']['file']).read_text());emit(label,4,'observer',c['before'],c['after'],availability=value['available'])
        else:emit(label,0 if label.startswith('verify-')else 1,'npm',c['before'],c['after'],c['outcome']['exitCode'],len(c['requests']))
    assert len(rows)==15 and len(authors)==1
    assert sum(r['sourceKind']=='npm'for r in rows)==6 and sum(r['availability']is not None for r in rows)==7
    return rows


def compare(row,value):
    a,e=value.split('/'),row['expected'].split('/');assert len(a)==len(e)==5
    for i in row['measuredFields']:assert a[i]==e[i],(row['case'],i,a,e)
def availability(row,value):
    if row['availability']is not None:assert row['availability']==value
def bend_call(data):
    state='S.CState{'+','.join(str(data[k])+'n'for k in ['backing','installed','author'])+'}'
    b=lambda k:'True{}'if data[k]else'False{}'
    return state,'S.current('+','.join([str(data['kind'])+'n',state,*[b(k)for k in ['referenced','lockAdmitted','matchingIndex','originReady']]])+')','S.preflight('+','.join([state,*[b(k)for k in ['lockAdmitted','matchingIndex','originReady']]])+')'


def main():
    receipt,commands,corrupt,edit=observations.inspect();rows=build(receipt,commands,corrupt,edit);generated=HERE/'generated';generated.mkdir(exist_ok=True)
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend');env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1')
    target=ROOT/'.build/formal/applications/npm-cache/Cache.olean';target.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.run([lean,'-DwarningAsError=true','-o',str(target),'applications/npm-cache/Cache.lean'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    path=generated/'cache.json';data=dict(schema=1,profile='owned-single-package-cache',rows=[r['input']for r in rows])
    def replay(value):
        path.write_text(json.dumps(value)+'\n');return subprocess.run([lean,'--run','applications/npm-cache/CacheCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    p=replay(data);assert p.returncode==0,p.stdout+p.stderr;actual=json.loads(p.stdout);assert len(actual)==len(rows)
    for r,v in zip(rows,actual):compare(r,v['current']);availability(r,v['available'])
    calls=[]
    for row in rows:
        state,current,proposal=bend_call(row['input']);proposal='S.render('+proposal+')'if row['input']['kind']==1 else'"-"'
        calls.append('S.render('+current+') ++ "/" ++ Bool.pick(String,S.available('+state+'),"1","0") ++ "/" ++ '+proposal+' ++ "\\n"')
    driver=generated/'CacheCase.bend';driver.write_text('import Base\nimport ../Cache.bend as S\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
    p=subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    assert p.stdout.splitlines()==[v['current']+'/'+str(int(v['available']))+'/'+(v['proposal']or'-')for v in actual]
    refusals=[]
    for name,edit_bad in [('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='all-caches')),('count',lambda d:d.update(rows=d['rows']*10)),
        ('operation',lambda d:d['rows'][0].update(kind=5)),('backing',lambda d:d['rows'][0].update(backing=3)),('installation',lambda d:d['rows'][0].update(installed=3)),
        ('author',lambda d:d['rows'][0].update(author=0)),('boolean',lambda d:d['rows'][0].update(matchingIndex='true'))]:
        bad=copy.deepcopy(data);edit_bad(bad);p=replay(bad);assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);refusals.append(name)
    mutations=[];n=next(i for i,r in enumerate(rows)if r['sourceKind']=='npm')
    for i in range(5):
        bad=copy.deepcopy(rows[n]);parts=bad['expected'].split('/');parts[i]='999';bad['expected']='/'.join(parts)
        try:compare(bad,actual[n]['current'])
        except AssertionError:mutations.append('outcome-'+str(i))
        else:raise AssertionError('Outcome mutation escaped')
    n=next(i for i,r in enumerate(rows)if r['availability']is not None);bad=copy.deepcopy(rows[n]);bad['availability']=not bad['availability']
    try:availability(bad,actual[n]['available'])
    except AssertionError:mutations.append('availability')
    else:raise AssertionError('Availability mutation escaped')
    ledger=json.loads((ROOT/'applications/sources/npm-cache-selections.json').read_text())
    for source in ledger['sources']:assert sha(ROOT/source['cache'])==source['sha256']
    files=[HERE/n for n in ['Cache.lean','Cache.bend','CacheCase.lean','probe.py','observations.py','conformance.py']]
    files +=[ROOT/'applications/sources/npm-cache-selections.json']
    files +=[p for p in RUN.rglob('*')if p.is_file()and'work'not in p.relative_to(RUN).parts and p.name!='conformance.json']
    report=dict(schema=1,scope='Selected referenced cache/CI profile,not a complete cache/index/installer implementation.',nativeNpmTransitions=6,controlledInterventions=2,nodeAvailabilityObservers=7,
        transitionComparisons=len(rows),availabilityComparisons=7,researchRefusals=refusals,observationMutations=mutations,
        comparisons=[{**r,'model':v}for r,v in zip(rows,actual)],basisSha256={str(p.relative_to(ROOT)):sha(p)for p in sorted(set(files))},driverSha256=sha(driver),
        tools={n:dict(path=str(Path(p).resolve()),sha256=sha(Path(p)))for n,p in [('lean',lean),('bend',bend)]},
        limits=['No npm/Node/server execution. Initial install supplies the admitted baseline;it is not generated by this model. Intervention and observer rows compare state only,not invented npm process outcomes.',
                'Referenced-object history for earlier verification is a source-informed premise,not a recovered historical index at every step. Offline-valid CI has a byte-identical matching request/index/SRI witness.',
                'Typed backing is a closed-fixture hash classification;unknown bytes refuse interpretation rather than becoming absent. Global index,permissions,metadata freshness,races and leases remain separate.',
                'Candidate preflight has cross-model agreement and conditional preservation laws only. Its acquisition/lookup evidence must survive clearing;global cache verification cannot supply that guarantee.',
                'One package,known successful origin and scripts disabled. No general acquisition failure ordering,rollback,remote trust/durability or complete feature promotion.'])
    (RUN/'conformance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in['comparisons','basisSha256']},indent=2))


if __name__=='__main__':main()
