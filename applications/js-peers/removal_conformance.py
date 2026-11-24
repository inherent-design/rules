#!/usr/bin/env python3
"""Compare retained native declaration edits, runtime lookups, and scoped models."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ADAPTER = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    trace = json.loads((run / 'trace.json').read_text())
    receipt = json.loads((run / 'receipt.json').read_text())
    inputs = [HERE / p for p in ['Removal.lean', 'Removal.bend', 'RemovalCase.lean']]
    inputs += [run / p for p in ['trace.json', 'receipt.json', 'probe.py']]
    inputs += sorted(run.glob('*-package.json')) + sorted(run.glob('*-package-lock.json')) + sorted(run.glob('*-pnpm-lock.yaml')) + sorted(run.glob('*-yarn.lock'))
    inputs += [run / (row['app'] + '-' + row['case'] + '.' + stream) for row in trace for stream in ['stdout', 'stderr']]
    basis = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    assert sha(run / 'probe.py') == receipt['producerSha256']
    assert len(trace) == receipt['commands'] == 36
    for row in trace:
        for stream in ['stdout', 'stderr']:
            assert sha(run / (row['app'] + '-' + row['case'] + '.' + stream)) == row['observed'][stream + 'Sha256']
    cases, expected, negative, references = [], [], [], []
    actions = {'remove-direct-leaf': 'remove-leaf', 'remove-transitive-only': 'remove-leaf',
        'readopt-identical-leaf': 'add-leaf', 'remove-parent': 'remove-parent', 'remove-last-leaf': 'remove-leaf'}
    for manager in ['npm', 'pnpm', 'yarn']:
        rows = {row['case']: row for row in trace if row['app'] == manager}
        assert rows['install']['outcome']['exitCode'] == 0
        lock_name = {'npm': 'package-lock.json', 'pnpm': 'pnpm-lock.yaml', 'yarn': 'yarn.lock'}[manager]
        for label in ['installed', *actions]:
            operation = 'install' if label == 'installed' else label
            after = rows[operation]['observed']['after']
            assert sha(run / (manager + '-' + label + '-package.json')) == after['manifestSha256']
            assert sha(run / (manager + '-' + label + '-' + lock_name)) == after['lockSha256']
            assert json.loads((run / (manager + '-' + label + '-package.json')).read_text()).get('dependencies', {}) == after['dependencies']
        assert set(rows['install']['observed']['after']['dependencies']) == {'fixture-parent', 'fixture-leaf'}
        for label, action in actions.items():
            row = rows[label]
            before, after = row['observed']['before'], row['observed']['after']
            runtime = json.loads((run / (manager + '-' + label + '-runtime.stdout')).read_text())
            parent_live = runtime['fixture-parent'].get('value') == 'leaf-one'
            leaf_visible = runtime['fixture-leaf'].get('value') == 'leaf-one'
            roots = after['dependencies']
            assert parent_live == ('fixture-parent' in roots)
            if not parent_live: assert runtime['fixture-parent']['error'] == 'MODULE_NOT_FOUND'
            if not leaf_visible: assert runtime['fixture-leaf']['error'] == 'MODULE_NOT_FOUND'
            live = parent_live or leaf_visible
            ok = row['outcome']['exitCode'] == 0
            cases.append(dict(profile=manager, action=action,
                parent='fixture-parent' in before['dependencies'], leaf='fixture-leaf' in before['dependencies']))
            expected.append('/'.join(str(int(x)) for x in [ok, parent_live, 'fixture-leaf' in roots, live, leaf_visible]))
            if label == 'remove-transitive-only':
                assert before == after, 'The repeated removal changed measured manifest/lock state.'
                assert row['outcome']['exitCode'] == (0 if manager == 'npm' else 1)
            if label == 'remove-direct-leaf':
                assert 'fixture-leaf' not in roots and parent_live
                negative.append('declaration-removal-means-payload-unavailable:' + manager)
                if leaf_visible: negative.append('root-lookup-means-direct-declaration:' + manager)
            if label == 'readopt-identical-leaf':
                original = rows['install']['observed']['after']['dependencies']['fixture-leaf']
                restored = roots['fixture-leaf']
                project = Path(receipt['originalWork']) / manager / 'project'
                def target(spec):
                    assert spec.startswith('file:')
                    return os.path.normpath(project / spec[5:])
                assert ok and target(original) == target(restored)
                references.append({'app': manager, 'original': original, 'restored': restored,
                    'sameArchiveTarget': True, 'sameSerializedReference': original == restored})
    generated = HERE / 'generated'; generated.mkdir(exist_ok=True)
    path = generated / 'removal.json'; path.write_text(json.dumps({'schema': 1, 'cases': cases}, indent=2) + '\n')
    env = dict(os.environ, LEAN_PATH=os.pathsep.join(str(ROOT / p) for p in ['.build', '.build/formal']), BEND_NO_TELEMETRY='1')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    result = subprocess.run([lean, '--run', 'applications/js-peers/RemovalCase.lean', str(path)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == expected
    calls = []
    for case in cases:
        profile = {'npm': 'Npm', 'pnpm': 'Pnpm', 'yarn': 'Yarn'}[case['profile']]
        action = {'remove-leaf': 'RemoveLeaf', 'add-leaf': 'AddLeaf', 'remove-parent': 'RemoveParent'}[case['action']]
        bit = lambda b: 'True{}' if b else 'False{}'
        calls.append(f'render(R.{profile}{{}}, R.{action}{{}}, R.Roots{{{bit(case["parent"])},{bit(case["leaf"])}}}) ++ "\\n"')
    runner = generated / 'RemovalCase.bend'
    runner.write_text('import Base\nimport ../Removal.bend as R\n\ndef bit(b: Bool) -> String:\n  match b:\n    case True{}: "1"\n    case False{}: "0"\n\ndef render_next(next: R.Roots, +profile: R.Profile, ok: Bool) -> String:\n  match next:\n    case R.Roots{+parent,+leaf}: bit(ok) ++ "/" ++ bit(parent) ++ "/" ++ bit(leaf) ++ "/" ++ bit(R.live_leaf(R.Roots{parent,leaf})) ++ "/" ++ bit(R.root_can_load_leaf(profile,R.Roots{parent,leaf}))\n\ndef render(+profile: R.Profile, +action: R.Action, +roots: R.Roots) -> String:\n  render_next(R.next(profile,action,roots),profile,R.accepted(roots,action,profile))\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(calls) + ')\n')
    result = subprocess.run([bend, str(runner)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == expected
    invalid = generated / 'removal-unsupported.json'
    invalid.write_text(json.dumps({'schema': 2, 'cases': cases}))
    result = subprocess.run([lean, '--run', 'applications/js-peers/RemovalCase.lean', str(invalid)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 2 and 'Unsupported removal schema' in result.stderr
    assert all(sha(ROOT / p) == digest for p, digest in basis.items()), 'Inputs changed during replay.'
    report = {'schema': 1, 'nativeCommands': 36, 'modeledDeclarationEdits': len(cases),
        'bothModelsMatch': True, 'unsupportedSchemaRefused': True, 'rejectedInterpretations': negative,
        'readoptionReferenceObservations': references,
        'adapterSha256': ADAPTER, 'basisSha256': basis,
        'limits': ['Two fixed selected identities, one required edge; not a solver, general linker, or package-manager implementation.',
            'Root declarations, parent loading and root lookup are separate measurements; cache contents and physical reclamation unmeasured.',
            'No lifecycle scripts, PnP, multiple workspaces, peers, failure during publication, or concurrency qualification.']}
    (run / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'basisSha256'}, indent=2))


if __name__ == '__main__':
    main()
