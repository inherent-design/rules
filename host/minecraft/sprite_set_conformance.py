#!/usr/bin/env python3
"""Pure retained sprite-set comparison; no Java, game, renderer or studied application."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
CAPTURES = ['sprite-set-1.21.1-20261125T135557269241Z', 'sprite-set-1.21.4-20261125T135646313805Z',
            'sprite-set-1.21.5-20261125T135647594737Z', 'sprite-set-1.21.11-20261125T135648913605Z',
            'sprite-set-26.3-20261125T135649723508Z']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
CODES = {'NONE': 0, 'java.lang.NullPointerException': 1, 'java.lang.ArithmeticException': 2,
         'java.lang.ArrayIndexOutOfBoundsException': 3, 'java.util.NoSuchElementException': 4}


def project(observed, plan, modern):
    assert observed['schema'] == 1 and observed['observerErrors'] == 0 and observed['firstAvailable'] is modern
    assert observed['identityAdapter'] == 'Unsafe.allocateInstance on original sprite class; fields/constructor/render methods unused'
    programs = []; measured = []; position = 0; calls = 0
    for case in plan['cases']:
        actions = []; outcomes = []
        for step in case['steps']:
            if step.get('modernOnly') and not modern:
                continue
            row = observed['rows'][position]; position += 1
            assert row['case'] == case['id'] and row['ordinal'] == len(actions) and row['step'] == step
            assert row['unexpected'] is False and row['error'] in CODES
            op = step['op']; kind = ['bind', 'bindNull', 'mutate', 'frame', 'first'].index(op)
            actions.append(dict(kind=kind, values=step.get('values', []), index=step.get('index', 0), max=step.get('max', 1), value=step.get('value', 0)))
            bound, supplied = row['bound'], row['input']
            for values in [bound, supplied]:
                assert values is None or (type(values) is list and len(values) <= 8 and all(type(v) is int and 0 <= v <= 3 for v in values))
            assert bound is None or all(v > 0 for v in bound)
            assert type(row['selected']) is int and 0 <= row['selected'] <= 3
            outcomes.append([CODES[row['error']], row['selected'], int(bound is not None), len(bound or []), int(supplied is not None), len(supplied or [])] + (bound or []) + [9] + (supplied or []))
            calls += int(op != 'mutate')
        programs.append(actions); measured.append(outcomes)
    assert position == len(observed['rows']) and observed['originalCalls'] == calls
    return dict(schema=1, contract='original-sprite-set-controls', firstAvailable=modern, cases=programs), measured


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', type=Path); a = p.parse_args()
    work = ROOT / '.build/minecraft/sprite-replay'; work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LEAN_PATH=os.environ.get('LEAN_PATH', str(ROOT / '.build/formal')), BEND_NO_TELEMETRY='1')
    def lean(data, label):
        path = work / (label + '.json'); path.write_text(json.dumps(data) + '\n')
        return subprocess.run([os.environ.get('LEAN', 'lean'), '--run', str(HERE / 'SpriteSetCase.lean'), str(path)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
    def bend(programs, label):
        def linked(xs):
            value = 'Nil{}'
            for x in reversed(xs): value = 'Con{' + x + ',' + value + '}'
            return value
        def bit(b): return 'True{}' if b else 'False{}'
        calls = []
        for program in programs:
            actions = []
            for r in program:
                fields = [str(r['kind'])+'n', linked([str(v)+'n' for v in r['values']]), bit(r['index'] < 0), str(abs(r['index']))+'n', bit(r['max'] < 0), str(abs(r['max']))+'n', str(r['value'])+'n']
                actions.append('M.SpriteAction{' + ','.join(fields) + '}')
            calls.append('M.sprite_program(' + linked(actions) + ',M.sprite_empty())')
        path = work / (label + '.bend'); path.write_text('import Base\nimport ../../../host/minecraft/SpriteSet.bend as M\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(calls) + ')\n')
        r = subprocess.run([os.environ.get('BEND', 'bend'), str(path)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, r.stdout + r.stderr
        flat = [[int(v) for v in line.split(':')] for line in r.stdout.splitlines()]; result = []
        for program in programs:
            result.append(flat[:len(program)]); flat = flat[len(program):]
        assert not flat
        return result
    basis = [HERE / n for n in ['SpriteSet.lean', 'SpriteSet.bend', 'SpriteSetCase.lean', 'sprite_set_cases.json', 'sprite_set_conformance.py']]
    plan = json.loads((HERE / 'sprite_set_cases.json').read_text()); observations = []; predictions = []; requests = []; profiles = []
    for i, name in enumerate(CAPTURES):
        cap = HERE / 'evidence' / name; r = json.loads((cap / 'receipt.json').read_text()); observed = json.loads((cap / 'observed.json').read_text()); modern = i >= 3
        assert r['observerErrors'] == 0 and r['rows'] == (41 if modern else 38) and r['originalCalls'] == (39 if modern else 36)
        assert json.loads((cap / 'sprite_set_cases.json').read_text()) == plan
        if 'requestSha256' in r:
            assert sha(cap / 'request.json') == r['requestSha256'] and json.loads((cap / 'request.json').read_text()) == plan
        else:
            frozen = (cap / 'native_sprite_set.py').read_text()
            assert "request=json.loads((cap/'sprite_set_cases.json').read_text())" in frozen
            assert "(cap/'request.json').write_text(json.dumps(request,indent=2)+'\\n')" in frozen
        assert sha(cap / 'observed.json') == r['observed.jsonSha256'] and sha(cap / 'bindings.json') == r['bindingsSha256']
        for f, h in r['sourcesSha256'].items(): assert sha(cap / f) == h
        for stem, cmd in zip(['compile', 'execute'], r['commands']):
            assert cmd['exitCode'] == 0 and cmd['ownedGroupAbsent'] and not cmd['timedOut']
            for stream in ['stdout', 'stderr']: assert sha(cap / (stem + '.' + stream)) == cmd[stream + 'Sha256']
        data, expected = project(observed, plan, modern); result = lean(data, str(i)); assert result.returncode == 0, result.stdout + result.stderr
        predicted = json.loads(result.stdout); assert predicted == expected == bend(data['cases'], str(i))
        profiles.append(dict(target=r['target'], profile=r['profile'], rows=r['rows'], originalCalls=r['originalCalls'], firstAvailable=modern,
                             requestBasis='frozen hashed plan,deterministic frozen producer,and observed step equality;separate actual-request digest omitted by original collector' if 'requestSha256' not in r else 'separately captured request digest'))
        observations.append(observed); predictions.append(predicted); requests.append(data); basis += [f for f in cap.iterdir() if f.is_file()]
    base = requests[0]; negatives = [dict(base, schema=2), dict(base, contract='particle-renderer'), dict(base, cases=base['cases']*4), dict(base, cases=[base['cases'][1]*4])]
    standard = dict(kind=3, values=[], index=0, max=1, value=0)
    for changes in [dict(kind=5), dict(index=17), dict(max=-17), dict(value=4), dict(values=[1]), dict(kind=0, values=[4]), dict(kind=True), dict(kind=4), dict(kind=2)]:
        negatives.append(dict(base, cases=[[standard | changes]]))
    for i, bad in enumerate(negatives): assert lean(bad, 'negative-'+str(i)).returncode == 2
    controls = []
    for case, ordinal, key, value in [('copied-input', 2, 'selected', 3), ('copied-input', 1, 'bound', [3,2]),
                                      ('failed-bind-retains', 1, 'bound', None), ('failed-bind-retains', 3, 'error', 'NONE'),
                                      ('three-frames', 6, 'selected', 2), ('empty-binding', 2, 'error', 'java.lang.ArrayIndexOutOfBoundsException'),
                                      ('replacement', 4, 'selected', 2)]:
        changed = copy.deepcopy(observations[0]); row = next(r for r in changed['rows'] if r['case'] == case and r['ordinal'] == ordinal); assert row[key] != value; row[key] = value
        try: assert project(changed, plan, False)[1] == predictions[0]
        except AssertionError: controls.append(case+':'+str(ordinal)+':'+key)
        else: raise AssertionError('Changed observation survived')
    report = dict(schema=1, status='passed-original-sprite-set-controls', profiles=profiles, boundaryComparisons=196, originalMethodCalls=186,
        authoredInputMutations=10, leanLaws=13, bendLaws=8, decoderRefusals=len(negatives), changedObservationControls=controls,
        basisSha256={str(f.relative_to(ROOT)): sha(f) for f in sorted(basis)},
        limits=['Constructor-bypassed original sprites are opaque identity adapters,not valid renderable objects or a standard Java allocation guarantee.',
                'Original collectors omitted a separate digest of the derived request. Frozen plan/source digests and exact observed-step equality supply the replay basis;original receipts remain unchanged.',
                'Signed frame/list sizes avoid multiplication overflow;denominator zero,unbound,empty and invalid-index cases are separate.',
                'Original helper and authored input-list mutation observations are counted separately;no real provider/atlas/particle engine/render/backend execution.',
                'Native macOS/JDK21 or25 only. First helper availability is versioned;not evidence that older versions lack all first-sprite behavior.',
                'Exception categories are projected from retained exact classes;the model does not qualify all runtime exception subclasses or stack traces.'])
    if a.output: a.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:report[k] for k in ['status', 'boundaryComparisons', 'originalMethodCalls', 'authoredInputMutations', 'decoderRefusals', 'changedObservationControls']}))


if __name__ == '__main__': main()
