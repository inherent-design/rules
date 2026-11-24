#!/usr/bin/env python3
"""Owner-run frozen/lock-only fixture; no registry, scripts, or user project."""
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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    pins = json.loads((HERE / 'sources/local-pins.json').read_text())['tools']
    for key in ['node', 'npm', 'pnpm', 'yarn']:
        assert sha(Path(pins[key]['path'])) == pins[key]['sha256'], key
    run = HERE / 'evidence' / ('js-lock-modes-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    (run / 'probe.py').write_bytes(PRODUCER)
    work = Path(tempfile.mkdtemp(prefix='rules-js-lock-modes-', dir='/private/tmp'))
    for root in [work, *work.parents]:
        assert not any((root / f).exists() for f in ['.npmrc', '.yarnrc', '.yarnrc.yml', 'pnpm-workspace.yaml']), root
    archives = work / 'archives'
    archives.mkdir()
    for version in ['1.0.0', '2.0.0']:
        with tarfile.open(archives / ('fixture-lock-mode-' + version + '.tgz'), 'w:gz') as tar:
            for name, text in [('package.json', json.dumps({'name': 'fixture-lock-mode', 'version': version, 'main': 'index.js'})),
                               ('index.js', 'module.exports = ' + json.dumps(version) + ';\n')]:
                payload = text.encode()
                info = tarfile.TarInfo('package/' + name)
                info.size, info.mode, info.mtime = len(payload), 0o644, 0
                tar.addfile(info, io.BytesIO(payload))
    rows, edits = [], []
    try:
        for manager in ['npm', 'pnpm', 'yarn']:
            base = work / manager
            project = base / 'project'
            for path in [project, base / 'home', base / 'cache', base / 'config', base / 'tmp']:
                path.mkdir(parents=True)
            for name in ['user.npmrc', 'global.npmrc']:
                (base / 'config' / name).write_text('')
            manifest = project / 'package.json'

            def author(version):
                before = sha(manifest) if manifest.exists() else None
                manifest.write_text(json.dumps({'name': 'lock-mode-fixture', 'private': True,
                    'dependencies': {'fixture-lock-mode': 'file:' + str(archives / ('fixture-lock-mode-' + version + '.tgz'))}}, indent=2) + '\n')
                edits.append(dict(app=manager, kind='author-manifest', version=version,
                    beforeSha256=before, afterSha256=sha(manifest)))

            author('1.0.0')
            if manager == 'yarn':
                (project / '.yarnrc.yml').write_text('nodeLinker: node-modules\nenableGlobalCache: false\nenableNetwork: false\nenableTelemetry: false\nenableScripts: false\n')
            env = dict(PATH=str(Path(pins['node']['path']).parent) + ':/usr/bin:/bin', HOME=str(base / 'home'),
                XDG_CONFIG_HOME=str(base / 'config'), XDG_CACHE_HOME=str(base / 'cache'), TMPDIR=str(base / 'tmp'),
                NPM_CONFIG_USERCONFIG=str(base / 'config/user.npmrc'), NPM_CONFIG_GLOBALCONFIG=str(base / 'config/global.npmrc'),
                NPM_CONFIG_CACHE=str(base / 'cache/npm'), NPM_CONFIG_REGISTRY='http://127.0.0.1:9',
                LANG='en_US.UTF-8', COREPACK_ENABLE_NETWORK='0', YARN_ENABLE_TELEMETRY='0',
                YARN_ENABLE_IMMUTABLE_INSTALLS='false', DO_NOT_TRACK='1', MISE_SKIP_RESHIM='1')
            if manager == 'npm':
                prefix = [pins['npm']['path']]
                common = ['--offline', '--ignore-scripts', '--no-audit', '--no-fund']
                mutable, frozen, lock_only = ['install'], ['ci'], ['install', '--package-lock-only']
                lock = project / 'package-lock.json'
            elif manager == 'pnpm':
                prefix = [pins['pnpm']['path']]
                common = ['--offline', '--ignore-scripts', '--store-dir', str(base / 'store')]
                mutable, frozen, lock_only = ['install', '--no-frozen-lockfile'], ['install', '--frozen-lockfile'], ['install', '--lockfile-only', '--no-frozen-lockfile']
                lock = project / 'pnpm-lock.yaml'
            else:
                prefix = [pins['node']['path'], pins['yarn']['path']]
                common = []
                mutable, frozen, lock_only = ['install'], ['install', '--immutable'], ['install', '--mode=update-lockfile']
                lock = project / 'yarn.lock'

            def image():
                modules = project / 'node_modules'
                files = {}
                if modules.exists():
                    for p in sorted(modules.rglob('*')):
                        if p.is_symlink():
                            files[str(p.relative_to(modules))] = {'symlink': os.readlink(p)}
                        elif p.is_file():
                            files[str(p.relative_to(modules))] = {'sha256': sha(p), 'bytes': p.stat().st_size}
                return dict(manifestSha256=sha(manifest), lockSha256=sha(lock) if lock.exists() else None,
                    modulesPresent=modules.exists(), moduleFiles=files)

            def command(label, args):
                before = image()
                start = time.monotonic()
                result = subprocess.run(args, cwd=project, env=env, input=b'', capture_output=True, timeout=90)
                stem = manager + '-' + label
                for stream, data in [('stdout', result.stdout), ('stderr', result.stderr)]:
                    (run / (stem + '.' + stream)).write_bytes(data)
                rows.append(dict(v=1, app=manager, case=label, argv=args,
                    observed=dict(before=before, after=image(), seconds=time.monotonic() - start,
                        stdoutSha256=hashlib.sha256(result.stdout).hexdigest(), stderrSha256=hashlib.sha256(result.stderr).hexdigest()),
                    outcome=dict(exitCode=result.returncode)))
                (run / 'trace.json').write_text(json.dumps(rows, indent=2) + '\n')
                return result

            def inspect(label):
                result = command(label + '-runtime', [pins['node']['path'], '-e',
                    'try {console.log(JSON.stringify({value:require("fixture-lock-mode"),path:require.resolve("fixture-lock-mode")}));}'
                    ' catch(e) {console.log(JSON.stringify({error:e.code}));}'])
                assert result.returncode == 0
                shutil.copyfile(manifest, run / (manager + '-' + label + '-package.json'))
                if lock.exists():
                    shutil.copyfile(lock, run / (manager + '-' + label + '-' + lock.name))

            for label, args in [('missing-frozen', frozen), ('initial-install', mutable),
                                ('stale-frozen', frozen), ('resolution-only', lock_only),
                                ('current-frozen', frozen), ('rematerialize-frozen', frozen)]:
                if label == 'stale-frozen':
                    author('2.0.0')
                if label == 'rematerialize-frozen':
                    before = image()
                    shutil.rmtree(project / 'node_modules')
                    edits.append(dict(app=manager, kind='remove-owned-node-modules', before=before, after=image()))
                result = command(label, prefix + args + common)
                inspect(label)
                # Unexpected results remain evidence; stop before assuming later preconditions.
                if label not in ['missing-frozen', 'stale-frozen'] and result.returncode != 0:
                    raise RuntimeError(manager + ' ' + label + ' failed; original evidence retained.')
        receipt = dict(schema=1, producerSha256=hashlib.sha256(PRODUCER).hexdigest(),
            tools={key: pins[key] for key in ['node', 'npm', 'pnpm', 'yarn']},
            platform=platform.platform(), architecture=platform.machine(), originalWork=str(work),
            archives={p.name: dict(sha256=sha(p), bytes=p.stat().st_size) for p in archives.iterdir()},
            commands=len(rows), ownerEdits=edits,
            scope='One exact local tarball dependency at two versions; private project/home/config/cache, disabled scripts and offline/disabled network. Lock hashes, module image and fresh-process runtime lookup measured separately. No cache-global-effect, interruption, registry, peer/workspace, or general solver qualification.')
        (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(dict(run=str(run), commands=len(rows), outcomes=[(r['app'], r['case'], r['outcome']['exitCode']) for r in rows if not r['case'].endswith('-runtime')]), indent=2))
    finally:
        shutil.move(str(work), str(run / 'work'))


if __name__ == '__main__':
    main()
