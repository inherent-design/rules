#!/usr/bin/env python3
"""Owned pnpm command/script namespace probe;no installs or global setup."""
from datetime import datetime,timezone
import hashlib,json,os,shlex,signal,subprocess,tempfile,time
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,indent=2)+'\n')


def main():
    cap=ROOT/'applications/evidence'/('pnpm-admission-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));cap.mkdir()
    work=Path(tempfile.mkdtemp(prefix='rules-pnpm-admission-',dir='/private/tmp'))
    for name in['home','tmp','cache','state','data','config','pmhome','project/packages/member']:(work/name).mkdir(parents=True)
    pins=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools'];pnpm=Path(pins['pnpm']['path']);node=Path(pins['node']['path'])
    assert sha(pnpm)==pins['pnpm']['sha256']and sha(node)==pins['node']['sha256']
    project=work/'project';member=project/'packages/member';events=work/'events.jsonl';marker=work/'marker.cjs'
    marker.write_text("const fs=require('fs');const row={label:process.argv[2],args:process.argv.slice(3),cwd:process.cwd(),npmCommand:process.env.npm_command};fs.appendFileSync(process.env.FIXTURE_EVENTS,JSON.stringify(row)+'\\n');console.log(JSON.stringify(row));\n")
    def script(label):return shlex.quote(str(node))+' '+shlex.quote(str(marker))+' '+shlex.quote(label)
    manifest=dict(name='fixture-admission-root',version='1.0.0',private=True,scripts={name:script(label)for name,label in[('tasks','tasks'),('edit','edit'),('xmas','xmas'),('pm','pm'),('fixture-inventory-script','fallback')]})
    write(project/'package.json',manifest);write(member/'package.json',dict(name='fixture-admission-member',version='1.0.0',private=True));(project/'pnpm-workspace.yaml').write_text('packages:\n  - packages/*\n')
    env=dict(PATH=str(node.parent)+':/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),PNPM_HOME=str(work/'pmhome'),XDG_CONFIG_HOME=str(work/'config'),XDG_DATA_HOME=str(work/'data'),XDG_STATE_HOME=str(work/'state'),XDG_CACHE_HOME=str(work/'cache'),CI='true',NO_COLOR='1',npm_config_offline='true',PNPM_CONFIG_OFFLINE='true',FIXTURE_EVENTS=str(events),LANG='C.UTF-8')
    (cap/'probe.py').write_bytes(Path(__file__).read_bytes());(cap/'marker.cjs').write_bytes(marker.read_bytes())
    write(cap/'setup.json',dict(schema=1,work=str(work),project=str(project),member=str(member),producerSha256=sha(cap/'probe.py'),markerSha256=sha(marker),tools={k:pins[k]for k in['node','pnpm']},environment=env,limits=['Full native CLI with owned package scripts and isolated home/state/config. No dependency acquisition,registry,global setup,runtime installation,pipeline execution,or real project touched.','Inherited environment is not forwarded. Offline settings and CI mode selected;this is not a network-denial sandbox.','Only tasks dispatch,explicit scripts,registered placeholders,and a declared fallback script execute. Other feature admission uses help only.']))
    commands=[];edits=[]
    def image():return {str(p.relative_to(project)):dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(project.rglob('*'))if p.is_file()}
    def command(label,cwd,args,expected,program=pnpm):
        before=image();old=events.read_text().splitlines()if events.exists()else[];stdout=cap/(label+'.stdout');stderr=cap/(label+'.stderr');started=time.monotonic()
        with stdout.open('xb')as out,stderr.open('xb')as err:
            child=subprocess.Popen([str(program),*args],cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
            write(cap/'current-process.json',dict(label=label,pid=child.pid,status='running'));timed=False
            try:code=child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                timed=True;child.send_signal(signal.SIGTERM)
                try:code=child.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);code=child.wait()
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        write(cap/'current-process.json',dict(label=label,pid=child.pid,status='terminal',exitCode=code,groupAbsent=absent,timedOut=timed))
        new=events.read_text().splitlines()if events.exists()else[];assert new[:len(old)]==old
        row=dict(label=label,argv=[str(program),*args],cwd=str(cwd),before=before,after=image(),events=[json.loads(s)for s in new[len(old):]],exitCode=code,pid=child.pid,groupAbsent=absent,timedOut=timed,seconds=time.monotonic()-started,streams={k:dict(path=p.name,sha256=sha(p))for k,p in[('stdout',stdout),('stderr',stderr)]})
        commands.append(row);write(cap/'commands.json',commands);print(json.dumps(dict(label=label,exitCode=code,events=len(row['events']),groupAbsent=absent)),flush=True)
        assert code==expected and not timed and absent,(label,code,expected)
        for name in['package.json','pnpm-workspace.yaml','packages/member/package.json']:
            assert before[name]==row['after'][name],(label,'author file changed',name)
    print(json.dumps(dict(capture=str(cap),work=str(work))),flush=True)
    command('pnpm-version',project,['--version'],0)
    command('node-version',project,['--version'],0,program=node)
    for label,cwd,args,code in[
        ('root-tasks-script',project,['tasks','status'],0),
        ('root-forced-tasks',project,['pm','tasks','status'],0),
        ('member-root-shadow',member,['tasks','status'],1),
        ('member-forced-tasks',member,['pm','tasks','status'],0),
        ('explicit-tasks',project,['run','tasks','status'],0),
        ('unsupported-edit',project,['edit'],1),
        ('explicit-edit',project,['run','edit'],0),
        ('unsupported-xmas-arguments',project,['xmas','--fixture-option'],1),
        ('declared-fallback',project,['fixture-inventory-script','--literal'],0),
        ('late-pm-is-script',project,['--dir','.', 'pm','tasks','status'],0),
        ('forced-run-remains-script',project,['pm','run','tasks','status'],0),
        ('builtin-help-before-override',project,['tasks','--help'],0),
        ('explicit-script-help',project,['run','tasks','--help'],0)]:command(label,cwd,args,code)
    old=image();manifest['scripts']['tasks']='';write(project/'package.json',manifest);edits.append(dict(label='empty-tasks-body',before=old,after=image(),scope='Explicit author edit between calls;not a pnpm mutation.'));write(cap/'interventions.json',edits)
    command('empty-tasks-builtin',project,['tasks','status'],0)
    command('empty-root-no-shadow',member,['tasks','status'],0)
    for name in['pipeline','runtime','permissions','with']:command('help-'+name,project,[name,'--help'],0)
    assert sha(pnpm)==pins['pnpm']['sha256']and sha(node)==pins['node']['sha256'];assert sha(marker)==sha(cap/'marker.cjs')
    write(cap/'receipt.json',dict(schema=1,commands=len(commands),allGroupsAbsent=all(c['groupAbsent']for c in commands),finalProject=image(),eventsSha256=sha(events),scope='Fifteen namespace cases,four help-only admission queries,two version reads. No engine,plugin,installer,pipeline/cache/runtime or registry behavior qualified.'))
    (cap/'events.jsonl').write_bytes(events.read_bytes());write(cap/'collection-basis.json',{p.name:sha(p)for p in sorted(cap.iterdir())if p.is_file()})
    print(json.dumps(dict(capture=str(cap),commands=len(commands),allGroupsAbsent=True)),flush=True)


if __name__=='__main__':main()
