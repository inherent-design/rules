#!/usr/bin/env python3
"""Owner-run original 1.21.11 element/face deserialization, without game launch."""
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
from mappings import read as read_mappings

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'java'))
from arena_probe import command
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ROLES = {
    'element': ('net.minecraft.client.renderer.block.model.BlockElement', ['from','to','faces','rotation','shade','lightEmission']),
    'elementDeserializer': ('net.minecraft.client.renderer.block.model.BlockElement$Deserializer', []),
    'face': ('net.minecraft.client.renderer.block.model.BlockElementFace', ['cullForDirection','tintIndex','texture','uvs','rotation']),
    'faceDeserializer': ('net.minecraft.client.renderer.block.model.BlockElementFace$Deserializer', []),
    'rotation': ('net.minecraft.client.renderer.block.model.BlockElementRotation', ['origin','value','rescale','transform']),
    'euler': ('net.minecraft.client.renderer.block.model.BlockElementRotation$EulerXYZRotation', ['x','y','z']),
    'scalar': ('net.minecraft.client.renderer.block.model.BlockElementRotation$SingleAxisRotation', ['axis','angle']),
    'uvs': ('net.minecraft.client.renderer.block.model.BlockElementFace$UVs', ['minU','minV','maxU','maxV']),
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['client','mappings','metadata','libraries','jdk','private']:
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args()
    target = next(t for t in json.loads((HERE/'targets.json').read_text())['javaReferences'] if t['release']=='1.21.11')
    assert sha(args.client)==target['source']['clientSha256'] and sha(args.metadata)==target['source']['metadataSha256']
    metadata = json.loads(args.metadata.read_text())
    assert hashlib.sha1(args.mappings.read_bytes()).hexdigest()==metadata['downloads']['client_mappings']['sha1']
    libraries = json.loads(args.libraries.read_text()); assert libraries['target']==target['id'] and libraries['metadataSha256']==sha(args.metadata)
    for row in libraries['libraries']:
        assert sha(Path(row['path']))==row['sha256']
    jdk=args.jdk.resolve(); fields=dict(re.findall(r'^([A-Z_]+)="([^"]*)"',(jdk/'release').read_text(),re.M)); assert fields['JAVA_VERSION'].startswith('21.')
    mappings=read_mappings(args.mappings)
    bindings={role:dict(originalName=n, **{'class':mappings[n]['name']}, getters={f:mappings[n]['methods'][f+'()'] for f in getters}) for role,(n,getters) in ROLES.items()}
    capture=args.private.resolve()/('elements-1.21.11-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));capture.mkdir(parents=True)
    for n in ['classes','home','tmp']:(capture/n).mkdir()
    sources=[HERE/'Element12111Probe.java',Path(__file__),HERE/'element12111_cases.json',HERE/'mappings.py',HERE.parent/'java/arena_probe.py']
    for source in sources:shutil.copyfile(source,capture/source.name)
    (capture/'bindings.json').write_text(json.dumps(bindings,indent=2)+'\n'); shutil.copyfile(args.libraries,capture/'library-input.json')
    with zipfile.ZipFile(args.client) as z:
        original={r['class'].replace('.','/')+'.class':hashlib.sha256(z.read(r['class'].replace('.','/')+'.class')).hexdigest() for r in bindings.values()}
    record=dict(schema=1,target=target['id'],clientSha256=sha(args.client),metadataSha256=sha(args.metadata),mappingSha256=sha(args.mappings),
        selectedClassMembersSha256=original,libraryReceiptSha256=sha(capture/'library-input.json'),libraries=libraries['libraries'],
        bindingsSha256=sha(capture/'bindings.json'),sourcesSha256={s.name:sha(capture/s.name) for s in sources},
        jdkReleaseSha256=sha(jdk/'release'),profile={k:fields[k] for k in ['JAVA_VERSION','JAVA_RUNTIME_VERSION','IMPLEMENTOR','OS_NAME','OS_ARCH']},
        tools={n:dict(path=str(jdk/'bin'/n),sha256=sha(jdk/'bin'/n)) for n in ['java','javac']},commands=[],
        scope='Original unmodified signed client;Gson element+face deserializers over authored parsed JSON values. No game/bootstrap,resource lookup,bake,renderer or provider execution.')
    def save():(capture/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    env=dict(os.environ,HOME=str(capture/'home'),TMPDIR=str(capture/'tmp')); classpath=os.pathsep.join(r['path'] for r in libraries['libraries']);save()
    argv=[str(jdk/'bin/javac'),'-J-XX:ActiveProcessorCount=2','-J-Xmx128m','--release','21','-proc:none','-Xlint:all,-classfile','-Werror','-encoding','UTF-8','-cp',classpath,'-d',str(capture/'classes'),str(capture/'Element12111Probe.java')]
    r=command(argv,capture,'compile',env,30);record['commands'].append(r);save();assert r['exitCode']==0 and r['ownedGroupAbsent'],capture
    argv=[str(jdk/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx128m','-Djava.awt.headless=true','-Duser.home='+str(capture/'home'),'-Djava.io.tmpdir='+str(capture/'tmp'),'-cp',os.pathsep.join([str(capture/'classes'),str(args.client.resolve()),classpath]),'study.minecraft.Element12111Probe',str(capture/'bindings.json'),str(capture/'element12111_cases.json'),str(capture/'observed.json')]
    r=command(argv,capture,'execute',env,30);record['commands'].append(r)
    record['observerClassSha256']=sha(capture/'classes/study/minecraft/Element12111Probe.class')
    if (capture/'observed.json').exists():
        observed=json.loads((capture/'observed.json').read_text());record.update(cases=len(observed['cases']),observerErrors=observed['observerErrors'],observedSha256=sha(capture/'observed.json'))
    save();assert sha(args.client)==record['clientSha256'] and all(sha(capture/n)==d for n,d in record['sourcesSha256'].items())
    assert all(sha(Path(row['path']))==row['sha256'] for row in libraries['libraries'])
    print(json.dumps(dict(capture=str(capture),exitCode=r['exitCode'],cases=record.get('cases'),observerErrors=record.get('observerErrors'),ownedGroupsAbsent=all(c['ownedGroupAbsent'] for c in record['commands']))))
    assert r['exitCode']==0 and r['ownedGroupAbsent'] and record.get('observerErrors')==0,capture


if __name__=='__main__':main()
