#!/usr/bin/env python3
"""Pure replay of retained mapping plans. Runs Lean/Bend, not Qt or MO2."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'applications/restic'))
from locks_probe import redact
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
NAME={'':0,'A':1,'B':2,'a':3,'missing':4,'overwrite':5}
PROFILE={'A':1,'B':2}
DEST={'/fixture/Data':1,'/fixture/Extra':2,'/fixture/Saves':3}
ORIGIN={'/fixture/mods/A':('mod',1),'/fixture/mods/B':('mod',2),'/fixture/overwrite':('overwrite',0),
        '/fixture/profiles/A/saves':('saves',1),'/fixture/profiles/B/saves':('saves',2),'/fixture/plugin':('plugin',1)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);a=p.parse_args();capture=a.capture.resolve()
    assert capture.is_relative_to(ROOT/'applications/evidence')
    receipt=json.loads((capture/'receipt.json').read_text());assert receipt['records']==19 and receipt['allOwnedProcessesRetired']
    for name,key in [('probe.py','producerSha256'),('driver.cpp','driverSha256'),('helper.py','helperSha256'),('cases.json','casesSha256'),('observe.stdout','observedSha256')]:assert sha(capture/name)==receipt[key]
    assert sha(ROOT/'applications/restic/locks_probe.py')==receipt['helperSha256']
    assert sha(capture/'work/routing-oracle')==receipt['binarySha256']
    assert sha(Path(receipt['compiler']['path']))==receipt['compiler']['sha256']
    assert sha(Path(receipt['sdk']['path'])/'SDKSettings.json')==receipt['sdk']['settingsSha256']
    source=ROOT/receipt['sourcePath'];text=source.read_text();selection=receipt['sourceSelection']
    assert sha(source)==receipt['sourceSha256']
    selected=text[text.index(selection['start']):text.index(selection['stop'])]
    assert hashlib.sha256(selected.encode()).hexdigest()==selection['sha256']==sha(capture/'work/selected_mapping.cpp')
    for value in json.loads((capture/'environment.json').read_text())['frameworks'].values():assert sha(Path(value['path']))==value['sha256']
    for command in json.loads((capture/'commands.json').read_text()):
        assert command['outcome']==dict(exitCode=0,timedOut=False)
        for stream in ['stdout','stderr']:
            info=command['streams'][stream];raw=capture/info['rawPrivatePath'];public=capture/(command['case']+'.'+stream)
            assert sha(raw)==info['rawSha256'] and sha(public)==info['publicSha256'] and redact(raw.read_bytes())==public.read_bytes()
    models=[HERE/n for n in ['Routing.lean','RoutingCase.lean','Routing.bend']]
    ledger=ROOT/'applications/sources/mo2-routing-selections.json';inputs=models+[ledger]+[p for p in capture.iterdir() if p.is_file() and p.name!='conformance.json']
    basis={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    for row in json.loads(ledger.read_text())['sources']:assert sha(ROOT/row['cache'])==row['sha256']
    requests=json.loads((capture/'cases.json').read_text());observations=[json.loads(line) for line in (capture/'observe.stdout').read_text().splitlines()]
    assert len(requests)==len(observations)==19 and len({r['case'] for r in requests})==19
    cases,expected=[],[]
    for request,record in zip(requests,observations):
        assert record['case']==request['case'] and record['request']==request
        assert record['qt']==receipt['qt']['pkgConfigVersion']=='6.12.0' and record['platformPlugin']=='offscreen'
        assert record['constructedProfile']=='/fixture/profiles/'+request['profile']
        assert request['dataPaths'] in [1,2]
        current=request['currentProfile'];requested=request['profile'];flags=request['localByProfile']
        plugin=dict(enabled=request['pluginEnabled'],rows=[dict(kind='plugin',identity=1,destination=1,directory=True,createTarget=True)])
        c=dict(active=[dict(identity=NAME[m['name']],reserved=m['name'].casefold()=='overwrite',regular=m['regular']) for m in request['active']],
            dataPaths=[1] if request['dataPaths']==1 else [1,2],custom=NAME[request['custom']],requestedProfile=PROFILE[requested],
            currentProfile=PROFILE[current],currentLocal=flags[current],requestedLocal=flags[requested],localFeature=request['localFeature'],
            plugins=[plugin] if request['plugin'] else [])
        observed=record['observed'];warning=record['warnings']
        assert len(warning)<=1 and (not warning or warning==['local save games not supported by this game plugin'])
        if not observed['accepted']:
            assert observed['error']=='The designated write target "'+request['custom']+'" is not enabled.'
            value='refuse/'+str(int(bool(warning)))
        else:
            rows=[]
            for mapping in observed['mappings']:
                kind,identity=ORIGIN[mapping['source']]
                assert type(mapping['directory']) is bool and type(mapping['createTarget']) is bool
                rows.append({'mod':'m','overwrite':'o','saves':'s','plugin':'p'}[kind]+str(identity)+':'+str(DEST[mapping['destination']])+':'+str(int(mapping['directory']))+':'+str(int(mapping['createTarget'])))
            value='accept/'+str(int(bool(warning)))+'/'+';'.join(rows)
        cases.append(c);expected.append(value)
    generated=HERE/'generated';generated.mkdir(exist_ok=True)
    data=dict(schema=1,cases=cases);path=generated/'routing.json';path.write_text(json.dumps(data,indent=2)+'\n')
    formal=generated/'routing-formal';artifact=formal/'applications/mo2/Routing.olean';artifact.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=str(formal),BEND_NO_TELEMETRY='1');lean=os.environ.get('LEAN','lean')
    compiled=subprocess.run([lean,'-DwarningAsError=true','-o',str(artifact),str(models[0])],cwd=ROOT,env=env,capture_output=True,text=True)
    assert compiled.returncode==0,compiled.stdout+compiled.stderr
    def lean_run(q):return subprocess.run([lean,'--run','applications/mo2/RoutingCase.lean',str(q)],cwd=ROOT,env=env,capture_output=True,text=True)
    result=lean_run(path);assert result.returncode==0,result.stdout+result.stderr
    actual=json.loads(result.stdout);assert actual['current']==expected and len(actual['proposed'])==19
    changed=[requests[i]['case'] for i,(x,y) in enumerate(zip(actual['current'],actual['proposed'])) if x!=y]
    assert changed==['nonregular-1','nonregular-2','local-different-profile-current-enabled','local-different-profile-selected-enabled']
    bit=lambda x:'True{}' if x else 'False{}'
    def listing(values):
        out='Nil{}'
        for value in reversed(values):out='Con{'+value+','+out+'}'
        return out
    def mapping_text(row):
        constructor={'mod':'ModOrigin','overwrite':'OverwriteOrigin','saves':'SaveOrigin','plugin':'PluginOrigin'}[row['kind']]
        origin='C.'+constructor+'{'+('' if row['kind']=='overwrite' else str(row['identity'])+'n')+'}'
        return 'C.RouteRow{'+','.join([origin,str(row['destination'])+'n',bit(row['directory']),bit(row['createTarget'])])+'}'
    def request_text(c):
        active=listing(['C.RouteMod{'+','.join([str(m['identity'])+'n',bit(m['reserved']),bit(m['regular'])])+'}' for m in c['active']])
        paths=listing([str(n)+'n' for n in c['dataPaths']])
        plugins=listing(['C.RoutePlugin{'+bit(p['enabled'])+','+listing([mapping_text(r) for r in p['rows']])+'}' for p in c['plugins']])
        return 'C.RouteRequest{'+','.join([active,paths,str(c['custom'])+'n',str(c['requestedProfile'])+'n',str(c['currentProfile'])+'n',
            bit(c['currentLocal']),bit(c['requestedLocal']),bit(c['localFeature']),plugins])+'}'
    calls=['pair('+request_text(c)+') ++ "\\n"' for c in cases]
    runner=generated/'RoutingCase.bend'
    runner.write_text('''import Base
import ../Routing.bend as C

def bit(b: Bool) -> String:
  match b:
    case True{}: "1"
    case False{}: "0"

def origin(o: C.RouteOrigin) -> String:
  match o:
    case C.ModOrigin{id}: "m" ++ Nat.show(id)
    case C.OverwriteOrigin{}: "o0"
    case C.SaveOrigin{id}: "s" ++ Nat.show(id)
    case C.PluginOrigin{id}: "p" ++ Nat.show(id)

def row(r: C.RouteRow) -> String:
  match r:
    case C.RouteRow{source,destination,directory,create}: origin(source) ++ ":" ++ Nat.show(destination) ++ ":" ++ bit(directory) ++ ":" ++ bit(create)

def joined(rows: List<&2, C.RouteRow>, prefix: String) -> String:
  match rows:
    case Nil{}: ""
    case Con{head,tail}: prefix ++ row(head) ++ joined(tail,";")

def render(r: C.RouteResult) -> String:
  match r:
    case C.RouteResult{accepted,warning,rows}:
      +w = warning
      Bool.pick(String,accepted,"accept/" ++ bit(w) ++ "/" ++ joined(rows,""),"refuse/" ++ bit(w))

def pair(+request: C.RouteRequest) -> String:
  render(C.plan(request,False{})) ++ "|" ++ render(C.plan(request,True{}))

def main() -> IO(Unit):
  IO.write('''+' ++ '.join(calls)+')\n')
    result=subprocess.run([os.environ.get('BEND','bend'),str(runner)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    pairs=[value.split('|') for value in result.stdout.splitlines()]
    assert [v[0] for v in pairs]==actual['current'] and [v[1] for v in pairs]==actual['proposed']
    negatives=[dict(data,schema=2)]+[dict(data,cases=[dict(cases[0],**change)]) for change in [dict(custom=6),dict(dataPaths=[]),dict(requestedProfile=0),dict(active=cases[0]['active']*2),dict(requestedLocal=True)]]
    bad=copy.deepcopy(cases[-2]);bad['plugins'][0]['rows'][0]['kind']='arbitrary';negatives.append(dict(data,cases=[bad]))
    bad=copy.deepcopy(cases[0]);bad['active'][0]['reserved']=False;negatives.append(dict(data,cases=[bad]))
    for i,value in enumerate(negatives):
        q=generated/f'routing-negative-{i}.json';q.write_text(json.dumps(value));result=lean_run(q);assert result.returncode==2 and result.stderr
    assert all(sha(ROOT/name)==digest for name,digest in basis.items())
    report=dict(schema=1,records=19,currentLeanMatches=True,currentBendMatches=True,proposedBendMatchesLean=True,
        researchInputsRefused=len(negatives),proposedDifferences=changed,basisSha256=basis,adapterSha256=sha(Path(__file__)),
        currentModels=actual['current'],proposedModels=actual['proposed'],
        limits=['Exact source method with fixture game/profile/catalog/save/plugin data; not native MO2/Windows/USVFS/physical writes.',
            'Active rows are already selected input; changing profile labels alone does not represent loading a different native profile.',
            'Local-save callback shape and plugin row profile are supplied fixture witnesses, not general plugin behavior or callback side-effect ordering.',
            'Four proposed differences are model-only; normal UI/caller reachability and intended profile-override semantics remain unresolved.',
            'Current Qt framework hashes are post-run readback. No supported-consumer/reproducible-build qualification.'])
    (capture/'conformance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['basisSha256','currentModels','proposedModels']},indent=2))


if __name__=='__main__':main()
