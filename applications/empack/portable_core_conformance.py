#!/usr/bin/env python3
"""Replay existing projection models against retained shared-core runtime packets.

No Rust, Node, browser, or application execution. The wire's path/byte facts are
checked independently; normalized domain comparisons reuse Projection unchanged.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

from portable_core_observations import RUN, ROOT, inspect, read, sha

HERE = Path(__file__).resolve().parent


def compare(actual, expected, status_only):
    assert len(actual) == len(expected) == len(status_only)
    for index, (found, want, narrow) in enumerate(zip(actual, expected, status_only, strict=True)):
        assert (dict(status=found['status']) if narrow else found) == want, (index, found, want)


def normalize(case, observed):
    records = case['records']
    paths = list(dict.fromkeys(r['path'] for r in records))
    assets = list(dict.fromkeys(r['sha256'] for r in records))
    assert len(paths) <= 2
    assert len({r['path'] for r in records if r['client'] >= 2 or r['server'] >= 2}) <= 1
    inputs = [dict(owner=i, layer=r['layer'], destination=paths.index(r['path']),
                   client=r['client'], server=r['server'], representation=r['representation'],
                   asset=assets.index(r['sha256']) if r['representation'] == 0 else 0)
              for i, r in enumerate(records)]
    value = dict(target=[0, 1, 5][case['recipe']], policy=[0, 4, 1][case['policy']], inputs=inputs)
    if 'error' in observed:
        label = observed['error']
        errors = {'DuplicateDestination': 'select/duplicate', 'InvalidEnvironment': 'select/invalid-environment',
                  'ChoiceRequired': 'select/choice-required', 'MaterializationRequired': 'finish/materialization'}
        matches = [meaning for key, meaning in errors.items() if key in label]
        assert len(matches) == 1
        # The actual adapter returns an error without an intermediate selected
        # view. A model finish error exposes that view; only status is compared.
        narrow = matches[0].startswith('finish/')
        output = dict(status=matches[0]) if narrow else dict(status=matches[0], entries=[], precedence=[], choices=[])
        return value, output, narrow
    entries = []
    for e in observed['entries']:
        source = inputs[e['owner']]
        path = 'config/p' + str(paths.index(e['path'])) + '.cfg'
        entries.append(f"s{e['owner']}:{e['layer']}:{path}:{e['client']['code']}:{e['server']['code']}:0:{source['asset']}")
    precedence = [f"s{p['replacement']}>s{p['replaced']}@config/p{paths.index(p['path'])}.cfg" for p in observed['precedence']]
    choices = [f"extra:{str(c['enabled']).lower()}:{str(c['usedDefault']).lower()}" for c in observed['choices']]
    return value, dict(status='ok', entries=sorted(entries), precedence=sorted(precedence), choices=choices), False


def main():
    cases, observed, build, browser = inspect()
    files = [p for p in RUN.iterdir() if p.is_file() and p.name not in ['conformance.json', 'basis.json']]
    files += [HERE / p for p in ['portable_core_observations.py', 'portable_core_conformance.py',
              'Projection.lean', 'ProjectionCase.lean', 'Projection.bend']]
    files += sorted((HERE / 'portable-core').iterdir())
    files += [ROOT / 'applications/sources/empack-portable-core-selections.json']
    basis = {str(p.relative_to(ROOT)): sha(p) for p in files}
    ledger = read(ROOT / 'applications/sources/empack-portable-core-selections.json')
    assert ledger['revision'] == build['revision']
    for pin in ledger['sources']:
        raw = subprocess.check_output(['git', '-C', str(ROOT.parent / 'empack'), 'show', build['revision'] + ':' + pin['path']])
        assert hashlib.sha256(raw).hexdigest() == pin['sha256']
    rows, expected, names, status_only = [], [], [], []
    for case in cases:
        if case['id'].startswith(('bad-', 'truncated', 'trailing')):
            continue
        row, output, narrow = normalize(case, observed[case['id']])
        names.append(case['id']); rows.append(row); expected.append(output); status_only.append(narrow)
    assert len(rows) == 19
    formal = Path(os.environ.get('STUDY_FORMAL_DIR', str(ROOT / '.build/formal')))
    env = dict(os.environ, LEAN_PATH=os.pathsep.join([str(formal), str(ROOT / '.build')]), BEND_NO_TELEMETRY='1')
    generated = HERE / 'generated'; generated.mkdir(exist_ok=True)
    packet = generated / 'portable-core.json'
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')

    def replay(value):
        packet.write_text(json.dumps(value) + '\n')
        return subprocess.run([lean, '--run', 'applications/empack/ProjectionCase.lean', str(packet)], cwd=ROOT, env=env, capture_output=True, text=True)

    result = replay(dict(schema=1, cases=rows)); assert result.returncode == 0, result.stdout + result.stderr
    actual = json.loads(result.stdout)
    compare(actual, expected, status_only)
    choice_calls, choice_expected, complete_calls, complete_expected, excluded = [], [], [], [], []
    bit = lambda value: 'True{}' if value else 'False{}'
    for name, row, output in zip(names, rows, actual, strict=True):
        if row['target'] == 5 or output['status'] in ['select/duplicate', 'select/invalid-environment']:
            excluded.append(name); continue
        side = 'server' if row['target'] == 1 else 'client'; layer = 3 if side == 'server' else 2
        for dest in sorted({r['destination'] for r in row['inputs']}):
            selected = sorted([r for r in row['inputs'] if r['destination'] == dest and r['layer'] in [0, 1, layer]], key=lambda r: r['layer'], reverse=True)
            nodes = []
            for r in selected:
                req = r[side]
                meaning = 'P.Unsupported{}' if req == 0 else 'P.Required{}' if req == 1 else 'P.Optional{' + bit(req == 3) + '}'
                nodes.append('P.Candidate{' + str(r['owner']) + 'n,' + meaning + '}')
            policy = {0: 'Preserve', 4: 'Defaults', 1: 'Unresolved'}[row['policy']]
            choice_calls.append('P.label(P.choose([' + ','.join(nodes) + '],P.' + policy + '{},True{})) ++ "\\n"')
            if output['status'].startswith('select/'):
                choice_expected.append('error/' + output['status'].removeprefix('select/'))
            else:
                entries = [e.split(':') for e in output['entries'] if e.split(':')[2] == f'config/p{dest}.cfg']
                assert len(entries) <= 1
                choice_expected.append('none' if not entries else entries[0][0] + ':' + entries[0][3 if side == 'client' else 4])
        for e in output['entries']:
            kind = e.split(':')[5]
            complete_calls.append('P.complete(P.' + ('Embedded' if kind == '0' else 'Unacquired') + '{},True{}) ++ "\\n"')
            complete_expected.append('ok' if kind == '0' else 'materialization')
    runner = generated / 'PortableCoreCase.bend'
    runner.write_text('import Base\nimport ../Projection.bend as P\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(choice_calls + complete_calls) + ')\n')
    result = subprocess.run([bend, str(runner)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == choice_expected + complete_expected
    refused = []
    for label, value, message in [
        ('schema', dict(schema=2, cases=rows), 'Unsupported projection schema'),
        ('recipe', dict(schema=1, cases=[dict(rows[0], target=99)]), 'Unknown recipe profile'),
        ('policy', dict(schema=1, cases=[dict(rows[0], policy=99)]), 'Unknown choice policy'),
        ('destination', dict(schema=1, cases=[dict(rows[0], inputs=[dict(rows[0]['inputs'][0], destination=2)])]), 'outside the captured profile')]:
        result = replay(value); assert result.returncode == 2 and message in result.stderr; refused.append(label)
    packet.write_text(json.dumps(dict(schema=1, cases=rows), indent=2) + '\n')
    rejected = []
    for label, file, change in [
        ('native-exit', 'native-cases.json', lambda d: d['rows'][0].update(exitCode=1)),
        ('native-observed-bytes', 'native-cases.json', lambda d: d['rows'][0].update(hex='00')),
        ('wasm-result', 'node-cases.json', lambda d: d['rows'][0].update(status=1)),
        ('browser-result', 'browser.json', lambda d: d['profiles'][0]['rows'][0].update(hex='00')),
        ('worker-error', 'browser.json', lambda d: d['profiles'][0]['errors'].append('worker failed')),
        ('browser-open', 'browser.json', lambda d: d['profiles'][1].update(contextClosed=False)),
        ('process-still-present', 'browser-closure.json', lambda d: d.update(originalGroupAbsent=False)),
        ('compiler-failure', 'build.json', lambda d: d['commands'][0].update(exitCode=1))]:
        value = copy.deepcopy(read(RUN / file)); change(value)
        try: inspect({file: value})
        except AssertionError: rejected.append(label)
        else: raise AssertionError('Changed observation was accepted: ' + label)
    value = copy.deepcopy(read(RUN / 'cases.json')); value[0]['records'][0]['bytes'] += 1
    try: inspect({'cases.json': value})
    except AssertionError: rejected.append('declared-input-differs-from-packet')
    else: raise AssertionError('Changed packet premise was accepted')
    model_controls = []
    for name, field, replacement in [
        ('local-jar-config', 'status', 'mutated'),
        ('local-jar-config', 'entries', []),
        ('client-precedence', 'precedence', []),
        ('optional-default-true', 'choices', []),
        ('duplicate-layer', 'status', 'ok'),
        ('missing-known-size', 'status', 'ok')]:
        changed = copy.deepcopy(actual); changed[names.index(name)][field] = replacement
        try: compare(changed, expected, status_only)
        except AssertionError: model_controls.append(name + ':' + field)
        else: raise AssertionError('Changed model outcome was accepted')
    assert all(sha(ROOT / p) == h for p, h in basis.items())
    report = dict(schema=1, basisSha256=basis, runtimeCases=32, runtimeTargets=['native', 'Node WASM', 'Chromium worker', 'WebKit worker'],
                  exactParity=True, leanCases=19, leanMatches=True, statusOnlyCases=[n for n, s in zip(names, status_only) if s],
                  bendChoices=len(choice_calls), bendRepresentationGates=len(complete_calls), bendMatches=True, bendExcludedCases=excluded,
                  decoderRefusals=refused, observationControls=rejected, changedModelOutcomesRejected=model_controls,
                  modelReuse='Projection.lean/ProjectionCase.lean/Projection.bend unchanged; no new duplicate planner.',
                  limits=['13 path/wire guards are actual runtime evidence outside the projection model.',
                          'Exact path-to-label and digest-to-label normalization; at most two destinations and one optional key per case. Not arbitrary choice maps.',
                          'Finish errors expose no selected intermediate view in the real wire; compare status only for that case.',
                          'Bend checks local choices/representation gates after global admission; not preserved-layer/global validation.',
                          'Exact runtime bytes/lengths/permissions are checked separately; Lean projection does not model hashing, paths, permissions or memory.',
                          'Core callers supply observations. No full portable engine, shared draft codec, browser consumer exporter or joined save/reopen flow.',
                          'No proof that installed empack binary corresponds to current source; toolchain subordinate-linker identity unqualified.',
                          'Node results have retained output and shared module identity, but no original collector invocation/Node-binary attestation.'])
    (RUN / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['basisSha256', 'limits']}, indent=2))


if __name__ == '__main__':
    main()
