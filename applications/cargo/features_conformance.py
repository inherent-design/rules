#!/usr/bin/env python3
"""Replay retained feature contexts through Lean/Bend; never execute Cargo."""
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
import tomllib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = ROOT / 'applications/evidence/cargo-features-20261124T181357949100Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    # Validate raw observations first. This runs no native build or executable.
    subprocess.run(['python3', str(HERE / 'features_observations.py')], cwd=ROOT, check=True, capture_output=True)
    receipt = json.loads((RUN / 'receipt.json').read_text())
    trace = json.loads((RUN / 'trace.json').read_text())
    configurations = json.loads((RUN / 'configuration.json').read_text())
    assert len(trace) == 51 and receipt['targetCleaned']
    assert receipt['tools']['rustc']['version'].split('host: ')[1].splitlines()[0] == 'aarch64-apple-darwin'
    source_pins = ROOT / 'applications/sources/cargo-features-selections.json'
    files = [HERE / n for n in ['Features.lean', 'Features.bend', 'FeaturesCase.lean',
        'features_conformance.py', 'features_observations.py', 'features-observations.json']]
    files += [source_pins, *[RUN / n for n in ['receipt.json', 'trace.json', 'configuration.json', 'probe.py', 'binaries.json']]]
    files += [ROOT / p['localCache'] for p in json.loads(source_pins.read_text())]
    for row in trace:
        for stream in ['stdout', 'stderr']:
            files.append(RUN / ('r' + str(row['resolver']) + '-' + row['case'] + '.' + stream))
    basis = {str(p.relative_to(ROOT)): sha(p) for p in files}

    # Guard the fixed model's graph. Request inputs never contain expected masks.
    for resolver, config in configurations.items():
        root = tomllib.loads(config['Cargo.toml'])
        assert root['workspace'] == dict(members=['app', 'flags', 'defaults'], **{'default-members': ['app'], 'resolver': resolver})
        app = tomllib.loads(config['app/Cargo.toml'])
        assert app['features'] == dict(default=['fixture-flags/extra'], explicit=['fixture-flags/explicit'])
        for key, feature in [('dependencies', 'normal'), ('build-dependencies', 'build'), ('dev-dependencies', 'dev')]:
            assert app[key] == {'fixture-flags': {'path': '../flags', 'default-features': False, 'features': [feature]}}
        assert app['target'] == {'cfg(windows)': {'dependencies': {'fixture-flags': {'path': '../flags', 'default-features': False, 'features': ['platform']}}}}
        sibling = tomllib.loads(config['defaults/Cargo.toml'])
        assert sibling['dependencies'] == {'fixture-flags': {'path': '../flags'}}
        assert sibling['features'] == {'default': ['fixture-flags/sibling']}
        flags = tomllib.loads(config['flags/Cargo.toml'])['features']
        assert flags == {n: (['defaulted'] if n == 'default' else []) for n in receipt['flags']}
    original = Path(receipt['originalWork']) / 'project' / 'app'
    requests, observed, labels = [], [], []
    metadata_counterexamples = []
    for row in trace:
        case, resolver, argv = row['case'], row['resolver'], row['argv']
        if case == 'clean':
            assert row['cwd'] == str(original.parent)
            continue
        assert row['cwd'] == str(original)
        if case.startswith('metadata'):
            data = json.loads((RUN / ('r' + str(resolver) + '-' + case + '.stdout')).read_text())
            ids = {p['id']: p['name'] for p in data['packages']}
            node = next(n for n in data['resolve']['nodes'] if ids[n['id']] == 'fixture-flags')
            assert set(node['features']) == set(receipt['flags']) - {'explicit'}
            metadata_counterexamples.append(dict(resolver=resolver, case=case, mask=479))
            continue
        if case.endswith('-runtime'):
            continue
        assert argv[0] == receipt['tools']['cargo']['path']
        args = argv[1:]
        command, args = args[0], args[1:]
        assert command in ['build', 'test']
        request = dict(resolver=resolver, context='app-member-native-mac', projection='compiled-roles',
            noDefault=False, allFeatures=False, featureArg=0, workspace=False, tests=command == 'test')
        selection = None
        while args:
            arg, args = args[0], args[1:]
            if arg == '-p':
                assert selection is None and args[0] == 'fixture-app'
                selection, args = 'app', args[1:]
            elif arg == '--workspace':
                assert selection is None
                selection = 'workspace'; request['workspace'] = True
            elif arg == '--features':
                assert request['featureArg'] == 0
                request['featureArg'] = {'explicit': 1, 'fixture-app/explicit': 2}[args[0]]
                args = args[1:]
            elif arg == '--no-default-features': request['noDefault'] = True
            elif arg == '--all-features': request['allFeatures'] = True
            elif arg == '--no-run': assert command == 'test'
            else: assert arg in ['--offline', '--message-format=json'], arg
        assert selection in ['app', 'workspace']
        stem = 'r' + str(resolver) + '-' + case
        if row['outcome']['exitCode'] == 0:
            runtime_row = next(t for t in trace if t['resolver'] == resolver and t['case'] == case + '-runtime')
            assert runtime_row['outcome']['exitCode'] == 0
            raw = (RUN / (stem + '-runtime.stdout')).read_text()
            pairs = re.findall(r'FIXTURE_(APP|TEST):(\{[^\n]+\})', raw)
            assert len(pairs) == 1 and (pairs[0][0] == 'TEST') == request['tests']
            observed.append(dict(code=0, **json.loads(pairs[0][1])))
        else:
            assert row['outcome']['exitCode'] == 101
            assert 'does not have a dependency named `fixture-app`' in (RUN / (stem + '.stderr')).read_text()
            observed.append(dict(code=101, normal=None, build=None))
        requests.append(request); labels.append(stem)
    assert len(requests) == 21 and len(metadata_counterexamples) == 9
    assert sum(r['code'] == 0 for r in observed) == 20

    # Extra combinations establish model agreement only, not new Cargo evidence.
    finite = []
    for resolver, no_default, all_features, tests, arg in itertools.product(
            [1, 2, 3], [False, True], [False, True], [False, True], [0, 1]):
        finite.append(dict(requests[0], resolver=resolver, noDefault=no_default, allFeatures=all_features,
            workspace=False, tests=tests, featureArg=arg))
    for resolver in [1, 2, 3]:
        finite.append(dict(requests[0], resolver=resolver, noDefault=True, allFeatures=False,
            workspace=False, tests=False, featureArg=2))
        finite.append(dict(requests[0], resolver=resolver, noDefault=True, allFeatures=False,
            workspace=True, tests=False, featureArg=0))
    assert len(finite) == 54
    generated = HERE / 'generated'; generated.mkdir(exist_ok=True)
    path = generated / 'features.json'
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    formal = generated / 'formal'
    artifact = formal / 'applications/cargo/Features.olean'; artifact.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LEAN_PATH=str(formal), BEND_NO_TELEMETRY='1')
    compiled = subprocess.run([lean, '-DwarningAsError=true', '-o', str(artifact), str(HERE / 'Features.lean')],
        cwd=ROOT, env=env, capture_output=True, text=True)
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    def replay(value):
        path.write_text(json.dumps(value) + '\n')
        return subprocess.run([lean, '--run', 'applications/cargo/FeaturesCase.lean', str(path)], cwd=ROOT, env=env, capture_output=True, text=True)
    result = replay(dict(schema=1, cases=requests + finite))
    assert result.returncode == 0, result.stdout + result.stderr
    actual = json.loads(result.stdout)
    assert actual[:21] == observed, [(n, a, o) for n, a, o in zip(labels, actual[:21], observed, strict=True) if a != o]
    bit = lambda b: 'True{}' if b else 'False{}'
    calls = []
    for q in requests + finite:
        args = ','.join([bit(q['resolver'] == 1), bit(q['noDefault']), bit(q['allFeatures']),
            str(q['featureArg']) + 'n', bit(q['workspace']), bit(q['tests'])])
        calls.append('F.render(F.Request{' + args + '}) ++ "\\n"')
    runner = generated / 'FeaturesCase.bend'
    runner.write_text('import Base\nimport ../Features.bend as F\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(calls) + ')\n')
    result = subprocess.run([bend, str(runner)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    def text(r): return ','.join('-' if r[k] is None else str(r[k]) for k in ['code', 'normal', 'build'])
    assert result.stdout.splitlines() == [text(r) for r in actual]
    negative = [
        (dict(schema=2, cases=[]), 'Unsupported Cargo feature schema'),
        (dict(schema=1, cases=[dict(requests[0], resolver=4)]), 'Unknown Cargo resolver'),
        (dict(schema=1, cases=[dict(requests[0], context='workspace-root')]), 'Unsupported Cargo feature context'),
        (dict(schema=1, cases=[dict(requests[0], projection='metadata')]), 'Metadata is not a compiled-role projection'),
        (dict(schema=1, cases=[dict(requests[0], featureArg=3)]), 'Unknown Cargo feature argument'),
        (dict(schema=1, cases=[dict(requests[0], featureArg=2, workspace=True)]), 'Qualified syntax is outside'),
        (dict(schema=1, cases=[dict(requests[0], featureArg=0, workspace=True, allFeatures=True)]), 'Workspace root feature selection is outside'),
        (dict(schema=1, cases=[{k: v for k, v in requests[0].items() if k != 'noDefault'}]), None),
        (dict(schema=1, cases=[dict(requests[0], noDefault='false')]), None),
    ]
    for value, message in negative:
        result = replay(value)
        assert result.returncode == 2 and not result.stdout, result.stdout + result.stderr
        if message: assert message in result.stderr
    path.write_text(json.dumps(dict(schema=1, cases=requests + finite), indent=2) + '\n')
    assert all(sha(ROOT / p) == value for p, value in basis.items()), 'Evidence/model changed during replay.'
    report = dict(schema=1, basisSha256=basis, nativeBuildRuntimePairsMatchBothModels=20,
        nativeQualifiedRefusalsMatchBothModels=1, additionalFiniteModelAgreementCases=54,
        invalidResearchInputsRefused=len(negative), metadataScopeCounterexamples=metadata_counterexamples,
        cases=[dict(label=n, request=q, observed=o) for n, q, o in zip(labels, requests, observed, strict=True)],
        limits=[
            'Fixed three-package graph; macOS native normal/build/dev and inactive Windows declarations. No actual Windows compilation.',
            'Metadata observations have a broader union; no complete metadata algorithm or conditional-only package filter qualification.',
            'Forwarding follows matching admitted dependency uses; no optional/weak/renamed/proc-macro/artifact dependency qualification.',
            'Role features match runtime/build-script witnesses and compiler feature sets, not counts of new physical units.',
            'Resolver3 feature projection equals resolver2 here; no registry/MSRV fallback or general cache/fingerprint qualification.',
            'Fifty-four extra inputs compare models only. Workspace requests are restricted to the captured no-default build; other root feature selection remains unmodeled. Decoder refusals are research-interface checks, not native CLI results.',
            'Executables were measured before cleanup and are absent. Replay executes neither Cargo nor captured executables.'])
    (HERE / 'features-comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['basisSha256', 'cases', 'metadataScopeCounterexamples']}, indent=2))


if __name__ == '__main__': main()
