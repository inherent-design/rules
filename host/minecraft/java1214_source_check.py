#!/usr/bin/env python3
"""Owner-local audit of original/private inputs; no native method/tool rerun."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path, kind='sha256'):
    value = hashlib.new(kind)
    with path.open('rb') as stream:
        for part in iter(lambda:stream.read(1_048_576),b''):
            value.update(part)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['client','mappings','metadata','views','range','api']:
        parser.add_argument('--' + name,type=Path,required=True)
    args = parser.parse_args()
    target = next(t for t in json.loads((HERE/'targets.json').read_text())['javaReferences'] if t['release']=='1.21.4')
    assert digest(args.client)==target['source']['clientSha256'] and digest(args.metadata)==target['source']['metadataSha256']
    meta = json.loads(args.metadata.read_text())
    assert digest(args.mappings,'sha1')==meta['downloads']['client_mappings']['sha1']
    assert args.mappings.stat().st_size==meta['downloads']['client_mappings']['size']
    views = json.loads((args.views/'receipt.json').read_text())
    native = json.loads((args.range/'receipt.json').read_text())
    api = json.loads((args.api/'receipt.json').read_text())
    assert views['mappingSha256']==native['mappingSha256']==digest(args.mappings)
    for r in [views,native,api]:
        assert r['clientSha256']==target['source']['clientSha256'] and r['target']==target['id']
        assert all(c['exitCode']==0 and c['ownedGroupAbsent'] and not c['timedOut'] for c in r['commands'])
    for capture,receipt in [(args.views,views),(args.range,native),(args.api,api)]:
        producer_key='producersSha256' if capture==args.views else 'sourcesSha256'
        for name,sha in receipt[producer_key].items():assert digest(capture/name)==sha
        for stem,command in zip(['remap','inspect'] if capture==args.views else ['compile','execute'],receipt['commands']):
            for stream in ['stdout','stderr']:assert digest(capture/(stem+'.'+stream))==command[stream+'Sha256']
    assert digest(args.range/'classes/study/minecraft/Range1214Probe.class')==native['observerClassSha256']
    assert digest(args.range/'class-load.log')==native['classLoadLogSha256']
    assert digest(args.api/'classes/study/host/HostApiScan.class')==api['classSha256']
    for receipt in [native,api]:
        for tool in receipt['tools'].values():assert digest(Path(tool['path']))==tool['sha256']
        java_home=Path(receipt['tools']['java']['path']).parent.parent
        assert digest(java_home/'release')==receipt['jdkReleaseSha256']
    for command,key in zip(views['commands'],['artSha256','decompilerSha256']):
        assert digest(Path(command['argv'][0]))==views['javaSha256']
        assert digest(Path(command['argv'][command['argv'].index('-jar')+1]))==views[key]
    with zipfile.ZipFile(args.client) as archive:
        for row in views['originalClassMembers'].values():
            assert hashlib.sha256(archive.read(row['member'])).hexdigest()==row['sha256']
        records=[json.loads(line)for line in (args.api/'execute.stdout').read_bytes().splitlines()]
        for row in records:
            if row['kind']=='class':assert hashlib.sha256(archive.read(row['entry'])).hexdigest()==row['sha256']
        assert hashlib.sha256(archive.read(native['originalClassMember'])).hexdigest()==native['originalClassSha256']
    for name,sha in views['viewsSha256'].items():assert digest(args.views/'source'/name)==sha
    assert digest(args.views/'mapped.jar')==views['mappedJarSha256']
    library_file=args.range/'library-input.json';assert digest(library_file)==native['libraryReceiptSha256']
    libraries=json.loads(library_file.read_text()); selected={r['name']:r for r in meta['libraries']}
    assert libraries['target']==target['id'] and libraries['metadataSha256']==target['source']['metadataSha256']
    new_bytes=0;reused=0
    for r in libraries['libraries']:
        source=selected[r['name']];artifact=source['downloads']['artifact'];path=Path(r['path'])
        assert len(r['name'].split(':'))==3 and not source.get('rules')
        assert r['url']==artifact['url'] and r['bytes']==artifact['size']==path.stat().st_size
        assert r['sha1']==artifact['sha1']==digest(path,'sha1') and r['sha256']==digest(path)
        if r['origin']=='official-metadata-url':new_bytes+=r['bytes']
        if r['origin']=='verified-reused-read-only-study-input':reused+=1
    catalog=json.loads((HERE/'java1214-registry-catalog.json').read_text())
    assert catalog['generatorSha256']==digest(HERE/'java12111_sources.py') and catalog['sharedReaderSha256']==digest(HERE/'catalog_sources.py')
    findings=json.loads((HERE/'java1214-findings.json').read_text());assert findings['generatorSha256']==digest(HERE/'java1214_contracts.py')
    for name,r in findings['inspectedSources'].items():
        assert r['original']==views['originalClassMembers'][name]
        assert digest(args.views/'source'/(name.replace('.','/')+'.java'))==r['privateViewSha256']
    capture_names=[p.name for p in [args.views,args.range,args.api]]
    hits=[]
    for line in subprocess.check_output(['ps','-axo','pid=,comm=,args='],text=True).splitlines():
        parts=line.strip().split(None,2)
        if len(parts)==3 and Path(parts[1]).name in ['java','javac'] and any(n in parts[2] for n in capture_names):hits.append(int(parts[0]))
    assert not hits,hits
    result=dict(schema=1,status='passed-owner-local-source-audit',producerSha256=digest(Path(__file__)),
        originalClassIdentities=len(views['originalClassMembers']),privateViews=len(views['viewsSha256']),
        staticClasses=next(r['classes']for r in records if r['kind']=='summary'),
        libraries=len(libraries['libraries']),libraryLogicalBytes=sum(r['bytes']for r in libraries['libraries']),
        newlyDownloadedBytes=new_bytes,readOnlyReusedArtifacts=reused,nativeCases=native['cases'],observerErrors=native['observerErrors'],
        actualOwnedJavaArgvMatches=hits,allGroupsAbsent=True,
        privateReceiptsSha256={p.name:digest(p/'receipt.json')for p in [args.views,args.range,args.api]},
        limits=['Read-only original/source/tool identity audit, not a rerun or transformation-equivalence proof.',
                'Raw class-loading log stays private; class loading is not initialization or a complete call/effect graph.',
                'Current-required exact-version library/artifact inputs retained; no cleanup or host-wide free-space claim.'])
    (HERE/'evidence/java1214-source-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
