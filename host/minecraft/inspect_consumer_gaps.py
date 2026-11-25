#!/usr/bin/env python3
"""Inspect a selected original 26.3 consumer group as private data."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'java'))
from arena_probe import command
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
MEMBERS = ['com/mojang/blaze3d/font/SpaceProvider',
           'com/mojang/blaze3d/font/SpaceProvider$Definition',
           'net/minecraft/client/renderer/block/BuiltInBlockModels',
           'net/minecraft/client/renderer/block/BuiltInBlockModels$Builder',
           'net/minecraft/client/renderer/block/BuiltInBlockModels$ModelFactory',
           'net/minecraft/client/renderer/block/BuiltInBlockModels$SpecialModelFactory']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['client', 'java', 'decompiler', 'private']:
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--surface', choices=['font-block', 'server-packs'], default='font-block')
    args = p.parse_args()
    target = next(t for t in json.loads((HERE / 'targets.json').read_text())['javaReferences'] if t['release'] == '26.3')
    assert sha(args.client) == target['source']['clientSha256']
    assert sha(args.decompiler) == '1dfcfe974395734fa467ce620661c7623d05ba83670de0529b1fbd63ff548b9d'
    java = args.java.resolve()
    assert 'JAVA_VERSION="25.' in (java.parent.parent / 'release').read_text()
    capture = args.private.resolve() / ('java263-' + args.surface + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    capture.mkdir(parents=True)
    for name in ['classes', 'source', 'tmp', 'home']:
        (capture / name).mkdir()
    for source in [Path(__file__), HERE.parent / 'java/arena_probe.py']:
        shutil.copyfile(source, capture / source.name)
    entries = {}
    with zipfile.ZipFile(args.client) as archive:
        members = MEMBERS if args.surface == 'font-block' else sorted(
            n.removesuffix('.class') for n in archive.namelist()
            if n.startswith('net/minecraft/client/resources/server/') and n.endswith('.class'))
        assert members
        for name in members:
            name += '.class'
            raw = archive.read(name)
            destination = capture / 'classes' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            entries[name] = sha(destination)
    argv = [str(java), '-XX:ActiveProcessorCount=2', '-Xmx256m', '-Djava.awt.headless=true',
            '-Duser.home=' + str(capture / 'home'), '-Djava.io.tmpdir=' + str(capture / 'tmp'), '-jar', str(args.decompiler.resolve()),
            '--folder', '--log-level=WARN', '--add-external=' + str(args.client.resolve()),
            str(capture / 'classes'), str(capture / 'source')]
    result = command(argv, capture, 'inspect', dict(os.environ, TMPDIR=str(capture / 'tmp')), 60)
    receipt = dict(schema=1, target=target['id'], surface=args.surface, clientSha256=sha(args.client),
        toolSha256=sha(args.decompiler), javaSha256=sha(java), jdkReleaseSha256=sha(java.parent.parent / 'release'),
        producerSha256=sha(capture / Path(__file__).name), helperSha256=sha(capture / 'arena_probe.py'),
        selectedClassSha256=entries, viewsSha256={str(p.relative_to(capture / 'source')): sha(p) for p in (capture / 'source').rglob('*.java')},
        command=result, scope='Private bytecode inspection/decompilation only;no original class linking,game or provider execution.')
    (capture / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    assert result['exitCode'] == 0 and result['ownedGroupAbsent'] and not result['timedOut']
    assert sha(args.client) == target['source']['clientSha256']
    (args.private / 'latest-consumer-gaps.json').write_text(json.dumps(dict(capture=str(capture)), indent=2) + '\n')
    print(json.dumps(dict(capture=str(capture), classEntries=len(entries), views=len(receipt['viewsSha256']), exitCode=result['exitCode'], ownedGroupAbsent=result['ownedGroupAbsent'])))


if __name__ == '__main__':
    main()
