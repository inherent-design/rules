"""Acquire the selected official npm tool under ignored study tools; never install globally."""
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
VERSION = '12.2.3'
REVISION = '7aa36da5c867b71fc7ea905f0392fc872f769cc6'


def main():
    tools = ROOT / 'applications/tools'
    dest = tools / ('npm-' + VERSION)
    assert not dest.exists(), 'Inspect and reuse an admitted tool; never overwrite it'
    pin = json.loads((ROOT / 'applications/sources/npm-manifest-npm12-tool.json').read_text())
    assert pin['version'] == VERSION and pin['gitHead'] == REVISION
    metadata_url = 'https://registry.npmjs.org/npm/' + VERSION
    raw_meta = urllib.request.urlopen(metadata_url, timeout=25).read()
    metadata = json.loads(raw_meta)
    assert metadata['name'] == 'npm' and metadata['version'] == VERSION and metadata['gitHead'] == REVISION
    url = metadata['dist']['tarball']
    assert url == f'https://registry.npmjs.org/npm/-/npm-{VERSION}.tgz'
    with urllib.request.urlopen(url, timeout=25) as response:
        raw = response.read((8 << 20) + 1)
    assert len(raw) <= 8 << 20
    integrity = 'sha512-' + base64.b64encode(hashlib.sha512(raw).digest()).decode()
    assert integrity == metadata['dist']['integrity'] == pin['integrity']
    assert hashlib.sha256(raw).hexdigest() == pin['archiveSha256']
    assert hashlib.sha1(raw).hexdigest() == metadata['dist']['shasum']
    import tarfile
    stage = Path(tempfile.mkdtemp(prefix='npm-' + VERSION + '-stage-', dir=tools))
    entries = []
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tar:
        members = tar.getmembers()
        assert len(members) <= 4096 and sum(m.size for m in members) <= 20 << 20
        seen = set()
        for m in members:
            path = PurePosixPath(m.name)
            assert not path.is_absolute() and path.parts[0] == 'package' and '..' not in path.parts
            assert '\\' not in m.name and m.name not in seen
            assert m.isfile() or m.isdir(), 'Only regular files and directories are admitted'
            assert m.size <= 5 << 20
            seen.add(m.name)
            target = stage.joinpath(*path.parts)
            assert target.resolve().is_relative_to(stage.resolve())
            if m.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            body = tar.extractfile(m).read()
            assert len(body) == m.size
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as output:
                output.write(body)
            target.chmod(m.mode & 0o755)
            entries.append(dict(path=m.name, bytes=m.size, sha256=hashlib.sha256(body).hexdigest()))
    package = json.loads((stage / 'package/package.json').read_text())
    assert package['name'] == 'npm' and package['version'] == VERSION
    selected = []
    ledger = json.loads((ROOT / 'applications/sources/npm-manifest-upstream-selections.json').read_text())
    for source in ledger:
        p = stage / 'package' / source['path']
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        assert digest == source['sha256']
        selected.append(dict(path=source['path'], sha256=digest))
    (stage / 'npm.tgz').write_bytes(raw)
    entry = stage / 'package/bin/npm-cli.js'
    receipt = dict(schema=1, version=VERSION, gitHead=REVISION, metadataUrl=metadata_url,
        metadataSha256=hashlib.sha256(raw_meta).hexdigest(), tarballUrl=url, integrity=integrity,
        archiveSha256=hashlib.sha256(raw).hexdigest(), archiveBytes=len(raw), files=len(entries),
        unpackedBytes=sum(v['bytes'] for v in entries), selectedSources=selected,
        entryRelative='package/bin/npm-cli.js', entrySha256=hashlib.sha256(entry.read_bytes()).hexdigest(),
        producerSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        engines=metadata['engines'], members=entries,
        scope='Official registry content integrity, regular-only bounded extraction, and selected source correspondence; no global install, tool execution, publisher-signature verification, or whole-build reproducibility claim.')
    (stage / 'acquisition-producer.py').write_bytes(Path(__file__).read_bytes())
    (stage / 'tool-acquisition.json').write_text(json.dumps(receipt, indent=2) + '\n')
    assert not dest.exists()
    stage.rename(dest)
    print(json.dumps(dict(tool=str(dest), version=VERSION, files=len(entries), archiveBytes=len(raw), unpackedBytes=receipt['unpackedBytes'])))


if __name__ == '__main__':
    main()
