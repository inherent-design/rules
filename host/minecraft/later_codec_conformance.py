#!/usr/bin/env python3
"""Replay retained 26.3 decoder observations; never launch a JVM or game."""
import argparse
import copy
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
DIRECTIONS = {s: i + 1 for i, s in enumerate(['down', 'up', 'north', 'south', 'west', 'east'])}


def bounded(value, maximum=1000):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError('Outside the selected nonnegative integer profile')
    return value


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Unsupported numeric token')
    n = Decimal(str(value))
    negative = n < 0
    n = abs(n)
    whole = int(n)
    fraction = (n - whole) * 10
    if whole > 1000 or fraction != int(fraction) or (negative and fraction):
        raise ValueError('Unsupported decimal token profile')
    return dict(negative=negative, whole=whole, fraction=int(fraction))


def pack_endpoint(value, top):
    tokens = value if type(value) is list else [value]
    if not 1 <= len(tokens) <= 2:
        raise ValueError('Unsupported pack endpoint shape')
    tokens = [bounded(v) for v in tokens]
    return dict(major=tokens[0], minor=tokens[1] if len(tokens) == 2 else (2147483647 if top else 0))


def project(row):
    """Build model input from request only, without reading its outcome."""
    action, raw = row['action'], row['input']
    if action == 'rotation':
        if type(raw) is not dict or set(raw) - {'rotation'}:
            raise ValueError('Unsupported rotation root')
        present = 'rotation' in raw
        r = raw.get('rotation', {})
        if type(r) is not dict or set(r) - {'origin', 'axis', 'angle', 'x', 'y', 'z', 'rescale'}:
            raise ValueError('Unsupported rotation fields')
        if 'origin' in r and r['origin'] != [8, 8, 8]:
            raise ValueError('Unselected origin profile')
        if 'axis' in r and type(r['axis']) is not str:
            raise ValueError('Unsupported axis token')
        if type(r.get('rescale', False)) is not bool:
            raise ValueError('Unsupported rescale token')
        scalar = 'axis' in r or 'angle' in r
        return dict(kind='rotation', data=dict(present=present, originValid='origin' in r,
            axisPresent='axis' in r, anglePresent='angle' in r,
            xyzPresent=any(k in r for k in ['x', 'y', 'z']),
            axis={'x': 1, 'y': 2, 'z': 3}.get(r.get('axis', '').lower(), 0),
            angle=bounded(r.get('angle', 0), 360),
            **{k: (0 if scalar else bounded(r.get(k, 0), 360)) for k in ['x', 'y', 'z']},
            rescale=r.get('rescale', False)))
    if action == 'shade':
        if type(raw) is not dict or set(raw) - {'shade_direction_override', 'shade'}:
            raise ValueError('Unsupported shade input')
        token = raw.get('shade_direction_override')
        if token is not None and type(token) is not str:
            raise ValueError('Unsupported direction token')
        return dict(kind='shade', data=dict(present='shade_direction_override' in raw,
            direction=DIRECTIONS.get(token, 0)))
    if action in ['format-bottom', 'format-top']:
        tokens = raw if type(raw) is list else [raw]
        return dict(kind='format', data=dict(top=action == 'format-top', tokens=[number(v) for v in tokens]))
    if action in ['pack-resource', 'pack-data']:
        if type(raw) is not dict or set(raw) - {'min_format', 'max_format', 'pack_format', 'supported_formats'}:
            raise ValueError('Unsupported pack fields')
        old = raw.get('supported_formats')
        if old is not None:
            if type(old) is not list or len(old) != 2:
                raise ValueError('Unsupported legacy range')
            old = [bounded(v) for v in old]
        return dict(kind='pack', data=dict(threshold=64 if action == 'pack-resource' else 81,
            lower=pack_endpoint(raw['min_format'], False) if 'min_format' in raw else None,
            upper=pack_endpoint(raw['max_format'], True) if 'max_format' in raw else None,
            main=bounded(raw['pack_format']) if 'pack_format' in raw else None, old=old))
    raise ValueError('Unselected action')


def observed(row):
    o = row['observed']
    assert not o.get('observerError'), 'Harness failure is not a product refusal'
    assert type(o['accepted']) is bool
    if not o['accepted']:
        assert 'error' in o or 'exception' in o
        return 'refused'
    v, action = o['value'], row['action']
    if action == 'rotation':
        if v['kind'] == 'absent':
            return 'ok:0/0/0/0/0/0/0'
        assert v['origin'] == [0.5, 0.5, 0.5]
        matrix = v['jomlComponents_m00_m01_m02_m03_m10_through_m33']
        assert len(matrix) == 16 and all(type(n) in (int, float) and math.isfinite(n) for n in matrix)
        # Matrix bytes/values are retained, but not predicted by this decision model.
        if v['kind'] == 'EulerXYZRotation':
            x, y, z = [bounded(int(n), 360) for n in v['angles']]
            assert [x, y, z] == v['angles']
            fields = [1, 0, 0, x, y, z, int(v['rescale'])]
        else:
            assert v['kind'] == 'SingleAxisRotation'
            angle = bounded(int(v['angle']), 360)
            assert angle == v['angle']
            fields = [2, {'X': 1, 'Y': 2, 'Z': 3}[v['axis']], angle, 0, 0, 0, int(v['rescale'])]
        return 'ok:' + '/'.join(map(str, fields))
    if action == 'shade':
        return 'ok:shade/' + str(0 if v is None else DIRECTIONS[v.lower()])
    def version(v):
        return str(bounded(v['major'])) + '.' + str(bounded(v['minor'], 2147483647))
    if action.startswith('format-'):
        return 'ok:' + version(v)
    if action.startswith('pack-'):
        return 'ok:' + version(v['min']) + '-' + version(v['max'])
    raise AssertionError('Unselected observed action')


def bend_input(row):
    d = row['data']
    boolean = lambda b: 'True{}' if b else 'False{}'
    nat = lambda n: str(n) + 'n'
    maybe = lambda v, f: 'None{}' if v is None else 'Some{' + f(v) + '}'
    version = lambda v: 'M.LDVersion{' + nat(v['major']) + ',' + nat(v['minor']) + '}'
    if row['kind'] == 'format':
        tokens = 'Nil{}'
        for n in reversed(d['tokens']):
            tokens = 'Con{M.LDNumber{' + ','.join([boolean(n['negative']), nat(n['whole']), nat(n['fraction'])]) + '},' + tokens + '}'
        return 'format(M.ld_decode_format(' + boolean(d['top']) + ',' + tokens + '))'
    if row['kind'] == 'rotation':
        keys = ['present', 'originValid', 'axisPresent', 'anglePresent', 'xyzPresent', 'axis', 'angle', 'x', 'y', 'z', 'rescale']
        return 'rotation(M.ld_decode_rotation(M.LDRotationInput{' + ','.join(boolean(d[k]) if type(d[k]) is bool else nat(d[k]) for k in keys) + '}))'
    if row['kind'] == 'shade':
        return 'shade(M.ld_decode_shade(' + boolean(d['present']) + ',' + nat(d['direction']) + '))'
    if row['kind'] == 'pack':
        values = [nat(d['threshold']), maybe(d['lower'], version), maybe(d['upper'], version),
                  maybe(d['main'], nat), maybe(d['old'], lambda v: 'M.LDOldRange{' + nat(v[0]) + ',' + nat(v[1]) + '}')]
        return 'pack(M.ld_decode_pack(M.LDPack{' + ','.join(values) + '}))'
    raise ValueError('Unknown model action')


BEND_RENDER = '''import Base
import ../../../host/minecraft/LaterDecode.bend as M
def version(v: M.LDVersion) -> String:
  match v:
    case M.LDVersion{a,b}: Nat.show(a) ++ "." ++ Nat.show(b)
def format(v: Maybe<&2,M.LDVersion>) -> String:
  match v:
    case None{}: "refused"
    case Some{v}: "ok:" ++ version(v)
def pack(v: Maybe<&2,M.LDBounds>) -> String:
  match v:
    case None{}: "refused"
    case Some{M.LDBounds{a,b}}: "ok:" ++ version(a) ++ "-" ++ version(b)
def shade(v: Maybe<&2,Nat>) -> String:
  match v:
    case None{}: "refused"
    case Some{n}: "ok:shade/" ++ Nat.show(n)
def rotation(v: Maybe<&2,M.LDRotation>) -> String:
  match v:
    case None{}: "refused"
    case Some{M.LDRotation{m,a,b,x,y,z,r}}: "ok:" ++ Nat.show(m) ++ "/" ++ Nat.show(a) ++ "/" ++ Nat.show(b) ++ "/" ++ Nat.show(x) ++ "/" ++ Nat.show(y) ++ "/" ++ Nat.show(z) ++ "/" ++ Bool.pick(String,r,"1","0")
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    manifest = json.loads((HERE / 'evidence/later-collector-dispositions.json').read_text())
    basis = []
    for record in manifest['records']:
        p = HERE / record['capture']
        assert sha(p / 'receipt.json') == record['receiptSha256']
        receipt = json.loads((p / 'receipt.json').read_text())
        assert sha(p / 'observed.json') == receipt['observedSha256']
        for name, digest in receipt['sourceSha256'].items():
            assert sha(p / name) == digest
        for stem, command in zip(['compile', 'execute'], receipt['commands']):
            assert command['ownedGroupAbsent'] and not command['timedOut']
            for stream in ['stdout', 'stderr']:
                assert sha(p / (stem + '.' + stream)) == command[stream + 'Sha256']
        basis += sorted(p.iterdir())
    capture = HERE / manifest['canonical']
    receipt = json.loads((capture / 'receipt.json').read_text())
    raw = json.loads((capture / 'observed.json').read_text())
    requests = json.loads((capture / receipt['requestFile']).read_text())
    targets = json.loads((HERE / 'targets.json').read_text())
    target = next(t for t in targets['javaReferences'] if t['id'] == receipt['target'])
    assert target['source']['clientSha256'] == receipt['clientSha256']
    assert target['declaredLauncherJavaMajor'] == 25 and receipt['profile']['JAVA_VERSION'].startswith('25.')
    assert raw['schema'] == 1 and raw['observerErrors'] == 0 and len(raw['cases']) == 40
    assert all(c['exitCode'] == 0 for c in receipt['commands'])
    assert receipt['comparisonEligibility'] == 'canonical-selected-method-scope'
    assert len({r['case'] for r in raw['cases']}) == 40
    assert [dict(id=r['case'], action=r['action'], input=r['input']) for r in raw['cases']] == requests['cases']
    canonical = {r['case']: r for r in raw['cases']}
    findings = json.loads((HERE / 'later-source-findings.json').read_text())
    assert findings['clientSha256'] == receipt['clientSha256']
    for finding in findings['findings']:
        for name, digest in finding['source']['originalClassMembersSha256'].items():
            if name in receipt['originalClassMembersSha256']:
                assert digest == receipt['originalClassMembersSha256'][name]
    for prediction in findings['plannedComparisons']:
        follow_up = prediction['followUp']
        assert follow_up['observation'] == manifest['canonical'] + '/observed.json'
        assert all(case in canonical for case in follow_up['cases'])
    # Recheck the original retained prefixes, rather than trusting their authored summary.
    prefix_matches = []
    for record in manifest['records'][:-1]:
        earlier = json.loads((HERE / record['capture'] / 'observed.json').read_text())
        good = [r for r in earlier['cases'] if not r.get('observerError') and not r.get('observed', {}).get('observerError')]
        assert all(r == canonical[r['case']] for r in good)
        prefix_matches.append(dict(capture=record['capture'], matchingNonHarnessRows=len(good)))
    rows = [project(r) for r in raw['cases']]
    answers = [observed(r) for r in raw['cases']]
    work = ROOT / '.build/minecraft/later-codec-replay'
    work.mkdir(parents=True, exist_ok=True)
    data = work / 'inputs.json'
    data.write_text(json.dumps(dict(schema=1, cases=rows), indent=2) + '\n')
    env = dict(os.environ, LEAN_PATH=str(ROOT / '.build/formal'), BEND_NO_TELEMETRY='1')
    def run_lean(path):
        return subprocess.run([os.environ.get('LEAN', 'lean'), '--run', str(HERE / 'LaterDecodeCase.lean'), str(path)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    result = run_lean(data)
    assert result.returncode == 0, result.stdout + result.stderr
    lean_values = json.loads(result.stdout)
    assert lean_values == answers, list(zip([r['case'] for r in raw['cases']], lean_values, answers))
    runner = work / 'LaterCase.bend'
    runner.write_text(BEND_RENDER + 'def main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(bend_input(r) + ' ++ "\\n"' for r in rows) + ')\n')
    result = subprocess.run([os.environ.get('BEND', 'bend'), str(runner)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    bend_values = result.stdout.splitlines()
    assert bend_values == answers, list(zip([r['case'] for r in raw['cases']], bend_values, answers))
    negatives = [dict(schema=2, cases=rows), dict(schema=1, cases=[dict(kind='unknown', data={})])]
    for index, key, value in [(0, 'axis', 4), (0, 'angle', 361), (13, 'direction', 7), (18, 'tokens', [dict(negative=False, whole=1, fraction=10)]), (18, 'tokens', [dict(negative=True, whole=0, fraction=5)]), (28, 'threshold', 65), (28, 'main', -1)]:
        row = copy.deepcopy(rows[index]); row['data'][key] = value
        negatives.append(dict(schema=1, cases=[row]))
    for i, value in enumerate(negatives):
        path = work / f'negative-{i}.json'; path.write_text(json.dumps(value))
        assert run_lean(path).returncode == 2
    bad_inputs = [dict(action='other', input={}), dict(action='rotation', input={'rotation': {'origin': [1, 2, 3], 'x': 20}}), dict(action='format-bottom', input=[-0.5]), dict(action='format-bottom', input=[True]), dict(action='pack-resource', input={'min_format': [97, 1, 2]}), dict(action='pack-data', input={'supported_formats': 'all'})]
    for row in bad_inputs:
        try:
            project(row)
        except ValueError:
            pass
        else:
            raise AssertionError('Unsupported request projected silently')
    changes = {'mixed-scalar-xyz': 'ok:1/0/0/20/0/0/0', 'invalid-scalar-with-xyz': 'ok:1/0/0/20/0/0/0', 'euler-rescale': 'ok:1/0/0/20/0/0/0', 'shade-uppercase': 'ok:shade/2', 'endpoint-top': 'ok:97.0', 'extra-format-components': 'refused', 'format-fractional': 'refused', 'resource-threshold': 'ok:65.0-65.0', 'minor-range-reversed': 'ok:97.2-97.1'}
    for case, value in changes.items():
        i = next(i for i, r in enumerate(raw['cases']) if r['case'] == case)
        changed = list(answers); changed[i] = value
        assert changed != answers and lean_values != changed and bend_values != changed
    basis += [HERE / n for n in ['LaterDecode.lean', 'LaterDecode.bend', 'LaterDecodeCase.lean', 'later_codec_conformance.py', 'export_later_codecs.py', 'targets.json', 'later-source-findings.json', 'evidence/later-collector-dispositions.json']]
    report = dict(schema=1, status='passed', canonicalCapture=manifest['canonical'], canonicalInputs=40,
        leanDecisions=len(lean_values), bendDecisions=len(bend_values), decoderRefusals=len(negatives), adapterRefusals=len(bad_inputs), changedObservationControls=len(changes),
        projectedInputsSha256=sha(data), retainedPrefixChecks=prefix_matches, comparisons=[dict(case=r['case'], action=r['action'], result=a) for r, a in zip(raw['cases'], answers)],
        basisSha256={str(p.relative_to(ROOT)): sha(p) for p in basis if p.is_file()},
        limits=['Selected original decoder methods/codecs under the recorded Java 25/macOS classpath, not full models, pack discovery, providers, rendering or other platforms.', 'Finite bounded numeric and JSON-shape profile; negative fractional syntax, overflow and general codec grammar remain unqualified.', 'Origin normalization is checked only for the selected [8,8,8] input. Matrices remain retained original values, not predicted geometry or rendered equivalence.', '125 calls across four executions include dependency failures and completion; comparisons count 40 unique canonical inputs.', 'No actual Polytone/Modefite/Compat hook, transformed game or coexistence execution.'])
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['status', 'canonicalInputs', 'leanDecisions', 'bendDecisions', 'decoderRefusals', 'adapterRefusals', 'changedObservationControls']}))


if __name__ == '__main__':
    main()
