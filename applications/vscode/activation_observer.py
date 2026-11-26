"""Interpret retained native API, target, SQLite, and process observations."""
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
CAP=ROOT/'applications/evidence/vscode-activation-20261126T042148920855Z'
PHASES=['a-disable','b-other','a-enable','a-confirm']
ID='rules-study.activation-target'
REVISION='661626d0e72f97806550790a98fb87116c9db825'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def identities(value):
    result=json.loads(value);assert isinstance(result,list)
    keys=[r['id']for r in result];assert len(keys)==len(set(keys));return set(keys)
def policy(rows,path):
    selected=[r for r in rows if r['path']==path];assert len(selected)==1,path
    values={r['key']:r['value']for r in selected[0]['rows']}
    assert len(values)==len(selected[0]['rows'])
    enabled=identities(values.get('extensionsIdentifiers/enabled','[]'))
    disabled=identities(values.get('extensionsIdentifiers/disabled','[]'))
    assert not enabled&disabled
    return enabled,disabled
def member(rows):
    assert len(rows)==1 and rows[0]['identifier']['id']==ID and rows[0]['version']=='0.0.1'
    return rows[0]

def observe(bundle,associations):
    request=[];observed=[];effects=[];all_pids=set();previous_storage=None;previous_membership=None
    for phase in PHASES:
        raw,terminal,before,tree,retirement,target=bundle[phase]
        identity=raw['identity'];scope='b'if phase=='b-other'else'a'
        assert identity['phase']==phase and identity['version']=='1.148.0'
        assert identity['uiKind']==1 and identity['remoteName']is None and identity['trusted']is True
        assert identity['workspace']==[associations[scope]['uri']]
        assert raw['status']=='quit-requested' and terminal['exit']==0
        assert before['membership']==terminal['membership'];member(terminal['membership'])
        if previous_storage is not None:
            assert before['storage']==previous_storage
            assert before['membership']==previous_membership
        previous_storage=terminal['afterStorage'];previous_membership=terminal['membership']
        assert tree['root']==int(identity['codePid']) and tree['root']!=identity['pid']
        processes=tree['observedDescendants'];pids={r['pid']for r in processes}
        assert len(pids)==len(processes) and tree['root']in pids and identity['pid']in pids
        assert set(retirement['trackedPIDs'])==pids and retirement['presentAfterExit']==[]
        assert not pids&all_pids;all_pids|=pids
        names=[r['kind']for r in target]
        for event in target:assert event['phase']==phase and event['pid']==identity['pid']
        assert names.count('activate')<=1 and names.count('deactivate')<=1 and names.count('dispose')<=1
        hooks='deactivate'in names
        assert hooks==('dispose'in names)
        if hooks:
            assert names[0]=='activate'and names[-2:]==['deactivate','dispose']
            assert target[0]['mode']==1
        elif names:raise AssertionError('Target events lack normal shutdown closure.')
        pings=[e for e in target if e['kind']=='ping'];used_pings=[]
        committed=[];pending=None;sequence=0
        for row in raw['rows']:
            action=row['action'];assert row.get('error')is None
            if action.startswith('requested-'):
                assert pending is None and row['sequence']==sequence+1
                pending=action.removeprefix('requested-');continue
            if action=='startup':
                assert sequence==0 and not committed and row['sequence']==0
            else:
                assert pending is not None
                assert action==('quit-requested'if pending=='quit'else pending)
                sequence+=1;assert row['sequence']==sequence;pending=None
            view=row['observed'];visible=view['visible'];active=view['isActive']
            assert isinstance(visible,bool)
            owned=[r for r in view['knownOwned']if r['id']==ID]
            if visible:
                assert isinstance(active,bool)and view['kind']==1 and view['version']=='0.0.1'
                assert len(owned)==1 and owned[0]['active']==active
                assert view['path']==terminal['membership'][0]['location']['fsPath']
            else:
                assert active is None and view['kind']is None and view['path']is None and not owned
            ping=action in ['activate','held-ping']
            if ping:
                ret=row['returned'];expected='activation-ack'if action=='activate'else'held-after-policy'
                assert active is True and ret['value']==expected and ret['pid']==identity['pid']
                matches=[e for e in pings if e['value']==expected]
                assert len(matches)==1 and matches[0]['ticks']==ret['ticks']
                heartbeat=view['heartbeat'];assert heartbeat['pid']==identity['pid']and heartbeat['ticks']>=ret['ticks']
                used_pings.append(expected)
            else:assert row.get('returned')is None
            committed.append(action)
            request.append({'phase':phase,'workspace':scope,'action':action,'mainExited':False,'trackedAbsent':False})
            observed.append({'phase':phase,'action':action,'visible':visible,'apiActive':active,
                'ping':ping,'storedOverride':None,'hooks':None,'retired':False})
        assert pending is None and sequence==raw['handled']and committed[-1]=='quit-requested'
        assert sorted(used_pings)==sorted(e['value']for e in pings)
        assert ('activate'in committed)==('activate'in names)
        enabled,disabled=policy(terminal['afterStorage'],associations[scope]['db'])
        global_enabled,global_disabled=policy(terminal['afterStorage'],'data/User/globalStorage/state.vscdb')
        assert ID not in global_enabled|global_disabled
        override=1 if ID in enabled else 2 if ID in disabled else 0
        prior_paths={r['path']for r in before['storage']}
        prior=policy(before['storage'],associations[scope]['db'])if associations[scope]['db']in prior_paths else None
        request.append({'phase':phase,'workspace':scope,'action':'retired','mainExited':True,'trackedAbsent':True})
        observed.append({'phase':phase,'action':'retired','visible':None,'apiActive':None,
            'ping':False,'storedOverride':override,'hooks':hooks,'retired':True})
        effects.append({'phase':phase,'workspace':scope,'workspaceEnabled':sorted(enabled),
            'workspaceDisabled':sorted(disabled),'globalDisabled':sorted(global_disabled),
            'priorWorkspaceEnabled':sorted(prior[0])if prior is not None else None,
            'priorWorkspaceDisabled':sorted(prior[1])if prior is not None else None,
            'workspaceEnabledAdded':sorted(enabled-prior[0])if prior is not None else None,
            'registeredVersion':terminal['membership'][0]['version'],'targetEvents':names,
            'trackedPIDs':sorted(pids)})
    return {'schema':1,'profile':'vscode-1.148-owned-workspace-runtime','initialGlobalDisabled':False,'events':request},observed,effects,all_pids

def evidence(private=True):
    meta=read(CAP/'meta.json');basis=read(CAP/'collection-basis.json')['basisSha256']
    assert meta['revision']==REVISION
    for path,digest in basis.items():assert sha(ROOT/path)==digest,path
    for name,key in [('activation_probe.py','producerSha256'),('activation-controller.cjs','controllerSha256'),('activation-target.cjs','targetSha256')]:
        assert sha(CAP/name)==meta[key]==sha(HERE/name)
    association_readback=read(CAP/'workspace-storage-map.json');associations={}
    for row in association_readback['rows']:
        uri=row['association']['folder'];scope='a'if uri.endswith('/workspace-a')else'b'
        assert uri=='file://'+meta['private']+'/workspace-'+scope and scope not in associations
        associations[scope]={'uri':uri,'db':str(Path(row['path']).parent/'state.vscdb')}
    assert set(associations)=={'a','b'}
    bundle={}
    for phase in PHASES:
        target=CAP/(phase+'.target.jsonl')
        bundle[phase]=[read(CAP/(phase+suffix))for suffix in['.observed.json','.exit.json','.before.json','.tree-before-quit.json','.retirement.json']]+[[json.loads(s)for s in target.read_text().splitlines()]if target.exists()else[]]
        assert bundle[phase][1]['codeSha256']==meta['codeSha256']
        assert bundle[phase][1]['targetSha256']==meta['targetSha256']
    data,observed,effects,pids=observe(bundle,associations)
    complete=read(CAP/'collection-complete.json');assert set(complete['trackedPIDs'])==pids and len(pids)==29
    assert complete['allFourMainProcessesWaited']and complete['trackedPIDsStillPresent']==[]and complete['privatePathProcessMatches']==[]
    excluded=[]
    selections=read(ROOT/'applications/sources/vscode-activation-selections.json')
    for source in selections['sources']:
        path=ROOT/source['cache']
        if private:assert sha(path)==source['sha256']
        else:excluded.append('source:'+source['path'])
    if private:
        p=Path(meta['private']);assert sha(p/'controller/controller.cjs')==meta['controllerSha256']
        assert sha(p/'extensions/rules-study.activation-target-0.0.1/target.cjs')==meta['targetSha256']
        assert sha('/Applications/Visual Studio Code.app/Contents/MacOS/Code')==meta['codeSha256']
        for row in association_readback['rows']:assert sha(p/row['path'])==row['sha256']
        # Read only selected current SQLite rows; earlier query images are retained values.
        for db in bundle['a-confirm'][1]['afterStorage']:
            with sqlite3.connect('file:'+str(p/db['path'])+'?mode=ro',uri=True)as conn:
                rows=conn.execute("select key,value from ItemTable where key like '%extensionsIdentifiers%' or key like '%disabledExtensions%'").fetchall()
            captured={r['key']:r['value']for r in db['rows']};current={k:v.decode()if isinstance(v,bytes)else v for k,v in rows}
            assert captured==current
    else:excluded+=['installed-Code','private-controller-and-target','current-SQLite-and-association-files','private-main-streams','prepared-originals']
    basis=dict(basis)
    for path in CAP.iterdir():
        if path.is_file():basis[str(path.relative_to(ROOT))]=sha(path)
    return data,observed,effects,excluded,basis,bundle,associations

if __name__=='__main__':
    import sys
    data,observed,effects,excluded,basis,_,_=evidence('--public'not in sys.argv)
    print(json.dumps({'observations':len(observed),'basis':len(basis),'excluded':excluded,'effects':effects},indent=2))
