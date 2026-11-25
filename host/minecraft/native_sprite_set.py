#!/usr/bin/env python3
"""Owner-run original mutable sprite-set helper with constructor-bypassed identity controls; never CI."""
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
from mappings import read

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'java'))
from arena_probe import command
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
BASE='net.minecraft.client.particle.'


def roles(version):
    modern = version in ['1.21.11', '26.3']
    owner = 'ParticleResources' if modern else 'ParticleEngine'
    sprite = 'net.minecraft.client.renderer.texture.TextureAtlasSprite'
    methods = {'bind': 'rebind(java.util.List)', 'frame': sprite+' get(int,int)'}
    if modern: methods['first'] = sprite+' first()'
    return {'set': BASE+owner+'$MutableSpriteSet', 'sprite': sprite}, {'set': methods}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['client','metadata','libraries','jdk','private']:
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--mappings',type=Path)
    p.add_argument('--brigadier',type=Path,help='Existing exact metadata-selected Java library;no acquisition.')
    p.add_argument('--version',required=True,choices=['1.21.1','1.21.4','1.21.5','1.21.11','26.3'])
    a = p.parse_args()
    target = next(t for t in json.loads((HERE/'targets.json').read_text())['javaReferences'] if t['release']==a.version)
    assert sha(a.client)==target['source']['clientSha256'] and sha(a.metadata)==target['source']['metadataSha256']
    metadata=json.loads(a.metadata.read_text()); lib=json.loads(a.libraries.read_text())
    if 'libraries' in lib:
        assert lib['target']==target['id'] and lib['metadataSha256']==sha(a.metadata)
        libraries=lib['libraries']
    else:
        libraries=[dict(name=r['name'],path=r['cachedPath'],sha256=sha(Path(r['cachedPath'])),sha1=r['artifact']['sha1'])
                   for r in lib[a.version] if r['cachedPath']]
    if a.brigadier:
        selected=next(r for r in metadata['libraries'] if r['name'].startswith('com.mojang:brigadier:'))
        artifact=selected['downloads']['artifact'];assert a.brigadier.stat().st_size==artifact['size']
        assert not any(r['name'].startswith('com.mojang:brigadier:') for r in libraries)
        libraries=libraries+[dict(name=selected['name'],path=str(a.brigadier.resolve()),sha256=sha(a.brigadier),sha1=artifact['sha1'])]
    for r in libraries:
        path=Path(r['path']); assert sha(path)==r['sha256']
        assert hashlib.sha1(path.read_bytes()).hexdigest()==r['sha1']
        assert any(m['name']==r['name'] and m.get('downloads',{}).get('artifact',{}).get('sha1')==r['sha1'] for m in metadata['libraries'])
    ROLES,METHODS=roles(a.version)
    if a.version=='26.3':
        assert a.mappings is None
        mappings={n:dict(name=n,fields={'sprites':'sprites'}if role=='set'else{},methods={s:s.split('(')[0].split()[-1] for s in METHODS.get(role,{}).values()}) for role,n in ROLES.items()}
    else:
        assert a.mappings and hashlib.sha1(a.mappings.read_bytes()).hexdigest()==metadata['downloads']['client_mappings']['sha1']
        mappings=read(a.mappings)
    bindings={role:dict(originalName=n,**{'class':mappings[n]['name']},fields={'sprites':mappings[n]['fields']['sprites']}if role=='set'else{},
        methods={key:mappings[n]['methods'][signature] for key,signature in METHODS.get(role,{}).items()}) for role,n in ROLES.items()}
    jdk=a.jdk.resolve(); release=dict(re.findall(r'^([A-Z_]+)="([^"]*)"',(jdk/'release').read_text(),re.M))
    assert release['JAVA_VERSION'].startswith('25.' if a.version=='26.3' else '21.')
    prefix='sprite-set-'
    cap=a.private.resolve()/(prefix+a.version+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));cap.mkdir(parents=True)
    for n in ['classes','home','tmp']:(cap/n).mkdir()
    producers=[Path(__file__),HERE/'SpriteSetProbe.java',HERE/'sprite_set_cases.json',HERE/'mappings.py',HERE.parent/'java/arena_probe.py']
    for f in producers:shutil.copyfile(f,cap/f.name)
    request=json.loads((cap/'sprite_set_cases.json').read_text())
    (cap/'request.json').write_text(json.dumps(request,indent=2)+'\n')
    (cap/'bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')
    with zipfile.ZipFile(a.client) as z:
        original={r['class'].replace('.','/')+'.class':hashlib.sha256(z.read(r['class'].replace('.','/')+'.class')).hexdigest() for r in bindings.values()}
    receipt=dict(schema=1,target=target['id'],clientSha256=sha(a.client),metadataSha256=sha(a.metadata),mappingSha256=sha(a.mappings) if a.mappings else None,
        selectedClassSha256=original,sourcesSha256={f.name:sha(cap/f.name) for f in producers},bindingsSha256=sha(cap/'bindings.json'),libraries=libraries,
        tools={n:dict(path=str(jdk/'bin'/n),sha256=sha(jdk/'bin'/n)) for n in ['java','javac']},jdkReleaseSha256=sha(jdk/'release'),
        profile={k:release[k] for k in ['JAVA_VERSION','JAVA_RUNTIME_VERSION','IMPLEMENTOR','OS_NAME','OS_ARCH']},commands=[],
        requestSha256=sha(cap/'request.json'),
        scope='Original MutableSpriteSet constructor/bind/frame/first with three Unsafe.allocateInstance sprite identity adapters. No deliberate sprite-field/constructor/render/close/engine/GPU call or game/provider entrypoint. Incidental JVM/class/library effects remain unqualified.')
    def save():(cap/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    save();env=dict(os.environ,TMPDIR=str(cap/'tmp'));cp=os.pathsep.join(r['path'] for r in libraries)
    argv=[str(jdk/'bin/javac'),'-J-XX:ActiveProcessorCount=2','-J-Xmx128m','--release','21','-proc:none','-Xlint:all,-classfile','-Werror','-encoding','UTF-8','-cp',cp,'-d',str(cap/'classes'),str(cap/'SpriteSetProbe.java')]
    r=command(argv,cap,'compile',env,30);receipt['commands'].append(r);save()
    assert r['exitCode']==0 and r['ownedGroupAbsent'] and not r['timedOut'],cap
    argv=[str(jdk/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx256m','-Djava.awt.headless=true','-Duser.home='+str(cap/'home'),'-Djava.io.tmpdir='+str(cap/'tmp'),
          '-Xlog:class+load=info:file='+str(cap/'class-load.log'),'-cp',os.pathsep.join([str(cap/'classes'),str(a.client.resolve()),cp]),
          'study.minecraft.SpriteSetProbe',str(cap/'bindings.json'),str(cap/'request.json'),str(cap/'observed.json')]
    r=command(argv,cap,'execute',env,30);receipt['commands'].append(r)
    receipt['observerClassesSha256']={str(f.relative_to(cap/'classes')):sha(f) for f in (cap/'classes').rglob('*.class')}
    for name in ['observed.json','class-load.log']:
        if (cap/name).is_file():receipt[name+'Sha256']=sha(cap/name)
    if (cap/'observed.json').exists():
        obs=json.loads((cap/'observed.json').read_text());receipt.update(rows=len(obs['rows']),originalCalls=obs['originalCalls'],observerErrors=obs['observerErrors'])
    save()
    assert sha(a.client)==receipt['clientSha256'] and all(sha(cap/n)==h for n,h in receipt['sourcesSha256'].items())
    assert all(sha(Path(r['path']))==r['sha256'] for r in libraries)
    (a.private/('latest-'+prefix+a.version+'.json')).write_text(json.dumps(dict(capture=str(cap)))+'\n')
    print(json.dumps(dict(capture=str(cap),exitCode=r['exitCode'],rows=receipt.get('rows'),originalCalls=receipt.get('originalCalls'),observerErrors=receipt.get('observerErrors'),ownedGroupsAbsent=all(c['ownedGroupAbsent'] for c in receipt['commands']))))
    assert r['exitCode']==0 and r['ownedGroupAbsent'] and not r['timedOut'] and receipt.get('observerErrors')==0,cap


if __name__=='__main__':main()
