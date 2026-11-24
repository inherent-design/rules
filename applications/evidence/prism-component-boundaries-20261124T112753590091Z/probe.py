#!/usr/bin/env python3
"""Owner-run component codec/cache and bounded removal-loop comparisons."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = Path(__file__).read_bytes()
sha = lambda data: hashlib.sha256(data).hexdigest()


def main():
    original = ROOT / 'applications/evidence/prism-components-20261124T111134328480Z'
    prior = json.loads((original / 'receipt.json').read_text())
    for name, digest in prior['generatedSha256'].items():
        assert sha((original / 'work' / name).read_bytes()) == digest
    selections = json.loads((ROOT / 'applications/sources/prism-components-selections.json').read_text())
    selected = {r['path']: (ROOT / r['cache']).read_bytes() for r in selections}
    for r in selections:
        assert sha(selected[r['path']]) == r['sha256']
    profile = selected['launcher/minecraft/PackProfile.cpp'].decode()
    component = selected['launcher/minecraft/Component.cpp'].decode()
    task = selected['launcher/minecraft/ComponentUpdateTask.cpp'].decode()
    meta_source = selected['launcher/meta/JsonFormat.cpp'].decode()

    def section(text, start, end):
        assert text.count(start) == 1 and text.count(end) == 1, (start, end)
        return text[text.index(start):text.index(end, text.index(start))]

    codec = section(profile, 'static QJsonObject componentToJsonV1', '\n// Save the given component container')
    removal = section(profile, 'bool PackProfile::remove(const int index)', '\nbool PackProfile::customize(')
    physical = section(profile, 'bool PackProfile::removeComponent_internal', '\nbool PackProfile::installJarMods_internal')
    loop = section(task, 'void ComponentUpdateTask::resolveDependencies(bool checkOnly)', '\n    RequireExSet toAdd;') + '\n}\n'
    refresh = section(component, 'static bool deepCompare(', '\nvoid Component::waitLoadMeta()')
    methods = [section(component, start, end) for start, end in [
        ('QString Component::getID()', '\nQString Component::getName()'),
        ('QString Component::getFilename()', '\nQDateTime Component::getReleaseDateTime()'),
        ('std::shared_ptr<class VersionFile> Component::getVersionFile()', '\nstd::shared_ptr<class Meta::VersionList> Component::getVersionList()'),
        ('bool Component::setEnabled(', '\nbool Component::isCustom()')]]
    parse = section(meta_source, 'void parseRequires(', '\n}  // namespace Meta')
    base = (original / 'work/main.cpp').read_text()
    base = base[:base.index('QJsonArray requirements(')]
    old_decl = section(base, 'class Component {', '// Pointer ownership/loading/QObject')
    decl = r'''
class PackProfile;
struct LibraryStub {
 bool isLocal()const{return false;}
 void getApplicableFiles(int,QStringList&,QStringList&,QStringList&,QStringList&,const QString&){}
};
using LibraryPtr=std::shared_ptr<LibraryStub>;
class VersionFile {
public:
 QString name,version;bool m_volatile=false;
 std::set<Meta::Require> m_requires,conflicts;
 QList<LibraryPtr> jarMods;
};
struct MetaVersionStub {std::shared_ptr<VersionFile> value;std::shared_ptr<VersionFile> data(){return value;}};
class Component {
public:
 PackProfile*m_parent=nullptr;
 QString m_uid,m_version,m_cachedVersion,m_cachedName;
 std::set<Meta::Require> m_cachedRequires,m_cachedConflicts;
 bool m_dependencyOnly=false,m_cachedVolatile=false,m_disabled=false,m_important=false;
 std::shared_ptr<VersionFile> m_file;std::shared_ptr<MetaVersionStub> m_metaVersion;
 int notifications=0;
 Component(PackProfile*p=nullptr,QString uid={}):m_parent(p),m_uid(uid){}
 void dataChanged(){notifications++;}
 QString getID();QString getVersion();QString getFilename();bool isCustom();bool isEnabled();bool canBeDisabled();bool isRemovable();
 bool setEnabled(bool);void updateCachedData();std::shared_ptr<VersionFile>getVersionFile()const;
};
'''
    base = base.replace(old_decl, decl)
    support = r'''
#include <QDir>
#include <QFileInfo>
#include <QModelIndex>
#include <stdexcept>
#include <sys/stat.h>
Q_LOGGING_CATEGORY(instanceProfileC,"rules.fixture.profile-removal")
namespace Json {
QJsonObject requireObject(const QJsonValue&v){if(!v.isObject())throw std::runtime_error("fixture expected object");return v.toObject();}
QJsonArray requireArray(const QJsonObject&o,const char*k){auto v=o.value(k);if(!v.isArray())throw std::runtime_error("fixture expected array");return v.toArray();}
QString requireString(const QJsonValue&v){if(!v.isString())throw std::runtime_error("fixture expected string");return v.toString();}
QString requireString(const QJsonObject&o,const char*k){return requireString(o.value(k));}
}
namespace Meta {
using namespace Json;
using RequireSet=std::set<Require>;
__PARSE__
}
template<class T,class...A>std::shared_ptr<T>makeShared(A&&...a){return std::make_shared<T>(std::forward<A>(a)...);}
struct ProbeLimit:std::runtime_error{ProbeLimit():std::runtime_error("three completed removal attempts; fixture guard"){};};
struct InstanceStub{QString name(){return "fixture";}int runtimeContext(){return 0;}QDir jarmodsPath(){return {};}};
struct ProfileDataStub {
 ComponentContainer components;ComponentIndex componentIndex;InstanceStub*m_instance=nullptr;
 int attempts=0,saveRequests=0,invalidations=0;
};
class PackProfile {
public:
 std::unique_ptr<ProfileDataStub>d=std::make_unique<ProfileDataStub>();InstanceStub instance;QString root;
 explicit PackProfile(QString r):root(r){d->m_instance=&instance;}
 QString patchFilePathForUid(const QString&uid){return root+"/"+uid+".json";}
 ComponentPtr getComponent(int index){if(++d->attempts>3)throw ProbeLimit();return d->components.at(index);}
 bool remove(int);bool remove(const QString&);bool removeComponent_internal(ComponentPtr);
 void beginRemoveRows(QModelIndex,int,int){}void endRemoveRows(){}
 void invalidateLaunchProfile(){d->invalidations++;}void scheduleSave(){d->saveRequests++;}
};
struct TaskDataStub {PackProfile*m_profile;};
class ComponentUpdateTask {
public:
 TaskDataStub*d;bool finalized=false;QString failure;
 explicit ComponentUpdateTask(TaskDataStub*data):d(data){}
 void resolveDependencies(bool);void finalizeComponents(){finalized=true;}
 void emitFailed(QString s){failure=s;}QString tr(const char*s){return QString::fromUtf8(s);}
};
'''
    support = support.replace('__PARSE__', parse)
    source = base + support + '\n'.join(methods) + refresh + codec + removal + physical + loop
    main = r'''
QJsonObject cached(ComponentPtr c){
 return {{"uid",c->m_uid},{"version",c->m_version},{"cachedVersion",c->m_cachedVersion},{"cachedName",c->m_cachedName},
  {"volatile",c->m_cachedVolatile},{"requires",int(c->m_cachedRequires.size())},{"conflicts",int(c->m_cachedConflicts.size())},
  {"requiredExact",c->m_cachedRequires.empty()?QString():c->m_cachedRequires.begin()->equalsVersion},
  {"notifications",c->notifications}};
}
void emitRow(QJsonObject row){std::cout<<QJsonDocument(row).toJson(QJsonDocument::Compact).toStdString()<<"\n";}
int main(int argc,char**argv){
 QCoreApplication app(argc,argv);if(argc!=2)return 2;QString root=QString::fromLocal8Bit(argv[1]);
 for(bool bit:{false,true}){
  PackProfile p(root);auto c=std::make_shared<Component>(&p,"fixture.codec");
  c->m_version=c->m_cachedVersion="1";c->m_cachedName="Fixture";c->m_dependencyOnly=true;c->m_cachedVolatile=bit;
  c->m_cachedRequires.insert({"fixture.dep","1",""});c->m_cachedConflicts.insert({"fixture.bad","2",""});
  auto wire=componentToJsonV1(c);auto decoded=componentFromJsonV1(&p,root+"/%1.json",wire);auto before=cached(decoded);
  decoded->updateCachedData();auto missing=cached(decoded);
  auto file=std::make_shared<VersionFile>();file->name="Fixture";file->version="1";file->m_volatile=bit;
  file->m_requires=c->m_cachedRequires;file->conflicts=c->m_cachedConflicts;
  decoded->m_metaVersion=std::make_shared<MetaVersionStub>();decoded->m_metaVersion->value=file;
  decoded->updateCachedData();auto loaded=cached(decoded);
  decoded->updateCachedData();auto repeated=cached(decoded);
  file->m_requires.clear();file->m_requires.insert({"fixture.dep","3",""});decoded->updateCachedData();auto changed=cached(decoded);
  emitRow({{"kind","codec-cache"},{"inputVolatile",bit},{"wire",wire},{"decoded",before},{"missingMetadata",missing},
   {"loadedMetadata",loaded},{"repeatedMetadata",repeated},{"changedExactSameUid",changed},{"qtRuntime",qVersion()}});
 }
 struct Case{const char*id;bool readOnly,important,checkOnly;};
 for(auto test:{Case{"remove-success",false,false,false},Case{"read-only-remove-failure",true,false,false},
   Case{"check-only-remove-success",false,false,true},Case{"check-only-read-only-failure",true,false,true},Case{"important-remove-refusal",false,true,false}}){
  QString path=root+"/"+test.id;QDir().mkpath(path);PackProfile p(path);
  auto c=std::make_shared<Component>(&p,"fixture.volatile");c->m_dependencyOnly=true;c->m_cachedVolatile=true;c->m_important=test.important;
  p.d->components.append(c);p.d->componentIndex.insert(c->m_uid,c);
  QFile patch(c->getFilename());if(!patch.open(QIODevice::WriteOnly))return 3;patch.write("{}\n");patch.close();
  struct stat info;auto bytes=path.toLocal8Bit();if(stat(bytes.constData(),&info))return 3;mode_t original=info.st_mode&0777;
  if(test.readOnly&&chmod(bytes.constData(),0555))return 3;
  bool guarded=false,prefixCompleted=false;TaskDataStub td{&p};ComponentUpdateTask task(&td);
  try{task.resolveDependencies(test.checkOnly);prefixCompleted=true;}catch(const ProbeLimit&){guarded=true;}
  if(chmod(bytes.constData(),original))return 3;
  struct stat restored;if(stat(bytes.constData(),&restored))return 3;
  emitRow({{"kind","removal-loop-prefix"},{"id",test.id},{"readOnly",test.readOnly},{"important",test.important},{"checkOnly",test.checkOnly},
   {"guarded",guarded},{"prefixCompleted",prefixCompleted},{"attemptsIncludingGuard",p.d->attempts},
   {"remainingComponents",p.d->components.size()},{"patchExistsAfter",QFile::exists(c->getFilename())},
   {"saveRequests",p.d->saveRequests},{"invalidations",p.d->invalidations},{"taskFinalized",task.finalized},{"taskFailure",task.failure},
   {"directoryModeBefore",int(original)},{"directoryModeRestored",int(restored.st_mode&0777)},{"qtRuntime",qVersion()}});
 }
}
'''
    source += main
    run = ROOT / 'applications/evidence' / ('prism-component-boundaries-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    work = run / 'work'
    (work / 'home').mkdir(parents=True)
    (work / 'tmp').mkdir()
    (work / 'fixtures').mkdir()
    (run / 'probe.py').write_bytes(PRODUCER)
    (work / 'main.cpp').write_text(source)
    for name in ['Version.cpp', 'Version.h']:
        (work / name).write_bytes((original / 'work' / name).read_bytes())
    pkg = '/opt/homebrew/bin/pkg-config'
    qt = subprocess.check_output([pkg, '--modversion', 'Qt6Core'], text=True).strip()
    assert qt == prior['qtVersion'] and qt.startswith('6.')
    flags = shlex.split(subprocess.check_output([pkg, '--cflags', '--libs', 'Qt6Core'], text=True))
    lib = subprocess.check_output([pkg, '--variable=libdir', 'Qt6Core'], text=True).strip()
    env = dict(PATH='/usr/bin:/bin', HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'), LANG='en_US.UTF-8')
    argv = ['/usr/bin/clang++', '-std=c++20', '-O0', '-DQT_NO_DEBUG', '-include', 'algorithm', '-I' + str(work),
        str(work / 'main.cpp'), str(work / 'Version.cpp'), '-o', str(work / 'probe'), *flags, '-Wl,-rpath,' + lib]
    build = subprocess.run(argv, env=env, capture_output=True, timeout=90)
    (run / 'compile.stdout').write_bytes(build.stdout)
    (run / 'compile.stderr').write_bytes(build.stderr)
    if build.returncode:
        (run / 'failed-build.json').write_text(json.dumps(dict(argv=argv, exitCode=build.returncode, producerSha256=sha(PRODUCER)), indent=2) + '\n')
        raise RuntimeError('Compile failed; retained diagnostics: ' + str(run))
    binary = sha((work / 'probe').read_bytes())
    try:
        execute = subprocess.run([str(work / 'probe'), str(work / 'fixtures')], env=env, capture_output=True, timeout=20)
    finally:
        for directory in (work / 'fixtures').iterdir():
            if directory.is_dir():
                os.chmod(directory, 0o755)
    (run / 'observed.stdout').write_bytes(execute.stdout)
    (run / 'observed.stderr').write_bytes(execute.stderr)
    assert execute.returncode == 0
    rows = [json.loads(line) for line in execute.stdout.splitlines()]
    assert len(rows) == 7 and {r['qtRuntime'] for r in rows} == {qt}
    rec = dict(schema=1, producerSha256=sha(PRODUCER), reusedCapture=str(original.relative_to(ROOT)),
        reusedReceiptSha256=sha((original / 'receipt.json').read_bytes()), sourceRevision=prior['sourceRevision'],
        sources={r['path']: r['sha256'] for r in selections},
        fragmentsSha256={key: sha(text.encode()) for key, text in dict(codec=codec, removal=removal, physicalRemoval=physical,
            removalLoopPrefix=loop, refresh=refresh, requireParser=parse).items()},
        generatedSha256={p.name: sha(p.read_bytes()) for p in work.glob('*') if p.is_file() and p.suffix in ['.cpp', '.h']},
        binarySha256=binary, compileCommand=argv, compileExit=build.returncode, executeExit=execute.returncode,
        qtVersion=qt, platform=platform.platform(), architecture=platform.machine(), uid=os.getuid(), cases=len(rows),
        stdoutSha256=sha(execute.stdout), stderrSha256=sha(execute.stderr),
        limits=['Selected codecs, Require parser/serializer bodies, cache refresh, removal methods and removal-loop prefix are unchanged pinned source; primary decision fragments reused unchanged.',
            'QObject/constructor/loading/JSON conversion/row notifications/save scheduling and no-local-JAR library interfaces are fixture adapters. Valid JSON objects and required fields only; not the actual native parser/constructor pipeline.',
            'Removal prefix ends before the caller change-planning/checkOnly tail. A getComponent adapter throws before a fourth removal attempt to bound repeated failure; no claim the product itself has this guard.',
            'Read-only removal uses actual owned directory chmod0555 and QFile deletion; directory modes restored. No personal instance or game paths accessed.',
            'Metadata snapshots are supplied in memory; no remote acquisition or actual cache/root persistence. Scheduled saves are counters, not durable receipts.'])
    assert sha((work / 'probe').read_bytes()) == binary
    (run / 'receipt.json').write_text(json.dumps(rec, indent=2) + '\n')
    print(json.dumps(dict(run=str(run), observations=rows), indent=2))


if __name__ == '__main__':
    main()
