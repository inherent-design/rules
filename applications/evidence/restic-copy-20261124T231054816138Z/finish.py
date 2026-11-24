"""Bounded readback completion of the failed producer; does not repeat copy."""
import hashlib, importlib.util, json, os
from pathlib import Path
import platform, signal, subprocess, time

RUN=Path(__file__).resolve().parent
ROOT=RUN.parents[2]
WORK=RUN/'work'
assert RUN.name=='restic-copy-20261124T231054816138Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('frozen_helper',RUN/'helper.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
raw_commands=json.loads((WORK/'private/commands.json').read_text())
assert raw_commands[-1]['case']=='dump-c-0'and raw_commands[-1]['outcome']['exitCode']==1
assert all(c['outcome']['ownedGroupAbsent']for c in raw_commands)
assert all(r['retired']for r in json.loads((RUN/'owned-processes.json').read_text()))
TOOL=ROOT/'applications/tools/restic-0.20.0/restic'
PIN=json.loads((ROOT/'applications/sources/restic-tool.json').read_text());assert sha(TOOL)==PIN['binarySha256']
repos={n:WORK/('repo-'+n)for n in ['a','b','c']}
def state():return {n:{str(p.relative_to(repo)):dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(repo.rglob('*'))if p.is_file()}for n,repo in repos.items()}
initial=state();assert initial==raw_commands[-1]['after']
rows=[];observations=json.loads((WORK/'private/observations.json').read_text())
env=dict(PATH='/usr/bin:/bin',HOME=str(WORK/'home'),TMPDIR=str(WORK/'tmp'),RESTIC_CACHE_DIR=str(WORK/'cache'),GOMAXPROCS='2',LANG='C.UTF-8')
def command(label,target,args):
    assert not(RUN/(label+'.stdout')).exists(),'Reconcile prior completion instead of repeating.'
    argv=[str(TOOL),'--repo',str(repos[target]),'--password-file',str(WORK/('password-'+target)),'--json',*args]
    started=time.monotonic();before=state()
    with (WORK/'private'/(label+'.stdout')).open('xb')as out,(WORK/'private'/(label+'.stderr')).open('xb')as err:
        p=subprocess.Popen(argv,cwd=WORK/'source',env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
        try:p.wait(timeout=45)
        finally:
            if p.poll()is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
    try:os.killpg(p.pid,0)
    except ProcessLookupError:absent=True
    else:absent=False
    streams={}
    for stream in ['stdout','stderr']:
        raw=WORK/'private'/(label+'.'+stream);public=RUN/(label+'.'+stream);public.write_bytes(helper.redact(raw.read_bytes()))
        streams[stream]=dict(rawSha256=sha(raw),publicSha256=sha(public),rawPrivatePath=str(raw.relative_to(RUN)))
    rows.append(dict(case=label,target=target,argv=argv,before=before,after=state(),streams=streams,outcome=dict(exitCode=p.returncode,ownedGroupAbsent=absent),seconds=time.monotonic()-started))
    (WORK/'private/finish-commands.json').write_text(json.dumps(rows,indent=2)+'\n')
    (RUN/'finish-commands.json').write_bytes(helper.redact(json.dumps(rows,indent=2).encode()+b'\n'))
    assert p.returncode==0 and absent and before==state(),(label,p.returncode)
    print(label,p.returncode,flush=True)
    return (WORK/'private'/(label+'.stdout')).read_bytes()

final=json.loads((WORK/'private/final-c.stdout').read_text())
listing=command('finish-ls','c',['ls',final[0]['id']])
nodes=[json.loads(line)for line in listing.splitlines()]
inner_path=next(n['path']for n in nodes if n.get('type')=='file'and n.get('name')=='mutable.txt')
assert inner_path=='/mutable.txt'
for i,s in enumerate(final):
    raw=command('finish-dump-'+str(i),'c',['dump',s['id'],inner_path])
    observations.append(dict(case='finish-dump-'+str(i),snapshot=s,payloadHex=raw.hex()))
configs={n:json.loads(command('finish-config-'+n,n,['cat','config']))for n in repos}
assert not any(list((r/'locks').glob('*'))for r in repos.values())
(WORK/'private/finished-observations.json').write_text(json.dumps(observations,indent=2)+'\n')
(RUN/'finished-observations.json').write_bytes(helper.redact(json.dumps(observations,indent=2).encode()+b'\n'))
receipt=dict(schema=1,tool=PIN,platform=platform.platform(),architecture=platform.machine(),producerSha256=sha(RUN/'probe.py'),helperSha256=sha(RUN/'helper.py'),completionSha256=sha(Path(__file__)),
    initialCommands=len(raw_commands),completionCommands=len(rows),copyCases=8,configs=configs,allOwnedGroupsAbsent=all(c['outcome']['ownedGroupAbsent']for c in rows),
    sourceRepositoryFilesUnchangedByCompletion=initial==state(),allocatedKiB=int(subprocess.check_output(['du','-sk',str(WORK)],text=True).split()[0]),
    originalObservationsSha256=sha(RUN/'observations.json'),finishedObservationsSha256=sha(RUN/'finished-observations.json'),rawFinishedObservationsSha256=sha(WORK/'private/finished-observations.json'),
    correction='Initial producer mistook Snapshot.Paths source selection for inner dump path. Failed dump preserved; one fresh ls finds /mutable.txt, then only readback/configuration commands complete. No copies or backups repeated.',
    limits=['Three generated local repositories and two tiny files;no real backup,remote backend,concurrency,interrupted copy,encryption or durability qualification.',
            'Published output is redacted by frozen helper. Raw streams,passwords and encrypted repos stay ignored/private. All initial effects and failed readback remain separately recorded.'])
(RUN/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(innerPath=inner_path,commands=len(rows),allocatedKiB=receipt['allocatedKiB'])))
