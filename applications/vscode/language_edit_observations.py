"""Read the retained language-edit fixture; never launch Code or touch a document."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CAP = ROOT/'applications/evidence/vscode-language-edit-20261126T005327358915Z'
PREP = ROOT/'applications/evidence/vscode-language-edit-20261126T005228104843Z'
MODES = ['workspace','workspace','guarded','editor-pair','editor-pair','editor-pair',
         'format-compute','format-apply','format-command','rename-compute','rename-apply']
IDS = ['workspace-fresh','workspace-late','caller-guarded','editor-parallel','editor-sequential',
       'editor-parallel-empty','format-compute','format-compute-late-apply',
       'interactive-format-late','rename-compute','rename-compute-late-apply']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())


def apply_ranges(text, edits):
    """Only the fixture's one ASCII line; not UTF-16 or general VS Code edits."""
    assert text.isascii() and text.endswith('\n') and text.count('\n') == 1
    ordered = sorted(edits, key=lambda e: e['range'][1:4:2])
    end = 0
    for e in ordered:
        a,b,c,d = e['range']
        assert a == c == 0 and end <= b <= d < len(text)
        assert e['newText'].isascii() and '\n' not in e['newText']
        end = d
    for e in reversed(ordered):
        _,b,_,d = e['range'];text = text[:b] + e['newText'] + text[d:]
    return text


def observe(raw, meta):
    assert raw['schema'] == 1 and raw['version'] == meta['version'] == '1.148.0'
    assert raw['status'] == 'quit-requested' and raw['handled'] == 12 and raw['activeProviders'] == 0
    rows = raw['rows'];assert [r['action'] for r in rows] == IDS
    assert len(raw['scaffold']) == 11
    uri = 'file://' + meta['work'] + '/project/document.rules-language'
    providers = [e for e in raw['events'] if e['kind'] in ['format','rename']]
    assert [e['action'] for e in providers] == IDS[6:]
    # The frozen producer's object spread overwrote 'provider-returned' with
    # entry.kind. These shape-checked records still occur after its gate.
    assert all(set(e) == {'kind','action','basis','computedWord','computedRange',
                         'canceledAtEntry','completedAgainst','canceledAtReturn'} for e in providers)
    canceled = [e for e in raw['events'] if e['kind'] == 'provider-canceled']
    assert all(e['provider'] == 'format' for e in canceled)
    assert len({e['action'] for e in canceled}) == len(canceled)
    packets, measured, details = [], [], []
    for i,(r,mode,reset) in enumerate(zip(rows,MODES,raw['scaffold'])):
        before,after,result = r['before'],r['after'],r['result']
        assert reset['action'] == r['action'] and reset['kind'] == 'owned-reset' and reset['result'] is True
        assert reset['after'] == before and before['text'] == 'alpha beta\n'
        if i:assert reset['before'] == rows[i-1]['after']
        for s in [before,after]:
            assert type(s['version']) is int and s['version'] > 0
            assert type(s['dirty']) is bool and not s['closed'] and s['activeIsOwn']
        assert r['activeProviders'] == 0
        basis = result.get('basis',result.get('firstBasis'));assert basis == before
        intervened = 'intervening' in result
        current = result['intervening']['after'] if intervened else before
        if intervened:
            assert result['intervening']['before'] == before
            assert result['intervening']['result'] is True
            assert current['text'] == 'shift ' + before['text'] and current['version'] == before['version'] + 1
        second = result.get('secondBasis',before)
        packet = dict(mode=mode,basis=before['version'],secondBasis=second['version'],intervened=intervened,
                      secondEmpty=result.get('secondHasNoEdits',False))
        if 'results' in result:
            assert len(result['results']) == 2 and all(type(v) is bool for v in result['results'])
            response = ','.join(str(v).lower() for v in result['results'])
            assert second['text'] == (before['text'] if second['version'] == before['version'] else 'ONE beta\n')
        elif mode == 'guarded':
            assert result['kind'] == 'authored-caller-policy' and result['allowed'] == result['apiCalled']
            assert result['allowed'] == (before['version'] == current['version'])
            response = 'not-called' if not result['apiCalled'] else str(result['result']['value']).lower()
            if not result['apiCalled']:assert result['result'] == {'kind':'not-called'}
        elif mode == 'format-command':
            assert result['commandReturn'] == {'kind':'undefined'} and result['windowMs'] == 500
            response = 'undefined'
        elif 'applied' in result:
            assert type(result['applied']) is bool;response = str(result['applied']).lower()
        else:
            assert result['returned']['kind'] in ['edits','workspace-edit'];response = 'returned-edits'
        was_canceled = False
        if i >= 6:
            provider = providers[i-6]
            assert provider['basis'] == {k:before[k] for k in ['version','text']}
            assert provider['completedAgainst'] == {k:current[k] for k in ['version','text']}
            assert provider['computedWord'] == 'alpha' and provider['computedRange'] == [0,0,0,5]
            assert provider['canceledAtEntry'] is False and type(provider['canceledAtReturn']) is bool
            was_canceled = provider['canceledAtReturn']
            assert was_canceled == any(e['action'] == r['action'] for e in canceled)
            if mode == 'format-command':assert result['canceledWithinWindow'] == was_canceled
            else:
                returned = result['returned']
                if returned['kind'] == 'workspace-edit':
                    assert len(returned['entries']) == 1 and returned['entries'][0]['uri'] == uri
                    edits = returned['entries'][0]['edits'];replacement = 'REN'
                else:edits = returned['edits'];replacement = 'FMT(alpha)'
                # Minimal formatting edits may differ from the provider's edit
                # representation. Check their effect against its captured plan.
                assert apply_ranges(current['text'],edits) == replacement + current['text'][5:]
                if 'beforeApply' in result:assert result['beforeApply'] == current
        packets.append(packet)
        measured.append([response,after['text'],after['version']-before['version'],was_canceled])
        details.append(dict(action=r['action'],basis=before['version'],currentBeforeApply=current['version'],
                            returned=result.get('returned'),dirtyAfter=after['dirty'],providersAtBoundary=r['activeProviders']))
    for c in raw['calls']:
        r = rows[IDS.index(c['action'])]
        if c['api'] == 'workspace.applyEdit':
            assert c['basis'] == r['before']
            assert c['submittedAt'] == r['result'].get('intervening',{}).get('after',r['before'])
    assert len(raw['calls']) == 12
    return dict(schema=1,profile='vscode-1.148-language-edit',cases=packets),measured,details


def evidence(owner_local=True):
    meta,raw = load(CAP/'meta.json'),load(CAP/'observed.json')
    assert meta['commit'] == '661626d0e72f97806550790a98fb87116c9db825'
    assert meta['operations'] == IDS + ['quit']
    assert sha(CAP/'extension.cjs') == meta['extensionSha256'] == sha(HERE/'language-edit-extension.cjs')
    assert sha(CAP/'probe.py') == meta['producerSha256'] == sha(HERE/'language_edit_probe.py')
    closure,exit = load(CAP/'closure.json'),load(CAP/'exit.json')
    assert closure['exit'] == exit and closure['work'] == meta['work'] and closure['remainingExactWorkArguments'] == []
    assert exit['exitCode'] == 0 and exit['groupAbsent'] is True
    assert not (PREP/'process.json').exists() and not (PREP/'observed.json').exists()
    for i,action in enumerate(IDS+['quit'],1):
        receipt = load(CAP/f'request-{i}.json')
        assert receipt['sequence'] == i and receipt['action'] == action
        assert receipt['status'] == ('quit-requested' if action == 'quit' else 'ready')
        assert len(receipt['observedSha256']) == 64
    settings = load(CAP/'settings.json')
    assert settings['files.autoSave'] == 'off' and not settings['editor.formatOnSave']
    assert not settings['editor.formatOnType'] and not settings['editor.formatOnPaste']
    process = load(CAP/'process.json');assert '--use-inmemory-secretstorage' in process['argv']
    assert process['pid'] > 0 and meta['work'] in process['argv'][-1]
    inputs,measured,details = observe(raw,meta)
    gate = load(CAP/'proof-gate.json')
    assert gate['exitCode'] == 0 and 'Checked 3 Lean modules and 2 Bend files.' in gate['stdout']
    for path,digest in gate['sourceSha256'].items():assert sha(ROOT/path) == digest
    excluded = []
    selections = ROOT/'applications/sources/vscode-language-edit-selections.json'
    for s in load(selections)['sources']:
        p = ROOT/s['cache']
        if owner_local:assert sha(p) == s['sha256'] and p.stat().st_size == s['bytes']
        else:excluded.append(s['cache'])
    if owner_local:
        for path,identity in meta['binaries'].items():assert sha(Path(path)) == identity['sha256']
        work = Path(meta['work'])
        assert (work/'project/document.rules-language').read_text() == raw['rows'][-1]['after']['text']
        assert sha(work/'extension/extension.cjs') == meta['extensionSha256']
        for stream in exit['privateStreams'].values():assert sha(Path(stream['path'])) == stream['sha256']
    else:excluded += ['installed Code/product/package/main/extension-host identities','private final file/extension','private app stdout/stderr']
    derived = {'model-input.json','measured.json','details.json','basis.json','controls.json','conformance.json','public-parity.json'}
    files = [p for c in [CAP,PREP] for p in c.iterdir() if p.is_file() and p.name not in derived]
    files += [selections,HERE/'language_edit_observations.py',HERE/'language_edit_conformance.py',HERE/'language_edit_probe.py',HERE/'language-edit-extension.cjs']
    files += [HERE/n for n in ['LanguageEdit.lean','LanguageEdit.bend','LanguageEditCase.lean','WorkspaceSearch.lean','WorkspaceSearch.bend']]
    return inputs,measured,details,{str(p.relative_to(ROOT)):sha(p) for p in sorted(files)},excluded
