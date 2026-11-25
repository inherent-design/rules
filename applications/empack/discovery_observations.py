"""Interpret the closed CLI fixture from captured inputs and independent output bytes."""
import gzip
import hashlib
import json
from pathlib import Path


def packets(run):
    read = lambda name: json.loads((run / name).read_text())
    vectors = read('vectors.json')['payloads']
    known = {}
    for number, row in enumerate(vectors):
        b = bytes.fromhex(row['hex'])
        assert len(b) == row['size'] == 128
        assert hashlib.md5(b).hexdigest() == row['md5']
        assert hashlib.sha256(b).hexdigest() == row['sha256']
        known[row['sha256']] = number
    assert vectors[0]['md5'] == vectors[1]['md5'] and vectors[0]['sha256'] != vectors[1]['sha256']
    commands = read('commands.json')
    results = read('results.json')
    assert results['complete']
    inputs, expected = [], []
    for result in results['cases']:
        command = next(c for c in commands if c['label'] == result['scan'])
        before = json.loads(gzip.decompress((run / command['before']['file']).read_bytes()))
        downloads = before['downloads']
        assert all(r['kind'] == 'file' and '/' not in name for name, r in downloads.items()), 'Only direct regular-file fixture roots admitted'
        base = 'ambiguous' if result['id'] == 'explicit-b' else 'entries' if result['id'] == 'entries-explicit' else result['id']
        lock = read(base + '-lock.json')
        assertions = lock['dependencies']['first']['files'][0]['expected']

        def matches(number):
            row = vectors[number]
            return row['size'] == assertions['size'] and all(row[algo] == digest for algo, digest in assertions['digests'].items())

        matching = []
        for name, row in sorted(downloads.items()):
            if row['bytes'] == 0:
                assert row['sha256'] == hashlib.sha256(b'').hexdigest()
                continue
            assert row['bytes'] == 128
            number = known[row['sha256']]
            if matches(number):
                matching.append(number)
        explicit, explicit_matches = None, False
        if '--file' in command['argv']:
            association = command['argv'][command['argv'].index('--file') + 1]
            key, path = association.split('=', 1)
            assert key == 'locked:first:primary'
            selected_path = Path(path)
            setup = read('setup.json')
            assert selected_path.parent == Path(setup['work']) / base / 'downloads'
            explicit = known[downloads[selected_path.name]['sha256']]
            explicit_matches = matches(explicit)
        inputs.append(dict(id=result['id'], entries=len(downloads), limit=10000,
                           matching=matching, explicit=explicit, explicitMatches=explicit_matches))
        # This side is from native publication/diagnostics, not choose() or input selection.
        product = result['product']
        selected = known[product['payloadSha256']] if product else None
        stderr = (run / (command['label'] + '.stderr')).read_text()
        if product:
            kind = 3
        elif 'Different candidate bytes match an obligation' in stderr:
            kind = 1
        elif 'Download discovery entry limit exceeded' in stderr:
            kind = 2
        else:
            raise AssertionError('Native outcome outside discovery fixture profile')
        expected.append(dict(id=result['id'], kind=kind, selected=selected,
                             published=product is not None, exitCode=command['exitCode']))
    return dict(schema=1, cases=inputs), expected
