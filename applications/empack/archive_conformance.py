"""Compare retained source/core/native observations; no empack, Rust, or archive extraction."""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import zipfile
from archive_facts import path_facts, metadata_facts, coherent_tree, closed_metadata_admission, RECORD_FIELDS

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
RUN=ROOT/'applications/evidence/empack-archives-20261125T135102774049Z'
NATIVE=ROOT/'applications/evidence/empack-archive-import-20261125T135422292082Z'
ENCODING=ROOT/'applications/evidence/empack-archive-encoding-20261125T142823826296Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())


def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')


def checked_bytes(path,digest):
    data=path.read_bytes()
    assert hashlib.sha256(data).hexdigest()==digest, 'Archive input digest mismatch: '+str(path)
    return data


def observed_stage(row):
    if row['accepted']:
        assert row['error']==''
        return 0
    messages=[('Missing ZIP end record',1),('Multi-disk ZIP',2),('Invalid ZIP64',3),
        ('Archive exceeds entry limit',4),('ZIP metadata exceeds',5),('ZIP directory overflow',6),
        ('ZIP directory extends',7),('fixture cancellation check refused',8),
        ('Invalid ZIP central directory member',9),('failed to fill whole buffer',10),
        ('ZIP member declares UTF-8',11),('Duplicate ZIP central directory',12),
        ('ZIP directory count differs',13),('ZIP member exceeds directory bounds',14)]
    matches=[code for text,code in messages if row['error'].startswith(text)]
    assert len(matches)==1,('Unknown or ambiguous corpus diagnostic',row)
    # EOF is associated with a directory header only in this selected corpus.
    if matches[0]==10:assert row['id']=='directory-count-too-large'
    return matches[0]


def observed_paths(text):
    rows=[]
    for line in text.splitlines():
        identity,opaque,portable,opaque_error,portable_error=line.split('\t')
        assert opaque in ['true','false']and portable in ['true','false']
        assert(opaque=='true')==(opaque_error=='')and(portable=='true')==(portable_error=='')
        rows.append(dict(id=identity,opaqueAllowed=opaque=='true',portableAllowed=portable=='true'))
    return rows


def observed_metadata(rows):
    return [dict(id=r['id'],code=observed_stage(r),checks=r['checks'])for r in rows]


def compare(actual,expected):
    assert actual==expected,'Archive observation differs from model output.'


def native_checks(receipt):
    assert receipt['complete']and receipt['allGroupsAbsent']and len(receipt['cases'])==10
    assert receipt['continuation']['fromCaseCount']==3
    assert receipt['cases'][2]['expectedExit']==1 and receipt['cases'][2]['exitCode']==2
    sentinel=hashlib.sha256(b'owned external sentinel\n').hexdigest()
    expected={ 'valid-config':(0,''),'opaque-jar':(0,''),
        'unused-traversal':(2,'file path contains an empty or traversal component'),
        'unused-reserved':(2,'file path contains a reserved device name'),
        'unused-case-aliases':(1,'File destination collides'),
        'unused-unicode-aliases':(1,'File destination collides'),
        'unused-file-ancestor':(1,'File destination collides'),
        'unused-duplicate':(1,'Duplicate ZIP central directory member'),
        'unused-symlink':(1,'Encrypted or linked source member'),
        'corrupt-override':(1,'Invalid checksum') }
    assert set(expected)=={r['id']for r in receipt['cases']}
    for row in receipt['cases']:
        code,cause=expected[row['id']]
        assert row['exitCode']==code and row['authorPublished']==(code==0)
        assert row['sentinelSha256']==sentinel and row['groupAbsent']and not row['timedOut']
        if code:
            assert not row['destinationSnapshot'] and row['beforeParent']==row['afterParent']
            assert cause in (NATIVE/(row['id']+'.stderr')).read_text()
        else:
            assert 'empack.yml'in row['destinationSnapshot']
    return expected


def encoding_checks(receipt):
    assert receipt['complete']and len(receipt['cases'])==2
    assert sha(ENCODING/'probe.py')==receipt['producerSha256']
    assert sha(ENCODING/'helpers.py')==receipt['helperSha256']
    single,mixed=receipt['cases']
    assert single['id']=='single-cp437'and single['exitCode']==0 and single['authorPublished']
    assert mixed['id']=='mixed-decoded-duplicate'and mixed['exitCode']==1 and not mixed['authorPublished']
    assert mixed['beforeParent']==mixed['afterParent']and not mixed['destinationSnapshot']
    assert'File destination collides'in(ENCODING/'mixed-decoded-duplicate.stderr').read_text()
    for row in receipt['cases']:
        assert row['groupAbsent']and not row['timedOut']
        for stream in ['stdout','stderr']:
            assert sha(ENCODING/(row['id']+'.'+stream))==row[stream+'Sha256']


def main():
    receipt=load(RUN/'receipt.json');native=load(NATIVE/'receipt.json')
    assert receipt['revision']=='0b4462e3032b4f09230b15329722eabefb7f574c'
    assert receipt['coreUnchanged']and receipt['paths']==34 and receipt['preflightCases']==26
    for folder,r in [(RUN,receipt),(NATIVE,native)]:
        assert sha(folder/'probe.py')==r['producerSha256']
    assert sha(NATIVE/'continue-probe.py')==native['continuation']['producerSha256']
    for key,name in [('driverSha256','driver.rs'),('fragmentSha256','fragments.rs'),('observedSha256','observed.json')]:
        assert sha(RUN/name)==receipt[key]
    for command in receipt['commands']:
        assert command['exitCode']==0
        for stream in ['stdout','stderr']:
            assert sha(RUN/(command['label']+'.'+stream))==command[stream+'Sha256']
    for row in native['cases']:
        for stream in ['stdout','stderr']:
            assert sha(NATIVE/(row['id']+'.'+stream))==row[stream+'Sha256']
    prior=ROOT/receipt['core']['receipt'];assert sha(prior)==receipt['core']['receiptSha256']
    core=load(prior);assert core['librarySha256']==receipt['core']['librarySha256']
    library=Path(receipt['core']['library'])
    if library.exists():assert sha(library)==receipt['core']['librarySha256']
    repo=ROOT.parent/'empack'
    def pinned_bytes(path,revision=receipt['revision']):
        return subprocess.check_output(['git','show',revision+':'+path],cwd=repo)
    raw_source=pinned_bytes(receipt['source']['path']);assert hashlib.sha256(raw_source).hexdigest()==receipt['source']['sha256']
    text=raw_source.decode()
    fragment=(RUN/'fragments.rs').read_text()
    for item in receipt['fragments']:
        body=text[item['start']:item['end']]
        assert hashlib.sha256(body.encode()).hexdigest()==item['sha256']and body in fragment
    for name,digest in core['sourceTree'].items():assert hashlib.sha256(pinned_bytes(name,core['sourceRevision'])).hexdigest()==digest
    paths=load(RUN/'paths.json');path_rows=observed_paths((RUN/'paths.stdout').read_text())
    assert [p['id']for p in paths]==[p['id']for p in path_rows]and len(paths)==34
    path_inputs=[dict(id=p['id'],**path_facts(p['value']))for p in paths]
    original=load(RUN/'observed.json');cases=load(RUN/'cases.json');assert len(original)==len(cases)==26
    metadata_inputs=[];metadata_rows=observed_metadata(original)
    for row,actual in zip(cases,original,strict=True):
        assert row['id']==actual['id']
        data=checked_bytes(ROOT/row['input'],row['sha256']);assert len(data)==row['bytes']<=65536
        metadata_inputs.append(metadata_facts(data,row['entryLimit'],row['cancelAfter'],row['id']))
        raw=(RUN/(row['id']+'.stdout')).read_text().rstrip('\n').split('\t',5)
        assert raw==[str(actual['accepted']).lower(),str(actual['checks']),str(actual['readBytes']),str(actual['largestBuffer']),str(actual['seeks']),actual['error']]
        assert actual['largestBuffer']<=65557
    native_checks(native);encoding=load(ENCODING/'receipt.json');encoding_checks(encoding)
    import_inputs=[];import_rows=[];import_details=[]
    imports=[(NATIVE,row,'Rules archive fixture')for row in native['cases']]
    imports += [(ENCODING,row,'Rules encoding fixture')for row in encoding['cases']]
    for folder,row,title in imports:
        path=(folder/'inputs'if folder==NATIVE else folder)/(row['id']+'.mrpack')
        data=checked_bytes(path,row.get('archiveSha256',row.get('inputSha256')))
        m=metadata_facts(data,20,-1,row['id'])
        # This closed ZIP32 corpus has no raw preflight rejection except exact
        # duplicates. Require all known declaration predicates, independently
        # read from bytes; this is not a general binary parser proof.
        metadata=closed_metadata_admission(m)
        with zipfile.ZipFile(path)as z:
            infos=z.infolist();assert len(infos)<=20
            assert all(e.compress_type==zipfile.ZIP_STORED and not(e.flag_bits&1)for e in infos),'Outside the stored/unencrypted local import profile'
            assert json.loads(z.read('modrinth.index.json'))==dict(formatVersion=1,game='minecraft',versionId='same-label',name=title,files=[],dependencies={'minecraft':'1.21.1'})
            names=[e.filename[:-1]if e.is_dir()else e.filename for e in infos]
            name_facts=[path_facts(name)for name in names]
            portable=all(not(f['commonUnsafe']or f['drivePrefix']or f['portableOnlyUnsafe'])for f in name_facts)
            tree=coherent_tree(infos)
            regular=all(stat.S_IFMT(e.external_attr>>16)in([0,stat.S_IFDIR]if e.is_dir()else[0,stat.S_IFREG])for e in infos)
            payload=True
            try:
                for e in infos:
                    if e.filename=='modrinth.index.json'or e.filename.startswith(('overrides/','client-overrides/','server-overrides/')):
                        z.read(e)
            except zipfile.BadZipFile:payload=False
            if row['id']=='valid-config':
                assert row['destinationSnapshot']['overrides/common/config/rules.txt']['sha256']==hashlib.sha256(z.read('overrides/config/rules.txt')).hexdigest()
            if row['id']=='opaque-jar':
                assert row['destinationSnapshot']['overrides/common/mods/fixture.jar']['sha256']==hashlib.sha256(z.read('overrides/mods/fixture.jar')).hexdigest()
            if folder==ENCODING:
                independently=[dict(name=e.filename,flags=e.flag_bits,crc=e.CRC,bodySha256=hashlib.sha256(z.read(e)).hexdigest())for e in infos]
                assert independently==row['independentNames']
                assert names[1]=='overrides/config/café.txt'and infos[1].flag_bits==0
                if row['id']=='single-cp437':
                    assert row['destinationSnapshot']['overrides/common/config/café.txt']['sha256']==hashlib.sha256(b'CP437 body\n').hexdigest()
                else:
                    assert names[1]==names[2]and infos[2].flag_bits&(1<<11)
                    assert m['records'][1]['rawUnique']and m['records'][2]['rawUnique']
        item=dict(id=row['id'],metadata=metadata,paths=portable,tree=tree,regular=regular,payload=payload)
        import_inputs.append(item);import_rows.append(dict(id=row['id'],published=row['authorPublished']))
        import_details.append(dict(id=row['id'],rawMetadata=m,outerNames=names,pathFacts=name_facts,
            normalization='PythonNFD/casefold on selected corpus; not full Rust Unicode-table equivalence.',
            fixedProfile='valid manifest,no remote selections,new destination,explicit --yes; not full importer/solver'))
    inputs=dict(schema=1,paths=path_inputs,metadata=metadata_inputs,imports=import_inputs)
    expected=dict(paths=path_rows,metadata=metadata_rows,imports=import_rows)
    write(RUN/'model-input.json',inputs);write(RUN/'import-facts.json',import_details)
    generated=ROOT/'.build/empack-archives-formal';generated.mkdir(exist_ok=True)
    env=dict(os.environ,LEAN_PATH=str(generated),BEND_NO_TELEMETRY='1');lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    command=[lean,'--run','applications/empack/ArchivesCase.lean',str(RUN/'model-input.json')]
    result=subprocess.run(command,env=env,cwd=ROOT,check=True,capture_output=True,text=True)
    actual=json.loads(result.stdout);compare(actual,expected)
    def bo(value):return 'True{}'if value else'False{}'
    def opt_bool(value):return 'None{}'if value is None else'Some{'+bo(value)+'}'
    def opt_nat(value):return 'None{}'if value is None else'Some{'+str(value)+'n}'
    def record_bend(r):return 'A.Record{'+','.join(opt_bool(r[k])for k in RECORD_FIELDS)+'}'
    pieces=[];wanted=[]
    for p,out in zip(path_inputs,path_rows,strict=True):
        args=[p[k]for k in ['commonUnsafe','drivePrefix','portableOnlyUnsafe']]
        for fn,n,key in [('opaque_name',2,'opaqueAllowed'),('portable_name',3,'portableAllowed')]:
            pieces.append('Bool.show(A.'+fn+'('+','.join(map(bo,args[:n]))+')) ++ "\\n"');wanted.append(str(out[key]))
    for m,out in zip(metadata_inputs,metadata_rows,strict=True):
        args=[opt_bool(m[k])for k in ['endValid','singleDisk','zip64Shape']]
        args += [opt_nat(m['entries']),str(m['entryLimit'])+'n',opt_nat(m['metadataBytes'])]
        args += [opt_bool(m[k])for k in ['noDirectoryOverflow','directoryWithin']]
        args += ['['+','.join(map(record_bend,m['records']))+']',opt_nat(m['cancelAfter']),opt_bool(m['finalCount'])]
        pieces.append('A.show_outcome(A.metadata_decision('+','.join(args)+')) ++ "\\n"');wanted.append(str(out['code'])+':'+str(out['checks']))
    for i,out in zip(import_inputs,import_rows,strict=True):
        pieces.append('Bool.show(A.published('+','.join(bo(i[k])for k in ['metadata','paths','tree','regular','payload'])+')) ++ "\\n"');wanted.append(str(out['published']))
    case=generated/'ArchivesCase.bend';case.write_text('import Base\nimport ../../applications/empack/Archives.bend as A\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(pieces)+')\n')
    result=subprocess.run([bend,str(case)],env=env,check=True,capture_output=True,text=True);assert result.stdout=='\n'.join(wanted)+'\n'
    empty=dict(schema=1,paths=[],metadata=[],imports=[])
    unknown=copy.deepcopy(metadata_inputs[1]);unknown['records'][0]['headerReadable']=None
    wrong_count=copy.deepcopy(metadata_inputs[1]);wrong_count['records']=[]
    invalid=[(dict(empty,schema=2),'Unsupported archive'),
             (dict(empty,metadata=[unknown]),'Needed archive fact is unknown'),
             (dict(empty,metadata=[wrong_count]),'record witness count differs')]
    for bad,cause in invalid:
        write(generated/'invalid.json',bad)
        result=subprocess.run(command[:-1]+[str(generated/'invalid.json')],env=env,cwd=ROOT,capture_output=True,text=True)
        assert result.returncode==2 and cause in result.stderr
    changes=0
    raw=(RUN/'paths.stdout').read_text().splitlines()
    for index,replacement in [(14,'path-14\tfalse\tfalse\tReservedName\tReservedName'),
                               (13,'path-13\ttrue\ttrue\t\t')]:
        changed_lines=list(raw);changed_lines[index]=replacement
        changed=copy.deepcopy(expected);changed['paths']=observed_paths('\n'.join(changed_lines))
        try:compare(actual,changed)
        except AssertionError as e:assert'Archive observation differs'in str(e);changes+=1
        else:raise AssertionError('Changed path API observation escaped')
    for identity,patch in [('cancel-first',dict(checks=0)),('invalid-declared-utf8',dict(accepted=True,error=''))]:
        changed_rows=copy.deepcopy(original);next(r for r in changed_rows if r['id']==identity).update(patch)
        changed=copy.deepcopy(expected);changed['metadata']=observed_metadata(changed_rows)
        try:compare(actual,changed)
        except AssertionError as e:assert'Archive observation differs'in str(e);changes+=1
        else:raise AssertionError('Changed preflight observation escaped')
    bad=copy.deepcopy(native);bad['cases'][2]['exitCode']=1
    try:native_checks(bad)
    except AssertionError:changes+=1
    else:raise AssertionError('Typed refusal-code change escaped')
    bad=copy.deepcopy(native);bad['cases'][-1]['authorPublished']=True
    try:native_checks(bad)
    except AssertionError:changes+=1
    else:raise AssertionError('Unexpected author publication escaped')
    unknown_fact=copy.deepcopy(import_details[0]['rawMetadata']);unknown_fact['records'][0]['headerReadable']=None
    try:closed_metadata_admission(unknown_fact)
    except AssertionError as e:assert'Needed archive fact is unknown'in str(e)
    else:raise AssertionError('Unknown metadata was classified as an invalid archive')
    probe=RUN/'inputs/one.zip';before=probe.read_bytes();mismatch=hashlib.sha256(before+b'changed').hexdigest()
    try:checked_bytes(probe,mismatch)
    except AssertionError as e:assert'input digest mismatch'in str(e)
    else:raise AssertionError('Input digest change escaped')
    basis_files=[p for p in RUN.rglob('*')if p.is_file()and p.name not in ['basis.json','conformance.json']]
    basis_files += [p for p in NATIVE.rglob('*')if p.is_file()]
    basis_files += [p for p in ENCODING.rglob('*')if p.is_file()]
    ledger=ROOT/'applications/sources/empack-archives-selections.json'
    selected=load(ledger)
    for item in selected['sources']:
        raw=pinned_bytes(item['path'],item['commit'])
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
    basis_files += [ledger]+[HERE/p for p in ['archive_driver.rs','archive_probe.py','archive_import_probe.py','archive_encoding_probe.py','archive_facts.py',Path(__file__).name,'Archives.lean','ArchivesCase.lean','Archives.bend']]
    write(RUN/'basis.json',{str(p.relative_to(ROOT)):sha(p)for p in basis_files})
    report=dict(schema=1,corePathApiRows=34,rawSourcePreflightRows=26,nativeImports=12,acceptedImports=3,refusedImports=9,encodingSupplementRows=2,
        scalarComparisons=132,leanLaws=12,bendLaws=6,observedMetadataStageTags=sorted({r['code']for r in metadata_rows}),sourceOnlyStageTags=[3,14],
        schemaUnknownAndWitnessRefusals=3,changedOutcomeControls=changes,inputDigestRefusal=True,observerUnknownRefusal=True,
        originalExpectationFailureRetained=True,basisFiles=len(basis_files),
        limits=['Unchanged preflight body with explicitly new error/context and cancellation adapters;not native Cancellation or the ZIP payload decoder.',
                'Boolean namespace projection,not a proof of arbitrary Unicode classifiers or all binary parser inputs.',
                'EOF-to-stage mapping is corpus-specific;it is not a stable public diagnostic API.',
                'Closed local mrpack composition;not full import solving or publisher authentication.',
                'Opaque JAR retention during import does not qualify inspect_opaque or a game/modloader.',
                'No TAR/7z,full memory ceiling,failed-read allowance,private extraction witness,crash,or cross-platform qualification.',
                'Current source and installed0.8.8 binary remain distinct evidence without reproducible-build proof.'])
    write(RUN/'conformance.json',report);print(json.dumps(report,indent=2))


if __name__=='__main__':main()
