#!/usr/bin/env python3
"""Pure replay of retained Qt source cases; never opens or edits a Prism instance."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ADAPTER = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
RANKS = {'': 0, '1.2': 1, '1.2+left': 1, '1.2+right': 1, '1.10': 2, '1.20.1': 3, '1.22': 4}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('primary', type=Path)
    parser.add_argument('order', type=Path)
    parser.add_argument('boundary', type=Path)
    args = parser.parse_args()
    primary, order, boundary = [p.resolve() for p in [args.primary, args.order, args.boundary]]
    initial_boundary = ROOT / 'applications/evidence/prism-component-boundaries-20261124T112753590091Z'
    inputs = [HERE / name for name in ['Components.lean', 'ComponentsCase.lean', 'Components.bend']]
    inputs.append(ROOT / 'applications/sources/prism-components-selections.json')
    for root in [primary, order, boundary, initial_boundary]:
        inputs += [p for p in sorted(root.iterdir()) if p.is_file() and p.name != 'conformance.json']
    basis = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    sources = json.loads(inputs[3].read_text())
    current = {r['path']: r['sha256'] for r in sources}
    for row in sources:
        assert sha(ROOT / row['cache']) == row['sha256']

    def load(root):
        receipt = json.loads((root / 'receipt.json').read_text())
        assert sha(root / 'probe.py') == receipt['producerSha256']
        assert sha(root / 'observed.stdout') == receipt['stdoutSha256']
        assert sha(root / 'observed.stderr') == receipt['stderrSha256']
        if 'inputSha256' in receipt:
            assert sha(root / 'input.json') == receipt['inputSha256']
        if 'sources' in receipt:
            assert all(current.get(p) == digest for p, digest in receipt['sources'].items())
        rows = [json.loads(line) for line in (root / 'observed.stdout').read_text().splitlines()]
        assert len(rows) == receipt['cases']
        assert {r['qtRuntime'] for r in rows} == {receipt['qtVersion']}
        assert receipt['qtVersion'].startswith('6.') and tuple(map(int, receipt['qtVersion'].split('.')[:2])) >= (6, 4)
        return receipt, rows

    prim_rec, prim = load(primary)
    order_rec, order_rows = load(order)
    boundary_rec, boundaries = load(boundary)
    _, initial_boundaries = load(initial_boundary)
    assert order_rec['reusedCapture'] == str(primary.relative_to(ROOT))
    assert order_rec['reusedReceiptSha256'] == sha(primary / 'receipt.json')
    assert order_rec['reusedBinarySha256'] == prim_rec['binarySha256']
    assert boundary_rec['reusedReceiptSha256'] == sha(primary / 'receipt.json')
    assert len(prim) == 19 and len(order_rows) == 3 and len(boundaries) == 9
    assert len(initial_boundaries) == 7
    added_fields = {'localJar', 'jarReadOnly', 'jarExistsAfter', 'jarDirectoryModeRestored'}
    assert [{k: v for k, v in r.items() if k not in added_fields} for r in boundaries[:7]] == initial_boundaries
    raw = prim + order_rows
    requests = json.loads((primary / 'input.json').read_text())['cases'] + json.loads((order / 'input.json').read_text())['cases']
    assert [r['id'] for r in raw] == [r['id'] for r in requests]
    normalized = []
    scalar_calls, scalar_expected = [], []
    bit = lambda value: 'True{}' if value else 'False{}'

    def call(expression, expected):
        scalar_calls.append(expression)
        scalar_expected.append(expected)

    for req, observed in zip(requests, raw):
        comps = []
        actual_states = {c['uid']: c for c in observed['componentStates']}
        for c in req['components']:
            flags = {k: c.get(k, False) for k in ['dependencyOnly', 'volatile', 'custom', 'disabled', 'important']}
            comps.append(dict(uid=c['uid'], version=c.get('version', ''), **flags,
                requirements=[dict(uid=r['uid'], exact=r.get('equals', ''), hint=r.get('suggests', '')) for r in c['requires']]))
            state = actual_states[c['uid']]
            call(f'bit(P.enabled({bit(flags["important"])},{bit(flags["dependencyOnly"])},{bit(flags["disabled"])}))', str(int(state['enabled'])))
            call(f'bit(P.can_disable({bit(flags["important"])},{bit(flags["dependencyOnly"])}))', str(int(state['canDisable'])))
            if observed['gatherOK']:
                required = any(r['uid'] == c['uid'] for r in observed['requirements'])
                call(f'bit(P.obsolete({bit(flags["dependencyOnly"])},{bit(flags["volatile"])},{bit(required)}))', str(int(c['uid'] in observed['proposedRemovals'])))
        normalized.append(dict(id=req['id'], components=comps))
        if len(comps) == 2 and all(len(c['requirements']) == 1 for c in comps):
            old, new = [c['requirements'][0] for c in comps]
            assert old['uid'] == new['uid']
            call(f'bit(P.exact_ok({bit(bool(new["exact"]))},{bit(bool(old["exact"]))},{bit(new["exact"] == old["exact"])}))', str(int(observed['gatherOK'])))
            if observed['gatherOK']:
                out, = observed['requirements']
                if not out['suggests']:
                    expected = 'none'
                elif out['suggests'] == new['hint']:
                    assert new['hint'] != old['hint']
                    expected = 'incoming'
                else:
                    assert out['suggests'] == old['hint']
                    expected = 'existing'
                call(f'hint(P.hint_source({bit(bool(new["hint"]))},{bit(bool(old["hint"]))},{bit(RANKS[new["hint"]] < RANKS[old["hint"]])}))', expected)
        if observed['gatherOK']:
            index = {c['uid']: c for c in comps}
            for r in observed['requirements']:
                c = index.get(r['uid'])
                if any(x['uid'] == r['uid'] for x in observed['proposedAdditions']):
                    decision = 'missing'
                elif any(x['uid'] == r['uid'] for x in observed['proposedChanges']):
                    decision = 'adjust'
                elif observed['changePlanOK'] is False:
                    assert len(observed['requirements']) == 1
                    decision = 'locked'
                else:
                    decision = 'met'
                custom, dep = (c['custom'], c['dependencyOnly']) if c else (False, False)
                same = bool(c and c['version'] == r['equals'])
                call(f'decision(P.change({bit(c is not None)},{bit(bool(r["equals"]))},{bit(same)},P.can_adjust({bit(custom)},{bit(dep)})))', decision)

    cache_inputs, removal_inputs = [], []
    stderr = (boundary / 'observed.stderr').read_text()
    for row in boundaries:
        if row['kind'] == 'codec-cache':
            cache_inputs.append(dict(id='cache-' + str(int(row['inputVolatile'])), volatile=row['inputVolatile']))
            assert row['wire'].get('cachedVolatile', False) == row['inputVolatile'] and 'volatile' not in row['wire']
            assert row['wire']['cachedRequires'] == [{'equals': '1', 'uid': 'fixture.dep'}]
            assert row['wire']['cachedConflicts'] == [{'equals': '2', 'uid': 'fixture.bad'}]
            for name in ['decoded', 'missingMetadata', 'loadedMetadata', 'repeatedMetadata', 'changedExactSameUid']:
                assert {k: row[name][k] for k in ['uid', 'version', 'cachedVersion', 'cachedName']} == dict(uid='fixture.codec', version='1', cachedVersion='1', cachedName='Fixture')
            call(f'bit(P.current_cached_volatile({bit(row["inputVolatile"])},False{{}},False{{}}))', str(int(row['decoded']['volatile'])))
        else:
            assert row['kind'] == 'removal-loop-prefix'
            assert row['directoryModeBefore'] == row['directoryModeRestored'] == 0o755
            assert row['taskFailure'] == '' and row['taskFinalized'] is False
            # Controlled writable/read-only scenario is an input, not inferred
            # from the desired output. Actual QFile error logs qualify failures.
            patch_writable, jar_writable = not row['readOnly'], not row['jarReadOnly']
            removal_inputs.append(dict(id=row['id'], important=row['important'], patchWritable=patch_writable,
                localJar=row['localJar'], jarWritable=jar_writable))
            if row['readOnly']:
                errors = [line for line in stderr.splitlines() if '/' + row['id'] + '/fixture.volatile.json' in line and 'Permission denied' in line]
                assert len(errors) == 3
            if row['localJar']:
                assert row['jarDirectoryModeRestored'] == 0o755
                if row['jarReadOnly']:
                    errors = [line for line in stderr.splitlines() if '/' + row['id'] + '/jars/fixture.jar' in line and 'Permission denied' in line]
                    assert len(errors) == 3
            expected_ok = not row['important'] and patch_writable and (not row['localJar'] or jar_writable)
            assert row['prefixCompleted'] == expected_ok
            assert row['guarded'] == (not expected_ok)
            assert row['attemptsIncludingGuard'] == (1 if expected_ok else 4)
            assert row['saveRequests'] == row['invalidations'] == int(expected_ok)
            assert row['patchExistsAfter'] == (row['important'] or not patch_writable)
            record_expression = f'P.record_removed({bit(row["important"])},{bit(patch_writable)},{bit(row["localJar"])},{bit(jar_writable)})'
            call(f'bit(P.after_removal(True{{}},{record_expression}))', str(int(row['remainingComponents'] != 0)))
            call(f'bit(P.patch_removed({bit(row["important"])},{bit(patch_writable)}))', str(int(not row['patchExistsAfter'])))
    assert stderr.count('is non-removable') == 3
    assert len(cache_inputs) == 2 and len(removal_inputs) == 7
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)
    path = generated / 'components.json'
    input_data = dict(schema=1, profile='cached-components-v1', components=normalized, caches=cache_inputs, removals=removal_inputs)
    path.write_text(json.dumps(input_data, indent=2) + '\n')
    env = dict(os.environ, LEAN_PATH=str(ROOT / '.build/formal'), BEND_NO_TELEMETRY='1')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')

    def run_lean(data):
        return subprocess.run([lean, '--run', 'applications/prism/ComponentsCase.lean', str(data)], cwd=ROOT, env=env, capture_output=True, text=True)

    result = run_lean(path)
    assert result.returncode == 0, result.stdout + result.stderr
    actual = json.loads(result.stdout)
    expected = [{k: v for k, v in row.items() if k != 'qtRuntime'} for row in raw]
    assert actual['components'] == expected
    cache_keys = ['volatile', 'requiredExact', 'requires', 'conflicts', 'notifications']
    for observed, model in zip([r for r in boundaries if r['kind'] == 'codec-cache'], actual['caches']):
        for stage in ['decoded', 'missingMetadata', 'loadedMetadata', 'repeatedMetadata', 'changedExactSameUid']:
            assert model[stage] == {k: observed[stage][k] for k in cache_keys}
    for observed, model in zip([r for r in boundaries if r['kind'] == 'removal-loop-prefix'], actual['removals']):
        assert model['pendingAfterThree'] == (observed['remainingComponents'] != 0)
        assert model['patchPresent'] == observed['patchExistsAfter']
        assert model['jarPresent'] == (observed['jarExistsAfter'] is True)
        assert model['currentResult'] == ('prefix-complete' if observed['prefixCompleted'] else 'retry')
        assert model['proposedPending'] == (observed['remainingComponents'] != 0)
        assert model['proposedPatchPresent'] == observed['patchExistsAfter']
        assert model['proposedJarPresent'] == (observed['jarExistsAfter'] is True)
        assert model['proposedResult'] == ('prefix-complete' if observed['prefixCompleted'] else 'failed-removal')

    runner = generated / 'ComponentsCase.bend'
    runner.write_text('import Base\nimport ../Components.bend as P\n\ndef bit(v: Bool) -> String:\n  match v:\n    case True{}: "1"\n    case False{}: "0"\n\ndef decision(v: P.Decision) -> String:\n  match v:\n    case P.Met{}: "met"\n    case P.Missing{}: "missing"\n    case P.Adjust{}: "adjust"\n    case P.Locked{}: "locked"\n\ndef hint(v: P.HintSource) -> String:\n  match v:\n    case P.NoHint{}: "none"\n    case P.Incoming{}: "incoming"\n    case P.Existing{}: "existing"\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(call + ' ++ "\\n"' for call in scalar_calls) + ')\n')
    result = subprocess.run([bend, str(runner)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == scalar_expected
    negatives = []
    for change in [dict(schema=2), dict(profile='full-prism'), dict(components=[dict(normalized[1], components=normalized[1]['components'] * 2)])]:
        negatives.append(dict(input_data, **change))
    for mutation in ['unknown-hint', 'unknown-exact', 'unknown-uid', 'duplicate-requirement']:
        bad = copy.deepcopy(input_data)
        req = bad['components'][1]['components'][0]['requirements'][0]
        if mutation == 'unknown-hint': req['hint'] = '999.unknown'
        elif mutation == 'unknown-exact': req['exact'] = 'unadmitted'
        elif mutation == 'unknown-uid': req['uid'] = 'external.actual.loader'
        else: bad['components'][1]['components'][0]['requirements'].append(dict(req))
        negatives.append(bad)
    for i, data in enumerate(negatives):
        bad = generated / f'components-negative-{i}.json'
        bad.write_text(json.dumps(data))
        result = run_lean(bad)
        assert result.returncode == 2 and result.stderr
    assert all(sha(ROOT / path) == digest for path, digest in basis.items())
    report = dict(schema=1, componentCases=22, cacheTraces=2, removalPrefixCases=7, bendScalarComparisons=len(scalar_calls),
        leanRelationsMatch=True, bendScalarsMatch=True, unsupportedInputsRefused=len(negatives), adapterSha256=ADAPTER,
        sourcesChecked=len(sources), basisSha256=basis,
        counterexamples=['rank equivalence is not exact identity', 'equal-ranked suggestion merge need not commute',
            'obsolete proposal does not ensure removal can succeed', 'checkOnly does not bypass obsolete-removal prefix',
            'cachedVolatile does not roundtrip through the current selected codec', 'unchanged metadata need not emit another notification',
            'a false removal result can follow successful patch deletion'],
        proposed='Stop with a failure result when removal fails; retain the component record and report any confirmed partial file effects. No product implementation or universal retry policy selected.',
        limits=['Selected cached-component source functions with fixture constructors/loading/JSON conversion/QObject/save adapters, not full native Prism.',
            'Ranks admit only selected strings and ASCII fixture UIDs; no general FlexVer/Qt codec or complete graph/resolution qualification.',
            'Real owned QFile permission refusals, zero or one local JAR at a fixture-supplied path; one-candidate stable snapshot. Fourth-call guard is fixture-only; no actual product limit.',
            'Cache projection has one required/conflicting entry and fixed identity/name/version; actual root publication, refresh acquisition and whole-profile persistence unqualified.',
            'No collection, compiler, launcher, network, JVM or desktop execution in this replay. Source caches remain owner-local.'])
    (primary / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'basisSha256'}, indent=2))


if __name__ == '__main__':
    main()
