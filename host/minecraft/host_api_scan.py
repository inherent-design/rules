#!/usr/bin/env python3
"""Owner-run static client bytecode census;does not start the inspected game."""
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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',type=Path,required=True);p.add_argument('--client',type=Path,required=True);p.add_argument('--private',type=Path,required=True);p.add_argument('--release',choices=['1.21.4','1.21.11','26.3'],default='26.3');args=p.parse_args()
    jdk=args.jdk.resolve();client=args.client.resolve();release=jdk/'release'
    fields=dict(re.findall(r'^([A-Z_]+)="([^"]*)"',release.read_text(),re.M));assert fields['JAVA_VERSION'].startswith('25.')
    targets=json.loads((HERE/'targets.json').read_text());target=next(t for t in targets['javaReferences'] if t['release']==args.release)
    assert sha(client)==target['source']['clientSha256'] and client.stat().st_size==target['source']['clientBytes']
    capture=args.private.resolve()/('host-api-'+args.release+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));capture.mkdir(parents=True)
    for n in ['classes','home','tmp']:(capture/n).mkdir()
    sources=[HERE/'HostApiScan.java',HERE/'host_api_scan.py',HERE.parent/'java/arena_probe.py']
    for source in sources:shutil.copyfile(source,capture/source.name)
    record=dict(schema=1,target=target['id'],targetDeclaredLauncherJavaMajor=target['declaredLauncherJavaMajor'],scope='Static direct invoke instructions/native declarations only;no target class loading/linking/execution. Inspection uses Java25 independently of the target launcher runtime.',clientSha256=sha(client),jdkReleaseSha256=sha(release),profile={k:fields[k] for k in ['JAVA_VERSION','JAVA_RUNTIME_VERSION','IMPLEMENTOR','OS_NAME','OS_ARCH']},tools={n:dict(path=str(jdk/'bin'/n),sha256=sha(jdk/'bin'/n)) for n in ['java','javac']},sourcesSha256={p.name:sha(capture/p.name) for p in sources},commands=[])
    def save():(capture/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    env=dict(os.environ,TMPDIR=str(capture/'tmp'));save()
    argv=[str(jdk/'bin/javac'),'-J-XX:ActiveProcessorCount=2','-J-Xmx128m','--release','25','-proc:none','-Xlint:all','-Werror','-d',str(capture/'classes'),str(capture/'HostApiScan.java')]
    r=command(argv,capture,'compile',env,30);record['commands'].append(r);save();assert r['exitCode']==0 and r['ownedGroupAbsent'],capture
    argv=[str(jdk/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx256m','-Djava.awt.headless=true','-Duser.home='+str(capture/'home'),'-Djava.io.tmpdir='+str(capture/'tmp'),'-cp',str(capture/'classes'),'study.host.HostApiScan',str(client)]
    r=command(argv,capture,'execute',env,45);record['commands'].append(r);record['classSha256']=sha(capture/'classes/study/host/HostApiScan.class');save();assert r['exitCode']==0 and r['ownedGroupAbsent'],capture
    summary=json.loads((capture/'execute.stdout').read_text().splitlines()[-1]);assert summary['kind']=='summary' and summary['classes']>0
    assert sha(client)==record['clientSha256'] and all(sha(capture/p.name)==record['sourcesSha256'][p.name] for p in sources)
    print(json.dumps(dict(capture=str(capture),summary=summary)))


if __name__=='__main__':main()
