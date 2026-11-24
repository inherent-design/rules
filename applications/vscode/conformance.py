#!/usr/bin/env python3
"""Replay retained native document states; no VS Code or GUI execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    receipt = json.loads((run / 'receipt.json').read_text())
    hashed = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert hashed(run / 'observed.json') == receipt['observedSha256']
    assert hashed(run / 'extension.cjs') == receipt['extensionSha256']
    data = json.loads((run / 'observed.json').read_text())
    assert data['status'] == 'quit-requested' and receipt['exit']['exitCode'] == 0
    assert data['identity']['version'] == '1.147.0' and data['identity']['uiKind'] == 1
    assert str(json.loads((run / 'process.json').read_text())['pid']) == data['identity']['codePid']
    rows = data['rows']
    assert len(rows) == 12
    operations = [r['operation'] for r in rows]
    inputs = run / 'model-input.json'
    inputs.write_text(json.dumps({'schema': 1, 'operations': operations}, indent=2) + '\n')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    env = dict(os.environ, LEAN_PATH=str(ROOT / '.build'), BEND_NO_TELEMETRY='1')
    result = subprocess.run([lean, '--run', 'applications/vscode/Case.lean', str(inputs)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    model = json.loads(result.stdout)
    observed = [dict(operation=r['operation'], **{k: r['observed'][k] for k in ['version', 'dirty', 'buffer', 'disk']}) for r in rows]
    assert model == observed, (model, observed)
    original = 'V.PointSnapshot{"original","original\\n"}'
    state = 'V.BufferState{1n,' + original + ',' + original + ',"original\\n"}'
    pieces = []
    for name in operations:
        if name in ['open', 'quit-requested']:
            pass
        elif name in ['edit-one', 'edit-two', 'edit-dirty']:
            key, text = {'edit-one': ('one', 'draft-one'), 'edit-two': ('two', 'draft-two'), 'edit-dirty': ('local', 'local-unsaved')}[name]
            state = 'V.edit(' + state + ',V.PointSnapshot{' + json.dumps(key) + ',' + json.dumps(text + '\n') + '})'
        elif name == 'save':
            state = 'V.save(' + state + ')'
        elif name == 'undo':
            state = 'V.edit(' + state + ',V.saved_point(' + state + '))'
        elif name == 'redo':
            state = 'V.edit(' + state + ',V.PointSnapshot{"two","draft-two\\n"})'
        elif name in ['external-clean', 'external-dirty']:
            state = 'V.external_write(' + state + ',V.PointSnapshot{' + json.dumps(name) + ',' + json.dumps(name + '\n') + '})'
        elif name == 'revert':
            state = 'V.revert(' + state + ',"external-dirty")'
        else:
            raise AssertionError(name)
        pieces.append('row(' + json.dumps(name) + ',' + state + ')')
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)
    source = '''import Base
import ../Document.bend as V

def row(operation: String, +editor: V.DocEditor) -> String:
  operation ++ "\\n" ++ Nat.show(V.version(editor)) ++ "\\n" ++ Bool.pick(String, V.dirty(editor), "true", "false") ++ "\\n" ++ V.point_text(V.current_point(editor)) ++ V.disk_text(editor)

def main() -> IO(Unit):
  IO.write(''' + ' ++ '.join(pieces) + ')\n'
    (generated / 'NativeCase.bend').write_text(source)
    result = subprocess.run([bend, str(generated / 'NativeCase.bend')], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    expected = ''.join(r['operation'] + '\n' + r['version'] + '\n' + str(r['dirty']).lower() + '\n' + r['buffer'] + r['disk'] for r in observed)
    assert result.stdout == expected
    by_op = {r['operation']: r for r in observed}
    saved = observed[2]
    undo = by_op['undo']
    assert int(undo['version']) > int(saved['version']) and not undo['dirty']
    assert undo['buffer'] == saved['buffer'] == undo['disk']
    assert by_op['external-dirty']['buffer'] != by_op['external-dirty']['disk'] and by_op['external-dirty']['dirty']
    for r in rows:
        if r['operation'] == 'save':
            assert r['outcome']['returned'] is True
    (run / 'model-output.json').write_text(json.dumps(model, indent=2) + '\n')
    report = {'schema': 1, 'states': 12, 'bothModelsMatchNativeSerialProjection': True,
              'eventVersionAsSavepointIdentityRejected': True,
              'externalDirtyWritePreservesBuffer': True, 'explicitRevertLoadsBacking': True,
              'models': {p.name: hashed(p) for p in [HERE / 'Document.lean', HERE / 'Document.bend', HERE / 'Case.lean']},
              'limits': ['History points are an admitted projection, not exported VSCode alternativeVersionId values or a full undo-stack model.',
                         'One LF/ASCII native file,serial operations,one macOS profile; no concurrent save,encoding change,error write,or browser qualification.',
                         'Initial keychain prompt was canceled; OS credential/profile behavior is not qualified by these file results.']}
    (run / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
