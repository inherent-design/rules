"""Prepare/control a private VS Code API fixture. Launch/request require re:desktop access."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
APP=Path('/Applications/Visual Studio Code.app/Contents')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,x:p.write_text(json.dumps(x,indent=2)+'\n')
OPERATIONS=['workspace-fresh','workspace-late','caller-guarded','editor-parallel','editor-sequential','editor-parallel-empty','format-compute','format-compute-late-apply','interactive-format-late','rename-compute','rename-compute-late-apply','quit']

def binaries():
    paths=[APP/'MacOS/Code',APP/'Resources/app/product.json',APP/'Resources/app/package.json',APP/'Resources/app/out/main.js',APP/'Resources/app/out/vs/workbench/api/node/extensionHostProcess.js']
    return {str(p):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in paths}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','launch','request']);parser.add_argument('run',nargs='?',type=Path);parser.add_argument('operation',nargs='?');args=parser.parse_args()
    if args.action=='prepare':
        preflight=json.loads((ROOT/'.build/vscode-language-preread/installed-preflight.json').read_text());package=json.loads((APP/'Resources/app/package.json').read_text());product=json.loads((APP/'Resources/app/product.json').read_text())
        assert package['version']==preflight['version']=='1.148.0' and product['commit']==preflight['commit']=='661626d0e72f97806550790a98fb87116c9db825'
        assert sha(APP/'MacOS/Code')==preflight['binarySha256']
        work=Path(tempfile.mkdtemp(prefix='rules-vlang-',dir='/private/tmp'));assert len(str(work/'user-data/1.148-main.sock').encode())<=103
        for p in ['project','extension','extensions','home','tmp','user-data/User']:(work/p).mkdir(parents=True)
        (work/'project/document.rules-language').write_text('alpha beta\n')
        run=ROOT/'applications/evidence'/('vscode-language-edit-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir()
        extension=HERE/'language-edit-extension.cjs';(work/'extension/extension.cjs').write_bytes(extension.read_bytes());(run/'extension.cjs').write_bytes(extension.read_bytes());(run/'probe.py').write_bytes(Path(__file__).read_bytes())
        manifest=dict(name='rules-private-language-edit-study',publisher='rules-study',version='0.0.1',engines=dict(vscode='^1.148.0'),main='./extension.cjs',activationEvents=['onStartupFinished'],contributes=dict(languages=[dict(id='rules-language-study',extensions=['.rules-language'],aliases=['Rules language fixture'])]))
        settings={'workbench.startupEditor':'none','files.autoSave':'off','files.hotExit':'off','editor.formatOnSave':False,'editor.formatOnType':False,'editor.formatOnPaste':False,'telemetry.telemetryLevel':'off','update.mode':'none','extensions.autoUpdate':False,'extensions.autoCheckUpdates':False,'security.workspace.trust.enabled':False,'git.enabled':False,'chat.disableAIFeatures':True}
        write(work/'extension/package.json',manifest);write(run/'extension-package.json',manifest);write(work/'user-data/User/settings.json',settings);write(run/'settings.json',settings)
        meta=dict(schema=1,run=str(run),work=str(work),output=str(run/'observed.json'),version=package['version'],commit=product['commit'],binaries=binaries(),producerSha256=sha(run/'probe.py'),extensionSha256=sha(extension),platform=platform.platform(),operations=OPERATIONS,
          scope='Generated local file and custom formatting/rename providers. Public extension API/native editor command observations only;no built-in language-engine/widget/accessibility or browser qualification. Private profiles reduce interference;shared host stores/incidental writes are not fully measured. Historical1.147 evidence remains unchanged.')
        write(run/'meta.json',meta);print(json.dumps(dict(run=str(run),work=str(work),version=meta['version'])));return
    assert args.run;run=args.run.resolve();assert run.parent==ROOT/'applications/evidence' and run.name.startswith('vscode-language-edit-')
    meta=json.loads((run/'meta.json').read_text());work=Path(meta['work']);assert work.parent==Path('/private/tmp') and work.name.startswith('rules-vlang-')
    if args.action=='launch':
        assert not (run/'process.json').exists(),'Earlier handle exists;reconcile it rather than restarting.'
        assert binaries()==meta['binaries'],'Installed Code changed;stop before launch.'
        command=[str(APP/'MacOS/Code'),'--new-window','--skip-welcome','--skip-release-notes','--use-inmemory-secretstorage','--user-data-dir',str(work/'user-data'),'--extensions-dir',str(work/'extensions'),'--extensionDevelopmentPath='+str(work/'extension'),str(work/'project')]
        env=dict(PATH='/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8',SHELL='/bin/bash',RULES_LANGUAGE_FIXTURE=str(run/'meta.json'))
        with (work/'app.stdout').open('xb') as out,(work/'app.stderr').open('xb') as err:
            child=subprocess.Popen(command,cwd=work,env=env,stdout=out,stderr=err,start_new_session=True);write(run/'process.json',dict(pid=child.pid,argv=command,environmentKeys=sorted(env),startedAt=datetime.now(timezone.utc).isoformat()));print(json.dumps(dict(pid=child.pid,run=str(run))),flush=True);code=child.wait()
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        write(run/'exit.json',dict(exitCode=code,groupAbsent=absent,privateStreams={n:dict(path=str(work/('app.'+n)),sha256=sha(work/('app.'+n))) for n in ['stdout','stderr']}));print(json.dumps(dict(exitCode=code,groupAbsent=absent)));return
    assert args.operation in OPERATIONS
    current=json.loads((run/'observed.json').read_text());assert current['status']=='ready' or args.operation=='quit'
    sequence=current['handled']+1;temporary=work/'control.tmp';write(temporary,dict(sequence=sequence,action=args.operation));temporary.replace(work/'control.json')
    started=time.monotonic();deadline=started+20
    while time.monotonic()<deadline:
        if args.operation=='quit' and (run/'exit.json').exists():print((run/'exit.json').read_text());return
        current=json.loads((run/'observed.json').read_text())
        if current['handled']==sequence:
            write(run/('request-'+str(sequence)+'.json'),dict(sequence=sequence,action=args.operation,status=current['status'],seconds=time.monotonic()-started,observedSha256=sha(run/'observed.json')))
            print(json.dumps(dict(action=args.operation,status=current['status'],rows=len(current['rows']),activeProviders=current['activeProviders'])));return
        if (run/'exit.json').exists():raise RuntimeError('Native handle is terminal;preserve output before deciding next action.')
        time.sleep(.08)
    raise RuntimeError('Observation timed out;inspect the same handle/current output. Do not restart from timeout alone.')

if __name__=='__main__':main()
