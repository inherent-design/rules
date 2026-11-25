#!/usr/bin/env python3
"""Inspect retained Qt/source/library evidence and independent private postimages."""
import hashlib,json
from pathlib import Path
from java_probe import function
ROOT=Path(__file__).resolve().parents[2];RUN=ROOT/'applications/evidence/prism-library-20261125T092450586460Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def inspect(native=None):
    receipt=read(RUN/'receipt.json');work=Path(receipt['work']);frozen=read(RUN/'observed.json')['rows']
    assert frozen==[json.loads(s)for s in(RUN/'observe.stdout').read_text().splitlines()]
    rows=frozen if native is None else native
    ids=['rename-label','rename-wrong-role','duplicate-label','group-directory','group-uuid-first','group-uuid-existing','group-uuid-candidate','lookup-collision','rename-group-merge','delete-group','trash-failure','delete-failure','undo-success','undo-directory-collision','undo-file-collision','undo-shortcut-collision','reload-collapse','load-duplicate','load-missing','load-unsupported','save-refused','save-unprobed','discover','rename-path']
    assert [r['id']for r in rows]==ids
    assert sha(RUN/'probe.py')==receipt['producerSha256']==sha(ROOT/'applications/prism/library_probe.py')
    assert sha(RUN/'driver.cpp')==receipt['driverSha256']
    review=read(RUN/'postimage-review.json');assert review['rawUnchanged']
    old=(RUN/'driver.cpp').read_text();expected=old.replace(review['oldSource'],review['correctedSource']);assert expected==(ROOT/'applications/prism/library_driver.cpp').read_text()
    assert sha(ROOT/'applications/prism/library_driver.cpp')==review['maintainedDriverSha256']
    assert sha(ROOT/'applications/prism/java_probe.py')==receipt['helperSha256']
    assert sha(work/'main.cpp')==receipt['generatedSha256'] and sha(work/'library-driver')==receipt['binarySha256']
    assert sha(Path('/usr/bin/clang++'))==receipt['compilerSha256'] and receipt['qtVersion']=='6.12.0'
    assert read(RUN/'collector-syntax.json')['exitCode']==0 and sha(work/'main-corrected.cpp')==read(RUN/'collector-syntax.json')['generatedSha256']
    commands=read(RUN/'commands.json');assert [c['id']for c in commands]==['compile','observe'] and all(c['exitCode']==0 and c['ownedGroupAbsent']for c in commands)
    frameworkArg=next(a for a in commands[0]['argv']if a.startswith('-Wl,-rpath,'))
    framework=Path(frameworkArg.removeprefix('-Wl,-rpath,'))/'QtCore.framework/Versions/A/QtCore'
    assert sha(framework)==receipt['frameworkSha256']
    assert not receipt['workspaceProcessHits']
    sources={}
    for item in read(ROOT/'applications/sources/prism-library-selections.json')['sources']:
        p=ROOT/item['cache'];assert sha(p)==item['sha256'];sources[item['path']]=p.read_text()
    for item in receipt['sources']:assert hashlib.sha256(sources[item['path']].encode()).hexdigest()==item['sha256']
    for item in receipt['excerpts']:assert hashlib.sha256(function(sources[item['path']],item['signature']).encode()).hexdigest()==item['sha256']
    current=function(sources['launcher/InstanceList.cpp'],'void InstanceList::setInstanceGroup(')
    candidate=current.replace('InstanceList::setInstanceGroup(', 'InstanceList::setInstanceGroupCanonical(').replace('m_instanceGroupIndex[id] = name;','m_instanceGroupIndex[inst->id()] = name;')
    assert hashlib.sha256(candidate.encode()).hexdigest()==receipt['candidateSha256']
    d={r['id']:r for r in rows};uuid='1'*32
    assert d['rename-label']['ok'] and d['rename-label']['after']['names']=={'a':'Renamed','b':'b'} and d['rename-label']['uuid']==uuid
    assert not d['rename-wrong-role']['ok'] and d['rename-wrong-role']['after']['names']=={'a':'a','b':'b'}
    assert d['duplicate-label']['after']['names']=={'a':'b','b':'b'}
    for id in['group-directory','group-uuid-existing','group-uuid-candidate']:
        assert d[id]['resolvedId']=='a' and d[id]['after']['index']=={'a':'New'} and d[id]['after']['saved']['groups']['New']['instances']==['a']
    assert d['group-uuid-first']['resolvedId']=='a' and d['group-uuid-first']['after']['index']=={uuid:'New'} and d['group-uuid-first']['after']['live']['a']=='' and d['group-uuid-first']['after']['saved']['groups']=={}
    assert d['lookup-collision']['resolvedId']=='a'
    assert d['rename-group-merge']['after']['index']=={'a':'New','b':'New'} and d['rename-group-merge']['after']['counts']=={'New':2}
    assert d['rename-group-merge']['after']['collapsed']==['New'] and d['delete-group']['after']['index']=={}
    for id in['trash-failure','delete-failure']:
        assert d[id]['bytes']=='a' and d[id]['after']['index']=={} and d[id]['after']['saved']['groups']=={} and d[id]['after']['roots']['a']
    assert d['trash-failure']['ok']is False
    for id,ok,remains in[('undo-success',True,False),('undo-directory-collision',True,False),('undo-file-collision',False,True),('undo-shortcut-collision',False,False)]:
        row=d[id];assert row['trashOk'] and row['trashed']['history']==1 and row['ok']==ok and row['after']['history']==0 and row['trashPayloadRemains']==remains and row['secondOk'] and row['second']['history']==0
    assert d['undo-directory-collision']['after']['index']=={'a1':'Old'}
    assert d['undo-shortcut-collision']['shortcutBytes']=='occupied' and d['undo-shortcut-collision']['after']['index']=={'a':'Old'}
    for name,expected in review['postimages'].items():
        for leaf,old in expected.items():
            p=work/'cases'/name/'instances'/leaf;data=p/'data'
            actual=dict(exists=p.exists(),directory=p.is_dir(),payload=data.read_text()if data.is_file()else None,occupiedBytes=p.read_text()if p.is_file()else None);assert actual==old
    assert review['postimages']['undo-directory-collision']['a1']['payload']=='a' and review['postimages']['undo-directory-collision']['a']['payload']is None
    assert (Path(d['undo-file-collision']['originalTrash'])/'data').read_text()=='a'
    assert d['reload-collapse']['after']['collapsed']==['','New']
    assert d['load-duplicate']['after']['counts']=={'New':2} and d['load-duplicate']['after']['index']=={'a':'New'} and d['load-duplicate']['resaved']['saved']['groups']['New']['instances']==['a']
    assert d['load-missing']['after']['index']=={'ghost':'New'} and d['load-missing']['resaved']['saved']['groups']=={}
    assert d['load-unsupported']['after']['index']=={'a':'Old'} and d['load-unsupported']['resaved']['saved']['formatVersion']=='1'
    for id in['save-refused','save-unprobed']:
        assert d[id]['after']['index']=={'a':'New'} and d[id]['after']['saved']['groups']['Old']['instances']==['a']
    assert d['discover']['found']==['.hidden','a','b','external']
    base=work/'cases/discover/instances';assert (base/'internal').is_symlink() and(base/'external').is_symlink()
    assert d['rename-path']['ok'] and d['rename-path']['newExists'] and not d['rename-path']['after']['roots']['a'] and Path(d['rename-path']['objectRoot']).name=='a'
    return d
