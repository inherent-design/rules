#!/usr/bin/env python3
"""Generated package/PATH/script execution fixtures; offline and private roots."""
from datetime import datetime,timezone
import hashlib,io,json,os,shlex,signal,subprocess,tarfile,tempfile,time
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()if p.is_file()else None
NAME='rules-exec-probe'
ARGS=['alpha β','literal; echo NOT_A_COMMAND','--flag=value']


def program(kind):
    return '#!/usr/bin/env node\n'+"const fs=require('fs');const row={kind:"+json.dumps(kind)+",args:process.argv.slice(2),cwd:process.cwd()};fs.appendFileSync(process.env.FIXTURE_EFFECT_FILE,JSON.stringify(row)+'\\n');console.log(JSON.stringify(row));\n"


def main():
    pins=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']
    for name in ['node','npm','pnpm','yarn']:assert sha(Path(pins[name]['path']))==pins[name]['sha256']
    assert not(Path(pins['node']['path']).parent/NAME).exists()
    run=ROOT/'applications/evidence'/('js-exec-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir()
    (run/'probe.py').write_bytes(PRODUCER)
    work=Path(tempfile.mkdtemp(prefix='rules-js-exec-',dir='/private/tmp'))
    for p in [work,*work.parents]:assert not any((p/n).exists()for n in ['.npmrc','.yarnrc','.yarnrc.yml','pnpm-workspace.yaml'])
    archive=work/'fixture-executable-1.0.0.tgz'
    with tarfile.open(archive,'w:gz')as tar:
        for name,data,mode in [('package.json',json.dumps(dict(name='fixture-executable',version='1.0.0',bin={NAME:'bin.cjs'})),0o644),('bin.cjs',program('dependency'),0o755)]:
            data=data.encode();entry=tarfile.TarInfo('package/'+name);entry.size=len(data);entry.mode=mode;entry.mtime=0;tar.addfile(entry,io.BytesIO(data))
    rows=[];owned=[]
    try:
        for app in ['npm','pnpm','yarn']:
            for profile in ['dependency-and-path','path-only','missing']:
                base=work/(app+'-'+profile);project=base/'project'
                for d in [project,project/'nested',base/'home',base/'cache',base/'config',base/'tmp',base/'path-bin',base/'global']:d.mkdir(parents=True)
                for n in ['user.npmrc','global.npmrc']:(base/'config'/n).write_text('')
                manifest=dict(name='fixture-exec-project',private=True,scripts={NAME:'node script.cjs'})
                if profile=='dependency-and-path':manifest['dependencies']={'fixture-executable':'file:'+str(archive)}
                (project/'package.json').write_text(json.dumps(manifest,indent=2)+'\n');(project/'script.cjs').write_text(program('root-script'))
                if profile!='missing':
                    p=base/'path-bin'/NAME;p.write_text(program('inherited-path'));p.chmod(0o755)
                (project/'pnpm-workspace.yaml').write_text('enableGlobalVirtualStore: false\nmanagePackageManagerVersions: false\n')
                (project/'.yarnrc.yml').write_text('nodeLinker: node-modules\nenableGlobalCache: false\nenableNetwork: false\nenableTelemetry: false\nenableScripts: false\n')
                effect=base/'effects.jsonl'
                env=dict(PATH=str(base/'path-bin')+':'+str(Path(pins['node']['path']).parent)+':/usr/bin:/bin',HOME=str(base/'home'),TMPDIR=str(base/'tmp'),
                    XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),NPM_CONFIG_USERCONFIG=str(base/'config/user.npmrc'),NPM_CONFIG_GLOBALCONFIG=str(base/'config/global.npmrc'),
                    NPM_CONFIG_CACHE=str(base/'cache/npm'),NPM_CONFIG_PREFIX=str(base/'global'),NPM_CONFIG_REGISTRY='http://127.0.0.1:9',NPM_CONFIG_UPDATE_NOTIFIER='false',
                    PNPM_HOME=str(base/'pnpm-home'),COREPACK_ENABLE_NETWORK='0',YARN_ENABLE_TELEMETRY='0',YARN_ENABLE_IMMUTABLE_INSTALLS='false',DO_NOT_TRACK='1',MISE_SKIP_RESHIM='1',
                    NO_COLOR='1',NO_UPDATE_NOTIFIER='1',LANG='en_US.UTF-8',FIXTURE_EFFECT_FILE=str(effect))
                prefix=[pins['node']['path'],pins['yarn']['path']]if app=='yarn'else[pins[app]['path']]
                lock={'npm':'package-lock.json','pnpm':'pnpm-lock.yaml','yarn':'yarn.lock'}[app]
                def image():
                    return dict(authored={n:sha(project/n)for n in ['package.json','script.cjs','pnpm-workspace.yaml','.yarnrc.yml']},lock=sha(project/lock),
                                effects=[json.loads(s)for s in effect.read_text().splitlines()]if effect.exists()else[])
                def command(label,args,cwd=None,expected=None):
                    stem=app+'-'+profile+'-'+label;before=image();start=time.monotonic();argv=prefix+args
                    with(run/(stem+'.stdout')).open('xb')as out,(run/(stem+'.stderr')).open('xb')as err:
                        p=subprocess.Popen(argv,cwd=cwd or project,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);owned.append(p)
                        (run/'owned-processes.json').write_text(json.dumps([dict(pid=c.pid,retired=c.poll()is not None)for c in owned],indent=2)+'\n')
                        timed=False
                        try:p.wait(timeout=60)
                        except subprocess.TimeoutExpired:timed=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
                    try:os.killpg(p.pid,0)
                    except ProcessLookupError:absent=True
                    else:absent=False
                    after=image();row=dict(app=app,profile=profile,operation=label,cwd=str(cwd or project),argv=argv,before=before,after=after,
                        streams={s:dict(file=stem+'.'+s,sha256=sha(run/(stem+'.'+s)))for s in ['stdout','stderr']},outcome=dict(exitCode=p.returncode,timedOut=timed,ownedGroupAbsent=absent),seconds=time.monotonic()-start)
                    rows.append(row);(run/'commands.json').write_text(json.dumps(rows,indent=2)+'\n');print(stem,p.returncode,flush=True)
                    assert not timed and absent and(expected is None or expected==p.returncode),(stem,p.returncode,expected)
                    assert before['authored']==after['authored']
                    if label!='install':assert before['lock']==after['lock']
                install=['install','--offline','--ignore-scripts','--no-audit','--no-fund']if app=='npm'else['install','--offline','--ignore-scripts','--store-dir',str(base/'store')]if app=='pnpm'else['install','--mode=skip-build']
                command('install',install,expected=0)
                execargs=['exec','--offline','--yes=false','--',NAME,*ARGS]if app=='npm'else['exec',NAME,*ARGS]
                command('exec',execargs)
                if profile=='dependency-and-path':
                    command('nested-exec',execargs,cwd=project/'nested')
                    command('run-script',['run',NAME,*(['--']if app=='npm'else[]),*ARGS],expected=0)
                if app=='npm':command('explicit-shell-call',['exec','--offline','--yes=false','--call',NAME+' '+shlex.join(ARGS)])
        (run/'receipt.json').write_text(json.dumps(dict(schema=1,producerSha256=sha(run/'probe.py'),tools={n:dict(path=pins[n]['path'],sha256=pins[n]['sha256'])for n in ['node','npm','pnpm','yarn']},
            work=str(work),archiveSha256=sha(archive),arguments=ARGS,commands=len(rows),allOwnedGroupsAbsent=all(r['outcome']['ownedGroupAbsent']for r in rows),
            workAllocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),
            limits=['Nine fresh offline projects;one generated package archive,owned PATH scripts and root scripts,no network service or global package installation.',
                    'All code generated;explicit execution may write only each private effect file. Authored and locked bytes preserved after installation. Cache/log/installation changes outside those observations are not claimed absent.',
                    'Yarn node-modules profile only. No temporary package download,registry,workspace scheduling,Windows,shell-injection vulnerability or universal executable search proof.']),indent=2)+'\n')
    finally:
        for p in owned:
            if p.poll()is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
        (run/'owned-processes.json').write_text(json.dumps([dict(pid=p.pid,retired=p.poll()is not None)for p in owned],indent=2)+'\n')
        print('capture',run,flush=True)


if __name__=='__main__':main()
