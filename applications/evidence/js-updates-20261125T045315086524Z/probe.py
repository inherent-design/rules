#!/usr/bin/env python3
"""Owner-run update-selection study: generated packages and loopback registry."""
from datetime import datetime,timezone
import argparse,base64,gzip,hashlib,http.server,io,json,os,platform,shutil,signal,stat,subprocess,tarfile,tempfile,threading,time,urllib.parse
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda b:hashlib.sha256(b).hexdigest()
NAMES=['rules-update-range','rules-update-pin']
VERSIONS=['1.0.0','1.1.0','2.0.0','2.1.0-beta.1']


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manager',choices=['npm','pnpm','yarn','all'],default='all');options=parser.parse_args()
    pins=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']
    for k in['node','npm','pnpm','yarn']:assert sha(Path(pins[k]['path']))==pins[k]['sha256'],k
    run=ROOT/'applications/evidence'/('js-updates-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir()
    (run/'probe.py').write_bytes(PRODUCER)
    work=Path(tempfile.mkdtemp(prefix='rules-js-updates-',dir='/private/tmp'))
    for p in[work,*work.parents]:
        assert not any((p/f).exists()for f in['package.json','.npmrc','.yarnrc','.yarnrc.yml','pnpm-workspace.yaml']),p
    (run/'archives').mkdir();(run/'responses').mkdir();(run/'states').mkdir()
    archives={};archive_info={};events=[];commands=[];owned=[];transitions=[]
    control=dict(stage='initial',case='setup',missing=None);mutex=threading.Lock()
    for name in NAMES:
        for version in VERSIONS:
            package=dict(name=name,version=version,main='index.js',license='UNLICENSED')
            files={'package.json':(json.dumps(package,separators=(',',':'))+'\n').encode(),'index.js':('module.exports='+json.dumps(version)+';\n').encode()}
            buf=io.BytesIO()
            with tarfile.open(fileobj=buf,mode='w',format=tarfile.USTAR_FORMAT)as archive:
                for path,data in files.items():
                    entry=tarfile.TarInfo('package/'+path);entry.mode=0o644;entry.mtime=0;entry.size=len(data);archive.addfile(entry,io.BytesIO(data))
            payload=gzip.compress(buf.getvalue(),mtime=0);filename=name+'-'+version+'.tgz';(run/'archives'/filename).write_bytes(payload)
            archives[name,version]=payload;archive_info[filename]=dict(name=name,version=version,bytes=len(payload),sha256=digest(payload),
                integrity='sha512-'+base64.b64encode(hashlib.sha512(payload).digest()).decode(),files={k:dict(bytes=len(v),sha256=digest(v))for k,v in files.items()})
    class Registry(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            path=urllib.parse.unquote(urllib.parse.urlsplit(self.path).path);pieces=path.lstrip('/').split('/')
            with mutex:
                current=dict(control);name=pieces[0];status=200;kind='application/json'
                if name not in NAMES or name==current['missing']:
                    status=404;body=b'{"error":"generated_fixture_not_found"}\n'
                elif len(pieces)==3 and pieces[1]=='-':
                    filename=pieces[2];info=archive_info.get(filename)
                    if info is None or info['name']!=name:status=404;body=b'not found'
                    else:body=archives[name,info['version']];kind='application/octet-stream'
                elif len(pieces)==1:
                    versions=VERSIONS[:1]if current['stage']=='initial'else VERSIONS
                    tag='1.0.0'if current['stage']=='initial'else'1.1.0'if current['stage']=='retagged'else'2.0.0'
                    package_versions={}
                    for version in versions:
                        filename=name+'-'+version+'.tgz';info=archive_info[filename]
                        package_versions[version]=dict(name=name,version=version,main='index.js',license='UNLICENSED',
                            dist=dict(tarball=origin+'/'+name+'/-/'+filename,integrity=info['integrity'],shasum=hashlib.sha1(archives[name,version]).hexdigest()))
                    metadata=dict(name=name,_id=name,**{'dist-tags':dict(latest=tag,**({'next':'2.1.0-beta.1'}if current['stage']!='initial'else{}))},
                        versions=package_versions,time=dict(created='2024-01-01T00:00:00.000Z',modified='2024-01-05T00:00:00.000Z',
                            **{v:f'2024-01-0{i+1}T00:00:00.000Z'for i,v in enumerate(versions)}))
                    body=(json.dumps(metadata,separators=(',',':'))+'\n').encode()
                else:status=404;body=b'not found'
                body_sha=digest(body);extension='.tgz'if kind=='application/octet-stream'else'.json'
                target=run/'responses'/(body_sha+extension)
                if not target.exists():target.write_bytes(body)
                events.append(dict(case=current['case'],stage=current['stage'],missing=current['missing'],method='GET',path=self.path,
                    status=status,bodySha256=body_sha,response=str(target.relative_to(run)),authorizationPresent=bool(self.headers.get('Authorization'))))
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Registry);server.daemon_threads=False
    origin='http://127.0.0.1:'+str(server.server_address[1]);thread=threading.Thread(target=server.serve_forever,name='rules-update-fixture');thread.start()
    try:
        for manager in(['npm','pnpm','yarn']if options.manager=='all'else[options.manager]):
            with mutex:control.update(stage='initial',case=manager+'-setup',missing=None)
            base=work/manager;project=base/'project'
            for d in[project,base/'home',base/'cache',base/'config',base/'state',base/'tmp',base/'local']:d.mkdir(parents=True)
            for name in['user.npmrc','global.npmrc']:(base/'config'/name).write_text('')
            (base/'local/package.json').write_text(json.dumps(dict(name='rules-update-local',version='1.0.0',main='index.js'))+'\n')
            (base/'local/index.js').write_text('module.exports="local-unchanged";\n')
            (project/'package.json').write_text(json.dumps(dict(name='rules-update-study',private=True,version='1.0.0',
                dependencies={NAMES[0]:'^1.0.0',NAMES[1]:'1.0.0','rules-update-local':'file:../local'}),indent=2)+'\n')
            (project/'.npmrc').write_text('registry='+origin+'\nignore-scripts=true\naudit=false\nfund=false\nfetch-retries=0\nupdate-notifier=false\n')
            env=dict(PATH=str(Path(pins['node']['path']).parent)+':/usr/bin:/bin',HOME=str(base/'home'),TMPDIR=str(base/'tmp'),
                XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_STATE_HOME=str(base/'state'),
                NPM_CONFIG_USERCONFIG=str(base/'config/user.npmrc'),NPM_CONFIG_GLOBALCONFIG=str(base/'config/global.npmrc'),
                NPM_CONFIG_CACHE=str(base/'cache/npm'),NPM_CONFIG_REGISTRY=origin,NPM_CONFIG_FETCH_RETRIES='0',NPM_CONFIG_IGNORE_SCRIPTS='true',
                NPM_CONFIG_AUDIT='false',NPM_CONFIG_FUND='false',NPM_CONFIG_UPDATE_NOTIFIER='false',PNPM_CONFIG_STATE_DIR=str(base/'state'),
                COREPACK_ENABLE_NETWORK='0',YARN_ENABLE_TELEMETRY='0',YARN_ENABLE_IMMUTABLE_INSTALLS='false',DO_NOT_TRACK='1',MISE_SKIP_RESHIM='1',LANG='en_US.UTF-8')
            if manager=='yarn':
                (project/'yarn.lock').write_text('')
                (project/'.yarnrc.yml').write_text('nodeLinker: node-modules\nenableGlobalCache: false\nenableTelemetry: false\nenableScripts: false\n'
                    'httpRetry: 0\n'+f'npmRegistryServer: {origin}\nunsafeHttpWhitelist: [127.0.0.1]\n')
                prefix=[pins['node']['path'],pins['yarn']['path']];install=['install'];within=['up','-R',*NAMES];latest=['up',*NAMES]
            elif manager=='pnpm':
                (project/'pnpm-workspace.yaml').write_text('packages: []\nstoreDir: '+str(base/'cache/store')+'\ncacheDir: '+str(base/'cache/metadata')+'\n')
                prefix=[pins['pnpm']['path']];install=['install','--ignore-scripts'];within=['update','--ignore-scripts'];latest=['update','--latest','--ignore-scripts','rules-update-*']
            else:
                prefix=[pins['npm']['path']];install=['install','--ignore-scripts'];within=['update','--ignore-scripts']
                latest=['install',NAMES[0]+'@latest',NAMES[1]+'@latest','--ignore-scripts']
            def image():
                authored={}
                for name in['package.json','package-lock.json','pnpm-lock.yaml','pnpm-workspace.yaml','yarn.lock','.npmrc','.yarnrc.yml']:
                    p=project/name
                    if p.exists():
                        value=p.read_bytes();key=digest(value);target=run/'states'/(key+'.txt')
                        if not target.exists():target.write_bytes(value)
                        authored[name]=dict(sha256=key,bytes=len(value),captured=str(target.relative_to(run)))
                files={}
                for p in sorted((project/'node_modules').rglob('*')):
                    s=p.lstat();name=str(p.relative_to(project/'node_modules'))
                    if stat.S_ISREG(s.st_mode):files[name]=dict(sha256=sha(p),bytes=s.st_size)
                    elif stat.S_ISLNK(s.st_mode):files[name]=dict(link=os.readlink(p))
                return dict(authored=authored,installed=files)
            def command(case,args,observer=False,expected=0):
                label=manager+'-'+case;before=image();started=time.monotonic()
                with mutex:control['case']=label;event_start=len(events)
                argv=([pins['node']['path']]if observer else prefix)+args
                with(run/(label+'.stdout')).open('xb')as out,(run/(label+'.stderr')).open('xb')as err:
                    child=subprocess.Popen(argv,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);owned.append(child)
                    (run/'owned-processes.json').write_text(json.dumps([dict(pid=p.pid,retired=p.poll()is not None)for p in owned],indent=2)+'\n')
                    timed=False
                    try:child.wait(timeout=60)
                    except subprocess.TimeoutExpired:timed=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
                try:os.killpg(child.pid,0)
                except ProcessLookupError:absent=True
                else:absent=False
                with mutex:requests=json.loads(json.dumps(events[event_start:]));current=dict(control)
                row=dict(app=manager,case=case,kind='fresh-node-observer'if observer else'native-command',argv=argv,
                    registry=current,before=before,after=image(),requests=requests,seconds=time.monotonic()-started,
                    outcome=dict(exitCode=child.returncode,timedOut=timed,ownedGroupAbsent=absent),
                    streams={s:dict(file=label+'.'+s,sha256=sha(run/(label+'.'+s)))for s in['stdout','stderr']})
                commands.append(row);(run/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');(run/'requests.json').write_text(json.dumps(events,indent=2)+'\n')
                print(label,child.returncode,'requests',len(requests),flush=True)
                assert absent and not timed,label
                if expected is not None:assert child.returncode==expected,(label,child.returncode)
                return row
            runtime='const fs=require("fs");const out={};for(const name of '+json.dumps(NAMES+['rules-update-local'])+') {try{const file=require.resolve(name);out[name]={value:require(name),manifest:require(name+"/package.json"),source:fs.readFileSync(file,"utf8")};}catch(e){out[name]={error:e.code};}}console.log(JSON.stringify(out));'
            def observe(label):return command(label,['-e',runtime],observer=True)
            def stage(name,missing=None):
                with mutex:
                    before=dict(control);control.update(stage=name,missing=missing)
                    transitions.append(dict(app=manager,before=before,after=dict(control),projectState=image()))
            def outdated(label,target=False):
                if manager!='yarn':return command(label,['outdated',*(NAMES[1:2]if target else[]),'--json'],expected=None)
            command('initial-install',install);observe('initial-runtime');stage('advanced')
            outdated('catalog-advanced');stage('advanced',missing=NAMES[1]);outdated('catalog-pin-unavailable',target=True)
            stage('advanced');outdated('catalog-pin-restored',target=True)
            command('within-range',within);observe('within-runtime');outdated('catalog-after-within')
            command('rewrite-latest',latest);observe('latest-runtime');outdated('catalog-after-latest')
            stage('retagged');outdated('catalog-retagged');command('rewrite-retagged',latest);observe('retagged-runtime')
        (run/'receipt.json').write_text(json.dumps(dict(schema=1,producerSha256=sha(run/'probe.py'),tools={k:pins[k]for k in['node','npm','pnpm','yarn']},
            platform=platform.platform(),architecture=platform.machine(),origin=origin,originalWork=str(work),commands=len(commands),
            archives=archive_info,registryTransitions=transitions,
            scope='Two registry roots (caret versus exact),one local root,generated two-file archives,private stores/configs and loopback HTTP. No registry authentication,remote reliability,peer/transitive/workspace solver or general semver proof.'),indent=2)+'\n')
    finally:
        for child in owned:
            if child.poll()is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
        server.shutdown();server.server_close();thread.join(timeout=5);assert not thread.is_alive()
        (run/'requests.json').write_text(json.dumps(events,indent=2)+'\n')
        (run/'closed.json').write_text(json.dumps(dict(serverClosed=server.socket.fileno()==-1,threadJoined=True,allOwnedProcessesRetired=all(p.poll()is not None for p in owned)))+'\n')
        (run/'owned-processes.json').write_text(json.dumps([dict(pid=p.pid,retired=p.poll()is not None)for p in owned],indent=2)+'\n')
        shutil.move(str(work),str(run/'work'));print('capture',run,flush=True)


if __name__=='__main__':main()
