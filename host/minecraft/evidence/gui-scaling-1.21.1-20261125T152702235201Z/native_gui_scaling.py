#!/usr/bin/env python3
"""Owner-run original GUI scaling codecs; no GUI, image loading or renderer calls."""
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
OWNER = 'net.minecraft.client.resources.metadata.gui.GuiSpriteScaling'


def cases(version):
    output = []
    def add(name, document):
        observation = OWNER+'$'+{'stretch':'Stretch','tile':'Tile','nine_slice':'NineSlice'}[document['type']]
        fields = [] if document['type']=='stretch' else ['width','height']
        if document['type']=='nine_slice' and version!='1.21.1':
            fields = fields+['stretchInner']
        output.append(dict(id=name, action='codec', **{'class':OWNER}, member='CODEC', input=document,
                           observationClass=observation, fields=fields))
    add('stretch-extra-dimensions', dict(type='stretch', width=0, height=-1))
    for name,w,h in [('tile-valid',8,8),('tile-zero-width',0,8),('tile-zero-height',8,0)]:
        add(name,dict(type='tile',width=w,height=h))
    for name,w,h,b in [
        ('nine-valid',8,8,1), ('nine-zero-scalar',8,8,0), ('nine-no-center',8,8,4),
        ('nine-zero-record',8,8,dict(left=0,top=0,right=0,bottom=0)),
        ('nine-negative-side',8,8,dict(left=-1,top=0,right=0,bottom=0)),
        ('nine-horizontal-overflow',8,8,dict(left=2147483647,top=0,right=1,bottom=0)),
        ('nine-both-overflow',8,8,dict(left=2147483647,top=2147483647,right=2147483647,bottom=2147483647)),
        ('nine-large-scalar',2147483647,2147483647,2147483647),
    ]:
        add(name,dict(type='nine_slice',width=w,height=h,border=b))
    for flag in [False,True]:
        add('nine-stretch-'+str(flag).lower(),dict(type='nine_slice',width=8,height=8,border=1,stretch_inner=flag))
    return output


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
        mappings={OWNER+suffix:dict(name=OWNER+suffix,fields={f:f for f in ['CODEC','width','height','stretchInner']},methods={})for suffix in ['', '$NineSlice', '$Tile', '$Stretch']}
    else:
        metadata=json.loads(paths['metadata'].read_text())
        assert hashlib.sha1(paths['mappings'].read_bytes()).hexdigest()==metadata['downloads']['client_mappings']['sha1']
        all_mappings=read(paths['mappings']);mappings={k:v for k,v in all_mappings.items()if k==OWNER or k.startswith(OWNER+'$')}
    request=dict(schema=1,mappings=mappings,initializers=[],cases=cases(a.version))
    cap=a.private.resolve()/('gui-scaling-'+a.version+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));cap.mkdir(parents=True)
    for n in ['classes','home','tmp']:(cap/n).mkdir()
    for src in [Path(__file__),HERE/'CodecProbe.java',HERE/'mappings.py',HERE.parent/'java/arena_probe.py']:shutil.copyfile(src,cap/src.name)
    (cap/'request.json').write_text(json.dumps(request,indent=2)+'\n');shutil.copyfile(a.inputs,cap/'inputs.json')
    with zipfile.ZipFile(paths['client'])as z:
        original={v['name'].replace('.','/')+'.class':hashlib.sha256(z.read(v['name'].replace('.','/')+'.class')).hexdigest()for v in mappings.values()}
    r=dict(schema=1,target=target['id'],clientSha256=sha(paths['client']),metadataSha256=sha(paths['metadata']),
        mappingSha256=sha(paths['mappings'])if a.version!='26.3'else None,fontBasisReceiptSha256=sha(a.font_basis/'receipt.json'),
        requestSha256=sha(cap/'request.json'),inputsSha256=sha(cap/'inputs.json'),selectedClassSha256=original,
        sourcesSha256={n:sha(cap/n)for n in ['native_gui_scaling.py','CodecProbe.java','mappings.py','arena_probe.py']},
        libraries=basis['libraries'],tools=basis['tools'],jdkReleaseSha256=sha(jdk/'release'),
        profile={k:release[k]for k in ['JAVA_VERSION','JAVA_RUNTIME_VERSION','IMPLEMENTOR','OS_NAME','OS_ARCH']},commands=[],
        scope='Original GuiSpriteScaling.CODEC.parse with14 authored integer/Boolean cases;no image loading,GUI,game,provider or renderer execution. Incidental JVM/class/library effects unqualified.')
    save=lambda:(cap/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
    save();cp=os.pathsep.join(lib['path']for lib in r['libraries']);env=dict(os.environ,TMPDIR=str(cap/'tmp'))
    argv=[str(jdk/'bin/javac'),'-J-XX:ActiveProcessorCount=2','-J-Xmx128m','--release','21','-proc:none','-Xlint:all,-classfile','-Werror','-encoding','UTF-8','-cp',cp,'-d',str(cap/'classes'),str(cap/'CodecProbe.java')]
    result=command(argv,cap,'compile',env,30);r['commands'].append(result);save();assert result['exitCode']==0 and result['ownedGroupAbsent']and not result['timedOut']
    argv=[str(jdk/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx256m','-Djava.awt.headless=true','-Duser.home='+str(cap/'home'),'-Djava.io.tmpdir='+str(cap/'tmp'),'-Xlog:class+load=info:file='+str(cap/'class-load.log'),'-cp',os.pathsep.join([str(cap/'classes'),str(paths['client']),cp]),'study.minecraft.CodecProbe',str(cap/'request.json'),str(cap/'observed.json')]
    result=command(argv,cap,'execute',env,30);r['commands'].append(result)
    r['observerClassesSha256']={str(f.relative_to(cap/'classes')):sha(f)for f in (cap/'classes').rglob('*.class')}
    for n in ['observed.json','class-load.log']:
        if(cap/n).exists():r[n+'Sha256']=sha(cap/n)
    if(cap/'observed.json').exists():
        rows=json.loads((cap/'observed.json').read_text());r['rows']=len(rows);r['observerErrors']=sum(bool(x.get('observerError'))for x in rows)
    save();assert result['exitCode']==0 and result['ownedGroupAbsent']and not result['timedOut']and r.get('observerErrors')==0
    assert sha(cap/'request.json')==r['requestSha256'] and sha(a.inputs)==r['inputsSha256']
    assert sha(paths['client'])==r['clientSha256'] and all(sha(cap/n)==h for n,h in r['sourcesSha256'].items())
    assert all(sha(Path(lib['path']))==lib['sha256']for lib in r['libraries'])
    (a.private/('latest-gui-scaling-'+a.version+'.json')).write_text(json.dumps(dict(capture=str(cap)))+'\n')
    print(json.dumps(dict(capture=str(cap),rows=r['rows'],observerErrors=r['observerErrors'],ownedGroupsAbsent=True)))


if __name__=='__main__':main()
