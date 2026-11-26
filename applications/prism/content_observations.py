"""Independent retained content-install observer;no native/application run."""
import hashlib,json
from pathlib import Path
from accounts_probe import function
import accounts_probe
import content_guard_probe
import content_chunk_probe

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
CURRENT=ROOT/'applications/evidence/prism-content-install-20261126T015852314941Z'
CANDIDATE=ROOT/'applications/evidence/prism-content-candidate-20261126T020852548554Z'
CHUNK=ROOT/'applications/evidence/prism-content-chunk-20261126T022625562938Z'
FAILED=ROOT/'applications/evidence/prism-content-install-20261126T015803830720Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
PAYLOAD={'OLD\n':1,'NEW\n':2,'DISABLED-OLD\n':3,content_chunk_probe.PAYLOAD:4}


def relative(path,work):
    p=Path(path);assert p.is_absolute() and '..' not in p.parts
    return str(p.relative_to(Path(work)/'cases'))


def expected_entry(path,state,work):
    key=relative(path,work);info=state.get(key)
    result=dict(exists=False,isFile=False,isDir=False,isSymLink=False)
    if not info:return result
    kind=info['kind']
    if kind=='file':
        assert info['bytes']==len(info['text'].encode()) and info['sha256']==hashlib.sha256(info['text'].encode()).hexdigest()
        return dict(exists=True,isFile=True,isDir=False,isSymLink=False,text=info['text'])
    if kind=='symlink':
        target=info['target'];target_key=relative(target,work);actual=state.get(target_key)
        assert actual is None or actual['kind']=='file'
        assert bool(actual)==info['targetExists']
        return dict(exists=bool(actual),isFile=bool(actual),isDir=False,isSymLink=True,linkTarget=target)
    assert kind=='directory';return dict(exists=True,isFile=False,isDir=True,isSymLink=False)


def payload(entry):
    if not entry['exists']:return 0
    assert entry['isFile'] and not entry['isSymLink']
    return PAYLOAD[entry['text']]


def observe(request,rows,before,after,variant):
    assert variant in ['current','candidate','chunk']
    assert request['schema']==1 and len(request['cases'])==len(rows)=={'current':8,'candidate':13,'chunk':1}[variant]
    work=request['work'];packets,observed,details=[],[],[];allowed=set()
    for case,row in zip(request['cases'],rows):
        assert row['id']==case['id'] and row['unsupportedFolderCopies']==0
        assert type(row['returned'])is bool and type(row['updateCalls'])is int
        dst=case['destination']+'/item.jar';src=case['source'];disabled=dst+'.disabled'
        dest_key=relative(dst,work);source_key=relative(src,work);allowed.add(dest_key)
        assert Path(dest_key).parts[-2:]==('installed','item.jar')
        assert Path(source_key).parts[0]==Path(dest_key).parts[0]
        assert Path(src).name=='item.jar'
        assert set(row['before'])==set(row['after'])==set(case['observe'])
        for path in case['observe']:
            assert row['before'][path]==expected_entry(path,before,work),(case['id'],'before',path)
            assert row['after'][path]==expected_entry(path,after,work),(case['id'],'after',path)
        policy='current' if variant=='current' else case['policy'];assert policy in ['current','guarded','staged']
        s=row['before'][src];d=row['before'][dst]
        if not s['exists']:source='missing';value=0
        elif src==dst:source='same-path';value=payload(d)
        elif s['isSymLink']:
            assert s['linkTarget']==dst and s['isFile'] and d['exists'];source='destination-alias';value=payload(d)
        else:
            assert s['isFile'] and not s['isDir'];source='regular';value=payload(s)
        extra=False;drop=case['operation']=='drop'
        assert case['operation'] in ['install','drop']
        if drop:
            urls=case['urls'];assert urls[0]==Path(src).as_uri() and len(urls) in [1,2]
            if len(urls)==2:
                missing=str(Path(src).parent/'missing.jar');assert urls[1]==Path(missing).as_uri() and not expected_entry(missing,before,work)['exists'];extra=True
            expected_paths=[src]+([missing]if extra else[])
        else:expected_paths=[src]
        assert [r['path']for r in row['installCalls']]==expected_paths
        assert all(type(r['returned'])is bool for r in row['installCalls'])
        watched=case['watching'];refresh=case['updateResult'];cancel=case.get('cancelBeforeCommit',False)
        assert all(type(v)is bool for v in [watched,refresh,cancel])
        disabled_before=row['before'][disabled]['exists'];assert not disabled_before or payload(row['before'][disabled])==3
        assert row['after'][disabled]==row['before'][disabled]
        packets.append(dict(policy=policy,source=source,destination=payload(d),sourcePayload=value,disabledSibling=disabled_before,
                            drop=drop,extraMissing=extra,watching=watched,refreshResult=refresh,cancelBeforeCommit=cancel))
        observed.append([row['returned'],[r['returned']for r in row['installCalls']],payload(row['after'][dst]),
                         row['after'][src]['exists'],row['after'][disabled]['exists'],row['updateCalls']])
        if source=='regular':assert before[source_key]==after[source_key]
        if source=='destination-alias':
            assert {k:v for k,v in before[source_key].items()if k!='targetExists'}=={k:v for k,v in after[source_key].items()if k!='targetExists'}
        if source=='same-path' or (policy=='guarded' and source=='destination-alias') or cancel:
            assert before.get(dest_key)==after.get(dest_key)
        details.append(dict(id=case['id'],policy=policy,sourceRelation=source,destinationRecordChanged=before.get(dest_key)!=after.get(dest_key),
                            lostPreviousPayload=bool(d['exists']and not row['after'][dst]['exists']),refreshCallbackControlled=not watched))
    # No unnamed file or staging residue may be promoted into the result.
    assert set(after)-set(before)<=allowed and set(before)-set(after)<=allowed
    for path in set(before)&set(after):
        if path not in allowed and before[path]['kind']=='file':assert before[path]==after[path]
    return packets,observed,details


def evidence(owner_local=True):
    basis={};excluded=[];all_inputs=[];all_observed=[];all_details=[]
    base_setup=load(CURRENT/'setup.json');candidate_setup=load(CANDIDATE/'setup.json')
    assert base_setup['sourceRevision']=='7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4'
    assert base_setup['qtVersion']==candidate_setup['qtVersion']=='6.12.0'
    assert base_setup['qtCoreSha256']==candidate_setup['qtCoreSha256']
    assert sha(CURRENT/'probe.py')==base_setup['producerSha256']==sha(HERE/'content_install_probe.py')
    assert sha(CURRENT/'driver.cpp')==base_setup['driverTemplateSha256']==sha(HERE/'content_install_driver.cpp')
    assert sha(CANDIDATE/'probe.py')==candidate_setup['producerSha256']==sha(HERE/'content_guard_probe.py')
    assert candidate_setup['baseGeneratedSha256']==base_setup['generatedSha256']
    assert candidate_setup['guard']==content_guard_probe.GUARD and candidate_setup['stagedBlock']==content_guard_probe.STAGED
    assert base_setup['extractorSha256']==candidate_setup['extractorSha256']==sha(Path(accounts_probe.__file__))
    for cap in [CURRENT,CANDIDATE,CHUNK]:
        for name,digest in load(cap/'collection-basis.json').items():assert sha(cap/name)==digest
        setup=load(cap/'setup.json');request=load(cap/'input.json');receipt=load(cap/'receipt.json');commands=load(cap/'commands.json')
        assert request['work']==setup['work'] and receipt['allGroupsAbsent']
        assert [c['label']for c in commands]==(['observe']if cap==CHUNK else ['compile','observe'])
        assert all(c['exitCode']==0 and c['groupAbsent']for c in commands)
        for command in commands:
            for name in ['stdout','stderr']:assert sha(cap/command[name]['path'])==command[name]['sha256']
        assert load(cap/'current-process.json')['status']=='terminal' and load(cap/'host-closure.json')['remainingExactWorkArguments']==[]
        rows=[json.loads(line)for line in(cap/'observe.stdout').read_text().splitlines()]
        before,after=load(cap/'before.json'),load(cap/'after.json')
        variant='current'if cap==CURRENT else'chunk'if cap==CHUNK else'candidate'
        packets,observed,details=observe(request,rows,before,after,variant)
        all_inputs+=packets;all_observed+=observed;all_details+=details
        original=load(cap/'collection-basis.json');files=[cap/p for p in original]+[cap/'collection-basis.json']
        if owner_local:
            work=Path(setup['work']);program=Path(setup['binary'])if cap==CHUNK else work/'probe'
            assert sha(program.parent/'main.cpp')==setup['generatedSha256']
            assert sha(program)==receipt['binarySha256']
            for name,info in after.items():
                p=work/'cases'/name;s=p.lstat();assert s.st_mode&0o777==info['mode'] and s.st_mtime_ns==info['mtimeNs']
                if info['kind']=='file':assert sha(p)==info['sha256']
                elif info['kind']=='symlink':assert p.is_symlink() and p.readlink()==Path(info['target']) and p.exists()==info['targetExists']
        else:excluded+=['private generated source/executable: '+cap.name,'private final filesystem: '+cap.name]
        for p in files:basis[str(p.relative_to(ROOT))]=sha(p)
    failed_commands=load(FAILED/'commands.json');assert len(failed_commands)==1 and failed_commands[0]['label']=='compile' and failed_commands[0]['exitCode']==1 and failed_commands[0]['groupAbsent']
    assert not(FAILED/'observe.stdout').exists()
    for p in FAILED.iterdir():
        if p.is_file():basis[str(p.relative_to(ROOT))]=sha(p)
    selections=ROOT/'applications/sources/prism-content-selections.json'
    selected={}
    for source in load(selections)['sources']:
        p=ROOT/source['cache']
        if owner_local:assert sha(p)==source['sha256'];selected[source['path']]=p.read_text()
        else:excluded.append(source['cache'])
    if owner_local:
        base_cpp=(Path(base_setup['work'])/'main.cpp').read_text()
        for entry in base_setup['excerpts']:
            body=function(selected[entry['path']],entry['signature']);assert hashlib.sha256(body.encode()).hexdigest()==entry['originalSha256']
            signature=entry['signature']
            if entry['transformation']!='none':body=body.replace('ResourceFolderModel::installResource(','ResourceFolderModel::installResourceOriginal(',1);signature=signature.replace('::installResource(','::installResourceOriginal(',1)
            actual=function(base_cpp,signature);assert actual==body and hashlib.sha256(actual.encode()).hexdigest()==entry['compiledSha256']
        cpp=(Path(candidate_setup['work'])/'main.cpp').read_text()
        for name,key in [('Guarded','guardedMethodSha256'),('Staged','stagedMethodSha256')]:assert hashlib.sha256(function(cpp,'bool ResourceFolderModel::installResource'+name+'(QString original_path)').encode()).hexdigest()==candidate_setup[key]
    else:excluded.append('private excerpt/body correspondence')
    gate=load(CANDIDATE/'proof-gate.json');assert gate['exitCode']==0 and 'Checked 2 Lean modules and 1 Bend files.'in gate['stdout']
    for p,h in gate['sourceSha256'].items():assert sha(ROOT/p)==h
    chunk_setup=load(CHUNK/'setup.json')
    assert sha(CHUNK/'probe.py')==chunk_setup['producerSha256']==sha(HERE/'content_chunk_probe.py')
    assert chunk_setup['binarySha256']==load(CANDIDATE/'receipt.json')['binarySha256'] and chunk_setup['generatedSha256']==candidate_setup['generatedSha256']
    assert chunk_setup['bytes']==len(content_chunk_probe.PAYLOAD.encode())>2*chunk_setup['chunkRequestBytes']
    for p in [selections,CANDIDATE/'proof-gate.json',HERE/'ContentInstall.lean',HERE/'ContentInstall.bend',HERE/'ContentInstallCase.lean',HERE/'content_observations.py',HERE/'content_conformance.py',HERE/'content_install_probe.py',HERE/'content_install_driver.cpp',HERE/'content_guard_probe.py',HERE/'content_chunk_probe.py',Path(accounts_probe.__file__)]:basis[str(p.relative_to(ROOT))]=sha(p)
    return dict(schema=1,profile='prism-regular-content-install',cases=all_inputs),all_observed,all_details,basis,excluded
