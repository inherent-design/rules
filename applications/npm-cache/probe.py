#!/usr/bin/env python3
"""Own one tiny registry/project/cache; distinguish cache and installed bytes."""
from datetime import datetime,timezone
import base64,gzip,hashlib,http.server,io,json,os
from pathlib import Path
import signal,stat,subprocess,tarfile,threading,time

ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    pins=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']
    for k in ['node','npm']:assert sha(Path(pins[k]['path']))==pins[k]['sha256']
    sources=json.loads((ROOT/'applications/sources/npm-cache-selections.json').read_text())
    for s in sources['sources']:assert sha(Path(s['installedSource']))==s['sha256']
    run=ROOT/'applications/evidence'/('npm-cache-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));work=run/'work'
    for d in ['home','tmp','cache','config','state','project','originals']:(work/d).mkdir(parents=True)
    (run/'probe.py').write_bytes(Path(__file__).read_bytes());project=work/'project';requests=[];commands=[];owned=[]
    package=dict(name='fixture-cache',version='1.0.0',main='index.js')
    files={'package.json':json.dumps(package).encode(),'index.js':b'module.exports="original fixture";\n'}
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w',format=tarfile.USTAR_FORMAT)as archive:
        for name,data in files.items():
            info=tarfile.TarInfo('package/'+name);info.size=len(data);info.mode=0o644;info.mtime=0;archive.addfile(info,io.BytesIO(data))
    tar=gzip.compress(buf.getvalue(),mtime=0);(run/'fixture.tgz').write_bytes(tar)
    digest=hashlib.sha512(tar).hexdigest();integrity='sha512-'+base64.b64encode(bytes.fromhex(digest)).decode()
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path=='/fixture-cache':
                body=json.dumps(dict(name='fixture-cache',**{'dist-tags':{'latest':'1.0.0'}},versions={'1.0.0':dict(package,dist=dict(tarball=origin+'/fixture-cache/-/fixture-cache-1.0.0.tgz',integrity=integrity))})).encode();kind='application/json';status=200
            elif self.path=='/fixture-cache/-/fixture-cache-1.0.0.tgz':body=tar;kind='application/octet-stream';status=200
            else:body=b'not found';kind='text/plain';status=404
            requests.append(dict(method='GET',path=self.path,status=status,bytes=len(body)))
            self.send_response(status);self.send_header('content-type',kind);self.send_header('content-length',str(len(body)));self.send_header('cache-control','public,max-age=600');self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);origin='http://127.0.0.1:'+str(server.server_address[1])
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    (project/'package.json').write_text(json.dumps(dict(name='cache-study',version='1.0.0',private=True,dependencies={'fixture-cache':'1.0.0'}),indent=2)+'\n')
    for name in ['user.npmrc','global.npmrc']:(work/'config'/name).write_text('')
    (project/'.npmrc').write_text('registry='+origin+'\nignore-scripts=true\naudit=false\nfund=false\n')
    env=dict(PATH=str(Path(pins['node']['path']).parent)+':/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),XDG_CONFIG_HOME=str(work/'config'),XDG_STATE_HOME=str(work/'state'),
        NPM_CONFIG_USERCONFIG=str(work/'config/user.npmrc'),NPM_CONFIG_GLOBALCONFIG=str(work/'config/global.npmrc'),NPM_CONFIG_CACHE=str(work/'cache'),NPM_CONFIG_AUDIT='false',NPM_CONFIG_FUND='false',NPM_CONFIG_IGNORE_SCRIPTS='true',NPM_CONFIG_UPDATE_NOTIFIER='false',MISE_SKIP_RESHIM='1',DO_NOT_TRACK='1',LANG='en_US.UTF-8')
    def image(base):
        result={}
        for p in sorted(base.rglob('*')):
            s=p.lstat();relative=str(p.relative_to(base))
            if stat.S_ISREG(s.st_mode):result[relative]=dict(bytes=s.st_size,sha256=sha(p),mode=stat.S_IMODE(s.st_mode))
            elif stat.S_ISLNK(s.st_mode):result[relative]=dict(link=os.readlink(p))
        return result
    def state():
        return dict(authored={p.name:dict(sha256=sha(p),text=p.read_text())for p in [project/'package.json',project/'package-lock.json',project/'.npmrc']if p.exists()},
                    installed=image(project/'node_modules'),cache=image(work/'cache/_cacache'))
    def command(label,args,expected=0,node=False):
        argv=[pins['node'if node else'npm']['path'],*args];before=state();start=len(requests);started=time.monotonic()
        with (run/(label+'.stdout')).open('xb')as out,(run/(label+'.stderr')).open('xb')as err:
            child=subprocess.Popen(argv,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);owned.append(child)
            (run/'owned-processes.json').write_text(json.dumps([dict(pid=p.pid,retired=p.poll()is not None)for p in owned],indent=2)+'\n')
            timed=False
            try:child.wait(timeout=40)
            except subprocess.TimeoutExpired:timed=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
        try:os.killpg(child.pid,0)
        except ProcessLookupError:absent=True
        else:absent=False
        row=dict(case=label,kind='observer'if node else'npm',argv=argv,before=before,after=state(),requests=requests[start:],
                 outcome=dict(exitCode=child.returncode,timedOut=timed,ownedGroupAbsent=absent),seconds=time.monotonic()-started,
                 streams={s:dict(file=label+'.'+s,sha256=sha(run/(label+'.'+s)))for s in ['stdout','stderr']})
        commands.append(row);(run/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');(run/'requests.json').write_text(json.dumps(requests,indent=2)+'\n')
        print(label,child.returncode,'requests',len(row['requests']),flush=True)
        assert not timed and absent
        if expected=='nonzero':assert child.returncode>0
        elif expected is not None:assert child.returncode==expected
        return row
    observer='try{console.log(JSON.stringify({available:true,value:require("fixture-cache")}))}catch(e){console.log(JSON.stringify({available:false,code:e.code}))}'
    def runtime(label):return command(label,['-e',observer],node=True)
    try:
        command('install',['install','--ignore-scripts']);runtime('runtime-initial')
        command('verify-valid',['cache','verify'])
        candidates=[p for p in(work/'cache/_cacache/content-v2/sha512').rglob('*')if p.is_file()and not p.is_symlink()and hashlib.sha512(p.read_bytes()).hexdigest()==digest]
        assert len(candidates)==1;target=candidates[0];s=target.lstat()
        assert stat.S_ISREG(s.st_mode)and s.st_nlink==1 and target.resolve().is_relative_to((work/'cache/_cacache/content-v2/sha512').resolve())
        assert target.read_bytes()==tar
        before=state();(work/'originals/cache-tar.tgz').write_bytes(target.read_bytes());target.chmod(0o600)
        bad=bytearray(tar);bad[0]^=1;target.write_bytes(bad)
        (run/'cache-corruption.json').write_text(json.dumps(dict(target=str(target.relative_to(work)),before=before,after=state(),expectedIntegrity=integrity,originalSha256=sha(work/'originals/cache-tar.tgz'),mutatedSha256=sha(target),nlinkBefore=s.st_nlink),indent=2)+'\n')
        runtime('runtime-after-cache-corruption');command('verify-corrupt',['cache','verify']);runtime('runtime-after-verify')
        command('ci-offline-missing',['ci','--offline','--ignore-scripts'],expected='nonzero');runtime('runtime-after-failed-ci')
        command('ci-origin-recovery',['ci','--ignore-scripts']);runtime('runtime-after-recovery')
        installed=project/'node_modules/fixture-cache/index.js';s=installed.lstat();assert stat.S_ISREG(s.st_mode)and s.st_nlink==1 and not installed.is_symlink()
        before=state();(work/'originals/installed-index.js').write_bytes(installed.read_bytes());installed.write_bytes(b'module.exports="edited installation";\n')
        (run/'installed-edit.json').write_text(json.dumps(dict(before=before,after=state(),target='node_modules/fixture-cache/index.js',originalSha256=sha(work/'originals/installed-index.js'),editedSha256=sha(installed)),indent=2)+'\n')
        command('verify-with-installed-edit',['cache','verify']);runtime('runtime-edited-installation')
        command('ci-offline-valid',['ci','--offline','--ignore-scripts']);runtime('runtime-final')
        for source in sources['sources']:assert sha(Path(source['installedSource']))==source['sha256']
        receipt=dict(schema=1,tools={k:pins[k]for k in ['node','npm']},producerSha256=sha(run/'probe.py'),origin=origin,commands=len(commands),
            fixtureSha256=sha(run/'fixture.tgz'),fixtureIntegrity=integrity,allOwnedGroupsAbsent=all(c['outcome']['ownedGroupAbsent']for c in commands),
            allocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),
            limits=['One owned project/private cache and one loopback registry;generated two-file archive only,no host/global cache or external registry service.',
                    'Deliberate corruption is confined to an exact hash-matched private regular cache file with nlink1 and retained original. Local installation edit is also owned/regular/nlink1.',
                    'Snapshots cover selected authored/installed/cache files,not process-wide IO,shared-cache races,remote trust/durability or arbitrary npm projects.'])
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    finally:
        for child in owned:
            if child.poll()is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
        server.shutdown();server.server_close();thread.join(timeout=5);assert not thread.is_alive()
        (run/'closed.json').write_text(json.dumps(dict(serverClosed=True,allOwnedProcessesRetired=all(c.poll()is not None for c in owned)))+'\n')
        (run/'owned-processes.json').write_text(json.dumps([dict(pid=p.pid,retired=p.poll()is not None)for p in owned],indent=2)+'\n')
        print('capture',run,flush=True)


if __name__=='__main__':main()
