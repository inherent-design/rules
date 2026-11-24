#!/usr/bin/env python3
"""Replay retained integrity observations; never execute restic or mutate repos."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from locks_conformance import redact

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    receipt = json.loads((run / 'receipt.json').read_text())
    rows = json.loads((run / 'trace.json').read_text())
    controls = json.loads((run / 'controls.json').read_text())
    assert receipt['commands'] == len(rows) == 20 and receipt['allOwnedProcessesRetired']
    assert receipt['copyBytesVerified'] and receipt['copyDistinctInodes'] and receipt['sourceRepoUnchanged']
    source = ROOT / receipt['sourceCapture']
    assert sha(source / 'receipt.json') == receipt['sourceReceiptSha256']
    assert sha(run / 'probe.py') == sha(HERE / 'integrity_probe.py') == receipt['producerSha256']
    assert sha(run / 'helper.py') == sha(HERE / 'locks_probe.py') == receipt['helperSha256']
    image = lambda p: {x.relative_to(p).as_posix(): {'sha256': sha(x), 'bytes': x.stat().st_size}
                       for x in sorted(p.rglob('*')) if x.is_file()}
    assert image(source / 'work/repository') == receipt['sourceRepositoryImage']
    assert image(run / 'work/repository') == receipt['finalImage']
    files = [run / name for name in ['receipt.json', 'trace.json', 'controls.json', 'probe.py', 'helper.py']]
    files += [HERE / name for name in ['Integrity.lean', 'Integrity.bend', 'IntegrityCase.lean',
              'integrity_probe.py', 'integrity_conformance.py', 'locks_conformance.py']]
    ledger = ROOT / 'applications/sources/restic-integrity-selections.json'
    files.append(ledger)
    for pin in json.loads(ledger.read_text())['sources']:
        assert sha(ROOT / pin['cache']) == pin['sha256']
    mapping_path = run / 'work/private/redaction-inputs.json'
    mapping = json.loads(mapping_path.read_text()); files.append(mapping_path)
    for row in rows:
        assert not row['timedOut']
        assert row['beforeImage'] == row['afterImage'] or 'repair' in row['case']
        for stream, rec in row['streams'].items():
            raw, public = run / rec['rawPrivatePath'], run / (row['case'] + '.' + stream)
            files += [raw, public]
            assert sha(raw) == rec['rawSha256'] and sha(public) == rec['publicSha256']
            assert redact(raw.read_bytes(), mapping) == public.read_bytes()
        before, after = row['beforeImage'], row['afterImage']
        for prefix in ['snapshots/', 'data/']:
            assert {k: v for k, v in before.items() if k.startswith(prefix)} == {
                k: v for k, v in after.items() if k.startswith(prefix)}
    by_name = {r['case']: r for r in rows}
    fault = controls[0]; target = fault['path']; target_id = Path(target).name
    pristine_path = run / 'work/private/pristine-pack'; files.append(pristine_path)
    pristine = pristine_path.read_bytes()
    assert sha(pristine_path) == fault['beforeSha256'] == target_id
    damaged = bytearray(pristine); damaged[fault['byteOffset']] ^= fault['xor']
    assert hashlib.sha256(damaged).hexdigest() == fault['afterSha256']
    assert fault['blob']['offset'] <= fault['byteOffset'] < fault['blob']['offset'] + fault['blob']['length'] < len(pristine)
    assert by_name['damaged-structure']['beforeImage'][target]['sha256'] == fault['afterSha256']
    assert by_name['after-repair-read-all']['beforeImage'][target]['sha256'] == fault['afterSha256']
    assert by_name['restored-read-all']['beforeImage'][target]['sha256'] == target_id
    assert controls[1]['notResticRecovery'] and controls[2]['kind'] == 'remove-clone-index-only'
    for name, rec in controls[2]['removedImage'].items():
        path = run / 'work/private/pristine-index' / name
        assert sha(path) == rec['sha256']; files.append(path)
    assert not any(k.startswith('index/') for k in by_name['missing-index-structure']['beforeImage'])
    assert by_name['missing-index-repair']['afterImage'] != by_name['missing-index-repair']['beforeImage']
    payload = b'Completed held A input.\n'
    for label in ['baseline-dump', 'restored-dump', 'rebuilt-index-dump']:
        assert (run / 'work/private' / (label + '.stdout')).read_bytes() == payload
    for label in ['damaged-dump', 'after-repair-dump']:
        assert by_name[label]['exitCode'] == 1
        assert (run / 'work/private' / (label + '.stdout')).read_bytes() != payload
    cases, expected, labels, calls = [], [], [], []
    bit = lambda b: 'True{}' if b else 'False{}'
    for row in rows:
        argv = row['argv'][5:]
        if argv[0] == 'cat':
            continue
        before = row['beforeImage']
        packs = [dict(id=Path(p).name, bucket=int(Path(p).name[:2], 16) % 2,
                      healthy=rec['sha256'] == Path(p).name)
                 for p, rec in before.items() if p.startswith('data/')]
        assert len(packs) == 4
        action = 1 if argv[0] == 'repair' else 2 if argv[0] == 'dump' else 0
        scope = 1 if '--read-data' in argv else (2 + int(argv[-1][0]) - 1) if '--read-data-subset' in argv else 0
        index_ok = any(p.startswith('index/') for p in before)
        case = dict(action=action, scope=scope, indexOK=index_ok, structureOK=True,
                    headersRecoverable=True, packs=packs, target=target_id)
        cases.append(case); labels.append(row['case'])
        expected.append(dict(success=row['exitCode'] == 0,
                             fullDataClaim=action == 0 and scope == 1 and row['exitCode'] == 0))
        if action == 1:
            expression = 'L.rebuilt_index(True{},False{})'
        elif action == 2:
            healthy = next(p['healthy'] for p in packs if p['id'] == target_id)
            expression = f'L.check({bit(index_ok)},True{{}},True{{}},{bit(healthy)})'
        else:
            expression = 'True{}'
            for p in packs:
                scope_term = ['L.Metadata{}', 'L.All{}', 'L.HalfFirst{}', 'L.HalfSecond{}'][scope]
                term = f'L.check({bit(index_ok)},True{{}},L.selected({scope_term},{bit(p["bucket"] == 1)}),{bit(p["healthy"])})'
                expression = f'Bool.and({expression},{term})'
        calls.append('Bool.show(' + expression + ') ++ "\\n"')
    basis = {str(p.relative_to(ROOT)): sha(p) for p in files}
    generated = HERE / 'generated'; generated.mkdir(exist_ok=True)
    path = generated / 'integrity.json'
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    env = dict(os.environ, LEAN_PATH='.build/formal:.build', BEND_NO_TELEMETRY='1')

    def replay(value):
        path.write_text(json.dumps(value) + '\n')
        return subprocess.run([lean, '--run', str(HERE / 'IntegrityCase.lean'), str(path)],
                              cwd=ROOT, env=env, capture_output=True, text=True)

    value = dict(schema=1, cases=cases)
    result = replay(value)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == expected
    runner = generated / 'IntegrityCase.bend'
    runner.write_text('import Base\nimport ../Integrity.bend as L\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(calls) + ')\n')
    result = subprocess.run([bend, str(runner)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == [str(x['success']) for x in expected]
    invalids = [('schema', dict(schema=2, cases=[]), 'Unsupported integrity schema')]
    for label, update, message in [('scope', dict(scope=4), 'Unsupported integrity scope'),
                                  ('action', dict(action=3), 'Unsupported integrity action'),
                                  ('missing-target', dict(action=2, target='absent'), 'Read target lacks')]:
        invalids.append((label, dict(schema=1, cases=[dict(cases[0], **update)]), message))
    duplicate = copy.deepcopy(cases[0]); duplicate['packs'] *= 2
    invalids.append(('duplicate-pack', dict(schema=1, cases=[duplicate]), 'Duplicate pack identity'))
    for label, invalid, message in invalids:
        result = replay(invalid)
        assert result.returncode == 2 and message in result.stderr, label
    path.write_text(json.dumps(value, indent=2) + '\n')
    assert all(sha(ROOT / name) == h for name, h in basis.items()), 'Evidence changed while consumed.'
    report = dict(schema=1, basisSha256=basis, nativeCommands=20, leanCases=len(cases),
        bendDecisions=len(calls), cases=labels, invalidResearchInputsRefused=[i[0] for i in invalids],
        redactionsVerifiedAgainstPrivateOriginals=True, sourceRepositoryUnchanged=True,
        mutationPreservesLengthAndHeaderRegion=True, snapshotsAndPackBytesUnchangedByCommands=True,
        repairIndexCannotClaimPayloadRecovery=True,
        rejectedInterpretations=['A successful default check verifies every data byte.',
            'A successful half-subset verifies the other half.',
            'A successful index repair restores damaged content.',
            'The fixture restoring pristine bytes is a native restic recovery feature.'],
        limits=['One known single-chunk file and same-size data-body fault in a four-pack local fixture.',
            'Metadata includes trees; the model structureOK premise does not reduce all metadata to index existence.',
            'FullDataClaim is a permitted source/request-scope claim, not a measured native output field.',
            'Successful header reconstruction is an explicit repair premise, not a proof of arbitrary repair availability.',
            'No repair-packs/snapshot forgetting, lost key, tree/header corruption, partial network reads or restore overwrite policy.',
            'Public copies are redacted; raw-equivalence verification needs retained owner-private work and source cache.'])
    (run / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'basisSha256'}, indent=2))


if __name__ == '__main__':
    main()
