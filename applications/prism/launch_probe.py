#!/usr/bin/env python3
"""Headless Qt launch sequencing with pinned Prism Task and controlled steps."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shlex
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=Path(__file__).read_bytes()
REV='7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4'
sha=lambda data:hashlib.sha256(data).hexdigest()


def main():
    cache=ROOT/'applications/tools/source-cache/launchers'
    source_paths=['launcher/launch/LaunchTask.cpp','launcher/launch/LaunchTask.h','launcher/launch/LaunchStep.cpp',
        'launcher/launch/LaunchStep.h','launcher/tasks/Task.cpp','launcher/tasks/Task.h','launcher/QObjectPtr.h',
        'launcher/AssertHelpers.h','launcher/MessageLevel.h']
    expected={
        'launcher/launch/LaunchTask.cpp':'f6fd07c4abf28a30feb24ece2fd3536e3050979576aaa541800297a248057e13',
        'launcher/launch/LaunchTask.h':'941c957cc14f2d11c9c27797905fe111556d5fa370a3bfab20189e33d471e0f1',
        'launcher/launch/LaunchStep.cpp':'cde7a49cfc76bcc55aa3370427ab7f405e8e3cc13b1a0adc2e0f1f24ef2c554e',
        'launcher/launch/LaunchStep.h':'aff761c33358f7fac90286d0065068095ca64bca62b5fe08f1116e743c2fdcc5',
        'launcher/tasks/Task.cpp':'0d8dad7a43e6952aee6cfbd2392b05e3704ab3134d7a59f162570315d689fb50',
        'launcher/tasks/Task.h':'34644742af7e1c9e8f727836209ffccd27828a3a86075435583099d21968a152',
        'launcher/QObjectPtr.h':'7edb81bcdd11b588fce3ff457626a2de5efff6d7d5b58d9fcf568283346a09a6',
        'launcher/AssertHelpers.h':'c64bc55d8a598c85f80057e78896eccd85244c4ca00a20dc24f56bf9cfa2b772',
        'launcher/MessageLevel.h':'beb8e559edffcded7b1470dcdc02f6067280642cfa8b06a949c1ec9ca706bdca'}
    sources={p:(cache/('prism__'+p.replace('/','__'))).read_bytes() for p in source_paths}
    for path,data in sources.items():assert sha(data)==expected[path],path
    original=sources['launcher/launch/LaunchTask.cpp'].decode()
    sections=[original[original.index('void LaunchTask::init()'):original.index('void LaunchTask::setCensorFilter')],
        original[original.index('void LaunchTask::proceed()'):original.index('shared_qobject_ptr<LogModel> LaunchTask::getLogModel')],
        original[original.index('void LaunchTask::emitSucceeded()'):original.index('QString expandVariables')]]
    header=r'''#pragma once
#include "launch/LaunchStep.h"
#include <QList>
#include <memory>
struct MinecraftInstance {bool running=false,crashed=false;void setRunning(bool x){running=x;}void setCrashed(bool x){crashed=x;}};
class LaunchTask:public Task {
 Q_OBJECT
public:
 enum State{NotStarted,Running,Waiting,Failed,Aborted,Finished};
 static std::unique_ptr<LaunchTask> create(MinecraftInstance*);
 void appendStep(shared_qobject_ptr<LaunchStep>);void prependStep(shared_qobject_ptr<LaunchStep>);
 void executeTask()override;void proceed();bool canAbort()const override;bool abort()override;
 int phase()const{return state;}int stepIndex()const{return currentStep;}
signals:
 void readyForLaunch();void requestProgress(Task*);
public slots:
 void onReadyForLaunch();void onStepFinished();void onProgressReportingRequested();
 void onLogLine(QString,MessageLevel){} void onLogLines(const QStringList&,MessageLevel){}
protected:
 explicit LaunchTask(MinecraftInstance*);void init();
 void emitSucceeded()override;void emitFailed(QString)override;
private:
 void finalizeSteps(bool,const QString&);
 MinecraftInstance* m_instance;QList<shared_qobject_ptr<LaunchStep>> m_steps;int currentStep=-1;State state=NotStarted;
};
'''
    main=r'''#include "launch/LaunchTask.h"
#include <QCoreApplication>
#include <QEvent>
#include <QEventLoop>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTimer>
#include <iostream>

struct ProbeStep:LaunchStep {
 QString mode;int id;QJsonArray* events;
 ProbeStep(LaunchTask*p,QString m,int i,QJsonArray*e):LaunchStep(p),mode(m),id(i),events(e){setObjectName("fixture-step-"+QString::number(id));setAbortable(mode.startsWith("hold-")&&mode!="hold-no-abort");}
 void event(QString s){events->append(s+":"+QString::number(id));}
 void executeTask()override {
   event("start");
   if(mode=="success")emitSucceeded();
   else if(mode=="failure")emitFailed("fixture failure");
   else if(mode=="ready")emit readyForLaunch();
   else if(mode=="progress")emit progressReportingRequest();
 }
 void proceed()override {event("proceed");emitSucceeded();}
 void finalize()override {event("finalize");}
 bool abort()override {
   event("abort-call");
   if(mode=="hold-refuse")return false;
   if(mode=="hold-queued") {QTimer::singleShot(0,this,[this]{event("abort-delivery");emitAborted();});return true;}
   return Task::abort();
 }
 void finishOwnedFixture(){if(isRunning()){event("fixture-cleanup");emitSucceeded();}}
};

QJsonObject snapshot(LaunchTask*task,MinecraftInstance&instance){return {{"phase",task->phase()},{"baseState",int(task->getState())},{"running",task->isRunning()},{"finished",task->isFinished()},{"successful",task->wasSuccessful()},{"canAbort",task->canAbort()},{"stepIndex",task->stepIndex()},{"instanceRunning",instance.running},{"instanceCrashed",instance.crashed},{"reason",task->failReason()}};}
void drain(){QCoreApplication::processEvents(QEventLoop::AllEvents);QCoreApplication::sendPostedEvents(nullptr,QEvent::DeferredDelete);}

void run(QString id,QStringList modes,QString action){
 MinecraftInstance instance;auto task=LaunchTask::create(&instance);task->setObjectName("fixture-launch-"+id);QJsonArray events;
 QObject::connect(task.get(),&Task::started,[&]{events.append("task-started");});
 QObject::connect(task.get(),&Task::succeeded,[&]{events.append("task-succeeded");});
 QObject::connect(task.get(),&Task::failed,[&](QString){events.append("task-failed");});
 QObject::connect(task.get(),&Task::aborted,[&]{events.append("task-aborted");});
 QObject::connect(task.get(),&Task::finished,[&]{events.append("task-finished");});
 QObject::connect(task.get(),&LaunchTask::readyForLaunch,[&]{events.append("ready-request");});
 QObject::connect(task.get(),&LaunchTask::requestProgress,[&](Task*){events.append("progress-request");});
 QList<shared_qobject_ptr<ProbeStep>> steps;
 for(int i=0;i<modes.size();++i){auto step=makeShared<ProbeStep>(task.get(),modes[i],i,&events);steps.append(step);task->appendStep(step);}
 auto initial=snapshot(task.get(),instance);task->start();auto afterStart=snapshot(task.get(),instance);QJsonValue accepted=QJsonValue::Null;
 if(action=="proceed")task->proceed();else if(action=="abort")accepted=task->abort();
 auto afterAction=snapshot(task.get(),instance);auto actionEvents=events;
 drain();auto afterDrain=snapshot(task.get(),instance);auto observedEvents=events;
 // Synthetic steps own no external process/resource. Settle any intentionally
 // held fixture after recording the observation, before destroying its owner.
 if(task->isRunning())for(auto step:steps)step->finishOwnedFixture();
 drain();auto afterCleanup=snapshot(task.get(),instance);auto cleanupEvents=events;
 QJsonObject out{{"id",id},{"modes",QJsonArray::fromStringList(modes)},{"action",action},{"initial",initial},{"afterStart",afterStart},{"abortAccepted",accepted},{"afterAction",afterAction},{"actionEvents",actionEvents},{"afterDrain",afterDrain},{"events",observedEvents},{"afterFixtureCleanup",afterCleanup},{"cleanupEvents",cleanupEvents}};
 std::cout<<QJsonDocument(out).toJson(QJsonDocument::Compact).toStdString()<<std::endl;
 steps.clear();task.reset();drain();
}
int main(int argc,char**argv){QCoreApplication app(argc,argv);
 run("empty",{},"none");run("success-three",{"success","success","success"},"none");
 run("failure-middle",{"success","failure","success"},"none");run("ready-proceed",{"ready","success"},"proceed");
 run("progress-proceed",{"progress","success"},"proceed");
 run("abort-disabled",{"hold-no-abort"},"abort");run("abort-refused",{"hold-refuse"},"abort");
 run("abort-sync",{"hold-sync"},"abort");run("abort-queued",{"hold-queued"},"abort");
 run("abort-after-first",{"success","hold-sync","success"},"abort");return 0;}
'''
    run=ROOT/'applications/evidence'/('prism-launch-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work=run/'work';(work/'home').mkdir(parents=True)
    (run/'probe.py').write_bytes(PRODUCER)
    for path in source_paths:
        if path.startswith('launcher/launch/LaunchTask.'):continue
        destination=work/path.removeprefix('launcher/');destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(sources[path])
    (work/'launch/LaunchTask.h').write_text(header)
    (work/'launch/LaunchTask.cpp').write_text('#include "LaunchTask.h"\n'+'\n'.join(sections))
    (work/'main.cpp').write_text(main)
    pkg='/opt/homebrew/bin/pkg-config';qt=subprocess.check_output([pkg,'--modversion','Qt6Core'],text=True).strip()
    assert tuple(map(int,qt.split('.')[:2]))>=(6,4) and qt.startswith('6.')
    libexec=Path(subprocess.check_output([pkg,'--variable=libexecdir','Qt6Core'],text=True).strip())
    flags=shlex.split(subprocess.check_output([pkg,'--cflags','--libs','Qt6Core'],text=True))
    libdir=subprocess.check_output([pkg,'--variable=libdir','Qt6Core'],text=True).strip()
    env={'PATH':'/usr/bin:/bin','HOME':str(work/'home'),'LANG':'en_US.UTF-8'}
    moc_commands=[]
    for name in ['tasks/Task.h','launch/LaunchStep.h','launch/LaunchTask.h']:
        target=work/('moc_'+Path(name).stem+'.cpp');argv=[str(libexec/'moc'),'-I'+str(work),str(work/name),'-o',str(target)]
        result=subprocess.run(argv,env=env,capture_output=True,timeout=30)
        (run/(Path(name).stem+'-moc.stdout')).write_bytes(result.stdout);(run/(Path(name).stem+'-moc.stderr')).write_bytes(result.stderr)
        moc_commands.append({'argv':argv,'exit':result.returncode});assert result.returncode==0,result.stderr.decode(errors='replace')
    cpp=[work/p for p in ['main.cpp','tasks/Task.cpp','launch/LaunchStep.cpp','launch/LaunchTask.cpp','moc_Task.cpp','moc_LaunchStep.cpp','moc_LaunchTask.cpp']]
    argv=['/usr/bin/clang++','-std=c++20','-O0','-DQT_NO_DEBUG','-I'+str(work),*[str(p)for p in cpp],'-o',str(work/'probe'),*flags,'-Wl,-rpath,'+libdir]
    compiled=subprocess.run(argv,env=env,capture_output=True,timeout=90)
    (run/'compile.stdout').write_bytes(compiled.stdout);(run/'compile.stderr').write_bytes(compiled.stderr)
    assert compiled.returncode==0,compiled.stderr.decode(errors='replace')
    executable_sha=sha((work/'probe').read_bytes());generated={str(p.relative_to(work)):sha(p.read_bytes()) for p in work.rglob('*') if p.is_file() and p.suffix in ['.cpp','.h']}
    executed=subprocess.run([str(work/'probe')],env=env,capture_output=True,timeout=20)
    (run/'observed.stdout').write_bytes(executed.stdout);(run/'observed.stderr').write_bytes(executed.stderr)
    assert executed.returncode==0,executed.stderr.decode(errors='replace')
    observed=[json.loads(line) for line in executed.stdout.splitlines()];assert len(observed)==10
    assert all(not r['afterFixtureCleanup']['running'] for r in observed)
    assert executable_sha==sha((work/'probe').read_bytes())
    receipt={'schema':1,'kind':'Pinned Task/LaunchStep with real Qt and selected LaunchTask bodies; not full Prism or a game launch',
        'producerSha256':sha(PRODUCER),'revision':REV,'sources':expected,'launchSectionsSha256':[sha(s.encode())for s in sections],
        'generatedSha256':generated,'executableSha256':executable_sha,'executableUnchanged':True,'qtVersion':qt,
        'mocCommands':moc_commands,'compileCommand':argv,'compileExit':compiled.returncode,'executeExit':executed.returncode,
        'compiler':subprocess.check_output(['/usr/bin/clang++','--version'],text=True),'platform':platform.platform(),
        'cases':len(observed),'stdoutSha256':sha(executed.stdout),'stderrSha256':sha(executed.stderr),
        'limits':['Full Task/LaunchStep source, QObjectPtr and AssertHelpers copied unchanged; LaunchTask declaration/instance/log handlers are fixture adapters.',
            'LaunchTask lifecycle bodies are unmodified; controlled steps simulate success/failure/readiness and synchronous/queued abort publication.',
            'Qt6Core supported major/minimum for pinned Prism; -DQT_NO_DEBUG, -O0, headless same-thread signals and a queued timer.',
            'No actual Java, process containment/retirement, resources, downloads, accounts, profiler, GUI dialogs or complete LaunchController.',
            'Held synthetic tasks are settled only after the recorded observation; cleanup snapshots are separate from tested outcomes.']}
    (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'run':str(run),'cases':10,'qt':qt,'allOwnedFixturesTerminal':True},indent=2))


if __name__=='__main__':main()
