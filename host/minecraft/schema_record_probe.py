#!/usr/bin/env python3
"""Owner-run original CodecUI one-field callers; no provider, game, or GUI launch."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'java'))
from arena_probe import command
sha = lambda p, kind='sha256': hashlib.new(kind, p.read_bytes()).hexdigest()
NAMES = ['com.google.code.gson:gson:2.10.1', 'com.google.guava:guava:32.1.2-jre',
    'com.google.guava:failureaccess:1.0.1', 'com.mojang:datafixerupper:8.0.16',
    'it.unimi.dsi:fastutil:8.5.12', 'org.slf4j:slf4j-api:2.0.9']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['jdk','bundled','metadata','reused','private']:
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    assert sha(args.bundled) == '389766940c13572819b4ba79cf9466c571256f01ecd0cb43dc3ac4b11ff3805a'
    target = next(t for t in json.loads((HERE/'targets.json').read_text())['javaReferences'] if t['id']=='java-1.21.1-vanilla')
    assert sha(args.metadata) == target['source']['metadataSha256']
    metadata = json.loads(args.metadata.read_text())
    selected = {l['name']:l['downloads']['artifact'] for l in metadata['libraries'] if l['name'] in NAMES}
    assert set(selected) == set(NAMES)
    reused = json.loads(args.reused.read_text())
    libraries = []
    for name in NAMES:
        artifact = selected[name]
        matches = [Path(l['path']) for l in reused['libraries'] if l['path'].endswith('/'+artifact['path'])]
        assert len(matches) == 1
        path = matches[0]; assert sha(path,'sha1') == artifact['sha1'] and path.stat().st_size == artifact['size']
        libraries.append(dict(name=name,path=str(path),sha256=sha(path),sha1=artifact['sha1'],bytes=artifact['size'],
            origin='read-only reuse; exact official 1.21.1 metadata artifact',url=artifact['url']))
    jdk = args.jdk.resolve()
    fields = dict(re.findall(r'^([A-Z_]+)="([^"]*)"',(jdk/'release').read_text(),re.M))
    assert fields['JAVA_VERSION'].startswith('21.')
    capture = args.private.resolve()/('schema-record-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    capture.mkdir(parents=True)
    for name in ['classes','home','tmp']:(capture/name).mkdir()
    for source in [Path(__file__),HERE/'SchemaRecordProbe.java',HERE.parent/'java/arena_probe.py']:
        shutil.copyfile(source,capture/source.name)
    shutil.copyfile(args.metadata,capture/'metadata.json')
    shutil.copyfile(args.reused,capture/'reused-input.json')
    cp = os.pathsep.join([str(args.bundled.resolve())]+[l['path'] for l in libraries])
    record = dict(schema=1,scope='Original bundled CodecUI record builder and supplied DFU/Gson dependencies under authored one-field callers; no Polytone manager, loader, Minecraft, renderer, GUI or account/world access.',
        bundledSha256=sha(args.bundled),metadataSha256=sha(args.metadata),reusedReceiptSha256=sha(args.reused),
        libraries=libraries,profile={k:fields[k] for k in ['JAVA_VERSION','JAVA_RUNTIME_VERSION','IMPLEMENTOR','OS_NAME','OS_ARCH']},
        jdkReleaseSha256=sha(jdk/'release'),tools={n:dict(path=str(jdk/'bin'/n),sha256=sha(jdk/'bin'/n)) for n in ['java','javac']},
        sourcesSha256={n:sha(capture/n) for n in ['SchemaRecordProbe.java','schema_record_probe.py','arena_probe.py']},commands=[],
        limits=['Explicit primitive schema avoids reflective schema inference and all game/registry classes.',
                'All six forms are authored API callers; null-default and custom MapCodec cases are not shown reachable in a Polytone pack.',
                'Only one-field group and selected integer/missing/null/wrong-string inputs; no full DFU grammar or floating/duplicate-key/partial semantics.',
                'Class-path library choice is fixed by this study, not a native JarJar negotiation result.'])
    def save():(capture/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    save();env=dict(os.environ,TMPDIR=str(capture/'tmp'))
    argv=[str(jdk/'bin/javac'),'-J-XX:ActiveProcessorCount=2','-J-Xmx128m','--release','21','-proc:none','-encoding','UTF-8',
        '-cp',cp,'-d',str(capture/'classes'),str(capture/'SchemaRecordProbe.java')]
    result=command(argv,capture,'compile',env,30);record['commands'].append(result);save()
    assert result['exitCode']==0 and result['ownedGroupAbsent'] and not result['timedOut'],capture
    record['observerClassesSha256']={str(p.relative_to(capture/'classes')):sha(p) for p in (capture/'classes').rglob('*.class')}
    argv=[str(jdk/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx96m','-Djava.awt.headless=true',
        '-Duser.home='+str(capture/'home'),'-Djava.io.tmpdir='+str(capture/'tmp'),
        '-Xlog:class+load=info:file='+str(capture/'class-load.log'),'-cp',str(capture/'classes')+os.pathsep+cp,'study.minecraft.SchemaRecordProbe']
    result=command(argv,capture,'execute',env,20);record['commands'].append(result);save()
    assert result['exitCode']==0 and result['ownedGroupAbsent'] and not result['timedOut'],capture
    raw=(capture/'execute.stdout').read_bytes();observed=json.loads(raw)
    assert observed['schema']==1 and len(observed['cases'])==30
    (capture/'observed.json').write_bytes(raw)
    record['observedSha256']=sha(capture/'observed.json');record['classLoadLogSha256']=sha(capture/'class-load.log')
    loaded=re.findall(r'\[class,load\] ([\w.$]+) source:',(capture/'class-load.log').read_text())
    assert not any(n.startswith(('net.minecraft.','net.mehvahdjukaar.polytone.')) for n in loaded)
    with zipfile.ZipFile(args.bundled) as archive:
        record['loadedBundledClassEntriesSha256']={n.replace('.','/')+'.class':hashlib.sha256(archive.read(n.replace('.','/')+'.class')).hexdigest() for n in loaded if n.startswith('net.mehvahdjukaar.codecui.')}
    assert 'net/mehvahdjukaar/codecui/SchemaRecord.class' in record['loadedBundledClassEntriesSha256']
    assert all(sha(capture/n)==v for n,v in record['sourcesSha256'].items())
    assert sha(args.bundled)==record['bundledSha256'] and sha(jdk/'release')==record['jdkReleaseSha256']
    for lib in libraries:assert sha(Path(lib['path']))==lib['sha256']
    save()
    print(json.dumps(dict(capture=str(capture),cases=30,loadedBundledClasses=len(record['loadedBundledClassEntriesSha256']),
        ownedGroupsAbsent=all(c['ownedGroupAbsent'] for c in record['commands']),gameOrPolytoneClassesLoaded=False)))


if __name__=='__main__':main()
