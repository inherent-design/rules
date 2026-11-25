"""Execute selected MO2 methods using real Qt strings and explicit field/callback adapters."""
from datetime import datetime, timezone
import copy
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    source_path = ROOT / 'applications/tools/source-cache/mo2-plugins/src__pluginlist.cpp'
    sources = json.loads((ROOT / '.build/mo2-plugin-source-acquisition.json').read_text())
    source = next(row for row in sources['sources'] if row['path'] == 'src/pluginlist.cpp')
    assert sha(source_path) == source['sha256']
    text = source_path.read_text()
    markers = [
        ('void PluginList::enableESP(', '\nint PluginList::findPluginByPriority('),
        ('void PluginList::setEnabledAll(', '\nvoid PluginList::sendToPriority('),
        ('void PluginList::syncLoadOrder(', '\nvoid PluginList::refreshLoadOrder('),
        ('IPluginList::PluginStates PluginList::state(', '\nvoid PluginList::setState('),
        ('void PluginList::setState(', '\nvoid PluginList::setLoadOrder('),
        ('void PluginList::setLoadOrder(', '\nint PluginList::priority('),
        ('void PluginList::pluginStatesChanged(', '\nboost::signals2::connection\nPluginList::onRefreshed('),
        ('void PluginList::updateIndices(', '\nvoid PluginList::generatePluginIndexes('),
        ('void PluginList::testMasters(', '\nQVariant PluginList::data('),
    ]
    cuts, bodies = [], []
    for start_marker, end_marker in markers:
        assert text.count(start_marker) == text.count(end_marker) == 1
        start = text.index(start_marker)
        end = text.index(end_marker, start)
        body = text[start:end]
        cuts.append(dict(signature=start_marker, textStart=start, textEnd=end, sha256=hashlib.sha256(body.encode()).hexdigest()))
        bodies.append(body)
    driver = HERE / 'plugin_driver.cpp'
    generated = driver.read_text().replace('/*METHODS*/', '\n'.join(bodies))
    def plugin(name, enabled=False, priority=0, loaded=False, forced=False, disabled=False, masters=(), missing=(), load=-1):
        return dict(name=name, enabled=enabled, priority=priority, forceLoaded=loaded, forceEnabled=forced,
            forceDisabled=disabled, masters=list(masters), missing=list(missing), loadOrder=load)
    cases = []
    def add(identity, plugins, actions):
        cases.append(dict(id=identity, plugins=plugins, actions=actions))
    for policy in ['free', 'loaded', 'enabled', 'disabled']:
        for active in [False, True]:
            p = plugin('A.esm', loaded=policy == 'loaded', forced=policy == 'enabled', disabled=policy == 'disabled')
            add('api-' + policy + '-' + str(int(active)), [p], [dict(kind='set-state', name='A.esm', active=active)])
    add('api-missing', [plugin('A.esm')], [dict(kind='set-state', name='ABSENT.esp', active=True)])
    add('helper-changed', [plugin('A.esm')], [dict(kind='enable', name='A.esm', active=True)])
    add('helper-unchanged', [plugin('A.esm', True)], [dict(kind='enable', name='A.esm', active=True)])
    add('helper-missing', [plugin('A.esm')], [dict(kind='enable', name='ABSENT.esp', active=True)])
    add('helper-forced-normalization', [plugin('A.esm', loaded=True)], [dict(kind='enable', name='A.esm', active=False)])
    policies = [plugin('A.esm'), plugin('B.esp', True, 1, forced=True), plugin('C.esp', False, 2, disabled=True)]
    add('bulk-changed', policies, [dict(kind='all', active=True)])
    add('bulk-no-change', [dict(policies[0], enabled=True), *policies[1:]], [dict(kind='all', active=True)])
    add('bulk-inconsistent-prestate', [plugin('A.esm', loaded=True), plugin('B.esp', True, 1, disabled=True)], [dict(kind='all', active=False)])
    order = [plugin('A.esm', True, 2, load=2), plugin('B.esp', True, 0, masters=['A.esm'], load=0), plugin('C.esp', False, 1, load=-1)]
    add('sync-priority-order', order, [dict(kind='sync')])
    add('api-then-normalize', order, [dict(kind='set-state', name='C.esp', active=True), dict(kind='sync'), dict(kind='masters')])
    add('masters-disabled', [plugin('A.esm'), plugin('B.esp', True, 1, masters=['A.esm'])], [dict(kind='masters')])
    add('masters-enabled-later', order, [dict(kind='masters')])
    add('masters-disabled-dependent-clears', [plugin('A.esm', masters=['ABSENT.esm'], missing=['OLD.esm'])], [dict(kind='masters')])
    add('masters-absent', [plugin('A.esm', True, masters=['ABSENT.esm'])], [dict(kind='masters')])
    for label, names in [('complete', ['C.esp', 'B.esp', 'A.esm']), ('partial', ['C.esp']),
                         ('unknown', ['ABSENT.esp', 'C.esp']), ('empty', []), ('duplicate', ['A.esm', 'A.esm'])]:
        add('order-' + label, order, [dict(kind='order', names=names)])
    add('order-then-sync', order, [dict(kind='order', names=['C.esp', 'B.esp', 'A.esm']), dict(kind='sync')])
    run = ROOT / 'applications/evidence' / ('mo2-plugins-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    work = Path(tempfile.mkdtemp(prefix='rules-mo2-plugins-', dir='/private/tmp'))
    for name in ['tmp', 'config', 'cache']:
        (work / name).mkdir()
    shutil.copyfile(__file__, run / 'probe.py')
    shutil.copyfile(driver, run / 'driver.cpp')
    write(run / 'input.json', dict(schema=1, cases=cases))
    (work / 'main.cpp').write_text(generated)
    pkg = '/opt/homebrew/bin/pkg-config'
    qt = subprocess.check_output([pkg, '--modversion', 'Qt6Core'], text=True).strip()
    assert qt.startswith('6.')
    flags = shlex.split(subprocess.check_output([pkg, '--cflags', '--libs', 'Qt6Core'], text=True))
    lib = Path(subprocess.check_output([pkg, '--variable=libdir', 'Qt6Core'], text=True).strip())
    compiler = Path('/usr/bin/clang++')
    env = dict(PATH='/usr/bin:/bin', LANG='en_US.UTF-8', TMPDIR=str(work / 'tmp'),
        XDG_CONFIG_HOME=str(work / 'config'), XDG_CACHE_HOME=str(work / 'cache'))
    receipt = dict(schema=1, work=str(work), revision=sources['revision'], source=source, cuts=cuts,
        producerSha256=sha(run / 'probe.py'), driverSha256=sha(run / 'driver.cpp'),
        inputSha256=sha(run / 'input.json'), generatedSha256=sha(work / 'main.cpp'), compilerSha256=sha(compiler),
        qtVersion=qt, qtFrameworkSha256=sha(lib / 'QtCore.framework/Versions/A/QtCore'),
        environment=env, commands=[], limits=[
            'Nine unchanged selected methods,real QtCore QString/QStringList,and std containers;no full MO2 or Windows process.',
            'Catalog/constructor/enum tags/comparator/logs/signals/game index generation are adapters;canonical exact ASCII names only.',
            'Signal calls are recorded;no real Qt slot delivery,writer,game feature,profile file,LOOT,plugin parser,USVFS or GUI.',
            'Duplicate order is constructed malformed input;full public API preconditions andcaller reachability remain separate.'])
    write(run / 'receipt.json', receipt)
    def command(label, argv):
        child = subprocess.Popen(argv, cwd=work, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timed = False
        try:
            out, err = child.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            timed = True
            os.killpg(child.pid, signal.SIGTERM)
            try:
                out, err = child.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                out, err = child.communicate(timeout=3)
        (run / (label + '.stdout')).write_bytes(out)
        (run / (label + '.stderr')).write_bytes(err)
        try:
            os.killpg(child.pid, 0)
            absent = False
        except ProcessLookupError:
            absent = True
        receipt['commands'].append(dict(label=label, argv=argv, pid=child.pid, exitCode=child.returncode,
            groupAbsent=absent, timedOut=timed, stdoutSha256=sha(run / (label + '.stdout')),
            stderrSha256=sha(run / (label + '.stderr'))))
        write(run / 'receipt.json', receipt)
        assert absent and not timed and child.returncode == 0, receipt['commands'][-1]
    command('compiler', [str(compiler), '--version'])
    command('compile', [str(compiler), '-std=c++20', '-O0', '-DQT_NO_DEBUG', str(work / 'main.cpp'),
        '-o', str(work / 'probe'), *flags, '-Wl,-rpath,' + str(lib)])
    receipt['binarySha256'] = sha(work / 'probe')
    write(run / 'receipt.json', receipt)
    command('observed', [str(work / 'probe'), str(run / 'input.json')])
    rows = json.loads((run / 'observed.stdout').read_text())
    assert [r['id'] for r in rows] == [r['id'] for r in cases]
    receipt['complete'] = True
    receipt['cases'] = len(cases)
    receipt['privateKiB'] = int(subprocess.check_output(['du', '-sk', str(work)], text=True).split()[0])
    write(run / 'receipt.json', receipt)
    print(json.dumps(dict(run=str(run), work=str(work), cases=len(cases))))


if __name__ == '__main__':
    main()
