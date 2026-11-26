"""Owner-run pure comparison of retained native observations and policy models."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import observations as obs

ROOT, HERE = obs.ROOT, Path(__file__).resolve().parent
write = lambda p,v:p.write_text(json.dumps(v,indent=2)+'\n')
sha = obs.sha
VERSIONS = ['1.0.0','1.1.0','2.0.0']


def normalize(manager, entries):
    rules = []
    for key,value in entries:
        if key == obs.LEAF: scope = 'global'
        elif key == obs.LEFT and manager == 'npm':
            assert list(value) == [obs.LEAF]; value=value[obs.LEAF]; scope='parent'
        elif key == obs.LEFT + ('>' if manager == 'pnpm' else '/') + obs.LEAF: scope='parent'
        elif key == obs.LEAF+'@' and manager == 'pnpm': scope='converge'
        elif key == obs.LEAF+'@>=1.0.0' and manager == 'pnpm': scope='broad'
        elif key == obs.LEAF+'@^1.0.0' and manager == 'pnpm': scope='narrow'
        else: raise ValueError(('Unadmitted policy spelling',manager,key))
        assert value in VERSIONS
        rules.append(dict(scope=scope,version=value))
    return rules


def build(observed):
    rows, bindings = [], []
    for run in obs.RUNS:
        commands=obs.read(run/'commands.json'); mutations=obs.read(run/'mutations.json')
        for manager,profile in dict.fromkeys((c['manager'],c['profile'])for c in commands):
            steps, facts = [], []
            for c in [c for c in commands if (c['manager'],c['profile']) == (manager,profile)]:
                removals=[m for m in mutations if m['action']=='owned-lock-removal' and m['after']==c['before']
                          and (m['manager'],m['profile'])==(manager,profile)]
                if removals:
                    assert len(removals)==1 and not c['query']
                    steps.append(dict(action='remove-lock',rules=[],target='2.0.0'))
                    facts.append(dict(kind='author-remove-lock',id=removals[0]['id']))
                args=c['argv'][2 if manager=='yarn' else 1:]
                if c['query']: action='query'; rules=[]
                elif args==['set','resolution',obs.LEAF+'@npm:^1.0.0','npm:2.0.0']: action='set'; rules=[]
                elif args==['install','--immutable','--check-resolutions']: action='check'; rules=[]
                else:
                    assert args[0] == 'install',args
                    action='install'; rules=normalize(manager,obs.policy(run,c,'before'))
                steps.append(dict(action=action,rules=rules,target='2.0.0'))
                fact=dict(kind='query'if c['query']else'operation',id=c['id'],exit=c['exitCode'])
                if c['query']:
                    value=next(x for x in observed['installed']if x['capture']==run.name and x['id']==c['id'])['versions']
                    fact['pair']=[value[obs.LEFT],value[obs.RIGHT]]if profile in ['graph','range']else[value[obs.LEAF]]*2
                elif profile=='manual':
                    # Decode only the selected one-descriptor lock block; this is not a lock parser.
                    text=obs.file_body(run,c['after'],'yarn.lock').decode()
                    block=re.findall(r'^"'+obs.LEAF+r'@npm:\^1\.0\.0":\n((?:  [^\n]*\n)+)',text,re.M)
                    assert len(block)==1
                    version=re.findall(r'^  version: (.+)$',block[0],re.M); assert len(version)==1 and version[0]in VERSIONS
                    assert '  resolution: "'+obs.LEAF+'@npm:'+version[0]+'"\n'in block[0]
                    fact['lockedVersion']=version[0]
                facts.append(fact)
            rows.append(dict(tool=manager,profile=profile,steps=steps))
            bindings.append(dict(capture=run.name,tool=manager,profile=profile,facts=facts))
    return dict(schema=1,profile='generated-caret-override-traces',rows=rows),bindings


def decode_text(text):
    exit_code,manual,choices=text.split('/')
    assert manual in ['-',*VERSIONS] and exit_code in ['0','1']
    pairs=[x.split(',')for x in choices.split(';')]if choices else[]
    assert all(len(x)==2 and all(v in VERSIONS for v in x)for x in pairs)
    return int(exit_code),manual,pairs


def compare(results, bindings):
    counts=dict(operationExits=0,runtimePairs=0,uniqueRuntimePredictions=0,rangeAdmissions=0,manualLocks=0)
    for results,trace in zip(results,bindings,strict=True):
        assert len(results)==len(trace['facts'])
        for text,fact in zip(results,trace['facts'],strict=True):
            code,manual,pairs=decode_text(text)
            if fact['kind']=='author-remove-lock': assert manual=='-'; continue
            assert code==fact['exit'],(trace['capture'],fact['id'],'exit',code,fact['exit'])
            if fact['kind']=='query':
                assert fact['pair']in pairs,(trace['capture'],fact['id'],'installed',pairs,fact['pair'])
                counts['runtimePairs']+=1
                counts['uniqueRuntimePredictions'if len(pairs)==1 else'rangeAdmissions']+=1
                if len(pairs)>1: assert trace['tool']=='pnpm'and trace['profile']=='range'
            else:
                counts['operationExits']+=1
                if 'lockedVersion'in fact:
                    assert pairs==[[fact['lockedVersion']]*2]
                    counts['manualLocks']+=1
    assert counts==dict(operationExits=31,runtimePairs=30,uniqueRuntimePredictions=28,rangeAdmissions=2,manualLocks=8),counts
    return counts


def blist(values,encode):
    value='Nil{}'
    for item in reversed(values):value='Con{'+encode(item)+','+value+'}'
    return value
def bend_trace(row):
    v=lambda s:'O.'+dict(zip(VERSIONS,['One','Minor','Two']))[s]+'{}'
    scope={'global':'Global','parent':'Parent','converge':'Converge','broad':'Broad','narrow':'Narrow'}
    action={'install':'Install','set':'SetResolution','check':'Check','remove-lock':'RemoveLock','query':'Query'}
    rule=lambda r:'O.Rule{O.'+scope[r['scope']]+'{},'+v(r['version'])+'}'
    request=lambda r:'O.Request{O.'+action[r['action']]+'{},'+blist(r['rules'],rule)+','+v(r['target'])+'}'
    return'O.lines(O.texts(O.trace('+blist(row['steps'],request)+',O.'+{'npm':'Npm','pnpm':'Pnpm','yarn':'Yarn'}[row['tool']]+'{},'+('True{}'if row['profile']in['direct','manual']else'False{}')+',O.InstallState{Nil{},None{}})))'


def evidence(private):
    ledger=obs.read(ROOT/'applications/sources/js-overrides-selections.json')
    checked,excluded=[],[]
    for row in ledger['sources']:
        path=ROOT/row['cache']
        if not private: excluded.append(row['cache']);continue
        raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256']
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['gitBlob']
        checked.append(row['cache'])
    return dict(checkedSourceCaches=checked,excludedSourceCaches=excluded)


def raw_controls():
    original=obs.read; controls=[]
    def check(name,filename,change):
        def read(path):
            value=original(path)
            if path==obs.RUNS[0]/filename:change(value)
            return value
        obs.read=read
        try:
            try:obs.inspect()
            except (AssertionError,KeyError,ValueError,StopIteration):controls.append(name)
            else:raise RuntimeError(('Raw observation control escaped',name))
        finally:obs.read=original
    check('stream-hash','commands.json',lambda x:x[0].update(stdoutSha256='0'*64))
    check('payload-length','commands.json',lambda x:next(e for e in x[0]['after'].values()if e['kind']=='file').update(bytes=-1))
    check('runtime-identity','npm-graph-baseline-runtime.stdout',lambda x:x[obs.LEFT]['value']['leaf'].update(version='2.0.0'))
    check('unexplained-edit','mutations.json',lambda x:x[0].update(after={}))
    return controls


def main():
    p=argparse.ArgumentParser();p.add_argument('--private',action='store_true');args=p.parse_args()
    observed=obs.inspect();data,bindings=build(observed)
    out=ROOT/'.build/js-overrides-review';out.mkdir(exist_ok=True)
    formal=ROOT/'.build/js-overrides-formal';target=formal/'applications/js-overrides/Overrides.olean';target.parent.mkdir(parents=True,exist_ok=True)
    lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend')
    env=dict(os.environ,LEAN_PATH=str(formal),BEND_NO_TELEMETRY='1')
    def run(cmd):return subprocess.run(cmd,cwd=ROOT,env=env,text=True,capture_output=True,timeout=120)
    checked=run([lean,'-DwarningAsError=true','-o',str(target),'applications/js-overrides/Overrides.lean'])
    assert checked.returncode==0,checked.stdout+checked.stderr
    path=out/'input.json'
    def replay(value):
        write(path,value);return run([lean,'--run','applications/js-overrides/OverridesCase.lean',str(path)])
    result=replay(data);assert result.returncode==0,result.stdout+result.stderr
    actual=json.loads(result.stdout);counts=compare(actual,bindings)
    driver=out/'OverridesNative.bend'
    driver.write_text('import Base\nimport ../../applications/js-overrides/Overrides.bend as O\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(bend_trace(r)for r in data['rows'])+')\n')
    result=run([bend,str(driver)]);assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.splitlines()==[s for row in actual for s in row]
    refusals=[]
    for name,change in [
        ('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='general-solver')),
        ('tool',lambda d:d['rows'][0].update(tool='unknown')),('operation',lambda d:d['rows'][0]['steps'][0].update(action='force')),
        ('version',lambda d:d['rows'][0]['steps'][0].update(target='3.0.0')),
        ('manual-tool',lambda d:next(r for r in d['rows']if r['profile']=='manual').update(tool='npm')),
        ('range-tool',lambda d:next(r for r in d['rows']if r['profile']=='range').update(tool='yarn')),
        ('count',lambda d:d['rows'][0].update(steps=[])),
        ('selector',lambda d:d['rows'][0]['steps'][2]['rules'][0].update(scope='catalog'))]:
        bad=copy.deepcopy(data);change(bad);result=replay(bad)
        assert result.returncode==2 and not result.stdout,(name,result.stdout,result.stderr);refusals.append(name)
    controls=[]
    for name,change in [
        ('yarn-order',lambda d:next(r for r in d['rows']if r['tool']=='yarn'and r['profile']=='graph')['steps'][4]['rules'].reverse()),
        ('direct-guard',lambda d:next(r for r in d['rows']if r['tool']=='npm'and r['profile']=='direct').update(tool='pnpm')),
        ('converge-kind',lambda d:next(r for r in d['rows']if r['tool']=='pnpm'and r['profile']=='graph')['steps'][8]['rules'][0].update(scope='global')),
        ('lock-lifetime',lambda d:next(r for r in d['rows']if r['profile']=='manual')['steps'][4].update(action='query')),
        ('explicit-check',lambda d:[s.update(action='query')for r in d['rows']if r['profile']=='manual'for s in r['steps']if s['action']=='check'])]:
        bad=copy.deepcopy(data);change(bad);result=replay(bad)
        assert result.returncode==0,result.stdout+result.stderr
        assert json.loads(result.stdout)!=actual,name;controls.append(name)
    changed=[]
    def find(items,identifier):return next(f for row in items for f in row['facts']if f['id']==identifier)
    for name,identifier,field,value in [
        ('npm-refusal','npm-direct-force-direct','exit',0),
        ('yarn-validation','yarn-manual-manual-check','exit',0),
        ('installed-locator','yarn-graph-global-first-runtime','pair',['2.0.0','1.0.0']),
        ('saved-selection','yarn-manual-set-resolution','lockedVersion','1.1.0')]:
        bad=copy.deepcopy(bindings);find(bad,identifier)[field]=value
        try:compare(actual,bad)
        except AssertionError:changed.append(name)
        else:raise AssertionError(('Changed observation escaped',name))
    raw=raw_controls();source=evidence(args.private)
    basis={**observed['basisSha256'],**{str(p.relative_to(ROOT)):sha(p)for p in [
        HERE/n for n in['Overrides.lean','OverridesCase.lean','Overrides.bend','observations.py','conformance.py','probe.py']
    ]},'applications/sources/js-overrides-selections.json':sha(ROOT/'applications/sources/js-overrides-selections.json')}
    assert all(sha(ROOT/p)==s for p,s in basis.items())
    record=dict(schema=1,counts=counts,nativeCounts=observed['counters'],bothModelsMatch=True,input=data,
                bindings=bindings,results=actual,researchRefusals=refusals,premiseControls=controls,changedObservationControls=changed,rawObservationControls=raw,
                sourceAvailability=source,basisSha256=basis,driverSha256=sha(driver),
                tools={k:dict(path=str(Path(v).resolve()),sha256=sha(Path(v)))for k,v in [('lean',lean),('bend',bend)]},
                limits=['No application/native rerun; generated catalog and selected controls only.',
                        'Twenty-eight runtime pairs predicted uniquely; two pnpm overlapping-range observations only admitted among matching alternatives.',
                        'Lock adapter checks one Yarn descriptor; no full graph/solver/semver/linker/rollback/concurrency or other-host qualification.'])
    write(out/'comparison.json',record)
    print(json.dumps({k:record[k]for k in['counts','researchRefusals','premiseControls','changedObservationControls','rawObservationControls','sourceAvailability']}))


if __name__=='__main__':main()
