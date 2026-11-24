#!/usr/bin/env python3
"""Owner-run local removal/re-adoption study; never open a user project."""
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
PRODUCER = Path(__file__).read_bytes()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    pins = json.loads((HERE / 'sources/local-pins.json').read_text())['tools']
    for key in ['node', 'npm', 'pnpm', 'yarn']:
        assert sha(Path(pins[key]['path'])) == pins[key]['sha256'], key
    run = HERE / 'evidence' / ('js-removal-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    (run / 'probe.py').write_bytes(PRODUCER)
    work = Path(tempfile.mkdtemp(prefix='rules-js-removal-', dir='/private/tmp'))
    for root in [work, *work.parents]:
        assert not any((root / f).exists() for f in ['.npmrc', '.yarnrc', '.yarnrc.yml', 'pnpm-workspace.yaml']), root
    archives = work / 'archives'
    archives.mkdir()

    def archive(name, dependencies, script):
        path = archives / (name + '-1.0.0.tgz')
        manifest = {'name': name, 'version': '1.0.0', 'main': 'index.js', 'dependencies': dependencies}
        with tarfile.open(path, 'w:gz') as tar:
            for filename, data in [('package.json', json.dumps(manifest)), ('index.js', script)]:
                payload = data.encode()
                info = tarfile.TarInfo('package/' + filename)
                info.size, info.mode, info.mtime = len(payload), 0o644, 0
                tar.addfile(info, io.BytesIO(payload))
        return path

    leaf = archive('fixture-leaf', {}, 'module.exports = "leaf-one";\n')
    parent = archive('fixture-parent', {'fixture-leaf': 'file:' + str(leaf)}, 'module.exports = require("fixture-leaf");\n')
    rows = []
    try:
        for manager in ['npm', 'pnpm', 'yarn']:
            base, project = work / manager, work / manager / 'project'
            for p in [project, base / 'home', base / 'cache', base / 'config', base / 'tmp']:
                p.mkdir(parents=True)
            for name in ['user.npmrc', 'global.npmrc']:
                (base / 'config' / name).write_text('')
            manifest = project / 'package.json'
            manifest.write_text(json.dumps({'name': 'removal-fixture', 'private': True,
                'dependencies': {'fixture-leaf': 'file:' + str(leaf), 'fixture-parent': 'file:' + str(parent)}}, indent=2) + '\n')
            if manager == 'yarn':
                (project / '.yarnrc.yml').write_text('nodeLinker: node-modules\nenableGlobalCache: false\nenableNetwork: false\nenableTelemetry: false\nenableScripts: false\n')
            env = {'PATH': str(Path(pins['node']['path']).parent) + ':/usr/bin:/bin', 'HOME': str(base / 'home'),
                'XDG_CONFIG_HOME': str(base / 'config'), 'XDG_CACHE_HOME': str(base / 'cache'), 'TMPDIR': str(base / 'tmp'),
                'NPM_CONFIG_USERCONFIG': str(base / 'config/user.npmrc'), 'NPM_CONFIG_GLOBALCONFIG': str(base / 'config/global.npmrc'),
                'NPM_CONFIG_CACHE': str(base / 'cache/npm'), 'NPM_CONFIG_REGISTRY': 'http://127.0.0.1:9',
                'LANG': 'en_US.UTF-8', 'COREPACK_ENABLE_NETWORK': '0', 'YARN_ENABLE_TELEMETRY': '0',
                'YARN_ENABLE_IMMUTABLE_INSTALLS': 'false', 'DO_NOT_TRACK': '1', 'MISE_SKIP_RESHIM': '1'}
            if manager == 'npm':
                prefix = [pins['npm']['path']]
                common = ['--offline', '--ignore-scripts', '--no-audit', '--no-fund']
                install, remove, add = ['install'], ['uninstall'], ['install']
                lock = project / 'package-lock.json'
            elif manager == 'pnpm':
                prefix = [pins['pnpm']['path']]
                common = ['--offline', '--ignore-scripts', '--store-dir', str(base / 'store')]
                install, remove, add = ['install'], ['remove'], ['add']
                lock = project / 'pnpm-lock.yaml'
            else:
                prefix = [pins['node']['path'], pins['yarn']['path']]
                common = []
                install, remove, add = ['install'], ['remove'], ['add']
                lock = project / 'yarn.lock'

            def state():
                return {'manifestSha256': sha(manifest), 'dependencies': json.loads(manifest.read_text()).get('dependencies', {}),
                    'lockSha256': sha(lock) if lock.exists() else None}

            def command(label, argv):
                before = state()
                started = time.monotonic()
                result = subprocess.run(argv, cwd=project, env=env, input=b'', capture_output=True, timeout=90)
                stem = manager + '-' + label
                for suffix, data in [('stdout', result.stdout), ('stderr', result.stderr)]:
                    (run / (stem + '.' + suffix)).write_bytes(data)
                rows.append({'v': 1, 'app': manager, 'case': label, 'argv': argv,
                    'observed': {'before': before, 'after': state(), 'seconds': time.monotonic() - started,
                        'stdoutSha256': hashlib.sha256(result.stdout).hexdigest(), 'stderrSha256': hashlib.sha256(result.stderr).hexdigest()},
                    'outcome': {'exitCode': result.returncode}})
                (run / 'trace.json').write_text(json.dumps(rows, indent=2) + '\n')
                return result

            def inspect(label):
                script = '''const fs=require('fs'), out={};
for (const name of ['fixture-parent','fixture-leaf']) {
 try {out[name]={value:require(name),path:require.resolve(name)};}
 catch(e) {out[name]={error:e.code};}
}
console.log(JSON.stringify(out));'''
                result = command(label + '-runtime', [pins['node']['path'], '-e', script])
                assert result.returncode == 0, label
                shutil.copyfile(manifest, run / (manager + '-' + label + '-package.json'))
                shutil.copyfile(lock, run / (manager + '-' + label + '-' + lock.name))

            first = command('install', prefix + install + common)
            if first.returncode != 0:
                raise RuntimeError(manager + ' fixture installation failed; retain observed trace before designing the next step.')
            inspect('installed')
            for label, args in [('remove-direct-leaf', remove + ['fixture-leaf']),
                    ('remove-transitive-only', remove + ['fixture-leaf']),
                    ('readopt-identical-leaf', add + ['fixture-leaf@file:' + str(leaf)]),
                    ('remove-parent', remove + ['fixture-parent']),
                    ('remove-last-leaf', remove + ['fixture-leaf'])]:
                result = command(label, prefix + args + common)
                if label != 'remove-transitive-only' and result.returncode != 0:
                    raise RuntimeError(manager + ' ' + label + ' refused; retain actual result.')
                inspect(label)
        receipt = {'schema': 1, 'producerSha256': hashlib.sha256(PRODUCER).hexdigest(),
            'tools': {k: pins[k] for k in ['node', 'npm', 'pnpm', 'yarn']},
            'platform': platform.platform(), 'architecture': platform.machine(), 'originalWork': str(work),
            'archives': {p.name: {'sha256': sha(p), 'bytes': p.stat().st_size} for p in archives.iterdir()},
            'commands': len(rows), 'scope': 'Two generated local archives, private project/config/cache; offline or disabled network and no lifecycle scripts. Root declarations and reachable runtime are measured independently; private cache reclamation and crash safety are not measured.'}
        (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'run': str(run), 'commands': len(rows), 'commandOutcomes': [(r['app'], r['case'], r['outcome']['exitCode']) for r in rows if not r['case'].endswith('-runtime')]}, indent=2))
    finally:
        shutil.move(str(work), str(run / 'work'))


if __name__ == '__main__':
    main()
