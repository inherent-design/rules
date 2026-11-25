#!/usr/bin/env python3
"""Check that retained range outcomes satisfy composed source/API contracts."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
CAPTURE = 'evidence/range-1.21.4-20261125T093433562856Z'


def project_native(row):
    raw = row['input']; values, query, index = raw['thresholds'], raw['query'], row['index']
    assert type(values) is list and len(values) <= 32 and values == sorted(values)
    assert all(type(n) is int and 0 <= n <= 32 for n in values)
    assert type(query) is int and -1 <= query <= 32 and type(index) is int and -1 <= index < len(values)
    for name in ['nativeThresholdsBefore','nativeThresholdsAfter']:
        assert type(row[name]) is list and all(type(v) in (int,float) and math.isfinite(v) and (v != 0 or math.copysign(1,v) > 0) for v in row[name])
    v = row['nativeQuery']
    assert type(v) in (int,float) and math.isfinite(v) and (v != 0 or math.copysign(1,v) > 0)
    assert row['nativeThresholdsBefore'] == row['nativeThresholdsAfter'] == values and row['nativeQuery'] == query
    assert not row.get('observerError')
    return dict(kind='game-floor', values=[v + 1 for v in values], query=query + 1, present=index >= 0, index=max(0, index), found=False)


def bend_expression(row):
    n = lambda v: str(v) + 'n'
    b = lambda v: 'True{}' if v else 'False{}'
    values = 'Nil{}'
    for value in reversed(row['values']):
        values = 'Con{' + n(value) + ',' + values + '}'
    result = 'Some{' + n(row['index']) + '}' if row['present'] else 'None{}'
    if row['kind'] == 'api-result':
        return 'A.as_binary_result(' + ','.join([values, n(row['query']), b(row['found']), n(row['index'])]) + ')'
    function = 'R.ri_admitted' if row['kind'] == 'game-floor' else 'A.as_binary_floor'
    return function + '(' + ','.join([values, n(row['query']), result]) + ')'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    capture = HERE / CAPTURE
    receipt = json.loads((capture / 'receipt.json').read_text())
    observed = json.loads((capture / 'observed.json').read_text())
    target = next(t for t in json.loads((HERE / 'targets.json').read_text())['javaReferences'] if t['release'] == '1.21.4')
    catalog = json.loads((HERE / 'java1214-registry-catalog.json').read_text())
    assert receipt['target'] == catalog['target'] == target['id']
    assert receipt['clientSha256'] == catalog['clientSha256'] == target['source']['clientSha256']
    assert receipt['mappingSha256'] == catalog['mappingSha256']
    assert receipt['observerErrors'] == observed['observerErrors'] == 0 and receipt['profile']['JAVA_VERSION'].startswith('21.')
    source = catalog['sources'][target['id'] + ':net.minecraft.client.renderer.item.RangeSelectItemModel']
    assert source['originalClassMember'] == receipt['originalClassMember'] and source['originalClassSha256'] == receipt['originalClassSha256']
    assert receipt['loadedOriginalClassMembersSha256'][receipt['originalClassMember']] == receipt['originalClassSha256']
    for n, digest in receipt['sourcesSha256'].items():
        assert sha(capture / n) == digest
    assert sha(capture / 'observed.json') == receipt['observedSha256'] and sha(capture / 'bindings.json') == receipt['bindingsSha256']
    assert all(c['exitCode'] == 0 and c['ownedGroupAbsent'] and not c['timedOut'] for c in receipt['commands'])
    for stem, command in zip(['compile', 'execute'], receipt['commands']):
        for stream in ['stdout', 'stderr']:
            assert sha(capture / (stem + '.' + stream)) == command[stream + 'Sha256']
    requests = json.loads((capture / 'range1214_cases.json').read_text())
    native = observed['cases']
    assert len(native) == receipt['cases'] == 76 and [r['input'] for r in native] == requests['cases']
    rows = [project_native(r) for r in native]
    doc = json.loads((HERE.parent / 'java/array-search-cases.json').read_text())
    assert [r['javaMajor'] for r in doc['references']] == [17,21,25] and len(doc['cases']) == 19
    rows += [{k: r[k] for k in ['kind','values','query','present','index','found']} for r in doc['cases']]
    answers = [True] * len(native) + [r['expected'] for r in doc['cases']]
    work = ROOT / '.build/minecraft/range1214-replay'
    work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LEAN_PATH=os.environ.get('LEAN_PATH', str(ROOT / '.build/formal')), BEND_NO_TELEMETRY='1')
    envelope = lambda rs: dict(schema=1, target='java-1.21.4-vanilla', hostContract='java17-21-25-arrays-float-ordered-integer-subset', cases=rs)
    def lean_run(request, name):
        path = work / (name + '.json'); path.write_text(json.dumps(request) + '\n')
        return subprocess.run([os.environ.get('LEAN', 'lean'), '--run', str(HERE / 'RangeIndexCase.lean'), str(path)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=45)
    def bend_run(rs, name):
        path = work / (name + '.bend')
        path.write_text('import Base\nimport ../../../host/minecraft/RangeIndex.bend as R\nimport ../../../host/java/ArraySearch.bend as A\ndef bit(b: Bool) -> String:\n  Bool.pick(String,b,"1","0")\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join('bit(' + bend_expression(r) + ') ++ "\\n"' for r in rs) + ')\n')
        result = subprocess.run([os.environ.get('BEND', 'bend'), str(path)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=45)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout.splitlines()
    result = lean_run(envelope(rows), 'cases')
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == answers
    assert bend_run(rows, 'Cases') == ['1' if a else '0' for a in answers]
    negatives = [dict(envelope(rows),schema=2), dict(envelope(rows),target='java-1.21.5-vanilla'),
                 dict(envelope(rows),hostContract='java18'), envelope([dict(rows[0],kind='other')])]
    for field, value in [('values',[2,1]), ('values',[1]*33), ('query',34), ('index',33)]:
        negatives.append(envelope([dict(rows[0], **{field:value})]))
    for i, request in enumerate(negatives):
        assert lean_run(request, 'negative-' + str(i)).returncode == 2
    changes = [('equal-15-query-1',7), ('equal-16-query-1',16), ('unique-16-query-15',14), ('equal-16-query-0',0), ('unique-32-query-32',30)]
    for i, (case, value) in enumerate(changes):
        raw = copy.deepcopy(next(r for r in native if r['case'] == case)); raw['index'] = value
        # Out-of-range native output fails projection; other changed results must
        # fail the composed contract. Legal duplicate alternatives are separate.
        try:
            variant = project_native(raw)
        except AssertionError:
            continue
        result = lean_run(envelope([variant]), 'changed-' + str(i))
        assert result.returncode == 0 and json.loads(result.stdout) == [False]
        assert bend_run([variant], 'Changed' + str(i)) == ['0']
    raw = next(r for r in native if r['case'] == 'equal-16-query-1')
    legal = []
    for value in [0,15]:
        variant = copy.deepcopy(raw); variant['index'] = value; legal.append(project_native(variant))
    result = lean_run(envelope(legal), 'legal-alternatives')
    assert result.returncode == 0 and json.loads(result.stdout) == [True,True]
    assert bend_run(legal, 'LegalAlternatives') == ['1','1']
    for mode in range(5):
        changed = copy.deepcopy(native[0] if mode < 3 else next(r for r in native if r["case"] == "equal-0-query-0"))
        if mode == 0:
            changed['nativeQuery'] = 20
        elif mode == 1:
            changed['nativeThresholdsAfter'] = [3]
        elif mode == 2:
            changed['observerError'] = 'mutated'
        else:
            changed['nativeQuery'] = False if mode == 3 else -0.0
        try:
            project_native(changed)
        except AssertionError:
            pass
        else:
            raise AssertionError('Changed readback admitted')
    basis = sorted(capture.iterdir()) + [HERE/n for n in ['RangeIndex.lean','RangeIndex.bend','RangeIndexCase.lean','range1214_conformance.py','java1214-registry-catalog.json','targets.json']] + [HERE.parent/'java'/n for n in ['ArraySearch.lean','ArraySearch.bend','array-search-cases.json']]
    report = dict(schema=1,status='passed-composed-contract',nativeOutcomesAdmitted=76,authoredContractCases=19,
        decoderRefusals=len(negatives),invalidNativeOutcomeControls=len(changes),legalUnobservedDuplicateAlternatives=2,
        changedReadbackRefusals=5,basisSha256={str(p.relative_to(ROOT)):sha(p) for p in basis if p.is_file()},
        limits=['Contract admits native outcomes; it does not predict a stable matching-duplicate index.',
                'Alternative indices are authored legal cases, not additional JVM observations.',
                'Integer-valued finite float subset only; signed zero, NaN, infinities and arbitrary fractions remain outside this adapter.',
                'No item property evaluation, model/bake/render execution, other JVM builds, or cross-platform runtime qualification.'])
    if args.output:
        args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','nativeOutcomesAdmitted','authoredContractCases','decoderRefusals','invalidNativeOutcomeControls','legalUnobservedDuplicateAlternatives','changedReadbackRefusals']}))


if __name__ == '__main__':
    main()
