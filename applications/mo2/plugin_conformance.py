"""Replay source-method observations;no compiler,Qt fixture,game or MO2 launch."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

from plugin_observations import NAMES, identity, model_input, model_output

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUN = ROOT / 'applications/evidence/mo2-plugins-20261125T155025191906Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())


def write(p, value):
    p.write_text(json.dumps(value, indent=2) + '\n')


def compare(actual, expected):
    assert actual == expected, 'MO2 method projection differs from retained observation'


def bend_rows(inputs, raw):
    calls, wanted, labels = [], [], []
    bo = lambda b: 'True{}' if b else 'False{}'
    li = lambda xs: '[' + ','.join(str(n) + 'n' for n in xs) + ']'
    def append(label, expression, expected):
        labels.append(label)
        calls.append(expression)
        wanted.append(expected)
    for initial, row in zip(inputs['cases'], raw, strict=True):
        metadata = {p['id']: p for p in initial['plugins']}
        before = row['before']
        for number, (action, after) in enumerate(zip(initial['actions'], row['steps'], strict=True)):
            mode, target, active = action['kind'], action['target'], action['active']
            catalog = list(metadata)
            indexed = [identity(name) for name in before['byName']]
            found = target in indexed
            enabled = [identity(p['name']) for p in before['plugins'] if p['enabled']]
            requested = [name for name in action['names'] if name in indexed]
            prefix = row['id'] + '/' + str(number)
            old_by_id = {identity(p['name']): p for p in before['plugins']}
            notifications = []
            delta_events = after['events'][len(before['events']):]
            actual_dirty = {identity(name) for event in delta_events if event['kind'] == 'state' for name in event['values']}
            for p in after['plugins']:
                key = identity(p['name'])
                old, flags = old_by_id[key], metadata[key]
                matches = found and key == target
                args = ','.join(bo(flags[field]) for field in ['loaded', 'forced', 'disabled'])
                append(prefix + '/enabled/' + str(key), 'Bool.show(P.enabled_after(' + str(mode) + 'n,' +
                    ','.join(bo(b) for b in [old['enabled'], active, matches]) + ',' + args + '))', str(p['enabled']))
                notify = 'P.notified(' + str(mode) + 'n,' + ','.join(bo(b) for b in [matches, old['enabled'], active]) + ',' + args + ')'
                notifications.append(notify)
                append(prefix + '/notified/' + str(key), 'Bool.show(' + notify + ')', str(key in actual_dirty))
                if mode == 3:
                    rank = 'P.priority(' + li(catalog) + ',' + li(requested) + ',' + str(key) + 'n)'
                    append(prefix + '/priority/' + str(key), 'Nat.show(' + rank + ')', str(p['priority']))
                    append(prefix + '/indexed/' + str(key), 'Bool.show(Nat.is_lt(' + rank + ',' + str(len(catalog)) + 'n))', str(p['queriedState'] != 'missing'))
                if mode == 4:
                    assert sorted(before['byPriority']) == catalog, 'Bend sync profile requires a valid priority permutation'
                    append(prefix + '/load/' + str(key), 'P.show_optional(P.load_order(' + li(before['byPriority']) + ',' + li(enabled) + ',' + str(key) + 'n))', str(p['loadOrder']))
                if mode == 5:
                    append(prefix + '/masters/' + str(key), 'P.show_list(P.missing(' + li(flags['masters']) + ',' + li(enabled) + ',' + bo(old['enabled']) + '))',
                        ''.join(str(identity(name)) + ',' for name in p['missing']))
            dirty = 'False{}'
            for notification in notifications:
                dirty = 'Bool.or(' + notification + ',' + dirty + ')'
            append(prefix + '/write-requests', 'Nat.show(P.write_requests(' + str(mode) + 'n,' + bo(found) + ',' + dirty + '))', str(after['writes'] - before['writes']))
            before = after
    return calls, wanted, labels


def main():
    receipt = load(RUN / 'receipt.json')
    assert receipt['complete'] and receipt['cases'] == 28
    assert sha(RUN / 'probe.py') == receipt['producerSha256'] and sha(RUN / 'driver.cpp') == receipt['driverSha256']
    assert sha(RUN / 'input.json') == receipt['inputSha256']
    for command in receipt['commands']:
        assert command['exitCode'] == 0 and command['groupAbsent'] and not command['timedOut']
        for stream in ['stdout', 'stderr']:
            assert sha(RUN / (command['label'] + '.' + stream)) == command[stream + 'Sha256']
    ledger = load(ROOT / 'applications/sources/mo2-plugin-selections.json')
    available, unavailable = [], []
    for source in ledger['sources']:
        path = ROOT / source['cache']
        if path.exists():
            data = path.read_bytes()
            assert sha(path) == source['sha256']
            assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == source['gitBlob']
            available.append(source['path'])
        else:
            unavailable.append(source['path'])
    source = ROOT / receipt['source']['cache']
    reconstructed = False
    if source.exists():
        text = source.read_text()
        bodies = []
        for cut in receipt['cuts']:
            body = text[cut['textStart']:cut['textEnd']]
            assert body.startswith(cut['signature']) and hashlib.sha256(body.encode()).hexdigest() == cut['sha256']
            bodies.append(body)
        generated = (RUN / 'driver.cpp').read_text().replace('/*METHODS*/', '\n'.join(bodies))
        assert hashlib.sha256(generated.encode()).hexdigest() == receipt['generatedSha256']
        reconstructed = True
    work = Path(receipt['work'])
    for path, digest in [(work / 'main.cpp', receipt['generatedSha256']), (work / 'probe', receipt['binarySha256']),
            (Path('/usr/bin/clang++'), receipt['compilerSha256'])]:
        if path.exists():
            assert sha(path) == digest
    compile_args = next(c['argv'] for c in receipt['commands'] if c['label'] == 'compile')
    lib = Path(next(arg.removeprefix('-Wl,-rpath,') for arg in compile_args if arg.startswith('-Wl,-rpath,')))
    qt = lib / 'QtCore.framework/Versions/A/QtCore'
    if qt.exists():
        assert sha(qt) == receipt['qtFrameworkSha256']
    proof = load(RUN / 'proof-gate.json')
    assert proof['observedExitCode'] == 0 and proof['observedSummary'] == 'Checked 2 Lean modules and 1 Bend files.'
    for path, digest in proof['sourceSha256'].items():
        assert sha(ROOT / path) == digest
    original = load(RUN / 'input.json')
    raw = load(RUN / 'observed.stdout')
    assert [r['id'] for r in original['cases']] == [r['id'] for r in raw]
    assert all(len(a['actions']) == len(b['steps']) for a, b in zip(original['cases'], raw, strict=True))
    inputs, expected = model_input(original), model_output(raw)
    write(RUN / 'model-input.json', inputs)
    write(RUN / 'observed-model-values.json', expected)
    formal = ROOT / '.build/mo2-plugins-formal'
    env = {**os.environ, 'LEAN_PATH': str(formal), 'BEND_NO_TELEMETRY': '1'}
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    command = [lean, '--run', 'applications/mo2/PluginsCase.lean']
    result = subprocess.run(command + [str(RUN / 'model-input.json')], cwd=ROOT, env=env, check=True, capture_output=True, text=True)
    actual = json.loads(result.stdout)
    compare(actual, expected)
    calls, wanted, labels = bend_rows(inputs, raw)
    case = formal / 'Replay.bend'
    case.write_text('import ../../applications/mo2/Plugins.bend as P\nimport Base\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ "\\n" ++ '.join(calls) + ' ++ "\\n")\n')
    result = subprocess.run([bend, str(case)], cwd=ROOT, env=env, check=True, capture_output=True, text=True)
    compared = result.stdout.splitlines()
    compare(compared, wanted)
    write(RUN / 'bend-projections.json', [dict(label=k, observed=v) for k, v in zip(labels, wanted, strict=True)])
    controls = []
    changes = [('missing-write', 'helper-unchanged', lambda r: r['steps'][0].update(writes=0)),
        ('unexpected-api-write', 'api-free-1', lambda r: r['steps'][0].update(writes=1)),
        ('stale-load', 'api-then-normalize', lambda r: r['steps'][1]['plugins'][2].update(loadOrder=-1)),
        ('missing-master', 'masters-disabled', lambda r: r['steps'][0]['plugins'][1].update(missing=[])),
        ('index-physical-assumption', 'order-duplicate', lambda r: r['steps'][0]['plugins'][2].update(queriedState='inactive'))]
    for label, key, change in changes:
        rows = copy.deepcopy(raw)
        row = next(r for r in rows if r['id'] == key)
        change(row)
        try:
            compare(actual, model_output(rows))
        except AssertionError as error:
            cause = 'Queried states and native name index disagree' if label == 'index-physical-assumption' else 'MO2 method projection differs'
            assert cause in str(error), (label, str(error))
            controls.append(label)
        else:
            raise AssertionError('Changed native observation escaped')
    for label, change, cause in [('schema', lambda d: d.update(schema=2), 'Unsupported plugin study schema'),
            ('catalog', lambda d: d['cases'][0]['plugins'][0].update(id=2), 'catalog IDs must be contiguous'),
            ('priority', lambda d: d['cases'][0]['plugins'][0].update(priority=2), 'priority must be a permutation'),
            ('master-set', lambda d: d['cases'][0]['plugins'][0].update(masters=[4,4]), 'Master metadata must be a set-shaped'),
            ('action', lambda d: d['cases'][0]['actions'][0].update(kind=8), 'Unsupported plugin operation'),
            ('name', lambda d: d['cases'][0]['actions'][0].update(target=9), 'Unsupported plugin operation')]:
        bad = copy.deepcopy(inputs)
        change(bad)
        path = formal / (label + '.json')
        write(path, bad)
        result = subprocess.run(command + [str(path)], cwd=ROOT, env=env, capture_output=True, text=True)
        assert result.returncode == 2 and cause in result.stderr
        controls.append(label)
    files = [p for p in RUN.rglob('*') if p.is_file() and p.name not in ['basis.json', 'conformance.json']]
    files += [HERE / name for name in ['plugin_driver.cpp', 'plugin_probe.py', 'plugin_observations.py', 'plugin_conformance.py', 'Plugins.lean', 'PluginsCase.lean', 'Plugins.bend']]
    files.append(ROOT / 'applications/sources/mo2-plugin-selections.json')
    write(RUN / 'basis.json', {str(p.relative_to(ROOT)): sha(p) for p in files})
    report = dict(schema=1, sourceMethods=9, sourceCases=28, observedTransitions=sum(len(r['steps']) for r in raw),
        leanFullTimelineMatch=True, bendProjectionComparisons=len(calls),
        leanLaws=17, bendLaws=9, negativeControls=controls, basisFiles=len(files),
        verifiedSourceCaches=available, unavailableSourceCaches=unavailable, reconstructedSelectedBodies=reconstructed,
        limits=['RealQtCore/selected unchanged source with field/enum/comparator/log/signal/game-index adapters;not native Windows MO2.',
            'Lean predicts complete fixture timelines;Bend predicts admitted per-step activation/rank/load/master/write projections from measured prestates.',
            'No real Qt slots,writer persistence,game plugin parsing/relationships,LOOT/USVFS/GUI or process-launch qualification.',
            'Duplicate order is a constructed API-shape counterexample;normal full-app caller reachability and API uniqueness contract are unresolved.',
            'Queried missing state is an index result here,not physical absence or deletion authority.'])
    write(RUN / 'conformance.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
