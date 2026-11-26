"""Retained four-window lifecycle comparison. Never launches VS Code."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import activation_observer as obs

ROOT=obs.ROOT
WORK=ROOT/'.build/vscode-activation-replay'
LEAN=os.environ.get('LEAN','lean')
BEND=os.environ.get('BEND','bend')
ENV={**os.environ,'LEAN_PATH':str(WORK/'formal'),'BEND_NO_TELEMETRY':'1'}

def run(argv):return subprocess.run(argv,cwd=ROOT,env=ENV,capture_output=True,text=True,timeout=120)

def main():
    WORK.mkdir(parents=True,exist_ok=True);formal=WORK/'formal/applications/vscode';formal.mkdir(parents=True,exist_ok=True)
    for name in ['Activation','ActivationCase']:
        p=run([LEAN,'-DwarningAsError=true','-o',str(formal/(name+'.olean')),'applications/vscode/'+name+'.lean'])
        assert p.returncode==0,p.stdout+p.stderr
    data,observed,effects,excluded,basis,bundle,associations=obs.evidence('--public'not in sys.argv)
    for name in ['Activation.lean','ActivationCase.lean','Activation.bend','activation_observer.py','activation_conformance.py']:
        p=obs.HERE/name;basis[str(p.relative_to(ROOT))]=obs.sha(p)
    path=WORK/'input.json'
    def replay(value):
        path.write_text(json.dumps(value)+'\n');return run([LEAN,'--run','applications/vscode/ActivationCase.lean',str(path)])
    p=replay(data);assert p.returncode==0,p.stdout+p.stderr
    assert json.loads(p.stdout)==observed,(p.stdout,observed)
    actions={'startup':0,'activate':1,'disable-workspace':2,'enable-workspace':3,'held-ping':4,'quit-requested':5,'retired':6}
    state='A.State{A.Policy{False{},0n,0n},False{},False{},False{},False{},False{}}'
    expressions=[]
    for row in data['events']:
        args=state+','+('True{}'if row['workspace']=='b'else'False{}')+','+str(actions[row['action']])+'n'
        expressions.append('A.observe('+args+')');state='A.step('+args+')'
    driver=WORK/'ActivationReplay.bend';driver.write_text('import Base\nimport '+str(obs.HERE/'Activation.bend')+' as A\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join('('+v+' ++ "\\n")'for v in expressions)+')\n')
    def scalar(value):
        if value is None:return '~'
        if isinstance(value,bool):return str(int(value))
        return str(value)
    expected=['/'.join(scalar(r[k])for k in ['visible','apiActive','ping','storedOverride','hooks','retired'])for r in observed]
    p=run([BEND,str(driver)]);assert p.returncode==0,p.stdout+p.stderr
    assert p.stdout.splitlines()==expected,(p.stdout,expected)
    idx={(r['phase'],r['action']):i for i,r in enumerate(data['events'])}
    retired=idx['a-disable','retired'];quit=idx['a-disable','quit-requested']
    def set_event(d,index,**kw):d['events'][index].update(**kw)
    refused=[]
    for name,edit in [
      ('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='all-extension-lifecycles')),
      ('global-premise',lambda d:d.update(initialGlobalDisabled=True)),
      ('empty-trace',lambda d:d.update(events=[])),('bound',lambda d:d.update(events=d['events']*2)),
      ('unknown-action',lambda d:set_event(d,0,action='kill')),
      ('workspace-identity',lambda d:set_event(d,0,workspace='remote')),
      ('phase-identity',lambda d:set_event(d,0,phase='personal-profile')),
      ('scope-disagreement',lambda d:set_event(d,0,workspace='b')),
      ('before-open',lambda d:set_event(d,0,action='activate')),
      ('missing-exit',lambda d:set_event(d,retired,mainExited=False)),
      ('missing-PID-absence',lambda d:set_event(d,retired,trackedAbsent=False)),
      ('retire-before-quit',lambda d:set_event(d,quit,action='retired',mainExited=True,trackedAbsent=True)),
      ('live-retirement-witness',lambda d:set_event(d,1,mainExited=True)),
      ('activate-absent-target',lambda d:set_event(d,idx['a-enable','enable-workspace'],action='activate')),
      ('ping-before-activation',lambda d:set_event(d,1,action='held-ping')),
      ('incomplete-retirement',lambda d:d['events'].pop())]:
        bad=copy.deepcopy(data);edit(bad);p=replay(bad)
        assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);refused.append(name)
    raw=[]
    def changed(name,edit,effect_only=False):
        value=copy.deepcopy(bundle);edit(value)
        try:_,result,new_effects,_=obs.observe(value,associations)
        except (AssertionError,KeyError):
            assert not effect_only,'The effect-only control must retain a valid trace.'
            raw.append({'name':name,'effectOnly':effect_only});return
        if effect_only:assert result==observed and new_effects!=effects,name
        else:assert result!=observed,name
        raw.append({'name':name,'effectOnly':effect_only})
    def api_row(b,phase,action):return next(r for r in b[phase][0]['rows']if r['action']==action)
    def active_flag(b):
        row=api_row(b,'a-disable','disable-workspace');row['observed']['isActive']=False
        next(r for r in row['observed']['knownOwned']if r['id']==obs.ID)['active']=False
    changed('disabled-running-observation',active_flag)
    changed('held-API-value',lambda b:api_row(b,'a-disable','held-ping')['returned'].update(value='stale-activation-ack'))
    changed('fresh-heartbeat-PID',lambda b:api_row(b,'a-disable','held-ping')['observed']['heartbeat'].update(pid=1))
    def erase_policy(b):
        rows=b['a-disable'][1]['afterStorage'];db=next(r for r in rows if r['path']==associations['a']['db']);db['rows']=[]
    changed('saved-workspace-policy',erase_policy)
    changed('other-workspace-identity',lambda b:b['b-other'][0]['identity'].update(workspace=[associations['a']['uri']]))
    changed('cross-window-storage-basis',lambda b:b['b-other'][2]['storage'][0].update(rows=[]))
    changed('disabled-reopen-API',lambda b:api_row(b,'a-enable','startup').update(observed=copy.deepcopy(api_row(b,'a-confirm','startup')['observed'])))
    def admission_is_not_activation(b):
        row=api_row(b,'a-enable','enable-workspace');row['observed']['isActive']=True
        next(r for r in row['observed']['knownOwned']if r['id']==obs.ID)['active']=True
    changed('enablement-activation-observation',admission_is_not_activation)
    changed('main-exit',lambda b:b['a-disable'][1].update(exit=1))
    changed('PID-still-present',lambda b:b['a-disable'][4].update(presentAfterExit=[b['a-disable'][0]['identity']['pid']]))
    changed('missing-deactivate-hook',lambda b:b['a-disable'][5].pop(-2))
    changed('target-receipt-PID',lambda b:b['b-other'][5][1].update(pid=1))
    def bundled_scope(b):
        for rows in [b['a-enable'][1]['afterStorage'],b['a-confirm'][2]['storage'],b['a-confirm'][1]['afterStorage']]:
            db=next(r for r in rows if r['path']==associations['a']['db'])
            next(r for r in db['rows']if r['key']=='extensionsIdentifiers/enabled')['value']=json.dumps([{'id':obs.ID}])
    changed('bundled-enable-effect',bundled_scope,True)
    assert all(obs.sha(ROOT/p)==h for p,h in basis.items()),'Evidence changed during replay.'
    path.write_text(json.dumps(data,indent=2)+'\n');(WORK/'observed.json').write_text(json.dumps(observed,indent=2)+'\n')
    report={'schema':1,'profile':data['profile'],'nativeDesktopPhases':4,'nativeCLIInstalls':1,
      'joinedLifecycleObservations':len(observed),'leanComparisons':len(observed),'bendComparisons':len(observed),
      'sourceMethodsExecuted':0,'refusedResearchDTOs':refused,'changedNativeObservations':raw,
      'basisSha256':basis,'privateExcluded':excluded,'effects':effects,
      'limits':['One serial four-window lifecycle, not eighteen independent complete workflows.',
        'Stored policy compared only at actual after-exit SQLite readbacks; other rows deliberately have null storedOverride.',
        'Quit request is separate from normal exit, target hooks and tracked process absence; arbitrary detached children and crash shutdown are not qualified.',
        'No GUI/app/source-method/extension execution by this checker; UI command bodies and API docs are read-only source context.',
        'Enable All Workspace includes a bundled extension override, not only the owned target; its actual execution is not inferred.']}
    (WORK/'conformance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in ['basisSha256','effects']},indent=2))

if __name__=='__main__':main()
