#!/usr/bin/env python3
"""Prepare/control a private VS Code fixture. Desktop lease is required to launch
or request GUI/editor actions. This script does not grant desktop authority.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
APP = Path('/Applications/Visual Studio Code.app/Contents')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'launch', 'request'])
    parser.add_argument('run', type=Path, nargs='?')
    parser.add_argument('operation', nargs='?')
    args = parser.parse_args()
    if args.action == 'prepare':
        product_commit = json.loads((APP / 'Resources/app/product.json').read_text())['commit']
        selected_commit = json.loads((ROOT / 'applications/sources/vscode-source.json').read_text())['commit']
        assert product_commit == selected_commit, 'Installed VS Code changed; review source/tool pins before collecting evidence.'
        run = ROOT / 'applications/evidence' / ('vscode-native-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        run.mkdir(parents=True)
        work = Path(tempfile.mkdtemp(prefix='rules-vscode-', dir='/private/tmp'))
        for p in [work / 'project', work / 'extension', work / 'extensions', work / 'user-data/User']:
            p.mkdir(parents=True)
        (work / 'project/document.txt').write_text('original\n')
        shutil.copyfile(HERE / 'native-extension.cjs', work / 'extension/extension.cjs')
        (work / 'extension/package.json').write_text(json.dumps({'name': 'rules-private-native-fixture', 'publisher': 'rules-study',
            'version': '0.0.1', 'engines': {'vscode': '^1.92.0'}, 'main': './extension.cjs', 'activationEvents': ['onStartupFinished']}, indent=2) + '\n')
        settings = {'workbench.startupEditor': 'none', 'files.autoSave': 'off', 'files.hotExit': 'off',
                    'telemetry.telemetryLevel': 'off', 'update.mode': 'none', 'extensions.autoUpdate': False,
                    'extensions.autoCheckUpdates': False, 'security.workspace.trust.enabled': False,
                    'git.enabled': False, 'chat.disableAIFeatures': True}
        (work / 'user-data/User/settings.json').write_text(json.dumps(settings, indent=2) + '\n')
        meta = {'schema': 1, 'work': str(work), 'output': str(run / 'observed.json'),
                'extensionSha256': hashlib.sha256((HERE / 'native-extension.cjs').read_bytes()).hexdigest(),
                'product': product_commit}
        (run / 'meta.json').write_text(json.dumps(meta, indent=2) + '\n')
        shutil.copyfile(HERE / 'native-extension.cjs', run / 'extension.cjs')
        print(json.dumps({'run': str(run), 'work': str(work)}, indent=2))
        return
    assert args.run
    run = args.run.resolve()
    meta = json.loads((run / 'meta.json').read_text())
    work = Path(meta['work'])
    assert work.parent == Path('/private/tmp') and work.name.startswith('rules-vscode-')
    if args.action == 'launch':
        executable = plistlib.loads((APP / 'Info.plist').read_bytes())['CFBundleExecutable']
        command = [str(APP / 'MacOS' / executable), '--new-window', '--skip-welcome', '--skip-release-notes', '--use-inmemory-secretstorage',
                   '--user-data-dir', str(work / 'user-data'), '--extensions-dir', str(work / 'extensions'),
                   '--extensionDevelopmentPath=' + str(work / 'extension'), str(work / 'project')]
        assert json.loads((APP / 'Resources/app/product.json').read_text())['commit'] == meta['product']
        for d in ['home', 'tmp']:
            (work / d).mkdir(exist_ok=True)
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(Path.home()), 'TMPDIR': str(work / 'tmp'),
               'LANG': 'en_US.UTF-8', 'SHELL': '/bin/bash', 'RULES_VSCODE_FIXTURE': str(run / 'meta.json')}
        with (work / 'app.stdout').open('wb') as out, (work / 'app.stderr').open('wb') as err:
            p = subprocess.Popen(command, env=env, stdout=out, stderr=err, start_new_session=True)
            (run / 'process.json').write_text(json.dumps({'pid': p.pid, 'argv': command}, indent=2) + '\n')
            print(json.dumps({'pid': p.pid, 'run': str(run)}), flush=True)
            code = p.wait()
        (run / 'exit.json').write_text(json.dumps({'exitCode': code}) + '\n')
        print(json.dumps({'exitCode': code, 'outputExists': Path(meta['output']).exists()}))
        return
    assert args.operation in ['edit-one', 'edit-two', 'save', 'undo', 'redo', 'external-clean', 'edit-dirty', 'external-dirty', 'revert', 'quit']
    before = json.loads(Path(meta['output']).read_text())
    sequence = before['handled'] + 1
    request = {'sequence': sequence, 'action': args.operation}
    tmp = work / 'control.tmp'
    tmp.write_text(json.dumps(request) + '\n')
    tmp.replace(work / 'control.json')
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        current = json.loads(Path(meta['output']).read_text())
        if current['handled'] == sequence:
            print(json.dumps({'status': current['status'], 'row': current['rows'][-1]}, indent=2))
            return
        time.sleep(0.08)
    raise RuntimeError('Fixture did not acknowledge; inspect current state before retrying.')


if __name__ == '__main__':
    main()
