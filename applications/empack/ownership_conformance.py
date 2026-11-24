#!/usr/bin/env python3
"""Replay actual core API results and retained CLI facts; no native execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ADAPTER_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    load = lambda name: json.loads((run / name).read_text())
    receipt, core, progress = load('receipt.json'), load('core-receipt.json'), load('progress.json')
    model_paths = [HERE / 'Ownership.lean', HERE / 'Ownership.bend', HERE / 'OwnershipCase.lean']
    basis_paths = [*model_paths, run / 'receipt.json', run / 'core-receipt.json', run / 'progress.json',
                   run / 'core-observed.tsv', run / 'ownership-probe.py', run / 'ownership-oracle.rs',
                   *(run / (c['label'] + suffix) for c in progress['commands'] for suffix in ['.stdout', '.stderr']),
                   *(run / ('release-' + label + '.json') for label in ['a', 'b', 'c'])]
    basis = {str(p.relative_to(ROOT)): sha(p) for p in basis_paths}
    assert sha(run / 'ownership-probe.py') == receipt['probeSha256']
    assert sha(run / 'progress.json') == receipt['progressSha256']
    assert sha(run / 'ownership-oracle.rs') == core['driverSha256']
    assert sha(run / 'core-observed.tsv') == core['observedSha256']
    for c in progress['commands']:
        assert sha(run / (c['label'] + '.stdout')) == c['stdoutSha256']
        assert sha(run / (c['label'] + '.stderr')) == c['stderrSha256']
    rows, expected = [], []
    for line in (run / 'core-observed.tsv').read_text().splitlines():
        previous, incoming, kind, content, readonly, executable, caps, decision = line.split('\t')
        row = dict(previous=int(previous), incoming=int(incoming), kind=int(kind), id=int(content),
            readonly=readonly == 'true', executable=executable == 'true', executableBits=caps == 'true')
        assert readonly in ['true', 'false'] and executable in ['true', 'false'] and caps in ['true', 'false']
        rows.append(row)
        expected.append(decision)
    assert len(rows) == core['cases'] == 252
    inputs = {'schema': 1, 'cases': rows}
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)
    model_input = generated / 'ownership-input.json'
    model_input.write_text(json.dumps(inputs, indent=2) + '\n')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    env = dict(os.environ, LEAN_PATH=os.pathsep.join(str(ROOT / p) for p in ['.build', '.build/formal']), BEND_NO_TELEMETRY='1')
    result = subprocess.run([lean, '--run', 'applications/empack/OwnershipCase.lean', str(model_input)],
                            cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == expected
    boolean = lambda b: 'True{}' if b else 'False{}'
    value = lambda id, ro=False, ex=False: f'O.FileValue{{{id}n,1n,{boolean(ro)},{boolean(ex)}}}'
    calls = []
    for r in rows:
        prior = 'O.Unowned{}' if r['previous'] == 0 else 'O.Owned{' + value(1) + ',O.' + ('Managed' if r['previous'] == 1 else 'Seed') + '{}}'
        incoming = 'O.Retire{}' if r['incoming'] == 0 else 'O.Incoming{' + value(2) + ',O.' + ('Managed' if r['incoming'] == 1 else 'Seed') + '{}}'
        current = ['O.Absent{}', 'O.Directory{}', 'O.Regular{' + value(r['id'], r['readonly'], r['executable']) + '}'][r['kind']]
        calls.append(f'O.label(O.plan({incoming},{prior},{current},{boolean(r["executableBits"])})) ++ "\\n"')
    case = generated / 'OwnershipCase.bend'
    case.write_text('import Base\nimport ../Ownership.bend as O\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(calls) + ')\n')
    result = subprocess.run([bend, str(case)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == expected
    for r, outcome in zip(rows, expected, strict=True):
        if r['incoming'] == 2 and r['kind'] == 2:
            assert outcome == 'preserve'
        if r['previous'] == 2 and r['incoming'] == 1 and r['kind'] != 1:
            assert outcome == 'seed-ownership'
        if r['previous'] == 0 and r['incoming'] == 1 and r['kind'] == 2:
            assert outcome == 'unowned'
        if r['previous'] == 1 and r['incoming'] == 1 and r['kind'] == 2 and r['id'] == 1 and not r['readonly'] and r['executable']:
            assert outcome == ('modified' if r['executableBits'] else 'replace')
    commands = {c['label']: c for c in progress['commands']}
    assert len(commands) == receipt['commands'] == 15
    for label in ['modified-managed-refused', 'seed-to-managed-refused']:
        assert commands[label]['exitCode'] == 1
        text = (run / (label + '.stderr')).read_text()
        assert 'game/payload.txt' in text and all(flag in text for flag in ['--preserve=', '--replace=', '--merge='])
    for o in progress['observations']:
        if 'before' in o:
            assert o['before'] == o['after']
    releases = [load('release-' + label + '.json') for label in ['a', 'b', 'c']]
    assert len({r['pack'] for r in releases}) == 1 and len({r['version'] for r in releases}) == 1
    assert [sha(run / ('release-' + label + '.json')) for label in ['a', 'b', 'c']] == receipt['releaseIds']
    assert len(set(receipt['releaseIds'])) == 3
    final_files = next(o['instanceFiles'] for o in progress['observations'] if o['kind'] == 'final')
    seed_assertion = next(f['sha256'] for f in releases[1]['files'] if f['destination'] == 'config/rules.txt')
    assert final_files['game/config/rules.txt']['sha256'] != seed_assertion
    before_check, final_check = load('check-accepted-override.stdout'), load('check-repaired.stdout')
    assert before_check['complete'] and before_check['verified_overrides'] == 1
    assert final_check['complete'] and final_check['release'] == receipt['releaseIds'][1]
    assert final_check['verified_files'] == 1 and final_check['verified_overrides'] == 0
    assert final_check['player_owned_entries'] == 1
    assert all(sha(ROOT / path) == digest for path, digest in basis.items()), 'Replay inputs changed during execution;inspect before retrying.'
    report = {'schema': 1, 'currentCoreApiCasesMatchBothModels': 252, 'nativeCliCommands': 15,
        'previewAndRefusalsPreserveMeasuredInstanceFiles': True, 'acceptedOverrideAndRepairChecksPass': True,
        'sameVersionLabelHasDistinctReleaseIdentities': True,
        'rejectedInterpretations': ['matching bytes establish unowned-file adoption',
            'missing former seed implies permission for managed adoption',
            'all executable changes matter on representations without executable bits',
            'seed preservation verifies publisher equality'],
        'models': {p.name: basis[str(p.relative_to(ROOT))] for p in model_paths},
        'basisSha256': basis,
        'adapterSha256': ADAPTER_SHA256, 'nativeReceiptSha256': sha(run / 'receipt.json'),
        'coreReceiptSha256': sha(run / 'core-receipt.json'),
        'limits': ['Finite core API matrix has fixed previous/incoming content and length;not all semantic states or an OS filesystem test.',
            'The installed release binary and standalone current core have separate source/build provenance.',
            'CLI flow is one macOS tiny snapshot fixture;no world groups,Prism layout,channel authentication,runtime,or crash recovery.',
            'Native file-preservation assertions are retained in the exact executed probe;not every intermediate file byte snapshot was separately captured.']}
    (run / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
