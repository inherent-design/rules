#!/usr/bin/env python3
"""Replay controlled native document transitions; never launch empack or a PTY."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
key = lambda image: json.dumps(image, sort_keys=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    receipt = json.loads((run / 'receipt.json').read_text())
    rows = json.loads((run / 'commands.json').read_text()); edits = json.loads((run / 'edits.json').read_text())
    assert receipt['commands'] == len(rows) == 28 and receipt['allOwnedProcessesRetired'] and receipt['sourceUnchanged']
    assert sha(run / 'probe.py') == sha(HERE / 'documents_probe.py') == receipt['producerSha256']
    for name, recorded in receipt['finalDocuments'].items():
        p = run / 'work/project' / name
        if recorded is None:
            assert not p.exists()
        else:
            s = p.lstat(); assert stat.S_ISREG(s.st_mode)
            assert dict(sha256=sha(p), bytes=s.st_size, mode=stat.S_IMODE(s.st_mode),
                        inode=str(s.st_ino), mtimeNs=str(s.st_mtime_ns)) == recorded
    source = ROOT / receipt['sourceCapture'] / 'work/parent/project'
    for name, recorded in receipt['sourceImage'].items():
        if recorded is not None:
            p = source / name; s = p.stat()
            assert sha(p) == recorded['sha256'] and str(s.st_ino) == recorded['inode'] and str(s.st_mtime_ns) == recorded['mtimeNs']
    files = [run / name for name in ['receipt.json', 'commands.json', 'edits.json', 'probe.py']]
    files += [HERE / name for name in ['Documents.lean', 'Documents.bend', 'DocumentsCase.lean', 'documents_probe.py', 'documents_conformance.py']]
    ledger = ROOT / 'applications/sources/empack-documents-selections.json'; files.append(ledger)
    for record in json.loads(ledger.read_text())['sources']:
        payload = subprocess.check_output(['git', '-C', str(ROOT.parent / 'empack'), 'show',
                                          '0b4462e3032b4f09230b15329722eabefb7f574c:' + record['path']])
        assert hashlib.sha256(payload).hexdigest() == record['sha256']
    for row in rows:
        for stream in ['stdout', 'stderr']:
            p = run / (row['case'] + '.' + stream); files.append(p)
            assert sha(p) == row[stream + 'Sha256']
    # Semantic labels describe only the controlled name and payload policy.
    # They are inferred from fixture mutations, not claimed native digest fields.
    initial = dict(name=0, seedPayload=True)
    states = {key(rows[0]['before']): dict(meaning=copy.deepcopy(initial), locked=copy.deepcopy(initial), valid=True)}

    def put(image, state):
        k = key(image)
        if k in states:
            assert states[k] == state, 'Inconsistent controlled state attribution.'
            return False
        states[k] = copy.deepcopy(state); return True

    def transform(label, state):
        state = copy.deepcopy(state)
        if label == 'remove-policy-binding':
            state['meaning']['seedPayload'] = False
        elif label.startswith('new-name-'):
            state['meaning']['name'] = {'author': 1, 'lock': 2, 'binding-absence': 3}[label.removeprefix('new-name-')]
        elif label == 'unsupported-schema':
            state['valid'] = False
        elif label == 'restore-valid-author':
            state['valid'] = True
        return state

    for _ in range(len(rows) + len(edits)):
        advanced = False
        for edit in edits:
            if key(edit['before']) in states:
                advanced |= put(edit['after'], transform(edit['case'], states[key(edit['before'])]))
        for row in rows:
            if key(row['before']) not in states:
                continue
            if row['control'].get('privateControllingPTY'):
                # The explicit edit is separately recorded before the answer.
                # The refusal must leave that already edited state intact.
                after_edit = row['control']['afterExplicitEdit']
                if key(after_edit) not in states:
                    continue
                advanced |= put(row['after'], states[key(after_edit)])
            else:
                next_state = copy.deepcopy(states[key(row['before'])])
                if row['argv'][-1] == 'sync':
                    next_state['locked'] = copy.deepcopy(next_state['meaning'])
                advanced |= put(row['after'], next_state)
        if not advanced:
            break
    assert all(key(r['before']) in states and key(r['after']) in states for r in rows)
    basis_view = lambda image: dict(author=image['empack.yml']['sha256'],
        bindings=image['empack.bindings.yml']['sha256'] if image['empack.bindings.yml'] else None,
        lock=image['empack.lock']['sha256'] if image['empack.lock'] else None)
    cases, expected, calls, bend_expected, names = [], [], [], [], []
    bit = lambda b: 'True{}' if b else 'False{}'
    for row in rows:
        race = bool(row['control'].get('privateControllingPTY'))
        image = row['control']['afterExplicitEdit'] if race else row['before']
        state = states[key(image)]; current = basis_view(image); prepared = basis_view(row['before'])
        is_sync = row['argv'][-1] == 'sync'
        cases.append(dict(action=1 if is_sync else 0, prepared=prepared, current=current,
                          **state, approved=True, otherChecks=True, writtenLock=basis_view(row['after'])['lock']))
        names.append(row['case'])
        if is_sync:
            if race:
                assert row['exitCode'] == 1 and row['control']['promptMarkerObservedLive']
                assert row['control']['answer'] == 'y' and row['after'] == image
                target = {'race-author': 'empack.yml', 'race-lock': 'empack.lock',
                          'race-binding-absence': 'empack.bindings.yml'}[row['case']]
                output = (run / (row['case'] + '.stdout')).read_text()
                assert 'Project inputs changed since preparation: ' + target in output
                assert 'Apply this synchronization plan?' in output
                expected.append('refused')
            else:
                assert row['exitCode'] == 0
                for name in ['empack.yml', 'empack.bindings.yml']:
                    a, b = row['before'][name], row['after'][name]
                    assert (a['sha256'] if a else None) == (b['sha256'] if b else None)
                expected.append('recorded')
            terms = [state['valid'], True, True] + [prepared[k] == current[k] for k in ['author', 'bindings', 'lock']]
            calls.append('Bool.show(D.may_record(' + ','.join(map(bit, terms)) + ')) ++ "\\n"')
            bend_expected.append(str(expected[-1] == 'recorded'))
        elif not state['valid']:
            assert row['exitCode'] == 2 and row['before'] == row['after']
            assert 'Unsupported author schema' in (run / (row['case'] + '.stderr')).read_text()
            expected.append('invalid')
        else:
            assert row['exitCode'] == 0 and row['before'] == row['after']
            native = json.loads((run / (row['case'] + '.stdout')).read_text())
            assert native['schema'] == 1 and native['runtime_satisfied'] and not native['dependencies']
            expected.append(native['lock_status'])
            semantic_same = state['locked'] == state['meaning']
            calls.append('Bool.show(D.current(True{},' + bit(semantic_same) + ')) ++ "\\n"')
            bend_expected.append(str(native['lock_status'] == 'current'))
    basis = {str(p.relative_to(ROOT)): sha(p) for p in files}
    generated = HERE / 'generated'; generated.mkdir(exist_ok=True); path = generated / 'documents.json'
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    env = dict(os.environ, LEAN_PATH='.build/formal:.build', BEND_NO_TELEMETRY='1')

    def replay(value):
        path.write_text(json.dumps(value) + '\n')
        return subprocess.run([lean, '--run', str(HERE / 'DocumentsCase.lean'), str(path)], cwd=ROOT,
                              env=env, capture_output=True, text=True)

    # The lock output identity is an observed symbolic result parameter; this
    # model does not generate encoded lock bytes or predict their digest.
    effects = [dict(label=label, **basis_view(row['after']), locked=states[key(row['after'])]['locked'])
               for label, row in zip(expected, rows, strict=True)]
    value = dict(schema=1, cases=cases); result = replay(value)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == effects
    driver = generated / 'DocumentsCase.bend'
    driver.write_text('import Base\nimport ../Documents.bend as D\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(calls) + ')\n')
    result = subprocess.run([bend, str(driver)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == bend_expected
    invalids = [('schema', dict(value, schema=2), 'Unsupported document research schema'),
                ('action', dict(schema=1, cases=[dict(cases[0], action=2)]), 'Unsupported document action'),
                ('meaning', dict(schema=1, cases=[dict(cases[0], meaning=dict(name=4, seedPayload=False))]), 'Meaning outside controlled')]
    for label, invalid, message in invalids:
        result = replay(invalid); assert result.returncode == 2 and message in result.stderr, label
    path.write_text(json.dumps(value, indent=2) + '\n')
    assert all(sha(ROOT / p) == h for p, h in basis.items()), 'Evidence changed while consumed.'
    report = dict(schema=1, basisSha256=basis, nativeCommands=28, leanCases=len(cases), bendDecisions=len(calls),
        invalidResearchInputsRefused=[i[0] for i in invalids], cases=names,
        semanticProjection='Controlled name and payload policy labels inferred from frozen fixture edits;not a general YAML/canonical-fingerprint oracle.',
        rejectedInterpretations=['A comment-only edit necessarily makes an exact lock stale.',
            'Semantic agreement authorizes an old prepared write after raw bytes change.',
            'Absent bindings and present empty bindings are the same publication precondition.',
            'Matching raw document hashes alone grants native publication.',
            'A readable prior lock proves it resolves changed author intent.'],
        limits=['One installed0.8.8binary,no-dependency root andfixed Vanilla runtime;source0b4462e correspondence is not proved.',
            'Three positive-confirmation races only:author comment,lock comment,absent-to-empty binding.',
            'Post-refusal equality covers thethree project docs withbytes/mode/inode/mtime,not global caches/logs/native state.',
            'No root replacement,wrong grant/engine,resource admission,crash/recovery/provider/materialized dependency/game qualification.',
            'Current strict native document behavior andproposed portable draft retention remain distinct.'])
    (run / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'basisSha256'}, indent=2))


if __name__ == '__main__':
    main()
