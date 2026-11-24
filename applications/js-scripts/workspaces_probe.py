#!/usr/bin/env python3
"""Owner-run workspace command fixtures: private local packages, no registry."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import tempfile
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()if p.is_file()else None


def main():
    pins=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']
    for name in ['node','npm','pnpm','yarn']:assert sha(Path(pins[name]['path']))==pins[name]['sha256'],name
    run=ROOT/'applications/evidence'/('js-workspaces-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir();(run/'probe.py').write_bytes(PRODUCER)
    work=Path(tempfile.mkdtemp(prefix='rules-js-workspaces-',dir='/private/tmp'))
    for p in [work,*work.parents]:
        assert not any((p/name).exists()for name in ['.npmrc','.yarnrc','.yarnrc.yml','pnpm-workspace.yaml']),p
    script="""const fs=require('node:fs');
const actor=process.argv[2];
const record=phase=>fs.appendFileSync(process.env.FIXTURE_LOG,JSON.stringify({actor,phase,cwd:process.cwd()})+'\\n');
record('start');
if(actor===process.env.FIXTURE_FAIL){record('failed');process.exit(7);}
record('succeeded');
"""
    cases={
        'npm':[
            ('root',['run','probe'],None),
            ('members',['run','probe','--workspaces','--if-present'],None),
            ('members-missing',['run','probe','--workspaces'],None),
            ('root-and-members',['run','probe','--workspaces','--include-workspace-root','--if-present'],None),
            ('selected-a',['run','probe','--workspace','fixture-a'],None),
            ('missing-selection',['run','probe','--workspace','not-a-workspace'],None),
            ('failed-b',['run','probe','--workspaces','--if-present'],'fixture-b')],
        'pnpm':[
            ('root',['run','probe'],None),
            ('members',['-r','--workspace-concurrency=1','run','probe'],None),
            ('root-and-members',['-r','--workspace-concurrency=1','--include-workspace-root','run','probe'],None),
            ('selected-a',['--filter','fixture-a','run','probe'],None),
            ('a-and-dependencies',['--filter','fixture-a...','--workspace-concurrency=1','run','probe'],None),
            ('b-and-dependents',['--filter','...fixture-b','--workspace-concurrency=1','run','probe'],None),
            ('missing-selection',['--filter','not-a-workspace','--fail-if-no-match','run','probe'],None),
            ('all-missing-script',['-r','--workspace-concurrency=1','run','absent'],None),
            ('failed-b',['-r','--workspace-concurrency=1','run','probe'],'fixture-b'),
            ('failed-b-no-bail',['-r','--workspace-concurrency=1','--no-bail','run','probe'],'fixture-b')],
        'yarn':[
            ('root',['run','probe'],None),
            ('members',['workspaces','foreach','--all','run','probe'],None),
            ('topological',['workspaces','foreach','--all','--topological','run','probe'],None),
            ('selected-a',['workspace','fixture-a','run','probe'],None),
            ('a-and-dependencies',['workspaces','foreach','--from','fixture-a','--recursive','--topological','run','probe'],None),
            ('missing-selection',['workspace','not-a-workspace','run','probe'],None),
            ('failed-b',['workspaces','foreach','--all','--topological','run','probe'],'fixture-b')]
    }
    rows=[];configs={}
    try:
        for manager in ['npm','pnpm','yarn']:
            base=work/manager;project=base/'project'
            for p in [project,base/'home',base/'cache',base/'config',base/'tmp']:p.mkdir(parents=True)
            for name in ['user.npmrc','global.npmrc']:(base/'config'/name).write_text('')
            root={'name':'fixture-root','version':'1.0.0','private':True,'workspaces':['packages/*'],'scripts':{'probe':'node probe.cjs fixture-root'}}
            if manager=='yarn':root['packageManager']='yarn@4.19.0'
            (project/'package.json').write_text(json.dumps(root,indent=2)+'\n');(project/'probe.cjs').write_text(script)
            for name in ['a','b','c','d']:
                folder=project/'packages'/name;folder.mkdir(parents=True)
                package={'name':'fixture-'+name,'version':'1.0.0','private':True}
                if name!='d':package['scripts']={'probe':'node ../../probe.cjs fixture-'+name}
                if name=='a':package['dependencies']={'fixture-b':'1.0.0'if manager=='npm'else'workspace:*'}
                (folder/'package.json').write_text(json.dumps(package,indent=2)+'\n')
            if manager=='pnpm':(project/'pnpm-workspace.yaml').write_text('packages:\n  - packages/*\nnodeLinker: isolated\nenableGlobalVirtualStore: false\n')
            if manager=='yarn':(project/'.yarnrc.yml').write_text('nodeLinker: node-modules\nenableGlobalCache: false\nenableNetwork: false\nenableTelemetry: false\nenableScripts: false\n')
            log=base/'effects.jsonl'
            env={'PATH':str(Path(pins['node']['path']).parent)+':/usr/bin:/bin','HOME':str(base/'home'),'XDG_CONFIG_HOME':str(base/'config'),'XDG_CACHE_HOME':str(base/'cache'),'TMPDIR':str(base/'tmp'),
                'NPM_CONFIG_USERCONFIG':str(base/'config/user.npmrc'),'NPM_CONFIG_GLOBALCONFIG':str(base/'config/global.npmrc'),'NPM_CONFIG_CACHE':str(base/'cache/npm'),'NPM_CONFIG_REGISTRY':'http://127.0.0.1:9',
                'LANG':'en_US.UTF-8','COREPACK_ENABLE_NETWORK':'0','YARN_ENABLE_TELEMETRY':'0','YARN_ENABLE_IMMUTABLE_INSTALLS':'false','DO_NOT_TRACK':'1','MISE_SKIP_RESHIM':'1','NO_COLOR':'1','NO_UPDATE_NOTIFIER':'1','FIXTURE_LOG':str(log)}
            if manager=='npm':prefix=[pins['npm']['path']];install=['install','--offline','--ignore-scripts','--no-audit','--no-fund']
            elif manager=='pnpm':prefix=[pins['pnpm']['path']];install=['install','--offline','--ignore-scripts','--store-dir',str(base/'store')]
            else:prefix=[pins['node']['path'],pins['yarn']['path']];install=['install']
            def state():
                paths=[project/'package.json',project/'probe.cjs',project/'package-lock.json',project/'pnpm-lock.yaml',project/'yarn.lock',project/'.yarnrc.yml',project/'pnpm-workspace.yaml']+sorted((project/'packages').glob('*/package.json'))
                return {'projectFiles':{str(p.relative_to(project)):sha(p)for p in paths},'effects': [json.loads(line)for line in log.read_text().splitlines()]if log.exists()else[]}
            def command(label,args,fail=None):
                before=state();selected_env=dict(env)
                if fail:selected_env['FIXTURE_FAIL']=fail
                start=time.monotonic();child=subprocess.Popen(prefix+args,cwd=project,env=selected_env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
                timed_out=False
                try:stdout,stderr=child.communicate(input=b'',timeout=60)
                except subprocess.TimeoutExpired:
                    timed_out=True
                    try:os.killpg(child.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    stdout,stderr=child.communicate()
                after=state();stem=manager+'-'+label
                (run/(stem+'.stdout')).write_bytes(stdout);(run/(stem+'.stderr')).write_bytes(stderr)
                row={'app':manager,'case':label,'argv':prefix+args,'fail':fail,'observed':{'before':before,'after':after,'effects':after['effects'][len(before['effects']):],'seconds':time.monotonic()-start,'stdoutSha256':hashlib.sha256(stdout).hexdigest(),'stderrSha256':hashlib.sha256(stderr).hexdigest()},'outcome':{'exitCode':child.returncode,'timedOut':timed_out}}
                rows.append(row);(run/'trace.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps({'app':manager,'case':label,'exitCode':child.returncode,'seconds':round(row['observed']['seconds'],3)}),flush=True)
                if timed_out:raise RuntimeError('Owned fixture group was killed after timeout;preserve records before retry.')
                return row
            installed=command('install',install)
            if installed['outcome']['exitCode']!=0:raise RuntimeError('Fixture install failed;do not qualify workspace execution cases.')
            configs[manager]={str(p.relative_to(project)):p.read_text()for p in [project/'package.json',project/'probe.cjs',*sorted((project/'packages').glob('*/package.json'))]}
            for label,args,fail in cases[manager]:command(label,args,fail)
        receipt={'schema':1,'producerSha256':hashlib.sha256(PRODUCER).hexdigest(),'tools':{name:pins[name]for name in ['node','npm','pnpm','yarn']},'platform':platform.platform(),'architecture':platform.machine(),'originalWork':str(work),'commands':len(rows),'scope':'Generated offline local workspace commands;selected project files and fixture script effects observed,not every cache/log/global effect. No user projects,registry publication or GUI.'}
        (run/'configuration.json').write_text(json.dumps(configs,indent=2)+'\n');(run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps({'run':str(run),'commands':len(rows),'work':str(work)}),flush=True)
    except BaseException as error:
        (run/'failure.json').write_text(json.dumps({'error':str(error),'originalWork':str(work),'commands':len(rows),'producerSha256':hashlib.sha256(PRODUCER).hexdigest()},indent=2)+'\n');raise


if __name__=='__main__':main()
