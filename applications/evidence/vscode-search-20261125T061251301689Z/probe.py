#!/usr/bin/env python3
"""Prepare/launch one isolated workspace/search fixture; desktop lease required."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import os
import plistlib
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
APP = Path('/Applications/Visual Studio Code.app/Contents')
PRODUCER = Path(__file__).read_bytes()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'launch'])
    parser.add_argument('run', nargs='?', type=Path)
    args = parser.parse_args()
    commit = json.loads((ROOT / 'applications/sources/vscode-source.json').read_text())['commit']
    assert json.loads((APP / 'Resources/app/product.json').read_text())['commit'] == commit
    assert sha(APP / 'MacOS/Code') == '826ae77cbbd1521dc8d295e4b80d042caa7d55c64cc36079cf6574b7d762e0e3'
    if args.action == 'prepare':
        run = ROOT / 'applications/evidence' / ('vscode-search-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        run.mkdir()
        work = Path(tempfile.mkdtemp(prefix='rules-vsc-search-', dir='/private/tmp'))
        assert len(str(work / 'user-data/1.14-main.sock').encode()) <= 103
        for folder in ['a', 'b', 'c', 'extension', 'extensions', 'user-data/User', 'tmp']:
            (work / folder).mkdir(parents=True)
        text = {'a/visible.txt':'needle disk-a\n', 'a/hidden.txt':'needle hidden-a\n',
                'a/search-hidden.txt':'needle search-hidden-a\n', 'b/visible.txt':'needle disk-b\n',
                'c/visible.txt':'needle disk-c\n', 'outside.txt':'needle outside\n'}
        for name, value in text.items():
            (work / name).write_text(value)
        settings = {'workbench.startupEditor':'none', 'files.autoSave':'off', 'files.hotExit':'off',
                    'telemetry.telemetryLevel':'off', 'update.mode':'none', 'extensions.autoUpdate':False,
                    'extensions.autoCheckUpdates':False, 'security.workspace.trust.enabled':False,
                    'git.enabled':False, 'chat.disableAIFeatures':True,
                    'files.exclude':{'**/hidden.txt':True}, 'search.exclude':{'**/search-hidden.txt':True},
                    'search.useIgnoreFiles':False, 'search.useGlobalIgnoreFiles':False,
                    'search.useParentIgnoreFiles':False, 'search.experimental.useIgnoreFilesInFindFiles':False}
        workspace = {'folders':[{'path':'a','name':'A'},{'path':'b','name':'B'}]}
        (work / 'user-data/User/settings.json').write_text(json.dumps(settings, indent=2) + '\n')
        workspace_path = work / 'Rules search study.code-workspace'
        workspace_path.write_text(json.dumps(workspace, indent=2) + '\n')
        package = {'name':'rules-private-search-fixture', 'publisher':'rules-study', 'version':'0.0.1',
                   'engines':{'vscode':'^1.147.0'}, 'main':'./extension.cjs', 'activationEvents':['onStartupFinished'],
                   'enabledApiProposals':['findTextInFiles']}
        (work / 'extension/package.json').write_text(json.dumps(package, indent=2) + '\n')
        extension = HERE / 'search-extension.cjs'
        (work / 'extension/extension.cjs').write_bytes(extension.read_bytes())
        for name, value in [('initial-files.json',text),('initial-settings.json',settings),
                            ('initial-workspace.json',workspace),('extension-package.json',package)]:
            (run / name).write_text(json.dumps(value, indent=2) + '\n')
        (run / 'extension.cjs').write_bytes(extension.read_bytes())
        (run / 'probe.py').write_bytes(PRODUCER)
        meta = dict(schema=1, work=str(work), output=str(run / 'observed.json'), workspace=str(workspace_path),
                    revision=commit, extensionSha256=sha(extension), producerSha256=sha(run / 'probe.py'))
        (run / 'meta.json').write_text(json.dumps(meta, indent=2) + '\n')
        print(json.dumps(dict(run=str(run), work=str(work))))
        return
    assert args.run
    run = args.run.resolve()
    meta = json.loads((run / 'meta.json').read_text())
    work = Path(meta['work'])
    assert run.parent == (ROOT / 'applications/evidence').resolve() and run.name.startswith('vscode-search-')
    assert work.parent == Path('/private/tmp') and work.name.startswith('rules-vsc-search-')
    assert sha(work / 'extension/extension.cjs') == meta['extensionSha256'] == sha(run / 'extension.cjs')
    executable = plistlib.loads((APP / 'Info.plist').read_bytes())['CFBundleExecutable']
    argv = [str(APP / 'MacOS' / executable), '--new-window', '--skip-welcome', '--skip-release-notes',
            '--use-inmemory-secretstorage', '--user-data-dir', str(work / 'user-data'),
            '--extensions-dir', str(work / 'extensions'), '--extensionDevelopmentPath=' + str(work / 'extension'),
            '--enable-proposed-api=rules-study.rules-private-search-fixture', meta['workspace']]
    env = dict(PATH='/usr/bin:/bin', HOME=str(Path.home()), TMPDIR=str(work / 'tmp'), LANG='en_US.UTF-8',
               SHELL='/bin/bash', RULES_VSCODE_SEARCH_META=str(run / 'meta.json'))
    started = time.monotonic()
    with (work / 'app.stdout').open('wb') as out, (work / 'app.stderr').open('wb') as err:
        child = subprocess.Popen(argv, env=env, stdout=out, stderr=err, start_new_session=True)
        (run / 'process.json').write_text(json.dumps(dict(pid=child.pid, argv=argv), indent=2) + '\n')
        print(json.dumps(dict(pid=child.pid, run=str(run))), flush=True)
        code = child.wait()
    result = dict(schema=1, exitCode=code, seconds=time.monotonic() - started, revision=commit,
                  launchProducerSha256=hashlib.sha256(PRODUCER).hexdigest(), extensionSha256=sha(run / 'extension.cjs'),
                  scope='Isolated multi-root fixture, ordinary OS HOME and in-memory secret storage. No personal profile, document, account, or workspace edits. OS-shared startup writes are not fully measured.')
    if Path(meta['output']).exists():
        result['observedSha256'] = sha(Path(meta['output']))
    (run / 'exit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    if code != 0:
        raise SystemExit(code if code > 0 else 128 - code)


if __name__ == '__main__':
    main()
