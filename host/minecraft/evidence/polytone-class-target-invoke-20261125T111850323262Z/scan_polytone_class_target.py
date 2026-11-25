#!/usr/bin/env python3
"""Inspect one original provider class with the retained Java25 class-file scanner."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'java'))
from arena_probe import command
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['artifact','scanner','jdk','private']:p.add_argument('--'+n,type=Path,required=True)
    args=p.parse_args();jdk=args.jdk.resolve();assert 'JAVA_VERSION="25.' in (jdk/'release').read_text()
    managers=json.loads((HERE/'polytone-managers.json').read_text())
    selected=next(m for m in managers['managers'] if m['id']=='polytone.slotify')
    assert sha(args.artifact)==managers['artifactSha256']
    prior=json.loads((args.scanner/'receipt.json').read_text());member=selected['className'].replace('.','/')+'.class'
    scanner=args.scanner/'classes/study/host/HostApiScan.class'
    assert sha(scanner)==prior['classSha256']
    assert sha(args.scanner/'HostApiScan.java')==prior['sourcesSha256']['HostApiScan.java']==sha(HERE/'HostApiScan.java')
    capture=args.private.resolve()/('polytone-class-target-invoke-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    capture.mkdir(parents=True)
    for n in ['classes/study/host','tmp','home']:(capture/n).mkdir(parents=True)
    for source in [Path(__file__),HERE/'HostApiScan.java',HERE.parent/'java/arena_probe.py']:shutil.copyfile(source,capture/source.name)
    shutil.copyfile(scanner,capture/'classes/study/host/HostApiScan.class')
    with zipfile.ZipFile(args.artifact) as archive:raw=archive.read(member)
    assert hashlib.sha256(raw).hexdigest()==selected['classEntrySha256']
    selected_jar=capture/'selected-original-class.jar'
    with zipfile.ZipFile(selected_jar,'w',compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(zipfile.ZipInfo(member,date_time=(1980,1,1,0,0,0)),raw)
    record=dict(schema=1,scope='Static instruction inspection of one unchanged original Polytone class. No provider/game class definition, linking, initialization or execution.',
        provider=managers['provider'],artifactSha256=sha(args.artifact),originalClassEntry=member,originalClassSha256=selected['classEntrySha256'],selectedJarSha256=sha(selected_jar),
        scannerReceiptSha256=sha(args.scanner/'receipt.json'),scannerClassSha256=sha(scanner),javaSha256=sha(jdk/'bin/java'),jdkReleaseSha256=sha(jdk/'release'),
        sourceSha256={n:sha(capture/n) for n in ['scan_polytone_class_target.py','HostApiScan.java','arena_probe.py']})
    argv=[str(jdk/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx64m','-Djava.awt.headless=true','-Duser.home='+str(capture/'home'),'-Djava.io.tmpdir='+str(capture/'tmp'),'-cp',str(capture/'classes'),'study.host.HostApiScan',str(selected_jar)]
    record['command']=command(argv,capture,'inspect',dict(os.environ,TMPDIR=str(capture/'tmp')),15)
    (capture/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    assert record['command']['exitCode']==0 and record['command']['ownedGroupAbsent'] and not record['command']['timedOut']
    facts=[json.loads(l) for l in (capture/'inspect.stdout').read_text().splitlines()]
    classes=[f for f in facts if f['kind']=='class'];assert len(classes)==1 and classes[0]['sha256']==selected['classEntrySha256']
    calls=[f for f in facts if f['kind']=='invoke' and f['owner']=='java/lang/Class' and f['name']=='forName']
    assert len(calls)==1 and calls[0]['opcode']=='INVOKESTATIC' and calls[0]['type']=='(Ljava/lang/String;)Ljava/lang/Class;' and calls[0]['method']=='parseWithLevel'
    assert sha(args.artifact)==record['artifactSha256'] and all(sha(capture/n)==d for n,d in record['sourceSha256'].items())
    destination=HERE/'evidence'/capture.name;destination.mkdir()
    for n in [*record['sourceSha256'],'inspect.stdout','inspect.stderr']:shutil.copyfile(capture/n,destination/n)
    public=dict(record,privateReceiptSha256=sha(capture/'receipt.json'))
    public['command']={k:v for k,v in record['command'].items() if k!='argv'}|dict(argvDisclosure='Exact argv stays private;frozen authored collector constructs it.')
    public['confirmedClassForNameCalls']=calls
    public['limits']=['Direct invoke instruction,not whole-program reachability,applied mixins,reflection targets or initialized classes.',
        'Scanner runs on Java25 independently of the provider runtime;original class bytes and selected JAR remain private.',
        'The original one-argument overload is verified;the supplied resource target and its effects still need their actual consumer context.']
    (destination/'receipt.json').write_text(json.dumps(public,indent=2)+'\n')
    print(json.dumps(dict(capture=str(capture),originalClasses=1,confirmedCalls=len(calls),ownedGroupAbsent=True)))


if __name__=='__main__':main()
