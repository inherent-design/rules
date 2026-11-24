#!/usr/bin/env python3
"""Replay retained hook-policy cases; never execute a package manager."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    receipt = json.loads((run / 'receipt.json').read_text())
    trace = json.loads((run / 'trace.json').read_text())
    native = json.loads((run / 'cases.json').read_text())
    retained = json.loads((run / 'retained-effects.json').read_text())
    assert len(trace) == receipt['commands'] == 42
    assert len(native) == receipt['cases'] == 21
    assert sha(run / 'probe.py') == receipt['producerSha256']
    inputs = [HERE / p for p in ['Policy.lean', 'Policy.bend', 'Case.lean', 'sources.json']]
    inputs += [run / p for p in ['receipt.json', 'trace.json', 'cases.json', 'probe.py', 'retained-effects.json']]
    retained_markers = {}
    for item in retained['files']:
        path = run / item['path']
        assert path.parent == run and sha(path) == item['sha256']
        retained_markers[path.name] = path
        inputs.append(path)
    for row in trace:
        assert not row['outcome']['timedOut']
        stem = row['app'] + '-' + row['case'] + '-' + row['operation']
        for stream in ['stdout', 'stderr']:
            path = run / (stem + '.' + stream)
            assert sha(path) == row['observed'][stream + 'Sha256']
            inputs.append(path)
    for path in run.iterdir():
        if path.name.endswith(('-package.json', '-package-lock.json', '-pnpm-lock.yaml', '-yarn.lock', '-.yarnrc.yml', '-pnpm-workspace.yaml')):
            inputs.append(path)
    basis = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    sources = json.loads((HERE / 'sources.json').read_text())['sources']
    for source in sources:
        assert sha(ROOT / source['cache']) == source['sha256']
    index = {(row['app'], row['case'], row['operation']): row for row in trace}
    assert len(index) == len(trace)
    cases, expected, decisions, effects = [], [], [], []
    for case in native:
        app, label = case['app'], case['id']
        assert case['configurationBefore'] == case['configurationAfter']
        config = case['configurationBefore']
        package = json.loads(config['package.json'])
        installed = index[app, label, 'install']
        before, after = installed['observed']['before'], installed['observed']['after']
        last = index[app, label, 'explicit-root' if case['scope'] == 'root' else 'inspect-module']['observed']['after']
        marker_name = app + '-' + label + '-effects.jsonl'
        if last['effectsSha256'] is None:
            assert marker_name not in retained_markers
        else:
            path = retained_markers[marker_name]
            assert sha(path) == last['effectsSha256']
            assert [json.loads(line) for line in path.read_text().splitlines()] == last['effects']
        assert before['effects'] == [] and before['lockSha256'] is None
        assert hashlib.sha256(config['package.json'].encode()).hexdigest() == before['manifestSha256'] == after['manifestSha256']
        for name, contents in config.items():
            assert (run / (app + '-' + label + '-' + name)).read_text() == contents
        lock_name = {'npm': 'package-lock.json', 'pnpm': 'pnpm-lock.yaml', 'yarn': 'yarn.lock'}[app]
        lock = run / (app + '-' + label + '-' + lock_name)
        assert (sha(lock) if lock.exists() else None) == after['lockSha256']
        if case['scope'] == 'dependency':
            source = package['dependencies']['fixture-hook']
            assert source == 'file:' + receipt['originalWork'] + '/archives/' + receipt['archive']['name']
            if app == 'npm':
                assert package.get('allowScripts', {}) == ({} if case['approval'] is None else {source: case['approval']})
                assert ('--ignore-scripts' in installed['argv']) == case['disabled']
                assert ('--dangerously-allow-all-scripts' in installed['argv']) == case['broad']
            elif app == 'pnpm':
                key = 'fixture-hook@file:../../archives/' + receipt['archive']['name']
                approvals = {} if case['approval'] is None else {key: case['approval']}
                assert config['pnpm-workspace.yaml'] == 'nodeLinker: isolated\nenableGlobalVirtualStore: false\nallowBuilds: ' + json.dumps(approvals) + '\ndangerouslyAllowAllBuilds: ' + str(case['broad']).lower() + '\n'
                assert ('--ignore-scripts' in installed['argv']) == case['disabled']
            else:
                assert package.get('dependenciesMeta', {}) == ({} if case['approval'] is None else {'fixture-hook': {'built': case['approval']}})
        if app == 'yarn':
            assert config['.yarnrc.yml'] == 'nodeLinker: node-modules\nenableGlobalCache: false\nenableNetwork: false\nenableTelemetry: false\nenableScripts: ' + str(not case['disabled']).lower() + '\n'
        row = {k: case[k] for k in ['app', 'approval', 'disabled', 'broad', 'fail', 'scope']}
        cases.append(row)
        markers = [e['scope'] + ':' + e['phase'] for e in after['effects']]
        for event in after['effects']:
            assert event['cwd'].startswith(receipt['originalWork'] + '/' + app + '-' + label + '/project')
        selected = 'run' if markers else ('review-required' if app == 'pnpm' and case['approval'] is None and case['scope'] == 'dependency' else 'skip')
        expected.append({'decision': selected, 'effects': markers, 'succeeds': installed['outcome']['exitCode'] == 0})
        decisions.append(selected)
        if case['scope'] == 'dependency':
            inspected = index[app, label, 'inspect-module']
            assert inspected['outcome']['exitCode'] == 0
            assert inspected['observed']['before'] == after == inspected['observed']['after']
            runtime = json.loads((run / (app + '-' + label + '-inspect-module.stdout')).read_text())
            assert runtime['available'] == after['packageEntryExists']
            if runtime['available']: assert runtime['value'] == 'fixture-hook-1.0.0'
            else: assert runtime['error'] == 'MODULE_NOT_FOUND'
        else:
            explicit = index[app, label, 'explicit-root']
            assert explicit['observed']['before'] == after and explicit['outcome']['exitCode'] == 0
            cases.append(dict(row, scope='explicit-root'))
            expected.append({'decision': 'run', 'effects': [e['scope'] + ':' + e['phase'] for e in explicit['observed']['after']['effects']], 'succeeds': True})
        effects.append({'app': app, 'case': label, 'exitCode': installed['outcome']['exitCode'],
            'hookMarkers': len(markers), 'selectedModulePresent': after['packageEntryExists'], 'lockPresent': after['lockSha256'] is not None})
    generated = HERE / 'generated'; generated.mkdir(exist_ok=True)
    path = generated / 'cases.json'
    path.write_text(json.dumps({'schema': 1, 'cases': cases}, indent=2) + '\n')
    env = dict(os.environ, LEAN_PATH=os.pathsep.join(str(ROOT / p) for p in ['.build', '.build/formal']), BEND_NO_TELEMETRY='1')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    def replay(data):
        path.write_text(json.dumps(data) + '\n')
        return subprocess.run([lean, '--run', 'applications/js-scripts/Case.lean', str(path)], cwd=ROOT, env=env, capture_output=True, text=True)
    result = replay({'schema': 1, 'cases': cases})
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == expected
    calls = []
    bit = lambda b: 'True{}' if b else 'False{}'
    for case in native:
        app = case['app']
        profile = ('P.Yarn{' + bit(not case['disabled']) + '}') if app == 'yarn' else ('P.' + {'npm': 'Npm', 'pnpm': 'Pnpm'}[app] + '{' + bit(case['disabled']) + ',' + bit(case['broad']) + '}')
        review = 'P.' + ('Unreviewed' if case['approval'] is None else 'Allow' if case['approval'] else 'Deny') + '{}'
        expression = 'P.workspace(' + profile + ')' if case['scope'] == 'root' else 'P.dependency(' + profile + ',' + review + ')'
        calls.append('P.label(' + expression + ') ++ "\\n"')
    runner = generated / 'Case.bend'
    runner.write_text('import Base\nimport ../Policy.bend as P\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(calls) + ')\n')
    result = subprocess.run([bend, str(runner)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == decisions
    negatives = []
    for name, data, diagnostic in [
        ('unknown-schema', {'schema': 2, 'cases': cases}, 'Unsupported script-policy schema'),
        ('unknown-profile', {'schema': 1, 'cases': [dict(cases[0], app='unselected')]}, 'Unknown script-policy profile'),
        ('unknown-scope', {'schema': 1, 'cases': [dict(cases[0], scope='all')]}, 'Unknown script-policy scope')]:
        result = replay(data)
        assert result.returncode == 2 and diagnostic in result.stderr
        negatives.append(name)
    path.write_text(json.dumps({'schema': 1, 'cases': cases}, indent=2) + '\n')
    assert all(sha(ROOT / p) == digest for p, digest in basis.items()), 'Frozen input changed during replay.'
    # Explicit source equivalence, not an extra Yarn wide-bypass policy.
    yarn = {c['id']: c for c in native if c['app'] == 'yarn'}
    assert yarn['deny']['configurationBefore'] == yarn['broad-allow-with-deny']['configurationBefore']
    report = {'schema': 1, 'adapterSha256': sha(Path(__file__)), 'basisSha256': basis,
        'nativeCommands': 42, 'installCases': 21, 'distinctInstallProfiles': 20, 'leanObservedOutcomes': len(cases),
        'leanMatches': True, 'bendDecisionsMatch': True, 'inputRefusals': negatives,
        'duplicateControl': 'Yarn broad-allow-with-deny repeats enabled-default explicit denial; it is not a distinct broad-bypass switch.',
        'scopedEffects': effects,
        'rejectedInterpretations': ['Scripts disabled has identical scope across tools.', 'An explicit denial always wins every broad override.',
            'Unreviewed and explicitly denied are the same decision.', 'A nonzero install leaves no selected files, lock, or hook output.',
            'A successful installation proves all hooks ran or the selected package is safe.'],
        'limits': ['Lean predicts controlled hook permission, marker sequence and injected failure status only. Bend compares permission decisions only.',
            'Selected module/lock visibility and exact exit codes are independent native observations, not predicted filesystem transitions.',
            'npm non-strict review, pnpm strict-dependency-build defaults, compatible Yarn hard package with node-modules linker.',
            'No general sandbox, rollback, registry/key-spoofing qualification, approval/rebuild command, workspace graph, signal, concurrency, or cross-platform claim.',
            'Retained work was moved after snapshots; original absolute links are not promised usable at the new location.']}
    (run / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['basisSha256', 'scopedEffects']}, indent=2))


if __name__ == '__main__':
    main()
