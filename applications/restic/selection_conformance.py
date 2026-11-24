#!/usr/bin/env python3
"""Replay captured snapshot filtering, grouping and previews without running restic."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ADAPTER = sha(Path(__file__))


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    receipt = json.loads((run / 'receipt.json').read_text()); trace = json.loads((run / 'trace.json').read_text())
    definitions = json.loads((run / 'snapshots.json').read_text()); native_cases = json.loads((run / 'cases.json').read_text())
    assert len(trace) == receipt['commands'] == 21 and len(definitions) == receipt['snapshots'] == 6
    assert len(native_cases) == receipt['cases'] == 12
    assert sha(run / 'probe.py') == receipt['producerSha256']
    extension = run / 'latest-selector'; extra = json.loads((extension / 'receipt.json').read_text())
    assert sha(extension / 'probe.py') == extra['producerSha256'] and sha(run / 'receipt.json') == extra['basisReceiptSha256']
    assert extra['observed']['before'] == extra['observed']['after'] == trace[-1]['observed']['after']
    assert not extra['outcome']['timedOut'] and extra['outcome']['exitCode'] == 0
    assert extra['argv'][-2:] == ['snapshots', 'latest']
    inputs = [HERE / p for p in ['Selection.lean', 'Selection.bend', 'SelectionCase.lean']]
    inputs.append(Path(__file__))
    assert sha(Path(__file__)) == ADAPTER, 'Replay producer changed after module entry.'
    inputs += [ROOT / 'applications/sources/restic-selection-selections.json']
    inputs += [run / p for p in ['receipt.json', 'trace.json', 'snapshots.json', 'cases.json', 'probe.py']]
    inputs += [extension / p for p in ['receipt.json', 'probe.py', 'stdout', 'stderr']]
    for stream in ['stdout', 'stderr']: assert sha(extension / stream) == extra['observed'][stream + 'Sha256']
    for row in trace:
        assert not row['outcome']['timedOut'] and row['outcome']['exitCode'] == 0
        for stream in ['stdout', 'stderr']:
            p = run / (row['operation'] + '.' + stream); inputs.append(p)
            assert sha(p) == row['observed'][stream + 'Sha256']
    basis = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    for source in json.loads((ROOT / 'applications/sources/restic-selection-selections.json').read_text())['sources']:
        assert sha(ROOT / source['cache']) == source['sha256']
    original = json.loads((run / 'snapshots-all.stdout').read_text())
    assert {s['id'] for s in original} == {s['id'] for s in json.loads((run / 'snapshots-after-previews.stdout').read_text())}
    assert len({s['id'] for s in definitions}) == len({s['timeRank'] for s in definitions}) == 6
    snapshots = []
    for spec in definitions:
        sn = next(s for s in original if s['id'] == spec['id'])
        assert sn['hostname'] == spec['host'] and sn['paths'] == [spec['path']] and sorted(sn['tags']) == sorted(spec['tags'])
        assert sn['time'].startswith(f'2026-01-{spec["timeRank"]:02d}T00:00:00')
        snapshots.append(dict(id=spec['id'], host=spec['host'], paths=sn['paths'], tags=sn['tags'], rank=spec['timeRank']))
    ids = {s['id']: s for s in snapshots}
    label = {s['id']: s['label'] for s in definitions}
    rows = {r['operation']: r for r in trace}
    base = rows['snapshots-all']['observed']['after']
    for row in trace[8:]: assert row['observed']['before'] == row['observed']['after'] == base
    cases, expected, filter_checks, newest_checks, keep_checks, summaries = [], [], [], [], [], []
    def flatten(value):
        if value and 'snapshots' in value[0]: return [s for group in value for s in group['snapshots']]
        return value or []
    def same(a, b, group):
        return all(a[field] == b[field] if field == 'host' else sorted(a[field]) == sorted(b[field]) for field in group.split(',') if field)
    for native in [*native_cases, {'id': 'explicit-latest', 'operation': 'latest-id', 'groupBy': ''}]:
        op = native['operation']; f = native.get('filter', {'hosts': [], 'paths': [], 'tags': []})
        case = dict(operation=op, hosts=f['hosts'], paths=f['paths'], tags=f['tags'], groupBy=native.get('groupBy', ''), keepTags=native.get('keepTags', []))
        if op == 'latest-id': value = json.loads((extension / 'stdout').read_text())
        else:
            row = rows[native['id']]; argv = row['argv'][row['argv'].index('--json') + 1:]
            value = json.loads((run / (native['id'] + '.stdout')).read_text())
            if op == 'select':
                flags = [v for host in f['hosts'] for v in ['--host', host]] + [v for p in f['paths'] for v in ['--path', p]] + [v for tags in f['tags'] for v in ['--tag', ','.join(tags)]]
                assert argv == ['snapshots', *flags]
            elif op == 'latest': assert argv == ['snapshots', '--latest', '1', '--group-by', native['groupBy']]
            else:
                assert argv[:4] == ['forget', '--keep-last', '1', '--dry-run']
                actual_group = argv[argv.index('--group-by') + 1] if '--group-by' in argv else 'host,paths'
                assert actual_group == case['groupBy']
                actual_tags = [argv[i + 1].split(',') for i, item in enumerate(argv) if item == '--keep-tag']
                assert actual_tags == case['keepTags']
        if op == 'keep':
            kept = [s['id'] for group in value for s in group['keep'] or []]
            removed = [s['id'] for group in value for s in group['remove'] or []]
            assert not set(kept) & set(removed) and set(kept) | set(removed) == set(ids)
            # The native group keys are also checked against their member records.
            fields = {'host': 'host', 'paths': 'paths', 'tags': 'tags'}
            for group in value:
                members = [*(group['keep'] or []), *(group['remove'] or [])]
                for item in members:
                    sn = ids[item['id']]
                    for field, key in fields.items():
                        expected_key = sn[field] if field in case['groupBy'].split(',') else '' if field == 'host' else []
                        assert (group[key] or ('' if field == 'host' else [])) == expected_key or (field != 'host' and sorted(group[key] or []) == sorted(expected_key))
            result = dict(selected=[], kept=sorted(kept), removed=sorted(removed))
        else:
            selected = [s['id'] for s in flatten(value)]
            assert len(selected) == len(set(selected)) and set(selected) <= set(ids)
            result = dict(selected=sorted(selected), kept=[], removed=[])
        cases.append(case); expected.append(result)
        summaries.append({'case': native['id'], **{key: sorted(label[i] for i in result[key]) for key in result}})
        if op == 'select':
            for sn in snapshots:
                host_ok = not f['hosts'] or sn['host'] in f['hosts']; path_ok = all(p in sn['paths'] for p in f['paths'])
                tag_ok = not f['tags'] or any(all(t in sn['tags'] for t in tags) for tags in f['tags'])
                filter_checks.append((host_ok, path_ok, tag_ok, sn['id'] in result['selected']))
        else:
            group = 'host,paths' if op == 'latest' and not case['groupBy'] else case['groupBy']
            for sn in snapshots:
                newer = False
                for other in snapshots:
                    same_key = same(sn, other, group); later = other['rank'] > sn['rank']
                    newest_checks.append((same_key, later, same_key and later)); newer |= same_key and later
                tagged = bool(case['keepTags']) and any(all(t in sn['tags'] for t in tags) for tags in case['keepTags'])
                keep_checks.append((newer, tagged, sn['id'] in (result['kept'] if op == 'keep' else result['selected'])))
    generated = HERE / 'generated'; generated.mkdir(exist_ok=True); path = generated / 'selection.json'
    env = dict(os.environ, LEAN_PATH=os.pathsep.join(str(ROOT / p) for p in ['.build', '.build/formal']), BEND_NO_TELEMETRY='1')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    def replay(value):
        path.write_text(json.dumps(value) + '\n')
        return subprocess.run([lean, '--run', 'applications/restic/SelectionCase.lean', str(path)], cwd=ROOT, env=env, capture_output=True, text=True)
    data = {'schema': 1, 'snapshots': snapshots, 'cases': cases}
    result = replay(data); assert result.returncode == 0, result.stdout + result.stderr; assert json.loads(result.stdout) == expected
    bit = lambda b: 'True{}' if b else 'False{}'
    calls = ['bit(P.filter_match(' + ','.join(bit(x) for x in item[:3]) + ')) ++ "\\n"' for item in filter_checks]
    calls += ['bit(P.newer_same_group(' + ','.join(bit(x) for x in item[:2]) + ')) ++ "\\n"' for item in newest_checks]
    calls += ['bit(P.retained(' + ','.join(bit(x) for x in item[:2]) + ')) ++ "\\n"' for item in keep_checks]
    runner = generated / 'SelectionCase.bend'; runner.write_text('import Base\nimport ../Selection.bend as P\n\ndef bit(b: Bool) -> String:\n  match b:\n    case True{}: "1"\n    case False{}: "0"\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(calls) + ')\n')
    result = subprocess.run([bend, str(runner)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == [str(int(item[-1])) for item in [*filter_checks, *newest_checks, *keep_checks]]
    refused = []
    invalids = [('schema', dict(data, schema=2), 'Unsupported restic-selection schema'),
        ('group', dict(data, cases=[dict(cases[0], groupBy='unknown')]), 'Unknown snapshot grouping profile'),
        ('operation', dict(data, cases=[dict(cases[0], operation='prune')]), 'Unknown snapshot-selection operation'),
        ('untagged', dict(data, cases=[dict(cases[0], tags=[['']])]), 'Untagged selector'),
        ('tied-time', dict(data, snapshots=[snapshots[0], dict(snapshots[1], rank=snapshots[0]['rank'])]), 'Unique snapshot identities and timestamps required')]
    for name, invalid, diagnostic in invalids:
        result = replay(invalid); assert result.returncode == 2 and diagnostic in result.stderr; refused.append(name)
    path.write_text(json.dumps(data, indent=2) + '\n')
    assert all(sha(ROOT / p) == h for p, h in basis.items()), 'Inputs changed during replay.'
    report = {'schema': 1, 'adapterSha256': ADAPTER, 'basisSha256': basis, 'nativeCommands': 22,
        'originalCommands': 21, 'laterReadOnlyCommands': 1, 'snapshots': 6, 'leanNativeCases': len(cases),
        'bendFilterChecks': len(filter_checks), 'bendNewerGroupChecks': len(newest_checks), 'bendKeepChecks': len(keep_checks),
        'bothModelsMatch': True, 'refusedInputs': refused, 'observedLabels': summaries,
        'rejectedInterpretations': ['Keep-last-one means one snapshot in the whole repository under every grouping.',
            'Empty group-by has interchangeable latest-selection meaning in snapshots and forget.',
            'A comma-separated tag list means OR, or repeated tag options mean AND.',
            'Keep-tag restricts the retained set to tagged snapshots only.', 'A previewed remove set means references or data were deleted.'],
        'limits': ['Unique ordered timestamps, keep-last-one and selected nonempty tag filters only; no tie/empty-tag/calendar/count-generalization proof.',
            'Lean implements grouping/filter/newest projection; Bend consumes independently checked equality/order/match facts, not a source decoder or sorting algorithm. Comparisons use membership, not presentation order.',
            'All policy operations are previews; scoped reference/pack hashes remain unchanged. No deletion/prune, remote/backend/lock/concurrency qualification.']}
    (run / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['basisSha256', 'observedLabels']}, indent=2))


if __name__ == '__main__': main()
