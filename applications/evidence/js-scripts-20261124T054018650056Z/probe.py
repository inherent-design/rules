#!/usr/bin/env python3
"""Owner-run hook-policy fixtures: generated local code, private roots, no network."""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def main():
    pins=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']
    for name in ['node','npm','pnpm','yarn']:assert sha(Path(pins[name]['path']))==pins[name]['sha256'],name
    run=ROOT/'applications/evidence'/('js-scripts-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir();(run/'probe.py').write_bytes(PRODUCER)
    work=Path(tempfile.mkdtemp(prefix='rules-js-scripts-',dir='/private/tmp'))
    for p in [work,*work.parents]:
        assert not any((p/name).exists() for name in ['.npmrc','.yarnrc','.yarnrc.yml','pnpm-workspace.yaml']),p
    archives=work/'archives';archives.mkdir()
    hook='''const fs=require('fs');
const [scope,phase]=process.argv.slice(2);
fs.appendFileSync(process.env.FIXTURE_EFFECT_FILE,JSON.stringify({scope,phase,cwd:process.cwd()})+'\\n');
if(process.env.FIXTURE_FAIL_STAGE===scope+':'+phase)process.exit(7);
'''
    package={'name':'fixture-hook','version':'1.0.0','main':'index.js',
        'scripts':{phase:'node hook.cjs dependency '+phase for phase in ['preinstall','install','postinstall']}}
    archive=archives/'fixture-hook-1.0.0.tgz'
    with tarfile.open(archive,'w:gz') as tar:
        for name,data in [('package.json',json.dumps(package)),('hook.cjs',hook),('index.js','module.exports="fixture-hook-1.0.0";\n')]:
            encoded=data.encode();entry=tarfile.TarInfo('package/'+name);entry.size=len(encoded);entry.mode=0o644;entry.mtime=0
            tar.addfile(entry,io.BytesIO(encoded))
    profiles=[('unreviewed',None,False,False,False),('deny',False,False,False,False),
        ('allow',True,False,False,False),('disabled-with-allow',True,True,False,False),
        ('broad-allow-with-deny',False,False,True,False),('allowed-failure',True,False,False,True),
        ('root-disabled',None,True,False,False)]
    rows=[];cases=[]
    try:
        for manager in ['npm','pnpm','yarn']:
            for label,approval,disabled,broad,fail in profiles:
                base=work/(manager+'-'+label);project=base/'project'
                for p in [project,base/'home',base/'cache',base/'config',base/'tmp']:p.mkdir(parents=True)
                for name in ['user.npmrc','global.npmrc']:(base/'config'/name).write_text('')
                effects=base/'effects.jsonl';manifest=project/'package.json'
                contents={'name':'fixture-project','private':True}
                root_case=label=='root-disabled'
                if root_case:
                    contents['scripts']={phase:'node hook.cjs root '+phase for phase in ['preinstall','install','postinstall','preprobe','probe','postprobe']}
                    (project/'hook.cjs').write_text(hook)
                else:contents['dependencies']={'fixture-hook':'file:'+str(archive)}
                source_key='file:'+str(archive)
                build_key='fixture-hook@file:../../archives/fixture-hook-1.0.0.tgz'
                if manager=='npm' and approval is not None:contents['allowScripts']={source_key:approval}
                if manager=='yarn' and approval is not None:contents['dependenciesMeta']={'fixture-hook':{'built':approval}}
                manifest.write_text(json.dumps(contents,indent=2)+'\n')
                if manager=='pnpm':
                    values={} if approval is None else {build_key:approval}
                    (project/'pnpm-workspace.yaml').write_text('nodeLinker: isolated\nenableGlobalVirtualStore: false\nallowBuilds: '+json.dumps(values)+'\ndangerouslyAllowAllBuilds: '+str(broad).lower()+'\n')
                if manager=='yarn':
                    (project/'.yarnrc.yml').write_text('nodeLinker: node-modules\nenableGlobalCache: false\nenableNetwork: false\nenableTelemetry: false\nenableScripts: '+str(not disabled).lower()+'\n')
                env={'PATH':str(Path(pins['node']['path']).parent)+':/usr/bin:/bin','HOME':str(base/'home'),
                    'XDG_CONFIG_HOME':str(base/'config'),'XDG_CACHE_HOME':str(base/'cache'),'TMPDIR':str(base/'tmp'),
                    'NPM_CONFIG_USERCONFIG':str(base/'config/user.npmrc'),'NPM_CONFIG_GLOBALCONFIG':str(base/'config/global.npmrc'),
                    'NPM_CONFIG_CACHE':str(base/'cache/npm'),'NPM_CONFIG_REGISTRY':'http://127.0.0.1:9',
                    'LANG':'en_US.UTF-8','COREPACK_ENABLE_NETWORK':'0','YARN_ENABLE_TELEMETRY':'0',
                    'YARN_ENABLE_IMMUTABLE_INSTALLS':'false','DO_NOT_TRACK':'1','MISE_SKIP_RESHIM':'1',
                    'NO_COLOR':'1','NO_UPDATE_NOTIFIER':'1','FIXTURE_EFFECT_FILE':str(effects)}
                if fail:env['FIXTURE_FAIL_STAGE']='dependency:postinstall'
                if manager=='npm':
                    prefix=[pins['npm']['path']];install=['install','--offline','--no-audit','--no-fund']
                    if disabled:install+=['--ignore-scripts']
                    if broad:install+=['--dangerously-allow-all-scripts']
                    lock=project/'package-lock.json'
                elif manager=='pnpm':
                    prefix=[pins['pnpm']['path']];install=['install','--offline','--store-dir',str(base/'store')]
                    if disabled:install+=['--ignore-scripts']
                    lock=project/'pnpm-lock.yaml'
                else:
                    prefix=[pins['node']['path'],pins['yarn']['path']];install=['install'];lock=project/'yarn.lock'

                def state():
                    return {'manifestSha256':sha(manifest),'lockSha256':sha(lock),
                        'packageEntryExists':(project/'node_modules/fixture-hook/index.js').is_file(),
                        'effectsSha256':sha(effects),'effects':[json.loads(line) for line in effects.read_text().splitlines()] if effects.exists() else []}

                def command(operation,argv):
                    before=state();began=time.monotonic()
                    process=subprocess.Popen(argv,cwd=project,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
                    timed_out=False
                    try:stdout,stderr=process.communicate(input=b'',timeout=90)
                    except subprocess.TimeoutExpired:
                        timed_out=True
                        try:os.killpg(process.pid,signal.SIGKILL)
                        except ProcessLookupError:pass
                        stdout,stderr=process.communicate()
                    stem=manager+'-'+label+'-'+operation
                    (run/(stem+'.stdout')).write_bytes(stdout);(run/(stem+'.stderr')).write_bytes(stderr)
                    row={'app':manager,'case':label,'operation':operation,'argv':argv,
                        'observed':{'before':before,'after':state(),'seconds':time.monotonic()-began,
                            'stdoutSha256':hashlib.sha256(stdout).hexdigest(),'stderrSha256':hashlib.sha256(stderr).hexdigest()},
                        'outcome':{'exitCode':process.returncode,'timedOut':timed_out}}
                    rows.append(row);(run/'trace.json').write_text(json.dumps(rows,indent=2)+'\n')
                    if timed_out:raise RuntimeError('Owned command group timed out and was killed; preserve records before any retry.')
                    return row

                configuration={name:(project/name).read_text() for name in ['package.json','pnpm-workspace.yaml','.yarnrc.yml'] if(project/name).exists()}
                case={'app':manager,'id':label,'approval':approval,'disabled':disabled,'broad':broad,'fail':fail,
                    'scope':'root' if root_case else 'dependency','configurationBefore':configuration}
                installed=command('install',prefix+install)
                case['installExit']=installed['outcome']['exitCode']
                if root_case:
                    run_args=(['--ignore-scripts'] if manager in ['npm','pnpm'] else [])+['run','probe']
                    command('explicit-root',prefix+run_args)
                else:
                    code='try { console.log(JSON.stringify({available:true,value:require("fixture-hook"),path:require.resolve("fixture-hook")})) } catch(e) { console.log(JSON.stringify({available:false,error:e.code})) }'
                    command('inspect-module',[pins['node']['path'],'-e',code])
                case['configurationAfter']={name:(project/name).read_text() for name in configuration}
                for name in ['package.json','package-lock.json','pnpm-lock.yaml','pnpm-workspace.yaml','.yarnrc.yml','yarn.lock']:
                    if(project/name).is_file():shutil.copyfile(project/name,run/(manager+'-'+label+'-'+name))
                cases.append(case);(run/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
        receipt={'schema':1,'producerSha256':hashlib.sha256(PRODUCER).hexdigest(),
            'tools':{name:pins[name]for name in ['node','npm','pnpm','yarn']},'platform':platform.platform(),'architecture':platform.machine(),
            'archive':{'name':archive.name,'sha256':sha(archive),'bytes':archive.stat().st_size,'manifest':package,'hookSha256':hashlib.sha256(hook.encode()).hexdigest()},
            'cases':len(cases),'commands':len(rows),'originalWork':str(work),
            'scope':'Generated local tarball and root hooks write only private fixture marker files. No third-party hook, network, account, user project or global tool change.',
            'limits':['Unix process sessions and private configuration; not cross-platform execution or a script sandbox.',
                'Source approval keys, disabled settings and broad overrides have application-specific meaning; root scripts and dependency hooks are measured separately.',
                'Package/cache/tree side effects are not presumed rolled back on refusal or failure; only recorded selected state is measured.']}
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps({'run':str(run),'cases':len(cases),'commands':len(rows),
            'installSummary':[{'app':r['app'],'case':r['case'],'exit':r['outcome']['exitCode'],'effects':[e['scope']+':'+e['phase']for e in r['observed']['after']['effects']],'packageEntry':r['observed']['after']['packageEntryExists']}for r in rows if r['operation']=='install']},indent=2))
    finally:
        shutil.move(str(work),str(run/'work'))


if __name__=='__main__':main()
