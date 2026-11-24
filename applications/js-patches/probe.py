#!/usr/bin/env python3
"""Owner-run single-package patch lifecycle; private roots and local content only."""
from datetime import datetime,timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import tarfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PRODUCER=Path(__file__).read_bytes();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
PACKAGE='fixture-patch';BASE='module.exports = "base";\n';PATCHED='module.exports = "patched";\n'


def main():
    pins=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']
    for name in ['node','pnpm','yarn']:assert sha(Path(pins[name]['path']))==pins[name]['sha256']
    run=ROOT/'applications/evidence'/('js-patches-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));work=run/'work'
    work.mkdir(parents=True);(run/'probe.py').write_bytes(PRODUCER);(run/'files').mkdir()
    archive=work/'fixture-patch-1.0.0.tgz'
    with tarfile.open(archive,'w:gz') as tar:
        for name,text in [('package.json',json.dumps(dict(name=PACKAGE,version='1.0.0',main='index.js'))),('index.js',BASE)]:
            data=text.encode();info=tarfile.TarInfo('package/'+name);info.size=len(data);info.mode=0o644;info.mtime=0;tar.addfile(info,io.BytesIO(data))
    original_archive=sha(archive);rows=[];edits=[];prepared=[]
    try:
        for manager in ['pnpm','yarn']:
            base=work/manager;project=base/'project'
            for name in ['project','home','tmp','config','cache']:(base/name).mkdir(parents=True)
            manifest=project/'package.json';original=dict(name='patch-lifecycle',private=True,dependencies={PACKAGE:'file:'+str(archive)})
            manifest.write_text(json.dumps(original,indent=2)+'\n')
            if manager=='pnpm':
                (project/'.npmrc').write_text('offline=true\nignore-scripts=true\nregistry=http://127.0.0.1:9\n')
                prefix=[pins['pnpm']['path']];common=['--store-dir',str(base/'store'),'--state-dir',str(base/'state')]
                mutable=['install','--offline','--ignore-scripts','--no-frozen-lockfile'];frozen=['install','--offline','--ignore-scripts','--frozen-lockfile']
            else:
                (project/'.yarnrc.yml').write_text('nodeLinker: node-modules\nenableGlobalCache: false\nenableNetwork: false\nenableTelemetry: false\nenableScripts: false\n')
                prefix=[pins['node']['path'],pins['yarn']['path']];common=[];mutable=['install'];frozen=['install','--immutable']
            env=dict(PATH=str(Path(pins['node']['path']).parent)+':/usr/bin:/bin',HOME=str(base/'home'),TMPDIR=str(base/'tmp'),
                XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),LANG='en_US.UTF-8',
                COREPACK_ENABLE_NETWORK='0',YARN_ENABLE_TELEMETRY='0',YARN_ENABLE_IMMUTABLE_INSTALLS='false',DO_NOT_TRACK='1',MISE_SKIP_RESHIM='1',
                NPM_CONFIG_USERCONFIG=str(base/'config/user.npmrc'),NPM_CONFIG_GLOBALCONFIG=str(base/'config/global.npmrc'),NPM_CONFIG_CACHE=str(base/'cache/npm'),NPM_CONFIG_REGISTRY='http://127.0.0.1:9')
            for name in ['user.npmrc','global.npmrc']:(base/'config'/name).write_text('')

            def retain(p):
                data=p.read_bytes();assert len(data)<200_000
                identity=hashlib.sha256(data).hexdigest();dest=run/'files'/(identity+'.txt')
                if dest.exists():assert dest.read_bytes()==data
                else:dest.write_bytes(data)
                return dict(sha256=identity,bytes=len(data),captured=str(dest.relative_to(run)))

            def image():
                files={}
                for relative in ['package.json','pnpm-workspace.yaml','pnpm-lock.yaml','yarn.lock','.npmrc','.yarnrc.yml']:
                    p=project/relative
                    if p.is_file():files[relative]=retain(p)
                for directory in ['patches','.yarn/patches']:
                    for p in sorted((project/directory).glob('*.patch')):files[str(p.relative_to(project))]=retain(p)
                p=project/'node_modules'/PACKAGE/'index.js';payload=None
                if p.is_file():
                    assert p.resolve().is_relative_to(base)
                    payload=dict(path=str(p.resolve()),content=p.read_text(),**retain(p))
                return dict(files=files,installed=payload)

            def command(label,args,expected=None):
                before=image();child=subprocess.Popen(args,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
                timed_out=False
                try:out,err=child.communicate(timeout=60)
                except subprocess.TimeoutExpired:
                    timed_out=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
                stem=manager+'-'+label
                for stream,data in [('stdout',out),('stderr',err)]:(run/(stem+'.'+stream)).write_bytes(data)
                rows.append(dict(app=manager,case=label,argv=args,observed=dict(before=before,after=image(),stdoutSha256=hashlib.sha256(out).hexdigest(),stderrSha256=hashlib.sha256(err).hexdigest()),outcome=dict(exitCode=child.returncode,timedOut=timed_out)))
                (run/'trace.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(dict(app=manager,case=label,exitCode=child.returncode)),flush=True)
                assert not timed_out and (expected is None or child.returncode==expected),'Retain unexpected outcome before changing the fixture.'
                return out,child.returncode

            def runtime(label):
                command(label+'-runtime',[pins['node']['path'],'-e','try{console.log(JSON.stringify({value:require("fixture-patch"),path:require.resolve("fixture-patch")}))}catch(e){console.log(JSON.stringify({error:e.code}))}'],expected=0)

            def prepare(label,extra):
                if manager=='pnpm':
                    edit=project/('edit-'+label);out,_=command(label,prefix+['patch',PACKAGE,'--edit-dir',str(edit)]+extra+common,0)
                else:
                    out,_=command(label,prefix+['patch',PACKAGE,'--json']+extra,0)
                    values=[json.loads(line) for line in out.splitlines()]
                    candidates=[v['path'] for v in values if 'path' in v];assert len(candidates)==1;edit=Path(candidates[0])
                assert edit.resolve().is_relative_to(base) and (edit/'index.js').is_file()
                prepared.append(dict(app=manager,case=label,path=str(edit),content=(edit/'index.js').read_text(),indexSha256=sha(edit/'index.js')))
                (run/'prepared.json').write_text(json.dumps(prepared,indent=2)+'\n');return edit

            command('initial-install',prefix+mutable+common,0);runtime('initial-install')
            edit=prepare('prepare',[]);assert (edit/'index.js').read_text()==BASE
            (edit/'index.js').write_text(PATCHED);edits.append(dict(app=manager,action='edit-prepared-index',path=str(edit/'index.js'),before=BASE,after=PATCHED))
            command('commit',prefix+(['patch-commit',str(edit)] if manager=='pnpm' else ['patch-commit','--save',str(edit)])+common,0);runtime('commit')
            command('frozen-after-commit',prefix+frozen+common);runtime('frozen-after-commit')
            command('install-patch',prefix+mutable+common,0);runtime('install-patch')
            assert (project/'node_modules'/PACKAGE/'index.js').read_text()==PATCHED
            prepare('prepare-default',[])
            prepare('prepare-alternative',['--ignore-existing'] if manager=='pnpm' else ['--update'])
            patch_files=list((project/('patches' if manager=='pnpm' else '.yarn/patches')).glob('*.patch'));assert len(patch_files)==1
            patch=patch_files[0];good=patch.read_bytes();assert b'-module.exports = "base";' in good
            bad=good.replace(b'-module.exports = "base";',b'-module.exports = "absent-context";')
            patch.write_bytes(bad);edits.append(dict(app=manager,action='make-hunk-inapplicable',path=str(patch),beforeSha256=hashlib.sha256(good).hexdigest(),afterSha256=sha(patch)))
            command('invalid-apply',prefix+mutable+common);runtime('invalid-apply')
            patch.write_bytes(good);edits.append(dict(app=manager,action='restore-patch',path=str(patch),afterSha256=sha(patch)))
            command('restore-valid',prefix+mutable+common,0);runtime('restore-valid')
            if manager=='pnpm':
                command('remove-missing-version-key',prefix+['patch-remove',PACKAGE+'@1.0.0']+common,1)
                command('remove-patch',prefix+['patch-remove',PACKAGE]+common,0)
            else:
                command('unplug',prefix+['unplug',PACKAGE],0);runtime('unplug')
                before=sha(manifest);value=json.loads(manifest.read_text());value['dependencies'][PACKAGE]=original['dependencies'][PACKAGE];manifest.write_text(json.dumps(value,indent=2)+'\n');edits.append(dict(app=manager,action='restore-original-dependency-reference',beforeSha256=before,afterSha256=sha(manifest)))
            runtime('remove-recipe-before-install')
            command('install-unpatched',prefix+mutable+common,0);runtime('install-unpatched')
        assert sha(archive)==original_archive
        for name in ['node','pnpm','yarn']:assert sha(Path(pins[name]['path']))==pins[name]['sha256']
        receipt=dict(schema=1,producerSha256=hashlib.sha256(PRODUCER).hexdigest(),tools={n:pins[n] for n in ['node','pnpm','yarn']},commands=len(rows),ownerEdits=edits,
            archiveSha256=original_archive,platform=platform.platform(),allOwnedProcessesRetired=True,
            allocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),
            scope='Single generated exact local tarball,one ordinary text hunk,direct root,node-modules linker,private config/cache/store,disabled scripts and offline/disabled network. No registry,workspaces,peers,binary patches,security/concurrency/interruption or general patch semantics.')
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(run=str(run),commands=len(rows),allocatedKiB=receipt['allocatedKiB']),indent=2))
    except BaseException as error:
        (run/'failure.json').write_text(json.dumps(dict(error=str(error),commands=len(rows),ownerEdits=edits),indent=2)+'\n');raise


if __name__=='__main__':main()
