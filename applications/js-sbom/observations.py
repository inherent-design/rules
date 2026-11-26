"""Independent retained-byte reader;no package manager,Node or private-root access."""
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'applications/evidence/js-sbom-20261126T065646155804Z'
PROD,DEV,OPTIONAL='rules-sbom-prod','rules-sbom-dev','rules-sbom-optional'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def body(image,path):
    e=image[path];assert e['kind']=='file';p=(RUN/e['captured']).resolve()
    assert p.is_relative_to((RUN/'states').resolve())
    value=p.read_bytes();assert len(value)==e['bytes']and hashlib.sha256(value).hexdigest()==e['sha256']
    return value


def normalized(document):
    document=json.loads(json.dumps(document))
    if document.get('bomFormat')=='CycloneDX':
        document.pop('serialNumber');document['metadata'].pop('timestamp')
    else:document.pop('documentNamespace');document['creationInfo'].pop('created')
    return document


def inspect():
    receipt=read(RUN/'receipt.json');commands=read(RUN/'commands.json');mutations=read(RUN/'mutations.json')
    assert receipt['complete']and receipt['commands']==len(commands)==26 and receipt['allRecordedGroupsAbsent']
    assert sha(RUN/'probe.py')==receipt['producerSha256']
    packages={}
    for item in read(RUN/'archives.json'):
        raw=(RUN/'archives'/item['filename']).read_bytes()
        assert len(raw)==item['bytes']and hashlib.sha256(raw).hexdigest()==item['sha256']and hashlib.sha512(raw).hexdigest()==item['sha512']
        with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz')as archive:
            assert archive.getnames()==['package/package.json','package/index.js']
            for member in archive.getmembers():
                assert member.isfile()and not member.issym()and not member.islnk()
                content=archive.extractfile(member).read();entry=item['files'][member.name.removeprefix('package/')]
                assert len(content)==entry['bytes']and hashlib.sha256(content).hexdigest()==entry['sha256']
                if member.name=='package/package.json':
                    m=json.loads(content);assert m['name']==item['name']and m['version']=='1.0.0'and m['license']=='MIT'and'scripts'not in m
        packages[item['name']]=item
    assert set(packages)=={PROD,DEV,OPTIONAL}
    previous,used,outputs,runtime,exits={},set(),[],[],[]
    for c in commands:
        manager=c['manager'];assert manager in ['npm','pnpm']and c['groupAbsent']and not c['timedOut']
        for stream in ['stdout','stderr']:assert sha(RUN/(c['id']+'.'+stream))==c[stream+'Sha256']
        for image in [c['before'],c['after']]:
            for path,entry in image.items():
                if entry['kind']=='file':body(image,path)
        if manager in previous and c['before']!=previous[manager]:
            state=previous[manager]
            while state!=c['before']:
                pending=[i for i,m in enumerate(mutations)if m['manager']==manager and i not in used]
                assert pending and mutations[pending[0]]['before']==state,'Unexplained ordered author mutation.'
                used.add(pending[0]);state=mutations[pending[0]]['after']
        previous[manager]=c['after']
        before=body(c['before'],'package.json');assert before==body(c['after'],'package.json')
        manifest=json.loads(before);assert manifest['name']=='rules-sbom-'+manager
        assert manifest['dependencies']=={PROD:'file:archives/'+PROD+'-1.0.0.tgz'}
        assert manifest['devDependencies']=={DEV:'file:archives/'+DEV+'-1.0.0.tgz'}
        assert manifest['optionalDependencies']=={OPTIONAL:'file:archives/'+OPTIONAL+'-1.0.0.tgz'}
        if c['id'].endswith('-install'):
            assert c['exitCode']==0;continue
        assert c['before']==c['after'],'Read/report command changed captured project entries.'
        if c['query']:
            assert c['exitCode']==0;value=read(RUN/(c['id']+'.stdout'));assert set(value)==set(packages)
            project=Path(receipt['work'])/manager/'project'
            for name,observed in value.items():
                if 'error'in observed:
                    assert name==PROD and c['id'].endswith('missing-runtime')and observed==dict(error='MODULE_NOT_FOUND')
                    continue
                file=Path(observed['file']);assert file.is_relative_to(project)and'..'not in file.parts
                path=file.relative_to(project).as_posix();code=body(c['after'],path)
                assert observed['sha256']==hashlib.sha256(code).hexdigest()
                assert code.startswith(b'module.exports=')and code.endswith(b';\n')
                assert observed['value']==json.loads(code[len('module.exports='):-2])
                pm=json.loads(body(c['after'],str(Path(path).parent/'package.json')))
                assert pm['name']==name and pm['version']=='1.0.0'
                if name!=PROD or c['id'].endswith('baseline-runtime'):assert observed['sha256']==packages[name]['files']['index.js']['sha256']
            runtime.append(dict(id=c['id'],manager=manager,observed=value));continue
        exits.append(dict(id=c['id'],manager=manager,argv=c['argv'][1:],exitCode=c['exitCode']))
        if c['exitCode']:
            assert not(RUN/(c['id']+'.stdout')).read_bytes(),'Failure unexpectedly emitted a partial document.'
            continue
        doc=read(RUN/(c['id']+'.stdout'))
        if doc.get('bomFormat')=='CycloneDX':
            assert doc['specVersion']==('1.5'if manager=='npm'else'1.7')
            root=doc['metadata']['component'];components=doc['components'];kind='cyclonedx'
            assert root['purl']=='pkg:npm/'+manifest['name']+'@1.0.0'
            assert root['name']==('project'if manager=='npm'else manifest['name'])
            assert doc['metadata']['lifecycles']==[dict(phase='pre-build'if'lock-only'in c['id']else'build')]
        else:
            assert doc['spdxVersion']=='SPDX-2.3';kind='spdx';root=next(v for v in doc['packages']if v['name']==manifest['name']);components=[v for v in doc['packages']if v is not root]
            assert all(v['filesAnalyzed']is False for v in doc['packages'])
        names={v['name']for v in components};assert names==({PROD}if c['id'].endswith('runtime-filter')else set(packages))
        if kind=='cyclonedx':
            ids=[v['bom-ref']for v in [root,*components]];assert len(ids)==len(set(ids))
            edges=doc['dependencies'];assert len(edges)==len(ids)and {e['ref']for e in edges}==set(ids)
            for edge in edges:
                assert len(edge['dependsOn'])==len(set(edge['dependsOn']))and set(edge['dependsOn'])<=set(ids)
                assert set(edge['dependsOn'])==({v['bom-ref']for v in components}if edge['ref']==root['bom-ref']else set())
        else:
            ids=[v['SPDXID']for v in [root,*components]];assert len(ids)==len(set(ids))
            edges=doc['relationships'];assert len(edges)==len(ids)
            assert edges.count(dict(spdxElementId='SPDXRef-DOCUMENT',relatedSpdxElement=root['SPDXID'],relationshipType='DESCRIBES'))==1
            for component in components:
                pairs=(component['SPDXID'],root['SPDXID'])if manager=='npm'else(root['SPDXID'],component['SPDXID'])
                assert len([e for e in edges if(e['spdxElementId'],e['relatedSpdxElement'])==pairs])==1
        for component in components:
            name=component['name'];assert component.get('version',component.get('versionInfo'))=='1.0.0'
            if kind=='cyclonedx':
                hashes=component.get('hashes',[])if manager=='npm'else next(v['hashes']for v in component['externalReferences']if v['type']=='distribution')
                assert hashes==[dict(alg='SHA-512',content=packages[name]['sha512'])]
            else:assert component['checksums']==[dict(algorithm='SHA512',checksumValue=packages[name]['sha512'])]
        outputs.append(dict(id=c['id'],manager=manager,format=kind,rootName=root['name'],declaredName=manifest['name'],names=sorted(names),normalized=normalized(doc)))
    assert len(used)==len(mutations)==8
    assert len(runtime)==6 and len(exits)==18 and len(outputs)==11
    for manager in ['npm','pnpm']:
        before=next(x for x in outputs if x['id']==manager+'-baseline-cyclonedx')
        changed=next(x for x in outputs if x['id']==manager+'-changed-cyclonedx')
        assert before['normalized']==changed['normalized'],'More than UUID/time changed after code mutation.'
        a=next(x for x in runtime if x['id']==manager+'-baseline-runtime')['observed'][PROD]
        b=next(x for x in runtime if x['id']==manager+'-changed-runtime')['observed'][PROD]
        assert a['sha256']!=b['sha256']and a['value']['value']=='original'and b['value']['value']=='changed'
    return dict(schema=1,nativeCommands=26,installations=2,runtimeQueries=6,sbomRequests=18,sbomDocuments=11,authoredMutations=8,
                exits=exits,outputs=outputs,runtime=runtime,basisSha256={str(p.relative_to(ROOT)):sha(p)for p in sorted(RUN.rglob('*'))if p.is_file()},
                limitation='Retained-byte projection only;no Lean/Bend comparison,complete SBOM schema/graph validation,archive-to-installed integrity guarantee or production correction yet.')


if __name__=='__main__':
    result=inspect();out=ROOT/'.build/js-sbom-review';out.mkdir(exist_ok=True)
    (out/'native-observations.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['nativeCommands','installations','runtimeQueries','sbomRequests','sbomDocuments','authoredMutations']}))
