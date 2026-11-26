"""Read retained extension evidence. Does not run Code, Node, or extensions."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
NATIVE=ROOT/'applications/evidence/vscode-extensions-20261126T040016341935Z'
SOURCE=ROOT/'applications/evidence/vscode-host-selection-20261126T040253545Z'
IDENTITY='rules-study.lifecycle-fixture'
VERSION='661626d0e72f97806550790a98fb87116c9db825'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def registered(snapshot):
    members=snapshot['membership']
    assert len(members)<=1
    if not members:return 0
    assert members[0]['identifier']['id']==IDENTITY
    return {'0.0.1':1,'0.0.2':2}[members[0]['version']]

def observe_native(rows,streams):
    labels=['version','empty','install-one','list-one','incompatible','after-refusal','install-two',
            'list-two','downgrade','after-downgrade','uninstall','after-uninstall','uninstall-again']
    assert [r['label']for r in rows]==labels
    requests=[];observed=[];effects=[];previous=None
    for row in rows:
        label=row['label'];before=row['before'];after=row['after'];out=streams[label]['stdout'];err=streams[label]['stderr']
        assert not row['timedOut'] and row['exit']in [0,1]
        assert not before['activationBeacon'] and not after['activationBeacon']
        assert before['settingsSha256']==after['settingsSha256']
        if previous is not None:assert before['membership']==previous['membership']
        previous=after
        if label=='version':
            assert out.splitlines()==['1.148.0',VERSION,'arm64'] and row['exit']==0
            continue
        old,new=registered(before),registered(after)
        requested=0;compatible=True
        if '--install-extension'in row['argv']:
            operation='install';arg=row['argv'][row['argv'].index('--install-extension')+1]
            requested={'fixture-0.0.1.vsix':1,'fixture-0.0.2.vsix':2,'fixture-0.0.3.vsix':3}[Path(arg).name]
            compatible=requested!=3
            assert '--force'not in row['argv']
            if row['exit']:
                assert 'not compatible with VS Code' in err;action='refused'
            elif 'successfully installed.'in out:action='installed'
            else:
                assert 'newer version'in out and "Use '--force'"in out;action='skipped'
        elif '--uninstall-extension'in row['argv']:
            operation='uninstall'
            assert row['argv'][-1]==IDENTITY
            if row['exit']==0:
                assert 'successfully uninstalled!'in out;action='removed'
            else:
                assert 'is not installed.'in err;action='absent'
        else:
            operation='query';action='listed'
            assert '--list-extensions'in row['argv'] and '--show-versions'in row['argv']
            assert out.splitlines()==([]if new==0 else[IDENTITY+'@0.0.'+str(new)])
        requests.append(dict(label=label,operation=operation,registered=old,requested=requested,compatible=compatible))
        observed.append(dict(label=label,action=action,exit=row['exit'],registered=new))
        effects.append(dict(label=label,registered=new,physicalVersions=sorted(v['version']for v in after['packages'].values()),
                            obsolete=after['obsolete'],activationBeacon=after['activationBeacon']))
    # Concrete identity and retention witnesses, not a promise about arbitrary failures.
    by={r['label']:r for r in rows}
    assert by['incompatible']['before']['membership']==by['incompatible']['after']['membership']
    assert by['incompatible']['before']['packages']==by['incompatible']['after']['packages']
    assert by['downgrade']['before']['membership']==by['downgrade']['after']['membership']
    assert by['uninstall']['after']['membership']==[]
    assert sorted(p['version']for p in by['uninstall']['after']['packages'].values())==['0.0.1','0.0.2']
    assert by['uninstall']['after']['obsolete']=={IDENTITY+'-0.0.1':True}
    return requests,observed,effects

def observe_hosts(requests,rows):
    assert len(rows)==len(requests)==30
    observed=[]
    for request,row in zip(requests,rows):
        assert request['label']==row['label']
        c=row['callback'];assert c['host']in [None,1,2,3] and c['preference']in[0,1,2]
        assert c['local']==request['local'] and c['remote']==request['remote']
        assert row['entries']==[['rules-study.fixture',c['host']]]
        assert c['identifier']==('rules-study.fixture'if request['local']else'RULES-STUDY.FIXTURE')
        observed.append(dict(label=row['label'],host=c['host']or 0,preference=c['preference'],kinds=c['kinds']))
    return observed

def evidence(private=True):
    nr=read(NATIVE/'receipt.json');sr=read(SOURCE/'receipt.json');setup=read(NATIVE/'setup.json')
    assert nr['revision']==sr['revision']==setup['revision']==VERSION
    assert nr['commands']==13 and sr['cases']==30
    assert sha(NATIVE/'commands.json')==nr['commandsSha256']
    assert sha(NATIVE/'setup.json')==nr['setupSha256']
    for name,digest in sr['files'].items(): assert sha(SOURCE/name)==digest
    assert sha(ROOT/'applications/sources/vscode-extensions-selections.json')==sr['selectionSha256']
    rows=read(NATIVE/'commands.json');streams={}
    for row in rows:
        streams[row['label']]={}
        for name,ref in row['streams'].items():
            path=NATIVE/ref['path'];assert sha(path)==ref['sha256'] and path.stat().st_size==ref['bytes']
            streams[row['label']][name]=path.read_text()
        for flag in ['user-data-dir','extensions-dir','extensions-download-dir','shared-data-dir','agent-plugins-dir','agents-user-data-dir','agents-extensions-dir']:
            at=row['argv'].index('--'+flag);assert Path(row['argv'][at+1]).is_relative_to(setup['private'])
    installed_readback=read(NATIVE/'installed-manifest-readback.json')['manifests']
    for version in ['0.0.1','0.0.2','0.0.3']:
        with zipfile.ZipFile(NATIVE/('fixture-'+version+'.vsix'))as z:
            manifest=z.read('extension/package.json');value=json.loads(manifest)
            assert value['version']==version and value['publisher']+'.'+value['name']==IDENTITY
            matches=[p for row in rows for p in row['after']['packages'].values()if p['version']==version]
            if version=='0.0.3':assert not matches
            else:
                [installed]=[r for r in installed_readback if r['manifest']['version']==version]
                installed_manifest=dict(installed['manifest']);metadata=installed_manifest.pop('__metadata')
                assert installed_manifest==value and 'installedTimestamp'in metadata
                assert matches and all(p['sha256']==installed['sha256']for p in matches)
                for member in ['main.cjs','browser.js']:
                    body=z.read('extension/'+member);digest=hashlib.sha256(body).hexdigest()
                    expected='extensions/'+IDENTITY+'-'+version+'/'+member
                    observed_files=[f for row in rows for f in row['after']['files']if f['path']==expected]
                    assert observed_files and all(f['sha256']==digest for f in observed_files)
    retirement=read(NATIVE/'retirement.json');assert retirement['allChildrenWaited']and retirement['matchingProcesses']==[]and not retirement['beaconPresent']
    request=read(SOURCE/'requests.json');host_observed=observe_hosts(request['cases'],read(SOURCE/'observed.json'))
    management,native_observed,effects=observe_native(rows,streams)
    omitted=[]
    ledger=read(ROOT/'applications/sources/vscode-extensions-selections.json')
    for src in ledger['sources']:
        path=ROOT/src['cache']
        if private and path.exists():assert sha(path)==src['sha256']
        else:omitted.append('source:'+src['id'])
    if not private:omitted.extend(['installed-Code-and-bundled-resources','private-profile-home-and-state','after-collection-tool-readback','failed-guard-and-compiler-prereads'])
    else:
        readback=read(ROOT/'.build/vscode-extensions-preread/tool-readback.json')
        for path,ref in readback['files'].items():assert sha(path)==ref['sha256']
        # Only this fixture's installed bytes; no profile mutation or application run.
        private_root=Path(setup['private'])
        for p in rows[-1]['after']['packages']:
            assert sha(private_root/p)==rows[-1]['after']['packages'][p]['sha256']
        assert not (private_root/'activated.json').exists()
    data={'schema':1,'profile':'vscode-1.148-local-vsix-and-source-hosts','hosts':request['cases'],'management':management}
    observed={'hosts':host_observed,'management':native_observed}
    basis={}
    for folder in [NATIVE,SOURCE]:
        for path in folder.iterdir():
            if path.is_file():basis[str(path.relative_to(ROOT))]=sha(path)
    return data,observed,effects,omitted,basis

if __name__=='__main__':
    import sys
    data,observed,effects,omitted,basis=evidence('--public'not in sys.argv)
    print(json.dumps({'hosts':len(data['hosts']),'management':len(data['management']),'basis':len(basis),'privateExcluded':omitted,'effects':effects},indent=2))
