"""Closed authored fixture interpretation, independent of packed membership."""
import hashlib
import json
from pathlib import Path
import posixpath
import tarfile


def packets(run):
    observed = json.loads((run / 'observed.json').read_text())['cases']
    inputs, expected, archives = [], [], []
    managers = ['npm', 'pnpm', 'yarn']
    allowed_patterns = {'ordinary-note.txt', 'dist/**', 'src/**', 'bin/**', 'README.md', 'LICENSE', 'private.txt'}
    def matches(path, patterns):
        values = patterns.splitlines()
        assert set(values) <= allowed_patterns, 'Outside literal fixture pattern profile'
        return any(path.startswith(p[:-2]) if p.endswith('/**') else path == p for p in values)
    for case in observed:
        request = json.loads((run / (case['id'] + '-input.json')).read_text())
        source, manifest = request['authored'], request['manifest']
        assert case['authoredBefore'] == case['authoredAfter'] == request['before']
        assert json.loads(source['package.json']) == manifest
        assert manifest.get('files') in [None, ['dist']]
        archive = run / (case['id'] + '.tgz')
        assert archive.stat().st_size <= 1 << 20
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == case['archiveSha256'], 'Retained archive digest differs'
        with tarfile.open(archive, 'r:gz') as tar:
            entries = tar.getmembers()
            assert len(entries) < 64 and sum(m.size for m in entries) < 1 << 20
            members = []
            selected = set()
            for m in entries:
                raw = tar.extractfile(m).read() if m.isfile() else b''
                members.append(dict(path=m.name, kind='file' if m.isfile() else 'symlink' if m.issym() else 'directory',
                                    link=m.linkname, mode=m.mode, bytes=m.size,
                                    sha256=hashlib.sha256(raw).hexdigest() if m.isfile() else None))
                path = m.name.removeprefix('package/')
                if m.isdir():
                    continue
                assert path in request['before'] and path not in selected
                selected.add(path)
                original = request['before'][path]
                if m.issym():
                    assert original['kind'] == 'symlink' and m.linkname == original['target']
                else:
                    assert original['kind'] == 'file'
                    if path == 'package.json':
                        assert json.loads(raw) == manifest
                    else:
                        assert hashlib.sha256(raw).hexdigest() == original['sha256']
            assert members == case['members']
        required = {'package.json', 'README.md', 'LICENSE', manifest['main'], *manifest['bin'].values()}
        for path, original in sorted(request['before'].items()):
            kind = 0
            if original['kind'] == 'symlink':
                assert original['target'] in ['public.js', '../../outside.txt', 'missing-target.txt']
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), original['target']))
                kind = 2 if resolved.startswith('../') or resolved.startswith('/') else 1 if resolved in request['before'] else 3
            nested = False
            if path.startswith('dist/') and 'dist/.npmignore' in source:
                nested = matches(path.removeprefix('dist/'), source['dist/.npmignore'])
            inputs.append(dict(id=case['id'] + ':' + path, manager=managers.index(case['manager']), kind=kind,
                globalExcluded=Path(path).name in ['.npmignore', '.gitignore', '.yarnrc.yml'], required=path in required,
                filesPresent='files' in manifest, listed=path.startswith('dist/'), npmPresent='.npmignore' in source,
                npmMatch=matches(path, source.get('.npmignore', '')), gitMatch=matches(path, source.get('.gitignore', '')),
                nestedMatch=nested))
            expected.append(dict(id=case['id'] + ':' + path, included=path in selected))
        archives.append(dict(id=case['id'], selectedEntries=len(selected), symlinks=sum(m['kind'] == 'symlink' for m in members),
                             manifestSemanticEquality=True, nonmanifestBytesAndLinkTextPreserved=True))
    return dict(schema=1, cases=inputs), expected, archives
