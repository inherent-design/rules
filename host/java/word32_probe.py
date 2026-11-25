#!/usr/bin/env python3
"""Collect authored int arithmetic on selected Java17/21/25 builds,never ordinary CI."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from arena_probe import command
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',type=Path,required=True);p.add_argument('--feature',type=int,choices=[17,21,25],required=True);p.add_argument('--private',type=Path,required=True);a=p.parse_args()
    jdk=a.jdk.resolve();fields=dict(re.findall(r'^([A-Z_]+)="([^"]*)"',(jdk/'release').read_text(),re.M));assert fields['JAVA_VERSION'].startswith(str(a.feature)+'.')
    cap=a.private.resolve()/('word32-'+str(a.feature)+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));cap.mkdir(parents=True)
    for n in ['classes','home','tmp']:(cap/n).mkdir()
    for f in [Path(__file__),HERE/'Word32Probe.java',HERE/'arena_probe.py']:shutil.copyfile(f,cap/f.name)
    sources={n:sha(cap/n)for n in ['word32_probe.py','Word32Probe.java','arena_probe.py']}
    receipt=dict(schema=1,scope='Authored runtime int add/subtract and signed/unsigned views;incidental JVM/stream/native work is not an analyzed effect closure. No game or studied application launch.',sourcesSha256=sources,
        feature=a.feature,profile={k:fields[k]for k in ['JAVA_VERSION','JAVA_RUNTIME_VERSION','IMPLEMENTOR','OS_NAME','OS_ARCH']},jdkReleaseSha256=sha(jdk/'release'),
        tools={n:dict(path=str(jdk/'bin'/n),sha256=sha(jdk/'bin'/n))for n in ['java','javac']},commands=[])
    def save():(cap/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    save();env=dict(os.environ,TMPDIR=str(cap/'tmp'))
    cmds=[('compile',[str(jdk/'bin/javac'),'-J-XX:ActiveProcessorCount=2','-J-Xmx64m','--release','17','-proc:none','-Xlint:all','-Werror','-d',str(cap/'classes'),str(cap/'Word32Probe.java')]),
          ('execute',[str(jdk/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx32m','-Djava.awt.headless=true','-Duser.home='+str(cap/'home'),'-Djava.io.tmpdir='+str(cap/'tmp'),'-cp',str(cap/'classes'),'study.host.Word32Probe'])]
    for label,argv in cmds:
        result=command(argv,cap,label,env,20);receipt['commands'].append(result);save();assert result['exitCode']==0 and result['ownedGroupAbsent']and not result['timedOut'],cap
    rows=json.loads((cap/'execute.stdout').read_text());assert rows['schema']==1 and len(rows['rows'])==10
    receipt.update(classSha256=sha(cap/'classes/study/host/Word32Probe.class'),observedSha256=sha(cap/'execute.stdout'),cases=10)
    assert all(sha(cap/n)==h for n,h in sources.items());save();(a.private/('latest-'+str(a.feature)+'.json')).write_text(json.dumps(dict(capture=str(cap)))+'\n')
    print(json.dumps(dict(capture=str(cap),cases=10,ownedGroupsAbsent=True)))


if __name__=='__main__':main()
