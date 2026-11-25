#!/usr/bin/env python3
"""One isolated packaged-JAR study; no build, provider download, or live cache."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
PRODUCT=ROOT.parent/'empack'
JAR=PRODUCT/'bootstrap/target/empack-bootstrap.jar'
JAR_SHA='8feefc756fa96b0f16e1e91a7d4bcc566c3d19cf02a655fae90b8ea6b2df7d40'
ENGINE=Path('/Users/zer0cell/.local/bin/empack')
ENGINE_SHA='99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
REVISION='0b4462e3032b4f09230b15329722eabefb7f574c'
JAVAS={17:Path('/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home/bin/java'),
       21:Path('/Users/zer0cell/.local/share/mise/installs/java/21.0.12+101.0.LTS/bin/java'),
       25:Path('/Users/zer0cell/.local/share/mise/installs/java/25.0.5.1+2.0.LTS/bin/java')}
PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def snapshot(root):
    if not root.exists():return None
    result={}
    for p in sorted(root.rglob('*')):
        s=p.lstat();key=p.relative_to(root).as_posix()
        if p.is_symlink():result[key]=dict(kind='link',target=os.readlink(p));continue
        result[key]=dict(kind='file'if p.is_file()else'directory',mode=s.st_mode&0o777,
            **(dict(bytes=s.st_size,sha256=sha(p))if p.is_file()else{}))
    return result

def prepare():
    assert sha(JAR)==JAR_SHA and sha(ENGINE)==ENGINE_SHA
    run=ROOT/'applications/evidence'/('empack-bootstrap-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work=run/'work';(work/'distribution').mkdir(parents=True)
    shutil.copyfile(JAR,work/'distribution/empack-bootstrap.jar')
    (run/'probe.py').write_bytes(PRODUCER)
    original=(ROOT/'applications/empack/bootstrap_fixture_engine.py').read_bytes()
    (run/'fixture-engine.py').write_bytes(original)
    # A concrete interpreter path avoids PATH selection and Java/shell quoting.
    script=('#!'+sys.executable+'\n').encode()+b'\n'.join(original.split(b'\n')[1:])
    fixture=work/'fixture-engine.py';fixture.write_bytes(script);fixture.chmod(0o700)
    metadata=json.loads(JAR.with_suffix('.json').read_text())
    assert metadata['jar_sha256']==JAR_SHA
    for path,h in metadata['sources'].items():
        b=subprocess.check_output(['git','-C',str(PRODUCT),'show',REVISION+':'+path]);assert hashlib.sha256(b).hexdigest()==h
    write(run/'jar-build.json',metadata)
    tools={}
    for major,java in JAVAS.items():
        result=subprocess.run([str(java),'-version'],capture_output=True,timeout=10)
        assert result.returncode==0
        tools[str(major)]=dict(path=str(java),sha256=sha(java),version=(result.stdout+result.stderr).decode())
    write(run/'setup.json',dict(schema=1,jar=dict(source=str(JAR),sha256=JAR_SHA,bytes=JAR.stat().st_size),
        sourceRevision=REVISION,nativeEngine=dict(path=str(ENGINE),sha256=ENGINE_SHA),java=tools,
        python=dict(path=sys.executable,sha256=sha(Path(sys.executable)),version=sys.version),
        originalFixtureSha256=hashlib.sha256(original).hexdigest(),executableFixtureSha256=sha(fixture)))
    print(json.dumps(dict(run=str(run.relative_to(ROOT)))))

def collect(run):
    run=run.resolve();assert run.parent==ROOT/'applications/evidence'
    assert (run/'probe.py').read_bytes()==PRODUCER
    with (run/'started.json').open('x')as f:json.dump(dict(producerSha256=sha(run/'probe.py')),f)
    work=run/'work';dist=work/'distribution';jar=dist/'empack-bootstrap.jar';fixture=work/'fixture-engine.py'
    assert sha(jar)==JAR_SHA and sha(ENGINE)==ENGINE_SHA
    commands=[];children=[]
    def execute(name,mode='record',major=25,locale='en_US.UTF-8',local=None,cache=None,explicit=True,
                append=True,dynamic=None,version='0.8.8-beta',protocol='empack-bootstrap/1',
                engine_version='0.8.8-beta',edit=None,signal_kind=None,native=False,extra=None):
        case=work/'cases'/name;base=case/'Pack Ω 日本';tools=base/'.empack-tools';tools.mkdir(parents=True)
        cache_root=case/'cache';home=case/'home';home.mkdir();log=case/'engine-events.jsonl'
        automatic=dist/'empack'
        if automatic.exists():automatic.unlink()
        if local:
            shutil.copyfile(fixture,automatic);automatic.chmod(0o700)
        if cache:
            slot=cache_root/hashlib.sha256(version.encode()).hexdigest()/'aarch64-apple-darwin'
            archive='a'*64;obj=slot/'objects'/archive;obj.mkdir(parents=True)
            cached=obj/'empack';shutil.copyfile(fixture,cached);cached.chmod(0o700)
            record={'kind':'empack-engine/1','version':version,'target':'aarch64-apple-darwin',
                    'archive':archive,'executable':sha(cached),'bytes':str(cached.stat().st_size)}
            if cache=='corrupt':cached.write_bytes(cached.read_bytes()+b'\n# changed after metadata\n')
            if cache=='wrong-target':record['target']='x86_64-apple-darwin'
            (slot/'ready.properties').write_text(''.join(k+'='+v+'\n'for k,v in record.items()))
        args=['--fixture-echo','Ω 日本','value with spaces']
        if signal_kind:args=['--fixture-wait']
        if name=='wrong-peer':args=['--fixture-wrong-peer']
        if native:
            source=ROOT/'applications/evidence/empack-pending-20261125T065233392919Z'
            for doc in ['empack.yml','empack.lock']:shutil.copyfile(source/('initial-'+doc),base/doc)
            args=['--state-dir',str(case/'native-state'),'--cache-dir',str(case/'native-cache'),
                  '--workdir',str(base),'--yes','--color','never','check','--json']
        record=dict(schema='empack-bootstrap-invocation/1',engine_version=version,arguments=args,append_arguments=append)
        path=tools/'run.json';path.write_text(json.dumps(record,ensure_ascii=False))
        if edit:edit(path,record)
        flags=['--cache',str(cache_root),'--offline']
        if explicit:flags+=['--engine',str(ENGINE if native else fixture)]
        if extra:flags+=extra
        if mode=='record':flags+=['--invocation-file',str(path.relative_to(base))]
        elif mode=='wrong-name':
            renamed=tools/'日本.json';path.rename(renamed);flags+=['--invocation-file',str(renamed.relative_to(base))]
        else:flags+=['--engine-version',version,'--',*args]
        if mode in ['record','wrong-name']and dynamic is not None:flags+=['--',*dynamic]
        env=dict(PATH='/usr/bin:/bin',HOME=str(home),TMPDIR=str(case),LANG=locale,LC_ALL=locale,
                 RULES_ENGINE_LOG=str(log),RULES_DISTRIBUTION=str(dist),RULES_ENGINE_VERSION=engine_version,
                 RULES_DIST_VERSION='9.9.9'if local=='wrong-version'else engine_version,
                 RULES_ENGINE_PROTOCOL=protocol,EMPACK_BOOTSTRAP_CONTROL='1:inherited-invalid-fixture',
                 HTTP_PROXY='http://127.0.0.1:9',HTTPS_PROXY='http://127.0.0.1:9',ALL_PROXY='http://127.0.0.1:9',NO_PROXY='')
        scopes=['Pack Ω 日本','cache','native-state','native-cache','home']
        before={n:snapshot(case/n)for n in scopes}
        argv=[str(JAVAS[major]),'-Dfile.encoding=UTF-8','-Duser.home='+str(home),'-jar',str(jar),*flags]
        with (run/(name+'.stdout')).open('xb')as out,(run/(name+'.stderr')).open('xb')as err:
            child=subprocess.Popen(argv,cwd=base,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
            children.append(child);start=time.monotonic();timed=False;sent=None
            write(run/'processes.json',[dict(pid=p.pid,retired=p.poll()is not None)for p in children])
            if signal_kind:
                deadline=start+10
                while time.monotonic()<deadline:
                    events=[json.loads(s)for s in log.read_text().splitlines()]if log.exists()else[]
                    if any(e['kind']=='started'for e in events):break
                    assert child.poll()is None,'Child exited before signal control'
                    time.sleep(0.02)
                else:raise AssertionError('No authenticated fixture start')
                sent=signal.SIGTERM if signal_kind=='cancel'else signal.SIGKILL
                os.kill(child.pid,sent)
            try:child.wait(timeout=25)
            except subprocess.TimeoutExpired:
                timed=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
        deadline=time.monotonic()+3;absent=False
        while time.monotonic()<deadline:
            try:os.killpg(child.pid,0)
            except ProcessLookupError:absent=True;break
            time.sleep(0.02)
        events=[json.loads(s)for s in log.read_text().splitlines()]if log.exists()else[]
        after={n:snapshot(case/n)for n in scopes}
        result=dict(case=name,java=major,locale=locale,argv=argv,exitCode=child.returncode,timedOut=timed,
            signalSent=int(sent)if sent else None,ownedGroupAbsent=absent,seconds=time.monotonic()-start,
            request=dict(mode=mode,explicit=explicit,local=local,cache=cache,append=append,dynamic=dynamic,
                         version=version,protocol=protocol,engineVersion=engine_version,nativeEngine=native),
            before=before,after=after,events=events,
            streams={s:sha(run/(name+'.'+s))for s in ['stdout','stderr']})
        commands.append(result);write(run/'commands.json',commands)
        write(run/'processes.json',[dict(pid=p.pid,retired=p.poll()is not None)for p in children])
        assert not timed and absent,(name,result)
    try:
        execute('static-append',dynamic=['runtime Ω 日本'])
        execute('append-refused',append=False,dynamic=['runtime'])
        execute('unknown-schema',edit=lambda p,r:p.write_text(json.dumps(dict(r,schema='future'))))
        execute('unknown-field',edit=lambda p,r:p.write_text(json.dumps(dict(r,unexpected=True))))
        execute('duplicate-field',edit=lambda p,r:p.write_text(json.dumps(r)[:-1]+',"append_arguments":true}'))
        execute('malformed-utf8',edit=lambda p,r:p.write_bytes(b'\xff'))
        execute('wrong-record-name',mode='wrong-name')
        def link_record(p,r):
            target=p.with_name('original.json');p.rename(target);p.symlink_to(target.name)
        execute('linked-record',edit=link_record)
        execute('direct-argv',mode='direct')
        for name,version in [('v-prefix','v0.8.8-beta'),('range','^0.8.8'),('build-metadata','0.8.8+one'),('leading-prerelease','0.8.8-01')]:
            execute(name,mode='direct',version=version)
        execute('development-explicit',engine_version='0.0.0-dev',extra=['--development-engine'])
        execute('wrong-explicit-version',engine_version='9.9.9')
        execute('wrong-protocol',protocol='other/1')
        execute('distribution-local',explicit=False,local='valid')
        execute('local-refused-cache-used',explicit=False,local='wrong-version',cache='valid')
        execute('warm-cache',explicit=False,cache='valid')
        execute('cache-corrupt',explicit=False,cache='corrupt')
        execute('cache-wrong-target',explicit=False,cache='wrong-target')
        execute('empty-offline',explicit=False)
        execute('wrong-peer')
        execute('cancel-result',signal_kind='cancel')
        execute('parent-loss',signal_kind='kill')
        for major in [17,21,25]:
            execute('native-check-'+str(major),major=major,native=True)
        execute('native-check-25-C',major=25,native=True,locale='C')
        write(run/'receipt.json',dict(schema=1,status='complete',commands=len(commands),allOwnedGroupsRetired=True,
            producerSha256=sha(run/'probe.py'),jarSha256=sha(jar),nativeEngineSha256=sha(ENGINE),
            limits=['Script engines are controlled peers,not native empack/runtime ownership.','Sixteen-byte? No synthetic credential or connection nonce is recorded.','Only three normal-locale and one Java25 C-locale read-only native check;no game/provider/runtime test.','Cache metadata is authored private fixture state,not authenticated official publication.','No Java8,Windows/Linux,download,archive extraction,power-loss or hostile-writer qualification.']))
        print(json.dumps(dict(run=str(run.relative_to(ROOT)),commands=len(commands),status='complete')))
    finally:
        for child in children:
            if child.poll()is None:
                os.killpg(child.pid,signal.SIGKILL);child.wait()
        write(run/'processes.json',[dict(pid=p.pid,retired=p.poll()is not None)for p in children])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','collect']);p.add_argument('run',type=Path,nargs='?');a=p.parse_args()
    if a.action=='prepare':prepare()
    else:
        assert a.run;collect(a.run)
if __name__=='__main__':main()
