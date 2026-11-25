#!/usr/bin/env python3
"""Owner-run original Compat policy/JSON APIs with supplied metadata;not a loader/game."""
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
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--compat',type=Path,required=True)
    p.add_argument('--basis',type=Path,required=True,help='Existing successful Java21 library/tool receipt directory;read-only.')
    p.add_argument('--maven-artifact',type=Path,required=True,help='Existing local class-path dependency;not FML-selected version qualification.')
    p.add_argument('--private',type=Path,required=True);a=p.parse_args()
    artifact=a.compat.resolve();basis=json.loads((a.basis/'receipt.json').read_text())
    pin=next(t for t in json.loads((HERE/'targets.json').read_text())['providers']if t['id']=='compat-4ae402eaa858eef4')
    assert sha(artifact)==pin['sha256']
    tools=basis['tools']
    for t in tools.values():assert sha(Path(t['path']))==t['sha256']
    jdk=Path(tools['java']['path']).parent.parent;assert 'JAVA_VERSION="21.'in(jdk/'release').read_text()
    libs=[l for l in basis['libraries']if l['name'].startswith(('com.google.code.gson:gson:','org.joml:joml:'))];assert len(libs)==2
    for l in libs:assert sha(Path(l['path']))==l['sha256']
    maven=a.maven_artifact.resolve();assert maven.is_file()
    libs+=[dict(name=maven.name,path=str(maven),sha256=sha(maven),role='Explicit local Maven test dependency;not actual FML library selection.')]
    with zipfile.ZipFile(artifact)as archive:
        selected={n:hashlib.sha256(archive.read(n)).hexdigest()for n in archive.namelist()if n in [
            'design/inherent/skyweavecompat/'+name+'.class'for name in ['Feature','FeatureSettings','FeatureSelection','DependencyVersions','client/model/MultiAxisModels']]}
        assert len(selected)==5 and all(int.from_bytes(archive.read(n)[6:8],'big')==65 for n in selected)
    cap=a.private.resolve()/('provider-policy-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));cap.mkdir(parents=True)
    for n in ['classes','home','tmp']:(cap/n).mkdir()
    for src in [Path(__file__),HERE/'ProviderProbe.java',HERE/'provider-cases.json',HERE.parent/'java/arena_probe.py']:shutil.copyfile(src,cap/src.name)
    shutil.copyfile(HERE/'provider-cases.json',cap/'request.json')
    r=dict(schema=1,artifactSha256=sha(artifact),target=pin['id'],selectedClassSha256=selected,basisReceiptSha256=sha(a.basis/'receipt.json'),
        requestSha256=sha(cap/'request.json'),sourcesSha256={n:sha(cap/n)for n in ['provider_probe.py','ProviderProbe.java','provider-cases.json','arena_probe.py']},
        tools=tools,libraries=libs,jdkReleaseSha256=sha(jdk/'release'),profile=dict(re.findall(r'^([A-Z_]+)="([^"]*)"',(jdk/'release').read_text(),re.M)),commands=[],
        scope='Actual selected Compat policy and JSON helper classes with explicit metadata/feature settings and Reader/JSON fixtures. Other features disabled in select;actual ModList,OptionalIntegrations,plugin,Mixin application,game,renderer and filesystem config load are not called. Presence/version metadata is supplied,not observed installed mods.')
    save=lambda:(cap/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');save()
    cp=os.pathsep.join([str(artifact),*[l['path']for l in libs]]);env=dict(os.environ,TMPDIR=str(cap/'tmp'))
    result=command([str(jdk/'bin/javac'),'-J-XX:ActiveProcessorCount=2','-J-Xmx128m','--release','21','-proc:none','-Xlint:all,-classfile','-Werror','-cp',cp,'-d',str(cap/'classes'),str(cap/'ProviderProbe.java')],cap,'compile',env,30)
    r['commands'].append(result);save();assert result['exitCode']==0 and result['ownedGroupAbsent']and not result['timedOut']
    result=command([str(jdk/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx256m','-Djava.awt.headless=true','-Duser.home='+str(cap/'home'),'-Djava.io.tmpdir='+str(cap/'tmp'),'-Xlog:class+load=info:file='+str(cap/'class-load.log'),'-cp',os.pathsep.join([str(cap/'classes'),cp]),'study.minecraft.ProviderProbe',str(cap/'request.json'),str(cap/'observed.json')],cap,'execute',env,30)
    r['commands'].append(result)
    r['observerClassesSha256']={str(f.relative_to(cap/'classes')):sha(f)for f in(cap/'classes').rglob('*.class')}
    for n in ['observed.json','class-load.log']:
        if(cap/n).exists():r[n+'Sha256']=sha(cap/n)
    if(cap/'observed.json').exists():
        data=json.loads((cap/'observed.json').read_text());r['observerErrors']=data['observerErrors'];r['cases']={key:len(data[key])for key in ['metadata','configuration','adaptation']}
    save();assert result['exitCode']==0 and result['ownedGroupAbsent']and not result['timedOut']and r.get('observerErrors')==0
    assert sha(artifact)==r['artifactSha256']and all(sha(cap/n)==h for n,h in r['sourcesSha256'].items())
    assert all(sha(Path(l['path']))==l['sha256']for l in libs)
    (a.private/'latest-provider-policy.json').write_text(json.dumps(dict(capture=str(cap)))+'\n')
    print(json.dumps(dict(capture=str(cap),cases=r['cases'],observerErrors=0,ownedGroupsAbsent=True)))


if __name__=='__main__':main()
