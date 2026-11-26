"""Owned path/local-Git metadata and lock fixture; no registry, build, or GUI."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write = lambda p,v:p.write_text(json.dumps(v,indent=2)+'\n')


def main():
    pins = json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']['cargo']
    cargo = Path(pins['path']);assert sha(cargo) == pins['sha256']
    rustc = cargo.with_name('rustc');assert rustc.is_file()
    work = Path(tempfile.mkdtemp(prefix='rules-cargo-lock-',dir='/private/tmp'))
    cap = ROOT/'applications/evidence'/('cargo-lock-sources-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));cap.mkdir()
    for n in ['home','cargo-home','tmp','path-app/src','path-lib/src','git-app/src','git-lib/src','patch-lib/src']:(work/n).mkdir(parents=True)
    env = dict(PATH='/usr/bin:/bin',HOME=str(work/'home'),CARGO_HOME=str(work/'cargo-home'),TMPDIR=str(work/'tmp'),
               RUSTC=str(rustc),RUSTDOC=str(rustc.with_name('rustdoc')),CARGO_TARGET_DIR=str(work/'target'),
               CARGO_TERM_COLOR='never',CARGO_BUILD_JOBS='1',CARGO_INCREMENTAL='0',LANG='en_US.UTF-8',
               GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_TERMINAL_PROMPT='0')
    manifests = {
        'path-app':'[package]\nname="rules-path-app"\nversion="1.0.0"\nedition="2021"\n[dependencies]\nrules-shared={path="../path-lib",version=">=1.0,<2"}\n',
        'path-lib':'[package]\nname="rules-shared"\nversion="1.0.0"\nedition="2021"\n',
        'git-lib':'[package]\nname="rules-shared"\nversion="1.0.0"\nedition="2021"\n',
        'patch-lib':'[package]\nname="rules-shared"\nversion="1.0.0"\nedition="2021"\n'}
    url = (work/'git-lib').as_uri()
    manifests['git-app']='[package]\nname="rules-git-app"\nversion="1.0.0"\nedition="2021"\n[dependencies]\nrules-shared={git='+json.dumps(url)+',branch="main"}\n'
    for n,text in manifests.items():
        (work/n/'Cargo.toml').write_text(text)
        (work/n/'src'/('main.rs' if n.endswith('app') else 'lib.rs')).write_text('fn main() {}\n' if n.endswith('app') else 'pub const VALUE:u8=1;\n')
    git = Path(shutil.which('git')).resolve();scaffold = []
    def gitcall(*args):
        q = subprocess.run([str(git),'-c','core.hooksPath=/dev/null','-C',str(work/'git-lib'),*args],env=env,capture_output=True,text=True)
        scaffold.append(dict(argv=q.args,exitCode=q.returncode,stdout=q.stdout,stderr=q.stderr));write(cap/'git-scaffold.json',scaffold)
        assert q.returncode == 0,q.stderr
        return q.stdout.strip()
    gitcall('init','--initial-branch=main');gitcall('add','Cargo.toml','src/lib.rs')
    gitcall('-c','user.name=Rules fixture','-c','user.email=rules@example.invalid','commit','--no-gpg-sign','-m','first image')
    first = gitcall('rev-parse','HEAD')
    def item(p):
        s = p.stat();return dict(bytes=s.st_size,mode=s.st_mode&0o777,mtimeNs=s.st_mtime_ns,sha256=sha(p))
    def state():
        files = {}
        for n in manifests:
            for p in sorted((work/n).rglob('*')):
                if p.is_file() and '.git' not in p.relative_to(work/n).parts:
                    info = item(p);assert info['bytes'] < 65536;info['text']=p.read_text();files[str(p.relative_to(work))]=info
        cache = {str(p.relative_to(work/'cargo-home')):item(p) for p in sorted((work/'cargo-home').rglob('*')) if p.is_file()}
        target = {str(p.relative_to(work/'target')):item(p) for p in sorted((work/'target').rglob('*')) if p.is_file()} if (work/'target').exists() else {}
        return dict(files=files,cache=cache,target=target)
    versions = {}
    for name,tool in [('rustc',rustc),('git',git)]:
        q = subprocess.run([str(tool),'--version'],env=env,capture_output=True,text=True,check=True)
        versions[name] = q.stdout.strip()
    rows = [];setup = dict(schema=1,work=str(work),cargo=pins,rustc=dict(path=str(rustc),sha256=sha(rustc),version=versions['rustc']),git=dict(path=str(git),sha256=sha(git),version=versions['git']),platform=platform.platform(),environment=env,firstGit=first,localGitUrl=url,producerSha256=sha(Path(__file__)),scope='Disposable owned path/local-file Git sources. No registry or build/check/run command. Cargo may run rustc information queries;not a compiler-process census. Exact private state snapshots are not a global-effect census.')
    write(cap/'setup.json',setup);shutil.copyfile(__file__,cap/'probe.py');write(cap/'initial.json',state())
    print(json.dumps(dict(capture=str(cap),work=str(work))),flush=True)
    def call(name,project,args,expected):
        before = state();command = [str(cargo),*args];out = cap/(name+'.stdout');err = cap/(name+'.stderr')
        with out.open('xb') as stdout,err.open('xb') as stderr:
            child = subprocess.Popen(command,cwd=work/project,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
            write(cap/'current-process.json',dict(id=name,pid=child.pid,argv=command,cwd=str(work/project),status='running'))
            try:code = child.wait(timeout=45)
            except subprocess.TimeoutExpired:
                write(cap/'current-process.json',dict(id=name,pid=child.pid,argv=command,cwd=str(work/project),status='observation-timeout;process-not-declared-terminal'))
                raise RuntimeError('Preserve and reconcile the same native PID;do not restart.')
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        row = dict(id=name,pid=child.pid,argv=command,cwd=str(work/project),exitCode=code,groupAbsent=absent,before=before,after=state(),stdout=dict(path=out.name,sha256=sha(out)),stderr=dict(path=err.name,sha256=sha(err)))
        rows.append(row);write(cap/'receipt.json',dict(schema=1,setup='setup.json',rows=rows));write(cap/'current-process.json',dict(id=name,pid=child.pid,status='terminal',exitCode=code,groupAbsent=absent));print(name,code,flush=True)
        assert absent,'Native group still exists;preserve before continuing.'
        assert code == expected,(name,code,'Expected status differs;retain originals and inspect before continuing.')
    metadata = ['metadata','--format-version','1']
    call('path-missing-frozen','path-app',metadata+['--frozen'],101)
    call('path-generate-offline','path-app',['generate-lockfile','--offline'],0)
    call('path-locked-offline','path-app',metadata+['--locked','--offline'],0)
    lock = work/'path-app/Cargo.lock';lock.write_bytes(b'# owned formatting control\n'+lock.read_bytes().replace(b'\n',b'\r\n'))
    call('path-format-only-frozen','path-app',metadata+['--frozen'],0)
    p=work/'path-lib/Cargo.toml';p.write_text(p.read_text().replace('1.0.0','1.1.0'))
    call('path-changed-locked','path-app',metadata+['--locked','--offline'],101)
    call('path-changed-offline','path-app',metadata+['--offline'],0)
    call('git-cold-offline','git-app',metadata+['--offline'],101)
    # The only permitted source URL is the just-created file:// repository.
    # This call permits Cargo source access,not contact with a remote service.
    call('git-cold-locked-local-fetch','git-app',metadata+['--locked'],101)
    call('git-warm-offline','git-app',metadata+['--offline'],0)
    p=work/'git-lib/src/lib.rs';p.write_text('pub const VALUE:u8=2;\n');gitcall('add','src/lib.rs');gitcall('-c','user.name=Rules fixture','-c','user.email=rules@example.invalid','commit','--no-gpg-sign','-m','second image same package version');second=gitcall('rev-parse','HEAD');setup['secondGit']=second;write(cap/'setup.json',setup)
    call('git-locked-after-source-advance','git-app',metadata+['--frozen'],0)
    call('git-update-offline','git-app',['update','-p','rules-shared','--offline'],0)
    call('git-update-local-fetch','git-app',['update','-p','rules-shared'],0)
    call('git-after-update-frozen','git-app',metadata+['--frozen'],0)
    p=work/'git-app/Cargo.toml';p.write_text(p.read_text()+'\n[patch.'+json.dumps(url)+']\nrules-shared={path="../patch-lib"}\n')
    call('patch-source-locked','git-app',metadata+['--locked','--offline'],101)
    call('patch-source-offline','git-app',metadata+['--offline'],0)
    call('patch-source-frozen','git-app',metadata+['--frozen'],0)
    write(cap/'final.json',state());write(cap/'closure.json',dict(allGroupsAbsent=all(r['groupAbsent'] for r in rows),commands=len(rows),scope='Recorded command groups only;not arbitrary detached descendants. Private inputs/cache are retained;no generated target cleanup claimed.'))
    print(json.dumps(dict(capture=str(cap),commands=len(rows),allGroupsAbsent=True)),flush=True)


if __name__=='__main__':main()
