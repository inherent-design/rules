#!/usr/bin/env python3
"""Owner-run public registry configuration fixtures; no install or network request."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'applications/restic'))
from locks_probe import redact
PRODUCER = Path(__file__).read_bytes()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
VALUES = {k: 'https://' + k + '.invalid/' for k in ['global','user','project','environment','command','written','home-write','project-write']}


def main():
    assert sys.argv[1:] in [[], ['--yarn-standard-rc'], ['--read-locations']]
    standard = sys.argv[1:] == ['--yarn-standard-rc']
    locations = sys.argv[1:] == ['--read-locations']
    pins = json.loads((ROOT / 'applications/sources/local-pins.json').read_text())['tools']
    for name in ['node','npm','pnpm','yarn']:
        assert sha(Path(pins[name]['path'])) == pins[name]['sha256']
    run = ROOT / 'applications/evidence' / ('js-config-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'
    work.mkdir(parents=True)
    (run / 'probe.py').write_bytes(PRODUCER)
    (run / 'helper.py').write_bytes((ROOT / 'applications/restic/locks_probe.py').read_bytes())
    rows, owned = [], []
    for app in (['yarn'] if standard else ['npm','pnpm'] if locations else ['npm','pnpm','yarn']):
        base = work / app
        home, config, project = base / 'home', base / 'config', base / 'project'
        for p in [home, config, project, base/'cache', base/'tmp', base/'state']:
            p.mkdir(parents=True)
        (project/'package.json').write_text(json.dumps({'name':'config-fixture','private':True,'workspaces':['child']})+'\n')
        child = project/'child';child.mkdir();(child/'package.json').write_text('{"name":"config-child","private":true}\n')
        user, global_file = config/'user.npmrc', config/'global.npmrc'
        user.write_text('registry='+VALUES['user']+'\n')
        global_file.write_text('registry='+VALUES['global']+'\n')
        # No real ancestor rc is admitted. npm/pnpm use the explicit local file;
        # Yarn uses a fixture-only filename for both project and home lookup.
        (project/'.npmrc').write_text('registry='+VALUES['project']+'\n')
        env = dict(PATH=str(Path(pins['node']['path']).parent)+':/usr/bin:/bin', HOME=str(home),
            XDG_CONFIG_HOME=str(config),XDG_CACHE_HOME=str(base/'cache'),XDG_STATE_HOME=str(base/'state'),
            TMPDIR=str(base/'tmp'), NPM_CONFIG_USERCONFIG=str(user),NPM_CONFIG_GLOBALCONFIG=str(global_file),
            NPM_CONFIG_CACHE=str(base/'cache/npm'), NPM_CONFIG_UPDATE_NOTIFIER='false',
            COREPACK_ENABLE_NETWORK='0',YARN_ENABLE_TELEMETRY='0',YARN_ENABLE_NETWORK='0',
            YARN_ENABLE_COLORS='0',YARN_RC_FILENAME='.fixture-yarnrc.yml',
            DO_NOT_TRACK='1',MISE_SKIP_RESHIM='1',LANG='en_US.UTF-8')
        if app=='npm':
            prefix=[pins['npm']['path']];key='registry';envkey='NPM_CONFIG_REGISTRY'
        elif app=='pnpm':
            prefix=[pins['pnpm']['path']];key='registry';envkey='PNPM_CONFIG_REGISTRY'
            (project/'pnpm-workspace.yaml').write_text('packages:\n  - child\n')
        else:
            prefix=[pins['node']['path'],pins['yarn']['path']];key='npmRegistryServer';envkey='YARN_NPM_REGISTRY_SERVER'
            rc_name = '.yarnrc.yml' if standard else '.fixture-yarnrc.yml'
            if standard:
                assert all(not (p/rc_name).exists() for p in project.parents)
                env.pop('YARN_RC_FILENAME')
            (home/rc_name).write_text('npmRegistryServer: '+VALUES['user']+'\n')
            (project/rc_name).write_text('npmRegistryServer: '+VALUES['project']+'\n')
            (project/'yarn.lock').write_text('# Fixture project marker; no install.\n')

        def image():
            values={}
            for root in [home,config,project]:
                for p in sorted(root.rglob('*')):
                    if p.is_file():
                        data=p.read_bytes()
                        # All files in these roots originate in this public-data fixture.
                        values[str(p.relative_to(base))]=dict(sha256=sha(p),bytes=len(data),content=data.decode())
            return values

        def command(label,args,overlay=None,cwd=None):
            before=image();started=time.monotonic();actual_env=dict(env,**(overlay or {}))
            stem=app+'-'+label
            private=base/'private';private.mkdir(exist_ok=True)
            with (private/(stem+'.stdout')).open('wb') as out,(private/(stem+'.stderr')).open('wb') as err:
                process=subprocess.Popen(prefix+args,cwd=cwd or project,env=actual_env,stdin=subprocess.DEVNULL,
                    stdout=out,stderr=err,start_new_session=True)
                owned.append(process);timed_out=False
                try:process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    timed_out=True;os.killpg(process.pid,signal.SIGKILL);process.wait()
            streams={}
            for stream in ['stdout','stderr']:
                raw=private/(stem+'.'+stream);public=run/(stem+'.'+stream);public.write_bytes(redact(raw.read_bytes()))
                streams[stream]=dict(rawSha256=sha(raw),publicSha256=sha(public),rawPrivatePath=str(raw.relative_to(run)))
            row=dict(app=app,case=label,argv=prefix+args,cwd=str((cwd or project).relative_to(base)),
                environment=overlay or {},before=before,after=image(),seconds=time.monotonic()-started,
                streams=streams,outcome=dict(exitCode=process.returncode,timedOut=timed_out))
            rows.append(row)
            private_rows=work/'trace-original.json';private_rows.write_text(json.dumps(rows,indent=2)+'\n')
            (run/'trace.json').write_bytes(redact(private_rows.read_bytes()))
            print(app,label,process.returncode,flush=True)
            assert not timed_out,'Preserve timeout before retry.'
            return row

        try:
            if app=='pnpm':
                assert command('initialize-global',['config','set',key,VALUES['global'],'--global'])['outcome']['exitCode']==0
            if locations:
                command('read-effective',['config','get',key])
                command('read-global-mode',['config','get',key,'--global'])
                command('read-global-location',['config','get',key,'--location=global'])
                command('read-project-location',['config','get',key,'--location=project'])
                continue
            command('get-project',['config','get',key])
            command('get-environment',['config','get',key],{envkey:VALUES['environment']})
            if app!='yarn':
                command('get-command',['config','get',key,'--registry',VALUES['command']],{envkey:VALUES['environment']})
            command('set-default',['config','set',key,VALUES['written']])
            command('get-after-default',['config','get',key])
            homeflag=['--home'] if app=='yarn' else ['--location=user'] if app=='npm' else ['--global']
            command('set-lower-masked',['config','set',key,VALUES['home-write']]+homeflag,{envkey:VALUES['environment']})
            command('get-masked',['config','get',key],{envkey:VALUES['environment']})
            command('get-without-environment',['config','get',key])
            projectflag=[] if app=='yarn' else ['--location=project']
            command('set-project',['config','set',key,VALUES['project-write']]+projectflag)
            command('get-after-project',['config','get',key])
            if app=='yarn':
                command('explain',['config',key,'--json'])
                command('unset-project',['config','unset',key])
            else:
                command('explain',['config','list'])
                command('unset-project',['config','delete',key,'--location=project'])
            command('get-after-unset',['config','get',key])
            if app in ['npm','pnpm']:
                command('get-global',['config','get',key,'--global'])
            else:
                command('get-child',['config','get',key],cwd=child)
            assert all(p.poll() is not None for p in owned)
        finally:
            for p in owned:
                if p.poll() is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
    receipt=dict(schema=1,profile='yarn-standard-rc' if standard else 'location-reads' if locations else 'three-tool-custom-rc',
        toolPins={k:pins[k] for k in ['node','npm','pnpm','yarn']},platform=platform.platform(),
        architecture=platform.machine(),producerSha256=hashlib.sha256(PRODUCER).hexdigest(),helperSha256=sha(run/'helper.py'),
        commands=len(rows),allOwnedProcessesRetired=all(p.poll() is not None for p in owned),
        rawTraceSha256=sha(work/'trace-original.json'),publicTraceSha256=sha(run/'trace.json'),
        limits=['Public .invalid registry values only; no install, package resolution, authentication, real secrets, or request to a service.',
            'Private HOME/XDG/state/cache/temp and explicit npm user/global files; custom Yarn rc filename in the primary profile, or checked absent ancestor standard rc files in its follow-up.',
            'Before/after images cover owned home/config/project files, not an OS-wide write or network audit.'])
    (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('capture',run,flush=True)


if __name__=='__main__':main()
