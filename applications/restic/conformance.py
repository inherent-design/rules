#!/usr/bin/env python3
"""Compare projected native restic transitions with Lean and Bend; no restic launch."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    findings = json.loads((run / 'findings.json').read_text())
    rows = json.loads((run / 'trace.json').read_text())
    commands = {r['operationId'].split('-', 1)[1]: r for r in rows}
    old, shared, new = [findings[group][key] for group, key in
                        [('oldContent', 'changed.txt'), ('expectedNewContent', 'shared.txt'), ('expectedNewContent', 'changed.txt')]]
    for role, identity in [('old', old), ('shared', shared), ('new', new)]:
        r = commands[role + '-blob-before']
        payload = (run / (role + '-blob-before.stdout')).read_bytes()
        assert r['outcome']['exitCode'] == 0 and hashlib.sha256(payload).hexdigest() == identity
    assert commands['old-blob-after']['outcome']['exitCode'] == 1
    assert 'blob not found' in (run / 'old-blob-after.stderr').read_text()
    for role, identity in [('shared', shared), ('new', new)]:
        assert commands[role + '-blob-after']['outcome']['exitCode'] == 0
        assert hashlib.sha256((run / (role + '-blob-after.stdout')).read_bytes()).hexdigest() == identity
    before = commands['forget-a']['observed']['beforePacks']
    assert commands['forget-a']['observed']['afterPacks'] == before
    assert findings['parentIsForgottenSnapshot'] and findings['expectedNewContent'] == findings['restoredContent']
    case = {'schema': 1, 'gone': findings['snapshotA'], 'exclusive': True,
            'snapshots': [{'id': findings['snapshotA'], 'parent': None, 'reachableData': [old, shared]},
                          {'id': findings['snapshotB'], 'parent': findings['snapshotBParent'], 'reachableData': [shared, new]}],
            'availableData': [old, shared, new]}
    assert len({old, shared, new}) == 3
    # This projection covers selected file-data blobs. Tree/index/pack closure is not inferred.
    (run / 'projected-input.json').write_text(json.dumps(case, indent=2) + '\n')
    lean = os.environ.get('LEAN', 'lean')
    bend = os.environ.get('BEND', 'bend')
    env = dict(os.environ, LEAN_PATH=str(REPO / '.build'), BEND_NO_TELEMETRY='1')
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)

    def evaluate(input_case, name):
        file = run / (name + '.json')
        file.write_text(json.dumps(input_case, indent=2) + '\n')
        answer = subprocess.check_output([lean, '--run', 'applications/restic/Case.lean', str(file)], cwd=REPO, env=env, text=True)
        interpreted = json.loads(answer)
        q = json.dumps  # All IDs are observed lowercase hexadecimal strings.
        assert all(len(v) == 64 and all(c in '0123456789abcdef' for c in v) for v in [input_case['gone'], *input_case['availableData']])
        snapshots = []
        for s in input_case['snapshots']:
            parent = 'None{}' if s['parent'] is None else 'Some{' + q(s['parent']) + '}'
            snapshots.append('R.Snap{' + q(s['id']) + ',' + parent + ',[' + ','.join(q(v) for v in s['reachableData']) + ']}')
        repo = 'R.Repo{[' + ','.join(snapshots) + '],[' + ','.join(q(v) for v in input_case['availableData']) + ']}'
        program = 'import Base\nimport ../Retention.bend as R\n\ndef main() -> IO(Unit):\n  do IO<Unit>:\n    +repo : R.Repository = ' + repo + '\n    IO.write("forget\\n" ++ R.lines(R.backing(R.forget(' + q(input_case['gone']) + ', repo))) ++ "prune\\n" ++ R.lines(R.backing(R.prune(' + ('True{}' if input_case['exclusive'] else 'False{}') + ', R.forget(' + q(input_case['gone']) + ', repo)))))\n'
        source = generated / 'NativeCase.bend'
        source.write_text(program)
        native = subprocess.check_output([bend, str(source)], cwd=REPO, env=env, text=True).splitlines()
        cut = native.index('prune')
        assert native[0] == 'forget'
        other = {'afterForget': native[1:cut], 'afterPrune': native[cut + 1:]}
        assert interpreted == other
        return interpreted

    correct = evaluate(case, 'model-case')
    assert correct == {'afterForget': [old, shared, new], 'afterPrune': [shared, new]}
    # Counterexample: treating B's parent link as a retaining edge predicts old data survives.
    broken = copy.deepcopy(case)
    broken['snapshots'][1]['reachableData'].append(old)
    wrong = evaluate(broken, 'negative-lineage-as-retention')
    assert old in wrong['afterPrune'] and old not in correct['afterPrune']
    refused = copy.deepcopy(case)
    refused['exclusive'] = False
    blocked = evaluate(refused, 'no-exclusive')
    assert blocked['afterPrune'] == [old, shared, new]
    receipt = {'schema': 1, 'nativeRun': str(run), 'nativeInputSha256': hashlib.sha256((run / 'projected-input.json').read_bytes()).hexdigest(),
               'observedForgetKeepsPackBytes': True, 'modelsAgree': True,
               'lineageAsRetentionCounterexampleRejected': True, 'noExclusiveNoReclamation': True,
               'models': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE / 'Retention.lean', HERE / 'Retention.bend', HERE / 'Case.lean']},
               'limits': ['Selected three file-data blobs, two snapshots, local stationary repository.',
                          'Complete tree reachability and lock correctness are premises, not proved by this adapter.',
                          'No generic retention policy, remote backend, corruption, or full physical-pack model qualified.']}
    (run / 'conformance.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
