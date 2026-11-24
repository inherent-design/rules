#!/usr/bin/env python3
"""Owner-run Modern JS constraints on six generated offline workspaces."""
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
import platform,signal,subprocess,time

ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
RULE=r'''const fs=require('node:fs');
let invocation=0;
module.exports={constraints:({Yarn})=>{
  const pass=++invocation;
  for(const w of Yarn.workspaces()){
    const counter=w.manifest.studyCounter??0;
    fs.appendFileSync('rule-calls.ndjson',JSON.stringify({pass,workspace:w.cwd,counter,license:w.manifest.license??null})+'\n');
    if(MODE==='simple')w.set('license','MIT');
    if(MODE==='mixed'){
      if(w.cwd==='.') {w.set('license','MIT');w.set('license','Apache-2.0');}
      else w.set('license','MIT');
    }
    if(MODE==='chain'&&w.cwd==='.'&&counter<12)w.set('studyCounter',counter+1);
    if(MODE==='late-throw'&&w.cwd==='.'){
      if(counter===1)throw Error('Owned rule fails after earlier pass saved counter1');
      w.set('studyCounter',1);
    }
    if(MODE==='same-object'&&w.cwd==='.'){
      const value={mode:'plain'};w.set('studyObject',value);w.set('studyObject',value);
    }
    if(MODE==='equal-objects'&&w.cwd==='.'){
      w.set('studyObject',{mode:'plain'});w.set('studyObject',{mode:'plain'});
    }
  }
}};
'''


def main():
    pins=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']
    for k in ['node','yarn']:assert sha(Path(pins[k]['path']))==pins[k]['sha256']
    run=ROOT/'applications/evidence'/('yarn-constraints-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));work=run/'work';work.mkdir(parents=True)
    (run/'probe.py').write_bytes(Path(__file__).read_bytes());commands=[];owned=[]
    def command(case,label,args,expected):
        base=work/case;project=base/'project';trace=project/'rule-calls.ndjson'
        def image():return {str(p.relative_to(project)):dict(bytes=p.stat().st_size,sha256=sha(p),text=p.read_text())for p in [project/'package.json',project/'packages/child/package.json',project/'yarn.lock',project/'yarn.config.cjs']if p.exists()}
        before=image();trace_before=trace.read_bytes()if trace.exists()else b'';started=time.monotonic();stem=case+'-'+label
        env=dict(PATH=str(Path(pins['node']['path']).parent)+':/usr/bin:/bin',HOME=str(base/'home'),TMPDIR=str(base/'tmp'),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_STATE_HOME=str(base/'state'),
                 COREPACK_ENABLE_NETWORK='0',YARN_ENABLE_NETWORK='0',YARN_ENABLE_TELEMETRY='0',YARN_ENABLE_HARDENED_MODE='0',YARN_ENABLE_COLORS='0',YARN_ENABLE_PROGRESS_BARS='0',YARN_RC_FILENAME='.fixture-yarnrc.yml',DO_NOT_TRACK='1',LANG='en_US.UTF-8')
        argv=[pins['node']['path'],pins['yarn']['path'],*args]
        with (run/(stem+'.stdout')).open('xb')as out,(run/(stem+'.stderr')).open('xb')as err:
            child=subprocess.Popen(argv,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);owned.append(child)
            (run/'owned-processes.json').write_text(json.dumps([dict(pid=p.pid,retired=p.poll()is not None)for p in owned],indent=2)+'\n')
            timed=False
            try:child.wait(timeout=40)
            except subprocess.TimeoutExpired:timed=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
        try:os.killpg(child.pid,0)
        except ProcessLookupError:absent=True
        else:absent=False
        after_trace=trace.read_bytes()if trace.exists()else b'';assert after_trace.startswith(trace_before)
        row=dict(case=case,label=label,argv=argv,before=before,after=image(),ruleVisits=[json.loads(line)for line in after_trace[len(trace_before):].splitlines()],
                 outcome=dict(exitCode=child.returncode,timedOut=timed,ownedGroupAbsent=absent),seconds=time.monotonic()-started,
                 streams={s:dict(file=stem+'.'+s,sha256=sha(run/(stem+'.'+s)))for s in ['stdout','stderr']})
        commands.append(row);(run/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');print(stem,child.returncode,'passes',len({v['pass']for v in row['ruleVisits']}),flush=True)
        assert not timed and absent and child.returncode==expected,(stem,child.returncode,expected)
        return row
    try:
        for case in ['simple','mixed','chain','late-throw','same-object','equal-objects']:
            base=work/case;project=base/'project'
            for d in ['home','tmp','config','cache','state','global','project/packages/child']:(base/d).mkdir(parents=True)
            assert all(not(p/'.fixture-yarnrc.yml').exists()for p in project.parents)
            (base/'home/.fixture-yarnrc.yml').write_text('{}\n')
            (project/'.fixture-yarnrc.yml').write_text('nodeLinker: node-modules\nenableScripts: false\nenableNetwork: false\nenableGlobalCache: false\ncacheFolder: .yarn/cache\nglobalFolder: '+str(base/'global')+'\n')
            (project/'package.json').write_text(json.dumps(dict(name='constraints-study-'+case,version='1.0.0',private=True,packageManager='yarn@4.19.0',workspaces=['packages/*'],studyCounter=0),indent=2)+'\n')
            (project/'packages/child/package.json').write_text(json.dumps(dict(name='constraints-child',version='1.0.0',private=True),indent=2)+'\n')
            (project/'yarn.config.cjs').write_text('const MODE='+json.dumps(case)+';\n'+RULE)
            command(case,'install',['install','--mode=skip-build'],0)
            command(case,'check',['constraints','--json'],1)
            command(case,'fix',['constraints','--fix','--json'],1 if case in ['mixed','late-throw','equal-objects']else 0)
            if case in ['simple','same-object']:command(case,'recheck',['constraints','--json'],0)
            if case=='chain':
                command(case,'post-cap-check',['constraints','--json'],1)
                command(case,'finish-fix',['constraints','--fix','--json'],0)
                command(case,'recheck',['constraints','--json'],0)
        receipt=dict(schema=1,tools={k:pins[k]for k in ['node','yarn']},platform=platform.platform(),architecture=platform.machine(),producerSha256=sha(run/'probe.py'),commands=len(commands),
                     allOwnedGroupsAbsent=all(c['outcome']['ownedGroupAbsent']for c in commands),allocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),
                     limits=['Only six generated private root/child projects;network disabled,dependency-free manifests,no fetched package or tool,no source/product edits.',
                             'Owned JS constraint callbacks deliberately log their input to rule-calls.ndjson;check is not claimed to be arbitrary-code side-effect-free.',
                             'Captured manifests/lock/configuration and per-pass calls,not process-wide disk tracing,simultaneous editors or general resolver/dependency compatibility.'])
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    finally:
        for child in owned:
            if child.poll()is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
        (run/'owned-processes.json').write_text(json.dumps([dict(pid=p.pid,retired=p.poll()is not None)for p in owned],indent=2)+'\n')
        print('capture',run,flush=True)


if __name__=='__main__':main()
