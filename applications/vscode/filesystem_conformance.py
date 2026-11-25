"""Check retained filesystem observations and pure models; never launch VS Code."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'applications/evidence/vscode-filesystem-source'
RUNS = [ROOT / ('applications/evidence/vscode-filesystem-' + suffix) for suffix in
        ['20261125T124652990742Z', '20261125T125524932768Z', '20261125T125958897211Z']]
PREP = ROOT / 'applications/evidence/vscode-filesystem-20261125T124545684898Z'
REV = '8a14f0cc1b08d531eb83255ea3764ae22aa932b5'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p):
    return json.loads(p.read_text())


def write(p, v):
    p.write_text(json.dumps(v, indent=2) + '\n')


def indexed(observed):
    rows = {r['name']: r for r in observed['rows']}
    assert len(rows) == len(observed['rows'])
    return rows


def provider(row, when, name):
    return next(p for p in row[when] if p['id'] == name)


def check_native(observations):
    first, follow, control = observations
    a, b, c = map(indexed, observations)
    assert [len(o['rows']) for o in observations] == [21, 6, 4]
    for o in observations:
        assert o['schema'] == 1 and o['version'] == '1.147.0'
        # Quit acknowledgement is not the process-retirement proof.
        assert o['status'] == 'ready'
        for r in o['rows']:
            assert 0 <= r['callStart'] <= r['callEnd'] <= len(o['calls'])
            assert 0 <= r['eventStart'] <= r['eventEnd'] <= len(o['events'])
    expected_errors = {'unknown-read', 'missing-file', 'duplicate-registration',
                       'readonly-scheme-write', 'readonly-file-enforcing-provider',
                       'disposed-read', 'readonly-disposed-read', 'write-refused-after-parent-creation'}
    for o in observations:
        for r in o['rows']:
            assert (r['error'] is not None) == (r['name'] in expected_errors)
    errors = [e for e in first['events'] if e['kind'] == 'fixture-error']
    assert len(errors) == 1 and errors[0]['action'] == 'detached'
    assert errors[0]['error']['message'] == 'Fixture wait timed out'
    assert not [e for o in [follow, control] for e in o['events'] if e['kind'] == 'fixture-error']
    assert a['unknown-scheme']['result'] == dict(writable=None, known=False)
    assert a['unknown-read']['error']['code'] == 'Unavailable'
    assert a['missing-file']['error']['code'] == 'FileNotFound'
    assert a['writable-stat']['result'] == dict(writable=True, stat=dict(type=1, ctime=1, mtime=1000, size=9))
    assert a['read-copy']['result'] == dict(original='original\n', mutated='Xriginal\n', again='original\n')
    assert provider(a['read-copy'], 'before', 'writable')['files'] == provider(a['read-copy'], 'after', 'writable')['files']
    assert 'already registered' in a['duplicate-registration']['error']['message']
    assert provider(a['duplicate-registration'], 'before', 'writable') == provider(a['duplicate-registration'], 'after', 'writable')
    assert a['write-normal']['result'] == dict(text='first saved\n')
    assert a['write-creates-parent']['result']['text'] == 'child\n'
    assert a['list-directory']['result'] == [['child.txt', 1]]
    assert a['readonly-scheme-stat']['result']['writable'] is False
    assert a['readonly-scheme-write']['error']['code'] == 'NoPermissions'
    ro = a['readonly-scheme-write']
    assert first['calls'][ro['callStart']:ro['callEnd']] == [] and ro['before'] == ro['after']
    assert a['readonly-file-stat']['result']['stat']['permissions'] == 1
    assert a['readonly-file-stat']['result']['writable'] is True
    assert a['readonly-file-permissive-provider']['result'] == dict(text='provider permitted\n')
    assert a['readonly-file-enforcing-provider']['error']['code'] == 'NoPermissions'
    assert a['queue-before-release']['result'] == c['copied-queue-before-release']['result'] == dict(secondDone=False, writeEntries=1)
    assert a['queue-mutated-input-result']['result'] == dict(secondDone=True, text='Xecond queued\n')
    assert c['copied-queue-result']['result'] == dict(secondDone=True, text='second queued\n')
    for o, expected in [(first, 'Xecond queued\n'), (control, 'second queued\n')]:
        calls = [v for v in o['calls'] if v['path'] == '/queue.txt' and v['op'] == 'write-enter']
        assert [bytes.fromhex(v['hex']).decode() for v in calls] == ['first queued\n', expected]
    assert a['disposed-scheme-view']['result'] == dict(writable=True, known=True, oldDone=False)
    assert a['rebound-before-old-completes']['result'] == dict(oldDone=False, current='new backing\n')
    final = a['old-write-completed-after-rebind']['result']
    assert final['oldDone'] is True and final['current'] == 'new backing\n'
    assert final['old']['files'] == {'/file.txt': 'old completed\n'}
    assert final['fresh']['files'] == {'/file.txt': 'new backing\n'}
    for name in ['old-incarnation', 'new-incarnation']:
        entries = [v for v in first['calls'] if v['provider'] == name and v['op'] == 'write-complete']
        assert len(entries) == (1 if name == 'old-incarnation' else 0)
    assert a['watched-event-delivered']['result'] == dict(observed=['rules-vfs-write:/file.txt'], activeWatches=1)
    assert a['watch-disposed-quiet-window']['result'] == dict(before=1, after=1, waitMs=250, activeWatches=0)
    assert len([v for v in first['calls'] if v['provider'] == 'writable' and v['op'] == 'watch-disposed']) == 1
    assert b['disposed-immediate-view']['result'] == dict(known=True, writable=True)
    assert b['disposed-settled-view']['result'] == dict(known=True, writable=True, waitMs=500)
    assert b['readonly-rebound-view']['result'] == dict(known=True, writable=False, text='readonly replacement\n')
    assert b['readonly-disposed-settled-view']['result'] == dict(known=True, writable=False, waitMs=500)
    assert b['disposed-read']['error']['code'] == b['readonly-disposed-read']['error']['code'] == 'Unavailable'
    failed = c['write-refused-after-parent-creation']
    assert failed['error']['code'] == 'NoPermissions'
    before, after = [provider(failed, key, 'writable') for key in ['before', 'after']]
    assert before['directories'] == ['/'] and after['directories'] == ['/', '/failed-parent']
    assert before['files'] == after['files'] == {'/file.txt': 'original\n'}
    assert c['created-parent-after-refusal']['result']['entries'] == []
    calls = control['calls'][failed['callStart']:failed['callEnd']]
    assert [v['op'] for v in calls] == ['stat', 'createDirectory', 'write-enter', 'write-refused']
    return a, b, c


def main():
    observations = [load(p / 'observed.json') for p in RUNS]
    a, b, c = check_native(observations)
    basis_files = []
    for run in [PREP] + RUNS:
        meta = load(run / 'meta.json')
        assert meta['product'] == REV and meta['version'] == '1.147.0'
        assert sha(run / 'probe.py') == meta['producerSha256']
        assert sha(run / 'extension.cjs') == meta['extensionSha256']
        settings = load(run / 'settings.json')
        assert settings['files.autoSave'] == settings['files.hotExit'] == 'off'
        if run == PREP:
            assert not (run / 'observed.json').exists() and not (run / 'process.json').exists()
        else:
            assert load(run / 'exit.json') == dict(exitCode=0, groupAbsent=True)
            assert load(run / 'closure.json')['workspaceProcessHits'] == []
            process = load(run / 'process.json')
            assert process['environmentKeys'] == ['LANG', 'PATH', 'RULES_VFS_FIXTURE', 'SHELL', 'TMPDIR']
            assert '--use-inmemory-secretstorage' in process['argv']
            assert '--user-data-dir' in process['argv'] and meta['work'] + '/user-data' in process['argv']
        basis_files += sorted(run.iterdir())
    # Check the frozen source variants, not a false claim that one current body
    # produced all three runs. The later copy control was not run in the first.
    ext = [(p / 'extension.cjs').read_text() for p in RUNS]
    assert 'async queued()' in ext[0] and 'copyInput=false' not in ext[0]
    assert 'async partial()' not in ext[1] and 'copyInput?bytes.slice():bytes' in ext[2]
    assert 'await until(()=>vscode.workspace.fs.isWritableFileSystem(uri.scheme)===undefined)' in ext[0]
    assert 'await pause(500)' in ext[1]
    source = load(SOURCE / 'observed.json')
    receipt = load(SOURCE / 'receipt.json')
    assert sha(SOURCE / 'fragment.cjs') == receipt['fragmentSha256']
    assert sha(SOURCE / 'observed.json') == receipt['observedSha256']
    assert sha(HERE / 'filesystem_source.py') == receipt['producerSha256']
    replay = subprocess.run(['node', str(SOURCE / 'fragment.cjs')], check=True, capture_output=True)
    assert json.loads(replay.stdout) == source and not replay.stderr
    for item in load(SOURCE / 'sources.json'):
        assert item['commit'] == REV and sha(ROOT / item['excerpt']) == item['excerptSha256']
        cache = ROOT / item['cache']
        if cache.exists():
            assert sha(cache) == item['sha256']
            lines = cache.read_text().splitlines(keepends=True)
            excerpt = (ROOT / item['excerpt']).read_text()
            for start, end in item['ranges']:
                assert ''.join(lines[start-1:end]) in excerpt
    assert load(ROOT / 'applications/sources/vscode-filesystem-selections.json')['sources'] == load(SOURCE / 'sources.json')
    events, event_results = [], []
    for now, proposed in zip(source['current'], source['proposed'], strict=True):
        e = now['event']; assert e == proposed['event']
        readonly = bool(e.get('provider', {}).get('capabilities', 0) & 2048)
        events.append(dict(id=e['id'], added=e['added'], providerPresent='provider' in e, readonly=readonly))
        def knowledge(value):
            return 0 if not value['known'] else (2 if value['writable'] else 1)
        event_results.append(dict(id=e['id'], current=knowledge(now), proposed=knowledge(proposed)))
    assert [r['current'] for r in event_results] == [2, 2, 1, 2, 1, 0]
    assert [r['proposed'] for r in event_results] == [2, 0, 1, 2, 0, 0]
    # The unrelated-scheme event must not replace fixture's current identity.
    assert source['current'][3]['fixtureWritable'] is source['proposed'][3]['fixtureWritable'] is False
    assert b['disposed-settled-view']['result']['writable'] == source['current'][1]['writable']
    assert b['readonly-disposed-settled-view']['result']['writable'] == source['current'][4]['writable']
    declarations = [('write-normal', False, False, False, observations[0], a),
        ('write-creates-parent', False, False, True, observations[0], a),
        ('readonly-scheme-write', True, False, False, observations[0], a),
        ('readonly-file-permissive-provider', False, False, False, observations[0], a),
        ('readonly-file-enforcing-provider', False, True, False, observations[0], a),
        ('write-refused-after-parent-creation', False, True, True, observations[2], c)]
    writes, write_results = [], []
    for name, ro, deny, missing, raw, rows in declarations:
        row = rows[name]
        calls = raw['calls'][row['callStart']:row['callEnd']]
        writes.append(dict(id=name, schemeReadonly=ro, backendDenied=deny, parentMissing=missing))
        write_results.append(dict(id=name, callback=any(v['op'] == 'write-enter' for v in calls),
            refused=row['error'] is not None, parentCreated=any(v['op'] == 'createDirectory' for v in calls)))
    queues = [dict(id='borrowed', copied=False, mutated=True), dict(id='caller-copy', copied=True, mutated=True)]
    queue_results = [dict(id='borrowed', seesMutation=a['queue-mutated-input-result']['result']['text'].startswith('X')),
                     dict(id='caller-copy', seesMutation=c['copied-queue-result']['result']['text'].startswith('X'))]
    inputs = dict(schema=1, events=events, writes=writes, queues=queues)
    expected = dict(events=event_results, writes=write_results, queues=queue_results)
    generated = ROOT / '.build/vscode-filesystem-formal'
    generated.mkdir(exist_ok=True)
    path = SOURCE / 'model-input.json'; write(path, inputs)
    env = dict(os.environ, LEAN_PATH=str(generated), BEND_NO_TELEMETRY='1')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    command = [lean, '--run', 'applications/vscode/FileSystemsCase.lean', str(path)]
    result = subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True, text=True)
    assert json.loads(result.stdout) == expected
    def bo(v): return 'True{}' if v else 'False{}'
    pieces, wanted = [], []
    def add(fn, args, value, typ):
        pieces.append(typ + '.show(F.' + fn + '(' + ','.join(map(bo, args)) + ')) ++ "\\n"')
        wanted.append(str(value))
    for e, result in zip(events, event_results, strict=True):
        add('current_knowledge', [e['providerPresent'], e['readonly']], result['current'], 'Nat')
        add('proposed_knowledge', [e['added'], e['providerPresent'], e['readonly']], result['proposed'], 'Nat')
    for w, result in zip(writes, write_results, strict=True):
        add('reaches_callback', [w['schemeReadonly']], result['callback'], 'Bool')
        add('refused', [w['schemeReadonly'], w['backendDenied']], result['refused'], 'Bool')
        add('creates_parent', [w['schemeReadonly'], w['parentMissing']], result['parentCreated'], 'Bool')
    for q, result in zip(queues, queue_results, strict=True):
        add('dispatch_sees_mutation', [q['copied'], q['mutated']], result['seesMutation'], 'Bool')
    bend_case = generated / 'FileSystemsCase.bend'
    bend_case.write_text('import Base\nimport ../../applications/vscode/FileSystems.bend as F\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(pieces) + ')\n')
    result = subprocess.run([bend, str(bend_case)], env=env, check=True, capture_output=True, text=True)
    assert result.stdout == '\n'.join(wanted) + '\n'
    refusals = 0
    for invalid in [dict(inputs, schema=2), dict(inputs, events=[{'id': 'missing-required-input'}])]:
        write(generated / 'invalid.json', invalid)
        result = subprocess.run(command[:-1] + [str(generated / 'invalid.json')], cwd=ROOT, env=env, capture_output=True)
        assert result.returncode == 2
        refusals += 1
    mutations = [(0, 'read-copy', 'again', 'Xriginal\n'),
                 (0, 'queue-mutated-input-result', 'text', 'second queued\n'),
                 (1, 'disposed-settled-view', 'known', False),
                 (1, 'readonly-disposed-settled-view', 'writable', True),
                 (2, 'copied-queue-result', 'text', 'Xecond queued\n')]
    rejected = 0
    for index, name, field, value in mutations:
        changed = copy.deepcopy(observations)
        indexed(changed[index])[name]['result'][field] = value
        try: check_native(changed)
        except AssertionError: rejected += 1
        else: raise AssertionError('Changed observation escaped: ' + name)
    changed = copy.deepcopy(observations)
    indexed(changed[2])['write-refused-after-parent-creation']['after'][0]['directories'] = ['/']
    try: check_native(changed)
    except AssertionError: rejected += 1
    else: raise AssertionError('Lost partial directory effect escaped')
    basis_files += [p for p in SOURCE.iterdir() if p.name not in ['conformance.json', 'basis.json']]
    basis_files += [HERE / p for p in ['FileSystems.lean', 'FileSystemsCase.lean', 'FileSystems.bend',
                                     'filesystem-extension.cjs', 'filesystem_probe.py', 'filesystem_source.py', Path(__file__).name]]
    basis_files += [ROOT / 'applications/sources/vscode-filesystem-selections.json']
    basis = {str(p.relative_to(ROOT)): sha(p) for p in basis_files if p.is_file()}
    write(SOURCE / 'basis.json', basis)
    report = dict(schema=1, nativeProcesses=3, independentlyAuditedNativeRows=31,
        sourceEventPairs=6, nativeWriteBoundaries=6, nativeQueueBoundaries=2,
        scalarModelComparisons=32, laws=dict(lean=10, bend=6),
        schemaRefusals=refusals, changedObservationRefusals=rejected, basisFiles=len(basis),
        originalTimeoutPreserved=True, preparationOnlyExcluded=True,
        limits=['No native OS/backend permission enforcement or sandbox qualification.',
                'Ordinary custom provider API, not text-document save/dirty logic or browser/remote storage.',
                'Proposed registration invalidation is source-fragment qualified, not applied to VS Code.',
                '500ms post-disposal and 250ms watcher windows are bounded observations.',
                'Shared host stores and VS Code external profile writes were not measured.',
                'No reproducible source-to-installed-application build proof.'])
    write(SOURCE / 'conformance.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
