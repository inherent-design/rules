#!/usr/bin/env python3
"""Owner-run real-Qt update cleanup/override-list fragments in disposable roots."""
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
sha = lambda b: hashlib.sha256(b).hexdigest()


def main():
    selections = json.loads((ROOT / 'applications/sources/prism-update-selections.json').read_text())
    sources = {p['path']: (ROOT / p['cache']).read_bytes() for p in selections}
    for p in selections: assert sha(sources[p['path']]) == p['sha256']
    creation = sources['launcher/InstanceCreationTask.cpp'].decode()
    filesystem = sources['launcher/FileSystem.cpp'].decode()
    overrides = sources['launcher/modplatform/helpers/OverrideUtils.cpp'].decode()

    def section(text, start, end):
        assert text.count(start) == 1 and text.count(end) == 1, (start, end)
        return text[text.index(start):text.index(end, text.index(start))]
    schedule = creation[creation.index('void InstanceCreationTask::scheduleToDelete('):]
    cleanup = section(creation, '    if (shouldOverride()) {', '\n    if (!m_abort) {')
    combine = section(filesystem, 'QString PathCombine(const QString& path1, const QString& path2)',
        '\nQString PathCombine(const QString& path1, const QString& path2, const QString& path3)')
    ensure = section(filesystem, 'bool ensureFilePathExists(QString filenamepath)', '\nbool ensureFolderPathExists(const QFileInfo folderPath)')
    enum = section(sources['launcher/InstanceTask.h'].decode(), 'enum class ShouldDeleteSaves', '\n[[nodiscard]] ShouldDeleteSaves')
    override_functions = overrides[overrides.index('namespace Override {'):]
    # Kept in ignored generated source with its original license/copyright header.
    notice = filesystem[:filesystem.index('#include "FileSystem.h"')]
    source = notice + r'''
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDebug>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTextStream>
#include <stdexcept>
struct QWidget {};
namespace FS {
bool deletePath(QString){throw std::logic_error("Existing override-list replacement is outside this fixture.");}
__ENSURE__
__COMBINE__
}
__OVERRIDES__
__ENUM__
class InstanceCreationTask {
public:
 QStringList m_filesToRemove,answers;ShouldDeleteSaves m_shouldDeleteSaves=ShouldDeleteSaves::NotAsked;
 int prompts=0;bool overrideExisting=true,cleanupPassed=false;QString failure;QJsonArray events;
 ShouldDeleteSaves askIfShouldDeleteSaves(QWidget*){
   if(prompts>=answers.size())throw std::logic_error("Unexpected dialog request");
   return answers[prompts++]=="Yes"?ShouldDeleteSaves::Yes:ShouldDeleteSaves::No;
 }
 bool shouldOverride(){return overrideExisting;}
 void setAbortable(bool b){events.append(QJsonObject{{"abortable",b}});}
 void setStatus(QString s){events.append(QJsonObject{{"status",s}});}
 QString tr(const char*s){return QString::fromUtf8(s);}
 void emitFailed(QString s){failure=s;events.append(QJsonObject{{"failed",s}});}
 void scheduleToDelete(QWidget*,QDir,QString,bool);
 void runCleanup(){
__CLEANUP__
 cleanupPassed=true; // Fixture continuation marker, not a whole-task success.
 }
};
__SCHEDULE__
QJsonObject image(QString root){
 QJsonObject out;QDir dir(root);
 QDirIterator it(root,QDir::AllEntries|QDir::NoDotAndDotDot|QDir::Hidden|QDir::System,QDirIterator::Subdirectories);
 while(it.hasNext()){
  QString path=it.next();QFileInfo info(path);QJsonObject row;
  if(info.isSymLink())row={{"kind","symlink"},{"target",info.symLinkTarget()},{"exists",info.exists()}};
  else if(info.isDir())row={{"kind","directory"}};
  else if(info.isFile()){
   QFile f(path);if(!f.open(QFile::ReadOnly))throw std::logic_error("Cannot snapshot fixture");auto bytes=f.readAll();
   row={{"kind","file"},{"bytes",QString::fromLatin1(bytes.toBase64())},{"sha256",QString::fromLatin1(QCryptographicHash::hash(bytes,QCryptographicHash::Sha256).toHex())}};
  }else throw std::logic_error("Unexpected fixture entry kind");
  out.insert(dir.relativeFilePath(path),row);
 }
 return out;
}
void writeFile(QString path,QByteArray bytes){
 if(!FS::ensureFilePathExists(path))throw std::logic_error("Cannot create fixture parent");
 QFile file(path);if(!file.open(QFile::WriteOnly)||file.write(bytes)!=bytes.size())throw std::logic_error("Cannot create fixture file");
}
QString relative(QString root,QString path){return QDir(root).relativeFilePath(QDir::cleanPath(path));}
int main(int argc,char**argv){
 QCoreApplication application(argc,argv);if(argc!=3)return 2;
 QFile input(QString::fromLocal8Bit(argv[1]));if(!input.open(QFile::ReadOnly))return 2;
 auto document=QJsonDocument::fromJson(input.readAll()).object();QString root=QString::fromLocal8Bit(argv[2]);
 if(document["schema"].toInt()!=1||QFileInfo(root).exists())return 2;
 QDir().mkpath(root);
 auto emitRow=[](QJsonObject row){row.insert("qtRuntime",qVersion());QTextStream(stdout)<<QJsonDocument(row).toJson(QJsonDocument::Compact)<<Qt::endl;};
 for(auto value:document["cleanup"].toArray()){
  auto spec=value.toObject();QString id=spec["id"].toString();QString base=root+"/"+id,game=base+"/game";
  QDir().mkpath(game+"/mods");auto files=spec["files"].toObject();
  for(auto it=files.begin();it!=files.end();++it)writeFile(game+"/"+it.key(),it.value().toString().toUtf8());
  for(auto v:spec["directories"].toArray())QDir().mkpath(game+"/"+v.toString());
  auto links=spec["links"].toObject();for(auto it=links.begin();it!=links.end();++it){
   FS::ensureFilePathExists(game+"/"+it.key());if(!QFile::link(game+"/"+it.value().toString(),game+"/"+it.key()))return 3;
  }
  auto before=image(game);InstanceCreationTask task;task.overrideExisting=spec["overrideExisting"].toBool();
  QString initial=spec["saveChoice"].toString();
  task.m_shouldDeleteSaves=initial=="Yes"?ShouldDeleteSaves::Yes:(initial=="No"?ShouldDeleteSaves::No:ShouldDeleteSaves::NotAsked);
  for(auto v:spec["answers"].toArray())task.answers.append(v.toString());
  for(auto v:spec["requests"].toArray()){
   auto request=v.toObject();task.scheduleToDelete(nullptr,QDir(game),request["path"].toString(),request["checkDisabled"].toBool());
  }
  QJsonArray scheduled,normalized;for(auto path:task.m_filesToRemove){scheduled.append(path);normalized.append(relative(game,path));}
  task.runCleanup();
  emitRow({{"id",id},{"kind","cleanup"},{"before",before},{"after",image(game)},
   {"scheduled",scheduled},{"normalized",normalized},{"prompts",task.prompts},{"cleanupPassed",task.cleanupPassed},
   {"failure",task.failure},{"events",task.events},{"saveChoice",task.m_shouldDeleteSaves==ShouldDeleteSaves::NotAsked?"NotAsked":(task.m_shouldDeleteSaves==ShouldDeleteSaves::Yes?"Yes":"No")}});
 }
 for(auto value:document["overrides"].toArray()){
  auto spec=value.toObject();QString id=spec["id"].toString(),name=spec["name"].toString();
  QString base=root+"/"+id,stage=base+"/"+name,records=base+"/mrpack";QDir().mkpath(stage);
  auto files=spec["files"].toObject();for(auto it=files.begin();it!=files.end();++it)writeFile(stage+"/"+it.key(),it.value().toString().toUtf8());
  auto before=image(stage);Override::createOverrides(name,records,stage);auto list=Override::readOverrides(name,records);
  QFile manifest(records+"/"+name+".txt");if(!manifest.open(QFile::ReadOnly))return 4;auto bytes=manifest.readAll();
  QJsonArray read;for(auto path:list)read.append(path);
  // Fixture old-install copy plus unrelated user canaries; the actual importer
  // is not used. Join the exact writer/reader/scheduler/cleanup fragments.
  QString game=base+"/installed-game";QDir().mkpath(game);
  for(auto it=files.begin();it!=files.end();++it)writeFile(game+"/"+it.key(),("installed:"+it.value().toString()).toUtf8());
  auto canaries=spec["canaries"].toObject();for(auto it=canaries.begin();it!=canaries.end();++it)writeFile(game+"/"+it.key(),it.value().toString().toUtf8());
  auto gameBefore=image(game);InstanceCreationTask task;
  for(auto path:list)task.scheduleToDelete(nullptr,QDir(game),path,false);
  QJsonArray normalized;for(auto path:task.m_filesToRemove)normalized.append(relative(game,path));
  task.runCleanup();
  emitRow({{"id",id},{"kind","overrides"},{"before",before},{"after",image(stage)},
   {"listBase64",QString::fromLatin1(bytes.toBase64())},{"read",read},
   {"gameBefore",gameBefore},{"gameAfter",image(game)},{"normalized",normalized},
   {"prompts",task.prompts},{"cleanupPassed",task.cleanupPassed},{"failure",task.failure}});
 }
 return 0;
}
'''
    for key, value in [('ENSURE', ensure), ('COMBINE', combine), ('OVERRIDES', override_functions),
        ('ENUM', enum), ('CLEANUP', cleanup), ('SCHEDULE', schedule)]: source = source.replace('__' + key + '__', value)
    cleanup_cases = []
    def case(label, files=None, requests=None, *, directories=None, links=None, choice='NotAsked', answers=None, override=True):
        cleanup_cases.append(dict(id=label, files=files or {}, requests=[dict(path=p, checkDisabled=b) for p, b in (requests or [])],
            directories=directories or [], links=links or {}, saveChoice=choice, answers=answers or [], overrideExisting=override))
    case('empty-path', {'options.txt': 'user'}, [('', True)])
    case('save-refused', {'saves/world/level.dat': 'world'}, [('saves/world/level.dat', True)], answers=['No'])
    case('save-approved', {'saves/world/level.dat': 'world'}, [('saves/world/level.dat', True)], answers=['Yes'])
    case('save-dot-prefix', {'saves/world/level.dat': 'world'}, [('./saves/world/level.dat', True)], answers=['No'])
    case('save-parent-prefix', {'saves/world/level.dat': 'world'}, [('mods/../saves/world/level.dat', True)], answers=['No'])
    case('save-dot-cached-no', {'saves/world/level.dat': 'world'}, [('./saves/world/level.dat', True)], choice='No')
    case('save-parent-cached-no', {'saves/world/level.dat': 'world'}, [('mods/../saves/world/level.dat', True)], choice='No')
    case('save-no-cached', {'saves/a.dat': 'a', 'saves/b.dat': 'b'}, [('saves/a.dat', False), ('saves/b.dat', False)], answers=['No', 'Yes'])
    case('save-yes-cached', {'saves/a.dat': 'a', 'saves/b.dat': 'b'}, [('saves/a.dat', False), ('saves/b.dat', False)], answers=['Yes', 'No'])
    case('save-preexisting-no', {'saves/a.dat': 'a'}, [('saves/a.dat', False)], choice='No')
    case('save-preexisting-yes', {'saves/a.dat': 'a'}, [('saves/a.dat', False)], choice='Yes')
    case('user-options-override', {'options.txt': 'user-changed-options'}, [('options.txt', False)])
    case('enabled-disabled-pair', {'mods/a.jar': 'enabled', 'mods/a.jar.disabled': 'disabled'}, [('mods/a.jar', True)])
    case('disabled-enabled-pair', {'mods/a.jar': 'enabled', 'mods/a.jar.disabled': 'disabled'}, [('mods/a.jar.disabled', True)])
    case('override-no-disabled-pair', {'mods/a.jar': 'enabled', 'mods/a.jar.disabled': 'disabled'}, [('mods/a.jar', False)])
    case('missing-is-skipped', {}, [('mods/absent.jar', True)])
    case('directory-fails', {}, [('config', False)], directories=['config'])
    case('partial-batch-continues', {'first.txt': 'first', 'last.txt': 'last'}, [('first.txt', False), ('config', False), ('last.txt', False)], directories=['config'])
    case('no-override-no-cleanup', {'options.txt': 'user'}, [('options.txt', False)], override=False)
    case('broken-link-skipped', {}, [('mods/link.jar', True)], links={'mods/link.jar': 'mods/absent.jar'})
    case('valid-link-only', {'payload.jar': 'retained-target'}, [('mods/link.jar', True)], links={'mods/link.jar': 'payload.jar'})
    case('save-prefix-not-substring', {'config/saves/a.txt': 'not-a-world'}, [('config/saves/a.txt', False)])
    override_cases = [dict(id=label, name=name, files=files, canaries=canaries) for label, name, files, canaries in [
        ('list-simple', 'overrides', {'options.txt': 'seed', 'config/a.toml': 'config'}, {'unrelated.txt': 'user'}),
        ('list-marker-in-filename', 'overrides', {'config/my-overrides-settings.toml': 'config'}, {'settings.toml': 'user'}),
        ('list-marker-in-directory', 'overrides', {'config/overrides/rules.json': 'config'}, {'rules.json': 'user'}),
        ('list-whitespace', 'overrides', {'  options.txt  ': 'seed'}, {'options.txt': 'user'}),
        ('list-unicode', 'overrides', {'config/日本 Ω.toml': 'config'}, {'unrelated.txt': 'user'}),
        ('list-client-marker', 'client-overrides', {'config/client-overrides-feature.json': 'config'}, {'feature.json': 'user'}),
        ('list-newline', 'overrides', {'config/line\nbreak.txt': 'config'}, {'config/line': 'user', 'break.txt': 'user'}),
        ('list-unicode-whitespace', 'overrides', {'\u00a0options.txt\u00a0': 'seed'}, {'options.txt': 'user'}),
    ]]
    spec = dict(schema=1, cleanup=cleanup_cases, overrides=override_cases)
    # Fixtures are authored by this producer; refuse path escape in initial data.
    for row in cleanup_cases + override_cases:
        assert row['id'].replace('-', '').isalnum()
        for path in [*row['files'], *row.get('directories', []), *row.get('links', {}), *row.get('canaries', {})]:
            assert path and not path.startswith('/') and '..' not in path.split('/')
        for request in row.get('requests', []):
            assert not request['path'].startswith('/') and '..' not in request['path'].split('/')[:1]
    run = ROOT / 'applications/evidence' / ('prism-update-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'; (work / 'home').mkdir(parents=True); (work / 'tmp').mkdir()
    (run / 'probe.py').write_bytes(PRODUCER)
    (run / 'input.json').write_text(json.dumps(spec, indent=2) + '\n')
    (work / 'main.cpp').write_text(source)
    pkg = '/opt/homebrew/bin/pkg-config'
    qt = subprocess.check_output([pkg, '--modversion', 'Qt6Core'], text=True).strip()
    assert qt.startswith('6.') and tuple(map(int, qt.split('.')[:2])) >= (6, 4)
    flags = shlex.split(subprocess.check_output([pkg, '--cflags', '--libs', 'Qt6Core'], text=True))
    lib = subprocess.check_output([pkg, '--variable=libdir', 'Qt6Core'], text=True).strip()
    env = dict(PATH='/usr/bin:/bin', HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'), LANG='en_US.UTF-8')
    command = ['/usr/bin/clang++', '-std=c++20', '-O0', '-DQT_NO_DEBUG', str(work / 'main.cpp'), '-o', str(work / 'probe'), *flags, '-Wl,-rpath,' + lib]
    compiled = subprocess.run(command, env=env, capture_output=True, timeout=90)
    for stream, value in [('stdout', compiled.stdout), ('stderr', compiled.stderr)]: (run / ('compile.' + stream)).write_bytes(value)
    if compiled.returncode:
        (run / 'failed-build.json').write_text(json.dumps(dict(command=command, code=compiled.returncode, producerSha256=sha(PRODUCER)), indent=2) + '\n')
        raise RuntimeError('Compile failed; original source/diagnostics retained at ' + str(run))
    execute_command = [str(work / 'probe'), str(run / 'input.json'), str(work / 'cases')]
    executed = subprocess.run(execute_command, env=env, capture_output=True, timeout=30)
    (run / 'observed.stdout').write_bytes(executed.stdout); (run / 'observed.stderr').write_bytes(executed.stderr)
    receipt = dict(schema=1, producerSha256=sha(PRODUCER), sourceRevision=selections[0]['commit'],
        sources={p['path']: p['sha256'] for p in selections}, generatedSha256={'main.cpp': sha(source.encode())},
        fragmentsSha256={k: sha(v.encode()) for k, v in dict(schedule=schedule, cleanup=cleanup, combine=combine, ensure=ensure, overrides=override_functions, enum=enum).items()},
        binarySha256=sha((work / 'probe').read_bytes()), binaryBytes=(work / 'probe').stat().st_size,
        compileCommand=command, compileExit=compiled.returncode, executeCommand=execute_command, executeExit=executed.returncode,
        compiler=subprocess.check_output(['/usr/bin/clang++', '--version'], text=True), qtVersion=qt,
        platform=platform.platform(), architecture=platform.machine(), environment=env,
        inputSha256=sha((run / 'input.json').read_bytes()), stdoutSha256=sha(executed.stdout), stderrSha256=sha(executed.stderr),
        limits=['Unmodified schedule method, cleanup block, override list methods and two filesystem helpers with supported real Qt6Core.',
            'Dialog answers, task fields, override flag, event rendering and continuation are fixture adapters; no actual GUI/dialog or constructor proof.',
            'Save-choice cache explicitly initialized per case; native header declaration has no initializer and constructor reachability remains unqualified.',
            'Existing list replacement branch is refused by fixture helper; no proof of its deletePath implementation.',
            'Files and links are disposable authored fixtures. Override-list cases join selected writer/reader/scheduler/cleanup fragments through an explicit old-install copy adapter; no archive extraction, downloads, complete staging/publication, incoming overlay, user instance or game launch.',
            'Raw paths and Qt-normalized destinations remain separate. Host results do not establish all-platform behavior or upstream format acceptance.'])
    (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    assert executed.returncode == 0, 'Execution failed; retain original diagnostics at ' + str(run)
    rows = [json.loads(line) for line in executed.stdout.splitlines()]
    assert len(rows) == len(cleanup_cases) + len(override_cases) == 30
    assert {row['qtRuntime'] for row in rows} == {qt}
    print(json.dumps(dict(run=str(run), cases=len(rows), qt=qt, binaryBytes=receipt['binaryBytes']), indent=2))


if __name__ == '__main__': main()
