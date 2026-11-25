#!/usr/bin/env python3
"""Owner-only original policy-class execution under explicit data/log adapters."""
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
sys.path.insert(0,str(HERE.parents[1]/'java'))
from arena_probe import command
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--jdk',type=Path,required=True);p.add_argument('--artifact',type=Path,required=True);p.add_argument('--private',type=Path,required=True);args=p.parse_args()
    jdk=args.jdk.resolve();fields=dict(re.findall(r'^([A-Z_]+)="([^"]*)"',(jdk/'release').read_text(),re.M));assert fields['JAVA_VERSION'].startswith('21.')
    assert sha(args.artifact)=='7c78b6f425d84a85dc1dcdc6d2d00073fbe16f9de0217325467d9d218a5cd96d'
    capture=args.private.resolve()/('polytone-priority-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));capture.mkdir(parents=True)
    for n in ['src','classes','original','home','tmp']:(capture/n).mkdir()
    sources=[HERE/'PriorityProbe.java',*sorted((HERE/'adapters').glob('*.java')),HERE/'native.py',HERE.parents[1]/'java/arena_probe.py']
    for source in sources:shutil.copyfile(source,capture/'src'/source.name)
    original='net/mehvahdjukaar/polytone/common/Parsed$SortedMap.class';dest=capture/'original'/original;dest.parent.mkdir(parents=True)
    with zipfile.ZipFile(args.artifact) as jar:dest.write_bytes(jar.read(original))
    record=dict(schema=1,scope='One unchanged original Parsed$SortedMap class;Parsed data/isEnabled,opaque ResourceLocation and nonthrowing logger adapters. Not full Polytone/Minecraft.',artifactSha256=sha(args.artifact),classEntry=original,classEntrySha256=sha(dest),sourceSha256={p.name:sha(capture/'src'/p.name) for p in sources},profile={k:fields[k] for k in ['JAVA_VERSION','JAVA_RUNTIME_VERSION','IMPLEMENTOR','OS_NAME','OS_ARCH']},jdkReleaseSha256=sha(jdk/'release'),tools={n:dict(path=str(jdk/'bin'/n),sha256=sha(jdk/'bin'/n)) for n in ['java','javac']},commands=[])
    def save():(capture/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    env=dict(os.environ,HOME=str(capture/'home'),TMPDIR=str(capture/'tmp'));save()
    argv=[str(jdk/'bin/javac'),'-J-XX:ActiveProcessorCount=2','-J-Xmx128m','--release','21','-proc:none','-Xlint:all','-Werror','-d',str(capture/'classes')]+[str(p) for p in sorted((capture/'src').glob('*.java'))]
    r=command(argv,capture,'compile',env,30);record['commands'].append(r);save();assert r['exitCode']==0 and r['ownedGroupAbsent'],capture
    argv=[str(jdk/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx64m','-Djava.awt.headless=true','-Duser.home='+str(capture/'home'),'-Djava.io.tmpdir='+str(capture/'tmp'),'-cp',str(capture/'classes')+os.pathsep+str(capture/'original'),'study.mc.PriorityProbe']
    r=command(argv,capture,'execute',env,15);record['commands'].append(r);record['adapterClassSha256']={str(p.relative_to(capture/'classes')):sha(p) for p in (capture/'classes').rglob('*.class')};save();assert r['exitCode']==0 and r['ownedGroupAbsent'],capture
    observed=json.loads((capture/'execute.stdout').read_text());assert observed['schema']==1 and len(observed['cases'])==48 and observed['originalClassSha256']==record['classEntrySha256']
    assert sha(dest)==record['classEntrySha256'] and all(sha(capture/'src'/n)==d for n,d in record['sourceSha256'].items())
    print(json.dumps(dict(capture=str(capture),cases=len(observed['cases']),ownedGroupAbsent=True)))


if __name__=='__main__':main()
