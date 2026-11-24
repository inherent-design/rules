#!/usr/bin/env python3
"""Owner-run check of ordinary npm install after a lock-only change."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
PRODUCER = Path(__file__).read_bytes()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    original = HERE / 'evidence/js-lock-modes-20261124T104619177625Z'
    pins = json.loads((original / 'receipt.json').read_text())['tools']
    for key in ['node', 'npm']:
        assert sha(Path(pins[key]['path'])) == pins[key]['sha256']
    archive_rows = json.loads((original / 'receipt.json').read_text())['archives']
    archives = original / 'work/archives'
    for name, row in archive_rows.items():
        assert sha(archives / name) == row['sha256']
    run = HERE / 'evidence' / ('js-lock-npm-refresh-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    (run / 'probe.py').write_bytes(PRODUCER)
    work = Path(tempfile.mkdtemp(prefix='rules-js-lock-refresh-', dir='/private/tmp'))
    for parent in [work, *work.parents]:
        assert not (parent / '.npmrc').exists()
    for name in ['project', 'home', 'cache', 'config', 'tmp']:
        (work / name).mkdir()
    for name in ['user.npmrc', 'global.npmrc']:
        (work / 'config' / name).write_text('')
    project = work / 'project'
    env = dict(PATH=str(Path(pins['node']['path']).parent) + ':/usr/bin:/bin', HOME=str(work / 'home'),
        XDG_CONFIG_HOME=str(work / 'config'), XDG_CACHE_HOME=str(work / 'cache'), TMPDIR=str(work / 'tmp'),
        NPM_CONFIG_USERCONFIG=str(work / 'config/user.npmrc'), NPM_CONFIG_GLOBALCONFIG=str(work / 'config/global.npmrc'),
        NPM_CONFIG_CACHE=str(work / 'cache/npm'), NPM_CONFIG_REGISTRY='http://127.0.0.1:9', LANG='en_US.UTF-8')
    rows = []

    def image():
        return {str(p.relative_to(project)): dict(sha256=sha(p), bytes=p.stat().st_size)
                for p in sorted(project.rglob('*')) if p.is_file() and not p.is_symlink()}

    def command(label, argv):
        before = image()
        start = time.monotonic()
        result = subprocess.run(argv, cwd=project, env=env, input=b'', capture_output=True, timeout=90)
        for stream, data in [('stdout', result.stdout), ('stderr', result.stderr)]:
            (run / (label + '.' + stream)).write_bytes(data)
        after = image()
        row = dict(v=1, app='npm', case=label, argv=argv, observed=dict(before=before, after=after,
            seconds=time.monotonic() - start, stdoutSha256=hashlib.sha256(result.stdout).hexdigest(),
            stderrSha256=hashlib.sha256(result.stderr).hexdigest()), outcome=dict(exitCode=result.returncode))
        rows.append(row)
        (run / 'trace.json').write_text(json.dumps(rows, indent=2) + '\n')
        for p in sorted(project.rglob('*.json')):
            if p.is_file():
                dest = run / 'images' / label / p.relative_to(project)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(p.read_bytes())
        assert result.returncode == 0, label

    def inspect(label):
        command(label + '-runtime', [pins['node']['path'], '-e', 'console.log(JSON.stringify({value:require("fixture-lock-mode"),path:require.resolve("fixture-lock-mode")}))'])

    try:
        for label, version, args in [('initial-install', '1.0.0', ['install']),
                                     ('resolution-only', '2.0.0', ['install', '--package-lock-only']),
                                     ('normal-refresh', None, ['install']),
                                     ('clean-frozen', None, ['ci'])]:
            if version:
                (project / 'package.json').write_text(json.dumps(dict(name='lock-refresh-fixture', private=True,
                    dependencies={'fixture-lock-mode': 'file:' + str(archives / ('fixture-lock-mode-' + version + '.tgz'))}), indent=2) + '\n')
            command(label, [pins['npm']['path'], *args, '--offline', '--ignore-scripts', '--no-audit', '--no-fund'])
            inspect(label)
        receipt = dict(schema=1, producerSha256=hashlib.sha256(PRODUCER).hexdigest(), tools={k: pins[k] for k in ['node', 'npm']},
            originalWork=str(work), platform=platform.platform(), architecture=platform.machine(), commands=len(rows),
            archivesBasis=str(original.relative_to(HERE.parent)), archives=archive_rows,
            scope='New private project/cache; source archives are read-only from the prior capture. Ordinary npm install after lock-only versus ci; no scripts/network/registry/workspaces or interruption.')
        (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(dict(run=str(run), runtime={label: json.loads((run / (label + '-runtime.stdout')).read_text())
            for label in ['initial-install', 'resolution-only', 'normal-refresh', 'clean-frozen']}), indent=2))
    finally:
        shutil.move(str(work), str(run / 'work'))


if __name__ == '__main__':
    main()
