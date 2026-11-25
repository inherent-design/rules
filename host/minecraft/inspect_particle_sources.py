#!/usr/bin/env python3
"""Private later particle consumer slices, using existing pinned original/named inputs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile
from mappings import read

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'java'))
from arena_probe import command
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ROOTS = ['net.minecraft.client.particle.' + n for n in ['ParticleDescription', 'ParticleEngine', 'ParticleResources',
    'ParticleGroup', 'ParticleProvider', 'ParticleRenderType', 'QuadParticleGroup', 'NoRenderParticleGroup',
    'ItemPickupParticleGroup', 'ElderGuardianParticleGroup', 'Particle', 'SingleQuadParticle', 'TrackingEmitter']]
ROOTS += ['net.minecraft.core.particles.ParticleLimit', 'net.minecraft.client.renderer.texture.TextureAtlasSprite']
ROOTS += ['net.minecraft.client.renderer.state.level.' + n for n in
          ['ParticleGroupRenderState', 'ParticlesRenderState', 'QuadParticleRenderState']]
ROOTS += ['net.minecraft.client.renderer.state.' + n for n in
          ['ParticleGroupRenderState', 'ParticlesRenderState', 'QuadParticleRenderState']]
ROOTS += ['net.minecraft.client.renderer.texture.UvMapping']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', choices=['1.21.11', '26.3'], required=True)
    for name in ['client', 'jdk', 'decompiler', 'private']:
        p.add_argument('--' + name, type=Path, required=True)
    for name in ['mapped', 'mapped-receipt', 'mappings']:
        p.add_argument('--' + name, type=Path)
    a = p.parse_args(); target = next(t for t in json.loads((HERE / 'targets.json').read_text())['javaReferences'] if t['release'] == a.version)
    assert sha(a.client) == target['source']['clientSha256']
    assert sha(a.decompiler) == '1dfcfe974395734fa467ce620661c7623d05ba83670de0529b1fbd63ff548b9d'
    jdk = a.jdk.resolve(); assert 'JAVA_VERSION="25.' in (jdk / 'release').read_text()
    if a.version == '26.3':
        assert a.mapped is None and a.mapped_receipt is None and a.mappings is None
        named = a.client; mapping = None
    else:
        assert a.mapped and a.mapped_receipt and a.mappings
        r = json.loads(a.mapped_receipt.read_text())
        assert r['clientSha256'] == sha(a.client) and r['mappedJarSha256'] == sha(a.mapped) and r['mappingSha256'] == sha(a.mappings)
        named = a.mapped; mapping = read(a.mappings)
    cap = a.private.resolve() / ('particle-views-' + a.version + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    cap.mkdir(parents=True)
    for n in ['classes', 'source', 'tmp', 'home']:
        (cap / n).mkdir()
    for src in [Path(__file__), HERE / 'mappings.py', HERE.parent / 'java/arena_probe.py']:
        shutil.copyfile(src, cap / src.name)
    original = {}; transformed = {}
    with zipfile.ZipFile(a.client) as source, zipfile.ZipFile(named) as archive:
        for member in archive.namelist():
            if not member.endswith('.class'):
                continue
            name = member[:-6].replace('/', '.')
            if not any(name == root or name.startswith(root + '$') for root in ROOTS):
                continue
            binary = mapping[name]['name'].replace('.', '/') + '.class' if mapping else member
            original[name] = dict(member=binary, sha256=hashlib.sha256(source.read(binary)).hexdigest())
            raw = archive.read(member); path = cap / 'classes' / member; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
            transformed[member] = sha(path)
    missing = [root for root in ROOTS if root not in original]
    assert all(root in original for root in ['net.minecraft.client.particle.ParticleResources',
        'net.minecraft.client.particle.ParticleEngine', 'net.minecraft.client.renderer.texture.TextureAtlasSprite'])
    argv = [str(jdk / 'bin/java'), '-XX:ActiveProcessorCount=2', '-Xmx256m', '-Djava.awt.headless=true',
            '-Duser.home=' + str(cap / 'home'), '-Djava.io.tmpdir=' + str(cap / 'tmp'), '-jar', str(a.decompiler.resolve()),
            '--folder', '--log-level=WARN', '--add-external=' + str(named.resolve()), str(cap / 'classes'), str(cap / 'source')]
    result = command(argv, cap, 'inspect', dict(os.environ, TMPDIR=str(cap / 'tmp')), 60)
    receipt = dict(schema=1, target=target['id'], clientSha256=sha(a.client), namedJarSha256=sha(named),
        mappingSha256=sha(a.mappings) if mapping else None, parentReceiptSha256=sha(a.mapped_receipt) if mapping else None,
        toolSha256=sha(a.decompiler), javaSha256=sha(jdk / 'bin/java'), jdkReleaseSha256=sha(jdk / 'release'),
        producersSha256={n: sha(cap / n) for n in ['inspect_particle_sources.py', 'mappings.py', 'arena_probe.py']},
        originalClassMembers=original, absentCandidateClassNames=missing, inspectionClassSha256=transformed,
        viewsSha256={str(p.relative_to(cap / 'source')): sha(p) for p in (cap / 'source').rglob('*.java')}, command=result,
        limits=['Renaming/decompilation is not a verified semantics-preserving transformation.',
                'Existing inputs only;no download,remap,game/provider/native renderer execution. Original class bytes and views remain private.'])
    (cap / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    assert result['exitCode'] == 0 and result['ownedGroupAbsent'] and not result['timedOut']
    assert sha(a.client) == target['source']['clientSha256']
    (a.private / ('latest-particle-views-' + a.version + '.json')).write_text(json.dumps(dict(capture=str(cap))) + '\n')
    print(json.dumps(dict(capture=str(cap), classes=len(original), views=len(receipt['viewsSha256']), groupAbsent=True)))


if __name__ == '__main__': main()
