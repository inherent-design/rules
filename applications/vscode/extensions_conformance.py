"""Compare both models with retained CLI/source observations; no app launch."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import extensions_observer as obs

ROOT=obs.ROOT
WORK=ROOT/'.build/vscode-extensions-replay'
LEAN=os.environ.get('LEAN','lean')
BEND=os.environ.get('BEND','bend')
ENV={**os.environ,'LEAN_PATH':str(WORK/'formal'),'BEND_NO_TELEMETRY':'1'}

def run(argv):
    return subprocess.run(argv,cwd=ROOT,env=ENV,capture_output=True,text=True,timeout=120)

def main():
    WORK.mkdir(parents=True,exist_ok=True)
    formal=WORK/'formal/applications/vscode';formal.mkdir(parents=True,exist_ok=True)
    for name in ['Extensions','ExtensionsCase']:
        p=run([LEAN,'-DwarningAsError=true','-o',str(formal/(name+'.olean')),'applications/vscode/'+name+'.lean'])
        assert p.returncode==0,p.stdout+p.stderr
    data,observed,effects,excluded,basis=obs.evidence('--public'not in sys.argv)
    for name in ['Extensions.lean','ExtensionsCase.lean','Extensions.bend','extensions_observer.py','extensions_conformance.py']:
        path=obs.HERE/name;basis[str(path.relative_to(ROOT))]=obs.sha(path)
    selected=ROOT/'applications/sources/vscode-extensions-selections.json';basis[str(selected.relative_to(ROOT))]=obs.sha(selected)
    path=WORK/'input.json'
    def replay(value):
        path.write_text(json.dumps(value)+'\n')
        return run([LEAN,'--run','applications/vscode/ExtensionsCase.lean',str(path)])
    p=replay(data);assert p.returncode==0,p.stdout+p.stderr
    assert json.loads(p.stdout)==observed,(p.stdout,observed)
    bool_bend=lambda b:'True{}'if b else'False{}'
    list_bend=lambda xs:'['+','.join(json.dumps(v)for v in xs)+']'
    expressions=[];expected=[]
    for r,o in zip(data['hosts'],observed['hosts']):
        ld=r['development']in['local','both'];rd=r['development']in['remote','both']
        pref='E.preference('+bool_bend(ld)+','+bool_bend(rd)+')'
        kinds='E.effective('+bool_bend(r['local'])+','+list_bend(r['localKinds'])+','+list_bend(r['remoteKinds'])+')'
        expressions.append('Nat.show(E.select('+','.join([kinds,*[bool_bend(v)for v in[r['surface']=='browser',r['local'],r['remote'],r['remoteHost'],r['worker']]],pref])+')) ++ "/" ++ Nat.show('+pref+')')
        expected.append(str(o['host'])+'/'+str(o['preference']))
    for r,o in zip(data['management'],observed['management']):
        expressions.append('E.manage('+','.join([str({'query':0,'install':1,'uninstall':2}[r['operation']])+'n',str(r['registered'])+'n',str(r['requested'])+'n',bool_bend(r['compatible'])])+')')
        expected.append(o['action']+'/'+str(o['exit'])+'/'+str(o['registered']))
    driver=WORK/'ExtensionsReplay.bend'
    driver.write_text('import Base\nimport '+str(obs.HERE/'Extensions.bend')+' as E\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join('('+v+' ++ "\\n")'for v in expressions)+')\n')
    p=run([BEND,str(driver)]);assert p.returncode==0,p.stdout+p.stderr
    assert p.stdout.splitlines()==expected,(p.stdout,expected)
    # Bounded codec refuses unsupported surfaces and impossible caller premises.
    refusals=[]
    changes=[('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='all-extensions')),
      ('missing-band',lambda d:d.update(management=[])),('case-bound',lambda d:d.update(hosts=d['hosts']*2)),
      ('unknown-surface',lambda d:d['hosts'][0].update(surface='remote-ui')),
      ('unknown-kind',lambda d:d['hosts'][0].update(localKinds=['node'])),
      ('empty-kinds',lambda d:d['hosts'][0].update(localKinds=[])),
      ('duplicate-kind',lambda d:d['hosts'][0].update(localKinds=['ui','ui'])),
      ('absent-scan',lambda d:d['hosts'][0].update(local=False,remote=False)),
      ('remote-host',lambda d:d['hosts'][2].update(remoteHost=False)),
      ('worker-unavailable-browser',lambda d:d['hosts'][18].update(worker=False)),
      ('development-placement',lambda d:d['hosts'][0].update(development='remote')),
      ('unknown-development',lambda d:d['hosts'][0].update(development='user-preference')),
      ('registered-version',lambda d:d['management'][0].update(registered=7)),
      ('engine-witness',lambda d:d['management'][1].update(compatible=False)),
      ('query-operand',lambda d:d['management'][0].update(requested=1))]
    for name,edit in changes:
        bad=copy.deepcopy(data);edit(bad);p=replay(bad)
        assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);refusals.append(name)
    premises=[];idx={r['label']:i for i,r in enumerate(data['hosts'])}
    for name,label,edit in [
      ('worker-availability','worker-enabled',lambda r:r.update(worker=False)),
      ('remote-window','desktop-local-workspace',lambda r:r.update(remoteHost=True)),
      ('kind-order','ui-first',lambda r:r.update(localKinds=['workspace','ui'])),
      ('development-preference','remote-development',lambda r:r.update(development='none')),
      ('local-manifest','local-manifest-wins',lambda r:r.update(localKinds=['workspace'])),
      ('browser-reserve','browser-web-before-ui-reserve',lambda r:r.update(localKinds=['ui']))]:
        bad=copy.deepcopy(data);edit(bad['hosts'][idx[label]]);p=replay(bad)
        assert p.returncode==0 and json.loads(p.stdout)!=observed,(name,p.stdout,p.stderr);premises.append(name)
    bad=copy.deepcopy(data);bad['management'][7]['registered']=1;p=replay(bad)
    assert p.returncode==0 and json.loads(p.stdout)!=observed
    premises.append('downgrade-registration-basis')
    native_rows=obs.read(obs.NATIVE/'commands.json');native_streams={r['label']:{n:(obs.NATIVE/v['path']).read_text()for n,v in r['streams'].items()}for r in native_rows}
    raw=[];ni={r['label']:i for i,r in enumerate(native_rows)}
    def native_change(name,edit):
        rs=copy.deepcopy(native_rows);ss=copy.deepcopy(native_streams);edit(rs,ss)
        try:_,value,_=obs.observe_native(rs,ss)
        except (AssertionError,KeyError):raw.append(name);return
        assert value!=observed['management'],name;raw.append(name)
    native_change('refusal-exit',lambda rs,ss:rs[ni['incompatible']].update(exit=0))
    native_change('list-readback',lambda rs,ss:ss['after-refusal'].update(stdout=obs.IDENTITY+'@0.0.2\n'))
    native_change('retained-directory',lambda rs,ss:rs[ni['uninstall']]['after']['packages'].pop(next(iter(rs[ni['uninstall']]['after']['packages']))))
    native_change('activation-beacon',lambda rs,ss:rs[ni['uninstall']]['after'].update(activationBeacon=True))
    native_change('downgrade-disposition',lambda rs,ss:ss['downgrade'].update(stdout='Installing extensions...\n'))
    native_change('membership-after-refusal',lambda rs,ss:rs[ni['incompatible']]['after'].update(membership=[]))
    hosts=obs.read(obs.SOURCE/'observed.json')
    for name,field,value in [('host-choice','host',2),('development-preference','preference',2),('effective-kinds','kinds',['web'])]:
        changed=copy.deepcopy(hosts);changed[0]['callback'][field]=value
        if field=='host':changed[0]['entries'][0][1]=value
        altered=obs.observe_hosts(data['hosts'],changed)
        assert altered!=observed['hosts'],name;raw.append(name)
    assert all(obs.sha(ROOT/p)==h for p,h in basis.items()),'Evidence or models changed during replay.'
    path.write_text(json.dumps(data,indent=2)+'\n')
    report={'schema':1,'profile':data['profile'],'nativeCLICalls':13,'nativeManagementOutcomes':12,'sourceHostOutcomes':30,
      'leanComparisons':42,'bendComparisons':42,'refusedDTOs':refusals,'changedPremises':premises,
      'changedRawObservations':raw,'basisSha256':basis,'privateExcluded':excluded,'effects':effects,
      'scope':'Retained native local VSIX management plus selected source caller/host methods; no app, extension, remote, browser, GUI, or network execution by this checker.'}
    (WORK/'conformance.json').write_text(json.dumps(report,indent=2)+'\n')
    (WORK/'observed.json').write_text(json.dumps(observed,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k not in ['basisSha256','effects']},indent=2))

if __name__=='__main__':main()
