#!/usr/bin/env python3
"""Pure lookup/context projection from captured exec/run/call observations."""
import copy,hashlib,json,os,subprocess
from pathlib import Path
import observations

ROOT=observations.ROOT
HERE=Path(__file__).resolve().parent
RUN=observations.RUN
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def build(receipt,commands):
    rows=[]
    for c in commands:
        if c['operation']=='install':continue
        mode=1 if c['operation']=='run-script'else 2 if c['operation']=='explicit-shell-call'else 0
        new=c['after']['effects'][len(c['before']['effects']):]
        event=new[0]if new else None
        selected={'dependency':1,'inherited-path':2,'root-script':3}[event['kind']]if event else 0
        # Diagnostic interpretation is explicit and bound to the exact stream;
        # identical numeric statuses alone cannot establish these phases.
        stage=0 if event else 1 if c['app']=='npm'and mode==0 else 2 if c['app']=='pnpm'else 3
        cwd=2 if c['operation']=='nested-exec'else 1
        data=dict(app={'npm':0,'pnpm':1,'yarn':2}[c['app']],mode=mode,dependencyBin=c['profile']=='dependency-and-path',inheritedBin=c['profile']!='missing',cwd=cwd,arguments=receipt['arguments'])
        expected=dict(selected=selected,stage=stage,exitCode=c['outcome']['exitCode'],cwd=cwd if event else 0,arguments=event['args']if event else[])
        rows.append(dict(case='/'.join([c['app'],c['profile'],c['operation']]),input=data,expected=expected,
            premise='Literal known command;installed package,private empty acquisition cache/global prefix,and known benign programs. Failure phase interprets checked stderr. Cwd/arguments come from the independent fixture event,not a shell-parser simulation.'))
    assert len(rows)==18;return rows


def compare(row,value):assert value==row['expected'],(row['case'],value,row['expected'])
def bend_string(value):return json.dumps(value,ensure_ascii=False)
def bend_args(args):
    result='Nil{}'
    for value in reversed(args):result='Con{'+bend_string(value)+','+result+'}'
    return result
def decode_bend(line):
    selected,stage,exit,cwd,count,args=line.split('/',5);count=int(count)
    if count:assert args.endswith('|');values=args[:-1].split('|')
    else:assert not args;values=[]
    assert len(values)==count
    return dict(selected=int(selected),stage=int(stage),exitCode=int(exit),cwd=int(cwd),arguments=values)


def main():
    receipt,commands,warnings=observations.inspect();rows=build(receipt,commands);generated=HERE/'generated';generated.mkdir(exist_ok=True)
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend');env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1')
    target=ROOT/'.build/formal/applications/js-exec/Exec.olean';target.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.run([lean,'-DwarningAsError=true','-o',str(target),'applications/js-exec/Exec.lean'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    path=generated/'exec.json';data=dict(schema=1,profile='offline-literal-command-context',rows=[r['input']for r in rows])
    def replay(value):
        path.write_text(json.dumps(value)+'\n');return subprocess.run([lean,'--run','applications/js-exec/ExecCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    p=replay(data);assert p.returncode==0,p.stdout+p.stderr;actual=json.loads(p.stdout);assert len(actual)==len(rows)
    for row,value in zip(rows,actual):compare(row,value)
    calls=[]
    for row in rows:
        r=row['input'];b=lambda k:'True{}'if r[k]else'False{}'
        ctx='S.EContext{'+','.join([b('dependencyBin'),b('inheritedBin'),str(r['cwd'])+'n',bend_args(r['arguments'])])+'}'
        calls.append('S.render(S.run('+str(r['app'])+'n,'+str(r['mode'])+'n,'+ctx+')) ++ "\\n"')
    driver=generated/'ExecCase.bend';driver.write_text('import Base\nimport ../Exec.bend as S\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
    p=subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    assert [decode_bend(s)for s in p.stdout.splitlines()]==actual
    refusals=[]
    for name,edit in [('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='arbitrary-shell')),('count',lambda d:d.update(rows=d['rows']*8)),
        ('app',lambda d:d['rows'][0].update(app=3)),('mode',lambda d:d['rows'][0].update(mode=3)),('cwd',lambda d:d['rows'][0].update(cwd=0)),
        ('npm-call',lambda d:d['rows'][0].update(app=1,mode=2)),('nested-script',lambda d:d['rows'][0].update(mode=1,cwd=2)),
        ('argument-count',lambda d:d['rows'][0].update(arguments=['a']*33)),('argument-bound',lambda d:d['rows'][0].update(arguments=['a'*4097])),
        ('line-codec',lambda d:d['rows'][0].update(arguments=['a|b'])),('nul',lambda d:d['rows'][0].update(arguments=['\0'])),
        ('boolean',lambda d:d['rows'][0].update(dependencyBin='true'))]:
        bad=copy.deepcopy(data);edit(bad);p=replay(bad);assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);refusals.append(name)
    mutations=[]
    for field,value in [('selected',999),('stage',999),('exitCode',999),('cwd',999),('arguments',['changed'])]:
        bad=copy.deepcopy(rows[0]);bad['expected'][field]=value
        try:compare(bad,actual[0])
        except AssertionError:mutations.append(field)
        else:raise AssertionError('Changed observation escaped')
    files=[HERE/n for n in ['Exec.lean','Exec.bend','ExecCase.lean','probe.py','observations.py','conformance.py']]
    files +=[ROOT/'applications/sources/js-exec-selections.json']
    files +=[p for p in RUN.iterdir()if p.is_file()and p.name!='conformance.json']
    report=dict(schema=1,nativeCommands=27,postInstallComparisons=18,fixtureExecutionEvents=13,ignoredSettingWarnings=warnings,researchRefusals=refusals,observationMutations=mutations,
        comparisons=[{**r,'model':v}for r,v in zip(rows,actual)],basisSha256={str(p.relative_to(ROOT)):sha(p)for p in sorted(set(files))},driverSha256=sha(driver),
        tools={n:dict(path=str(Path(p).resolve()),sha256=sha(Path(p)))for n,p in [('lean',lean),('bend',bend)]},
        limits=['No npm,pnpm,Yarn,Node,fixture or network execution in replay. Installs provide admitted contexts and are not predicted by the model.',
            'Literal command,one admitted dependency binary/PATH program/named script,empty private npm acquisition cache/global prefix,all known programs successful. No arbitrary executable,package acquisition or child-failure qualification.',
            'Exact argv/cwd events are native;model forwards an admitted vector without parsing shellcode. Restricted line codec only frames the Bend research driver and does not limit program/user arguments.',
            'Npm ENOTCACHED,pnpm command-not-found and Yarn/shell127 diagnostics separately bind interpreted failure phase;status1 alone does not identify acquisition versus execution lookup.',
            'Frozen first collector retains an ignored pnpm setting warning. Maintained collector removes it;no native capture is reattributed and no rerun is needed for that correction.',
            'Yarn node-modules only;no Windows,PnP,recursive tasks,colliding package binaries,permission/race,global reuse,online registry or shell-injection proof. Source and binary correspondence are selected-version/module identities,not reproducible upstream builds.'])
    (RUN/'conformance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in ['comparisons','basisSha256']},indent=2))


if __name__=='__main__':main()
