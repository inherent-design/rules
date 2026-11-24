#!/usr/bin/env python3
"""Replay native seed limits and proposed evidence classes; never run empack."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ADAPTER = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    receipt = json.loads((run / 'receipt.json').read_text())
    models = [HERE / name for name in ['ObservationDemand.lean', 'ObservationDemand.bend', 'ObservationDemandCase.lean']]
    paths = [*models, run / 'receipt.json', run / 'probe.py', run / 'progress.json',
             *(run / (c['label'] + suffix) for c in receipt['commands'] for suffix in ['.stdout', '.stderr'])]
    basis = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    assert sha(run / 'probe.py') == receipt['probeSha256']
    for c in receipt['commands']:
        assert sha(run / (c['label'] + '.stdout')) == c['stdoutSha256']
        assert sha(run / (c['label'] + '.stderr')) == c['stderrSha256']
    observed = receipt['observations']
    assert observed['checkExit'] == 0 and observed['checkComplete']
    assert observed['previewExit'] == 1 and 'Snapshot exceeds byte limit' in observed['previewDiagnostic']
    assert observed['seedSizeUnchanged'] and observed['seedMtimeUnchanged']
    assert observed['seedAllocatedBytesBefore'] == observed['seedAllocatedBytesAfter'] == 4096
    assert observed['restoredSeedCheckExit'] == 0
    checked = json.loads((run / 'check-sparse-seed.stdout').read_text())
    assert checked['player_owned_entries'] == 1 and checked['verified_files'] == 1
    assert any(f['subject'] == 'config/rules.txt' and f['state'] == 'player-owned' for f in checked['findings'])
    cases, expected = [], []

    def add(role, kind, known, seed, explicit, outcome):
        cases.append(dict(role=role, kind=kind, knownBytes=known, seed=seed, explicitChange=explicit))
        expected.append(outcome)

    add('installed-destination', 'regular', False, True, False, 'preserve-no-byte-claim')
    add('installed-destination', 'regular', True, True, False, 'preserve-no-byte-claim')
    add('installed-destination', 'regular', False, False, False, 'need-byte-facts')
    add('installed-destination', 'regular', True, False, False, 'compare-content')
    add('installed-destination', 'regular', False, True, True, 'need-byte-facts')
    add('installed-destination', 'unavailable', False, True, False, 'need-observation')
    add('installed-destination', 'directory', False, True, False, 'reject-kind')
    add('installed-destination', 'absent', False, True, False, 'prepare-absent-plan')
    add('distribution-source', 'regular', False, True, False, 'need-byte-facts')
    add('distribution-source', 'regular', True, True, False, 'compare-content')
    add('distribution-source', 'absent', False, True, False, 'missing-source')
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)
    inputs = dict(schema=1, size=observed['seedLogicalBytes'], maximum=8 * 1024 ** 3, cases=cases)
    input_path = generated / 'observation-demand.json'
    input_path.write_text(json.dumps(inputs, indent=2) + '\n')
    env = dict(os.environ, LEAN_PATH=os.pathsep.join(str(ROOT / p) for p in ['.build', '.build/formal']), BEND_NO_TELEMETRY='1')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    result = subprocess.run([lean, '--run', 'applications/empack/ObservationDemandCase.lean', str(input_path)],
                            cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == {'currentByteGate': False, 'proposed': expected}
    calls = []
    for c in cases:
        role = 'D.InstalledDestination{}' if c['role'] == 'installed-destination' else 'D.DistributionSource{}'
        evidence = {'unavailable': 'D.Unavailable{}', 'absent': 'D.Absent{}', 'directory': 'D.Directory{}',
                    'regular': 'D.Regular{' + ('Some{O.FileValue{1n,1n,False{},False{}}}' if c['knownBytes'] else 'None{}') + '}'}[c['kind']]
        policy = 'O.Seed{}' if c['seed'] else 'O.Managed{}'
        explicit = 'True{}' if c['explicitChange'] else 'False{}'
        calls.append(f'D.label(D.next_step({role},{evidence},{policy},{explicit})) ++ "\\n"')
    case = generated / 'ObservationDemandCase.bend'
    case.write_text('import Base\nimport ../Ownership.bend as O\nimport ../ObservationDemand.bend as D\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(calls) + ')\n')
    result = subprocess.run([bend, str(case)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == expected
    invalid = json.loads(json.dumps(inputs))
    invalid['cases'][0].update(kind='unavailable', knownBytes=True)
    bad = generated / 'invalid-observation-demand.json'
    bad.write_text(json.dumps(invalid))
    result = subprocess.run([lean, '--run', 'applications/empack/ObservationDemandCase.lean', str(bad)],
                            cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 2 and 'Only a regular-file observation' in result.stderr
    assert all(sha(ROOT / path) == digest for path, digest in basis.items()), 'Inputs changed during replay.'
    report = {'schema': 1, 'nativeCommands': len(receipt['commands']), 'nativeByteGateMatchesLean': True,
        'proposedEvidenceCasesMatchBothModels': len(cases),
        'inconsistentEvidenceRefused': True,
        'currentPreviewAcceptsOversizedPreservedSeed': False,
        'proposalImplemented': False, 'basisSha256': basis, 'adapterSha256': ADAPTER,
        'limits': ['One metadata stress fixture,not a normal-size performance measurement or data-loss reproduction.',
            'Only the current byte-admission predicate is compared to the native refusal;proposed classification is design simulation.',
            'Large numeric sizes are evaluated by Lean;Bend replay covers qualitative role/evidence classification only.',
            'No new native observation/publication implementation or authorization is established.']}
    (run / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'basisSha256'}, indent=2))


if __name__ == '__main__':
    main()
