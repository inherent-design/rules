#!/usr/bin/env python3
"""Two new mixed-axis helper calls using frozen existing observer/classes;no rebuild/game."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'java'))
from arena_probe import command
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--basis',type=Path,required=True)
    p.add_argument('--compat',type=Path,required=True);p.add_argument('--private',type=Path,required=True);a=p.parse_args()
    parent=a.basis.resolve();base=json.loads((parent/'receipt.json').read_text());artifact=a.compat.resolve()
    assert sha(artifact)==base['artifactSha256']
    for n,h in base['sourcesSha256'].items():assert sha(parent/n)==h
    for n,h in base['observerClassesSha256'].items():assert sha(parent/'classes'/n)==h
    for t in base['tools'].values():assert sha(Path(t['path']))==t['sha256']
    for lib in base['libraries']:assert sha(Path(lib['path']))==lib['sha256']
    cases=[]
    for name,origin,angles in [('mixed-positive',[8,4,12],[30,60,90]),('mixed-signed',[-4,16,0],[-45,22.5,30])]:
        element={'from':[0,0,0],'to':[16,16,16],'faces':{'north':{'texture':'#all'}},'rotation':dict(origin=origin,**dict(zip(['x','y','z'],angles,strict=True)))}
        cases.append(dict(id=name,input=dict(textures=dict(all='study:owned'),elements=[element])))
    request=dict(schema=1,metadata=[],configuration=[],adaptation=cases)
    cap=a.private.resolve()/('provider-matrix-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));cap.mkdir(parents=True)
    for n in ['home','tmp']:(cap/n).mkdir()
    shutil.copyfile(Path(__file__),cap/'provider_matrix_probe.py');shutil.copyfile(HERE.parent/'java/arena_probe.py',cap/'arena_probe.py')
    shutil.copyfile(parent/'ProviderProbe.java',cap/'ProviderProbe.java');shutil.copyfile(parent/'receipt.json',cap/'parent-receipt.json')
    (cap/'request.json').write_text(json.dumps(request,indent=2)+'\n')
    r=dict(schema=1,parentCapture=parent.name,parentReceiptSha256=sha(parent/'receipt.json'),artifactSha256=base['artifactSha256'],
        observerClassesSha256=base['observerClassesSha256'],sourcesSha256={n:sha(cap/n)for n in ['provider_matrix_probe.py','ProviderProbe.java','arena_probe.py']},
        requestSha256=sha(cap/'request.json'),tools=base['tools'],libraries=base['libraries'],jdkReleaseSha256=base['jdkReleaseSha256'],commands=[],
        scope='Two additional mixed-axis inputs only,reusing the frozen successful observer;no metadata selection rerun,compiler,game,loader,renderer or FML dependency-selection qualification.')
    save=lambda:(cap/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');save()
    cp=os.pathsep.join([str(parent/'classes'),str(artifact),*[l['path']for l in base['libraries']]])
    java=base['tools']['java']['path']
    result=command([java,'-XX:ActiveProcessorCount=2','-Xmx256m','-Djava.awt.headless=true','-Duser.home='+str(cap/'home'),'-Djava.io.tmpdir='+str(cap/'tmp'),'-Xlog:class+load=info:file='+str(cap/'class-load.log'),'-cp',cp,'study.minecraft.ProviderProbe',str(cap/'request.json'),str(cap/'observed.json')],cap,'execute',dict(os.environ,TMPDIR=str(cap/'tmp')),30)
    r['commands'].append(result)
    for n in ['observed.json','class-load.log']:
        if(cap/n).exists():r[n+'Sha256']=sha(cap/n)
    if(cap/'observed.json').exists():
        raw=json.loads((cap/'observed.json').read_text());r['observerErrors']=raw['observerErrors'];r['adaptationCalls']=len(raw['adaptation'])
    save();assert result['exitCode']==0 and result['ownedGroupAbsent']and not result['timedOut']and r.get('observerErrors')==0 and r.get('adaptationCalls')==2
    assert sha(artifact)==r['artifactSha256']and all(sha(parent/'classes'/n)==h for n,h in r['observerClassesSha256'].items())
    assert all(sha(cap/n)==h for n,h in r['sourcesSha256'].items())
    (a.private/'latest-provider-matrix.json').write_text(json.dumps(dict(capture=str(cap)))+'\n');print(json.dumps(dict(capture=str(cap),calls=2,ownedGroupAbsent=True)))


if __name__=='__main__':main()
