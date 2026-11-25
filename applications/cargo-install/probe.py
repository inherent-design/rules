#!/usr/bin/env python3
"""Own a two-bin path crate and private Cargo install/target roots."""
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
import shutil,signal,stat,subprocess,tempfile,time

ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
PACKAGE='rules-install-ownership'
A='rules-install-a'
B='rules-install-b'


def main():
    pin=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']['cargo'];cargo=Path(pin['path']);assert sha(cargo)==pin['sha256'];rustc=cargo.with_name('rustc');assert rustc.is_file()
    run=ROOT/'applications/evidence'/('cargo-install-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));work=run/'work';installed=work/'installed'
    for d in ['home','tmp','cargo-home','target','originals','installed/bin']:(work/d).mkdir(parents=True)
    project=Path(tempfile.mkdtemp(prefix='rules-cargo-install-',dir='/private/tmp'));(project/'src').mkdir()
    (run/'locations.json').write_text(json.dumps(dict(source=str(project),work=str(work),reason='Avoid unrelated real-home Cargo configuration discovery. Source is owned/disposable;retained copy after collection.'),indent=2)+'\n')
    assert all(not(p/'.cargo'/f).exists()for p in project.parents for f in ['config','config.toml'])
    (run/'probe.py').write_bytes(Path(__file__).read_bytes())
    (work/'cargo-home/config.toml').write_text('[net]\noffline=true\n')
    env=dict(PATH=str(cargo.parent)+':/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),CARGO_HOME=str(work/'cargo-home'),CARGO_TARGET_DIR=str(work/'target'),RUSTC=str(rustc),RUSTDOC=str(cargo.with_name('rustdoc')),
             CARGO_NET_OFFLINE='true',CARGO_BUILD_JOBS='1',CARGO_INCREMENTAL='0',CARGO_TERM_COLOR='never',CARGO_PROFILE_RELEASE_DEBUG='0',CARGO_PROFILE_RELEASE_STRIP='symbols',LANG='en_US.UTF-8')
    def sources(version,broken=False):
        (project/'Cargo.toml').write_text('[package]\nname="'+PACKAGE+'"\nversion="'+version+'"\nedition="2021"\nautobins=false\n[workspace]\n[[bin]]\nname="'+A+'"\npath="src/a.rs"\n[[bin]]\nname="'+B+'"\npath="src/b.rs"\n[profile.release]\nopt-level=0\ndebug=0\nstrip="symbols"\ncodegen-units=1\n')
        for name,stem in [('a.rs','a'),('b.rs','b')]:
            (project/'src'/name).write_text('fn main( {'if broken and stem=='a'else'fn main(){println!("'+version+'-'+stem+'");}\n')
    sources('0.1.0')
    foreign=installed/'bin/unrelated-study-file';foreign.write_text('Owned unrelated marker\n');foreign_hash=sha(foreign)
    initial=installed/'bin'/A;initial.write_text('#!/bin/sh\nprintf "untracked placeholder\\n"\n');initial.chmod(0o755)
    rows=[];controls=[];owned=[]
    def image(root):
        result={}
        for p in sorted(root.rglob('*')):
            s=p.lstat();key=str(p.relative_to(root))
            if stat.S_ISDIR(s.st_mode):result[key]=dict(kind='directory',mode=stat.S_IMODE(s.st_mode))
            elif stat.S_ISREG(s.st_mode):
                value=dict(kind='file',bytes=s.st_size,mode=stat.S_IMODE(s.st_mode),nlink=s.st_nlink,inode=s.st_ino,sha256=sha(p))
                if p.name in ['.crates.toml','.crates2.json','Cargo.toml','Cargo.lock','a.rs','b.rs','owned-marker']:value['text']=p.read_text()
                result[key]=value
            else:raise AssertionError('Unexpected nonregular fixture path: '+key)
        return result
    def save():(run/'commands.json').write_text(json.dumps(rows,indent=2)+'\n');(run/'controls.json').write_text(json.dumps(controls,indent=2)+'\n')
    def command(label,argv,expected=0):
        before=image(installed);source_before=image(project);started=time.monotonic()
        with (run/(label+'.stdout')).open('xb')as out,(run/(label+'.stderr')).open('xb')as err:
            p=subprocess.Popen([str(a)for a in argv],cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);owned.append(p)
            (run/'owned-processes.json').write_text(json.dumps([dict(pid=c.pid,retired=c.poll()is not None)for c in owned],indent=2)+'\n')
            timed=False
            try:p.wait(timeout=60)
            except subprocess.TimeoutExpired:timed=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
        try:os.killpg(p.pid,0)
        except ProcessLookupError:absent=True
        else:absent=False
        row=dict(case=label,argv=[str(a)for a in argv],before=before,after=image(installed),sourceBefore=source_before,sourceAfter=image(project),outcome=dict(exitCode=p.returncode,timedOut=timed,ownedGroupAbsent=absent),seconds=time.monotonic()-started,
                 streams={s:dict(file=label+'.'+s,sha256=sha(run/(label+'.'+s)))for s in ['stdout','stderr']})
        rows.append(row);save();print(label,p.returncode,round(row['seconds'],2),flush=True)
        assert not timed and absent and p.returncode==expected,(label,p.returncode,expected)
        assert sha(foreign)==foreign_hash,'A command touched the unrelated marker.'
        return row
    def install(label,force=False,expected=0):
        return command(label,[cargo,'install','--offline','--path',project,'--root',installed,'--target-dir',work/'target',*(['--force']if force else[])],expected)
    def listing(label):return command(label,[cargo,'install','--list','--root',installed])
    def control(label,before,detail):controls.append(dict(case=label,before=before,after=image(installed),detail=detail));save()
    def replace_script(label):
        p=installed/'bin'/A;s=p.lstat();assert stat.S_ISREG(s.st_mode)and s.st_nlink==1
        before=image(installed);shutil.copy2(p,work/'originals'/(label+'-original'))
        temp=work/'originals'/(label+'-script');temp.write_text('#!/bin/sh\nprintf "manual replacement\\n"\n');temp.chmod(0o755);os.replace(temp,p)
        control(label,before,'Replace only the owned regular A path;retain original executable.')
    try:
        command('cargo-version',[cargo,'--version','--verbose']);command('rustc-version',[rustc,'--version','--verbose'])
        command('lock',[cargo,'generate-lockfile','--offline'])
        install('untracked-collision',expected=101)
        install('force-initial',force=True)
        command('runtime-a-initial',[installed/'bin'/A]);command('runtime-b-initial',[installed/'bin'/B]);listing('catalog-initial')
        replace_script('manual-a')
        listing('catalog-manual');command('runtime-a-manual',[installed/'bin'/A])
        install('path-refresh');command('runtime-a-refreshed',[installed/'bin'/A])
        sources('0.1.0',broken=True);install('compile-refusal',expected=101)
        command('runtime-a-after-compile-refusal',[installed/'bin'/A]);command('runtime-b-after-compile-refusal',[installed/'bin'/B])
        sources('0.2.0');before=image(installed);p=installed/'bin'/B;s=p.lstat();assert stat.S_ISREG(s.st_mode)and s.st_nlink==1
        os.rename(p,work/'originals/v1-b');p.mkdir();(p/'owned-marker').write_text('Owned replacement blocker\n');control('block-b-directory',before,'Preserve original B by rename;create owned nonempty directory at its old name.')
        install('partial-replacement',expected=101);command('runtime-a-partial',[installed/'bin'/A]);listing('catalog-partial')
        before=image(installed);os.rename(p,work/'originals/blocker-b');shutil.copy2(work/'originals/v1-b',p);control('restore-b-for-retry',before,'Preserve blocker directory;restore prior regular B bytes before retry.')
        install('complete-replacement');command('runtime-a-v2',[installed/'bin'/A]);command('runtime-b-v2',[installed/'bin'/B])
        before=image(installed);os.rename(p,work/'originals/v2-b');control('remove-b-for-preflight',before,'Retain B outside bin to inspect filtered-uninstall preflight.')
        command('uninstall-a-with-missing-b',[cargo,'uninstall','--root',installed,'--bin',A,PACKAGE],101)
        before=image(installed);os.rename(work/'originals/v2-b',p);control('restore-b-for-uninstall',before,'Restore retained B before actual uninstall.')
        replace_script('manual-a-v2');command('uninstall-manual-a',[cargo,'uninstall','--root',installed,'--bin',A,PACKAGE])
        command('runtime-b-after-subset-uninstall',[p]);listing('catalog-subset')
        command('uninstall-rest',[cargo,'uninstall','--root',installed,PACKAGE]);listing('catalog-final')
        receipt=dict(schema=1,producerSha256=sha(run/'probe.py'),tools={name:dict(path=str(path),sha256=sha(path))for name,path in [('cargo',cargo),('rustc',rustc)]},commands=len(rows),controls=len(controls),
                     allOwnedGroupsAbsent=all(c['outcome']['ownedGroupAbsent']for c in rows),unrelatedMarkerSha256=foreign_hash,
                     targetAllocatedKiB=int(subprocess.check_output(['du','-sk',str(work/'target')],text=True).split()[0]),workAllocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),
                     limits=['One generated two-bin path crate,private Cargo home/target/install root,offline,jobs1,incremental0. No installed/global tool or external registry used.',
                             'Owned script replacements,directory blocker and missing B are explicit interventions,not unobserved Cargo corruption. Originals/blocker retained;no payload hardlinks.',
                             'Metadata/bin/source images and process outcomes;no syscall,durable crash,multiwriter,no-track,registry/Git freshness or Windows qualification.'])
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    finally:
        for p in owned:
            if p.poll()is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
        (run/'owned-processes.json').write_text(json.dumps([dict(pid=p.pid,retired=p.poll()is not None)for p in owned],indent=2)+'\n')
        shutil.copytree(project,work/'project-retained')
        assert image(project)==image(work/'project-retained')or all(sha(p)==sha(work/'project-retained'/p.relative_to(project))for p in project.rglob('*')if p.is_file())
        # The small source root stays available until qualification;no active or
        # failed experiment is removed merely because collection returned.
        print('capture',run,flush=True)


if __name__=='__main__':main()
