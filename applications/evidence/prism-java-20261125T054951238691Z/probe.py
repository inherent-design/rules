#!/usr/bin/env python3
"""Selected Prism settings/check methods with Qt and declared adapters; no JVM."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = Path(__file__).read_bytes()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def function(text, signature):
    assert text.count(signature) == 1, signature
    start = text.index(signature)
    mask = re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
                  lambda m: ' ' * len(m.group()), text, flags=re.S)
    first = mask.index('{', start)
    depth = 0
    for end in range(first, len(mask)):
        depth += (mask[end] == '{') - (mask[end] == '}')
        if depth == 0:
            return text[start:end + 1]
    raise AssertionError(signature)


def main():
    ledger = json.loads((ROOT / 'applications/sources/prism-java-selections.json').read_text())
    selected = {}
    for row in ledger['sources']:
        path = ROOT / row['cache']
        assert sha(path) == row['sha256']
        selected[row['path']] = path.read_text()
    run = ROOT / 'applications/evidence' / ('prism-java-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'
    for directory in ['settings', 'home', 'tmp']:
        (work / directory).mkdir(parents=True)
    (run / 'probe.py').write_bytes(PRODUCER)
    copied = {}
    for name in ['Setting.h', 'Setting.cpp', 'OverrideSetting.h', 'OverrideSetting.cpp',
                 'PassthroughSetting.h', 'PassthroughSetting.cpp']:
        path = 'launcher/settings/' + name
        target = work / name
        target.write_text(selected[path])
        copied[path] = sha(target)
    (work / 'JavaVersion.h').write_text(selected['launcher/java/JavaVersion.h'])
    copied['launcher/java/JavaVersion.h'] = sha(work / 'JavaVersion.h')
    # Storage is deliberately synchronous in memory. No INI, bookmarks, save
    # locks, disk publication or real SettingsObject lifetime is exercised.
    (work / 'settings/SettingsObject.h').write_text(r'''#pragma once
#include <QObject>
#include <QMap>
#include "Setting.h"
class SettingsObject : public QObject {
public:
 QMap<QString,QVariant> values;
 QMap<QString,std::shared_ptr<Setting>> fields;
 QVariant retrieveValue(const Setting& s) const { return values.value(s.id()); }
 void attach(std::shared_ptr<Setting> s) {
  s->m_storage=this;fields.insert(s->id(),s);
  QObject::connect(s.get(),&Setting::SettingChanged,this,[this](const Setting&s,QVariant v){values[s.id()]=v;});
  QObject::connect(s.get(),&Setting::settingReset,this,[this](const Setting&s){values.remove(s.id());});
 }
 std::shared_ptr<Setting> add(QString key,QVariant def) {auto s=std::make_shared<Setting>(QStringList{key},def);attach(s);return s;}
 QVariant get(QString key) {auto s=fields.value(key);return s?s->get():QVariant();}
 void set(QString key,QVariant v) {fields.value(key)->set(v);}
};
''')
    excerpts = []

    def take(path, signature):
        body = function(selected[path], signature)
        excerpts.append(dict(path=path, signature=signature, sha256=hashlib.sha256(body.encode()).hexdigest(), transformation='none'))
        return body

    version = '\n'.join(take('launcher/java/JavaVersion.cpp', s) for s in [
        'JavaVersion& JavaVersion::operator=(const QString& javaVersionString)',
        'JavaVersion::JavaVersion(const QString& rhs)', 'QString JavaVersion::toString() const'])
    check = '\n'.join(take('launcher/launch/steps/CheckJava.cpp', s) for s in [
        'void CheckJava::executeTask()', 'void CheckJava::checkJavaFinished(const JavaChecker::Result& result)',
        'void CheckJava::printJavaInfo(const QString& version, const QString& architecture, const QString& realArchitecture, const QString& vendor)'])
    verify = take('launcher/minecraft/launch/VerifyJavaInstall.cpp', 'void VerifyJavaInstall::executeTask()')
    source = r'''
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDateTime>
#include <QDebug>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QRegularExpression>
#include <QStandardPaths>
#include <iostream>
#include <memory>
#include "settings/SettingsObject.h"
#include "OverrideSetting.h"
#include "PassthroughSetting.h"
#include "JavaVersion.h"
__VERSION__
namespace MessageLevel {enum Enum{Warning,Launcher,Fatal,Error};}
namespace FS {QString ResolveExecutable(QString p){return p;}}
namespace JavaUtils {QString checker;QString getJavaCheckPath(){return checker;}}
struct Profile {
 QList<int> majors;Profile* getProfile(){return this;}
 QList<int> getCompatibleJavaMajors(){return majors;}
};
struct Instance {
 SettingsObject store;Profile profile;int contextUpdates=0;
 SettingsObject* settings(){return &store;}
 Profile* getPackProfile(){return &profile;}
 void updateRuntimeContext(){contextUpdates++;}
};
struct Parent {Instance inst;Instance* instance(){return &inst;}};
struct Step {
 Parent* m_parent;bool succeeded=false,failed=false;QString reason;QJsonArray logs;
 explicit Step(Parent*p):m_parent(p){}
 static QString tr(const char*s){return QString::fromUtf8(s);}
 void emitSucceeded(){succeeded=true;}void emitFailed(QString s){failed=true;reason=s;}
 void logLine(QString text,MessageLevel::Enum level){logs.append(QJsonObject{{"text",text},{"level",int(level)}});}
 void logLines(QStringList lines,MessageLevel::Enum level){for(auto line:lines)logLine(line,level);}
};
// Result delivery and task ownership are explicit fixture inputs. This class
// never starts a process, and the source connect call below is a no-op adapter.
struct JavaChecker {
 struct Result {
  enum class Validity{Errored,ReturnedInvalidData,Valid};
  Validity validity;QString errorLog,outLog;JavaVersion javaVersion;
  QString mojangPlatform,realPlatform,javaVendor;
 };
 bool started=false;JavaChecker(QString,QString,int,int,int,int){}
 void start(){started=true;}void checkFinished(const Result&){}
};
template<class... Args> void connect(Args...){ }
struct CheckJava:Step {
 using Step::Step;QString m_javaPath,m_javaSignature;std::unique_ptr<JavaChecker> m_JavaChecker;
 void executeTask();void checkJavaFinished(const JavaChecker::Result&);
 void printJavaInfo(const QString&,const QString&,const QString&,const QString&);
};
struct VerifyJavaInstall:Step {using Step::Step;void executeTask();};
__CHECK__
__VERIFY__
void pair(SettingsObject&g,SettingsObject&i,std::shared_ptr<Setting>gate,QString name,QVariant def,bool pass) {
 auto global=g.add(name,def);
 if(pass)i.attach(std::make_shared<PassthroughSetting>(global,gate));
 else i.attach(std::make_shared<OverrideSetting>(global,gate));
}
QJsonObject values(SettingsObject&s){return QJsonObject::fromVariantMap(s.values);}
QJsonObject snapshot(SettingsObject&g,SettingsObject&i,QString key){
 auto s=i.fields.value(key);return {{"global",g.get(key).toString()},{"local",i.values.contains(key)?QJsonValue(i.values[key].toString()):QJsonValue::Null},
 {"effective",s->get().toString()},{"default",s->defValue().toString()}};
}
int main(int argc,char**argv){
 QCoreApplication app(argc,argv);if(argc!=3)return 2;
 QFile file(QString::fromLocal8Bit(argv[1]));if(!file.open(QIODevice::ReadOnly))return 2;
 QJsonParseError error;auto doc=QJsonDocument::fromJson(file.readAll(),&error);
 if(error.error!=QJsonParseError::NoError||doc.object()["schema"].toInt()!=1)return 2;
 for(auto raw:doc.object()["cases"].toArray()){
  auto c=raw.toObject();auto kind=c["kind"].toString();QJsonObject out{{"id",c["id"]},{"kind",kind},{"qtRuntime",qVersion()}};
  if(kind=="setting"){
   SettingsObject g,i;auto gate=i.add("gate",c["gate"].toBool());
   pair(g,i,gate,"value",c["globalDefault"].toString(),c["passthrough"].toBool());
   g.values["value"]=c["global"].toString();if(!c["local"].isNull())i.values["value"]=c["local"].toString();
   QJsonArray trace;trace.append(snapshot(g,i,"value"));
   for(auto r:c["actions"].toArray()){
    auto a=r.toObject();auto op=a["op"].toString();
    if(op=="set")i.set("value",a["value"].toString());
    else if(op=="global")g.set("value",a["value"].toString());
    else if(op=="gate")gate->set(a["value"].toBool());
    else if(op=="reset")i.fields["value"]->reset();else return 2;
    trace.append(snapshot(g,i,"value"));
   }out["trace"]=trace;
  }else if(kind=="pipeline"){
   Parent parent;SettingsObject g;auto&i=parent.inst.store;auto gate=i.add("OverrideJavaLocation",c["override"].toBool());
   i.add("OverrideJava",false);auto path=QString::fromLocal8Bit(argv[2]);
   if(!c["executable"].toBool())path+=".missing";
   pair(g,i,gate,"JavaPath",path,false);
   pair(g,i,gate,"IgnoreJavaCompatibility",c["ignore"].toBool(),false);
   i.add("MaxMemAlloc",c["memory"].toInt());
   const QStringList keys{"JavaVersion","JavaArchitecture","JavaRealArchitecture","JavaVendor","JavaSignature"};
   for(auto key:keys)pair(g,i,gate,key,"",true);
   auto stored=c["stored"].toObject();for(auto key:keys)g.values[key]=stored[key].toString();
   QCryptographicHash h(QCryptographicHash::Sha1);h.addData(QByteArray::number(QFileInfo(path).lastModified().toMSecsSinceEpoch()));h.addData(path.toUtf8());
   auto current=QString::fromLatin1(h.result().toHex());
   g.values["JavaSignature"]=c["signatureMatches"].toBool()?current:QString("old");
   for(auto m:c["majors"].toArray())parent.inst.profile.majors.append(m.toInt());
   JavaUtils::checker=c["checkerAvailable"].toBool()?QString("fixture-checker.jar"):QString();
   CheckJava task(&parent);task.executeTask();bool probed=bool(task.m_JavaChecker);
   if(probed){JavaChecker::Result result;result.validity=static_cast<JavaChecker::Result::Validity>(c["probe"].toInt());
    result.javaVersion=c["resultVersion"].toString();result.mojangPlatform=c["resultArch"].toString();
    result.realPlatform="aarch64";result.javaVendor="fixture-vendor";result.errorLog="fixture start error";result.outLog="fixture invalid output";
    task.checkJavaFinished(result);
   }
   VerifyJavaInstall verify(&parent);if(task.succeeded)verify.executeTask();
   QJsonObject effective;for(auto key:keys)effective[key]=i.get(key).toString();
   out["probed"]=probed;out["checkSucceeded"]=task.succeeded;out["checkFailed"]=task.failed;
   out["checkReason"]=task.reason;out["contextUpdates"]=parent.inst.contextUpdates;
   out["verifyCalled"]=task.succeeded;out["verifySucceeded"]=verify.succeeded;out["verifyFailed"]=verify.failed;
   out["verifyReason"]=verify.reason;out["checkLogs"]=task.logs;out["verifyLogs"]=verify.logs;
   out["effective"]=effective;out["globalStored"]=values(g);out["localStored"]=values(i);
   out["signatureMatchesAfter"]=i.get("JavaSignature").toString()==current;
   out["globalSignatureMatchesAfter"]=g.get("JavaSignature").toString()==current;
   out["selectedMajor"]=JavaVersion(i.get("JavaVersion").toString()).major();
  }else return 2;
  std::cout<<QJsonDocument(out).toJson(QJsonDocument::Compact).constData()<<"\n";
 }return 0;
}
'''
    source = source.replace('__VERSION__', version).replace('__CHECK__', check).replace('__VERIFY__', verify)
    (work / 'main.cpp').write_text(source)
    # The file is only an executable-existence/mtime witness. It is never run.
    executable = work / 'java-fixture'
    executable.write_text('#!/bin/sh\nexit 97\n')
    executable.chmod(0o700)
    cases = []
    for passthrough in [False, True]:
        for gate in [False, True]:
            for local in [None, 'local']:
                actions = [dict(op='set', value='written'), dict(op='global', value='next-global'),
                           dict(op='gate', value=not gate), dict(op='set', value='next-global'),
                           dict(op='reset'), dict(op='gate', value=True)]
                cases.append(dict(id=f'settings-{int(passthrough)}-{int(gate)}-{int(local is not None)}', kind='setting',
                                  passthrough=passthrough, gate=gate, globalDefault='default',
                                  global_='global', local=local, actions=actions))
                cases[-1]['global'] = cases[-1].pop('global_')
    for passthrough in [False, True]:
        cases.append(dict(id=f'equal-write-{int(passthrough)}', kind='setting', passthrough=passthrough,
                          gate=True, globalDefault='default', global_='global', local=None,
                          actions=[dict(op='set', value='global'), dict(op='global', value='changed')]))
        cases[-1]['global'] = cases[-1].pop('global_')
    defaults = dict(kind='pipeline', override=False, executable=True, checkerAvailable=True,
                    memory=4096, ignore=False, majors=[21], signatureMatches=True, probe=2,
                    stored=dict(JavaVersion='21.0.1', JavaArchitecture='64', JavaRealArchitecture='aarch64', JavaVendor='old-vendor'),
                    resultVersion='25.0.1', resultArch='64')

    def pipeline(id, **kw):
        cases.append(dict(defaults, id=id, **kw))

    pipeline('cached-compatible')
    pipeline('cached-incompatible', majors=[25])
    pipeline('cached-ignore', majors=[25], ignore=True)
    pipeline('cached-no-requirement', majors=[])
    pipeline('cached-32-memory', stored=dict(defaults['stored'], JavaArchitecture='32'))
    pipeline('cached-32-2048', memory=2048, stored=dict(defaults['stored'], JavaArchitecture='32'))
    pipeline('missing-global-executable', executable=False)
    pipeline('missing-instance-executable', executable=False, override=True)
    pipeline('missing-checker-cached', checkerAvailable=False)
    for override in [False, True]:
        for probe in [0, 1, 2]:
            pipeline(f'probe-{int(override)}-{probe}', override=override, probe=probe, signatureMatches=False)
    for field in ['JavaVersion', 'JavaArchitecture', 'JavaRealArchitecture', 'JavaVendor']:
        pipeline('missing-' + field, stored=dict(defaults['stored'], **{field: ''}), majors=[25])
    pipeline('invalid-probe-empty-version', signatureMatches=False, probe=1,
             stored=dict(defaults['stored'], JavaVersion=''))
    pipeline('invalid-probe-empty-no-requirement', signatureMatches=False, probe=1,
             stored=dict(defaults['stored'], JavaVersion=''), majors=[])
    pipeline('valid-probe-compatible', signatureMatches=False, majors=[25])
    pipeline('valid-probe-ignore', signatureMatches=False, ignore=True)
    pipeline('valid-probe-32-warning', signatureMatches=False, majors=[25], resultArch='32')
    pipeline('legacy-major-parser', stored=dict(defaults['stored'], JavaVersion='1.8.0_452'), majors=[8])
    pipeline('unparseable-version', stored=dict(defaults['stored'], JavaVersion='unknown'))
    pipeline('unparseable-no-requirement', stored=dict(defaults['stored'], JavaVersion='unknown'), majors=[])
    (run / 'input.json').write_text(json.dumps(dict(schema=1, cases=cases), indent=2) + '\n')
    env = dict(PATH='/usr/bin:/bin', HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'), LANG='en_US.UTF-8')
    processes, commands = [], []

    def command(label, argv, timeout):
        with (run / (label + '.stdout')).open('xb') as out, (run / (label + '.stderr')).open('xb') as err:
            process = subprocess.Popen(argv, env=env, cwd=work, stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=err, start_new_session=True)
            processes.append(process)
            (run / 'owned-processes.json').write_text(json.dumps([dict(pid=p.pid, retired=p.poll() is not None) for p in processes], indent=2) + '\n')
            timed = False
            start = time.monotonic()
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed = True
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            absent = True
        else:
            absent = False
        commands.append(dict(case=label, argv=argv, exitCode=process.returncode, timedOut=timed,
                             ownedGroupAbsent=absent, seconds=time.monotonic() - start,
                             streams={s: sha(run / (label + '.' + s)) for s in ['stdout', 'stderr']}))
        (run / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        assert process.returncode == 0 and not timed and absent, (label, process.returncode)

    try:
        pkg = '/opt/homebrew/bin/pkg-config'
        flags = shlex.split(subprocess.check_output([pkg, '--cflags', '--libs', 'Qt6Core'], text=True))
        lib = subprocess.check_output([pkg, '--variable=libdir', 'Qt6Core'], text=True).strip()
        libexec = subprocess.check_output([pkg, '--variable=libexecdir', 'Qt6Core'], text=True).strip()
        moc = Path(libexec) / 'moc'
        for name in ['Setting', 'OverrideSetting', 'PassthroughSetting']:
            command('moc-' + name, [str(moc), str(work / (name + '.h')), '-o', str(work / ('moc_' + name + '.cpp'))], 20)
        units = ['main.cpp', 'Setting.cpp', 'OverrideSetting.cpp', 'PassthroughSetting.cpp',
                 'moc_Setting.cpp', 'moc_OverrideSetting.cpp', 'moc_PassthroughSetting.cpp']
        command('compile', ['/usr/bin/clang++', '-std=c++20', '-O0', '-I' + str(work),
                            *[str(work / f) for f in units], '-o', str(work / 'probe'), *flags, '-Wl,-rpath,' + lib], 90)
        command('observe', [str(work / 'probe'), str(run / 'input.json'), str(executable)], 20)
        rows = [json.loads(line) for line in (run / 'observe.stdout').read_text().splitlines()]
        assert len(rows) == len(cases) and [r['id'] for r in rows] == [c['id'] for c in cases]
        receipt = dict(schema=1, producerSha256=sha(run / 'probe.py'), generatedSourceSha256=sha(work / 'main.cpp'),
                       storageAdapterSha256=sha(work / 'settings/SettingsObject.h'), executableWitnessSha256=sha(executable),
                       binarySha256=sha(work / 'probe'), copiedSources=copied, excerpts=excerpts,
                       compiler=subprocess.check_output(['/usr/bin/clang++', '--version'], text=True),
                       qtVersion=subprocess.check_output([pkg, '--modversion', 'Qt6Core'], text=True).strip(),
                       frameworkSha256=sha(Path(lib) / 'QtCore.framework/Versions/A/QtCore'),
                       moc=dict(path=str(moc), sha256=sha(moc)),
                       cases=len(cases), allOwnedGroupsAbsent=all(c['ownedGroupAbsent'] for c in commands),
                       workAllocatedKiB=int(subprocess.check_output(['du', '-sk', str(work)], text=True).split()[0]),
                       limits=['No JVM, game, launcher GUI, account, network or live configuration execution.',
                               'Original Setting/OverrideSetting/PassthroughSetting classes with synchronous in-memory storage adapter.',
                               'Unchanged selected CheckJava/VerifyJavaInstall/JavaVersion method bodies; result delivery,parent/profile/context and path resolver adapters.',
                               'No real probe process, automatic selection/download, concurrent settings writer, disk publication or process retirement qualification.',
                               'Supported Qt version differs from installed Prism Qt; selected source execution is not full-launcher qualification.'])
        (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(dict(run=str(run.relative_to(ROOT)), cases=len(cases), commands=len(commands), workAllocatedKiB=receipt['workAllocatedKiB'])))
    finally:
        for process in processes:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        (run / 'owned-processes.json').write_text(json.dumps([dict(pid=p.pid, retired=p.poll() is not None) for p in processes], indent=2) + '\n')


if __name__ == '__main__':
    main()
