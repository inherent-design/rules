#!/usr/bin/env python3
"""Owner-run original linked-filesystem APIs over owned bytes;no game or renderer."""
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
sys.path.insert(0, str(HERE.parent/'java'))
from arena_probe import command
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ROLES={'fs':'net.minecraft.server.packs.linkfs.LinkFileSystem','builder':'net.minecraft.server.packs.linkfs.LinkFileSystem$Builder'}
METHODS={'fs':{'builder':'builder()'},'builder':{'put':'put(java.util.List,java.nio.file.Path)','build':'build(java.lang.String)'}}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version',choices=['1.21.1','1.21.4','1.21.5','1.21.11','26.3'],required=True)
    p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--font-basis',type=Path,required=True,help='Existing successful pinned library/tool/classpath receipt;read-only.')
    p.add_argument('--private',type=Path,required=True)
    a=p.parse_args(); paths={k:Path(v)for k,v in json.loads(a.inputs.read_text())['profiles'][a.version].items()}
    target=next(t for t in json.loads((HERE/'targets.json').read_text())['javaReferences']if t['release']==a.version)
    basis=json.loads((a.font_basis/'receipt.json').read_text());assert basis['target']==target['id']
    assert sha(paths['client'])==basis['clientSha256']==target['source']['clientSha256']
    assert sha(paths['metadata'])==target['source']['metadataSha256']
    for lib in basis['libraries']:assert sha(Path(lib['path']))==lib['sha256']
    jdk=Path(basis['tools']['java']['path']).parent.parent
    for name,t in basis['tools'].items():assert sha(Path(t['path']))==t['sha256']
    release=dict(re.findall(r'^([A-Z_]+)="([^"]*)"',(jdk/'release').read_text(),re.M))
    assert release['JAVA_VERSION'].startswith('25.'if a.version=='26.3'else'21.')
    if a.version=='26.3':
        mappings={role:dict(name=name,methods={k:v.split('(')[0]for k,v in METHODS[role].items()})for role,name in ROLES.items()}
    else:
        metadata=json.loads(paths['metadata'].read_text())
        assert hashlib.sha1(paths['mappings'].read_bytes()).hexdigest()==metadata['downloads']['client_mappings']['sha1']
        all_mappings=read(paths['mappings']);mappings={role:all_mappings[name]for role,name in ROLES.items()}
    bindings={role:dict(originalName=ROLES[role],**{'class':item['name']},methods={k:item['methods'][signature]if a.version!='26.3'else item['methods'][k]for k,signature in METHODS[role].items()})for role,item in mappings.items()}
    cap=a.private.resolve()/('linkfs-native-'+a.version+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));cap.mkdir(parents=True)
    for n in ['classes','home','tmp']:(cap/n).mkdir()
    for src in [Path(__file__),HERE/'LinkFSProbe.java',HERE/'mappings.py',HERE.parent/'java/arena_probe.py']:shutil.copyfile(src,cap/src.name)
    (cap/'bindings.json').write_text(json.dumps(bindings,indent=2)+'\n');shutil.copyfile(a.inputs,cap/'inputs.json')
    with zipfile.ZipFile(paths['client'])as z:
        original={v['name'].replace('.','/')+'.class':hashlib.sha256(z.read(v['name'].replace('.','/')+'.class')).hexdigest()for v in mappings.values()}
    r=dict(schema=1,target=target['id'],clientSha256=sha(paths['client']),metadataSha256=sha(paths['metadata']),
        mappingSha256=sha(paths['mappings'])if a.version!='26.3'else None,fontBasisReceiptSha256=sha(a.font_basis/'receipt.json'),
        bindingsSha256=sha(cap/'bindings.json'),inputsSha256=sha(cap/'inputs.json'),selectedClassSha256=original,
        sourcesSha256={n:sha(cap/n)for n in ['native_linkfs.py','LinkFSProbe.java','mappings.py','arena_probe.py']},
        libraries=basis['libraries'],tools=basis['tools'],jdkReleaseSha256=sha(jdk/'release'),
        profile={k:release[k]for k in ['JAVA_VERSION','JAVA_RUNTIME_VERSION','IMPLEMENTOR','OS_NAME','OS_ARCH']},commands=[],
        scope='Original LinkFileSystem.Builder andselected FileSystem/Path/provider/library IO APIs withowned A/B/absent backingfiles.23snapshots;not allmethodcallscounted. No game/GUI/renderer/index-parser/provider-coexistence. Incidental JVM/library effects unqualified.')
    save=lambda:(cap/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
    save();cp=os.pathsep.join(lib['path']for lib in r['libraries']);env=dict(os.environ,TMPDIR=str(cap/'tmp'))
    argv=[str(jdk/'bin/javac'),'-J-XX:ActiveProcessorCount=2','-J-Xmx128m','--release','21','-proc:none','-Xlint:all,-classfile','-Werror','-encoding','UTF-8','-cp',cp,'-d',str(cap/'classes'),str(cap/'LinkFSProbe.java')]
    result=command(argv,cap,'compile',env,30);r['commands'].append(result);save();assert result['exitCode']==0 and result['ownedGroupAbsent']and not result['timedOut']
    argv=[str(jdk/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx256m','-Djava.awt.headless=true','-Duser.home='+str(cap/'home'),'-Djava.io.tmpdir='+str(cap/'tmp'),'-Xlog:class+load=info:file='+str(cap/'class-load.log'),'-cp',os.pathsep.join([str(cap/'classes'),str(paths['client']),cp]),'study.minecraft.LinkFSProbe',str(cap/'bindings.json'),str(cap/'work'),str(cap/'observed.json')]
    result=command(argv,cap,'execute',env,30);r['commands'].append(result)
    r['observerClassesSha256']={str(f.relative_to(cap/'classes')):sha(f)for f in (cap/'classes').rglob('*.class')}
    for n in ['observed.json','class-load.log']:
        if(cap/n).exists():r[n+'Sha256']=sha(cap/n)
    if(cap/'observed.json').exists():
        rows=json.loads((cap/'observed.json').read_text());r['rows']=len(rows['rows']);r['observerErrors']=rows['observerErrors'];r['ownedOriginalBytesRestored']=rows['ownedOriginalBytesRestored']
    save();assert result['exitCode']==0 and result['ownedGroupAbsent']and not result['timedOut']and r.get('observerErrors')==0 and r.get('ownedOriginalBytesRestored')is True
    assert sha(cap/'bindings.json')==r['bindingsSha256'] and sha(a.inputs)==r['inputsSha256']
    assert sha(paths['client'])==r['clientSha256'] and all(sha(cap/n)==h for n,h in r['sourcesSha256'].items())
    assert all(sha(Path(lib['path']))==lib['sha256']for lib in r['libraries'])
    (a.private/('latest-linkfs-native-'+a.version+'.json')).write_text(json.dumps(dict(capture=str(cap)))+'\n')
    print(json.dumps(dict(capture=str(cap),rows=r['rows'],observerErrors=r['observerErrors'],ownedGroupsAbsent=True)))


if __name__=='__main__':main()
