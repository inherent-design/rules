#!/usr/bin/env python3
"""Continue a retired private fixture; never restart or edit its original producer."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('primary',type=Path);primary=p.parse_args().primary.resolve()
    assert primary==ROOT/'applications/evidence/js-patches-20261124T173857262805Z'
    trace=json.loads((primary/'trace.json').read_text());assert len(trace)==36 and trace[-1]['app']=='yarn' and trace[-1]['case']=='unplug' and trace[-1]['outcome']==dict(exitCode=1,timedOut=False)
    pins=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']
    for name in ['node','pnpm','yarn']:assert sha(Path(pins[name]['path']))==pins[name]['sha256']
    for row in trace:
        for stream in ['stdout','stderr']:assert sha(primary/(row['app']+'-'+row['case']+'.'+stream))==row['observed'][stream+'Sha256']
        for frame in [row['observed']['before'],row['observed']['after']]:
            for value in frame['files'].values():assert sha(primary/value['captured'])==value['sha256']
    run=ROOT/'applications/evidence'/('js-patches-followup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir();(run/'files').mkdir();(run/'probe.py').write_bytes(PRODUCER)
    rows=[];edits=[]
    for manager in ['yarn','pnpm']:
        base=primary/'work'/manager;project=base/'project';manifest=project/'package.json'
        env=dict(PATH=str(Path(pins['node']['path']).parent)+':/usr/bin:/bin',HOME=str(base/'home'),TMPDIR=str(base/'tmp'),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),LANG='en_US.UTF-8',COREPACK_ENABLE_NETWORK='0',YARN_ENABLE_TELEMETRY='0',YARN_ENABLE_IMMUTABLE_INSTALLS='false',DO_NOT_TRACK='1',MISE_SKIP_RESHIM='1',NPM_CONFIG_USERCONFIG=str(base/'config/user.npmrc'),NPM_CONFIG_GLOBALCONFIG=str(base/'config/global.npmrc'),NPM_CONFIG_CACHE=str(base/'cache/npm'),NPM_CONFIG_REGISTRY='http://127.0.0.1:9')
        prefix=[pins['pnpm']['path']] if manager=='pnpm' else [pins['node']['path'],pins['yarn']['path']]
        common=['--store-dir',str(base/'store'),'--state-dir',str(base/'state')] if manager=='pnpm' else []
        mutable=['install','--offline','--ignore-scripts','--no-frozen-lockfile'] if manager=='pnpm' else ['install']

        def retain(p):
            data=p.read_bytes();assert len(data)<200_000
            digest=hashlib.sha256(data).hexdigest();dest=run/'files'/(digest+'.txt');dest.write_bytes(data)
            return dict(sha256=digest,bytes=len(data),captured=str(dest.relative_to(run)))

        def image():
            files={}
            for relative in ['package.json','pnpm-workspace.yaml','pnpm-lock.yaml','yarn.lock','.npmrc','.yarnrc.yml']:
                q=project/relative
                if q.is_file():files[relative]=retain(q)
            for directory in ['patches','.yarn/patches']:
                for q in sorted((project/directory).glob('*.patch')):files[str(q.relative_to(project))]=retain(q)
            q=project/'node_modules/fixture-patch/index.js';installed=None
            if q.is_file():
                assert q.resolve().is_relative_to(base);installed=dict(path=str(q.resolve()),content=q.read_text(),**retain(q))
            return dict(files=files,installed=installed)

        def observed_equal(a,b):
            def clean(x):
                if isinstance(x,dict):return {k:clean(v) for k,v in x.items() if k!='captured'}
                return x
            return clean(a)==clean(b)

        prior=next(r for r in reversed(trace) if r['app']==manager)['observed']['after'];assert observed_equal(image(),prior),'Private fixture changed; do not continue.'

        def command(label,args,expected=None):
            before=image();child=subprocess.Popen(args,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);timed_out=False
            try:out,err=child.communicate(timeout=60)
            except subprocess.TimeoutExpired:
                timed_out=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
            stem=manager+'-'+label
            for stream,data in [('stdout',out),('stderr',err)]:(run/(stem+'.'+stream)).write_bytes(data)
            row=dict(app=manager,case=label,argv=args,observed=dict(before=before,after=image(),stdoutSha256=hashlib.sha256(out).hexdigest(),stderrSha256=hashlib.sha256(err).hexdigest()),outcome=dict(exitCode=child.returncode,timedOut=timed_out));rows.append(row)
            (run/'trace.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(dict(app=manager,case=label,exitCode=child.returncode)),flush=True)
            assert not timed_out and (expected is None or child.returncode==expected),'Keep failed continuation; do not repeat blindly.'
            return row

        def runtime(label):command(label+'-runtime',[pins['node']['path'],'-e','try{console.log(JSON.stringify({value:require("fixture-patch"),path:require.resolve("fixture-patch")}))}catch(e){console.log(JSON.stringify({error:e.code}))}'],0)

        if manager=='yarn':
            runtime('after-unplug-refusal')
            before=image();value=json.loads(manifest.read_text());original=next(r for r in trace if r['app']==manager and r['case']=='initial-install')['observed']['before']['files']['package.json'];source=json.loads((primary/original['captured']).read_text());value['dependencies']['fixture-patch']=source['dependencies']['fixture-patch'];manifest.write_text(json.dumps(value,indent=2)+'\n');edits.append(dict(app=manager,action='restore-unpatched-dependency-reference',before=before,after=image()))
            runtime('reference-restored-before-install');command('install-unpatched',prefix+mutable+common,0);runtime('install-unpatched')
        else:
            # Restore only authored recipe inputs from retained successful evidence.
            # No lock, modules, cache or state file is fabricated by the harness.
            before=image();basis=next(r for r in trace if r['app']==manager and r['case']=='install-patch')['observed']['after']
            for relative in ['pnpm-workspace.yaml','patches/fixture-patch.patch']:
                target=project/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((primary/basis['files'][relative]['captured']).read_bytes())
            patch=project/'patches/fixture-patch.patch';good=patch.read_bytes();patch.write_bytes(good.replace(b'-module.exports = "base";',b'-module.exports = "absent-context";'));edits.append(dict(app=manager,action='restore-authored-recipe-with-invalid-hunk',before=before,after=image()))
            command('bad-install',prefix+mutable+common,1);runtime('bad-install')
            command('retry-same-bad-install',prefix+mutable+common);runtime('retry-same-bad-install')
            before=image();patch.write_bytes(good);edits.append(dict(app=manager,action='restore-valid-patch',before=before,after=image()));command('restore-valid',prefix+mutable+common,0);runtime('restore-valid')
    receipt=dict(schema=1,producerSha256=hashlib.sha256(PRODUCER).hexdigest(),primary=str(primary.relative_to(ROOT)),primaryTraceSha256=sha(primary/'trace.json'),primaryProducerSha256=sha(primary/'probe.py'),commands=len(rows),ownerEdits=edits,tools={n:pins[n] for n in ['node','pnpm','yarn']},platform=platform.platform(),allOwnedProcessesRetired=True,scope='Explicit continuation of verified private retired fixture. Finishes Yarn unpatch and probes pnpm same-invalid-hunk retry. Actual command results and file/runtime observations,not native rollback or full store integrity qualification.')
    (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(run=str(run),commands=len(rows)),indent=2))


if __name__=='__main__':main()
