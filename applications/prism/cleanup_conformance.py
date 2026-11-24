#!/usr/bin/env python3
"""Replay frozen Prism cleanup/record fragments; never run the native probe."""
import base64
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import update_observations as retained

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = retained.CAPTURE
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
CHOICES = dict(NotAsked=0, Yes=1, No=2)


def main():
    with contextlib.redirect_stdout(io.StringIO()): retained.main()
    spec = json.loads((RUN / 'input.json').read_text())
    rows = {r['id']: r for r in map(json.loads, (RUN / 'observed.stdout').read_text().splitlines())}
    pins = ROOT / 'applications/sources/prism-update-selections.json'
    basis_files = [HERE / n for n in ['Cleanup.lean', 'CleanupCase.lean', 'Cleanup.bend',
        'cleanup_conformance.py', 'update_observations.py', 'update-observations.json']]
    basis_files.append(pins)
    basis_files += [ROOT / p['cache'] for p in json.loads(pins.read_text())]
    for capture in [RUN, retained.FIRST]:
        basis_files += [p for p in capture.iterdir() if p.is_file()]
    basis = {str(p.relative_to(ROOT)): sha(p) for p in basis_files}
    cases_root = RUN / 'work/cases'

    def cells(frame, root, targets):
        result = []
        for path, node in sorted(frame.items()):
            kind = dict(file=0, directory=1).get(node['kind'])
            target = None
            if node['kind'] == 'symlink':
                kind = 3 if node['exists'] else 2
                target = os.path.relpath(node['target'], root)
            assert kind is not None
            result.append(dict(path=path, kind=kind, **(dict(target=target) if targets else {})))
        return result

    inputs, expected, labels, native = [], [], [], []
    for item in spec['cleanup'] + spec['overrides']:
        row = rows[item['id']]; direct = row['kind'] == 'cleanup'
        root = cases_root / item['id'] / ('game' if direct else 'installed-game')
        before, after = (row['before'], row['after']) if direct else (row['gameBefore'], row['gameAfter'])
        assert set(after) <= set(before) and all(before[k] == value for k, value in after.items())
        q = dict(kind=row['kind'], choice=CHOICES[item['saveChoice']] if direct else 0,
            answers=[CHOICES[a] for a in item['answers']] if direct else [],
            requests=[dict(path=r['path'], pairDisabled=r['checkDisabled']) for r in item['requests']] if direct else [],
            overrideExisting=item['overrideExisting'] if direct else True,
            cells=cells(before, root, True), paths=[] if direct else sorted(item['files']), name='' if direct else item['name'])
        e = dict(choice=CHOICES[row['saveChoice']] if direct else 0, prompts=row['prompts'], paths=row['normalized'],
            remaining=cells(after, root, False), failed=bool(row['failure']), cleanupPassed=row['cleanupPassed'],
            recordRefused=False, records=[] if direct else row['read'])
        inputs.append(q); expected.append(e); labels.append(item['id']); native.append(row)
    assert len(inputs) == 30
    generated = HERE / 'generated'; formal = generated / 'formal'
    artifact = formal / 'applications/prism/Cleanup.olean'; artifact.parent.mkdir(parents=True, exist_ok=True)
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    env = dict(os.environ, LEAN_PATH=str(formal), BEND_NO_TELEMETRY='1')
    compiled = subprocess.run([lean, '-DwarningAsError=true', '-o', str(artifact), 'applications/prism/Cleanup.lean'],
        cwd=ROOT, env=env, capture_output=True, text=True)
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    path = generated / 'cleanup.json'
    def replay(value):
        path.write_text(json.dumps(value) + '\n')
        return subprocess.run([lean, '--run', 'applications/prism/CleanupCase.lean', str(path)], cwd=ROOT, env=env, capture_output=True, text=True)
    data = dict(schema=1, profile='qt6-mac-relative-static-links', cases=inputs)
    result = replay(data); assert result.returncode == 0, result.stdout + result.stderr
    actual = json.loads(result.stdout); assert len(actual) == 30
    changes = []
    def comparable(value, override):
        value = copy.deepcopy(value)
        if override:
            for field in ['paths', 'records']:
                if field in value: value[field].sort()
        return value
    for name, q, a, e in zip(labels, inputs, actual, expected, strict=True):
        override = q['kind'] == 'overrides'
        assert comparable(a['current'], override) == comparable(e, override), (name, a['current'], e)
        if comparable(a['current'], override) != comparable(a['proposed'], override): changes.append(name)
        if override:
            p = a['proposed']
            original = next(i for i in spec['overrides'] if i['id'] == name)
            before_paths = {c['path'] for c in q['cells']}
            remaining = {c['path'] for c in p['remaining']}
            if any('\n' in s or '\r' in s for s in original['files']):
                assert p['recordRefused'] and remaining == before_paths
            else:
                assert not p['recordRefused']
                assert set(original['canaries']) <= remaining
                assert remaining == before_paths - set(original['files'])
    assert set(changes) == {'save-dot-prefix', 'save-parent-prefix', 'save-dot-cached-no', 'save-parent-cached-no',
        'list-marker-in-filename', 'list-marker-in-directory', 'list-whitespace', 'list-client-marker', 'list-newline', 'list-unicode-whitespace'}
    for label in ['save-dot-prefix', 'save-parent-prefix', 'save-dot-cached-no', 'save-parent-cached-no']:
        index = labels.index(label)
        assert actual[index]['proposed']['remaining'] == [dict(path=c['path'], kind=c['kind']) for c in inputs[index]['cells']]

    # Bend implements scheduling, record text and failure aggregation only.
    # It does not independently model the complete typed filesystem mutation.
    bit = lambda b: 'True{}' if b else 'False{}'
    choice = lambda n: 'F.' + ['Unasked', 'Yes', 'No'][n] + '{}'
    quote = lambda s: json.dumps(s, ensure_ascii=False)
    strings = lambda ss: '[' + ','.join(quote(s) for s in ss) + ']'
    calls, bend_expected, kinds = [], [], []
    for q, a in zip(inputs, actual, strict=True):
        if q['kind'] == 'cleanup':
            # Derived from original input, not the observed or Lean plan.
            requests = '[' + ','.join('F.CleanupRequest{' + ','.join([quote(r['path']),
                quote(os.path.normpath(r['path'])), bit(r['pairDisabled'])]) + '}' for r in q['requests']) + ']'
            initial = 'F.CleanupPlan{' + choice(q['choice']) + ',0n,[],[' + ','.join(choice(c) for c in q['answers']) + '],False{}}'
            for proposed in [False, True]:
                calls.append('F.render(F.plan(' + requests + ',' + initial + ',' + bit(proposed) + '))')
                outcome = a['proposed' if proposed else 'current']
                bend_expected.append({k: outcome[k] for k in ['choice', 'prompts', 'paths']} | dict(unknown=False)); kinds.append('schedule')
            directories = sorted(c['path'] for c in q['cells'] if c['kind'] == 1)
            # Failure consumes the admitted Bend plan, not every requested path
            # and not a native or Lean failure outcome supplied as input.
            calls.append('F.boolean(F.failure_summary(F.plan(' + requests + ',' + initial + ',False{}),' +
                strings(directories) + ',' + bit(q['overrideExisting']) + '))')
            bend_expected.append(a['current']['failed']); kinds.append('failure')
        else:
            calls.append('F.strings(F.read_records(' + quote(q['name']) + ',' + strings(q['paths']) + '))')
            bend_expected.append(a['current']['records']); kinds.append('records')
    runner = generated / 'CleanupCases.bend'
    runner.write_text('import Base\nimport ../Cleanup.bend as F\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(c + ' ++ "\\n"' for c in calls) + ')\n')
    result = subprocess.run([bend, str(runner)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    outputs = [json.loads(line) for line in result.stdout.splitlines()]; assert len(outputs) == 74
    for kind, observed, e in zip(kinds, outputs, bend_expected, strict=True):
        assert (sorted(observed) == sorted(e)) if kind == 'records' else observed == e, (kind, observed, e)

    negative = [dict(data, schema=2), dict(data, profile='windows')]
    first = copy.deepcopy(inputs[0]); save = copy.deepcopy(inputs[1]); linked = copy.deepcopy(inputs[20])
    assert labels[20] == 'valid-link-only'
    for change in [dict(kind='publish'), dict(choice=3), dict(answers=[0]), dict(overrideExisting='yes')]:
        negative.append(dict(data, cases=[dict(first, **change)]))
    negative.append(dict(data, cases=[dict(save, answers=[])]))
    for path_name in ['/absolute.txt', 'mods/../../escape', 'bad\x00name']:
        negative.append(dict(data, cases=[dict(first, requests=[dict(path=path_name, pairDisabled=False)])]))
    for cell in [dict(path='new', kind=4, target=None), dict(path='./new', kind=0, target=None),
                 dict(path='new', kind=3, target=None)]:
        negative.append(dict(data, cases=[dict(first, cells=[cell])]))
    negative.append(dict(data, cases=[dict(first, cells=first['cells'] * 2)]))
    negative.append(dict(data, cases=[dict(linked, requests=[dict(path='payload.jar', pairDisabled=False)])]))
    negative.append(dict(data, cases=[dict(linked, requests=[dict(path='mods/link.jar/child', pairDisabled=False)])]))
    override = copy.deepcopy(inputs[22]); assert override['kind'] == 'overrides'
    for change in [dict(name='server-overrides'), dict(paths=['config/my-overrides😀tail']),
        dict(requests=[dict(path='x', pairDisabled=False)])]: negative.append(dict(data, cases=[dict(override, **change)]))
    for value in negative:
        r = replay(value); assert r.returncode == 2 and r.stderr and not r.stdout, r.stdout + r.stderr
    path.write_text(json.dumps(data, indent=2) + '\n')
    assert all(sha(ROOT / p) == digest for p, digest in basis.items()), 'Input changed during replay.'
    report = dict(schema=1, basisSha256=basis, currentLeanCleanupCasesMatch=22, currentLeanJoinedRecordEffectCasesMatch=8,
        currentBendSchedulingCasesMatch=22, currentBendRecordBagsMatch=8, currentBendFailureSummariesMatch=22,
        proposedSchedulingLeanBendAgree=22, proposedLeanEffectDifferences=changes, malformedResearchInputsRefused=len(negative),
        limits=['Exact retained source fragments with explicit initial cache/dialog adapters, not native constructor or full importer qualification.',
            'Lean models typed static nodes and lexical relative paths. Decoder rejects mutated link referents/symlinked ancestors; no general realpath or dynamic symlink model.',
            'Bend projects scheduling/record text/failure aggregation. It does not independently reproduce the whole typed filesystem cleanup.',
            'Override record and planned-path comparison uses bags, not filesystem iterator order. Joined final effects match only these captured cases.',
            'String slicing starts and whitespace are the captured profile; no full QString UTF-16 or Unicode-whitespace equivalence.',
            'Proposals are pure models. Existing damaged historical records are not reconstructed, and no seed ownership or automatic rollback is introduced.',
            'Research input refusals are Lean decoder checks, not production Prism refusals. Native helper process exit zero is collection completion, not each task result.',
            'No archive extraction, network, incoming overlay, complete staging/publication, GUI, game launch or supported-platform matrix qualification.'])
    (HERE / 'cleanup-comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'basisSha256'}, indent=2))


if __name__ == '__main__': main()
