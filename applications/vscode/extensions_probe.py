"""Owner-run local VSIX lifecycle. Never part of ordinary CI; no GUI launch."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
CODE = Path('/Applications/Visual Studio Code.app/Contents/MacOS/Code')
APP = CODE.parent.parent / 'Resources/app'
PIN = '661626d0e72f97806550790a98fb87116c9db825'
IDENTITY = 'rules-study.lifecycle-fixture'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    assert sha(CODE) == '38af459b440e3e57b983affc83ae48ced6fe820f642f771cf885ca5bee68a5c0'
    assert json.loads((APP/'product.json').read_text())['commit'] == PIN
    private = Path(tempfile.mkdtemp(prefix='rules-vsc-ext-', dir='/private/tmp'))
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    capture = ROOT/'applications/evidence'/('vscode-extensions-'+stamp)
    capture.mkdir(parents=True)
    dirs = {name: private/name for name in ['home','tmp','data','extensions','downloads','shared','plugins','agents-data','agents-extensions','workspace']}
    for path in dirs.values():
        path.mkdir()
    settings = dirs['data']/'User/settings.json'
    write(settings, {'telemetry.telemetryLevel':'off','update.mode':'none',
                     'extensions.autoUpdate':False,'extensions.autoCheckUpdates':False,
                     'security.workspace.trust.enabled':True,'chat.disableAIFeatures':True})
    flags = []
    for flag, name in [('user-data-dir','data'),('extensions-dir','extensions'),
                       ('extensions-download-dir','downloads'),('shared-data-dir','shared'),
                       ('agent-plugins-dir','plugins'),('agents-user-data-dir','agents-data'),
                       ('agents-extensions-dir','agents-extensions')]:
        flags += ['--'+flag, str(dirs[name])]
    flags += ['--use-inmemory-secretstorage','--disable-telemetry']
    beacon = private/'activated.json'
    env = {'PATH':'/usr/bin:/bin:/usr/sbin:/sbin', 'HOME':str(dirs['home']),
           'TMPDIR':str(dirs['tmp'])+'/', 'LANG':'en_US.UTF-8', 'LC_ALL':'en_US.UTF-8',
           'ELECTRON_RUN_AS_NODE':'1','VSCODE_DISABLE_TELEMETRY':'1',
           'RULES_EXTENSION_BEACON':str(beacon)}
    env['XDG_CONFIG_HOME'] = str(dirs['home']/'config')
    env['XDG_CACHE_HOME'] = str(dirs['home']/'cache')
    packages = {}
    for version, engine in [('0.0.1','^1.100.0'),('0.0.2','^1.100.0'),('0.0.3','^999.0.0')]:
        manifest = {'name':'lifecycle-fixture','publisher':'rules-study','displayName':'Owned lifecycle fixture',
                    'version':version,'engines':{'vscode':engine},'main':'./main.cjs',
                    'browser':'./browser.js','extensionKind':['workspace','web'],
                    'activationEvents':['onStartupFinished']}
        entries = {'extension/package.json':json.dumps(manifest,indent=2)+'\n',
                   'extension/main.cjs':"exports.activate=()=>{require('fs').writeFileSync(process.env.RULES_EXTENSION_BEACON,JSON.stringify({version:"+json.dumps(version)+"}));};\n",
                   'extension/browser.js':"exports.activate=()=>console.log('owned browser lifecycle fixture');\n",
                   '[Content_Types].xml':'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="json" ContentType="application/json"/><Default Extension="cjs" ContentType="application/javascript"/><Default Extension="js" ContentType="application/javascript"/></Types>',
                   'extension.vsixmanifest':'<?xml version="1.0"?><PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011"><Metadata><Identity Language="en-US" Id="lifecycle-fixture" Version="'+version+'" Publisher="rules-study"/><DisplayName>Owned lifecycle fixture</DisplayName><Description xml:space="preserve">Disposable study fixture</Description></Metadata><Installation><InstallationTarget Id="Microsoft.VisualStudio.Code"/></Installation><Dependencies/><Assets><Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/></Assets></PackageManifest>'}
        path = private/('fixture-'+version+'.vsix')
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for name, text in entries.items():
                z.writestr(name,text)
        packages[version] = path
        # Owned fixture bytes are public, unlike installed application binaries.
        (capture/path.name).write_bytes(path.read_bytes())
    tools = {str(p):{'sha256':sha(p),'bytes':p.stat().st_size} for p in [CODE,APP/'product.json',APP/'out/cli.js',Path(__file__)]}
    write(capture/'setup.json', {'schema':1,'revision':PIN,'version':'1.148.0','private':str(private),
          'dirs':{k:str(v)for k,v in dirs.items()},'tools':tools,'env':env,'flags':flags,
          'scope':'Electron Node CLI, owned local VSIX only. No desktop, marketplace ID, remote host, account, or extension host activation.'})
    rows = []

    def snapshot():
        files = []
        for base in ['data','extensions','shared','downloads','home','plugins','agents-data','agents-extensions']:
            for p in sorted(dirs[base].rglob('*')):
                if p.is_file() and not p.is_symlink():
                    files.append({'path':str(p.relative_to(private)),'bytes':p.stat().st_size,'sha256':sha(p)})
        membership = []
        index = dirs['extensions']/'extensions.json'
        if index.exists():
            membership = json.loads(index.read_text())
        packages_now = {}
        for p in sorted(dirs['extensions'].glob('*/package.json')):
            value = json.loads(p.read_text())
            packages_now[str(p.relative_to(private))] = {'name':value['name'],'version':value['version'],'sha256':sha(p)}
        obsolete = dirs['extensions']/'.obsolete'
        return {'files':files,'membership':membership,'packages':packages_now,
                'obsolete':json.loads(obsolete.read_text())if obsolete.exists()else None,
                'activationBeacon':beacon.exists(),'settingsSha256':sha(settings)}

    def run(label,args):
        before = snapshot()
        argv = [str(CODE),str(APP/'out/cli.js'),*flags,*map(str,args)]
        started=time.time()
        p=subprocess.Popen(argv,cwd=dirs['workspace'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timeout=False
        try:
            out,err=p.communicate(timeout=90)
        except subprocess.TimeoutExpired:
            timeout=True
            os.killpg(p.pid,signal.SIGTERM)
            try: out,err=p.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate()
        streams={}
        for name,data in [('stdout',out),('stderr',err)]:
            path=capture/(label+'.'+name);path.write_bytes(data)
            streams[name]={'path':path.name,'sha256':sha(path),'bytes':len(data)}
        row={'label':label,'argv':argv,'cwd':str(dirs['workspace']),'pid':p.pid,
             'exit':p.returncode,'timedOut':timeout,'seconds':round(time.time()-started,4),
             'streams':streams,'before':before,'after':snapshot()}
        rows.append(row);write(capture/'commands.json',rows)
        print(label,p.returncode,round(time.time()-started,2),flush=True)
        if timeout: raise RuntimeError('Preserved timed-out operation; do not restart.')

    run('version',['--version'])
    run('empty',['--list-extensions','--show-versions'])
    run('install-one',['--install-extension',packages['0.0.1'],'--do-not-include-pack-dependencies','--do-not-sync'])
    run('list-one',['--list-extensions','--show-versions'])
    run('incompatible',['--install-extension',packages['0.0.3'],'--do-not-include-pack-dependencies','--do-not-sync'])
    run('after-refusal',['--list-extensions','--show-versions'])
    run('install-two',['--install-extension',packages['0.0.2'],'--do-not-include-pack-dependencies','--do-not-sync'])
    run('list-two',['--list-extensions','--show-versions'])
    run('downgrade',['--install-extension',packages['0.0.1'],'--do-not-include-pack-dependencies','--do-not-sync'])
    run('after-downgrade',['--list-extensions','--show-versions'])
    run('uninstall',['--uninstall-extension',IDENTITY])
    run('after-uninstall',['--list-extensions','--show-versions'])
    run('uninstall-again',['--uninstall-extension',IDENTITY])
    # Read process table only; do not signal unspecified processes.
    ps=subprocess.run(['/bin/ps','-axo','pid=,ppid=,command='],capture_output=True,text=True,check=True)
    matches=[s for s in ps.stdout.splitlines()if str(private)in s]
    write(capture/'retirement.json',{'private':str(private),'allChildrenWaited':True,'matchingProcesses':matches,'beaconPresent':beacon.exists()})
    assert not matches,matches
    assert not beacon.exists()
    assert all(sha(p)==v['sha256']for p,v in tools.items())
    write(capture/'receipt.json',{'schema':1,'kind':'native-electron-node-cli','revision':PIN,
          'private':str(private),'commands':len(rows),'producerSha256':sha(__file__),
          'commandsSha256':sha(capture/'commands.json'),'setupSha256':sha(capture/'setup.json'),
          'noGUI':True,'noExtensionActivationObserved':True,'allOwnedChildrenWaited':True})
    print(json.dumps({'capture':str(capture),'private':str(private)}),flush=True)


if __name__=='__main__':
    main()
