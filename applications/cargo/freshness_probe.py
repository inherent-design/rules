#!/usr/bin/env python3
"""One tiny offline Cargo fixture: watched env, physical script runs and outputs."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
BIN=Path('/Users/zer0cell/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
BUILD='''use std::{env,fs,io::Write,path::PathBuf};
fn main() {
    println!("cargo::rerun-if-changed=build.rs");
    println!("cargo::rerun-if-changed=input.txt");
    println!("cargo::rerun-if-env-changed=RULES_TRACKED");
    println!("cargo::rerun-if-env-changed=RULES_FAIL");
    let watched=env::var("RULES_TRACKED").ok();
    // Deliberately undeclared input. Its omission is a fixture violation.
    let hidden=env::var("RULES_HIDDEN").ok();
    let fail=env::var_os("RULES_FAIL").is_some();
    let input=fs::read_to_string("input.txt").unwrap();
    let data=format!("tracked={:?};hidden={:?};file={};fail={}",watched,hidden,input.trim(),fail);
    let mut journal=fs::OpenOptions::new().append(true).create(true)
        .open(env::var_os("RULES_JOURNAL").unwrap()).unwrap();
    writeln!(journal,"start {}",data).unwrap();
    let out=PathBuf::from(env::var_os("OUT_DIR").unwrap());
    fs::write(out.join("selected.txt"),&data).unwrap();
    writeln!(journal,"wrote {}",out.join("selected.txt").display()).unwrap();
    if fail {
        writeln!(journal,"failed").unwrap();
        panic!("controlled failure after generated-file write");
    }
    writeln!(journal,"success").unwrap();
}
'''
MAIN='''fn main() {
    println!("{}|macro={:?}",include_str!(concat!(env!("OUT_DIR"),"/selected.txt")),option_env!("RULES_MACRO"));
}
'''

def image(root):
    if not root.exists():return None
    result={}
    for p in sorted(root.rglob('*')):
        assert not p.is_symlink(),p
        s=p.stat()
        result[p.relative_to(root).as_posix()]=dict(kind='file'if p.is_file()else'directory',mode=s.st_mode&0o777,
            **(dict(bytes=s.st_size,sha256=sha(p),mtimeNs=str(s.st_mtime_ns))if p.is_file()else{}))
    return result

def prepare():
    pins=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']
    assert sha(BIN/'cargo')==pins['cargo']['sha256']
    assert sha(BIN/'rustc')=='12cab30aa9890d54445e29149a1e82d18fbe457de12801bd11bbe7e5e7fe33a0'
    run=ROOT/'applications/evidence'/('cargo-freshness-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir()
    work=Path(tempfile.mkdtemp(prefix='rules-cargo-freshness-',dir='/private/tmp'))
    for parent in [work,*work.parents]:
        assert not any((parent/'.cargo'/f).exists()for f in ['config','config.toml']),parent
    for name in ['project/src','home','cargo-home','tmp']:(work/name).mkdir(parents=True)
    (work/'project/Cargo.toml').write_text('[package]\nname="rules-freshness"\nversion="0.1.0"\nedition="2021"\n[profile.dev]\ndebug=0\nincremental=false\n')
    (work/'project/build.rs').write_text(BUILD);(work/'project/src/main.rs').write_text(MAIN);(work/'project/input.txt').write_text('first\n')
    (run/'probe.py').write_bytes(PRODUCER)
    for name in ['Cargo.toml','build.rs','src/main.rs','input.txt']:
        p=run/'source'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(work/'project'/name,p)
    env=dict(PATH=str(BIN)+':/usr/bin:/bin',HOME=str(work/'home'),CARGO_HOME=str(work/'cargo-home'),
        CARGO_TARGET_DIR=str(work/'target'),RUSTC=str(BIN/'rustc'),RUSTDOC=str(BIN/'rustdoc'),
        TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8',CARGO_BUILD_JOBS='1',CARGO_NET_OFFLINE='true',
        CARGO_TERM_COLOR='never',CARGO_INCREMENTAL='0',RULES_JOURNAL=str(work/'script-invocations.log'),
        RULES_HIDDEN='hidden-first',RULES_MACRO='macro-first')
    tools={n:dict(path=str(BIN/n),sha256=sha(BIN/n),version=subprocess.check_output([str(BIN/n),'--version','--verbose'],env=env,text=True))for n in ['cargo','rustc']}
    assert '344c4567c634a25837e3c3476aac08af84cf9203'in tools['cargo']['version']
    write(run/'setup.json',dict(schema=1,work=str(work),environment=env,tools=tools,platform=platform.platform(),
        machine=platform.machine(),ancestryConfigAbsent=True,scope='One trusted local crate,own target andhome;no registry dependencies/network,proc macros or package sandbox.'))
    print(json.dumps(dict(run=str(run.relative_to(ROOT)),work=str(work))))

def collect(run):
    run=run.resolve();assert run.parent==ROOT/'applications/evidence'
    assert (run/'probe.py').read_bytes()==PRODUCER
    with (run/'started.json').open('x')as f:json.dump(dict(producerSha256=sha(run/'probe.py')),f)
    setup=json.loads((run/'setup.json').read_text());work=Path(setup['work']);project=work/'project';env=dict(setup['environment'])
    for name,t in setup['tools'].items():assert sha(Path(t['path']))==t['sha256']
    commands=[];edits=[];children=[];outdir=None
    def state():
        journal=work/'script-invocations.log'
        return dict(project=image(project),target=image(work/'target'),cargoHome=image(work/'cargo-home'),
            journal=journal.read_text()if journal.exists()else'',binary=sha(work/'target/debug/rules-freshness')if(work/'target/debug/rules-freshness').exists()else None,
            generated=(outdir/'selected.txt').read_text()if outdir is not None and(outdir/'selected.txt').exists()else None)
    def command(label,kind='build'):
        nonlocal outdir
        before=state();argv=[str(BIN/'cargo'),'build','--offline','--message-format=json']if kind=='build'else[str(BIN/'cargo'),'clean','--offline']if kind=='clean'else[str(work/'target/debug/rules-freshness')]
        with (run/(label+'.stdout')).open('xb')as out,(run/(label+'.stderr')).open('xb')as err:
            child=subprocess.Popen(argv,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
            children.append(child);write(run/'processes.json',[dict(pid=p.pid,retired=p.poll()is not None)for p in children]);start=time.monotonic();timed=False
            try:child.wait(timeout=60)
            except subprocess.TimeoutExpired:timed=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
        try:os.killpg(child.pid,0)
        except ProcessLookupError:absent=True
        else:absent=False
        messages=[]
        if kind=='build':
            messages=[json.loads(s)for s in(run/(label+'.stdout')).read_text().splitlines()]
            outputs=[Path(x['out_dir'])for x in messages if x.get('reason')=='build-script-executed']
            if outputs:
                assert len(set(outputs))==1
                if outdir is not None:assert outdir==outputs[0]
                outdir=outputs[0]
        after=state()
        row=dict(case=label,kind=kind,argv=argv,exitCode=child.returncode,timedOut=timed,ownedGroupAbsent=absent,
            seconds=time.monotonic()-start,environment={k:env.get(k)for k in ['RULES_TRACKED','RULES_HIDDEN','RULES_MACRO','RULES_FAIL']},
            before=before,after=after,messages=messages,streams={s:sha(run/(label+'.'+s))for s in ['stdout','stderr']})
        commands.append(row);write(run/'commands.json',commands);write(run/'processes.json',[dict(pid=p.pid,retired=p.poll()is not None)for p in children])
        assert not timed and absent,(label,row)
        return row
    def change(label,updates=None,file=None,remove_generated=False):
        before=state();old={k:env.get(k)for k in ['RULES_TRACKED','RULES_HIDDEN','RULES_MACRO','RULES_FAIL']}
        for k,v in(updates or{}).items():
            if v is None:env.pop(k,None)
            else:env[k]=v
        if file is not None:(project/'input.txt').write_text(file+'\n')
        if remove_generated:
            assert outdir is not None and outdir.is_relative_to(work/'target')
            p=outdir/'selected.txt';assert p.is_file();p.unlink()
        edits.append(dict(case=label,before=before,after=state(),oldEnvironment=old,
            newEnvironment={k:env.get(k)for k in old},action=dict(environment=updates,file=file,removeGenerated=remove_generated)))
        write(run/'edits.json',edits)
    def build(label):
        row=command(label)
        if(work/'target/debug/rules-freshness').is_file():command(label+'-run','run')
        return row
    try:
        assert build('cold')['exitCode']==0,'First compile must admit the fixture before continuation.'
        build('same')
        change('hidden-env',{'RULES_HIDDEN':'hidden-second'});build('hidden-env')
        change('tracked-empty',{'RULES_TRACKED':''});build('tracked-empty')
        change('tracked-value',{'RULES_TRACKED':'value'});build('tracked-value')
        change('tracked-unset',{'RULES_TRACKED':None});build('tracked-unset')
        change('macro-env',{'RULES_MACRO':'macro-second'});build('macro-env')
        change('watched-file',file='second');build('watched-file')
        change('fail',{'RULES_FAIL':'yes'});build('fail')
        build('fail-retry')
        change('recover',{'RULES_FAIL':None});build('recover')
        change('delete-generated',remove_generated=True);build('missing-output')
        build('missing-output-retry')
        change('restore-input',file='third');build('restored')
        build('same-restored')
        before_clean=state();saved=work/'retained-product';shutil.copyfile(work/'target/debug/rules-freshness',saved)
        # One small final product remains for independent reinspection; all
        # compiler intermediates are removed by the owned Cargo cleanup.
        clean=command('clean','clean');assert clean['exitCode']==0 and not(work/'target').exists()
        shutil.copyfile(work/'script-invocations.log',run/'script-invocations.log')
        (run/'final-generated.txt').write_text(before_clean['generated'])
        write(run/'receipt.json',dict(schema=1,status='complete',commands=len(commands),builds=sum(c['kind']=='build'for c in commands),
            producerSha256=sha(run/'probe.py'),tools=setup['tools'],work=str(work),outDir=str(outdir),allOwnedGroupsRetired=True,
            sourceAfter=image(project),retainedProduct=dict(path=str(saved),sha256=sha(saved),bytes=saved.stat().st_size),
            targetRemoved=True,limits=['One local Cargo1.92macOSarm64 profile;no checksum-freshness,parallel/cross-target/registry/proc-macro qualification.','Build script deliberately omits an input and writes an observation journal outsideOUT_DIR;not product defects.','Missing generated output and failed script are owned fixture interventions,not an unexplained corruption report.']))
        print(json.dumps(dict(run=str(run.relative_to(ROOT)),commands=len(commands),builds=sum(c['kind']=='build'for c in commands),status='complete')))
    finally:
        for child in children:
            if child.poll()is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
        write(run/'processes.json',[dict(pid=p.pid,retired=p.poll()is not None)for p in children])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','collect']);p.add_argument('run',type=Path,nargs='?');a=p.parse_args()
    if a.action=='prepare':prepare()
    else:assert a.run;collect(a.run)
if __name__=='__main__':main()
