#!/usr/bin/env python3
"""Owner-run Java 25 native-memory scope witness;outside ordinary CI."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def command(argv,capture,name,env,timeout):
    start=time.monotonic()
    with (capture/(name+'.stdout')).open('wb') as out,(capture/(name+'.stderr')).open('wb') as err:
        p=subprocess.Popen(argv,cwd=capture,env=env,stdout=out,stderr=err,start_new_session=True)
        expired=False
        try:code=p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            expired=True;os.killpg(p.pid,signal.SIGKILL);code=p.wait()
    try:os.killpg(p.pid,0);absent=False
    except ProcessLookupError:absent=True
    return dict(argv=argv,exitCode=code,timedOut=expired,ownedGroupAbsent=absent,elapsedSeconds=time.monotonic()-start,stdoutSha256=sha(capture/(name+'.stdout')),stderrSha256=sha(capture/(name+'.stderr')))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--jdk',type=Path,required=True);parser.add_argument('--private',type=Path,required=True);args=parser.parse_args()
    jdk=args.jdk.resolve();release=(jdk/'release').read_text();fields=dict(re.findall(r'^([A-Z_]+)="([^"]*)"',release,re.M))
    assert fields['JAVA_VERSION'].startswith('25.'),'This witness selects an actual JDK25,not PATH java'
    capture=args.private.resolve()/('java25-arena-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));capture.mkdir(parents=True)
    for name in ['classes','home','tmp']:(capture/name).mkdir()
    for name in ['ArenaProbe.java','arena_probe.py']:shutil.copyfile(HERE/name,capture/name)
    record=dict(schema=1,scope='Java25 Arena confined/shared segment access and sequential close;no game,GPU,FFI,raw-address or concurrent-close claim.',profile={k:fields[k] for k in ['JAVA_VERSION','JAVA_RUNTIME_VERSION','IMPLEMENTOR','OS_NAME','OS_ARCH']},jdkReleaseSha256=sha(jdk/'release'),tools={name:dict(path=str(jdk/'bin'/name),sha256=sha(jdk/'bin'/name)) for name in ['java','javac']},sourceSha256={name:sha(capture/name) for name in ['ArenaProbe.java','arena_probe.py']},commands=[])
    if fields['OS_NAME']=='Darwin':record['host']=subprocess.check_output(['sw_vers'],text=True)
    env=dict(os.environ,HOME=str(capture/'home'),TMPDIR=str(capture/'tmp'))
    def save():(capture/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    compile_args=[str(jdk/'bin/javac'),'-J-XX:ActiveProcessorCount=2','-J-Xmx128m','--release','25','-proc:none','-Xlint:all','-Werror','-encoding','UTF-8','-d',str(capture/'classes'),str(capture/'ArenaProbe.java')]
    result=command(compile_args,capture,'compile',env,30);record['commands'].append(result);save();assert result['exitCode']==0 and result['ownedGroupAbsent'],capture
    execute_args=[str(jdk/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx64m','-Djava.awt.headless=true','-Duser.home='+str(capture/'home'),'-Djava.io.tmpdir='+str(capture/'tmp'),'-cp',str(capture/'classes'),'study.host.ArenaProbe']
    result=command(execute_args,capture,'execute',env,15);record['commands'].append(result);record['classSha256']=sha(capture/'classes/study/host/ArenaProbe.class');save()
    assert result['exitCode']==0 and result['ownedGroupAbsent'],capture
    observed=json.loads((capture/'execute.stdout').read_text());assert observed['schema']==1 and len(observed['events'])==11
    assert all(sha(capture/name)==digest for name,digest in record['sourceSha256'].items()) and sha(jdk/'release')==record['jdkReleaseSha256']
    print(json.dumps(dict(capture=str(capture),events=len(observed['events']),exitCode=result['exitCode'],ownedGroupAbsent=result['ownedGroupAbsent'])))


if __name__=='__main__':main()
