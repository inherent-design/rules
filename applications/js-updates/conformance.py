#!/usr/bin/env python3
"""Pure update/query replay over frozen HTTP, project, lock, and runtime facts."""
import copy,fnmatch,hashlib,json,os,re,subprocess
from pathlib import Path
import observations

ROOT,HERE=observations.ROOT,Path(__file__).resolve().parent
NAMES=observations.NAMES;LOCAL='rules-update-local';sha=observations.sha
def scalar(s):
    assert re.fullmatch(r'(?:[1-9][0-9]*\.[0-9]+\.[0-9]+|file:\.\./local)',s),s
    return s
def authored(run,state):return json.loads((run/state['authored']['package.json']['captured']).read_text())['dependencies']
def saved(run,state,app):
    specs=authored(run,state);result={}
    if app=='npm':
        lock=json.loads((run/state['authored']['package-lock.json']['captured']).read_text())
        assert lock['packages']['']['dependencies']==specs
        for name in specs:
            entry=lock['packages']['node_modules/'+name]
            if name==LOCAL:assert entry['link']and entry['resolved']=='../local';result[name]='local:1'
            else:result[name]=scalar(entry['version'])
    elif app=='pnpm':
        text=(run/state['authored']['pnpm-lock.yaml']['captured']).read_text();assert text.count('\n  .:\n')==1
        body=text.split('\n    dependencies:\n',1)[1].split('\npackages:',1)[0];entries={}
        for match in re.finditer(r'^      ([a-z0-9-]+):\n        specifier: ([^\n]+)\n        version: ([^\n]+)\n',body,re.M):
            name,spec,value=match.groups();assert name not in entries;entries[name]=(spec,scalar(value))
        assert set(entries)==set(specs)
        for name,(spec,value)in entries.items():
            assert spec==specs[name]
            result[name]='local:1'if name==LOCAL else value
    else:
        text=(run/state['authored']['yarn.lock']['captured']).read_text()
        for name in NAMES:
            blocks=re.findall(r'^"'+re.escape(name)+r'@npm:([^"\n]+)":\n((?:  [^\n]*\n)+)',text,re.M)
            assert len(blocks)==1,(name,'Unqualified multi-context Yarn lock')
            spec,body=blocks[0];assert spec==specs[name]
            version=re.search(r'^  version: (.+)$',body,re.M).group(1);scalar(version)
            assert '  resolution: "'+name+'@npm:'+version+'"\n'in body;result[name]=version
        assert '"'+LOCAL+'@file:../local::locator='in text;result[LOCAL]='local:1'
    return result
def runtime(run,row):
    value=json.loads((run/row['streams']['stdout']['file']).read_text())
    return{name:('local:1'if name==LOCAL else scalar(v['value']))for name,v in value.items()}
def semantic_state(run,state,app,installed):
    specs=authored(run,state);locked=saved(run,state,app)
    return[dict(name=name,spec=specs[name],saved=locked[name],installed=installed[name])for name in sorted(specs)]
def text(report):
    states=''.join(s['name']+'='+','.join(s[k]for k in['spec','saved','installed'])+';'for s in report['states'])
    rows=''.join(r['name']+'='+','.join(r[k]for k in['current','wanted','latest'])+';'for r in report['rows'])
    return str(report['exitCode'])+'/'+states+'/'+rows
def stable_catalog(meta):
    stable=[v for v in meta['versions']if re.fullmatch(r'[1-9][0-9]*\.[0-9]+\.[0-9]+',v)]
    excluded=[v for v in meta['versions']if v not in stable]
    assert all(re.fullmatch(r'[1-9][0-9]*\.[0-9]+\.[0-9]+-[a-z0-9.]+',v)for v in excluded)
    assert meta['dist-tags']['latest']in stable
    return dict(stable=stable,latest=meta['dist-tags']['latest']),excluded


def build(observed):
    rows=[];histories={};bindings={};scope_basis=[]
    for run,command in observed:
        app,case=command['app'],command['case'];key=(run,app);hist=histories.setdefault(key,{})
        online={};failed={}
        for e in command['requests']:
            if e['path'].endswith('.tgz'):continue
            name=e['path'].lstrip('/').split('?')[0]
            if e['status']==200:
                meta=json.loads((run/e['response']).read_text());assert meta['name']==name
                hist[name]=dict(meta=meta,response=e['response'],case=case);online[name]=hist[name]
            else:failed[name]=e['status']
        if command['kind']=='fresh-node-observer':bindings[key]=runtime(run,command);continue
        if case=='initial-install':continue
        before=semantic_state(run,command['before'],app,bindings[key]);args=command['argv'][2 if app=='yarn'else 1:]
        if case.startswith('catalog-'):action='inspect';assert args[0]=='outdated'
        elif case=='within-range':action='refresh'
        else:assert case in['rewrite-latest','rewrite-retagged'];action='rewrite-latest'
        if action=='inspect':patterns=[s for s in args[1:]if not s.startswith('-')]
        elif app=='npm'and action=='rewrite-latest':patterns=[s.removesuffix('@latest')for s in args[1:]if not s.startswith('-')]
        else:patterns=[s for s in args[1:]if not s.startswith('-')]
        assert all(p in[*NAMES,LOCAL,'rules-update-*']for p in patterns),patterns
        deps=[];witnesses=[]
        for s in before:
            name=s['name'];selected=not patterns or any(fnmatch.fnmatchcase(name,p)for p in patterns)
            prior=hist.get(name);status=200 if name in online else failed.get(name,0)
            if not selected or name==LOCAL and status==0:evidence='not-queried';catalog=None
            elif status==200:evidence='online';catalog,excluded=stable_catalog(prior['meta'])
            elif status==404 and(app=='npm'or prior is None):evidence='missing';catalog=None
            elif prior is not None:evidence='prior';catalog,excluded=stable_catalog(prior['meta'])
            else:raise AssertionError((app,case,name,'No qualified catalog basis'))
            if evidence in['online','prior']:witnesses.append(dict(name=name,basisCase=prior['case'],response=prior['response'],excludedPrereleases=excluded))
            deps.append(dict(**s,selected=selected,evidence=evidence,lookupStatus=status,catalog=catalog))
        if action=='inspect':
            after=bindings[key];reported=json.loads((run/command['streams']['stdout']['file']).read_text())
            query_rows=[dict(name=name,**{k:value[k]for k in['current','wanted','latest']})for name,value in sorted(reported.items())]
        else:
            query_rows=[]
            if command['outcome']['exitCode']:
                assert command['before']==command['after'];after=bindings[key]
            else:
                label={'within-range':'within-runtime','rewrite-latest':'latest-runtime','rewrite-retagged':'retagged-runtime'}[case]
                after=runtime(run,next(r for path,r in observed if path==run and r['app']==app and r['case']==label))
        expected=dict(exitCode=command['outcome']['exitCode'],states=semantic_state(run,command['after'],app,after),rows=query_rows)
        rows.append(dict(capture=str(run.relative_to(ROOT)),app=app,case=case,input=dict(profile=app,action=action,dependencies=deps),
            requestArguments=args,catalogBasis=witnesses,expected=expected))
        scope_basis.append(dict(app=app,case=case,patterns=patterns,selected=[d['name']for d in deps if d['selected']]))
    return dict(schema=1,profile='positive-major-stable-caret-tags',rows=[r['input']for r in rows]),rows,scope_basis


def blist(values,encode):
    result='Nil{}'
    for value in reversed(values):result='Con{'+encode(value)+','+result+'}'
    return result
def bend_call(row):
    r=row['input'];q=lambda s:json.dumps(s,ensure_ascii=False);b=lambda x:'True{}'if x else'False{}'
    def v(s):return'U.V{'+','.join(t+'n'for t in s.split('.'))+'}'
    def selection(s):return'U.LocalBasis{'+s.split(':')[1]+'n}'if s.startswith('local:')else'U.Registry{'+v(s)+'}'
    def spec(s):return'U.Local{'+q(s)+'}'if s.startswith('file:')else'U.Caret{'+v(s[1:])+'}'if s.startswith('^')else'U.Exact{'+v(s)+'}'
    def dep(d):
        c=d['catalog'];cat='None{}'if c is None else'Some{U.Catalog{'+blist(c['stable'],v)+','+v(c['latest'])+'}}'
        evidence={'online':'Online','prior':'Prior','missing':'Missing','not-queried':'NotQueried'}[d['evidence']]
        return'U.Dep{'+','.join([q(d['name']),spec(d['spec']),selection(d['installed']),selection(d['saved']),b(d['selected']),'U.'+evidence+'{}',cat])+'}'
    return'U.run_text(U.'+{'npm':'Npm','pnpm':'Pnpm','yarn':'Yarn'}[r['profile']]+'{},U.'+{'refresh':'Refresh','rewrite-latest':'RewriteLatest','inspect':'Inspect'}[r['action']]+'{},'+blist(r['dependencies'],dep)+')'


def main():
    observed=observations.inspect();data,rows,scopes=build(observed)
    paths=[HERE/n for n in['Updates.lean','Updates.bend','UpdatesCase.lean','probe.py','observations.py','conformance.py']]
    paths +=[ROOT/'applications/sources/js-updates-selections.json']
    paths +=[p for run in[observations.MAIN,observations.YARN]for p in run.rglob('*')if p.is_file()and'work'not in p.relative_to(run).parts and p.name!='conformance.json']
    basis={str(p.relative_to(ROOT)):sha(p)for p in sorted(set(paths))}
    generated=HERE/'generated';generated.mkdir(exist_ok=True)
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend');env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1')
    target=ROOT/'.build/formal/applications/js-updates/Updates.olean';target.parent.mkdir(parents=True,exist_ok=True)
    result=subprocess.run([lean,'-DwarningAsError=true','-o',str(target),'applications/js-updates/Updates.lean'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+result.stderr
    path=generated/'updates.json'
    def replay(value):
        path.write_text(json.dumps(value)+'\n');return subprocess.run([lean,'--run','applications/js-updates/UpdatesCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    result=replay(data);assert result.returncode==0,result.stdout+result.stderr
    actual=json.loads(result.stdout);expected=[text(r['expected'])for r in rows];assert actual==expected,(expected,actual)
    driver=generated/'UpdatesCase.bend';driver.write_text('import Base\nimport ../Updates.bend as U\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(bend_call(r)+' ++ "\\n"'for r in rows)+')\n')
    result=subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.splitlines()==expected,(expected,result.stdout)
    refusals=[]
    first_registry=next(i for i,d in enumerate(data['rows'][0]['dependencies'])if d['catalog'])
    def first(d):return d['rows'][0]['dependencies'][first_registry]
    for name,change in [('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='general-semver')),
        ('application',lambda d:d['rows'][0].update(profile='unknown')),('action',lambda d:d['rows'][0].update(action='upgrade-all')),
        ('version',lambda d:first(d).update(installed='1.0.0-beta.1')),('zero-major',lambda d:first(d).update(spec='^0.1.0')),
        ('noncanonical-version',lambda d:first(d).update(installed='01.0.0')),('source-kind',lambda d:first(d).update(installed='local:1')),
        ('duplicate-name',lambda d:d['rows'][0]['dependencies'].append(d['rows'][0]['dependencies'][0])),
        ('tag-target',lambda d:first(d)['catalog'].update(latest='31.0.0')),('duplicate-version',lambda d:first(d)['catalog']['stable'].append(first(d)['catalog']['stable'][0])),
        ('lookup-evidence',lambda d:first(d).update(evidence='online',lookupStatus=404)),('network-class',lambda d:first(d).update(evidence='missing',lookupStatus=500,catalog=None)),
        ('name',lambda d:first(d).update(name='bad|name')),('boolean',lambda d:first(d).update(selected='true')),
        ('missing-field',lambda d:first(d).pop('lookupStatus')),('empty-catalog',lambda d:first(d)['catalog'].update(stable=[])),
        ('row-bound',lambda d:d.update(rows=d['rows']*6)),('unqueried-response',lambda d:first(d).update(evidence='not-queried',catalog=None)),
        ('yarn-inspector',lambda d:d['rows'][0].update(profile='yarn')),
        ('ambiguous-tag-preference',lambda d:d['rows'][0]['dependencies'][2]['catalog'].update(latest='1.0.0')),
        ('unqualified-cold-pnpm',lambda d:next(r for r in d['rows']if r['profile']=='pnpm'and r['action']=='inspect')['dependencies'][1].update(evidence='missing',lookupStatus=404,catalog=None))]:
        bad=copy.deepcopy(data);change(bad);result=replay(bad)
        assert result.returncode==2 and not result.stdout,(name,result.stdout,result.stderr);refusals.append(name)
    premise_controls=[]
    for name,change in [('tag-direction',lambda d:next(r for r in d['rows']if r['profile']=='npm'and r['action']=='rewrite-latest')['dependencies'][1]['catalog'].update(latest='1.1.0')),
        ('declaration-style',lambda d:first(d).update(spec='^1.0.0')),
        ('saved-versus-installed',lambda d:next(r for r in d['rows']if r['profile']=='pnpm'and r['action']=='inspect')['dependencies'][1].update(saved='1.1.0')),
        ('requested-scope',lambda d:d['rows'][0]['dependencies'][2].update(selected=False,evidence='not-queried',lookupStatus=0,catalog=None))]:
        bad=copy.deepcopy(data);change(bad);result=replay(bad);assert result.returncode==0,result.stdout+result.stderr
        assert json.loads(result.stdout)!=expected,name;premise_controls.append(name)
    observation_controls=[]
    for name,index,field in [('pin-bypass',0,'states'),('wanted-meaning',0,'rows'),('silent-omission',1,'exitCode'),('target-direction',-1,'states')]:
        bad=copy.deepcopy([r['expected']for r in rows]);before=text(bad[index])
        if field=='exitCode':bad[index][field]=1-bad[index][field]
        elif field=='states':bad[index][field][1]['installed']='31.0.0'
        else:bad[index][field]=[]
        assert text(bad[index])!=before and [text(r)for r in bad]!=actual,name;observation_controls.append(name)
    assert all(sha(ROOT/name)==value for name,value in basis.items()),'Source/evidence basis changed during replay.'
    record=dict(schema=1,nativeProcesses=len(observed),modeledCommands=len(rows),bothModelsMatch=True,comparisons=[dict(**r,model=a)for r,a in zip(rows,actual)],
        scopeWitnesses=scopes,researchRefusals=refusals,normalizedPremiseControls=premise_controls,observationControls=observation_controls,
        driverSha256=sha(driver),basisSha256=basis,
        tools={k:dict(path=str(Path(v).resolve()),sha256=sha(Path(v)))for k,v in[('lean',lean),('bend',bend)]},
        limits=['Pure replay;no package-manager,Node runtime,registry or native fixture rerun.',
            'Positive-major stable exact/caret profile after checked catalog admission;listed prereleases retained as excluded witnesses. No general semver,alias/workspace/peer graph,release-age or linker proof.',
            'A satisfying tag must equal the greatest admitted version;different resolver preferences outside that premise are refused,not silently equated.',
            'Prior catalog inputs are earlier observed fixture metadata;they do not instrument the precise native cache read. Missing lookup here is404,not every network error.',
            'Selected project state and successful materialization are compared with locks and fresh runtime observations. Planning refusal is not general rollback or no-cache-effects proof.',
            'Finite lock-field adapters parse only this one-importer/single-context fixture;not general JSON/YAML parser or schema validation proofs.',
            'The original wildcard/local-source collector refusal remains distinct from the corrected Yarn-only fixture. No production changes or other-platform qualification.'])
    (observations.MAIN/'conformance.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:v for k,v in record.items()if k not in['comparisons','scopeWitnesses','basisSha256']},indent=2))


if __name__=='__main__':main()
