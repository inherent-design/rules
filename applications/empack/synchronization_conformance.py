#!/usr/bin/env python3
"""Compare retained core scope observations without executing Rust/empack."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def accepted(text):
    values = re.findall(r'GameVersion\("(1\.21)"\)', text)
    assert text == '[' + ', '.join('GameVersion("' + v + '")' for v in values) + ']'
    return values


def runtime(text, requested=False):
    prefix = r'RuntimeIntent \{ java_major: 21, minecraft: GameVersion\("([^"\n]+)"\), acceptable_versions: (\[.*?\]), loader: (\w+), loader_version: (None|Some\(LoaderVersion\("[^"\n]+"\)\)) \}' if requested else r'RuntimeResolution \{ minecraft: GameVersion\("([^"\n]+)"\), loader: (\w+), loader_version: (None|Some\(LoaderVersion\("[^"\n]+"\)\)) \}'
    match = re.fullmatch(prefix, text); assert match, 'Unsupported captured Rust runtime rendering.'
    if requested:
        game, policy, loader, version = match.groups(); versions = accepted(policy)
    else:
        game, loader, version = match.groups(); versions = None
    version = None if version == 'None' else re.fullmatch(r'Some\(LoaderVersion\("([^"]+)"\)\)', version).group(1)
    return dict(game=game, loader=loader, version=version), versions


def roots(snapshot):
    result = []
    for row in snapshot['roots']:
        source = re.fullmatch(r'Provider\(Modrinth\(ModrinthProjectId\("Project([1-5])"\)\)\)', row['source'])
        if source:
            project = int(source[1])
        else:
            assert row['source'] == 'Search { query: "Fixture", providers: NonEmpty([Modrinth]) }'
            project = None
        pin = re.fullmatch(r'ProviderPin\(ModrinthVersion\(ModrinthVersionId\("Version([12])"\)\)\)', row['selection'])
        assert pin or row['selection'] == 'Automatic'
        assert row['placement'] == 'Automatic'
        result.append(dict(key=row['key'], project=project, pin=int(pin[1]) if pin else None))
    return result


def nodes(snapshot):
    result = []
    for row in snapshot['nodes']:
        record = row['record']
        projects = re.findall(r'ModrinthProjectId\("Project([1-5])"\)', record)
        versions = re.findall(r'ModrinthVersionId\("Version([12])"\)', record)
        assert len(projects) == 3 and len(set(projects)) == 1 and len(versions) == 2 and len(set(versions)) == 1
        assert 'kind: Mod,' in record and 'incompatibilities: [],' in record and 'source_selector: None,' in record
        assert 'layer: Common, requirements: Requirements { client: Required, server: Required }' in record
        assert f'PortableRelPath("mods/{projects[0]}.jar")' in record
        coverage = {'Some(CompleteForSelection)': 0, 'Some(Partial)': 1}[row['coverage']]
        result.append(dict(key=row['key'], project=int(projects[0]), version=int(versions[0]), record=record,
                           coverage=coverage, edgesPresent=row['edgesPresent'], edges=row['edges']))
    return result


def normalized(roots, prior):
    aliases = {}
    for root in roots:
        if any(n['key'] == root['key'] for n in prior):
            continue
        old = next((n for n in prior if n['project'] == root['project'] and not any(r['key'] == n['key'] for r in roots)), None)
        if old is None:
            continue
        if old['key'] in aliases:
            return None
        aliases[old['key']] = root['key']
    result = []
    for old in prior:
        n = copy.deepcopy(old); n['key'] = aliases.get(n['key'], n['key'])
        n['edges'] = sorted(aliases.get(k, k) for k in n['edges']); result.append(n)
    return sorted(result, key=lambda n: n['key'])


def sat(request, selected):
    return request['game'] == selected['game'] and request['loader'] == selected['loader'] and (request['version'] is None or request['version'] == selected['version'])


def reason(row):
    if row['result'] == 'ok':
        assert not row['diagnostic']; return ''
    if row['stage'] in ['rebind', 'proposed']:
        return {'rebind': 'alias', 'proposed': 'proposed'}[row['stage']]
    choices = {'Synchronization cannot upgrade a valid locked runtime': 'runtime',
        'Synchronization cannot discard a prior installation': 'discard',
        'Synchronization changes a valid retained selection; request an explicit update': 'retained',
        'Synchronization includes an unjustified new installation': 'unjustified'}
    if row['diagnostic'].startswith('Changed selection ') and 'retained dependents' in row['diagnostic']:
        return 'dependent'
    return choices[row['diagnostic']]


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve(); receipt = json.loads((run / 'receipt.json').read_text())
    original = [json.loads(line) for line in (run / 'observed.stdout').read_text().splitlines()]
    assert len(original) == receipt['cases'] == 24 and receipt['allOwnedProcessesRetired']
    assert sha(run / 'probe.py') == sha(HERE / 'synchronization_probe.py') == receipt['producerSha256']
    assert sha(run / 'driver.rs') == sha(HERE / 'synchronization_oracle.rs') == receipt['driverSha256']
    assert sha(run / 'observed.stdout') == receipt['observedSha256']
    prior_capture = ROOT / receipt['priorCoreCapture']
    assert sha(prior_capture / 'receipt.json') == receipt['priorCoreReceiptSha256']
    assert sha(prior_capture / 'work/libempack_core.rlib') == receipt['librarySha256']
    files = [run / n for n in ['receipt.json', 'commands.json', 'probe.py', 'driver.rs', 'projection-review.json']]
    files += [prior_capture / 'receipt.json', prior_capture / 'work/libempack_core.rlib']
    review = json.loads((run / 'projection-review.json').read_text())
    initial = ROOT / review['originalCapture'] / 'observed.stdout'; files.append(initial)
    assert sha(initial) == review['originalObservedSha256'] and sha(run / 'observed.stdout') == review['revisedObservedSha256']
    stripped = copy.deepcopy(original)
    for observation in stripped:
        for field in ['before', 'proposed', 'normalized']:
            if observation[field] is not None:
                for node in observation[field]['nodes']:
                    node.pop('edgesPresent')
    assert stripped == [json.loads(line) for line in initial.read_text().splitlines()]
    files += [HERE / n for n in ['Synchronization.lean', 'Synchronization.bend', 'SynchronizationCase.lean',
        'synchronization_probe.py', 'synchronization_oracle.rs', 'synchronization_conformance.py']]
    ledger = ROOT / 'applications/sources/empack-synchronization-selections.json'; files.append(ledger)
    pins = dict(receipt['sourceSha256'])
    for pin in json.loads(ledger.read_text())['sources']:
        assert pin['path'] not in pins or pins[pin['path']] == pin['sha256']; pins[pin['path']] = pin['sha256']
    for path, digest in pins.items():
        data = subprocess.check_output(['git', '-C', str(ROOT.parent / 'empack'), 'show', receipt['revision'] + ':' + path])
        assert hashlib.sha256(data).hexdigest() == digest
    commands = json.loads((run / 'commands.json').read_text()); assert len(commands) == 2
    for command in commands:
        assert command['exitCode'] == 0 and not command['timedOut']
        for stream in ['stdout', 'stderr']:
            p = run / (command['case'] + '.' + stream); files.append(p); assert sha(p) == command[stream + 'Sha256']
    rows, expected, calls, bend_expected = [], [], [], []
    bit = lambda b: 'True{}' if b else 'False{}'
    for observation in original:
        before, after = observation['before'], observation['proposed']
        requested, requested_accepted = runtime(before['requestedRuntime'], True)
        prior_runtime, _ = runtime(before['selectedRuntime']); proposed_runtime, _ = runtime(after['selectedRuntime'])
        assert before['requestedRuntime'] == after['requestedRuntime']
        row = dict(roots=roots(before), prior=nodes(before), proposed=nodes(after), requestedRuntime=requested,
            priorRuntime=prior_runtime, proposedRuntime=proposed_runtime, requestedAccepted=requested_accepted,
            priorAccepted=accepted(before['acceptable']), proposedAccepted=accepted(after['acceptable']), sameRevision=observation['sameRevision'])
        rows.append(row)
        expected.append(dict(runtimeSatisfied=observation['runtimeSatisfied'], affected=observation['affected'],
            normalized=nodes(observation['normalized']) if observation['normalized'] is not None else None,
            stage=observation['stage'], result=observation['result'], changed=observation['changed'], reason=reason(observation)))
        if observation['stage'] != 'scope':
            continue
        # Independent adapter traversal: it reads request/prior/proposed values,
        # never the native affected or changed result to construct its scope.
        old = normalized(row['roots'], row['prior']); assert old is not None
        active = set()
        for root in row['roots']:
            selected = next((n for n in old if n['key'] == root['key']), None)
            satisfied = selected is not None and (root['project'] is None or root['project'] == selected['project']) and (root['pin'] is None or root['pin'] == selected['version'])
            if not sat(requested, prior_runtime) or row['priorAccepted'] != requested_accepted or (root['project'] is None and not row['sameRevision']) or not satisfied:
                active.add(root['key'])
        by_key = {n['key']: n for n in row['proposed']}; allowed = set(); pending = list(active)
        while pending:
            k = pending.pop()
            if k not in allowed:
                allowed.add(k); pending.extend(by_key[k]['edges'])
        terms = [f'S.runtime_ok({bit(sat(requested, prior_runtime))},{bit(prior_runtime == proposed_runtime)})']
        for previous in old:
            following = by_key.get(previous['key']); k = previous['key']
            same_metadata = following is not None and all(previous[f] == following[f] for f in ['coverage', 'edgesPresent', 'edges'])
            same_selection = following is not None and all(previous[f] == following[f] for f in ['project', 'version'])
            flags = [following is not None, k in allowed, any(r['key'] == k for r in row['roots']) and k not in active,
                following is not None and previous['record'] == following['record'], same_metadata, same_selection,
                any(n['key'] not in allowed and k in n['edges'] for n in old)]
            terms.append('S.old_ok(' + ','.join(map(bit, flags)) + ')')
        for n in row['proposed']:
            terms.append(f'S.new_ok({bit(any(p["key"] == n["key"] for p in old))},{bit(n["key"] in allowed)})')
        expression = 'True{}'
        for term in terms:
            expression = 'Bool.and(' + expression + ',' + term + ')'
        calls.append('Bool.show(' + expression + ') ++ "\\n"'); bend_expected.append(str(observation['result'] == 'ok'))
    basis = {str(p.relative_to(ROOT)): sha(p) for p in files}
    generated = HERE / 'generated'; generated.mkdir(exist_ok=True); path = generated / 'synchronization.json'
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    env = dict(os.environ, LEAN_PATH='.build/formal:.build', BEND_NO_TELEMETRY='1')

    def replay(value):
        path.write_text(json.dumps(value) + '\n')
        return subprocess.run([lean, '--run', str(HERE / 'SynchronizationCase.lean'), str(path)], cwd=ROOT, env=env, capture_output=True, text=True)

    value = dict(schema=1, cases=rows); result = replay(value)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == expected
    driver = generated / 'SynchronizationCase.bend'
    driver.write_text('import Base\nimport ../Synchronization.bend as S\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(calls) + ')\n')
    result = subprocess.run([bend, str(driver)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == bend_expected
    invalids = [('schema', dict(value, schema=2), 'Unsupported synchronization research schema')]
    for label, change, message in [('unknown-key', lambda r: r['roots'][0].update(key='unknown'), 'root key/order'),
        ('duplicate-node', lambda r: r['prior'].append(copy.deepcopy(r['prior'][0])), 'node identity'),
        ('dangling-edge', lambda r: r['proposed'][0].update(edges=['x']), 'graph/evidence profile'),
        ('unobserved-same-pin-edit', lambda r: r['proposed'][0].update(record='new evidence'), 'separate evidence model'),
        ('unknown-coverage', lambda r: r['proposed'][0].update(coverage=2), 'graph/evidence profile')]:
        bad = copy.deepcopy(rows[0]); change(bad); invalids.append((label, dict(schema=1, cases=[bad]), message))
    for label, bad, message in invalids:
        result = replay(bad); assert result.returncode == 2 and message in result.stderr, label
    path.write_text(json.dumps(value, indent=2) + '\n')
    assert all(sha(ROOT / p) == h for p, h in basis.items()), 'Evidence changed while consumed.'
    report = dict(schema=1, basisSha256=basis, sourcePins=len(pins), pipelineCases=24, leanCases=24,
        bendScopeDecisions=len(calls), phases=dict(scope=22, proposed=1, rebind=1), invalidResearchInputsRefused=[v[0] for v in invalids],
        scope='Fixed provider-mod/common/required/automatic-placement profile;opaque actual record equality labels andsynthetic revision controls. Not canonical codec/catalog/materialization/native grant qualification.',
        sourceQualifiedFindings=['Changed records are not full lock deltas;allowed coverage/edge-only changes can be absent.',
            'Production candidate source encodes wholeproposed lock;no dropped-publication defect established.',
            'Search is scoped to overallsemantic revision;ordinary recorded candidate requiresfreshresolution onchange,notproof realcatalog updates.'],
        limits=['Same-pin file/assertion/additive incompatibility edits are rejected by research decoder,not modeled as production refusals.',
            'Bend checks22local scope decisions;Lean separately compares aliases,affected roots,precondition stages andchanged records.',
            'All provider IDs,version labels andsource assertions are fictional;version labels establish equality,not chronology.',
            'Complete observations andfixed runtime/profile are premises;no actual dependency compatibility,host effects or release qualification.'])
    (run / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'basisSha256'}, indent=2))


if __name__ == '__main__':
    main()
