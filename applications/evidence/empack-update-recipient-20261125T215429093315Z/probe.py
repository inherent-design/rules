"""Bounded released-CLI author update flow against public Modrinth metadata."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[3]
BINARY=Path('/Users/zer0cell/.local/bin/empack')
EXPECTED='99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')


def image(root):
    values={}
    for directory,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            p=Path(directory)/name;s=p.lstat();rel=p.relative_to(root).as_posix()
            if stat.S_ISLNK(s.st_mode):values[rel]=dict(kind='link',target=os.readlink(p),mode=s.st_mode)
            elif stat.S_ISDIR(s.st_mode):values[rel]=dict(kind='directory',mode=s.st_mode)
            elif stat.S_ISREG(s.st_mode):
                raw=p.read_bytes();item=dict(kind='file',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),sha512=hashlib.sha512(raw).hexdigest(),mode=s.st_mode,mtimeNs=s.st_mtime_ns)
                if p.name in ['empack.yml','empack.lock','empack.bindings.yml']:item['bytesHex']=raw.hex()
                values[rel]=item
            else:raise AssertionError('Unexpected fixture entry')
    return values


def main():
    assert sha(BINARY)==EXPECTED
    preread=ROOT/'.build/selection-handoff-preread'
    context=json.loads((preread/'receipt.json').read_text());versions=json.loads((preread/'versions.json').read_text());project_metadata=json.loads((preread/'project.json').read_text())
    for name,row in context['requests'].items():assert sha(preread/(name+'.json'))==row['sha256']
    choices=context['eligibleVersions'];assert len(choices)>=2
    old,new=choices[0],choices[-1]
    assert old['id']!=new['id'] and project_metadata['id']==context['project']=='uXXizFIs'
    for value in [old,new]:
        record=next(r for r in versions if r['id']==value['id'])
        assert record['project_id']==context['project'] and not record['dependencies'] and value['file'] in record['files']
    run=ROOT/'applications/evidence'/('empack-update-flow-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir();(run/'probe.py').write_bytes(Path(__file__).read_bytes())
    work=Path(tempfile.mkdtemp(prefix='rules-empack-update-flow-',dir='/private/tmp'))
    for name in ['project','state','cache','tmp']:(work/name).mkdir(mode=0o700)
    project=work/'project';(project/'pack').mkdir()
    for name in ['project','versions']:(work/('api-'+name+'.json')).write_bytes((preread/(name+'.json')).read_bytes())
    metadata=dict(requests=context['requests'],project=context['project'],old=old,target=new,scope='Independent anonymous public API sampling before native execution; not instrumented native responses. Full sampled bodies retained privately.')
    write(run/'independent-metadata.json',metadata)
    author="""schema: 6
pack: {id: rules.selection.handoff, name: Rules selection handoff, version: '1', authors: [Fixture]}
runtime: {minecraft: '1.21.1', loader: {kind: fabric, pin: '0.16.0'}, java: {preferred: 21}}
dependencies:
  ferrite:
    source: modrinth:PROJECT
    pin: 'OLD'
    type: mod
build:
  default: [client]
  profiles:
    client: {target: prism, delivery: bundled, environment: client}
""".replace('PROJECT',context['project']).replace('OLD',old['id'])
    (project/'empack.yml').write_text(author)
    env=dict(PATH=os.environ['PATH'],LANG='en_US.UTF-8',TMPDIR=str(work/'tmp'),NO_COLOR='1',DO_NOT_TRACK='1')
    write(run/'setup.json',dict(schema=1,work=str(work),binary=str(BINARY),binarySha256=EXPECTED,producerSha256=sha(run/'probe.py'),author=author,metadataSha256=sha(run/'independent-metadata.json'),privateApiBodySha256={name:sha(work/('api-'+name+'.json')) for name in ['project','versions']},environmentKeys=sorted(env),scope='Disposable own author project/state/cache; public API/CDN reads and two tiny selected mod artifacts only. No engine build,Java,game,personal pack,channel,GitHub publication or host installation changes. Explicit state/cache roots select private stores.'))
    base=[str(BINARY),'--state-dir',str(work/'state'),'--cache-dir',str(work/'cache'),'--workdir',str(project),'--net-timeout','45','--color','never','--yes']
    rows=[]
    def command(label,args,preview=False,structured=False):
        before=image(project);began=time.monotonic();child=subprocess.Popen(base+args,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timed=False
        print(json.dumps(dict(start=label,pid=child.pid)),flush=True)
        try:out,err=child.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
        (run/(label+'.stdout')).write_bytes(out);(run/(label+'.stderr')).write_bytes(err)
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        after=image(project)
        row=dict(id=label,argv=base+args,pid=child.pid,exitCode=child.returncode,timedOut=timed,groupAbsent=absent,seconds=time.monotonic()-began,before=before,after=after,streams={name:sha(run/(label+'.'+name)) for name in ['stdout','stderr']})
        rows.append(row);write(run/'commands.json',rows)
        print(json.dumps(dict(finish=label,exitCode=child.returncode,seconds=row['seconds'])),flush=True)
        assert not timed and absent and child.returncode==0,'Retain original failure before investigating; no automatic rerun.'
        if preview:assert before==after,'Preview changed captured author entries'
        if structured:
            value=json.loads(out);write(run/(label+'.json'),value)
        return after
    try:
        command('sync-old',['sync','--materialize'])
        command('inspect-old',['manifest','diff','--json'],True,True)
        command('held-old',['update','--all','--json','--quiet'],True,True)
        command('unpin',['unpin','ferrite'])
        command('inspect-unpinned',['manifest','diff','--json'],True,True)
        command('automatic-preview',['update','--all','--json','--quiet'],True,True)
        command('exact-preview',['update','--all','--pin','ferrite='+new['id'],'--json','--quiet'],True,True)
        command('apply-exact',['update','--all','--pin','ferrite='+new['id'],'--apply','--quiet'])
        command('inspect-new',['manifest','diff','--json'],True,True)
        command('held-new',['update','--all','--json','--quiet'],True,True)
        assert sha(BINARY)==EXPECTED
        write(run/'receipt.json',dict(schema=1,complete=True,commands=len(rows),allRecordedGroupsAbsent=all(r['groupAbsent'] for r in rows),producerSha256=sha(run/'probe.py'),binarySha256=EXPECTED,setupSha256=sha(run/'setup.json'),metadataSha256=sha(run/'independent-metadata.json'),allocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),scope='Ten released-CLI commands against live public provider data in own one-root fixture. Before/after author snapshots and streams retained; compatibility, payload identity, expected plan effects and actual changes need independent review. No world/runtime/consumer launch or broad graph/platform qualification.'))
        print(json.dumps(dict(run=str(run),complete=True,commands=len(rows))),flush=True)
    except BaseException as error:
        write(run/'failure.json',dict(error=str(error),commands=len(rows),allRecordedGroupsAbsent=all(r['groupAbsent'] for r in rows)));print(json.dumps(dict(run=str(run),complete=False)),flush=True);raise


if __name__=='__main__':main()
