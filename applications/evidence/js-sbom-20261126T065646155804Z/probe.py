"""Owner-run offline SBOM basis study over three generated archives."""
from datetime import datetime,timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import signal
import stat
import subprocess
import tarfile
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
sha=lambda b:hashlib.sha256(b).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,indent=2)+'\n')
PROD,DEV,OPTIONAL='rules-sbom-prod','rules-sbom-dev','rules-sbom-optional'


def main():
    pins=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']
    for name in ['node','npm','pnpm']:assert sha(Path(pins[name]['path']).read_bytes())==pins[name]['sha256']
    run=ROOT/'applications/evidence'/('js-sbom-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir();(run/'probe.py').write_bytes(Path(__file__).read_bytes())
    for name in ['states','archives']:(run/name).mkdir()
    work=Path(tempfile.mkdtemp(prefix='rules-js-sbom-',dir='/private/tmp'))
    for ancestor in [work,*work.parents]:
        assert not any((ancestor/n).exists()for n in ['package.json','.npmrc','pnpm-workspace.yaml'])
    commands,mutations,archives=[],[],[]
    for name in [PROD,DEV,OPTIONAL]:
        package=dict(name=name,version='1.0.0',main='index.js',license='MIT')
        bodies={'package.json':(json.dumps(package)+'\n').encode(),'index.js':('module.exports='+json.dumps(dict(name=name,value='original'))+';\n').encode()}
        buffer=io.BytesIO()
        with tarfile.open(fileobj=buffer,mode='w',format=tarfile.USTAR_FORMAT)as archive:
            for path,body in bodies.items():
                info=tarfile.TarInfo('package/'+path);info.mode=0o644;info.mtime=0;info.size=len(body);archive.addfile(info,io.BytesIO(body))
        raw=gzip.compress(buffer.getvalue(),mtime=0);filename=name+'-1.0.0.tgz';(run/'archives'/filename).write_bytes(raw)
        archives.append(dict(name=name,version='1.0.0',filename=filename,bytes=len(raw),sha256=sha(raw),sha512=hashlib.sha512(raw).hexdigest(),files={p:dict(bytes=len(b),sha256=sha(b))for p,b in bodies.items()}))
    write(run/'archives.json',archives)

    def image(project):
        result={}
        for directory,dirs,names in os.walk(project,followlinks=False):
            for name in sorted(dirs+names):
                p=Path(directory)/name;s=p.lstat();key=p.relative_to(project).as_posix()
                if stat.S_ISLNK(s.st_mode):result[key]=dict(kind='link',target=os.readlink(p))
                elif stat.S_ISDIR(s.st_mode):result[key]=dict(kind='directory',mode=stat.S_IMODE(s.st_mode))
                else:
                    assert stat.S_ISREG(s.st_mode);raw=p.read_bytes();digest=sha(raw);capture='states/'+digest+'.bin'
                    if not(run/capture).exists():(run/capture).write_bytes(raw)
                    result[key]=dict(kind='file',bytes=len(raw),sha256=digest,mode=stat.S_IMODE(s.st_mode),captured=capture)
        return result
    def alive(pgid):
        try:os.killpg(pgid,0);return True
        except ProcessLookupError:return False
    def child(manager,label,args,project,env,query=False):
        before=image(project);argv=[pins['node']['path'],*args]if query else[pins[manager]['path'],*args]
        started=time.monotonic();process=subprocess.Popen(argv,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timeout=False
        try:stdout,stderr=process.communicate(timeout=90)
        except subprocess.TimeoutExpired:
            timeout=True;os.killpg(process.pid,signal.SIGKILL);stdout,stderr=process.communicate()
        identifier=manager+'-'+label
        for kind,body in [('stdout',stdout),('stderr',stderr)]:(run/(identifier+'.'+kind)).write_bytes(body)
        row=dict(id=identifier,manager=manager,argv=argv,query=query,pid=process.pid,exitCode=process.returncode,timedOut=timeout,seconds=time.monotonic()-started,groupAbsent=not alive(process.pid),before=before,after=image(project),stdoutSha256=sha(stdout),stderrSha256=sha(stderr))
        commands.append(row);write(run/'commands.json',commands)
        assert row['groupAbsent']and not timeout
        if label=='install':assert process.returncode==0,stderr.decode(errors='replace')
        return row
    def mutate(manager,label,project,action):
        before=image(project);action();mutations.append(dict(manager=manager,id=manager+'-'+label,action=label,before=before,after=image(project)));write(run/'mutations.json',mutations)
    query="const fs=require('fs'),r=require('module').createRequire(process.cwd()+'/package.json'),v={};for(const n of "+json.dumps([PROD,DEV,OPTIONAL])+ "){try{const file=r.resolve(n);v[n]={file,value:r(n),sha256:require('crypto').createHash('sha256').update(fs.readFileSync(file)).digest('hex')}}catch(e){v[n]={error:e.code}}};console.log(JSON.stringify(v))"
    error=None
    try:
        for manager in ['npm','pnpm']:
            own=work/manager;project=own/'project';project.mkdir(parents=True)
            for n in ['cache','config','state','store','global','tmp']:(own/n).mkdir()
            (own/'config/user.npmrc').write_text('');(own/'config/global.npmrc').write_text('')
            env={k:v for k,v in os.environ.items()if not k.lower().startswith(('npm_','pnpm_','yarn_','corepack_'))}
            env.update(dict(PATH=str(Path(pins['node']['path']).parent)+':'+env['PATH'],XDG_CACHE_HOME=str(own/'cache'),XDG_CONFIG_HOME=str(own/'config'),XDG_STATE_HOME=str(own/'state'),TMPDIR=str(own/'tmp'),npm_config_userconfig=str(own/'config/user.npmrc'),npm_config_globalconfig=str(own/'config/global.npmrc'),npm_config_cache=str(own/'cache'),CI='1',NO_UPDATE_NOTIFIER='1'))
            (project/'.npmrc').write_text('registry=http://127.0.0.1:9/\naudit=false\nfund=false\nignore-scripts=true\nupdate-notifier=false\n')
            (project/'archives').mkdir()
            for item in archives:(project/'archives'/item['filename']).write_bytes((run/'archives'/item['filename']).read_bytes())
            manifest=dict(name='rules-sbom-'+manager,version='1.0.0',private=True,license='MIT',dependencies={PROD:'file:archives/'+PROD+'-1.0.0.tgz'},devDependencies={DEV:'file:archives/'+DEV+'-1.0.0.tgz'},optionalDependencies={OPTIONAL:'file:archives/'+OPTIONAL+'-1.0.0.tgz'})
            write(project/'package.json',manifest)
            if manager=='pnpm':
                (project/'pnpm-workspace.yaml').write_text('packages: []\nstoreDir: '+json.dumps(str(own/'store'))+'\ncacheDir: '+json.dumps(str(own/'cache'))+'\nstateDir: '+json.dumps(str(own/'state'))+'\npackageImportMethod: copy\n')
            child(manager,'install',['install','--offline','--ignore-scripts'],project,env)
            child(manager,'baseline-runtime',['-e',query],project,env,True)
            def sbom(label,format='cyclonedx',extra=None):return child(manager,label,['sbom','--sbom-format='+format,*(extra or[])],project,env)
            sbom('baseline-cyclonedx');sbom('baseline-spdx','spdx')
            sbom('runtime-filter',extra=['--omit=dev','--omit=optional']if manager=='npm'else['--prod','--no-optional'])
            target=(project/'node_modules'/PROD/'index.js').resolve();assert target.is_relative_to(own)
            def tamper():
                sibling=target.with_name('.rules-replacement');sibling.write_text('module.exports='+json.dumps(dict(name=PROD,value='changed'))+';\n');os.replace(sibling,target)
            mutate(manager,'replace-prod-code',project,tamper)
            child(manager,'changed-runtime',['-e',query],project,env,True);sbom('changed-cyclonedx')
            root_entry=project/'node_modules'/PROD;held=own/'held-prod'
            mutate(manager,'hold-prod-entry',project,lambda:os.rename(root_entry,held))
            child(manager,'missing-runtime',['-e',query],project,env,True)
            sbom('missing-cyclonedx');sbom('missing-lock-only',extra=['--package-lock-only']if manager=='npm'else['--lockfile-only'])
            mutate(manager,'restore-prod-entry',project,lambda:os.rename(held,root_entry))
            lock=project/('package-lock.json'if manager=='npm'else'pnpm-lock.yaml')
            mutate(manager,'hold-lock',project,lambda:os.rename(lock,own/'held-lock'))
            sbom('no-lock-cyclonedx');sbom('no-lock-explicit',extra=['--package-lock-only']if manager=='npm'else['--lockfile-only'])
            child(manager,'missing-format',['sbom'],project,env)
    except BaseException as exc:
        error=repr(exc);write(run/'failure.json',dict(error=error));raise
    finally:
        write(run/'commands.json',commands);write(run/'mutations.json',mutations)
        write(run/'receipt.json',dict(schema=1,complete=error is None,error=error,work=str(work),platform=platform.platform(),producerSha256=sha((run/'probe.py').read_bytes()),tools={n:pins[n]for n in ['node','npm','pnpm']},commands=len(commands),allRecordedGroupsAbsent=all(not alive(c['pid'])for c in commands),networkScope='Offline installs from own local archives;registry configured to unused loopback port9. No network interception or universal-network-effects proof.',effects='Project images include paths/modes/links/bytes,but not mtime. Separate private caches/configs/quarantine retained. No HOME override or personal project/global install.',allocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0])))
        print(run)


if __name__=='__main__':main()
