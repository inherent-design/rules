#!/usr/bin/env python3
"""Private VS Code configuration fixture; desktop access required for launch."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
APP=Path('/Applications/Visual Studio Code.app/Contents')
PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','launch']);parser.add_argument('run',nargs='?',type=Path);args=parser.parse_args()
    revision=json.loads((ROOT/'applications/sources/vscode-source.json').read_text())['commit']
    assert json.loads((APP/'Resources/app/product.json').read_text())['commit']==revision
    if args.action=='prepare':
        run=ROOT/'applications/evidence'/('vscode-configuration-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir()
        work=Path(tempfile.mkdtemp(prefix='rules-vsc-cfg-',dir='/private/tmp'))
        assert len(str(work/'user-data/1.14-main.sock').encode())<=103, 'Private profile exceeds the pinned macOS IPC socket path limit.'
        for p in ['a/.vscode','b/.vscode','extension','extensions','user-data/User','tmp']:(work/p).mkdir(parents=True)
        for folder in ['a','b']:(work/folder/'fixture.txt').write_text('Generated configuration fixture.\n')
        extension=HERE/'configuration-extension.cjs';(work/'extension/extension.cjs').write_bytes(extension.read_bytes());(run/'extension.cjs').write_bytes(extension.read_bytes());(run/'probe.py').write_bytes(PRODUCER)
        package={'name':'rules-private-config-fixture','publisher':'rules-study','version':'0.0.1','engines':{'vscode':'^1.147.0'},'main':'./extension.cjs','activationEvents':['onStartupFinished'],
            'contributes':{'configuration':{'title':'Rules fixture','properties':{
                'fixture.scope.value':{'type':'string','default':'base-default','scope':'language-overridable'},
                'fixture.scope.object':{'type':'object','default':{'defaultOnly':'d','nested':{'d':'d','x':'default'},'arr':['default']},'scope':'language-overridable'},
                'fixture.scope.nullable':{'type':['string','null'],'default':'base-nullable','scope':'language-overridable'}}},
            'configurationDefaults':{'[javascript]':{'fixture.scope.value':'language-default'}}}}
        (work/'extension/package.json').write_text(json.dumps(package,indent=2)+'\n');(run/'extension-package.json').write_text(json.dumps(package,indent=2)+'\n')
        settings={'workbench.startupEditor':'none','files.autoSave':'off','files.hotExit':'off','telemetry.telemetryLevel':'off','update.mode':'none','extensions.autoUpdate':False,'extensions.autoCheckUpdates':False,'security.workspace.trust.enabled':False,'git.enabled':False,'chat.disableAIFeatures':True,
            'fixture.scope.value':'user','fixture.scope.object':{'userOnly':'u','nested':{'u':'u','x':'user'},'arr':['user']},'fixture.scope.nullable':None}
        workspace={'folders':[{'path':'a'},{'path':'b'}],'settings':{'fixture.scope.value':'workspace','fixture.scope.object':{'workspaceOnly':'w','nested':{'w':'w'},'arr':['workspace']}}}
        folder_a={'fixture.scope.value':'folder-a','fixture.scope.object':{'folderOnly':'a','nested':{'a':'a','x':'folder-a'},'arr':['folder-a']}}
        folder_b={'fixture.scope.value':'folder-b'}
        files={'user':work/'user-data/User/settings.json','workspace':work/'Rules configuration study.code-workspace','folderA':work/'a/.vscode/settings.json','folderB':work/'b/.vscode/settings.json'}
        initial={'user':settings,'workspace':workspace,'folderA':folder_a,'folderB':folder_b}
        for key,p in files.items():p.write_text(json.dumps(initial[key],indent=2)+'\n')
        (run/'initial-settings.json').write_text(json.dumps(initial,indent=2)+'\n')
        meta={'schema':1,'work':str(work),'output':str(run/'observed.json'),'revision':revision,'settingsFiles':{key:str(p)for key,p in files.items()},'extensionSha256':sha(extension),'producerSha256':hashlib.sha256(PRODUCER).hexdigest()}
        (run/'meta.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps({'run':str(run),'workspace':str(files['workspace'])}));return
    assert args.run
    run=args.run.resolve();meta=json.loads((run/'meta.json').read_text());work=Path(meta['work'])
    assert run.parent==(ROOT/'applications/evidence').resolve() and run.name.startswith('vscode-configuration-') and work.parent==Path('/private/tmp') and work.name.startswith('rules-vsc-cfg-')
    assert sha(work/'extension/extension.cjs')==meta['extensionSha256']==sha(run/'extension.cjs')
    executable=plistlib.loads((APP/'Info.plist').read_bytes())['CFBundleExecutable']
    argv=[str(APP/'MacOS'/executable),'--new-window','--skip-welcome','--skip-release-notes','--use-inmemory-secretstorage','--user-data-dir',str(work/'user-data'),'--extensions-dir',str(work/'extensions'),'--extensionDevelopmentPath='+str(work/'extension'),str(Path(meta['settingsFiles']['workspace']))]
    env={'PATH':'/usr/bin:/bin','HOME':str(Path.home()),'TMPDIR':str(work/'tmp'),'LANG':'en_US.UTF-8','SHELL':'/bin/bash','RULES_VSCODE_CONFIG_META':str(run/'meta.json')}
    started=time.monotonic()
    with (work/'app.stdout').open('wb')as out,(work/'app.stderr').open('wb')as err:
        child=subprocess.Popen(argv,env=env,stdout=out,stderr=err,start_new_session=True)
        (run/'process.json').write_text(json.dumps({'pid':child.pid,'argv':argv},indent=2)+'\n');print(json.dumps({'pid':child.pid,'run':str(run)}),flush=True)
        code=child.wait()
    result={'schema':1,'exitCode':code,'seconds':time.monotonic()-started,'revision':revision,'extensionSha256':sha(run/'extension.cjs'),'launchProducerSha256':hashlib.sha256(PRODUCER).hexdigest(),
        'scope':'Native desktop configuration APIs on a disposable trusted multi-root workspace and isolated user-data/extensions; ordinary HOME and in-memory secret storage. No normal profile/settings/workspace writes. Workspace trust is disabled for this fixture,not qualified.'}
    if Path(meta['output']).exists():result['observedSha256']=sha(Path(meta['output']))
    (run/'exit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    if code!=0:raise SystemExit(code if code>0 else 128-code)


if __name__=='__main__':main()
