#!/usr/bin/env python3
"""Owner-run acquisition of two immutable documentation inputs, never a client test."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REVISION = '80b7b1713df821debb4a8022e32e6b0ad840a273'
REPOSITORY = 'MicrosoftDocs/minecraft-creator'
FILES = {
    'texture-sets.md': 'creator/Reference/Content/TextureSetsReference/TextureSetsConcepts/TextureSetsIntroduction.md',
    'vibrant-packs.md': 'creator/Documents/VibrantVisuals/VVResourcePacks.md',
}


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'inherent-design-rules-research', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(1_000_001)
    if len(data) > 1_000_000:
        raise ValueError('Documentation response exceeds the selected byte limit')
    return data


def main():
    producer = Path(__file__).read_bytes()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    capture = ROOT / '.build/minecraft' / ('bedrock-texture-docs-' + stamp)
    capture.mkdir(parents=True, exist_ok=False)
    (capture / 'acquire_texture_docs.py').write_bytes(producer)
    api = 'https://api.github.com/repos/' + REPOSITORY
    commit_bytes = fetch(api + '/git/commits/' + REVISION)
    (capture / 'commit.json').write_bytes(commit_bytes)
    commit = json.loads(commit_bytes)
    assert commit['sha'] == REVISION
    records = []
    for name, path in FILES.items():
        metadata = fetch(api + '/contents/' + urllib.parse.quote(path, safe='/') + '?ref=' + REVISION)
        (capture / (name + '.metadata.json')).write_bytes(metadata)
        selected = json.loads(metadata)
        assert selected['path'] == path and selected['type'] == 'file'
        url = 'https://raw.githubusercontent.com/' + REPOSITORY + '/' + REVISION + '/' + path
        raw = fetch(url)
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        assert len(raw) == selected['size'] and blob == selected['sha']
        (capture / name).write_bytes(raw)
        records.append(dict(file=name, path=path, url=url, gitBlob=blob, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    assert Path(__file__).read_bytes() == producer
    receipt = dict(schema=1, repository=REPOSITORY, commit=REVISION, gitTree=commit['tree']['sha'],
                   capturedAt=stamp, producerSha256=hashlib.sha256(producer).hexdigest(),
                   commitResponseSha256=hashlib.sha256(commit_bytes).hexdigest(), files=records,
                   limits=['Documentation revision, not executable client or renderer qualification.',
                           'GitHub commit/contents responses bind requested immutable source paths; no whole-repository tree reconstruction.',
                           'Input documents stay private; public outputs retain authored interpretation and source identities.'])
    (capture / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (ROOT / '.build/minecraft/latest-bedrock-texture-docs.json').write_text(json.dumps(dict(capture=str(capture))) + '\n')
    print(json.dumps(dict(capture=str(capture.relative_to(ROOT)), files=len(records), bytes=sum(r['bytes'] for r in records))))


if __name__ == '__main__':
    main()
