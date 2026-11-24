#!/usr/bin/env python3
"""Private offline peer-context fixtures for npm, pnpm, and Yarn Berry.

Archives contain only this file's generated manifests and tiny JavaScript.
No package lifecycle script, registry dependency, or user project is used.
Failures are observations, not silently retried or converted into successes.
"""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import time

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main():
    pins = json.loads((HERE / 'sources/local-pins.json').read_text())['tools']
    for key in ['node', 'npm', 'pnpm', 'yarn']:
        assert sha(Path(pins[key]['path'])) == pins[key]['sha256'], key
    node = pins['node']['path']
    run = HERE / 'evidence' / ('js-peers-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir(parents=True)
    shutil.copyfile(Path(__file__), run / 'probe.py')
    work = Path(tempfile.mkdtemp(prefix='rules-js-peers-', dir='/private/tmp'))
    for root in [work, *work.parents]:
        assert not any((root / f).exists() for f in ['.npmrc', '.yarnrc', '.yarnrc.yml', 'pnpm-workspace.yaml']), root
    archives = work / 'archives'
    archives.mkdir()

    def archive(name, version, source, peer=False):
        manifest = {'name': name, 'version': version, 'main': 'index.js'}
        if peer:
            manifest['peerDependencies'] = {'fixture-api': '*'}
        path = archives / (name + '-' + version + '.tgz')
        with tarfile.open(path, 'w:gz') as tar:
            for filename, data in [('package.json', json.dumps(manifest)), ('index.js', source)]:
                payload = data.encode()
                info = tarfile.TarInfo('package/' + filename)
                info.size, info.mode, info.mtime = len(payload), 0o644, 0
                tar.addfile(info, io.BytesIO(payload))
        return path

    api1 = archive('fixture-api', '1.0.0', 'module.exports = "api-one";\n')
    api2 = archive('fixture-api', '2.0.0', 'module.exports = "api-two";\n')
    plugin = archive('fixture-plugin', '1.0.0', 'module.exports = {peer: require("fixture-api"), peerPath: require.resolve("fixture-api")};\n', True)
    archives_receipt = {p.name: {'sha256': sha(p), 'bytes': p.stat().st_size} for p in archives.iterdir()}
    rows, findings = [], {}
    script = '''const fs = require('fs');
const {createRequire} = require('module');
const {resolve} = require('path');
const result = {};
for (const side of ['left', 'right']) {
  const req = createRequire(resolve(side, 'package.json'));
  const pluginPath = req.resolve('fixture-plugin');
  result[side] = {direct: req('fixture-api'), directPath: req.resolve('fixture-api'),
    plugin: req('fixture-plugin'), pluginPath,
    pluginContent: fs.readFileSync(pluginPath, 'utf8'),
    pluginManifest: fs.readFileSync(req.resolve('fixture-plugin/package.json'), 'utf8')};
}
console.log(JSON.stringify(result));
'''
    try:
        for manager in ['npm', 'pnpm', 'yarn']:
            base = work / manager
            project = base / 'project'
            for path in [project, base / 'home', base / 'cache', base / 'config', base / 'tmp']:
                path.mkdir(parents=True)
            for name in ['user.npmrc', 'global.npmrc']:
                (base / 'config' / name).write_text('')
            root_manifest = {'name': 'peer-fixture', 'private': True, 'workspaces': ['left', 'right']}
            (project / 'package.json').write_text(json.dumps(root_manifest, indent=2) + '\n')
            for side, api in [('left', api1), ('right', api2)]:
                (project / side).mkdir()
                manifest = {'name': 'fixture-' + side, 'version': '1.0.0', 'private': True,
                            'dependencies': {'fixture-api': 'file:' + str(api), 'fixture-plugin': 'file:' + str(plugin)}}
                (project / side / 'package.json').write_text(json.dumps(manifest, indent=2) + '\n')
            if manager == 'pnpm':
                (project / 'pnpm-workspace.yaml').write_text('packages:\n  - left\n  - right\n')
            if manager == 'yarn':
                (project / '.yarnrc.yml').write_text('nodeLinker: node-modules\nenableGlobalCache: false\nenableNetwork: false\nenableTelemetry: false\nenableScripts: false\n')
            env = {'PATH': str(Path(node).parent) + ':/usr/bin:/bin', 'HOME': str(base / 'home'),
                   'XDG_CONFIG_HOME': str(base / 'config'), 'XDG_CACHE_HOME': str(base / 'cache'),
                   'TMPDIR': str(base / 'tmp'), 'LANG': 'en_US.UTF-8',
                   'NPM_CONFIG_USERCONFIG': str(base / 'config/user.npmrc'),
                   'NPM_CONFIG_GLOBALCONFIG': str(base / 'config/global.npmrc'),
                   'NPM_CONFIG_CACHE': str(base / 'cache/npm'), 'NPM_CONFIG_REGISTRY': 'http://127.0.0.1:9',
                   'MISE_SKIP_RESHIM': '1', 'YARN_ENABLE_TELEMETRY': '0', 'YARN_ENABLE_IMMUTABLE_INSTALLS': 'false',
                   'COREPACK_ENABLE_NETWORK': '0', 'DO_NOT_TRACK': '1'}
            if manager == 'npm':
                prefix = [pins['npm']['path']]
                install = ['install', '--offline', '--ignore-scripts', '--no-audit', '--no-fund']
                frozen = ['ci', '--offline', '--ignore-scripts', '--no-audit', '--no-fund']
                lock_name = 'package-lock.json'
            elif manager == 'pnpm':
                prefix = [pins['pnpm']['path']]
                install = ['install', '--offline', '--ignore-scripts', '--store-dir', str(base / 'store')]
                frozen = install + ['--frozen-lockfile']
                lock_name = 'pnpm-lock.yaml'
            else:
                prefix = [node, pins['yarn']['path']]
                install = ['install']
                frozen = ['install', '--immutable']
                lock_name = 'yarn.lock'

            def state():
                return {'lockSha256': sha(project / lock_name), 'nodeModulesExists': (project / 'node_modules').exists(),
                        'manifests': {side: sha(project / side / 'package.json') for side in ['left', 'right']}}

            def command(label, argv, feature):
                before = state()
                start = time.monotonic()
                completed = subprocess.run(argv, cwd=project, env=env, capture_output=True, timeout=90)
                stem = manager + '-' + label
                (run / (stem + '.stdout')).write_bytes(completed.stdout)
                (run / (stem + '.stderr')).write_bytes(completed.stderr)
                rows.append({'v': 2, 'app': manager, 'feature': manager + '.' + feature, 'operationId': stem,
                             'profile': manager + '-darwin-arm64-local-tarballs-node-modules', 'target': str(project),
                             'basis': str(len(rows)), 'request': {'argv': argv},
                             'observed': {'before': before, 'after': state(), 'seconds': time.monotonic() - start,
                                          'stdoutSha256': hashlib.sha256(completed.stdout).hexdigest(),
                                          'stderrSha256': hashlib.sha256(completed.stderr).hexdigest()},
                             'outcome': {'exitCode': completed.returncode}})
                (run / 'trace.json').write_text(json.dumps(rows, indent=2) + '\n')
                return completed

            feature = {'npm': 'installation', 'pnpm': 'install-store', 'yarn': 'installation'}[manager]
            first = command('install', prefix + install, feature)
            observation = {'installExit': first.returncode, 'installed': None, 'frozenExit': None, 'afterFrozen': None}
            if first.returncode == 0:
                runtime = command('runtime', [node, '-e', script], feature)
                if runtime.returncode == 0:
                    observation['installed'] = json.loads(runtime.stdout)
                if manager == 'npm':
                    graph = command('list', prefix + ['ls', '--all', '--json', '--offline'], feature)
                    observation['listExit'] = graph.returncode
                left = project / 'left/package.json'
                changed = json.loads(left.read_text())
                changed['dependencies']['fixture-api'] = 'file:' + str(api2)
                left.write_text(json.dumps(changed, indent=2) + '\n')
                locked = command('frozen', prefix + frozen, feature)
                observation['frozenExit'] = locked.returncode
                after = command('after-frozen-runtime', [node, '-e', script], feature)
                if after.returncode == 0:
                    observation['afterFrozen'] = json.loads(after.stdout)
                # Retain generated manifests and lock for source-independent inspection.
                for src, dest in [(project / 'package.json', 'package.json'), (left, 'left-after.json'),
                                  (project / 'right/package.json', 'right.json'), (project / lock_name, lock_name)]:
                    if src.is_file():
                        shutil.copyfile(src, run / (manager + '-' + dest))
            findings[manager] = observation
            (run / 'findings.json').write_text(json.dumps(findings, indent=2) + '\n')
        (run / 'receipt.json').write_text(json.dumps({'schema': 1, 'entrypointSha256': sha(Path(__file__)),
            'tools': {k: pins[k] for k in ['node', 'npm', 'pnpm', 'yarn']}, 'archives': archives_receipt,
            'platform': platform.platform(), 'architecture': platform.machine(), 'originalWork': str(work),
            'retainedWork': 'work', 'ancestryConfigAbsent': True,
            'policy': 'Only generated local tarballs; private homes/config/stores; offline or disabled network; lifecycle scripts disabled.',
            'limits': ['Node-modules linker only; no lifecycle execution, registry trust, missing/incompatible peers, optional peers, or concurrent operations.',
                       'Profiles intentionally choose disabled scripts/offline operation; not claims about default package-manager policy.']}, indent=2) + '\n')
        print(json.dumps({'run': str(run), 'summary': {k: {'installExit': v['installExit'], 'frozenExit': v['frozenExit'], 'runtime': {side: {'direct': r['direct'], 'peer': r['plugin']['peer']} for side, r in (v['installed'] or {}).items()}} for k, v in findings.items()}}, indent=2))
    finally:
        shutil.move(str(work), str(run / 'work'))


if __name__ == '__main__':
    main()
