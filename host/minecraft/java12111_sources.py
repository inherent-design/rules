#!/usr/bin/env python3
"""Map 1.21.11 registrations from pinned private inspection copies, not runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from catalog_sources import Views, vanilla

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--views', type=Path, required=True)
    parser.add_argument('--client', type=Path, required=True)
    args = parser.parse_args()
    capture = args.views.resolve()
    receipt = json.loads((capture / 'receipt.json').read_text())
    target = next(t for t in json.loads((HERE / 'targets.json').read_text())['javaReferences'] if t['release'] == '1.21.11')
    assert receipt['target'] == target['id'] and receipt['clientSha256'] == sha(args.client) == target['source']['clientSha256']
    assert len(receipt['commands']) == 2 and all(c['exitCode'] == 0 and c['ownedGroupAbsent'] and not c['timedOut'] for c in receipt['commands'])
    assert {str(p.relative_to(capture / 'source')) for p in (capture / 'source').rglob('*.java')} == set(receipt['viewsSha256'])
    for name, digest in receipt['viewsSha256'].items():
        assert sha(capture / 'source' / name) == digest
    sources = {}
    views = Views([capture / 'source'], target['id'], sources)
    categories = vanilla(views, '1.21.11')
    with zipfile.ZipFile(args.client) as archive:
        for source in sources.values():
            original = receipt['originalClassMembers'][source['className']]
            assert hashlib.sha256(archive.read(original['member'])).hexdigest() == original['sha256']
            source.update(originalClassMember=original['member'], originalClassSha256=original['sha256'],
                evidence='Private mapped/decompiled inspection copy;original class identity retained. No transformation or native conformance proof.')
    result = dict(schema=1, status='independent 1.21.11 source discovery;not runtime qualification', target=target['id'],
        clientSha256=receipt['clientSha256'], mappingSha256=receipt['mappingSha256'], mappedJarSha256=receipt['mappedJarSha256'],
        privateViewReceiptSha256=sha(capture / 'receipt.json'), generatorSha256=sha(Path(__file__)), sharedReaderSha256=sha(HERE / 'catalog_sources.py'),
        categories=categories, sources=sources,
        limits=['Literal registrations and whole-file field candidates only;not a complete per-type schema.',
                'Mapped/decompiled inspection copies are not executed and are not proved translations.',
                'Matching registered IDs or candidates do not establish reference,context,bake,render or provider equivalence.',
                'No original class/source/mapping/artwork payload exported;private inputs remain required for source reinspection.'])
    (HERE / 'java12111-registry-catalog.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(target=target['id'], registrations=sum(len(v['entries']) for v in categories.values()), categories={k: len(v['entries']) for k, v in categories.items()}, sourceFiles=len(sources))))


if __name__ == '__main__':
    main()
