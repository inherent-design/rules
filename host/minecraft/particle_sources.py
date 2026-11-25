#!/usr/bin/env python3
"""Attribute selected particle definition/provider/admission/render owners; no game export."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from atlas_sources import VIEWS
from mappings import read

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
PARTS = ['net.minecraft.client.particle.' + n for n in ['ParticleDescription', 'ParticleEngine', 'ParticleResources',
    'ParticleGroup', 'QuadParticleGroup', 'NoRenderParticleGroup', 'ItemPickupParticleGroup', 'ElderGuardianParticleGroup',
    'Particle', 'SingleQuadParticle', 'TextureSheetParticle', 'ParticleProvider', 'ParticleRenderType', 'SpriteSet']]
PARTS += ['net.minecraft.core.particles.ParticleGroup', 'net.minecraft.core.particles.ParticleLimit',
          'net.minecraft.client.renderer.texture.TextureAtlasSprite']
PARTS += [prefix + n for prefix in ['net.minecraft.client.renderer.state.', 'net.minecraft.client.renderer.state.level.']
          for n in ['ParticleGroupRenderState', 'ParticlesRenderState', 'QuadParticleRenderState']]
PROVIDER = ['content.particle.custom.CustomParticlesManager', 'content.particle.gpu.GpuParticles', 'content.particle.gpu.GpuParticleRenderer']


def attribute(path, binary, archive):
    member = binary.replace('.', '/') + '.class'
    identities = {n: hashlib.sha256(archive.read(n)).hexdigest() for n in archive.namelist()
                  if n == member or (n.startswith(member[:-6]+'$') and n.endswith('.class'))}
    assert member in identities
    if not path.is_file(): return dict(originalClassesSha256=identities, viewStatus='pending source inspection')
    text = path.read_text()
    return dict(originalClassesSha256=identities, viewSha256=sha(path),
        locators=[dict(line=i, kind='source declaration/call candidate') for i, line in enumerate(text.splitlines(), 1)
                  if any(marker in line for marker in ['"textures"', 'rebind(', 'get(int', 'first(', 'createParticle(', 'void add(', 'boolean add(',
                    'allOf(', 'preparationBarrier', 'clearParticles(', 'onReload', 'EvictingQueue', 'new ArrayDeque',
                    'pendingClose', 'retireAll(', 'void clear(', 'void close(', 'extractRenderState(', 'updateCount(', 'spriteSets.'])])


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--private', type=Path, required=True); p.add_argument('--check', action='store_true'); a = p.parse_args()
    private = a.private.resolve(); targets = json.loads((HERE/'targets.json').read_text())['javaReferences']; rows = []
    for version, oldview in VIEWS.items():
        cap = Path(json.loads((private/('latest-sprite-set-'+version+'.json')).read_text())['capture']); r = json.loads((cap/'receipt.json').read_text())
        argv = r['commands'][1]['argv']; client = Path(argv[argv.index('-cp')+1].split(':')[1]); target = next(t for t in targets if t['release'] == version)
        assert sha(client) == r['clientSha256'] == target['source']['clientSha256'] and r['observerErrors'] == 0
        mapping = None
        if version != '26.3':
            mp = private/(version+'-client-mappings.txt') if version in ['1.21.1','1.21.5'] else next((private/'inputs').glob('java-'+version+'-client_mappings-*.txt'))
            assert sha(mp) == r['mappingSha256']; mapping = read(mp)
        modern = version in ['1.21.11', '26.3']; source = private/oldview
        if modern:
            views = Path(json.loads((private/('latest-particle-views-'+version+'.json')).read_text())['capture']); vr = json.loads((views/'receipt.json').read_text()); source = views/'source'
            assert vr['clientSha256'] == sha(client) and vr['command']['ownedGroupAbsent'] and vr['command']['exitCode'] == 0
            for rel, h in vr['viewsSha256'].items(): assert sha(source/rel) == h
        sources = {}; absent = []
        with zipfile.ZipFile(client) as archive:
            for name in PARTS:
                if (mapping is not None and name not in mapping) or (mapping is None and name.replace('.', '/')+'.class' not in archive.namelist()):
                    absent.append(name); continue
                sources[name] = attribute(source/(name.replace('.', '/')+'.java'), mapping[name]['name'] if mapping else name, archive)
        owner = 'ParticleResources' if modern else 'ParticleEngine'
        ownerText = (source/('net/minecraft/client/particle/'+owner+'.java')).read_text()
        assert 'ImmutableList.copyOf' in ownerText and 'rebind(' in ownerText
        rows.append(dict(target=target['id'], clientSha256=sha(client), mappingSha256=r['mappingSha256'], sources=sources,
            absentCandidateNames=absent, resourcesOwner=owner, renderStateNamespace='level' if version == '26.3' else 'renderer.state' if modern else 'direct engine rendering',
            queueInterpretation='probabilistic tail admission plus hard capacity,with rejected pending-count compensation' if version == '26.3' else 'EvictingQueue with capacity16384; eviction/count ownership still needs qualification',
            helperFirstAvailable=modern, limits=['Absent selected class names do not prove absence of equivalent features under another owner.', 'Source candidates are not complete consumer closure or verified decompilation.']))
    pc = private/'polytone-views-20261125T045755602461Z'; pr = json.loads((pc/'receipt.json').read_text()); artifact = Path(pr['argv'][-2])
    assert sha(artifact) == pr['inputSha256'] == json.loads((HERE/'polytone-lifecycles.json').read_text())['artifactSha256']
    provider = {}
    with zipfile.ZipFile(artifact) as archive:
        for part in PROVIDER:
            name = 'net.mehvahdjukaar.polytone.'+part; rel = name.replace('.', '/')+'.java'; path = pc/'source'/rel
            assert sha(path) == pr['viewsSha256'][rel]; provider[name] = attribute(path, name, archive)
    result = dict(schema=1, status='partial source ownership map plus bounded original sprite-set helper comparisons', targets=rows,
        polytone=dict(artifactSha256=sha(artifact), sources=provider),
        typedEdges=[dict(source='definition', target='registered sprite set', relation='lookup/admission;unregistered definition can be ignored before its reader opens'),
                    dict(source='particle provider', target='mutable sprite set', relation='retained reference;rebind changes the captured set contents'),
                    dict(source='reload apply', target='particle queues and sprite sets', relation='ordered effects;not global rollback or physical/device retirement'),
                    dict(source='particle engine', target='group/render state', relation='queue admission,live counts and extracted frame state are separate'),
                    dict(source='Polytone active GPU renderer', target='pending-close renderer', relation='retirement request;later render calls close;native completion remains separate')],
        limits=['No full resource parser/provider/atlas/GPU/game execution. Original helpers operate only on constructor-bypassed identity tokens.',
                'Sprite get math is compared in bounded nonoverflow ranges;no PRNG or full animation timing proof.',
                'Queue policies and reload/source effects are source interpretation,not native engine or memory measurements.',
                'Provider coexistence,custom renderer fidelity,Windows/Linux/native backend and independent Bedrock comparisons remain pending.'])
    dest = HERE/'particle-sources.json'
    if a.check: assert json.loads(dest.read_text()) == result
    else: dest.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(targets=5, inspectedJavaViews=sum('viewSha256'in s for r in rows for s in r['sources'].values()), pendingJavaViews=sum('viewStatus'in s for r in rows for s in r['sources'].values()), providerViews=len(provider), checked=a.check)))


if __name__ == '__main__': main()
