#!/usr/bin/env python3
"""Read retained native API results and independently read fixture artifacts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'applications/evidence/vscode-search-20261125T061429674973Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
IDS = ['initial', 'files-default', 'files-no-excludes', 'files-relative-a', 'files-pre-cancelled',
       'text-default', 'text-file-excludes', 'dirty-a', 'text-disk-after-dirty', 'text-buffer-after-dirty',
       'text-open-outside', 'add-c', 'duplicate-c', 'files-after-add', 'remove-b', 'files-after-remove',
       'apply-stale-range', 'apply-missing-text-target', 'apply-mixed-existing-target',
       'apply-interleaved-existing-target', 'cleanup-save']


def line(text):
    assert text.endswith('\n') and '\n' not in text[:-1] and all(ord(c) < 128 for c in text)
    return text[:-1]


def inspect():
    meta = json.loads((RUN / 'meta.json').read_text())
    exit = json.loads((RUN / 'exit.json').read_text())
    observed = json.loads((RUN / 'observed.json').read_text())
    host = json.loads((RUN / 'host-observed.json').read_text())
    assert exit['exitCode'] == 0 and observed['status'] == 'complete' and observed['error'] is None
    assert sha(RUN / 'observed.json') == exit['observedSha256']
    assert sha(RUN / 'extension.cjs') == meta['extensionSha256'] == exit['extensionSha256'] == sha(ROOT / 'applications/vscode/search-extension.cjs')
    assert sha(RUN / 'probe.py') == meta['producerSha256'] == exit['launchProducerSha256'] == sha(ROOT / 'applications/vscode/search_probe.py')
    assert meta['revision'] == exit['revision'] == '8a14f0cc1b08d531eb83255ea3764ae22aa932b5'
    assert host['originalProcessGroupAbsent'] and not host['matchingProcessIds']
    assert sha(RUN / 'final-workspace.json') == host['workspaceSha256']
    assert [r['id'] for r in observed['rows']] == IDS
    initial = json.loads((RUN / 'initial-files.json').read_text())
    assert set(initial) == {'a/visible.txt', 'a/hidden.txt', 'a/search-hidden.txt', 'b/visible.txt', 'c/visible.txt', 'outside.txt'}
    for text in initial.values():
        line(text)
    settings = json.loads((RUN / 'initial-settings.json').read_text())
    assert settings['files.exclude'] == {'**/hidden.txt': True} and settings['search.exclude'] == {'**/search-hidden.txt': True}
    assert settings['files.autoSave'] == 'off' and not settings['security.workspace.trust.enabled']
    package = json.loads((RUN / 'extension-package.json').read_text())
    assert package['enabledApiProposals'] == ['findTextInFiles']
    process = json.loads((RUN / 'process.json').read_text())
    assert '--enable-proposed-api=rules-study.rules-private-search-fixture' in process['argv']
    assert '--use-inmemory-secretstorage' in process['argv']
    assert json.loads((RUN / 'initial-workspace.json').read_text()) == {'folders': [{'path':'a','name':'A'}, {'path':'b','name':'B'}]}
    final = json.loads((RUN / 'final-workspace.json').read_text())
    assert [f['path'] for f in final['folders']] == ['a', 'c']
    rows = observed['rows']
    by = {r['id']: r for r in rows}
    assert [f['path'] for f in by['initial']['folders']] == ['a','b']
    for row in rows:
        assert [f['index'] for f in row['folders']] == list(range(len(row['folders'])))
        for name, f in row['files'].items():
            if f['present']:
                assert name in initial or name in ['a/created.txt','a/interleaved.txt']
                if f['text']:
                    line(f['text'])
        for b in row['buffers']:
            assert not b['closed'] and b['version'] >= 1
            line(b['text'])
        if row['kind'] == 'text-search':
            assert row['result']['complete'] == {'limitHit':False,'message':[]}
            for match in row['result']['matches']:
                text = line(match['preview'])
                query = row['result']['query']
                assert text.count(query) == 1
                start = text.index(query)
                assert match['ranges'] == [[0,start,0,start+len(query)]]
    dirty = by['dirty-a']
    a = next(b for b in dirty['buffers'] if b['path'] == 'a/visible.txt')
    assert a['dirty'] and a['text'] == 'buffer-only draft-a\n'
    assert dirty['files']['a/visible.txt']['text'] == initial['a/visible.txt']
    stale = by['apply-stale-range']
    assert stale['result']['basis'] == {'version':3,'text':'needle base\n','range':[0,0,0,6]}
    assert stale['result']['beforeApply'] == {'version':4,'text':'prefix needle base\n'}
    assert stale['result']['accepted'] is True and stale['result']['error'] is None
    assert next(b for b in stale['buffers'] if b['path']=='a/visible.txt')['text'] == 'fixed needle base\n'
    assert stale['files']['a/visible.txt']['text'] == 'needle base\n'
    for id in ['apply-missing-text-target','apply-mixed-existing-target']:
        assert by[id]['buffers'] == stale['buffers'] and by[id]['files'] == stale['files']
        assert by[id]['result'] == {'accepted':False,'error':None}
    partial = by['apply-interleaved-existing-target']
    assert partial['result'] == {'accepted':False,'error':None}
    assert partial['files']['a/interleaved.txt'] == {'present':True,'text':''}
    assert not partial['files']['a/created.txt']['present']
    after = next(b for b in partial['buffers'] if b['path']=='a/visible.txt')
    assert after['text'] == 'before-failed-create fixed needle base\n' and after['dirty']
    assert partial['files']['a/visible.txt']['text'] == 'needle base\n'
    assert by['cleanup-save']['result'] == {'documents':[{'path':'a/visible.txt','saved':True}]}
    assert observed['files'] == by['cleanup-save']['files']
    for name, f in host['files'].items():
        if f['present']:
            assert observed['files'][name] == {k:v for k,v in f.items() if k != 'sha256'}
            assert hashlib.sha256(f['text'].encode()).hexdigest() == f['sha256']
        elif name in observed['files']:
            assert observed['files'][name] == {'present':False}
    for name in initial:
        if name != 'a/visible.txt':
            assert host['files'][name]['text'] == initial[name]
    for f in json.loads((RUN / 'toolchain-readback.json').read_text())['files'].values():
        assert sha(Path(f['path'])) == f['sha256']
    sources = json.loads((ROOT / 'applications/sources/vscode-search-selections.json').read_text())['sources']
    for source in sources:
        assert sha(ROOT / source['cache']) == source['sha256']
    diagnostics = json.loads((RUN / 'diagnostic-excerpts.json').read_text())['excerpts']
    assert len(diagnostics) == 3
    for excerpt in diagnostics:
        log = Path(excerpt['path'])
        assert log.is_relative_to(Path(meta['work']) / 'user-data/logs')
        assert sha(log) == excerpt['fileSha256']
        assert log.read_text().splitlines()[excerpt['line'] - 1] == excerpt['text']
    assert 'a/missing.txt' in diagnostics[0]['text'] and 'nonexistent file' in diagnostics[0]['text']
    assert all('a/visible.txt' in d['text'] and 'already exists' in d['text'] for d in diagnostics[1:])
    return rows, host, sources


def normalized(row):
    id, kind = row['id'], row['kind']
    if kind in ['snapshot', 'cleanup']:
        return None
    if kind in ['file-search', 'text-search', 'cancel-search']:
        roots = [f['path'] for f in row['folders']]
        if id == 'files-relative-a':
            roots = ['a']
        respect = id in ['files-default','files-relative-a','text-file-excludes']
        buffers = {b['path']: b for b in row['buffers']}
        # A and outside are explicitly shown with preview:false by this fixture.
        # General loaded-model versus visible-editor admission is not inferred.
        assert set(buffers) <= {'a/visible.txt','outside.txt'}
        resources = []
        for name, file in sorted(row['files'].items()):
            if not file['present']:
                continue
            buffer = buffers.get(name)
            query = row['result'].get('query','needle')
            resources.append(dict(identity=name,root=name.split('/')[0] if '/' in name else '',present=True,
                                  excluded=name=='a/hidden.txt',providerMatch=query in file['text'],
                                  openEligible=buffer is not None,openMatch=buffer is not None and query in buffer['text']))
        return dict(kind='text' if kind=='text-search' else 'file', roots=roots, respect=respect,
                    resources=resources, cancelled=kind=='cancel-search')
    if kind == 'workspace-change':
        start,count,adds = {'add-c':(2,0,['c']), 'duplicate-c':(3,0,['c']), 'remove-b':(1,1,[])}[id]
        return dict(kind='workspace',roots=[f['path'] for f in row['result']['before']],start=start,count=count,adds=adds)
    if id == 'apply-stale-range':
        # Version at submission is source-derived from the immediately preceding
        # native API observation, not a captured internal RPC DTO.
        return dict(kind='version',planned=row['result']['basis']['version'],submitted=row['result']['beforeApply']['version'],actual=row['result']['beforeApply']['version'])
    effects = {'apply-missing-text-target':[(False,[])],
               'apply-mixed-existing-target':[(False,[]),(True,['later'])],
               'apply-interleaved-existing-target':[(True,['created:a/interleaved.txt']),(True,['buffer-prefix']),(False,[]),(True,['later'])]}[id]
    return dict(kind='groups',groups=[dict(admitted=a,effects=e) for a,e in effects])


def measured(row, previous):
    kind,id = row['kind'],row['id']
    if kind == 'file-search':
        return 'F|' + ','.join(row['result']['paths'])
    if kind == 'cancel-search':
        assert row['result']['error'] is None
        return 'F|' + ','.join(row['result']['paths'])
    if kind == 'text-search':
        return 'T|' + ','.join(m['path'] for m in row['result']['matches'])
    if kind == 'workspace-change':
        return 'W|' + ('1' if row['result']['accepted'] else '0') + '|' + ','.join(f['path'] for f in row['result']['immediate']) + '|' + ','.join(f['path'] for f in row['folders'])
    if id == 'apply-stale-range':
        return 'E|' + ('1' if row['result']['accepted'] else '0')
    if kind in ['text-edit','resource-edit']:
        effects = []
        for name,file in row['files'].items():
            if file['present'] and not previous['files'][name]['present']:
                effects.append('created:' + name)
        before = next(b['text'] for b in previous['buffers'] if b['path']=='a/visible.txt')
        after = next(b['text'] for b in row['buffers'] if b['path']=='a/visible.txt')
        if before != after:
            assert after == 'before-failed-create ' + before
            effects.append('buffer-prefix')
        return 'G|' + ('1' if row['result']['accepted'] else '0') + '|' + ','.join(effects)
    return None


if __name__ == '__main__':
    rows,host,sources = inspect()
    print(json.dumps(dict(nativeRows=len(rows),comparisonRows=sum(normalized(r) is not None for r in rows),
                          sourceFiles=len(sources),processGroupAbsent=host['originalProcessGroupAbsent'],workAllocatedKiB=host['workAllocatedKiB'])))
