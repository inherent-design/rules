#!/usr/bin/env python3
"""Owner-run five Files.isSameFile calls on one explicitly selected existing JDK."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'java'))
from arena_probe import command
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',type=Path,required=True);p.add_argument('--feature',type=int,choices=[17,21,25],required=True);p.add_argument('--private',type=Path,required=True);a=p.parse_args()
    jdk=a.jdk.resolve();fields=dict(re.findall(r'^([A-Z_]+)="([^"]*)"',(jdk/'release').read_text(),re.M));assert fields['JAVA_VERSION'].startswith(str(a.feature)+'.')
    cap=a.private.resolve()/('java-same-file-'+str(a.feature)+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));cap.mkdir(parents=True)
    for n in ['classes','home','tmp']:(cap/n).mkdir()
    for src in [Path(__file__),HERE/'SameFileProbe.java',HERE.parent/'java/arena_probe.py']:shutil.copyfile(src,cap/src.name)
    r=dict(schema=1,feature=a.feature,profile={k:fields[k]for k in ['JAVA_VERSION','JAVA_RUNTIME_VERSION','IMPLEMENTOR','OS_NAME','OS_ARCH']},
        sourcesSha256={n:sha(cap/n)for n in ['java_probe.py','SameFileProbe.java','arena_probe.py']},
        jdkReleaseSha256=sha(jdk/'release'),tools={n:dict(path=str(jdk/'bin'/n),sha256=sha(jdk/'bin'/n))for n in ['java','javac']},commands=[],
        limits=['Five standard Files.isSameFile calls plus separate attribute reads on owned empty directories;no application,GUI,daemon,account or network.',
                'Library result and object existence are separate;not a complete provider/permission/race/symlink or native object-identity proof.'])
    save=lambda:(cap/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');save();env=dict(os.environ,TMPDIR=str(cap/'tmp'))
    argv=[str(jdk/'bin/javac'),'-J-XX:ActiveProcessorCount=2','-J-Xmx64m','--release','17','-proc:none','-Xlint:all','-Werror','-encoding','UTF-8','-d',str(cap/'classes'),str(cap/'SameFileProbe.java')]
    c=command(argv,cap,'compile',env,20);r['commands'].append(c);save();assert c['exitCode']==0 and c['ownedGroupAbsent']and not c['timedOut']
    argv=[str(jdk/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx64m','-Djava.awt.headless=true','-Duser.home='+str(cap/'home'),'-Djava.io.tmpdir='+str(cap/'tmp'),'-cp',str(cap/'classes'),'study.host.SameFileProbe',str(cap/'work')]
    c=command(argv,cap,'execute',env,15);r['commands'].append(c);r['classSha256']=sha(cap/'classes/study/host/SameFileProbe.class');save()
    assert c['exitCode']==0 and c['ownedGroupAbsent']and not c['timedOut']
    assert sha(jdk/'release')==r['jdkReleaseSha256']and all(sha(cap/n)==h for n,h in r['sourcesSha256'].items())
    assert len((cap/'execute.stdout').read_text().splitlines())==5
    (a.private/('latest-java-same-file-'+str(a.feature)+'.json')).write_text(json.dumps(dict(capture=str(cap)))+'\n')
    print(json.dumps(dict(capture=str(cap),feature=a.feature,calls=5,ownedGroupsAbsent=True)))


if __name__=='__main__':main()
