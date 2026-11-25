#!/usr/bin/env python3
"""Acquire bounded exact Bedrock sample schemas/docs, without artwork or a client."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request
import uuid

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def select(tree):
    """All client schemas and doc modules, plus one JSON anchor per sample family."""
    rows = [r for r in tree['tree'] if r['type'] == 'blob']
    names = {r['path'] for r in rows if r['path'].startswith('metadata/json_schemas/client/')
             or (r['path'].startswith('metadata/doc_modules/') and r['path'].endswith('.json'))}
    names.update({'LICENSE.md', 'README.md', 'version.json', 'resource_pack/manifest.json'})
    families = {}
    for r in sorted(rows, key=lambda r: r['path']):
        parts = r['path'].split('/')
        if parts[0] == 'resource_pack' and r['path'].endswith('.json'):
            key = parts[1] if len(parts) > 2 else '@root/' + parts[1]
            families.setdefault(key, r['path'])
    names.update(families.values())
    return [r for r in rows if r['path'] in names], families


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trees', type=Path, required=True)
    p.add_argument('--private', type=Path, required=True)
    args = p.parse_args()
    targets = json.loads((HERE.parent / 'targets.json').read_text())
    private = args.private.resolve()
    private.mkdir(parents=True, exist_ok=True)
    blobs = private / 'blobs'
    blobs.mkdir(exist_ok=True)
    selected, plans, unique = [], [], {}
    for target in targets['bedrockReferences']:
        source = target['source']
        path = args.trees / ('bedrock-tree-' + source['tag'] + '.json')
        assert sha(path) == source['treeResponseSha256']
        tree = json.loads(path.read_text())
        assert not tree.get('truncated')
        rows, families = select(tree)
        plans.append(dict(target=target['id'], commit=source['commit'], treeResponseSha256=sha(path),
                          selectedFiles=len(rows), exampleAnchors=families))
        for r in rows:
            assert r['size'] <= 8 * 1024 * 1024
            row = dict(target=target['id'], path=r['path'], gitBlob=r['sha'], bytes=r['size'],
                       url='https://raw.githubusercontent.com/Mojang/bedrock-samples/' + source['commit'] + '/' + urllib.parse.quote(r['path'], safe='/'))
            if r['sha'] in unique:
                assert unique[r['sha']]['bytes'] == r['size']
            unique.setdefault(r['sha'], row)
            selected.append(row)
    assert sum(r['bytes'] for r in unique.values()) <= 32 * 1024 * 1024
    capture = private / ('acquisition-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    capture.mkdir()
    (capture / 'acquire.py').write_bytes(Path(__file__).read_bytes())
    (capture / 'plan.json').write_text(json.dumps(dict(schema=1, plans=plans, files=selected), indent=2) + '\n')

    def acquire(row):
        destination = blobs / (row['gitBlob'] + '.blob')
        origin = 'verified-existing-study-input'
        if not destination.exists():
            temporary = blobs / (row['gitBlob'] + '.part-' + uuid.uuid4().hex)
            request = urllib.request.Request(row['url'], headers={'User-Agent': 'rules-source-study'})
            with urllib.request.urlopen(request, timeout=30) as response, temporary.open('xb') as output:
                count = 0
                while chunk := response.read(65536):
                    count += len(chunk)
                    assert count <= row['bytes']
                    output.write(chunk)
            verify(temporary, row)
            try:
                os.link(temporary, destination)
            except FileExistsError:
                pass
            temporary.unlink()
            origin = 'pinned-official-source-url'
        verify(destination, row)
        return dict(gitBlob=row['gitBlob'], bytes=row['bytes'], sha256=sha(destination), origin=origin)

    def verify(path, row):
        raw = path.read_bytes()
        assert len(raw) == row['bytes']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['gitBlob']

    results = []
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            for i, row in enumerate(pool.map(acquire, unique.values()), 1):
                results.append(row)
                if i % 25 == 0:
                    print(json.dumps(dict(acquired=i, uniqueBlobs=len(unique))), flush=True)
    finally:
        receipt = dict(schema=1, capturedAt=datetime.now(timezone.utc).isoformat(),
                       producerSha256=sha(capture / 'acquire.py'), planSha256=sha(capture / 'plan.json'),
                       completed=len(results), selectedFiles=len(selected), uniqueBlobs=len(unique),
                       plannedUniqueBytes=sum(r['bytes'] for r in unique.values()), networkConcurrency=2,
                       results=results, complete=len(results) == len(unique),
                       limits=['Source tags are not client binaries or runtime qualification.',
                               'All client schema files and doc modules are selected; one JSON example per resource family is an anchor, not complete asset coverage.',
                               'No image, audio, executable, game installation or native client acquired.'])
        (capture / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    assert receipt['complete']
    (private / 'latest.json').write_text(json.dumps(dict(capture=str(capture)), indent=2) + '\n')
    print(json.dumps({k: receipt[k] for k in ['completed', 'selectedFiles', 'uniqueBlobs', 'plannedUniqueBytes', 'complete']}))


if __name__ == '__main__':
    main()
