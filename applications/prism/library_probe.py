#!/usr/bin/env python3
"""Selected Prism library methods with real Qt/private files; no OS trash/GUI."""
from datetime import datetime,timezone
import hashlib,json,os,shlex,signal,subprocess,tempfile,time
from pathlib import Path
from java_probe import function
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;PRODUCER=Path(__file__).read_bytes();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def main():
    cache=ROOT/'applications/tools/source-cache/prism-instances';sources={}
    for name in['InstanceList.cpp','InstanceList.h','BaseInstance.cpp','BaseInstance.h']:sources[name]=(cache/('launcher__'+name)).read_text()
    run=ROOT/'applications/evidence'/('prism-library-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir();work=Path(tempfile.mkdtemp(prefix='rules-prism-library-',dir='/private/tmp'))
    for n in['home','tmp','cases']:(work/n).mkdir()
    (run/'probe.py').write_bytes(PRODUCER);(run/'driver.cpp').write_bytes((HERE/'library_driver.cpp').read_bytes());bodies=[];cuts=[]
    signatures=['int InstanceList::rowCount(','QModelIndex InstanceList::index(','QVariant InstanceList::data(','bool InstanceList::setData(','BaseInstance* InstanceList::getInstanceById(','int InstanceList::getInstIndex(','GroupId InstanceList::getInstanceGroup(','void InstanceList::setInstanceGroup(','QStringList InstanceList::getGroups(','void InstanceList::deleteGroup(','void InstanceList::renameGroup(','bool InstanceList::isGroupCollapsed(','void InstanceList::increaseGroupCount(','void InstanceList::decreaseGroupCount(','void InstanceList::saveGroupList(','void InstanceList::loadGroupList(','bool InstanceList::trashInstance(','bool InstanceList::trashedSomething(','bool InstanceList::undoTrashInstance(','void InstanceList::deleteInstance(','QList<InstanceId> InstanceList::discoverInstances(']
    for name,sigs in[('InstanceList.cpp',signatures),('BaseInstance.cpp',['QString BaseInstance::id(','void BaseInstance::setName(','bool BaseInstance::syncInstanceDirName('])]:
        for sig in sigs:
            body=function(sources[name],sig);bodies.append(body);cuts.append(dict(path='launcher/'+name,signature=sig,sha256=hashlib.sha256(body.encode()).hexdigest(),transformation='none'))
    current=function(sources['InstanceList.cpp'],'void InstanceList::setInstanceGroup(');candidate=current.replace('InstanceList::setInstanceGroup(', 'InstanceList::setInstanceGroupCanonical(').replace('m_instanceGroupIndex[id] = name;','m_instanceGroupIndex[inst->id()] = name;');assert candidate!=current and candidate.count('m_instanceGroupIndex[inst->id()] = name;')==1
    bodies.append(candidate);source=(run/'driver.cpp').read_text().replace('__BODIES__','\n'.join(bodies));(work/'main.cpp').write_text(source)
    pkg='/opt/homebrew/bin/pkg-config';flags=shlex.split(subprocess.check_output([pkg,'--cflags','--libs','Qt6Core'],text=True));lib=Path(subprocess.check_output([pkg,'--variable=libdir','Qt6Core'],text=True).strip())
    env=dict(PATH='/opt/homebrew/bin:/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8',QT_HASH_SEED='0')
    commands=[]
    def command(id,argv,timeout):
        start=time.monotonic()
        with(run/(id+'.stdout')).open('wb')as out,(run/(id+'.stderr')).open('wb')as err:
            p=subprocess.Popen(argv,env=env,stdout=out,stderr=err,start_new_session=True)
            try:code=p.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
                raise
        try:os.killpg(p.pid,0);absent=False
        except ProcessLookupError:absent=True
        c=dict(id=id,argv=argv,pid=p.pid,exitCode=code,seconds=time.monotonic()-start,ownedGroupAbsent=absent);commands.append(c);write(run/'commands.json',commands);assert code==0,(run/(id+'.stderr')).read_text()[-2500:];assert absent
    binary=work/'library-driver';command('compile',['/usr/bin/clang++','-std=c++20','-O0',str(work/'main.cpp'),'-o',str(binary),*flags,'-Wl,-rpath,'+str(lib)],90)
    command('observe',[str(binary),str(work/'cases')],15)
    rows=[json.loads(s)for s in(run/'observe.stdout').read_text().splitlines()];assert len(rows)==24;write(run/'observed.json',dict(schema=1,rows=rows))
    ps=subprocess.check_output(['ps','-axo','pid=,ppid=,args='],text=True);hits=[s for s in ps.splitlines()if str(work)in s and 'python3 - <<'not in s];assert not hits,hits
    write(run/'receipt.json',dict(schema=1,work=str(work),producerSha256=sha(run/'probe.py'),driverSha256=sha(run/'driver.cpp'),helperSha256=sha(HERE/'java_probe.py'),sources=[dict(path='launcher/'+n,sha256=hashlib.sha256(s.encode()).hexdigest())for n,s in sources.items()],excerpts=cuts,candidateSha256=hashlib.sha256(candidate.encode()).hexdigest(),generatedSha256=sha(work/'main.cpp'),binarySha256=sha(binary),compilerSha256=sha(Path('/usr/bin/clang++')),compiler=subprocess.check_output(['/usr/bin/clang++','--version'],text=True),qtVersion=subprocess.check_output([pkg,'--modversion','Qt6Core'],text=True).strip(),frameworkSha256=sha(lib/'QtCore.framework/Versions/A/QtCore'),workspaceProcessHits=hits,privateKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),limits=['Selected unchanged method bodies;adapter BaseInstance/SettingsObject,WatchLock/signals and private trash/FS operations.','No launcher constructor,real INI backend,watcher,GUI,OS trash,account,game or user data.','Canonical insertion is a separately identified private candidate,not a product patch.']))
    print(json.dumps(dict(run=str(run.relative_to(ROOT)),rows=len(rows),work=str(work))))
if __name__=='__main__':main()
