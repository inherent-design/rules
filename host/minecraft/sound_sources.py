#!/usr/bin/env python3
"""Attribute sound definition/consumer inspection; exports identities, not game source."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile
from atlas_sources import VIEWS
from mappings import read

HERE = Path(__file__).resolve().parent
PARTS = ['net/minecraft/client/sounds/' + n for n in
         ['WeighedSoundEvents', 'Weighted', 'SoundManager', 'SoundEngine', 'SoundBufferLibrary', 'ChannelAccess', 'SoundEngineExecutor']]
PARTS += ['net/minecraft/client/resources/sounds/' + n for n in ['Sound', 'SoundEventRegistration', 'SoundEventRegistrationSerializer']]
PARTS += ['com/mojang/blaze3d/audio/' + n for n in ['Library', 'Channel', 'SoundBuffer']]
PROVIDER = ['content/sound/SoundTypesManager', 'content/sound/PolytoneSoundType', 'common/codec/CodecUtils',
            'common/codec/ForwardAwareByNameCodec', 'Polytone']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def attribute(path, binary, archive):
    member = binary.replace('.', '/') + '.class'
    entries = {n: hashlib.sha256(archive.read(n)).hexdigest() for n in archive.namelist()
               if n == member or (n.startswith(member[:-6] + '$') and n.endswith('.class'))}
    assert member in entries, member
    if not path.is_file():
        return dict(originalClassesSha256=entries, viewStatus='pending inspection; class identity alone is not source review')
    text = path.read_text()
    return dict(viewSha256=sha(path), originalClassesSha256=entries,
                fieldCandidates=[dict(field=m[1], line=text[:m.start()].count('\n') + 1)
                                 for m in re.finditer(r'"(replace|subtitle|sounds|name|type|volume|pitch|weight|preload|stream|attenuation_distance|break_sound|step_sound|place_sound|hit_sound|fall_sound)"', text)],
                consumerLocators=[dict(line=i, kind='source call/declaration candidate') for i, line in enumerate(text.splitlines(), 1)
                                  if any(s in line for s in ['getWeight(', 'getSound(', 'preload(', 'preloadIfRequired(', 'void clear(',
                                                            'thenAccept(', 'thenRun(', 'release(', 'registry.get(', 'registry.put(',
                                                            'registerDynamic(', 'unregisterDynamic(', 'isFutureId(', 'loadFutureIds('])])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--private', type=Path, required=True)
    p.add_argument('--check', action='store_true')
    a = p.parse_args(); private = a.private.resolve(); rows = []
    targets = json.loads((HERE / 'targets.json').read_text())['javaReferences']
    for v, view in VIEWS.items():
        capture = Path(json.loads((private / ('latest-sound-' + v + '.json')).read_text())['capture'])
        receipt = json.loads((capture / 'receipt.json').read_text())
        assert receipt['observerErrors'] == 0 and receipt['bootstrapContext'] is True
        argv = receipt['commands'][1]['argv']; client = Path(argv[argv.index('-cp') + 1].split(':')[1])
        target = next(t for t in targets if t['release'] == v)
        assert sha(client) == receipt['clientSha256'] == target['source']['clientSha256']
        mapping = None
        if v != '26.3':
            mp = private / (v + '-client-mappings.txt') if v in ['1.21.1', '1.21.5'] else next((private / 'inputs').glob('java-' + v + '-client_mappings-*.txt'))
            assert sha(mp) == receipt['mappingSha256']; mapping = read(mp)
        source = private / view
        if v == '26.3':
            source = private / 'java263-sound-contracts-20261125T131239619710Z/source'
        with zipfile.ZipFile(client) as archive:
            sources = {part + '.java': attribute(source / (part + '.java'), mapping[part.replace('/', '.')]['name'] if mapping else part.replace('/', '.'), archive) for part in PARTS}
        rows.append(dict(target=target['id'], clientSha256=sha(client), mappingSha256=receipt['mappingSha256'], sources=sources))
    views = private / 'polytone-views-20261125T045755602461Z'
    pr = json.loads((views / 'receipt.json').read_text()); artifact = Path(pr['argv'][-2])
    assert sha(artifact) == pr['inputSha256'] == json.loads((HERE / 'polytone-lifecycles.json').read_text())['artifactSha256']
    prefix = 'net/mehvahdjukaar/polytone/'
    with zipfile.ZipFile(artifact) as archive:
        provider = {prefix + part + '.java': attribute(views / 'source' / (prefix + part + '.java'), (prefix + part).replace('/', '.'), archive) for part in PROVIDER}
        for rel, entry in provider.items(): assert entry['viewSha256'] == pr['viewsSha256'][rel]
        future = archive.read('future_ids.txt')
    result = dict(schema=1, status='source inspection and bounded original-method comparisons; not audio/provider qualification',
                  targets=rows, polytone=dict(artifactSha256=sha(artifact), sources=provider,
                                             futureIdsSha256=hashlib.sha256(future).hexdigest(), futureIdsMeaning='Bundled future-version ID set, not pending dynamic registrations or live resolution.'),
                  obligations=[
                      'Preserve raw numeric input, library conversion, signed word, individual positivity and aggregate bound as separate facts.',
                      'Indirect events capture a preparation registry; public registry replacement does not identify all retained consumers.',
                      'Resource presence, decoder admission, device initialization, preload completion, channel admission and audible playback require separate evidence.',
                      'Buffer cache clear attaches disposal continuations and clears the map; it is not an all-futures completion acknowledgement.',
                      'Polytone dynamic event IDs, sound types, sounds.json entries, audio bytes and server authority are different domains.'
                  ], limits=[
                      'Field and consumer candidates are locators, not an exhaustive grammar, verified decompilation or inferred effect closure.',
                      'Native evidence uses authored callbacks and recorded original PRNG draws; mutable callbacks are not proved reachable through normal vanilla definitions.',
                      'No audio device, actual Ogg decode, game entrypoint, provider execution, Windows/Linux native playback or Bedrock equivalence.',
                      'Modefite/Compat sound and resource-admission overlap remain pending; absence of a dedicated hook is not proof of no effects.'
                  ])
    dest = HERE / 'sound-sources.json'
    if a.check: assert json.loads(dest.read_text()) == result
    else: dest.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(targets=5, javaViews=sum('viewSha256' in s for r in rows for s in r['sources'].values()),
                          pendingJavaViews=sum('viewStatus' in s for r in rows for s in r['sources'].values()), providerViews=len(provider), checked=a.check)))


if __name__ == '__main__': main()
