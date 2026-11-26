"""Owner-only activation collection. GUI launch/actions require re:desktop access."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
import zipfile

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
CODE=Path('/Applications/Visual Studio Code.app/Contents/MacOS/Code')
APP=CODE.parent.parent/'Resources/app'
PIN='661626d0e72f97806550790a98fb87116c9db825'
SHA='38af459b440e3e57b983affc83ae48ced6fe820f642f771cf885ca5bee68a5c0'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
def check():
    assert sha(CODE)==SHA and json.load(open(APP/'product.json'))['commit']==PIN
def paths(run):
    meta=json.load(open(run/'meta.json'));p=Path(meta['private'])
    assert run.parent==ROOT/'applications/evidence' and run.name.startswith('vscode-activation-')
    assert p.parent==Path('/private/tmp')and p.name.startswith('rules-vsc-act-')
    return meta,p
def flags(p):
    result=[]
    for flag,folder in [('user-data-dir','data'),('extensions-dir','extensions'),('extensions-download-dir','downloads'),('shared-data-dir','shared'),('agent-plugins-dir','plugins'),('agents-user-data-dir','agents-data'),('agents-extensions-dir','agents-extensions')]:result+=['--'+flag,str(p/folder)]
    return result+['--use-inmemory-secretstorage','--disable-telemetry']
def env(p):
    return {'PATH':'/usr/bin:/bin','HOME':str(Path.home()),'TMPDIR':str(p/'tmp')+'/',
      'XDG_CONFIG_HOME':str(p/'xdg-config'),'XDG_CACHE_HOME':str(p/'xdg-cache'),
      'LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8','SHELL':'/bin/bash','VSCODE_DISABLE_TELEMETRY':'1'}
def storage(p):
    out=[]
    for f in sorted((p/'data/User').glob('**/state.vscdb')):
        with sqlite3.connect('file:'+str(f)+'?mode=ro',uri=True)as db:
            rows=db.execute("select key,value from ItemTable where key like '%extensionsIdentifiers%' or key like '%disabledExtensions%'").fetchall()
        out.append({'path':str(f.relative_to(p)),'rows':[{'key':k,'value':v.decode()if isinstance(v,bytes)else v}for k,v in rows]})
    return out

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','install','launch','request']);parser.add_argument('run',nargs='?',type=Path);parser.add_argument('--phase');parser.add_argument('--operation');args=parser.parse_args();check()
    if args.action=='prepare':
        p=Path(tempfile.mkdtemp(prefix='rules-vsc-act-',dir='/private/tmp'))
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run=ROOT/'applications/evidence'/('vscode-activation-'+stamp);run.mkdir()
        for d in ['data/User','extensions','downloads','shared','plugins','agents-data','agents-extensions','tmp','workspace-a','workspace-b','controller','xdg-config','xdg-cache']:(p/d).mkdir(parents=True)
        write(p/'data/User/settings.json',{'workbench.startupEditor':'none','window.title':'Rules extension lifecycle fixture','files.hotExit':'off','telemetry.telemetryLevel':'off','update.mode':'none','extensions.autoUpdate':False,'extensions.autoCheckUpdates':False,'extensions.autoRestart':False,'security.workspace.trust.enabled':False,'git.enabled':False,'chat.disableAIFeatures':True})
        controller={'publisher':'rules-study','name':'activation-controller','version':'0.0.1','engines':{'vscode':'^1.148.0'},'main':'./controller.cjs','extensionKind':['ui'],'activationEvents':['onStartupFinished']}
        target={'publisher':'rules-study','name':'activation-target','version':'0.0.1','engines':{'vscode':'^1.148.0'},'main':'./target.cjs','extensionKind':['workspace'],'activationEvents':[]}
        write(p/'controller/package.json',controller);(p/'controller/controller.cjs').write_bytes((HERE/'activation-controller.cjs').read_bytes())
        for file in ['activation-controller.cjs','activation-target.cjs','activation_probe.py']:(run/file).write_bytes((HERE/file).read_bytes())
        write(run/'controller-package.json',controller);write(run/'target-package.json',target)
        archive=p/'target.vsix'
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED)as z:
            z.writestr('extension/package.json',json.dumps(target,indent=2)+'\n');z.writestr('extension/target.cjs',(HERE/'activation-target.cjs').read_bytes())
            z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="json" ContentType="application/json"/><Default Extension="cjs" ContentType="application/javascript"/></Types>')
            z.writestr('extension.vsixmanifest','<?xml version="1.0"?><PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011"><Metadata><Identity Language="en-US" Id="activation-target" Version="0.0.1" Publisher="rules-study"/><DisplayName>Owned activation target</DisplayName><Description xml:space="preserve">Disposable fixture</Description></Metadata><Installation><InstallationTarget Id="Microsoft.VisualStudio.Code"/></Installation><Dependencies/><Assets><Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/></Assets></PackageManifest>')
        (run/'target.vsix').write_bytes(archive.read_bytes())
        meta={'schema':1,'capture':str(run),'private':str(p),'revision':PIN,'version':'1.148.0','producerSha256':sha(HERE/'activation_probe.py'),'controllerSha256':sha(HERE/'activation-controller.cjs'),'targetSha256':sha(HERE/'activation-target.cjs'),'codeSha256':SHA,'scope':'Private named data stores, ordinary HOME/in-memory secrets; trust disabled, not enforcement. No marketplace/account/personal profile.'};write(run/'meta.json',meta);print(json.dumps({'capture':str(run),'private':str(p)}));return
    run=args.run.resolve();meta,p=paths(run)
    assert sha(run/'activation_probe.py')==meta['producerSha256']==sha(__file__)
    if args.action=='install':
        argv=[str(CODE),str(APP/'out/cli.js'),*flags(p),'--install-extension',str(p/'target.vsix'),'--do-not-include-pack-dependencies','--do-not-sync']
        cli_home=p/'cli-home';cli_home.mkdir(exist_ok=True)
        e={**env(p),'HOME':str(cli_home),'ELECTRON_RUN_AS_NODE':'1'}
        r=subprocess.run(argv,cwd=p,env=e,capture_output=True,timeout=60)
        (run/'install.stdout').write_bytes(r.stdout);(run/'install.stderr').write_bytes(r.stderr);write(run/'install.json',{'argv':argv,'exit':r.returncode,'home':str(cli_home),'stdoutSha256':sha(run/'install.stdout'),'stderrSha256':sha(run/'install.stderr')});assert r.returncode==0;print('Installed owned target via CLI');return
    assert args.phase in ['a-disable','b-other','a-enable','a-confirm']
    phase=args.phase
    if args.action=='launch':
        assert not (run/(phase+'.process.json')).exists(),'Do not restart an observed phase.'
        if (p/'control.json').exists():
            old=json.load(open(p/'control.json'));write(run/(old['phase']+'.last-control.json'),old);(p/'control.json').unlink()
        workspace='workspace-b'if phase=='b-other'else'workspace-a'
        argv=[str(CODE),*flags(p),'--new-window','--skip-welcome','--skip-release-notes','--extensionDevelopmentPath='+str(p/'controller'),str(p/workspace)]
        e={**env(p),'RULES_ACTIVATION_META':str(run/'meta.json'),'RULES_ACTIVATION_PHASE':phase,'RULES_ACTIVATION_EVENTS':str(run/(phase+'.target.jsonl')),'RULES_ACTIVATION_HEARTBEAT':str(p/(phase+'.heartbeat.json'))}
        write(run/(phase+'.before.json'),{'storage':storage(p),'membership':json.load(open(p/'extensions/extensions.json'))})
        started=time.monotonic()
        with (p/(phase+'.stdout')).open('wb')as out,(p/(phase+'.stderr')).open('wb')as err:
            child=subprocess.Popen(argv,env=e,stdout=out,stderr=err,start_new_session=True)
            write(run/(phase+'.process.json'),{'pid':child.pid,'argv':argv,'workspace':workspace});print(json.dumps({'pid':child.pid,'phase':phase}),flush=True)
            code=child.wait()
        write(run/(phase+'.exit.json'),{'exit':code,'seconds':time.monotonic()-started,'afterStorage':storage(p),'membership':json.load(open(p/'extensions/extensions.json')),'codeSha256':sha(CODE),'targetSha256':sha(p/'extensions/rules-study.activation-target-0.0.1/target.cjs')})
        print(json.dumps({'phase':phase,'exit':code}),flush=True);return
    assert args.operation in ['observe','activate','held-ping','disable-workspace','enable-workspace','quit']
    observed=run/(phase+'.observed.json');current=json.load(open(observed));assert current['status']=='ready',current['status']
    sequence=current['handled']+1;control={'phase':phase,'sequence':sequence,'action':args.operation}
    temp=p/'control.tmp';write(temp,control);temp.replace(p/'control.json');deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        if args.operation=='quit'and(run/(phase+'.exit.json')).exists():print((run/(phase+'.exit.json')).read_text());return
        value=json.load(open(observed))
        if value['handled']==sequence and value['status']=='ready':print(json.dumps(value['rows'][-1]));return
        time.sleep(.1)
    print(json.dumps({'observationTimeout':True,'phase':phase,'sequence':sequence,'operation':args.operation,'processHandleNotClassified':True}));raise SystemExit(3)

if __name__=='__main__':main()
