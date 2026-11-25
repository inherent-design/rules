#!/usr/bin/env python3
"""Read native update fixtures and their actual bytes; no application run."""
import base64,hashlib,io,json,tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MAIN=ROOT/'applications/evidence/js-updates-20261125T045212755778Z'
YARN=ROOT/'applications/evidence/js-updates-20261125T045315086524Z'
NAMES=['rules-update-range','rules-update-pin']
VERSIONS=['1.0.0','1.1.0','2.0.0','2.1.0-beta.1']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def inspect():
    all_rows=[];tools=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']
    for k in['node','npm','pnpm','yarn']:assert sha(Path(tools[k]['path']))==tools[k]['sha256']
    sources=json.loads((ROOT/'applications/sources/js-updates-selections.json').read_text())['sources']
    tree={r['path']:r['sha']for r in json.loads((ROOT/'applications/tools/source-cache/pnpm-tree.json').read_text())['tree']if r['type']=='blob'}
    for source in sources:
        p=ROOT/source['cache'];b=p.read_bytes();assert sha(p)==source['sha256']
        if source['application']=='pnpm':assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==source['gitBlobSha1']==tree[source['path']]
        if source.get('matchesInstalledFile'):assert Path(source['installedSource']).read_bytes()==b
    for run in[MAIN,YARN]:
        rows=json.loads((run/'commands.json').read_text());all_rows +=[(run,r)for r in rows]
        assert len({(r['app'],r['case'])for r in rows})==len(rows)
        assert json.loads((run/'closed.json').read_text())==dict(serverClosed=True,threadJoined=True,allOwnedProcessesRetired=True)
        assert all(p['retired']for p in json.loads((run/'owned-processes.json').read_text()))
        if run==YARN:
            receipt=json.loads((run/'receipt.json').read_text());assert sha(run/'probe.py')==receipt['producerSha256']and receipt['commands']==8
            assert receipt['tools']=={k:tools[k]for k in['node','npm','pnpm','yarn']}
        else:
            stop=json.loads((run/'collector-stop.json').read_text());assert stop['frozenProducerSha256']==sha(run/'probe.py')and stop['mainCommands']==33
        archives={}
        for p in(run/'archives').iterdir():
            with tarfile.open(fileobj=io.BytesIO(p.read_bytes()),mode='r:gz')as archive:
                assert sorted(archive.getnames())==['package/index.js','package/package.json']
                manifest=json.loads(archive.extractfile('package/package.json').read());code=archive.extractfile('package/index.js').read()
                assert manifest['name']in NAMES and manifest['version']in VERSIONS
                assert code==('module.exports='+json.dumps(manifest['version'])+';\n').encode()
                assert 'scripts'not in manifest and 'dependencies'not in manifest
                archives[manifest['name'],manifest['version']]=p
        assert len(archives)==8
        for p in(run/'states').iterdir():assert p.stem==sha(p)
        for p in(run/'responses').iterdir():assert p.stem==sha(p)
        events=json.loads((run/'requests.json').read_text())
        for event in events:
            assert event['method']=='GET'and not event['authorizationPresent']
            body=(run/event['response']).read_bytes();assert hashlib.sha256(body).hexdigest()==event['bodySha256']
            if event['status']==404:assert json.loads(body)==dict(error='generated_fixture_not_found')
            elif event['path'].endswith('.tgz'):
                name,_,filename=event['path'].lstrip('/').split('/');assert event['status']==200
                p=run/'archives'/filename;assert body==p.read_bytes()
            else:
                meta=json.loads(body);assert event['status']==200 and event['path']=='/'+meta['name']
                initial=event['stage']=='initial';versions=VERSIONS[:1]if initial else VERSIONS
                assert list(meta['versions'])==versions
                tag='1.0.0'if initial else'1.1.0'if event['stage']=='retagged'else'2.0.0'
                assert meta['dist-tags']['latest']==tag and (initial or meta['dist-tags']['next']=='2.1.0-beta.1')
                for version,v in meta['versions'].items():
                    p=archives[meta['name'],version];payload=p.read_bytes()
                    assert v['name']==meta['name']and v['version']==version
                    assert v['dist']['integrity']=='sha512-'+base64.b64encode(hashlib.sha512(payload).digest()).decode()
                    assert v['dist']['shasum']==hashlib.sha1(payload).hexdigest()
        previous={}
        for r in rows:
            assert not r['outcome']['timedOut']and r['outcome']['ownedGroupAbsent']
            for stream,value in r['streams'].items():assert sha(run/value['file'])==value['sha256']
            for state in[r['before'],r['after']]:
                for value in state['authored'].values():
                    p=run/value['captured'];assert sha(p)==value['sha256']and p.stat().st_size==value['bytes']
            if r['app']in previous:assert r['before']==previous[r['app']]['after']
            previous[r['app']]=r
            assert all(e in events and e['case']==r['app']+'-'+r['case']for e in r['requests'])
            if r['kind']=='fresh-node-observer':
                assert r['outcome']['exitCode']==0 and not r['requests']and r['before']==r['after']
                actual=json.loads((run/r['streams']['stdout']['file']).read_text());assert set(actual)==set(NAMES+['rules-update-local'])
                for name,value in actual.items():
                    assert 'error'not in value and value['manifest']['name']==name
                    if name=='rules-update-local':
                        assert value['value']=='local-unchanged'
                        assert value['manifest']==dict(name=name,version='1.0.0',main='index.js')
                        assert value['source']=='module.exports="local-unchanged";\n'
                    else:
                        version=value['value'];assert value['manifest']['version']==version
                        with tarfile.open(archives[name,version],mode='r:gz')as tar:
                            assert value['source'].encode()==tar.extractfile('package/index.js').read()
                            assert value['manifest']==json.loads(tar.extractfile('package/package.json').read())
            elif r['case'].startswith('catalog-'):
                assert r['before']==r['after'],'Catalog query changed selected project state'
        # Final on-disk selected author inputs are compared with the recorded
        # final image; this is not a whole-volume or process-wide IO assertion.
        for app,last in previous.items():
            for name,value in last['after']['authored'].items():assert sha(run/'work'/app/'project'/name)==value['sha256']
    def row(app,case):
        run=YARN if app=='yarn'else MAIN
        return run,next(r for path,r in all_rows if path==run and r['app']==app and r['case']==case)
    def runtime(app,case):
        run,r=row(app,case);value=json.loads((run/r['streams']['stdout']['file']).read_text());return[value[n]['value']for n in NAMES]
    for app in['npm','pnpm','yarn']:
        assert runtime(app,'initial-runtime')==['1.0.0','1.0.0']
        assert runtime(app,'within-runtime')==['1.1.0','1.0.0']
        assert runtime(app,'latest-runtime')==['2.0.0','2.0.0']
        assert runtime(app,'retagged-runtime')==(['2.0.0','2.0.0']if app=='pnpm'else['1.1.0','1.1.0'])
        run,r=row(app,'within-range');before=json.loads((run/r['before']['authored']['package.json']['captured']).read_text())
        after=json.loads((run/r['after']['authored']['package.json']['captured']).read_text())
        assert before['dependencies'][NAMES[1]]==after['dependencies'][NAMES[1]]=='1.0.0'
        assert before['dependencies'][NAMES[0]]=='^1.0.0'
        assert after['dependencies'][NAMES[0]]==('^1.1.0'if app=='pnpm'else'^1.0.0')
        if app!='pnpm':assert r['before']['authored']['package.json']==r['after']['authored']['package.json']
        run,r=row(app,'rewrite-latest');manifest=json.loads((run/r['after']['authored']['package.json']['captured']).read_text())
        assert manifest['dependencies'][NAMES[0]]=='^2.0.0'
        assert manifest['dependencies'][NAMES[1]]==('2.0.0'if app=='pnpm'else'^2.0.0')
    for app in['npm','pnpm']:
        # Check the full emitted row, not only the three fields modeled below.
        # The original temp root is independently recorded in pnpm's authored
        # store setting; do not derive expected locations from query output.
        source_row=next(r for path,r in all_rows if path==MAIN and r['app']=='pnpm'and r['case']=='initial-install')
        config=(MAIN/source_row['before']['authored']['pnpm-workspace.yaml']['captured']).read_text()
        store_line=next(line for line in config.splitlines()if line.startswith('storeDir: '))[10:]
        assert store_line.endswith('/pnpm/cache/store');original_root=store_line[:-len('/pnpm/cache/store')]
        for run,r in all_rows:
            if r['app']!=app or not r['case'].startswith('catalog-'):continue
            for name,value in json.loads((run/r['streams']['stdout']['file']).read_text()).items():
                assert name in NAMES
                if app=='npm':
                    assert set(value)=={'current','wanted','latest','dependent','location'}
                    assert value['dependent']=='project'and value['location']==original_root+'/npm/project/node_modules/'+name
                else:
                    assert set(value)=={'current','wanted','latest','isDeprecated','dependencyType'}
                    assert value['isDeprecated']is False and value['dependencyType']=='dependencies'
        run,r=row(app,'catalog-advanced');value=json.loads((run/r['streams']['stdout']['file']).read_text())
        assert set(value)==set(NAMES)and value[NAMES[1]]['current']==value[NAMES[1]]['wanted']=='1.0.0'
        assert value[NAMES[0]]['current']=='1.0.0'and value[NAMES[0]]['wanted']==('1.1.0'if app=='npm'else'1.0.0')
        assert all(v['latest']=='2.0.0'for v in value.values())and r['outcome']['exitCode']==1
        run,r=row(app,'catalog-pin-unavailable');assert any(e['path']=='/'+NAMES[1]and e['status']==404 for e in r['requests'])
        actual=json.loads((run/r['streams']['stdout']['file']).read_text())
        if app=='npm':assert actual=={}and r['outcome']['exitCode']==0
        else:assert actual[NAMES[1]]['latest']=='2.0.0'and r['outcome']['exitCode']==1
        assert(run/r['streams']['stderr']['file']).read_bytes()==b''
        run,r=row(app,'catalog-retagged');actual=json.loads((run/r['streams']['stdout']['file']).read_text())
        if app=='npm':assert all(v['current']==v['wanted']=='2.0.0'and v['latest']=='1.1.0'for v in actual.values())and set(actual)==set(NAMES)
        else:assert actual=={}and r['outcome']['exitCode']==0
    last=json.loads((MAIN/'commands.json').read_text())[-1]
    assert last['argv'][-1]=='rules-update-*'and last['outcome']['exitCode']==1 and last['before']==last['after']
    assert any(e['status']==404 and e['path']=='/rules-update-local'for e in last['requests'])
    return all_rows


if __name__=='__main__':
    rows=inspect();print(json.dumps(dict(commands=len(rows),nativeManagerCommands=sum(r['kind']=='native-command'for _,r in rows),
        freshNodeObservers=sum(r['kind']=='fresh-node-observer'for _,r in rows),allProcessesAndServersClosed=True,modelComparison=False)))
