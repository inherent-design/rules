"""Owner-run installed CLI observed-file adoption. No engine build or desktop."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[3]
BINARY = Path('/Users/zer0cell/.local/bin/empack')
EXPECTED = '99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
REV = '0b4462e3032b4f09230b15329722eabefb7f574c'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
write = lambda p, v: p.write_text(json.dumps(v, indent=2) + '\n')


def pack(value):
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w', compression=zipfile.ZIP_STORED) as z:
        for name, data in [('pack.mcmeta', json.dumps({'pack': {'pack_format': 34, 'description': 'Owned adoption fixture ' + value}})), ('assets/rules/textures/marker.txt', value)]:
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0));z.writestr(info, data.encode())
    return b.getvalue()


def main():
    assert sha(BINARY) == EXPECTED
    helper = ROOT / 'applications/empack/update-flow/probe.py'
    spec = importlib.util.spec_from_file_location('snapshot_only', helper)
    prior = importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    run = ROOT / 'applications/evidence' / ('empack-adoption-flow-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir();(run / 'probe.py').write_bytes(Path(__file__).read_bytes())
    work = Path(tempfile.mkdtemp(prefix='rules-empack-adoption-', dir='/private/tmp'))
    for n in ['projects', 'state', 'cache', 'tmp']:(work / n).mkdir(mode=0o700)
    source_paths = ['crates/empack-lib/src/application/engine_host/cli/update.rs', 'crates/empack-lib/src/application/engine_host/cli/update/initial.rs',
                    'crates/empack-lib/src/application/engine_host/dependencies.rs', 'crates/empack-lib/src/engine/addition/direct.rs',
                    'crates/empack-lib/src/engine/addition/native/adoption.rs']
    sources = []
    repo = ROOT.parent / 'empack'
    for n in source_paths:
        raw = subprocess.check_output(['git', '-C', str(repo), 'show', REV + ':' + n])
        assert (repo / n).read_bytes() == raw
        sources.append(dict(path=n,revision=REV,sha256=hashlib.sha256(raw).hexdigest(),gitBlob=hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()))
    payloads = {v: pack(v) for v in ['A', 'B']}
    for key, raw in payloads.items():(run / ('payload-' + key + '.zip')).write_bytes(raw)
    author = dict(schema=6,pack=dict(id='rules.adoption.CASE',name='Rules adoption CASE',version='one',authors=['Fixture']),
                  runtime=dict(minecraft='1.21.1',loader='vanilla',java=dict(preferred=21)),dependencies={})
    placement = [dict(destination='resourcepacks/observed.zip',layer='common',environment=dict(client='required',server='unsupported'))]
    for name in ['url', 'local', 'all-roots']:
        project = work / 'projects' / name;project.mkdir();(project / 'pack/resourcepacks').mkdir(parents=True)
        (project / 'pack/resourcepacks/observed.zip').write_bytes(payloads['A'])
        doc = json.loads(json.dumps(author).replace('CASE', name))
        root = dict(type='resource-pack',placement=placement)
        if name == 'local':
            (project / 'vendor').mkdir();(project / 'vendor/observed.zip').write_bytes(payloads['A']);root['path']='vendor/observed.zip'
        else:root.update(url='https://example.invalid/observed.zip',**{'accept-observed':True})
        doc['dependencies']['observed'] = root
        if name == 'all-roots':
            doc['dependencies']['second'] = dict(root,url='https://example.invalid/second.zip',placement=[dict(placement[0],destination='resourcepacks/second.zip')])
            (project / 'pack/resourcepacks/second.zip').write_bytes(payloads['A'])
        write(project / 'empack.yml',doc)
        (work / 'state' / name).mkdir(mode=0o700);(work / 'cache' / name).mkdir(mode=0o700)
    env = dict(PATH=os.environ['PATH'],LANG='en_US.UTF-8',TMPDIR=str(work/'tmp'),NO_COLOR='1',DO_NOT_TRACK='1')
    setup = dict(schema=1,work=str(work),binary=str(BINARY),binarySha256=sha(BINARY),producerSha256=sha(run/'probe.py'),
                 snapshotHelper=str(helper.relative_to(ROOT)),snapshotHelperSha256=sha(helper),sourceIdentities=sources,
                 environmentKeys=sorted(env),payloads={v:hashlib.sha256(b).hexdigest()for v,b in payloads.items()},
                 limits=['No engine build, consumer export, Java/game, personal pack or desktop.','URL uses reserved example.invalid; request absence is not a network interception proof.','Separate explicit state/cache roots; source/current binary identity recorded, no reproducible build claim.'])
    write(run/'setup.json',setup);commands=[];mutations=[]
    def image(p):
        result = prior.image(p)
        for n,v in result.items():
            if v['kind']=='file' and (n.startswith('pack/') or n.startswith('vendor/')):
                s=(p/n).stat();v.update(inode=s.st_ino,device=s.st_dev,ctimeNs=s.st_ctime_ns)
        return result
    def command(name,label,args,success):
        project=work/'projects'/name;scopes=dict(project=project,state=work/'state'/name,cache=work/'cache'/name)
        before={k:image(p)for k,p in scopes.items()}
        argv=[str(BINARY),'--workdir',str(project),'--state-dir',str(scopes['state']),'--cache-dir',str(scopes['cache']),'--net-timeout','3','--color','never','--yes',*args]
        began=time.monotonic();p=subprocess.Popen(argv,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        write(run/'current-process.json',dict(pid=p.pid,label=label,status='running',argv=argv));timed=False
        try:out,err=p.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(p.pid,signal.SIGTERM)
            try:out,err=p.communicate(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate(timeout=10)
        for stream,raw in [('stdout',out),('stderr',err)]:(run/(label+'.'+stream)).write_bytes(raw)
        try:os.killpg(p.pid,0);absent=False
        except ProcessLookupError:absent=True
        after={k:image(p)for k,p in scopes.items()}
        row=dict(id=label,project=name,argv=argv,pid=p.pid,exitCode=p.returncode,timedOut=timed,groupAbsent=absent,seconds=time.monotonic()-began,
                 before=before,after=after,streams={s:sha(run/(label+'.'+s))for s in ['stdout','stderr']})
        commands.append(row);write(run/'commands.json',commands);write(run/'current-process.json',dict(pid=p.pid,label=label,status='terminal',exitCode=p.returncode,groupAbsent=absent))
        print(json.dumps(dict(id=label,exitCode=p.returncode,seconds=row['seconds'])),flush=True)
        assert not timed and absent and ((p.returncode==0)==success),'Unexpected native outcome; retain evidence, do not restart automatically.'
        assert {k:v for k,v in before['project'].items()if k.startswith(('pack/','vendor/'))}=={k:v for k,v in after['project'].items()if k.startswith(('pack/','vendor/'))},'Adoption changed payload snapshot.'
        if '--dry-run'in args or not success:assert before['project']==after['project'],'Preview/refusal changed project.'
    def mutate(name,label,path,value):
        p=work/'projects'/name/path;before=image(work/'projects'/name)
        if value is None:p.unlink()
        else:p.write_bytes(value)
        mutations.append(dict(id=label,project=name,path=path,value=None if value is None else hashlib.sha256(value).hexdigest(),before=before,after=image(work/'projects'/name)));write(run/'mutations.json',mutations)
    try:
        command('all-roots','incomplete-first-lock',['adopt','observed'],False)
        command('all-roots','duplicate-first-lock',['adopt','observed','observed','second'],False)
        command('url','url-first-preview',['adopt','observed','--dry-run'],True)
        command('url','url-first-apply',['adopt','observed'],True)
        command('url','url-unchanged-preview',['adopt','observed','--dry-run'],True)
        mutate('url','author-changed-observed-url','pack/resourcepacks/observed.zip',payloads['B'])
        command('url','url-changed-preview',['adopt','observed','--dry-run'],True)
        command('url','url-changed-apply',['adopt','observed'],True)
        command('local','local-first-apply',['adopt','observed'],True)
        mutate('local','author-changed-local-destination','pack/resourcepacks/observed.zip',payloads['B'])
        command('local','local-mismatch-refusal',['adopt','observed'],False)
        mutate('local','author-restored-local-destination','pack/resourcepacks/observed.zip',payloads['A'])
        command('local','local-unchanged-preview',['adopt','observed','--dry-run'],True)
        mutate('local','author-removed-local-destination','pack/resourcepacks/observed.zip',None)
        command('local','local-missing-refusal',['adopt','observed'],False)
        assert sha(BINARY)==EXPECTED
        write(run/'receipt.json',dict(schema=1,complete=True,commands=len(commands),mutations=len(mutations),allGroupsAbsent=all(c['groupAbsent']for c in commands),work=str(work),producerSha256=sha(run/'probe.py'),binarySha256=sha(BINARY),allocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0])))
        print(json.dumps(dict(capture=str(run),commands=len(commands),allGroupsAbsent=True)))
    except BaseException as error:
        write(run/'failure.json',dict(error=str(error),commands=len(commands),work=str(work)));raise


if __name__=='__main__':main()
