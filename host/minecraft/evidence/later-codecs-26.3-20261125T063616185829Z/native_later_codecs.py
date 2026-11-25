#!/usr/bin/env python3
"""Owner-run original 26.3 method/codec witness;no download,Gradle or game startup."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import zipfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'java'))
from arena_probe import command
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',type=Path,required=True);p.add_argument('--client',type=Path,required=True);p.add_argument('--libraries',type=Path,required=True);p.add_argument('--private',type=Path,required=True);p.add_argument('--cases',type=Path,default=HERE/'later_codec_cases.json');args=p.parse_args()
    jdk=args.jdk.resolve();client=args.client.resolve();fields=dict(re.findall(r'^([A-Z_]+)="([^"]*)"',(jdk/'release').read_text(),re.M));assert fields['JAVA_VERSION'].startswith('25.')
    target=next(t for t in json.loads((HERE/'targets.json').read_text())['javaReferences'] if t['release']=='26.3');assert sha(client)==target['source']['clientSha256']
    libs=json.loads(args.libraries.read_text());assert libs['target']==target['id'] and libs['metadataSha256']==target['source']['metadataSha256']
    for row in libs['libraries']:assert sha(Path(row['path']))==row['sha256']
    capture=args.private.resolve()/('later-codecs-26.3-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));capture.mkdir(parents=True)
    for n in ['classes','home','tmp']:(capture/n).mkdir()
    selected=json.loads(args.cases.read_text());all_cases=json.loads((HERE/'later_codec_cases.json').read_text());assert selected['schema']==1 and selected['target']==target['id'] and args.cases.suffix=='.json'
    assert selected['cases'] and all(row in all_cases['cases'] for row in selected['cases'])
    sources=[HERE/'LaterCodecProbe.java',HERE/'native_later_codecs.py',args.cases,HERE.parent/'java/arena_probe.py']
    for source in sources:shutil.copyfile(source,capture/source.name)
    shutil.copyfile(args.libraries,capture/'library-input.json')
    assert sha(capture/'library-input.json')==sha(args.libraries)
    wanted=['net/minecraft/client/resources/model/cuboid/CuboidModelElement$Deserializer','net/minecraft/client/resources/model/cuboid/CuboidModelElement','net/minecraft/client/resources/model/cuboid/CuboidRotation','net/minecraft/client/resources/model/cuboid/CuboidRotation$EulerXYZRotation','net/minecraft/client/resources/model/cuboid/CuboidRotation$SingleAxisRotation','net/minecraft/core/Direction','net/minecraft/core/Direction$Axis','net/minecraft/server/packs/metadata/pack/PackFormat','net/minecraft/server/packs/metadata/pack/PackFormat$IntermediaryFormat','net/minecraft/server/packs/PackType']
    with zipfile.ZipFile(client) as jar:members={n+'.class':hashlib.sha256(jar.read(n+'.class')).hexdigest() for n in wanted}
    record=dict(schema=1,target=target['id'],scope='Original selected decoder methods and format codecs;no complete model/pack repository,bootstrap registry,world,renderer or provider execution.',clientSha256=sha(client),requestFile=args.cases.name,requestSha256=sha(capture/args.cases.name),originalClassMembersSha256=members,sourceSha256={s.name:sha(capture/s.name) for s in sources},libraryReceiptSha256=sha(args.libraries),libraries=libs['libraries'],jdkReleaseSha256=sha(jdk/'release'),profile={k:fields[k] for k in ['JAVA_VERSION','JAVA_RUNTIME_VERSION','IMPLEMENTOR','OS_NAME','OS_ARCH']},tools={n:dict(path=str(jdk/'bin'/n),sha256=sha(jdk/'bin'/n)) for n in ['java','javac']},commands=[])
    def save():(capture/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    env=dict(os.environ,HOME=str(capture/'home'),TMPDIR=str(capture/'tmp'));classpath=os.pathsep.join(l['path'] for l in libs['libraries']);save()
    argv=[str(jdk/'bin/javac'),'-J-XX:ActiveProcessorCount=2','-J-Xmx128m','--release','25','-proc:none','-Xlint:all,-classfile','-Werror','-encoding','UTF-8','-cp',classpath,'-d',str(capture/'classes'),str(capture/'LaterCodecProbe.java')]
    r=command(argv,capture,'compile',env,30);record['commands'].append(r);save();assert r['exitCode']==0 and r['ownedGroupAbsent'],capture
    argv=[str(jdk/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx128m','-Djava.awt.headless=true','-Duser.home='+str(capture/'home'),'-Djava.io.tmpdir='+str(capture/'tmp'),'-cp',os.pathsep.join([str(capture/'classes'),str(client),classpath]),'study.minecraft.LaterCodecProbe',str(capture/args.cases.name),str(capture/'observed.json')]
    r=command(argv,capture,'execute',env,20);record['commands'].append(r);record['observerClassSha256']=sha(capture/'classes/study/minecraft/LaterCodecProbe.class')
    if (capture/'observed.json').exists():
        observed=json.loads((capture/'observed.json').read_text());record.update(observedSha256=sha(capture/'observed.json'),cases=len(observed['cases']),observerErrors=observed['observerErrors'])
    save();assert sha(client)==record['clientSha256'] and all(sha(capture/n)==d for n,d in record['sourceSha256'].items())
    assert all(sha(Path(l['path']))==l['sha256'] for l in libs['libraries'])
    print(json.dumps(dict(capture=str(capture),exitCode=r['exitCode'],cases=record.get('cases'),observerErrors=record.get('observerErrors'),ownedGroupsAbsent=all(c['ownedGroupAbsent'] for c in record['commands']))))
    assert r['exitCode']==0 and r['ownedGroupAbsent'] and record.get('observerErrors')==0,capture


if __name__=='__main__':main()
