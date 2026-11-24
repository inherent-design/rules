#!/usr/bin/env python3
"""Pure retained replay: project selections, runtime reads, and npm hidden index."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ADAPTER = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('followups', nargs=2, type=Path)
    args = parser.parse_args()
    run, followups = args.run.resolve(), [p.resolve() for p in args.followups]
    inputs = [HERE / p for p in ['LockModes.lean', 'LockModesCase.lean', 'LockModes.bend']]
    inputs.append(ROOT / 'applications/sources/js-lock-modes-selections.json')
    for capture in [run, *followups]:
        inputs += [p for p in sorted(capture.rglob('*')) if p.is_file() and 'work' not in p.relative_to(capture).parts
                   and p.name not in ['conformance.json']]
    basis = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    selected_sources = json.loads(inputs[3].read_text())
    for row in selected_sources:
        assert sha(ROOT / row['cache']) == row['sha256']
    cases, expected, shared_fields, references = [], [], [], []

    def load(capture, count):
        rows = json.loads((capture / 'trace.json').read_text())
        receipt = json.loads((capture / 'receipt.json').read_text())
        assert len(rows) == receipt['commands'] == count
        assert sha(capture / 'probe.py') == receipt['producerSha256']
        for r in rows:
            stem = r['app'] + '-' + r['case'] if capture == run else r['case']
            for stream in ['stdout', 'stderr']:
                assert sha(capture / (stem + '.' + stream)) == r['observed'][stream + 'Sha256']
        return rows, receipt

    def version(value):
        assert value in ['1.0.0', '2.0.0']
        return int(value[0])

    def wanted(text):
        deps = json.loads(text)['dependencies']
        assert set(deps) == {'fixture-lock-mode'}
        found = re.findall(r'fixture-lock-mode-([12])\.0\.0\.tgz$', deps['fixture-lock-mode'])
        assert len(found) == 1
        return int(found[0])

    def locked(manager, text):
        if manager == 'npm':
            return version(json.loads(text)['packages']['node_modules/fixture-lock-mode']['version'])
        # Deliberately fixed local-tarball profile, not a YAML/general lock codec.
        found = set(re.findall(r'fixture-lock-mode-([12])\.0\.0\.tgz', text))
        assert len(found) == 1
        return int(next(iter(found)))

    def stream_runtime(capture, stem):
        data = json.loads((capture / (stem + '-runtime.stdout')).read_text())
        if 'error' in data:
            assert data['error'] == 'MODULE_NOT_FOUND'
            return 0
        return version(data['value'])

    rows, receipt = load(run, 36)
    file_by_sha = {sha(p): p for p in run.glob('*-*.json') if p.name not in ['trace.json', 'receipt.json']}
    file_by_sha.update({sha(p): p for p in run.glob('*-pnpm-lock.yaml')})
    file_by_sha.update({sha(p): p for p in run.glob('*-yarn.lock')})
    module_deltas = []
    for manager in ['npm', 'pnpm', 'yarn']:
        prior_runtime = 0
        previous = None
        for r in [r for r in rows if r['app'] == manager and not r['case'].endswith('-runtime')]:
            b, a = r['observed']['before'], r['observed']['after']
            mode = 'refresh' if r['case'] == 'initial-install' else 'resolve-only' if r['case'] == 'resolution-only' else 'frozen'
            want = wanted(file_by_sha[b['manifestSha256']].read_text())
            lock = locked(manager, file_by_sha[b['lockSha256']].read_text()) if b['lockSha256'] else 0
            old_payload = prior_runtime if b['modulesPresent'] else 0
            if previous is not None and r['case'] != 'rematerialize-frozen':
                assert b['moduleFiles'] == previous['moduleFiles']
            case = dict(profile=manager, mode=mode, wanted=want, locked=lock, payload=old_payload,
                        hidden=lock if manager == 'npm' and b['modulesPresent'] else 0)
            new_lock = locked(manager, file_by_sha[a['lockSha256']].read_text()) if a['lockSha256'] else 0
            new_payload = stream_runtime(run, manager + '-' + r['case'])
            cases.append(case)
            ok = r['outcome']['exitCode'] == 0
            # Only three shared fields were independently observed here. The npm
            # before-index label is source-interpreted, not decoded native data.
            expected.append('/'.join(str(int(x)) for x in [ok, new_lock, new_payload]))
            shared_fields.append(3)
            assert b['manifestSha256'] == a['manifestSha256']
            if not ok:
                assert b == a
            if mode == 'frozen' and ok:
                assert b['lockSha256'] == a['lockSha256']
            if mode == 'resolve-only':
                assert new_payload == old_payload == 1 and new_lock == want == 2
                names = b['moduleFiles'].keys() | a['moduleFiles'].keys()
                changed = sorted(n for n in names if b['moduleFiles'].get(n) != a['moduleFiles'].get(n))
                assert changed == (['.package-lock.json'] if manager == 'npm' else [])
                module_deltas.append(dict(app=manager, changedModuleEntries=changed))
            prior_runtime, previous = new_payload, a
        assert prior_runtime == 2

    followup_outcomes = []
    for capture in followups:
        rec = json.loads((capture / 'receipt.json').read_text())
        rows, rec = load(capture, 10 if rec.get('control') else 8)
        images = [p for p in (capture / 'images').rglob('*.json')]
        values = {sha(p): p.read_text() for p in images}

        def observed_state(image):
            def get(path):
                return values[image[path]['sha256']] if path in image else None
            pkg, lock = get('package.json'), get('package-lock.json')
            installed, hidden = get('node_modules/fixture-lock-mode/package.json'), get('node_modules/.package-lock.json')
            return dict(wanted=wanted(pkg), locked=locked('npm', lock) if lock else 0,
                payload=version(json.loads(installed)['version']) if installed else 0,
                hidden=locked('npm', hidden) if hidden else 0)

        local = {}
        for r in rows:
            if r['case'].endswith('-runtime'):
                continue
            before, after = r['observed']['before'], r['observed']['after']
            b, a = observed_state(before), observed_state(after)
            mode = 'resolve-only' if r['case'] == 'resolution-only' else 'frozen' if r['case'] == 'clean-frozen' else 'refresh'
            cases.append(dict(profile='npm', mode=mode, **b))
            expected.append('/'.join(str(x) for x in [1, a['locked'], a['payload'], a['hidden']]))
            shared_fields.append(4)
            assert stream_runtime(capture, r['case']) == a['payload']
            assert before['package.json'] == after['package.json']
            local[r['case']] = a
        assert local['resolution-only'] == local['normal-refresh'] == dict(wanted=2, locked=2, payload=1, hidden=2)
        assert local['clean-frozen']['payload'] == 2
        if rec.get('control'):
            edit, = rec['ownerEdits']
            assert edit['kind'] == 'remove-owned-hidden-lock-control'
            assert edit['before']['node_modules/.package-lock.json']
            b, a = dict(edit['before']), dict(edit['after'])
            del b['node_modules/.package-lock.json']
            assert b == a, 'Control changed more than its private hidden index.'
            assert local['refresh-without-hidden']['payload'] == 2
        followup_outcomes.append(dict(capture=str(capture.relative_to(ROOT)), control=rec.get('control', False), states=local))
        references.append(dict(capture=str(capture.relative_to(ROOT)), archivedFixtureBasis=rec['archivesBasis']))

    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)
    path = generated / 'lock-modes.json'
    path.write_text(json.dumps(dict(schema=1, cases=cases), indent=2) + '\n')
    env = dict(os.environ, LEAN_PATH=str(ROOT / '.build/formal'), BEND_NO_TELEMETRY='1')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')

    def lean_run(input_path):
        return subprocess.run([lean, '--run', 'applications/js-peers/LockModesCase.lean', str(input_path)],
            cwd=ROOT, env=env, capture_output=True, text=True)

    result = lean_run(path)
    assert result.returncode == 0, result.stdout + result.stderr
    actual = json.loads(result.stdout)
    assert ['/'.join(row.split('/')[:n]) for row, n in zip(actual, shared_fields)] == expected
    bit = lambda v: ['M.Absent{}', 'M.One{}', 'M.Two{}'][v]
    calls = []
    for c in cases:
        profile = {'npm': 'Npm', 'pnpm': 'Pnpm', 'yarn': 'Yarn'}[c['profile']]
        mode = {'refresh': 'Refresh', 'frozen': 'Frozen', 'resolve-only': 'ResolveOnly'}[c['mode']]
        args = ','.join(bit(c[n]) for n in ['wanted', 'locked', 'payload', 'hidden'])
        calls.append(f'render(M.{profile}{{}},M.{mode}{{}},M.State{{{args}}}) ++ "\\n"')
    runner = generated / 'LockModesCase.bend'
    runner.write_text('import Base\nimport ../LockModes.bend as M\n\ndef label(v: M.Revision) -> String:\n  match v:\n    case M.Absent{}: "0"\n    case M.One{}: "1"\n    case M.Two{}: "2"\n\ndef bit(v: Bool) -> String:\n  match v:\n    case True{}: "1"\n    case False{}: "0"\n\ndef fields(ok: Bool, s: M.State) -> String:\n  match s:\n    case M.State{wanted,locked,payload,hidden}: bit(ok) ++ "/" ++ label(locked) ++ "/" ++ label(payload) ++ "/" ++ label(hidden)\n\ndef render(+profile: M.Profile, +mode: M.Mode, +s: M.State) -> String:\n  fields(M.accepted(mode,s),M.step(profile,mode,s))\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(calls) + ')\n')
    result = subprocess.run([bend, str(runner)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == actual
    negatives = [dict(schema=2, cases=cases),
        *[dict(schema=1, cases=[dict(cases[0], **change)]) for change in
          [dict(profile='classic-yarn'), dict(mode='check-cache'), dict(wanted=0), dict(locked=3), dict(profile='pnpm', hidden=1)]]]
    for i, negative in enumerate(negatives):
        bad = generated / f'lock-modes-negative-{i}.json'
        bad.write_text(json.dumps(negative))
        result = lean_run(bad)
        assert result.returncode == 2 and result.stderr
    assert all(sha(ROOT / name) == value for name, value in basis.items()), 'Frozen comparison inputs changed.'
    report = dict(schema=1, nativeCommands=54, modeledInstallOutcomes=len(cases), sharedProfileCases=18,
        decodedNpmHiddenCases=len(cases) - 18, bothModelsMatch=True, unsupportedInputsRefused=len(negatives),
        moduleDeltasForResolutionOnly=module_deltas, followups=followup_outcomes, fixtureReferences=references,
        rejectedInterpretations=['lock current means payload current', 'lock-only leaves every module entry unchanged',
            'successful ordinary npm install always matches requested payload in this profile', 'hidden index is necessarily actual payload evidence'],
        adapterSha256=ADAPTER, basisSha256=basis,
        limits=['Nonempty one-dependency local-archive profile; only versions1/2, scripts disabled, no registry network.',
            'Main18cases compare accepted/lock/runtime only; their npm index input is source-interpreted. Followup9cases decode saved hidden and package metadata separately.',
            'Decoder/replays are research tools, not package-manager codecs or a general resolver/linker/cache admission model.',
            'No interruption, arbitrary filesystems, symlinks/mtime races, workspaces, peers, native-build or multi-platform qualification.',
            'Native collectors remain outside ordinary CI. Proposed cache invalidation is not an implemented production change.'])
    (run / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['basisSha256', 'followups']}, indent=2))


if __name__ == '__main__':
    main()
