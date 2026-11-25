#!/usr/bin/env python3
"""Create a bounded private mapped inspection slice; never execute game classes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import zipfile
from mappings import read as read_mappings

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'java'))
from arena_probe import command
sha = lambda p, kind='sha256': hashlib.new(kind, p.read_bytes()).hexdigest()
PREFIXES = ['net.minecraft.server.packs.', 'net.minecraft.client.resources.',
    'net.minecraft.client.renderer.block.model.', 'net.minecraft.client.renderer.item.',
    'net.minecraft.client.renderer.texture.', 'net.minecraft.client.renderer.special.',
    'net.minecraft.client.color.', 'net.minecraft.client.gui.font.', 'com.mojang.blaze3d.font.',
    'com.mojang.blaze3d.pipeline.', 'net.minecraft.client.renderer.ShaderManager',
    'net.minecraft.client.renderer.Post', 'net.minecraft.client.particle.ParticleDescription',
    'net.minecraft.client.particle.ParticleEngine', 'net.minecraft.client.sounds.',
    'com.mojang.blaze3d.audio.', 'net.minecraft.client.renderer.RenderPipelines']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ['client', 'mappings', 'metadata', 'jdk', 'art', 'decompiler', 'private']:
        p.add_argument('--' + key, type=Path, required=True)
    args = p.parse_args()
    target = next(t for t in json.loads((HERE / 'targets.json').read_text())['javaReferences'] if t['release'] == '1.21.11')
    assert sha(args.client) == target['source']['clientSha256'] and sha(args.metadata) == target['source']['metadataSha256']
    metadata = json.loads(args.metadata.read_text())
    expected = metadata['downloads']['client_mappings']
    assert sha(args.mappings, 'sha1') == expected['sha1'] and args.mappings.stat().st_size == expected['size']
    assert sha(args.art) == '43fcb978664ba04fc0b3b1b1a14eccabb4bc87b7a415e0eb8bdd1c2f12324321'
    assert sha(args.decompiler) == '1dfcfe974395734fa467ce620661c7623d05ba83670de0529b1fbd63ff548b9d'
    jdk = args.jdk.resolve()
    fields = dict(re.findall(r'^([A-Z_]+)="([^"]*)"', (jdk / 'release').read_text(), re.M))
    assert fields['JAVA_VERSION'].startswith('21.')
    mappings = read_mappings(args.mappings)
    selected = {n: m for n, m in mappings.items() if any(n.startswith(prefix) for prefix in PREFIXES)}
    assert 300 <= len(selected) <= 1200
    capture = args.private.resolve() / ('java12111-views-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    capture.mkdir(parents=True)
    for name in ['classes', 'source', 'tmp', 'home']:
        (capture / name).mkdir()
    for source in [Path(__file__), HERE / 'mappings.py', HERE.parent / 'java/arena_probe.py']:
        shutil.copyfile(source, capture / source.name)
    with zipfile.ZipFile(args.client) as archive:
        original = {name: dict(member=m['name'].replace('.', '/') + '.class', sha256=hashlib.sha256(archive.read(m['name'].replace('.', '/') + '.class')).hexdigest()) for name, m in selected.items()}
    record = dict(schema=1, target=target['id'], clientSha256=sha(args.client), metadataSha256=sha(args.metadata),
        mappingSha256=sha(args.mappings), mappingSha1=expected['sha1'], prefixes=PREFIXES,
        profile={k: fields[k] for k in ['JAVA_VERSION', 'JAVA_RUNTIME_VERSION', 'IMPLEMENTOR', 'OS_NAME', 'OS_ARCH']},
        jdkReleaseSha256=sha(jdk / 'release'), javaSha256=sha(jdk / 'bin/java'), artSha256=sha(args.art), decompilerSha256=sha(args.decompiler),
        producersSha256={n: sha(capture / n) for n in ['inspect_java12111.py', 'mappings.py', 'arena_probe.py']},
        originalClassMembers=original, commands=[], scope='Mapped/decompiled source inspection only;no original or transformed game class execution.')
    def save():
        (capture / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
    save()
    env = dict(os.environ, HOME=str(capture / 'home'), TMPDIR=str(capture / 'tmp'))
    common = [str(jdk / 'bin/java'), '-XX:ActiveProcessorCount=2', '-Xmx512m', '-Djava.awt.headless=true',
              '-Duser.home=' + str(capture / 'home'), '-Djava.io.tmpdir=' + str(capture / 'tmp')]
    mapped = capture / 'mapped.jar'
    argv = common + ['-jar', str(args.art.resolve()), '--input', str(args.client.resolve()), '--output', str(mapped),
                     '--names', str(args.mappings.resolve()), '--reverse', '--threads', '2']
    r = command(argv, capture, 'remap', env, 120)
    record['commands'].append(r); save()
    assert r['exitCode'] == 0 and r['ownedGroupAbsent'] and not r['timedOut'], capture
    record['mappedJarSha256'] = sha(mapped)
    renamed = {}
    with zipfile.ZipFile(mapped) as archive:
        for name in selected:
            member = name.replace('.', '/') + '.class'
            raw = archive.read(member)
            destination = capture / 'classes' / member
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            renamed[member] = sha(destination)
    record['mappedClassMembersSha256'] = renamed; save()
    argv = common + ['-jar', str(args.decompiler.resolve()), '--folder', '--log-level=WARN',
                     '--add-external=' + str(mapped), str(capture / 'classes'), str(capture / 'source')]
    r = command(argv, capture, 'inspect', env, 120)
    record['commands'].append(r)
    record['viewsSha256'] = {str(p.relative_to(capture / 'source')): sha(p) for p in (capture / 'source').rglob('*.java')}
    record['limits'] = ['Renaming/decompilation is not a proved semantics-preserving transformation.',
        'Missing external inheritance/library warnings remain in raw logs;no native equivalence is inferred.',
        'The selected prefixes are a resource/graphics inspection slice,not the complete runtime/consumer closure.',
        'Heap512MiB/activeprocessors2 are JVM settings,not physical-memory or host-wide bounds.',
        'Original/mapped artifacts and inspection text stay private. No game,provider,account,world or renderer launched.']
    save()
    assert r['exitCode'] == 0 and r['ownedGroupAbsent'] and not r['timedOut'], capture
    assert sha(args.client) == record['clientSha256'] and sha(args.mappings) == record['mappingSha256']
    assert all(sha(capture / n) == d for n, d in record['producersSha256'].items())
    (args.private / 'latest-java12111-views.json').write_text(json.dumps(dict(capture=str(capture)), indent=2) + '\n')
    print(json.dumps(dict(capture=str(capture), selectedClasses=len(selected), views=len(record['viewsSha256']), ownedGroupsAbsent=all(c['ownedGroupAbsent'] for c in record['commands']))))


if __name__ == '__main__':
    main()
