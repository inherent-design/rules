#!/usr/bin/env python3
"""Owner-run supported-Qt component decision fragments, never a live instance."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = Path(__file__).read_bytes()
sha = lambda data: hashlib.sha256(data).hexdigest()


def main():
    selections = json.loads((ROOT / 'applications/sources/prism-components-selections.json').read_text())
    selected = {row['path']: (ROOT / row['cache']).read_bytes() for row in selections}
    for row in selections:
        assert sha(selected[row['path']]) == row['sha256']
    task = selected['launcher/minecraft/ComponentUpdateTask.cpp'].decode()
    component = selected['launcher/minecraft/Component.cpp'].decode()
    meta = selected['launcher/meta/JsonFormat.h'].decode()
    aliases = selected['launcher/minecraft/PackProfile_p.h'].decode()

    def section(text, start, end):
        assert text.count(start) == 1 and text.count(end) == 1, (start, end)
        return text[text.index(start):text.index(end, text.index(start))]

    functions = section(task, 'namespace {\nstruct RequireEx', '\nComponentContainer ComponentUpdateTask::collectTreeLinked')
    require = section(meta, 'struct Require {', '\nusing RequireSet')
    accessors = [section(component, start, end) for start, end in [
        ('QString Component::getVersion()', '\nQString Component::getFilename()'),
        ('bool Component::isEnabled()', '\nbool Component::setEnabled('),
        ('bool Component::isCustom()', '\nbool Component::isCustomizable()'),
        ('bool Component::isRemovable()', '\nbool Component::isRevertible()')]]
    container_aliases = section(aliases, 'using ComponentContainer', '\n\nstruct PackProfileData')
    adapter = r'''
#include <QCoreApplication>
#include <QDebug>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QList>
#include <QLoggingCategory>
#include <QMap>
#include <QString>
#include <algorithm>
#include <cassert>
#include <iostream>
#include <memory>
#include <set>
#include "Version.h"
Q_LOGGING_CATEGORY(instanceProfileResolveC,"rules.fixture.component-decisions")
namespace Meta {
__REQUIRE__
}
class Component {
public:
 QString m_uid,m_cachedVersion;
 std::set<Meta::Require> m_cachedRequires;
 bool m_dependencyOnly=false,m_cachedVolatile=false,m_disabled=false,m_important=false;
 std::shared_ptr<int> m_file;
 QString getVersion();bool isCustom();bool isEnabled();bool canBeDisabled();bool isRemovable();
};
// Pointer ownership/loading/QObject delivery are fixture adapters; only cached values are supplied.
using ComponentPtr=std::shared_ptr<Component>;
__ALIASES__
__ACCESSORS__
__FUNCTIONS__
QJsonArray requirements(const RequireExSet& entries) {
 QJsonArray out;
 for(const auto&r:entries)out.append(QJsonObject{{"uid",r.uid},{"equals",r.equalsVersion},{"suggests",r.suggests},{"firstDependee",double(r.indexOfFirstDependee)}});
 return out;
}
int main(int argc,char**argv) {
 QCoreApplication app(argc,argv);
 if(argc!=2)return 2;
 QFile file(QString::fromLocal8Bit(argv[1]));if(!file.open(QIODevice::ReadOnly))return 2;
 QJsonParseError error;auto doc=QJsonDocument::fromJson(file.readAll(),&error);
 if(error.error!=QJsonParseError::NoError||doc.object()["schema"].toInt()!=1)return 2;
 for(auto item:doc.object()["cases"].toArray()) {
  auto input=item.toObject();ComponentContainer components;ComponentIndex index;QJsonArray states;
  for(auto raw:input["components"].toArray()) {
   auto data=raw.toObject();auto comp=std::make_shared<Component>();
   comp->m_uid=data["uid"].toString();if(comp->m_uid.isEmpty()||index.contains(comp->m_uid))return 2;
   comp->m_cachedVersion=data["version"].toString();comp->m_dependencyOnly=data["dependencyOnly"].toBool();
   comp->m_cachedVolatile=data["volatile"].toBool();comp->m_disabled=data["disabled"].toBool();comp->m_important=data["important"].toBool();
   if(data["custom"].toBool())comp->m_file=std::make_shared<int>(1);
   for(auto value:data["requires"].toArray()) {
    auto req=value.toObject();Meta::Require r;r.uid=req["uid"].toString();r.equalsVersion=req["equals"].toString();r.suggests=req["suggests"].toString();
    if(r.uid.isEmpty()||!comp->m_cachedRequires.insert(r).second)return 2;
   }
   components.append(comp);index.insert(comp->m_uid,comp);
   states.append(QJsonObject{{"uid",comp->m_uid},{"enabled",comp->isEnabled()},{"canDisable",comp->canBeDisabled()},{"custom",comp->isCustom()},{"version",comp->getVersion()}});
  }
  RequireExSet gathered,add,change;QStringList remove;
  bool gatherOK=gatherRequirementsFromComponents(components,gathered);QJsonValue planOK=QJsonValue::Null;
  // This is a one-pass decision comparison, not the caller's remove/reload recursion.
  if(gatherOK){getTrivialRemovals(components,gathered,remove);planOK=getTrivialComponentChanges(index,gathered,add,change);}
  QJsonObject out{{"id",input["id"]},{"gatherOK",gatherOK},{"requirements",requirements(gathered)},
   {"proposedRemovals",QJsonArray::fromStringList(remove)},{"changePlanOK",planOK},
   {"proposedAdditions",requirements(add)},{"proposedChanges",requirements(change)},{"componentStates",states},{"qtRuntime",qVersion()}};
  std::cout<<QJsonDocument(out).toJson(QJsonDocument::Compact).toStdString()<<"\n";
 }
}
'''
    source = adapter.replace('__REQUIRE__', require).replace('__ALIASES__', container_aliases).replace('__ACCESSORS__', '\n'.join(accessors)).replace('__FUNCTIONS__', functions)
    req = lambda uid, exact='', suggests='': dict(uid=uid, equals=exact, suggests=suggests)

    def comp(uid, version='', requirements=(), **props):
        return dict(uid=uid, version=version, requires=list(requirements), **props)

    game = lambda version='1.21.1', **kw: comp('net.minecraft', version, **kw)
    loader = lambda *rs, **kw: comp('fixture.loader', '1.0', rs, **kw)
    mc = lambda exact='', suggests='': req('net.minecraft', exact, suggests)
    fixtures = [
        ('empty', []),
        ('missing-exact', [loader(mc('1.21.1'))]),
        ('met-explicit', [game(), loader(mc('1.21.1'))]),
        ('mismatch-adjustable-dependency', [game('1.20.1', dependencyOnly=True), loader(mc('1.21.1'))]),
        ('mismatch-explicit-protected', [game('1.20.1'), loader(mc('1.21.1'))]),
        ('mismatch-custom-dependency-protected', [game('1.20.1', dependencyOnly=True, custom=True), loader(mc('1.21.1'))]),
        ('same-exact-requirements', [loader(mc('1.21.1')), comp('fixture.other', '1', [mc('1.21.1')])]),
        ('exact-plus-unconstrained', [loader(mc()), comp('fixture.other', '1', [mc('1.21.1')])]),
        ('conflicting-exacts', [loader(mc('1.20.1')), comp('fixture.other', '1', [mc('1.21.1')])]),
        ('numeric-suggestions', [loader(mc('', '1.2')), comp('fixture.other', '1', [mc('', '1.10')])]),
        ('exact-and-different-suggestion', [loader(mc('1.21.1', '1.20.1')), comp('fixture.other', '1', [mc('', '1.22')])]),
        ('obsolete-volatile-dependency', [game(dependencyOnly=True, volatile=True)]),
        ('unreferenced-nonvolatile-dependency', [game(dependencyOnly=True)]),
        ('unreferenced-explicit-volatile', [game(volatile=True)]),
        ('required-volatile-dependency', [game(dependencyOnly=True, volatile=True), loader(mc())]),
        ('disabled-root-still-requires', [game(dependencyOnly=True, volatile=True), loader(mc(), disabled=True)]),
        ('dependency-flag-cannot-disable', [game(dependencyOnly=True, disabled=True), loader(mc())]),
        ('important-flag-cannot-disable', [game(important=True, disabled=True)]),
        ('two-missing-identities', [loader(mc('1.21.1'), req('fixture.library', '3'))]),
    ]
    input_data = dict(schema=1, cases=[dict(id=label, components=components) for label, components in fixtures])
    run = ROOT / 'applications/evidence' / ('prism-components-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    work = run / 'work'
    (work / 'home').mkdir(parents=True)
    (work / 'tmp').mkdir()
    (run / 'probe.py').write_bytes(PRODUCER)
    (run / 'input.json').write_text(json.dumps(input_data, indent=2) + '\n')
    (work / 'main.cpp').write_text(source)
    for suffix in ['cpp', 'h']:
        (work / ('Version.' + suffix)).write_bytes(selected['launcher/Version.' + suffix])
    pkg = '/opt/homebrew/bin/pkg-config'
    qt = subprocess.check_output([pkg, '--modversion', 'Qt6Core'], text=True).strip()
    assert qt.startswith('6.') and tuple(map(int, qt.split('.')[:2])) >= (6, 4)
    flags = shlex.split(subprocess.check_output([pkg, '--cflags', '--libs', 'Qt6Core'], text=True))
    lib = subprocess.check_output([pkg, '--variable=libdir', 'Qt6Core'], text=True).strip()
    env = dict(PATH='/usr/bin:/bin', HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'), LANG='en_US.UTF-8')
    command = ['/usr/bin/clang++', '-std=c++20', '-O0', '-DQT_NO_DEBUG', '-include', 'algorithm', '-I' + str(work),
        str(work / 'main.cpp'), str(work / 'Version.cpp'), '-o', str(work / 'probe'), *flags, '-Wl,-rpath,' + lib]
    compiled = subprocess.run(command, env=env, capture_output=True, timeout=90)
    for stream, data in [('stdout', compiled.stdout), ('stderr', compiled.stderr)]:
        (run / ('compile.' + stream)).write_bytes(data)
    if compiled.returncode:
        (run / 'failed-build.json').write_text(json.dumps(dict(command=command, exitCode=compiled.returncode, producerSha256=sha(PRODUCER), selectedSources=selections), indent=2) + '\n')
        raise RuntimeError('Native compile failed; source and original diagnostics retained at ' + str(run))
    binary_hash = sha((work / 'probe').read_bytes())
    execute = subprocess.run([str(work / 'probe'), str(run / 'input.json')], env=env, capture_output=True, timeout=20)
    (run / 'observed.stdout').write_bytes(execute.stdout)
    (run / 'observed.stderr').write_bytes(execute.stderr)
    assert execute.returncode == 0
    rows = [json.loads(line) for line in execute.stdout.splitlines()]
    assert len(rows) == len(fixtures) and {row['qtRuntime'] for row in rows} == {qt}
    assert sha((work / 'probe').read_bytes()) == binary_hash
    receipt = dict(schema=1, producerSha256=sha(PRODUCER), sourceRevision='7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4',
        sources={row['path']: row['sha256'] for row in selections},
        compiledFragmentsSha256=dict(require=sha(require.encode()), aliases=sha(container_aliases.encode()),
            accessors=[sha(body.encode()) for body in accessors], decisions=sha(functions.encode())),
        generatedSha256={p.name: sha(p.read_bytes()) for p in work.glob('*') if p.is_file() and p.suffix in ['.cpp', '.h']},
        binarySha256=binary_hash, compileCommand=command, compileExit=compiled.returncode, executeExit=execute.returncode,
        compiler=subprocess.check_output(['/usr/bin/clang++', '--version'], text=True), qtVersion=qt,
        platform=platform.platform(), architecture=platform.machine(), cases=len(rows),
        inputSha256=sha((run / 'input.json').read_bytes()), stdoutSha256=sha(execute.stdout), stderrSha256=sha(execute.stderr),
        limits=['Pinned unmodified Require struct, Version class, selected Component accessors and four component decision functions with real supported Qt types.',
            'Component declaration/pointer loading are fixture adapters: cached fields supplied, custom file represented only by non-null marker; no JSON metadata parser, network, QObject delivery or native constructor proof.',
            'One-pass proposed decisions; no caller fixed-point removals, metadata reload/download, actual publication, UI, accounts, Java process or game launch.',
            'Version comparison implementation compiled unchanged; selected numeric suggestions do not qualify its full string domain.',
            'Extra source-only profile aggregation and Java admission files are inspected but not executed by this fixture.'])
    (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(run=str(run), cases=len(rows), qt=qt), indent=2))


if __name__ == '__main__':
    main()
