#!/usr/bin/env python3
"""Pure configuration replay; executes Lean/Bend, never package managers."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'applications/restic'))
from locks_probe import redact
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
VALUES={f'https://{name}.invalid/':n for n,name in enumerate(['global','user','project','environment','command','written','home-write','project-write'],1)}
VALUES.update({'https://registry.npmjs.org/':9,'https://registry.yarnpkg.com':10})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures',nargs=3,type=Path)
    a=p.parse_args();captures=[p.resolve() for p in a.captures]
    models=[HERE/name for name in ['Configuration.lean','ConfigurationCase.lean','Configuration.bend']]
    ledger=ROOT/'applications/sources/js-config-selections.json';inputs=models+[ledger];all_rows=[]
    for capture,count in zip(captures,[42,13,9]):
        assert capture.is_relative_to(ROOT/'applications/evidence')
        receipt=json.loads((capture/'receipt.json').read_text())
        assert receipt['commands']==count and receipt['allOwnedProcessesRetired']
        assert sha(capture/'probe.py')==receipt['producerSha256']
        assert sha(capture/'helper.py')==receipt['helperSha256']==sha(ROOT/'applications/restic/locks_probe.py')
        raw=capture/'work/trace-original.json'
        assert sha(raw)==receipt['rawTraceSha256']
        assert sha(capture/'trace.json')==receipt['publicTraceSha256']
        assert redact(raw.read_bytes())==(capture/'trace.json').read_bytes()
        rows=json.loads((capture/'trace.json').read_text());assert len(rows)==count
        for row in rows:
            assert row['outcome']==dict(exitCode=0,timedOut=False)
            stem=row['app']+'-'+row['case']
            for stream in ['stdout','stderr']:
                info=row['streams'][stream];r=capture/info['rawPrivatePath'];q=capture/(stem+'.'+stream)
                assert sha(r)==info['rawSha256'] and sha(q)==info['publicSha256']
                assert redact(r.read_bytes())==q.read_bytes()
            all_rows.append((capture,row))
        inputs += [p for p in capture.iterdir() if p.is_file() and p.name!='conformance.json']
    basis={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    for row in json.loads(ledger.read_text())['sources']:
        assert sha(ROOT/row['cache'])==row['sha256']
    native_npm=Path('/Users/zer0cell/.local/share/mise/installs/node/26.13.1/lib/node_modules/npm')
    npm_matches={}
    for file,installed in [('lib/commands/config.js','lib/commands/config.js'),('workspaces/config/lib/index.js','node_modules/@npmcli/config/lib/index.js'),('workspaces/config/lib/definitions/definitions.js','node_modules/@npmcli/config/lib/definitions/definitions.js')]:
        cached=ROOT/'applications/tools/source-cache/js-config'/('npm__'+file.replace('/','__'))
        assert cached.read_bytes()==(native_npm/installed).read_bytes()
        npm_matches[file]=sha(cached)

    def stored(image,path,key):
        if path not in image:return None
        text=image[path]['content']
        matches=re.findall(r'^'+re.escape(key)+r'\s*[:=]\s*(.*?)\s*$',text,re.M)
        if not matches:return None
        assert len(matches)==1
        value=matches[0]
        if value.startswith('"'):value=json.loads(value)
        return VALUES[value]

    def paths(app,custom):
        if app=='npm':return dict(global_='config/global.npmrc',home='config/user.npmrc',project='project/.npmrc')
        if app=='pnpm':return dict(global_='config/pnpm/auth.ini',home=None,project='project/.npmrc')
        rc='.fixture-yarnrc.yml' if custom else '.yarnrc.yml'
        return dict(global_=None,home='home/'+rc,project='project/'+rc)

    def state(image,locations,key):
        return {k.removesuffix('_'):stored(image,path,key) if path else None for k,path in locations.items()}

    cases,expected=[],[]
    for capture,row in all_rows:
        app=row['app'];argv=row['argv'];args=argv[argv.index('config')+1:];key='npmRegistryServer' if app=='yarn' else 'registry'
        custom=app=='yarn' and 'home/.fixture-yarnrc.yml' in row['before']
        locations=paths(app,custom);before=state(row['before'],locations,key);after=state(row['after'],locations,key)
        action={'get':'get','set':'set','delete':'unset','unset':'unset','list':'explain'}.get(args[0],'explain')
        assert args[0] in ['get','set','delete','unset','list',key]
        location=None
        for argument in args:
            if argument in ['--global','--location=global']:location='global'
            if argument=='--location=user' or argument=='--home':location='home'
            if argument=='--location=project':location='project'
        context_global=location=='global'
        envkey={'npm':'NPM_CONFIG_REGISTRY','pnpm':'PNPM_CONFIG_REGISTRY','yarn':'YARN_NPM_REGISTRY_SERVER'}[app]
        environment=VALUES[row['environment'][envkey]] if envkey in row['environment'] else None
        command=VALUES[args[args.index('--registry')+1]] if '--registry' in args else None
        written=VALUES[args[2]] if action=='set' else 1
        c=dict(app=app,**before,environment=environment,command=command,globalMode=context_global,
            customRc=custom,fallback=10 if app=='yarn' else 9,action=action,location=location,value=written)
        changed=sorted(k for k in set(row['before'])|set(row['after']) if row['before'].get(k)!=row['after'].get(k))
        if action in ['set','unset']:
            scope=location or {'npm':'home','pnpm':'global','yarn':'project'}[app]
            file=locations['global_' if scope=='global' else scope]
            assert changed==[file],(app,row['case'],changed,file)
        else:
            assert not changed
            scope='none'
        output=(capture/(app+'-'+row['case']+'.stdout')).read_text().strip()
        visible=None;native_source=None;reported=None
        if action=='get':visible=VALUES[output]
        if action=='explain':
            if app=='yarn':
                v=json.loads(output);assert v['key']==key;visible=VALUES[v['effective']]
                native_source='project' if '/project/' in v['source'] else 'home' if '/home/' in v['source'] else None
                assert native_source=='project'
            elif app=='pnpm':visible=VALUES[json.loads(output)['registry']]
            else:
                match=re.findall(r'^registry = "([^"]+)"$',output,re.M);assert len(match)==1;visible=VALUES[match[0]]
                assert '; overridden by project' in output
        elif action=='set' and app=='yarn':
            match=re.fullmatch(r"➤ YN0000: Successfully set npmRegistryServer to '([^']+)'",output)
            assert match;reported=VALUES[match[1]]
        elif action=='set':assert not output
        expected.append(dict(app=app,case=row['case'],state=after,effective=visible,source=native_source,
                             writeScope=scope,reported=reported,written=written if action=='set' else None))
        cases.append(c)
    generated=HERE/'generated';generated.mkdir(exist_ok=True)
    data=dict(schema=1,cases=cases);path=generated/'config.json';path.write_text(json.dumps(data,indent=2)+'\n')
    formal=generated/'config-formal';artifact=formal/'applications/js-config/Configuration.olean';artifact.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=str(formal),BEND_NO_TELEMETRY='1');lean=os.environ.get('LEAN','lean')
    compiled=subprocess.run([lean,'-DwarningAsError=true','-o',str(artifact),str(models[0])],cwd=ROOT,env=env,capture_output=True,text=True)
    assert compiled.returncode==0,compiled.stdout+compiled.stderr
    def lean_run(file):return subprocess.run([lean,'--run','applications/js-config/ConfigurationCase.lean',str(file)],cwd=ROOT,env=env,capture_output=True,text=True)
    result=lean_run(path);assert result.returncode==0,result.stdout+result.stderr
    actual=json.loads(result.stdout);assert len(actual)==64
    for value,native in zip(actual,expected):
        g,h,p,v,source,wrote,reported=value.split('/')
        assert [int(g),int(h),int(p)]==[native['state'][k] or 0 for k in ['global','home','project']]
        if native['effective'] is not None:assert int(v)==native['effective']
        if native['source'] is not None:assert source==native['source']
        assert wrote==native['writeScope'] and int(reported)==(native['reported'] or 0)
    native_misreports=[r for r in expected if r['reported'] and r['reported']!=r['written']]
    assert len(native_misreports)==2 and all(r['case']=='set-lower-masked' for r in native_misreports)
    bit=lambda x:'True{}' if x else 'False{}'
    nat=lambda x:str(x or 0)+'n'
    managers={'npm':'Npm{}','pnpm':'Pnpm{}','yarn':'Yarn{}'}
    actions={'get':'Get{}','explain':'Explain{}','set':'Set{}','unset':'Unset{}'}
    scopes={None:'Default{}','global':'Global{}','home':'Home{}','project':'Project{}'}
    calls=[]
    for c in cases:
        s='C.State{'+','.join(nat(c[k]) for k in ['global','home','project'])+'}'
        context='C.Context{'+','.join([nat(c['environment']),nat(c['command']),bit(c['globalMode']),bit(c['customRc']),nat(c['fallback'])])+'}'
        calls.append('row(C.'+managers[c['app']]+','+s+','+context+',C.'+actions[c['action']]+',C.'+scopes[c['location']]+','+nat(c['value'])+') ++ "\\n"')
    runner=generated/'ConfigCase.bend'
    runner.write_text('''import Base
import ../Configuration.bend as C

def scope_name(s: C.Scope) -> String:
  match s:
    case C.Default{}: "none"
    case C.Global{}: "global"
    case C.Home{}: "home"
    case C.Project{}: "project"

def state_text(s: C.State) -> String:
  match s:
    case C.State{global,home,project}: Nat.show(global) ++ "/" ++ Nat.show(home) ++ "/" ++ Nat.show(project)

def row(+a: C.Manager, +s: C.State, +c: C.Context, +action: C.Action, +scope: C.Scope, +v: Nat) -> String:
  next = C.after(a,s,action,scope,v)
  e = C.effective(a,next,c,False{})
  state_text(next) ++ "/" ++ Nat.show(C.value(e)) ++ "/" ++ C.source_name(e) ++ "/" ++ Bool.pick(String,C.writes(action),scope_name(C.target(a,scope)),"none") ++ "/" ++ Nat.show(C.reported(a,action,s,c,scope,v))

def main() -> IO(Unit):
  IO.write('''+' ++ '.join(calls)+')\n')
    # This runner uses the language's explicit sharing for values needed twice.
    text=runner.read_text().replace('  next =','  +next =').replace('  e =','  +e =');runner.write_text(text)
    result=subprocess.run([os.environ.get('BEND','bend'),str(runner)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.splitlines()==actual
    bad=[dict(data,schema=2)]+[dict(data,cases=[dict(cases[0],**x)]) for x in [dict(app='other'),dict(action='apply'),dict(location='machine'),dict(value=0),dict(environment=11)]]
    yarn_row=next(c for c in cases if c['app']=='yarn')
    bad.append(dict(data,cases=[dict(yarn_row,command=5)]))
    for i,value in enumerate(bad):
        q=generated/f'config-negative-{i}.json';q.write_text(json.dumps(value));result=lean_run(q);assert result.returncode==2 and result.stderr
    assert all(sha(ROOT/name)==digest for name,digest in basis.items())
    report=dict(schema=1,commands=64,leanMatches=True,bendMatches=True,reportedVsWrittenDisagreements=native_misreports,
        malformedResearchInputsRefused=len(bad),basisSha256=basis,adapterSha256=sha(Path(__file__)),npmInstalledMatches=npm_matches,
        modelRows=actual,nativeComparisons=expected,
        limits=['One public nonempty scalar registry key; complex merge, auth/secrets, parse failures, concurrent writes, persistence failures and other platforms unqualified.',
                'Effective source is source/model interpretation except retained explicit explanation evidence; no invented native source field.',
                'Yarn custom filename and standard-filename runs are separate profiles; not repeat coverage.',
                'Current misleading headline/custom home read behavior retained; corrected reporting/home alignment proposed only.',
                'Private originals required for raw/public verification; no package-manager or network execution during replay.'])
    (captures[0]/'conformance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['basisSha256','modelRows','nativeComparisons']},indent=2))


if __name__=='__main__':main()
