#!/usr/bin/env python3
"""Compare retained JS package-manager traces and two models; no installs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def hashed(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    trace = json.loads((run / 'trace.json').read_text())
    rows = {r['operationId']: r for r in trace}
    receipt = json.loads((run / 'receipt.json').read_text())
    assert hashed((run / 'probe.py').read_bytes()) == receipt['entrypointSha256']
    for row in trace:
        for stream in ['stdout', 'stderr']:
            assert hashed((run / (row['operationId'] + '.' + stream)).read_bytes()) == row['observed'][stream + 'Sha256']
    env = dict(os.environ, LEAN_PATH=str(ROOT / '.build'), BEND_NO_TELEMETRY='1')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)

    def evaluate(case):
        path = run / 'model-input.json'
        path.write_text(json.dumps(case, indent=2) + '\n')
        a = json.loads(subprocess.check_output([lean, '--run', 'applications/js-peers/Case.lean', str(path)], cwd=ROOT, env=env, text=True))
        for key in ['content', 'direct', 'hoisted', 'declared', 'locked', 'lockBytes', 'installed']:
            assert re.fullmatch(r'[0-9a-f]{64}', case[key]), key
        profile = {'npm': 'NpmHoisted', 'pnpm': 'PnpmIsolated', 'yarn': 'YarnNodeModules'}[case['profile']]
        q = json.dumps
        source = '''import Base
import ../Contexts.bend as C

def bit(b: Bool) -> String:
  match b:
    case True{}: "true"
    case False{}: "false"

def decision_lines(a: C.Admission) -> String:
  match a:
    case C.Decision{refused, state}:
      match state:
        case C.State{declared, locked, lock_bytes, installed}:
          bit(refused) ++ "\\n" ++ declared ++ "\\n" ++ lock_bytes ++ "\\n" ++ installed ++ "\\n"

def main() -> IO(Unit):
  do IO<Unit>:
    +i : C.Instance = C.instantiate(C.PROFILE{}, CONTENT, DIRECT, HOISTED)
    IO.write(C.content(i) ++ "\\n" ++ C.provider(i) ++ "\\n" ++ decision_lines(C.frozen_admission(C.State{DECLARED, LOCKED, LOCK_BYTES, INSTALLED})))
'''
        for token, value in [('PROFILE', profile), ('CONTENT', q(case['content'])), ('DIRECT', q(case['direct'])),
                             ('HOISTED', q(case['hoisted'])), ('DECLARED', q(case['declared'])), ('LOCKED', q(case['locked'])),
                             ('LOCK_BYTES', q(case['lockBytes'])), ('INSTALLED', q(case['installed']))]:
            source = source.replace(token, value)
        script = generated / 'NativeCase.bend'
        script.write_text(source)
        lines = subprocess.check_output([bend, str(script)], cwd=ROOT, env=env, text=True).splitlines()
        assert len(lines) == 6 and lines[2] in ['true', 'false']
        b = dict(zip(['content', 'peer', 'refused', 'declarationAfter', 'lockAfter', 'installedAfter'], lines))
        b['refused'] = lines[2] == 'true'
        assert a == b, (a, b)
        return a

    api = {label: receipt['archives'][name]['sha256'] for label, name in
           [('api-one', 'fixture-api-1.0.0.tgz'), ('api-two', 'fixture-api-2.0.0.tgz')]}
    assert len(set(api.values())) == 2
    cases, contents = [], set()
    for manager in ['npm', 'pnpm', 'yarn']:
        assert rows[manager + '-install']['outcome']['exitCode'] == 0
        assert rows[manager + '-runtime']['outcome']['exitCode'] == 0
        assert rows[manager + '-frozen']['outcome']['exitCode'] == 1
        assert rows[manager + '-after-frozen-runtime']['outcome']['exitCode'] == 0
        runtime = json.loads((run / (manager + '-runtime.stdout')).read_text())
        after = json.loads((run / (manager + '-after-frozen-runtime.stdout')).read_text())
        assert runtime == after
        frozen = rows[manager + '-frozen']['observed']
        assert frozen['before']['lockSha256'] == frozen['after']['lockSha256']
        assert frozen['before']['manifests'] == frozen['after']['manifests']
        lock_name = {'npm': 'package-lock.json', 'pnpm': 'pnpm-lock.yaml', 'yarn': 'yarn.lock'}[manager]
        assert hashed((run / (manager + '-' + lock_name)).read_bytes()) == frozen['after']['lockSha256']
        assert hashed((run / (manager + '-left-after.json')).read_bytes()) == frozen['after']['manifests']['left']
        assert hashed((run / (manager + '-right.json')).read_bytes()) == frozen['after']['manifests']['right']
        changed_left = json.loads((run / (manager + '-left-after.json')).read_text())
        assert changed_left['dependencies']['fixture-api'].endswith('/archives/fixture-api-2.0.0.tgz')
        # Reconstruct the single edited field; validate exact original bytes against
        # the before-install hash, rather than presenting reconstruction as a raw capture.
        original_left = json.loads(json.dumps(changed_left))
        original_left['dependencies']['fixture-api'] = original_left['dependencies']['fixture-api'].replace('fixture-api-2.0.0.tgz', 'fixture-api-1.0.0.tgz')
        reconstructed = (json.dumps(original_left, indent=2) + '\n').encode()
        assert hashed(reconstructed) == rows[manager + '-install']['observed']['before']['manifests']['left']
        installed = hashed(json.dumps(runtime, sort_keys=True).encode())
        for side in ['left', 'right']:
            observed = runtime[side]
            content = hashed((observed['pluginManifest'] + '\0' + observed['pluginContent']).encode())
            contents.add(content)
            manifest = json.loads(observed['pluginManifest'])
            assert manifest['name'] == 'fixture-plugin' and manifest['version'] == '1.0.0'
            assert manifest['peerDependencies'] == {'fixture-api': '*'}
            case = {'schema': 1, 'profile': manager, 'content': content, 'direct': api[observed['direct']],
                    'hoisted': api['api-one'], 'declared': api['api-two'], 'locked': api['api-one'],
                    'lockBytes': frozen['before']['lockSha256'], 'installed': installed}
            model = evaluate(case)
            assert model['content'] == content and model['peer'] == api[observed['plugin']['peer']]
            assert model['refused'] and model['declarationAfter'] == case['declared']
            assert model['lockAfter'] == frozen['after']['lockSha256'] and model['installedAfter'] == installed
            cases.append({'application': manager, 'workspace': side, 'input': case, 'model': model,
                          'nativePeer': api[observed['plugin']['peer']]})
    assert len(contents) == 1  # Same measured manifest+entrypoint bytes, different peer bindings.
    npm_graph = json.loads((run / 'npm-list.stdout').read_text())
    assert rows['npm-list']['outcome']['exitCode'] == 0 and not npm_graph.get('problems')
    right = {c['application']: c for c in cases if c['workspace'] == 'right'}
    assert right['npm']['nativePeer'] != right['npm']['input']['direct']
    assert all(right[m]['nativePeer'] == right[m]['input']['direct'] for m in ['pnpm', 'yarn'])
    assert right['npm']['input']['content'] == right['pnpm']['input']['content']
    (run / 'projected-cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    result = {'schema': 1, 'cases': len(cases), 'modelsAgreeWithNative': True,
              'uniformPeerProviderPolicyRejected': True, 'contentAloneAsRuntimeIdentityRejected': True,
              'frozenRefusalsPreserveMeasuredLockDraftAndBindings': True,
              'originalManifestReconstructionMatchesBeforeHashes': True,
              'traceSha256': hashed((run / 'trace.json').read_bytes()),
              'models': {p.name: hashed(p.read_bytes()) for p in [HERE / 'Contexts.lean', HERE / 'Contexts.bend', HERE / 'Case.lean']},
              'limits': ['Fixture-profile projection does not implement the full hoister, peer resolver, or semver algorithm.',
                         'Package content projects the measured manifest and entrypoint, not a universal filesystem tree identity.',
                         'Frozen admission/refusal is checked for one changed local dependency specification; matching admission is not install completion.',
                         'Lock, draft, and runtime-binding observations do not establish absence of cache/log or other file effects.',
                         'No registry, scripts, optional/missing peers, PnP linker, other operating system, or concurrency tested.']}
    (run / 'conformance.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
