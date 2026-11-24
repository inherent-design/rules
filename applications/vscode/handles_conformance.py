#!/usr/bin/env python3
"""Replay retained handle-registry fragments; no browser or application execution."""
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
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    receipt = json.loads((run / 'receipt.json').read_text())
    assert receipt['schema'] == 1 and not receipt.get('error') and not receipt['pageErrors']
    assert receipt['sourceRevision'] == '8a14f0cc1b08d531eb83255ea3764ae22aa932b5'
    assert receipt['sdkVersion'] == '1.64.1' and receipt['browserVersion'] == '156.0.8078.4'
    assert sha(run / 'probe.mjs') == receipt['probeSha256']
    assert sha(run / 'observed.json') == receipt['observedSha256']
    selected = {row['path']: row['sha256'] for row in json.loads((ROOT / 'applications/sources/vscode-selections.json').read_text())}
    for source in receipt['sources'].values():
        assert selected[source['path']] == source['sha256']
    observed = json.loads((run / 'observed.json').read_text())
    assert observed['secure'] and observed['browserHandles']['queryPermission'] == 'granted'
    assert observed['browserHandles']['distinctSameName']
    rows = observed['cases']
    assert len(rows) == 6
    pairs, aborted = rows[:5], rows[5]
    assert [r['id'] for r in pairs] == ['same-file', 'different-files', 'file-then-directory', 'directory-then-file', 'new-provider-unloaded-alias']
    inputs = {'schema': 1, 'cases': [dict(id=r['id'], firstFile=r['firstKind'] == 'file',
        secondFile=r['secondKind'] == 'file', sameEntry=r['sameUnderlyingEntry'], freshReceiver=r['freshReceiver']) for r in pairs]}
    path = run / 'model-input.json'
    path.write_text(json.dumps(inputs, indent=2) + '\n')
    env = dict(os.environ, LEAN_PATH=str(ROOT / '.build'), BEND_NO_TELEMETRY='1')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    result = subprocess.run([lean, '--run', 'applications/vscode/HandlesCase.lean', str(path)],
                            cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    lean_rows = json.loads(result.stdout)
    expected = [dict(id=r['id'], secondSuffix=r['secondUri'] != r['firstUri'],
        **{k: r[k] for k in ['currentIsFirst', 'currentIsSecond', 'persistedIsFirst', 'persistedIsSecond']}) for r in pairs]
    assert lean_rows == expected, (lean_rows, expected)
    functions = ['second_suffix', 'memory_first', 'memory_second', 'stored_first', 'stored_second']
    pieces = []
    for row in inputs['cases']:
        args = ','.join('True{}' if row[k] else 'False{}' for k in ['firstFile', 'secondFile', 'sameEntry', 'freshReceiver'])
        pieces.extend('Bool.show(H.' + name + '(' + args + ')) ++ "\\n"' for name in functions)
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)
    case = generated / 'HandlesCase.bend'
    case.write_text('import Base\nimport ../Handles.bend as H\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(pieces) + ')\n')
    result = subprocess.run([bend, str(case)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    fields = ['secondSuffix', 'currentIsFirst', 'currentIsSecond', 'persistedIsFirst', 'persistedIsSecond']
    assert result.stdout == ''.join(str(r[k]) + '\n' for r in expected for k in fields)
    assert aborted['id'] == 'aborted-handle-persistence' and aborted['memoryIsFirst']
    assert aborted['freshLookup'] == 'Unavailable' and aborted['errors']
    # These stronger interpretations are contradicted by measured rows.
    assert any(not r['sameUnderlyingEntry'] and r['firstUri'] == r['secondUri'] for r in pairs)
    assert any(r['currentIsFirst'] != r['persistedIsFirst'] for r in pairs)
    invalid = {'schema': 1, 'cases': [dict(id='impossible-kind', firstFile=True, secondFile=False, sameEntry=True, freshReceiver=False)]}
    bad = generated / 'invalid-handles.json'
    bad.write_text(json.dumps(invalid))
    result = subprocess.run([lean, '--run', 'applications/vscode/HandlesCase.lean', str(bad)],
                            cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 2 and 'both a file and a directory' in result.stderr
    report = {
        'schema': 1, 'sourceFragmentCases': 6, 'pairCasesMatchBothModels': 5,
        'abortedPersistenceRetainsMemoryOnly': True,
        'rejectedInterpretations': ['basename aliases always distinguish native entries', 'memory and persisted aliases always agree', 'returned registration implies persisted registration'],
        'impossibleKindInputRefused': True,
        'models': {p.name: sha(p) for p in [HERE / 'Handles.lean', HERE / 'Handles.bend', HERE / 'HandlesCase.lean']},
        'adapterSha256': sha(Path(__file__)), 'receiptSha256': sha(run / 'receipt.json'),
        'limits': ['Five two-registration projections,not a complete registry,case-folding,or suffix allocator.',
            'Unmodified method fragments with URI/error dependency adapters and real OPFS/IDB;not full VS Code UI or user file permissions.',
            'New provider object means empty memory in the same browser page;no actual application-process restart.',
            'Immutable-key proposal is proved as a separate candidate;not implemented or native-qualified.']}
    (run / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
