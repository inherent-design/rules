#!/usr/bin/env python3
"""Owner-run attribution of interpreted documentation rules, not a schema parser."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
REVISION = '80b7b1713df821debb4a8022e32e6b0ad840a273'
CLAIMS = [
    ('texture-layer-validity', 'texture-sets.md', '## Invalid *.texture_set.json',
     'Require color and keep the normal/height and MER/MERS alternatives exclusive.'),
    ('pack-local-reference', 'texture-sets.md', '## Resource Stack Behavior',
     'Image backing belongs to the defining pack, independently of other packs\' image priority.'),
    ('extension-precedence', 'texture-sets.md', '## Referencing Texture Resources',
     'For duplicate eligible image names, prefer TGA, then PNG, JPG, and JPEG.'),
    ('eligible-definition-replacement', 'texture-sets.md', '## Resource Stack Behavior',
     'Selected definitions replace rather than merge. Invalid-candidate fallback remains unresolved.'),
    ('channel-declarations', 'texture-sets.md', '## Invalid *.texture_set.json',
     'Image and uniform layers have different declared channel counts.'),
    ('consumer-and-variation', 'texture-sets.md', '### Heightmap',
     'Vibrant texture objects restrict heightmaps; uniform MERS has a separate variation limit.'),
    ('mers-component-choice', 'texture-sets.md', '### Metalness_emissive_roughness_subsurface',
     'The larger metal/subsurface channel wins; ties favor subsurface.'),
    ('vibrant-declaration-prerequisite', 'vibrant-packs.md', '# Vibrant Visuals Resource Packs',
     'PBR authoring-floor guidance and the raytraced alternative are independent evidence, preceding runtime/device qualification.'),
]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    args = p.parse_args()
    capture = args.capture.resolve()
    r = json.loads((capture / 'receipt.json').read_text())
    assert r['commit'] == REVISION
    assert sha((capture / 'acquire_texture_docs.py').read_bytes()) == r['producerSha256']
    sources = []
    bodies = {}
    for s in r['files']:
        raw = (capture / s['file']).read_bytes()
        assert sha(raw) == s['sha256'] and len(raw) == s['bytes']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == s['gitBlob']
        bodies[s['file']] = raw.decode()
        sources.append(dict(id=s['file'], **s, repository=r['repository'], commit=r['commit'], kind='documentation'))
    claims = []
    for id, source, heading, meaning in CLAIMS:
        assert heading in bodies[source], (source, heading)
        claims.append(dict(id=id, source=source, section=heading, interpretation=meaning,
                           status='source-interpreted; native comparison absent'))
    # A variation condition is in a different subsection than the heightmap rule.
    claims[5]['additionalSection'] = '## Specifying uniform values'
    assert claims[5]['additionalSection'] in bodies['texture-sets.md']
    catalog = json.loads((HERE / 'catalog.json').read_text())
    previous = [s for s in catalog['sources'] if s['path'] == 'metadata/doc_modules/texture-sets.json']
    assert len(previous) == 3
    for s in previous:
        raw = (ROOT / '.build/minecraft/bedrock-sources/blobs' / (s['gitBlob'] + '.blob')).read_bytes()
        assert sha(raw) == s['sha256']
        sources.append(dict(s, kind='selected-sample-doc-module'))
    result = dict(schema=1, edition='bedrock', documentationRevision=REVISION,
                  acquisitionReceiptSha256=sha((capture / 'receipt.json').read_bytes()), sources=sources,
                  claims=claims, researchPolicy=dict(id='research-evidence-policy',
                    interpretation='Missing and unmeasured backing are distinct; accumulate scoped issues without inventing an engine diagnostic order.'),
                  limits=['The models interpret this documentation revision, not every selected sample tag or executable build.',
                          'Previous sample docs retain independent identities and the existing sketch/prose disagreement.',
                          'No source-text decoder, image parser, native client, renderer, or fallback chain was executed.'])
    (HERE / 'texture-sources.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status='attributed-not-native', sourceFiles=len(sources), interpretedClaims=len(claims))))


if __name__ == '__main__':
    main()
