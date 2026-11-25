"""Bounded new-bin/replacement cleanup control using the completed owned target."""
import hashlib,json,os
from pathlib import Path
import signal,subprocess,time

RUN=Path(__file__).resolve().parent
ROOT=RUN.parents[2]
WORK=RUN/'work'
assert RUN.name=='cargo-install-20261125T003504421536Z'
receipt=json.loads((RUN/'receipt.json').read_text());locations=json.loads((RUN/'locations.json').read_text());project=Path(locations['source'])
assert all(p['retired']for p in json.loads((RUN/'owned-processes.json').read_text()))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cargo=Path(receipt['tools']['cargo']['path']);rustc=Path(receipt['tools']['rustc']['path'])
assert sha(cargo)==receipt['tools']['cargo']['sha256']and sha(rustc)==receipt['tools']['rustc']['sha256']
installed=WORK/'mixed-new-root';assert not installed.exists(),'Reconcile any previous followup instead of repeating.'
(installed/'bin/rules-install-a').mkdir(parents=True);(installed/'bin/rules-install-a/owned-marker').write_text('Owned blocking directory\n')
env=dict(PATH=str(cargo.parent)+':/usr/bin:/bin',HOME=str(WORK/'home'),TMPDIR=str(WORK/'tmp'),CARGO_HOME=str(WORK/'cargo-home'),CARGO_TARGET_DIR=str(WORK/'target'),RUSTC=str(rustc),RUSTDOC=str(cargo.with_name('rustdoc')),
         CARGO_NET_OFFLINE='true',CARGO_BUILD_JOBS='1',CARGO_INCREMENTAL='0',CARGO_TERM_COLOR='never',CARGO_PROFILE_RELEASE_DEBUG='0',CARGO_PROFILE_RELEASE_STRIP='symbols',LANG='en_US.UTF-8')
def image():
    result={}
    for p in sorted(installed.rglob('*')):
        if p.is_dir():result[str(p.relative_to(installed))]=dict(kind='directory')
        else:
            assert p.is_file()and not p.is_symlink()
            row=dict(kind='file',bytes=p.stat().st_size,sha256=sha(p))
            if p.name in ['.crates.toml','.crates2.json','owned-marker']:row['text']=p.read_text()
            result[str(p.relative_to(installed))]=row
    return result
rows=[]
def command(label,argv,expected):
    before=image();start=time.monotonic()
    with (RUN/(label+'.stdout')).open('xb')as out,(RUN/(label+'.stderr')).open('xb')as err:
        child=subprocess.Popen([str(a)for a in argv],cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
        (RUN/'followup-active.json').write_text(json.dumps(dict(case=label,pid=child.pid,argv=[str(a)for a in argv]))+'\n')
        try:child.wait(timeout=45)
        finally:
            if child.poll()is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
    try:os.killpg(child.pid,0)
    except ProcessLookupError:absent=True
    else:absent=False
    rows.append(dict(case=label,argv=[str(a)for a in argv],before=before,after=image(),outcome=dict(exitCode=child.returncode,ownedGroupAbsent=absent),seconds=time.monotonic()-start,
                     streams={s:dict(file=label+'.'+s,sha256=sha(RUN/(label+'.'+s)))for s in ['stdout','stderr']}))
    (RUN/'new-bin-followup.json').write_text(json.dumps(dict(schema=1,scope='Fresh owned mixed new/replacement root;reuses prior target,no source edits or new dependencies.',producerSha256=sha(Path(__file__)),root=str(installed),commands=rows),indent=2)+'\n')
    (RUN/'followup-active.json').write_text(json.dumps(dict(case=label,pid=child.pid,retired=True,ownedGroupAbsent=absent))+'\n')
    assert child.returncode==expected and absent,(label,child.returncode)
    print(label,child.returncode,flush=True)

command('new-bin-replace-failure',[cargo,'install','--offline','--path',project,'--root',installed,'--target-dir',WORK/'target','--force'],101)
command('new-bin-catalog',[cargo,'install','--list','--root',installed],0)
command('new-bin-uninstall',[cargo,'uninstall','--root',installed,'--bin','rules-install-b','rules-install-ownership'],101)
print('B exists', (installed/'bin/rules-install-b').exists())
