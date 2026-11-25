#!/usr/bin/env python3
"""Owner-run deduplication study with generated packages and a loopback registry."""
from datetime import datetime,timezone
import base64,gzip,hashlib,http.server,io,json,os,signal,stat,subprocess,tarfile,tempfile,threading,time,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
LEAF='rules-dedupe-leaf';FLEX='rules-dedupe-flex';FIXED='rules-dedupe-fixed';B='rules-dedupe-later'
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def main():
 pins=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']
 for key in ['node','npm','pnpm','yarn']:assert sha(Path(pins[key]['path']).read_bytes())==pins[key]['sha256']
 run=ROOT/'applications/evidence'/('js-dedupe-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir();work=Path(tempfile.mkdtemp(prefix='rules-js-dedupe-',dir='/private/tmp'))
 for p in [work,*work.parents]:assert not any((p/n).exists()for n in ['package.json','.npmrc','.yarnrc.yml','.rules-dedupe.yml','pnpm-workspace.yaml']),p
 assert not(Path.home()/'.rules-dedupe.yml').exists(),'Private study config filename already exists'
 for name in ['archives','responses','states']:(run/name).mkdir()
 (run/'probe.py').write_bytes(Path(__file__).read_bytes());control=dict(stage=0,case='setup');lock=threading.Lock();requests=[];commands=[];packages={};owned=[];error=None
 def package(name,version,deps):
  manifest=dict(name=name,version=version,license='UNLICENSED',main='index.js',dependencies=deps)
  code=('module.exports='+json.dumps(dict(name=name,version=version))+';\n'if name==LEAF else'module.exports=require('+json.dumps(LEAF)+');\n').encode();files={'package.json':(json.dumps(manifest,separators=(',',':'))+'\n').encode(),'index.js':code};buf=io.BytesIO()
  with tarfile.open(fileobj=buf,mode='w',format=tarfile.USTAR_FORMAT)as t:
   for path,body in files.items():
    info=tarfile.TarInfo('package/'+path);info.size=len(body);info.mode=0o644;info.mtime=0;t.addfile(info,io.BytesIO(body))
  payload=gzip.compress(buf.getvalue(),mtime=0);filename=name+'-'+version+'.tgz';(run/'archives'/filename).write_bytes(payload);packages[name,version]=dict(manifest=manifest,payload=payload,filename=filename,sha256=sha(payload),integrity='sha512-'+base64.b64encode(hashlib.sha512(payload).digest()).decode(),shasum=hashlib.sha1(payload).hexdigest(),files={k:dict(bytes=len(v),sha256=sha(v))for k,v in files.items()})
 for version in ['1.0.0','1.1.0','1.2.0']:package(LEAF,version,{})
 for name,range in [(FLEX,'^1.0.0'),(FIXED,'1.0.0'),(B,'^1.1.0')]:package(name,'1.0.0',{LEAF:range})
 class Registry(http.server.BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def do_GET(self):
   path=urllib.parse.unquote(urllib.parse.urlsplit(self.path).path);parts=path.lstrip('/').split('/')
   with lock:
    case=dict(control);status=200;kind='application/json';body=b'';name=parts[0]
    if len(parts)==3 and parts[1]=='-':
     p=next((p for (n,v),p in packages.items()if n==name and p['filename']==parts[2]),None)
     if p:body=p['payload'];kind='application/octet-stream'
     else:status=404
    elif len(parts)==1 and name in [LEAF,FLEX,FIXED,B]:
     versions=['1.0.0','1.1.0','1.2.0'][:case['stage']+1]if name==LEAF else['1.0.0'];values={}
     for version in versions:
      p=packages[name,version];values[version]={**p['manifest'],'dist':dict(tarball=origin+'/'+name+'/-/'+p['filename'],integrity=p['integrity'],shasum=p['shasum'])}
     body=(json.dumps(dict(name=name,_id=name,**{'dist-tags':dict(latest=versions[-1])},versions=values,time=dict(created='2024-01-01T00:00:00.000Z',modified='2024-01-05T00:00:00.000Z',**{v:'2024-01-02T00:00:00.000Z'for v in versions})),separators=(',',':'))+'\n').encode()
    else:status=404
    if status==404:body=b'{"error":"owned_fixture_not_found"}\n'
    digest=sha(body);target=run/'responses'/(digest+('.tgz'if kind=='application/octet-stream'else'.json'))
    if not target.exists():target.write_bytes(body)
    requests.append(dict(**case,path=self.path,status=status,sha256=digest,response=str(target.relative_to(run)),authorizationPresent=bool(self.headers.get('Authorization'))))
   self.send_response(status);self.send_header('content-type',kind);self.send_header('content-length',str(len(body)));self.send_header('cache-control','no-store');self.end_headers()
   try:self.wfile.write(body)
   except BrokenPipeError:pass
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Registry);server.daemon_threads=False;origin='http://127.0.0.1:'+str(server.server_address[1]);thread=threading.Thread(target=server.serve_forever);thread.start()
 def image(project):
  files={}
  for p in sorted(project.rglob('*')):
   mode=p.lstat().st_mode;key=str(p.relative_to(project))
   if stat.S_ISLNK(mode):files[key]=dict(link=os.readlink(p));continue
   if not stat.S_ISREG(mode):continue
   body=p.read_bytes();digest=sha(body);target=run/'states'/(digest+'.bin')
   if not target.exists():target.write_bytes(body)
   files[key]=dict(bytes=len(body),sha256=digest,captured=str(target.relative_to(run)))
  return files
 try:
  for manager in ['npm','pnpm','yarn']:
   for profile,first in [('overlap',FLEX),('exact',FIXED)]:
    base=work/(manager+'-'+profile);project=base/'project';project.mkdir(parents=True)
    for name in ['cache','config','state','tmp','global']:(base/name).mkdir()
    for name in ['user.npmrc','global.npmrc']:(base/'config'/name).write_text('')
    manifest=dict(name='rules-dedupe-study',version='1.0.0',private=True,dependencies={first:'1.0.0'});write(project/'package.json',manifest)
    (project/'.npmrc').write_text('registry='+origin+'\nignore-scripts=true\naudit=false\nfund=false\nfetch-retries=0\nupdate-notifier=false\n')
    # No HOME/CODEX_HOME override. Explicit tool config/cache/global paths and
    # a private Yarn rc basename avoid user credentials/configuration.
    env=dict(PATH=str(Path(pins['node']['path']).parent)+':/usr/bin:/bin',TMPDIR=str(base/'tmp'),LANG='en_US.UTF-8',TERM='dumb',NO_COLOR='1',
     XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_STATE_HOME=str(base/'state'),
     NPM_CONFIG_USERCONFIG=str(base/'config/user.npmrc'),NPM_CONFIG_GLOBALCONFIG=str(base/'config/global.npmrc'),NPM_CONFIG_CACHE=str(base/'cache/npm'),NPM_CONFIG_PREFIX=str(base/'global'),NPM_CONFIG_REGISTRY=origin,NPM_CONFIG_FETCH_RETRIES='0',NPM_CONFIG_IGNORE_SCRIPTS='true',NPM_CONFIG_AUDIT='false',NPM_CONFIG_FUND='false',NPM_CONFIG_UPDATE_NOTIFIER='false',
     PNPM_HOME=str(base/'global'),PNPM_CONFIG_STATE_DIR=str(base/'state'),COREPACK_ENABLE_NETWORK='0',YARN_RC_FILENAME='.rules-dedupe.yml',YARN_GLOBAL_FOLDER=str(base/'global'),YARN_CACHE_FOLDER=str(base/'cache/yarn'),YARN_ENABLE_TELEMETRY='0',YARN_ENABLE_IMMUTABLE_INSTALLS='false',YARN_IGNORE_PATH='1',DO_NOT_TRACK='1')
    if manager=='yarn':
     (project/'yarn.lock').write_text('');(project/'.rules-dedupe.yml').write_text('nodeLinker: node-modules\nenableGlobalCache: false\nenableTelemetry: false\nenableScripts: false\nhttpRetry: 0\nnpmRegistryServer: '+origin+'\nunsafeHttpWhitelist: [127.0.0.1]\n');prefix=[pins['node']['path'],pins['yarn']['path']];install=['install'];check=['dedupe','--check'];apply=['dedupe']
    elif manager=='pnpm':
     (project/'pnpm-workspace.yaml').write_text('packages: []\nstoreDir: '+str(base/'cache/store')+'\ncacheDir: '+str(base/'cache/metadata')+'\nautoDedupe: false\n');prefix=[pins['pnpm']['path']];install=['install','--no-frozen-lockfile','--ignore-scripts'];check=['dedupe','--check','--ignore-scripts'];apply=['dedupe','--ignore-scripts']
    else:prefix=[pins['npm']['path']];install=['install','--ignore-scripts'];check=['find-dupes','--json','--ignore-scripts'];apply=['dedupe','--ignore-scripts']
    def command(case,args,observer=False,required=None):
     label=manager+'-'+profile+'-'+case
     with lock:control['case']=label;start_requests=len(requests)
     before=image(project);argv=([pins['node']['path']]if observer else prefix)+args;started=time.monotonic();p=subprocess.Popen(argv,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);owned.append(p);timed=False
     try:out,err=p.communicate(timeout=60)
     except subprocess.TimeoutExpired:
      timed=True;os.killpg(p.pid,signal.SIGTERM)
      try:out,err=p.communicate(timeout=3)
      except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate(timeout=5)
     try:os.killpg(p.pid,0);absent=False
     except ProcessLookupError:absent=True
     (run/(label+'.stdout')).write_bytes(out);(run/(label+'.stderr')).write_bytes(err)
     with lock:observed=json.loads(json.dumps(requests[start_requests:]));stage=control['stage']
     row=dict(manager=manager,profile=profile,case=case,argv=argv,kind='fresh-node-observer'if observer else'native-command',before=before,after=image(project),registryStage=stage,requests=observed,exitCode=p.returncode,seconds=time.monotonic()-started,timedOut=timed,groupAbsent=absent,streams={s:dict(path=label+'.'+s,sha256=sha(b))for s,b in [('stdout',out),('stderr',err)]});commands.append(row);write(run/'commands.json',commands);write(run/'requests.json',requests);print(label,p.returncode,flush=True);assert absent and not timed
     if required is not None:assert p.returncode==required,label
     return row
    runtime='const fs=require("fs"),{createRequire}=require("module"),out={};for(const name of '+json.dumps([first,B])+'){try{const p=require.resolve(name+"/package.json"),r=createRequire(p),f=r.resolve('+json.dumps(LEAF)+');out[name]={parent:p,leaf:f,value:r('+json.dumps(LEAF)+'),manifest:JSON.parse(fs.readFileSync(r.resolve('+json.dumps(LEAF+'/package.json')+'),"utf8")),source:fs.readFileSync(f,"utf8")};}catch(e){out[name]={error:e.code};}}console.log(JSON.stringify(out));'
    with lock:control['stage']=0
    command('seed',install,required=0)
    manifest['dependencies'][B]='1.0.0';write(project/'package.json',manifest)
    with lock:control['stage']=1
    command('add-later',install,required=0);command('before',['-e',runtime],True,0)
    with lock:control['stage']=2
    command('check-before',check);command('apply',apply,required=0);command('after',['-e',runtime],True,0);command('check-after',check)
 except BaseException as e:error=dict(type=type(e).__name__,message=str(e));raise
 finally:
  for p in owned:
   if p.poll()is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
  server.shutdown();server.server_close();thread.join(timeout=5)
  write(run/'requests.json',requests);write(run/'receipt.json',dict(schema=1,work=str(work),origin=origin,pins={k:pins[k]for k in ['node','npm','pnpm','yarn']},producerSha256=sha((run/'probe.py').read_bytes()),commands=len(commands),requests=len(requests),serverClosed=not thread.is_alive(),allChildrenTerminal=all(p.poll()is not None for p in owned),error=error,scope='Generated loopback registry;isolated explicit tool paths;no HOME override,global install,real registry,personal project or dependency scripts. pnpm autoDedupe:false is explicit fixture policy.',archives={p['filename']:{k:v for k,v in p.items()if k not in ['payload','filename']}for p in packages.values()}));(ROOT/'.build/js-dedupe-current').write_text(str(run)+'\n')
 print(json.dumps(dict(run=str(run.relative_to(ROOT)),commands=len(commands),serverClosed=not thread.is_alive())))
if __name__=='__main__':main()
