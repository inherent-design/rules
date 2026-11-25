#!/usr/bin/env python3
"""Prepare/launch one isolated task API fixture; live launch needs desktop custody."""
import argparse
from datetime import datetime,timezone
import hashlib,json,os,plistlib,shutil,subprocess,sys,tempfile,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];APP=Path('/Applications/Visual Studio Code.app/Contents');REV='8a14f0cc1b08d531eb83255ea3764ae22aa932b5';PRODUCER=Path(__file__).read_bytes();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','launch']);p.add_argument('run',type=Path,nargs='?');a=p.parse_args()
    assert json.loads((APP/'Resources/app/product.json').read_text())['commit']==REV
    assert sha(APP/'MacOS/Code')=='826ae77cbbd1521dc8d295e4b80d042caa7d55c64cc36079cf6574b7d762e0e3'
    if a.action=='prepare':
        run=ROOT/'applications/evidence'/('vscode-tasks-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir()
        work=Path(tempfile.mkdtemp(prefix='rules-vsc-tasks-',dir='/private/tmp'));project=work/'project'
        for name in ['project/.vscode','extension','user-data/User','extensions','tmp']:(work/name).mkdir(parents=True)
        worker=work/'task_worker.py';shutil.copyfile(HERE/'task_worker.py',worker)
        settings={'security.workspace.trust.enabled':False,'telemetry.telemetryLevel':'off','workbench.startupEditor':'none',
          'window.restoreWindows':'none','extensions.autoCheckUpdates':False,'extensions.autoUpdate':False,'update.mode':'none',
          'terminal.integrated.enablePersistentSessions':False,'task.autoDetect':'off'}
        write(work/'user-data/User/settings.json',settings)
        child_log=work/'child-events.jsonl';gate=work/'ready-gate';python=sys.executable
        tasks={'version':'2.0.0','tasks':[]}
        for name,mode in [('rules-background','background'),('rules-dependent','exit')]:
            t=dict(label=name,type='process',command=python,args=[str(worker),'--log',str(child_log),'--name',name,'--mode',mode,'--gate',str(gate)],
                   presentation=dict(reveal='never',panel='dedicated',showReuseMessage=False),problemMatcher=[])
            if mode=='background':
                t.update(isBackground=True,problemMatcher={'owner':'rules-study','pattern':{'regexp':'^(ERROR) (.*)$','file':1,'message':2},
                          'background':{'activeOnStart':True,'beginsPattern':'^BEGIN$','endsPattern':'^READY$'}})
            else:t.update(dependsOn='rules-background',dependsOrder='sequence')
            tasks['tasks'].append(t)
        write(project/'.vscode/tasks.json',tasks)
        package=dict(name='rules-task-fixture',publisher='rules-study',version='0.0.1',engines={'vscode':'^1.147.0'},main='./extension.cjs',
                     activationEvents=['onStartupFinished'],contributes={'taskDefinitions':[{'type':'rules-task-study','required':['name'],'properties':{'name':{'type':'string'}}}]})
        write(work/'extension/package.json',package);shutil.copyfile(HERE/'task-extension.cjs',work/'extension/extension.cjs')
        for src,dst in [(HERE/'task-extension.cjs',run/'extension.cjs'),(HERE/'task_worker.py',run/'task_worker.py'),(work/'extension/package.json',run/'package.json'),(project/'.vscode/tasks.json',run/'tasks.json')]:shutil.copyfile(src,dst)
        (run/'probe.py').write_bytes(PRODUCER)
        write(run/'meta.json',dict(schema=1,work=str(work),project=str(project),output=str(run/'observed.json'),childLog=str(child_log),gate=str(gate),
            worker=str(worker),python=python,revision=REV,extensionSha256=sha(run/'extension.cjs'),workerSha256=sha(worker),producerSha256=sha(run/'probe.py')))
        print(json.dumps(dict(run=str(run.relative_to(ROOT)),work=str(work))));return
    run=a.run.resolve();assert run.parent==ROOT/'applications/evidence';meta=json.loads((run/'meta.json').read_text());work=Path(meta['work'])
    assert (run/'probe.py').read_bytes()==PRODUCER and sha(work/'extension/extension.cjs')==meta['extensionSha256']
    with(run/'launch-started.json').open('x')as f:json.dump(dict(producerSha256=sha(run/'probe.py')),f)
    argv=[str(APP/'MacOS/Code'),'--new-window','--skip-welcome','--skip-release-notes','--use-inmemory-secretstorage',
        '--user-data-dir',str(work/'user-data'),'--extensions-dir',str(work/'extensions'),'--extensionDevelopmentPath='+str(work/'extension'),str(work/'project')]
    env=dict(PATH='/usr/bin:/bin',HOME=str(Path.home()),TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8',SHELL='/bin/bash',RULES_VSCODE_TASK_META=str(run/'meta.json'))
    start=time.monotonic()
    with(work/'app.stdout').open('wb')as out,(work/'app.stderr').open('wb')as err:
        child=subprocess.Popen(argv,env=env,stdout=out,stderr=err,start_new_session=True);write(run/'process.json',dict(pid=child.pid,argv=argv));print(json.dumps(dict(pid=child.pid,run=str(run))),flush=True);code=child.wait()
    write(run/'exit.json',dict(schema=1,exitCode=code,seconds=time.monotonic()-start,revision=REV,launchProducerSha256=hashlib.sha256(PRODUCER).hexdigest(),
        scope='Isolated workspace/profile,ordinary OS HOME,in-memory secret storage. OS-shared startup effects unmeasured. Native task children checked separately.',
        observedSha256=sha(Path(meta['output']))if Path(meta['output']).exists()else None))
    print(json.dumps(dict(exitCode=code,run=str(run))))
if __name__=='__main__':main()
