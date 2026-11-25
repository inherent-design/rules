#!/usr/bin/env python3
"""Owner-run Java17/21/25 class-lookup/initialization witness; authored classes only."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
from arena_probe import command

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jdk',type=Path,required=True);parser.add_argument('--private',type=Path,required=True);args=parser.parse_args()
    jdk=args.jdk.resolve();fields=dict(re.findall(r'^([A-Z_]+)="([^"]*)"',(jdk/'release').read_text(),re.M))
    assert fields['JAVA_VERSION'].split('.')[0] in ['17','21','25']
    capture=args.private.resolve()/('class-init-'+fields['JAVA_VERSION'].split('.')[0]+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    capture.mkdir(parents=True)
    for name in ['classes','home','tmp']:(capture/name).mkdir()
    for name in ['ClassInitProbe.java','class_init_probe.py','arena_probe.py']:shutil.copyfile(HERE/name,capture/name)
    record=dict(schema=1,scope='Authored class literals,Class.forName defaults/explicit initialization and controlled child-first class loaders; no application/provider/game/GUI class or native plugin loaded.',
        profile={k:fields[k] for k in ['JAVA_VERSION','JAVA_RUNTIME_VERSION','IMPLEMENTOR','OS_NAME','OS_ARCH']},
        host=dict(system=platform.system(),kernelRelease=platform.release(),machine=platform.machine()),
        tools={n:dict(path=str(jdk/'bin'/n),sha256=sha(jdk/'bin'/n)) for n in ['java','javac']},
        jdkReleaseSha256=sha(jdk/'release'),sourcesSha256={n:sha(capture/n) for n in ['ClassInitProbe.java','class_init_probe.py','arena_probe.py']},
        commands=[],limits=['Selected authored classes/serial requests on the recorded JDK/host; no simultaneous initialization,custom module,security-manager or arbitrary-loader contract.',
            'initialize=false suppresses initialization of the named non-array class here; custom loader code can still execute and have effects.',
            'Class identities are observer labels of actual Class reference equality, not executable capabilities or persistent identities.',
            'Initialization failures retain authored counter effects; no application rollback/recovery or Polytone runtime defect is established.'])
    if platform.system()=='Darwin':record['host']['swVers']=subprocess.check_output(['sw_vers'],text=True)
    def save():(capture/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    save();env=dict(os.environ,TMPDIR=str(capture/'tmp'))
    argv=[str(jdk/'bin/javac'),'-J-XX:ActiveProcessorCount=2','-J-Xmx128m','--release','17','-proc:none','-Xlint:all','-Werror','-encoding','UTF-8','-d',str(capture/'classes'),str(capture/'ClassInitProbe.java')]
    result=command(argv,capture,'compile',env,30);record['commands'].append(result);save()
    assert result['exitCode']==0 and result['ownedGroupAbsent'] and not result['timedOut'],capture
    classes={str(p.relative_to(capture/'classes')):sha(p) for p in (capture/'classes').rglob('*.class')}
    assert classes
    for name in classes:
        raw=(capture/'classes'/name).read_bytes();assert raw[:4]==b'\xca\xfe\xba\xbe' and struct.unpack('>HH',raw[4:8])==(0,61)
    record['classesSha256']=classes
    argv=[str(jdk/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx64m','-Djava.awt.headless=true','-Duser.home='+str(capture/'home'),'-Djava.io.tmpdir='+str(capture/'tmp'),'-cp',str(capture/'classes'),'study.host.ClassInitProbe',str(capture/'classes')]
    result=command(argv,capture,'execute',env,15);record['commands'].append(result);save()
    assert result['exitCode']==0 and result['ownedGroupAbsent'] and not result['timedOut'],capture
    rows=[json.loads(line) for line in (capture/'execute.stdout').read_text().splitlines()]
    cases=[r for r in rows if 'case' in r];runtime=[r for r in rows if 'runtimeClass' in r]
    assert len(cases)==19 and len(runtime)==2 and [r['index'] for r in cases]==list(range(19))
    record['cases']=len(cases);record['runtimeClassesSha256']={r['runtimeClass']:r['sha256'] for r in runtime}
    record['observedSha256']=sha(capture/'execute.stdout')
    assert all(sha(capture/n)==d for n,d in record['sourcesSha256'].items())
    assert sha(jdk/'release')==record['jdkReleaseSha256']
    for name,tool in record['tools'].items():assert sha(Path(tool['path']))==tool['sha256']
    save();print(json.dumps(dict(capture=str(capture),java=fields['JAVA_RUNTIME_VERSION'],cases=len(cases),ownedGroupsAbsent=True)))


if __name__=='__main__':main()
