#!/usr/bin/env python3
"""Execute pinned launcher source fragments, not either complete application.

MO2 uses fixture types for the sort method's accessed fields. Prism's filter
uses real Qt6 QString/QByteArray and std::vector, with its surrounding staging
guard projected separately. No VFS injection, GUI, download, or instance write.
Upstream method bodies remain in ignored generated work, not redistributed.
"""
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    run = HERE / 'evidence' / ('launcher-fragments-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'
    (work / 'home').mkdir(parents=True)
    shutil.copyfile(Path(__file__), run / 'probe.py')
    selections = json.loads((HERE / 'sources/launcher-selections.json').read_text())
    by_path = {(r['application'], r['path']): r for r in selections}

    def source(app, path):
        row = by_path[app, path]
        data = Path(row['cache']).read_bytes()
        assert sha(data) == row['sha256']
        return data.decode()

    original = source('mo2', 'src/shared/fileentry.cpp')
    mo2 = original[original.index('void FileEntry::sortOrigins()'):original.index('\nbool FileEntry::isFromArchive')]
    original = source('prism', 'launcher/modplatform/modrinth/ModrinthInstanceCreationTask.cpp')
    prism = original[original.index('        // Let\'s remove all duplicated, identical resources!'):original.index('        QDir oldMinecraftDir')]
    cpp = r'''#include <QtCore/QCoreApplication>
#include <QtCore/QJsonDocument>
#include <QtCore/QJsonArray>
#include <QtCore/QJsonObject>
#include <QtCore/QFile>
#include <QtCore/QDebug>
#include <algorithm>
#include <climits>
#include <iostream>
#include <map>
#include <mutex>
#include <vector>

struct Archive { bool present; int value; bool isValid() const { return present; } int order() const { return value; } };
struct Alternative { int origin; Archive data; int originID() const { return origin; } bool isFromArchive() const { return data.present; } Archive archive() const { return data; } };
struct Origin { int priority; int getPriority() const { return priority; } };
struct Parent { std::map<int, Origin> origins; Origin getOriginByID(int id) { return origins.at(id); } };
struct FileEntry { std::mutex m_OriginsMutex; std::vector<Alternative> m_Alternatives; int m_Origin; Archive m_Archive; Parent* m_Parent; void sortOrigins(); };
MO2_BODY

struct File { QString path; QByteArray hash; };
std::vector<File> decodeFiles(QJsonArray array) { std::vector<File> out; for (auto v: array) { auto o=v.toObject(); out.push_back({o["path"].toString(), QByteArray::fromHex(o["hash"].toString().toLatin1())}); } return out; }
QJsonArray encodeFiles(const std::vector<File>& files) { QJsonArray out; for (auto f: files) out.append(QJsonObject{{"path",f.path},{"hash",QString::fromLatin1(f.hash.toHex())}}); return out; }
void filterFiles(std::vector<File>& m_files, std::vector<File>& oldFiles) {
PRISM_BODY
}

int main(int argc, char** argv) {
  QCoreApplication app(argc,argv);
  if (argc!=2) return 2;
  QFile f(QString::fromLocal8Bit(argv[1])); if (!f.open(QIODevice::ReadOnly)) return 3;
  auto input=QJsonDocument::fromJson(f.readAll()).object();
  QJsonArray mo2Results, prismResults;
  for (auto v: input["mo2"].toArray()) {
    auto c=v.toObject(); auto candidates=c["candidates"].toArray(); if(candidates.empty()) return 4;
    Parent parent; FileEntry entry; entry.m_Parent=&parent;
    for (int i=0;i<candidates.size();++i) {
      auto o=candidates[i].toObject(); auto id=o["id"].toInt();
      parent.origins[id]=Origin{o["priority"].toInt()}; Archive archive{!o["loose"].toBool(),o["archiveOrder"].toInt()};
      if(i==0) {entry.m_Origin=id;entry.m_Archive=archive;} else entry.m_Alternatives.push_back({id,archive});
    }
    entry.sortOrigins(); mo2Results.append(QJsonObject{{"id",c["id"]},{"winner",entry.m_Origin}});
  }
  for (auto v: input["prism"].toArray()) {
    auto c=v.toObject(); auto incoming=decodeFiles(c["new"].toArray()); auto pending=incoming; auto old=decodeFiles(c["old"].toArray());
    filterFiles(pending,old);
    bool reparse=pending.empty();
    // Projection of createInstance's empty-vector guard, assuming valid required-only manifest parsing succeeds.
    auto downloads=reparse?incoming:pending;
    prismResults.append(QJsonObject{{"id",c["id"]},{"remainingNew",encodeFiles(pending)},{"remainingOld",encodeFiles(old)},{"reparsed",reparse},{"downloads",encodeFiles(downloads)}});
  }
  std::cout << QJsonDocument(QJsonObject{{"mo2",mo2Results},{"prism",prismResults},{"qtVersion",qVersion()}}).toJson(QJsonDocument::Compact).toStdString() << std::endl;
}
'''.replace('MO2_BODY', mo2).replace('PRISM_BODY', prism)
    (work / 'probe.cpp').write_text(cpp)
    ranks = [(loose, value) for loose in [False, True] for value in [-1, 0, 1, 2]]
    mo2_cases = []
    for number, (left, right) in enumerate(itertools.permutations(ranks, 2)):
        def candidate(identity, rank):
            loose, value = rank
            return {'id': identity, 'loose': loose, 'priority': value if loose else 99 - identity,
                    'archiveOrder': value if not loose else 99 - identity}
        mo2_cases.append({'id': 'pair-' + str(number), 'candidates': [candidate(1, left), candidate(2, right)]})
    h = lambda value: hashlib.sha512(value.encode()).hexdigest()
    file = lambda path, value: {'path': path, 'hash': h(value)}
    old = [file('config/old.json', 'same'), file('config/extra.json', 'before')]
    prism_cases = [
        {'id': 'same-path-plus-change', 'old': old, 'new': [file('config/old.json', 'same'), file('config/extra.json', 'after')]},
        {'id': 'moved-path-plus-change', 'old': old, 'new': [file('config/new.json', 'same'), file('config/extra.json', 'after')]},
        {'id': 'single-moved-path', 'old': old[:1], 'new': [file('config/new.json', 'same')]},
        {'id': 'all-unchanged', 'old': old, 'new': old},
        {'id': 'swapped-content-plus-change', 'old': old + [file('config/third.json', 'third-before')],
         'new': [file('config/old.json', 'before'), file('config/extra.json', 'same'), file('config/third.json', 'third-after')]},
        {'id': 'unicode-moved-plus-change', 'old': [file('config/α.json', 'same'), old[1]],
         'new': [file('config/日本.json', 'same'), file('config/extra.json', 'after')]},
    ]
    inputs = {'schema': 1, 'mo2': mo2_cases, 'prism': prism_cases}
    (run / 'input.json').write_text(json.dumps(inputs, indent=2) + '\n')
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(work / 'home'), 'LANG': 'en_US.UTF-8'}
    pkg = '/opt/homebrew/bin/pkg-config'
    flags = shlex.split(subprocess.check_output([pkg, '--cflags', '--libs', 'Qt6Core'], text=True))
    qt_version = subprocess.check_output([pkg, '--modversion', 'Qt6Core'], text=True).strip()
    assert qt_version.split('.')[0] == '6' and int(qt_version.split('.')[1]) >= 4
    libdir = subprocess.check_output([pkg, '--variable=libdir', 'Qt6Core'], text=True).strip()
    argv = ['/usr/bin/clang++', '-std=c++20', '-O0', str(work / 'probe.cpp'), '-o', str(work / 'probe'), *flags, '-Wl,-rpath,' + libdir]
    compile_result = subprocess.run(argv, env=env, capture_output=True, timeout=90)
    (run / 'compile.stdout').write_bytes(compile_result.stdout)
    (run / 'compile.stderr').write_bytes(compile_result.stderr)
    assert compile_result.returncode == 0, compile_result.stderr.decode(errors='replace')
    executed = subprocess.run([str(work / 'probe'), str(run / 'input.json')], env=env, capture_output=True, timeout=20)
    (run / 'observed.stdout').write_bytes(executed.stdout)
    (run / 'observed.stderr').write_bytes(executed.stderr)
    assert executed.returncode == 0
    observed = json.loads(executed.stdout)
    assert observed['qtVersion'] == qt_version
    receipt = {'schema': 1, 'kind': 'executed-source-fragments; not full native products',
               'entrypointSha256': sha(Path(__file__).read_bytes()), 'generatedCppSha256': sha(cpp.encode()),
               'fragments': {'mo2SortSha256': sha(mo2.encode()), 'prismFilterSha256': sha(prism.encode())},
               'compileCommand': argv, 'compileExit': compile_result.returncode, 'executeExit': executed.returncode,
               'compiler': subprocess.check_output(['/usr/bin/clang++', '--version'], text=True),
               'qtVersion': qt_version, 'platform': platform.platform(), 'architecture': platform.machine(),
               'inputSha256': sha((run / 'input.json').read_bytes()), 'stdoutSha256': sha(executed.stdout),
               'stderrSha256': sha(executed.stderr), 'mo2Cases': len(mo2_cases), 'prismCases': len(prism_cases),
               'limits': ['MO2 sort uses fixture implementations of the accessed fields/methods; no Windows VFS or application execution.',
                          'Prism filter uses real supported Qt6 types, but is not the full importer or GUI; empty-result reparse is a separate translated guard.',
                          'Prism fixture manifests are required-only and assumed valid; no downloads, credentials, or installed instances used.',
                          'No source-fragment result substitutes for complete native launch/update qualification.']}
    (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'run': str(run), 'mo2Cases': len(mo2_cases), 'prismCases': len(prism_cases), 'qt': qt_version}, indent=2))


if __name__ == '__main__':
    main()
