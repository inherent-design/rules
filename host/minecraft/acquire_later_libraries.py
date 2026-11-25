#!/usr/bin/env python3
"""Acquire exact selected Java-only 26.3 codec dependencies, never native payloads."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import urllib.request
import uuid
import zipfile

HERE=Path(__file__).resolve().parent
sha=lambda p,kind='sha256':hashlib.new(kind,p.read_bytes()).hexdigest()
WANTED={'com.google.code.gson:gson','com.google.guava:failureaccess','com.google.guava:guava','com.mojang:datafixerupper','com.mojang:logging','it.unimi.dsi:fastutil','org.apache.logging.log4j:log4j-api','org.apache.logging.log4j:log4j-core','org.apache.logging.log4j:log4j-slf4j2-impl','org.joml:joml','org.slf4j:slf4j-api'}
WANTED.update({'org.apache.commons:commons-lang3','commons-io:commons-io','com.mojang:authlib'})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--metadata',type=Path,required=True);p.add_argument('--private',type=Path,required=True);p.add_argument('--include-netty-java',action='store_true');args=p.parse_args()
    target=next(t for t in json.loads((HERE/'targets.json').read_text())['javaReferences'] if t['release']=='26.3')
    assert sha(args.metadata)==target['source']['metadataSha256'];meta=json.loads(args.metadata.read_text())
    private=args.private.resolve();private.mkdir(parents=True,exist_ok=True);rows=[]
    wanted=set(WANTED)
    if args.include_netty_java:wanted.update(':'.join(l['name'].split(':')[:2]) for l in meta['libraries'] if l['name'].startswith('io.netty:') and len(l['name'].split(':'))==3)
    selected=[l for l in meta['libraries'] if ':'.join(l['name'].split(':')[:2]) in wanted and len(l['name'].split(':'))==3];assert {':'.join(l['name'].split(':')[:2]) for l in selected}==wanted and len(selected)==len(wanted)
    for library in selected:
        assert len(library['name'].split(':'))==3 and not library.get('rules'),'No native/classified/conditional artifact selected'
        a=library['downloads']['artifact'];destination=(private/a['path']).resolve();assert destination.is_relative_to(private)
        assert a['url'].startswith('https://libraries.minecraft.net/')
        destination.parent.mkdir(parents=True,exist_ok=True);origin='verified-existing-project-cache'
        if not destination.exists():
            temporary=destination.with_name(destination.name+'.part-'+uuid.uuid4().hex)
            with urllib.request.urlopen(a['url'],timeout=30) as response,temporary.open('xb') as out:
                while chunk:=response.read(65536):out.write(chunk)
            assert temporary.stat().st_size==a['size'] and sha(temporary,'sha1')==a['sha1'],temporary
            # Link publishes without overwriting another admitted writer's input.
            try:os.link(temporary,destination)
            except FileExistsError:pass
            assert destination.stat().st_size==a['size'] and sha(destination,'sha1')==a['sha1']
            temporary.unlink();origin='official-metadata-url'
        assert destination.stat().st_size==a['size'] and sha(destination,'sha1')==a['sha1']
        with zipfile.ZipFile(destination) as archive:assert not any(n.lower().endswith(('.so','.dll','.dylib','.jnilib','.a')) for n in archive.namelist()),'Native payload in selected Java artifact'
        rows.append(dict(name=library['name'],path=str(destination),url=a['url'],sha1=a['sha1'],sha256=sha(destination),bytes=a['size'],origin=origin))
    receipt=dict(schema=1,capturedAt=datetime.now(timezone.utc).isoformat(),target=target['id'],metadataSha256=sha(args.metadata),producerSha256=sha(Path(__file__)),libraries=rows,scope='Exact selected Java-only codec/math/logging dependencies;not full launcher classpath or loaded native/backend qualification.')
    (private/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(private=str(private),libraries=len(rows),bytes=sum(r['bytes'] for r in rows))))


if __name__=='__main__':main()
