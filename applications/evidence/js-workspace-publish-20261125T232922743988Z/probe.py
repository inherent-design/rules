"""Owner-run workspace publication/consumer fixture. Loopback and generated code only."""
from datetime import datetime,timezone
import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import platform
import signal
import socket
import stat
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.parse

ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda b:hashlib.sha256(b).hexdigest()
write=lambda p,x:p.write_text(json.dumps(x,indent=2)+'\n')


def image(root):
    values={}
    for directory,dirs,files in os.walk(root,followlinks=False):
        for n in sorted(dirs+files):
            p=Path(directory)/n;s=p.lstat();rel=p.relative_to(root).as_posix()
            if stat.S_ISLNK(s.st_mode):values[rel]=dict(kind='link',target=os.readlink(p))
            elif stat.S_ISDIR(s.st_mode):values[rel]=dict(kind='directory')
            else:
                assert stat.S_ISREG(s.st_mode);raw=p.read_bytes()
                value=dict(kind='file',bytes=len(raw),sha256=digest(raw),mode=s.st_mode,mtimeNs=s.st_mtime_ns)
                if p.name in ['package.json','hooks.jsonl','pnpm-publish-summary.json']:value['bytesHex']=raw.hex()
                values[rel]=value
    return values


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remaining-after-first-capture',action='store_true',help='Skip npm success and late failure already retained in the first capture.')
    selection=parser.parse_args()
    pins=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']
    for n in ['node','npm','pnpm','yarn']:assert sha(Path(pins[n]['path']))==pins[n]['sha256']
    for source in json.loads((ROOT/'applications/sources/js-publication-selections.json').read_text()):
        if 'installedCorrespondence' in source:assert sha(Path(source['installedCorrespondence']['path']))==source['sha256']
    work=Path(tempfile.mkdtemp(prefix='rules-js-workspace-publish-',dir='/private/tmp'))
    for p in [work,*work.parents]:assert not any((p/n).exists() for n in ['.npmrc','.yarnrc.yml','pnpm-workspace.yaml'])
    run=ROOT/'applications/evidence'/('js-workspace-publish-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir();(run/'probe.py').write_bytes(Path(__file__).read_bytes())
    records={};archives={};events=[];errors=[];rows=[];control=dict(case='setup');mutex=threading.Lock()
    def record_events():write(run/'server-events.json',events)
    class Registry(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def log_message(self,*args):pass
        def reply(self,status,body,kind='application/json'):
            data=json.dumps(body).encode() if kind=='application/json' else body
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('Connection','close');self.end_headers();self.wfile.write(data);self.close_connection=True
        def do_GET(self):
            self.connection.settimeout(5);path=urllib.parse.unquote(urllib.parse.urlsplit(self.path).path.lstrip('/'))
            with mutex:
                if path.startswith('tarballs/'):
                    key=path.removeprefix('tarballs/').removesuffix('.tgz');data=archives.get(key)
                    events.append(dict(case=control['case'],method='GET',path=self.path,status=200 if data else 404,artifact=key));record_events()
                    status=200 if data else 404;body=data if data else b'';kind='application/octet-stream'
                else:
                    versions=records.get(path,{})
                    events.append(dict(case=control['case'],method='GET',path=self.path,status=200 if versions else 404));record_events()
                    status=200 if versions else 404;body=dict(name=path,_id=path,_rev='fixture-'+str(len(versions)),versions=versions,**{'dist-tags':{'latest':list(versions)[-1]} if versions else {}}) if versions else {'error':'not_found'};kind='application/json'
            self.reply(status,body,kind)
        def do_PUT(self):
            try:self.put()
            except Exception as e:
                with mutex:errors.append(dict(case=control['case'],type=type(e).__name__,message=str(e)));write(run/'server-errors.json',errors)
                self.reply(500,{'error':'fixture_assertion'})
        def put(self):
            self.connection.settimeout(5);length=int(self.headers.get('Content-Length','0'));assert 0<length<1_000_000
            data=self.rfile.read(length);request=json.loads(data);name=urllib.parse.unquote(urllib.parse.urlsplit(self.path).path.lstrip('/'))
            assert name.startswith('rules-workspace-fixture-') and request['name']==name
            assert len(request['versions'])==len(request['_attachments'])==1
            version,manifest=next(iter(request['versions'].items()));attachment=next(iter(request['_attachments'].values()));tarball=base64.b64decode(attachment['data'],validate=True)
            assert len(tarball)==attachment['length'] and len(tarball)<100_000
            with tarfile.open(fileobj=io.BytesIO(tarball),mode='r:gz') as tar:
                members=tar.getmembers();assert len(members)<20 and sum(m.size for m in members)<100_000
                assert all(m.isdir() or m.isfile() for m in members)
                files={m.name:digest(tar.extractfile(m).read()) for m in members if m.isfile()}
                packaged=json.loads(tar.extractfile('package/package.json').read())
                assert packaged['name']==name and packaged['version']==version and set(files)=={'package/package.json','package/index.js'}
            assert manifest['dist']['shasum']==hashlib.sha1(tarball).hexdigest()
            assert manifest['dist']['integrity']=='sha512-'+base64.b64encode(hashlib.sha512(tarball).digest()).decode()
            address=digest(tarball)
            with mutex:
                exists=version in records.get(name,{})
                status=409 if exists else 201
                event=dict(case=control['case'],method='PUT',path=self.path,name=name,version=version,accepted=not exists,status=status,
                    archiveSha256=address,archiveBytes=len(tarball),files=files,packagedManifest=packaged,requestSha256=digest(data),authorizationPresent=bool(self.headers.get('Authorization')))
                events.append(event)
                if not exists:
                    stored=json.loads(json.dumps(manifest));stored['dist']['tarball']=url+'tarballs/'+address+'.tgz'
                    records.setdefault(name,{})[version]=stored;archives[address]=tarball
                    (run/('received-'+str(len(events)-1)+'.json')).write_bytes(data);(run/('received-'+str(len(events)-1)+'.tgz')).write_bytes(tarball)
                record_events()
            self.reply(status,{'ok':True} if not exists else {'error':'version_exists'})
    server=ThreadingHTTPServer(('127.0.0.1',0),Registry);server.daemon_threads=False
    thread=threading.Thread(target=server.serve_forever,name='rules-workspace-registry');thread.start();url=f'http://127.0.0.1:{server.server_port}/'
    setup=dict(schema=1,work=str(work),producerSha256=sha(run/'probe.py'),tools={n:pins[n] for n in ['node','npm','pnpm','yarn']},platform=platform.platform(),architecture=platform.machine(),registry=url,
      remainingAfterFirstCapture=selection.remaining_after_first_capture,
      scope='Generated private/consumer/producer workspaces; manager-specific declaration profiles, own hooks and loopback npm-style registry; success artifacts consumed by isolated npm then generated Node code. No public registry/account/userproject,realcredential,Gitpolicy,TLS,replication/durability,arbitraryresolver or platform qualification. HOME is intentionally private only in each child test profile; host environment is not modified.')
    write(run/'setup.json',setup)
    def command(label,manager,kind,project,prefix,args,env,expected,request):
        with mutex:control['case']=label;start=len(events);before_registry=json.loads(json.dumps(records))
        before=image(project);started=time.monotonic();child=subprocess.Popen(prefix+args,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timed=False;print(json.dumps(dict(start=label,pid=child.pid)),flush=True)
        try:out,err=child.communicate(timeout=90)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
        (run/(label+'.stdout')).write_bytes(out);(run/(label+'.stderr')).write_bytes(err)
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        with mutex:after_registry=json.loads(json.dumps(records));selected_events=json.loads(json.dumps(events[start:]))
        row=dict(id=label,manager=manager,kind=kind,argv=prefix+args,root=str(project),pid=child.pid,exitCode=child.returncode,timedOut=timed,groupAbsent=absent,seconds=time.monotonic()-started,request=request,
          before=before,after=image(project),registryBefore=before_registry,registryAfter=after_registry,serverEvents=selected_events,streams={n:sha(run/(label+'.'+n)) for n in ['stdout','stderr']})
        rows.append(row);write(run/'commands.json',rows);print(json.dumps(dict(finish=label,exitCode=child.returncode,puts=[e.get('name') for e in selected_events if e['method']=='PUT'],seconds=row['seconds'])),flush=True)
        assert not timed and absent and child.returncode==expected and not errors,'Retain failure; do not automatically repeat collection'
        return row
    try:
        hook="""const fs = require('fs');
fs.appendFileSync(process.env.FIXTURE_HOOK_LOG, JSON.stringify({role:process.argv[2],event:process.argv[3],cwd:process.cwd()})+'\\n');
if (process.argv[2]===process.env.FIXTURE_FAIL_PACKAGE && process.argv[3]===process.env.FIXTURE_FAIL_HOOK) process.exit(7);
"""
        for manager in ['npm','pnpm','yarn']:
            for case,version in [('success','1.0.0'),('producer-late-failure','1.1.0'),('private-pre-hook-failure','1.2.0')]:
                if selection.remaining_after_first_capture and manager=='npm' and case in ['success','producer-late-failure']:continue
                base=work/manager/case;project=base/'project'
                for p in [project,base/'home',base/'config',base/'cache',base/'tmp']:p.mkdir(parents=True)
                npmrc=base/'config/user.npmrc';npmrc.write_text(f'registry={url}\n//127.0.0.1:{server.server_port}/:_authToken=rules-local-workspace-only\nfetch-retries=0\nupdate-notifier=false\n')
                (base/'config/global.npmrc').write_text('')
                env=dict(PATH=str(Path(pins['node']['path']).parent)+':/usr/bin:/bin',HOME=str(base/'home'),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),TMPDIR=str(base/'tmp'),
                  NPM_CONFIG_USERCONFIG=str(npmrc),NPM_CONFIG_GLOBALCONFIG=str(base/'config/global.npmrc'),NPM_CONFIG_CACHE=str(base/'cache/npm'),NPM_CONFIG_REGISTRY=url,NPM_CONFIG_FETCH_RETRIES='0',
                  PNPM_CONFIG_FETCH_RETRIES='0',PNPM_CONFIG_STATE_DIR=str(base/'state'),LANG='en_US.UTF-8',COREPACK_ENABLE_NETWORK='0',YARN_ENABLE_TELEMETRY='0',YARN_ENABLE_IMMUTABLE_INSTALLS='false',DO_NOT_TRACK='1',MISE_SKIP_RESHIM='1',CI='1',NO_COLOR='1',FORCE_COLOR='0',
                  FIXTURE_HOOK_LOG=str(project/'hooks.jsonl'),FIXTURE_FAIL_PACKAGE='',FIXTURE_FAIL_HOOK='')
                names={r:'rules-workspace-fixture-'+manager+'-'+r for r in ['private','consumer','producer']}
                workspace_dirs=['packages/0-private','packages/a-consumer','packages/z-producer']
                root_manifest=dict(name='rules-workspace-fixture-'+manager+'-root',private=True,version=version,workspaces=workspace_dirs,packageManager=manager+'@'+pins[manager]['version'])
                write(project/'package.json',root_manifest)
                if manager=='pnpm':(project/'pnpm-workspace.yaml').write_text('packages:\n  - packages/*\n')
                if manager=='yarn':(project/'.yarnrc.yml').write_text('nodeLinker: node-modules\nenableGlobalCache: false\nenableTelemetry: false\nenableImmutableInstalls: false\n'+f'globalFolder: {base}/cache/yarn-global\nnpmRegistryServer: {url}\nnpmPublishRegistry: {url}\nunsafeHttpWhitelist: [127.0.0.1]\nnpmAuthToken: rules-local-workspace-only\nnpmAlwaysAuth: true\nhttpRetry: 0\n')
                for role,relative in zip(['private','consumer','producer'],workspace_dirs,strict=True):
                    pkg=project/relative;pkg.mkdir(parents=True)
                    manifest=dict(name=names[role],version=version,private=role=='private',main='index.js',files=['index.js'],license='UNLICENSED',publishConfig=dict(registry=url),
                      scripts={event:'node hook.cjs '+role+' '+event for event in ['prepublish','prepublishOnly','prepack','postpack','publish','postpublish']})
                    if role=='consumer':manifest['dependencies']={names['producer']:version if manager=='npm' else 'workspace:*'}
                    write(pkg/'package.json',manifest);(pkg/'hook.cjs').write_text(hook)
                    (pkg/'index.js').write_text('module.exports = '+('require('+json.dumps(names['producer'])+')' if role=='consumer' else json.dumps(role+':'+version))+';\n')
                prefix=[pins['node']['path'],pins['yarn']['path']] if manager=='yarn' else [pins[manager]['path']]
                if manager=='yarn':command(manager+'-'+case+'-initialize',manager,'initialize',project,prefix,['install'],env,0,dict(case=case,version=version))
                fail_role='producer' if case=='producer-late-failure' else 'private' if case=='private-pre-hook-failure' else ''
                fail_hook=('postpack' if manager=='yarn' else 'postpublish') if fail_role=='producer' else ('prepublish' if manager=='yarn' else 'prepublishOnly') if fail_role else ''
                child_env={**env,'FIXTURE_FAIL_PACKAGE':fail_role,'FIXTURE_FAIL_HOOK':fail_hook}
                if manager=='npm':args=['publish','--workspaces','--json','--fetch-retries=0','--no-audit','--no-fund']
                elif manager=='pnpm':args=['--recursive','publish','--no-git-checks','--json','--registry',url,'--npmrc-auth-file',str(npmrc),'--report-summary']
                else:args=['workspaces','foreach','-A','-t','--no-private','npm','publish','--json']
                expected=(7 if manager=='npm' else 1) if case=='producer-late-failure' or case=='private-pre-hook-failure' and manager=='npm' else 0
                command(manager+'-'+case,manager,'publish',project,prefix,args,child_env,expected,dict(case=case,version=version,sourceNames=names,workspaceDirs=workspace_dirs,dependency=version if manager=='npm' else 'workspace:*',failingRole=fail_role,failingHook=fail_hook))
                if case=='success':
                    consumer=base/'consumer';consumer.mkdir();write(consumer/'package.json',dict(name='rules-workspace-runtime-consumer',private=True,version='0.0.0'))
                    command(manager+'-consume',manager,'consume',consumer,[pins['npm']['path']],['install',names['consumer']+'@'+version,'--ignore-scripts','--no-audit','--no-fund','--fetch-retries=0'],env,0,dict(case=case,version=version,source=names['consumer']))
                    program='console.log(JSON.stringify({value:require('+json.dumps(names['consumer'])+'),resolved:require.resolve('+json.dumps(names['consumer'])+')}))'
                    command(manager+'-execute-consumer',manager,'execute',consumer,[pins['node']['path']],['-e',program],env,0,dict(case=case,version=version,source=names['consumer']))
        write(run/'registry-final.json',records)
        write(run/'receipt.json',dict(schema=1,complete=True,commands=len(rows),publicationOutcomes=sum(r['kind']=='publish' for r in rows),consumerInstalls=sum(r['kind']=='consume' for r in rows),consumerExecutions=sum(r['kind']=='execute' for r in rows),allRecordedGroupsAbsent=all(r['groupAbsent'] for r in rows),setupSha256=sha(run/'setup.json'),producerSha256=sha(run/'probe.py'),serverErrors=errors,allocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),scope='Three source-derived workspace publication cases per manager and successful artifacts consumed by npm/Node; own memory registry. No real registry/auth/TLS/durability/default retry/platform or general resolver qualification. Models and independent artifact/effect review pending.'))
        print(json.dumps(dict(run=str(run),work=str(work),complete=True)),flush=True)
    except BaseException as e:
        write(run/'failure.json',dict(type=type(e).__name__,message=str(e),commands=len(rows),serverErrors=errors));print(json.dumps(dict(run=str(run),work=str(work),complete=False)),flush=True);raise
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
        write(run/'server-events.json',events);write(run/'server-retired.json',dict(threadJoined=not thread.is_alive(),listeningSocketClosed=server.socket.fileno()==-1))
        assert not thread.is_alive()


if __name__=='__main__':main()
