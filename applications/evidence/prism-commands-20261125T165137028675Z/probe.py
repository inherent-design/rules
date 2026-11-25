"""Execute pinned Prism hooks with real Qt processes and private instance/task adapters."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, value):
    p.write_text(json.dumps(value, indent=2) + '\n')


def main():
    assert os.uname().sysname == 'Darwin', 'Selected macOS/Qt installation only'
    ledger_path = ROOT / 'applications/sources/prism-command-selections.json'
    ledger = json.loads(ledger_path.read_text())
    sources = {}
    for row in ledger['sources']:
        p = ROOT / row['cache']
        b = p.read_bytes()
        assert sha(p) == row['sha256']
        assert hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest() == row['gitBlob']
        sources[row['path']] = b
    run = ROOT / 'applications/evidence' / ('prism-commands-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    work = Path(tempfile.mkdtemp(prefix='rules-prism-commands-', dir='/private/tmp'))
    for name in ['home', 'tmp', 'cache', 'config', 'launch', 'game Ω 日本']:
        (work / name).mkdir()
    for name, target in [('commands_driver.cpp', 'driver.cpp'), ('commands_adapter.h', 'adapter.h')]:
        (run / target).write_bytes((HERE / name).read_bytes())
    (run / 'probe.py').write_bytes(Path(__file__).read_bytes())
    copied = ['launcher/LoggedProcess.cpp', 'launcher/LoggedProcess.h', 'launcher/MessageLevel.h',
              'launcher/Commandline.cpp', 'launcher/Commandline.h',
              'launcher/launch/steps/PreLaunchCommand.cpp', 'launcher/launch/steps/PreLaunchCommand.h',
              'launcher/launch/steps/PostLaunchCommand.cpp', 'launcher/launch/steps/PostLaunchCommand.h']
    for path in copied:
        (work / Path(path).name).write_bytes(sources[path])
    (work / 'commands_adapter.h').write_bytes((HERE / 'commands_adapter.h').read_bytes())
    for n in ['LaunchTask.h', 'LaunchStep.h']:
        (work / 'launch' / n).write_text('#pragma once\n#include "commands_adapter.h"\n')
    task = sources['launcher/launch/LaunchTask.cpp'].decode()
    variables = task[task.index('QString expandVariables('):]
    wrapper = sources['launcher/minecraft/launch/LauncherPartLaunch.cpp'].decode()
    begin = wrapper.index('    QString wrapperCommandStr =')
    end = wrapper.index('\n#ifdef Q_OS_LINUX', begin)
    selected = wrapper[begin:end]
    generated = (HERE / 'commands_driver.cpp').read_text().replace('// @@VARIABLE_FUNCTIONS@@', variables).replace('// @@WRAPPER_BLOCK@@', selected)
    (work / 'main.cpp').write_text(generated)
    env = dict(PATH='/usr/bin:/bin', HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'),
               XDG_CACHE_HOME=str(work / 'cache'), XDG_CONFIG_HOME=str(work / 'config'), LANG='en_US.UTF-8')
    commands = []
    def execute(label, argv, allow_failure=False):
        start = time.monotonic()
        with (run / (label + '.stdout')).open('xb') as out, (run / (label + '.stderr')).open('xb') as err:
            # A failed empty-token probe must not create a core dump.
            def no_core():
                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            p = subprocess.Popen(argv, cwd=work, env=env, stdin=subprocess.DEVNULL,
                                 stdout=out, stderr=err, start_new_session=True, preexec_fn=no_core)
            timed = False
            try:
                p.wait(timeout=35)
            except subprocess.TimeoutExpired:
                timed = True
                os.killpg(p.pid, signal.SIGTERM)
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait()
        try:
            os.killpg(p.pid, 0)
            absent = False
        except ProcessLookupError:
            absent = True
        row = dict(label=label, argv=argv, exitCode=p.returncode, pid=p.pid, processGroup=p.pid,
                   processGroupAbsent=absent, timedOut=timed, seconds=time.monotonic()-start,
                   streams={s: sha(run / (label + '.' + s)) for s in ['stdout', 'stderr']})
        commands.append(row)
        write(run / 'commands.json', commands)
        assert absent and not timed, row
        assert allow_failure or p.returncode == 0, (label, (run / (label + '.stderr')).read_text()[-1800:])
        return row
    pkg = '/opt/homebrew/bin/pkg-config'
    execute('qt-version', [pkg, '--modversion', 'Qt6Core'])
    execute('qt-flags', [pkg, '--cflags', '--libs', 'Qt6Core'])
    flags = shlex.split((run / 'qt-flags.stdout').read_text())
    execute('compiler-version', ['/usr/bin/clang++', '--version'])
    moc = '/opt/homebrew/share/qt/libexec/moc'
    moc_flags = [p for p in flags if p.startswith('-I') or p.startswith('-D')]
    headers = ['LoggedProcess.h', 'commands_adapter.h', 'PreLaunchCommand.h', 'PostLaunchCommand.h']
    cpp = ['LoggedProcess.cpp', 'Commandline.cpp', 'PreLaunchCommand.cpp', 'PostLaunchCommand.cpp', 'main.cpp']
    for n in headers:
        target = 'moc_' + Path(n).stem + '.cpp'
        execute('moc-' + Path(n).stem, [moc, '-I' + str(work), *moc_flags, str(work / n), '-o', str(work / target)])
        cpp.append(target)
    binaries = {}
    for variant, options in [('release', ['-DQT_NO_DEBUG']), ('checked', ['-UQT_NO_DEBUG'])]:
        binary = work / ('probe-' + variant)
        execute('compile-' + variant, ['/usr/bin/clang++', '-std=c++20', '-O0', *options,
                '-I' + str(work), *[str(work / n) for n in cpp], '-o', str(binary), *flags,
                '-Wl,-rpath,/opt/homebrew/lib'])
        binaries[variant] = dict(path=str(binary), sha256=sha(binary))
    default = dict(PATH='/usr/bin:/bin', HOME=str(work / 'home'), LANG='en_US.UTF-8',
                   RULES_VALUE='two words', RULES_SPACE='   ')
    # Wrapper-child only records the passed Java invocation; it does not launch Java.
    authored = [
        ('pre-ok', 'pre', '$PROBE child success "two words" "Ω 日本"', False),
        ('post-ok', 'post', '$PROBE child success', False),
        ('pre-exit7', 'pre', '$PROBE child exit7', False),
        ('post-exit7', 'post', '$PROBE child exit7', False),
        ('pre-missing', 'pre', str(work / 'not-installed'), False),
        ('post-missing', 'post', str(work / 'not-installed'), False),
        ('pre-abort', 'pre', '$PROBE child hold', True),
        ('post-abort', 'post', '$PROBE child hold', True),
        ('pre-space', 'pre', '   ', False),
        ('post-empty-quotes', 'post', '""', False),
        ('wrapper-none', 'wrapper', '', False),
        ('wrapper-space', 'wrapper', '   ', False),
        ('wrapper-ok', 'wrapper', '$PROBE wrapper-child "wrapper argument"', False),
        ('wrapper-missing', 'wrapper', str(work / 'not-installed'), False),
        ('wrapper-expanded-space', 'wrapper', '$RULES_SPACE', False),
        ('parse-single-quotes', 'parse', 'program \'two words\'', False),
        ('parse-tab', 'parse', 'program\targument', False),
        ('parse-empty-argument', 'parse', 'program "" tail', False),
        ('parse-unquoted-value', 'parse', 'program $RULES_VALUE', False),
        ('parse-quoted-value', 'parse', 'program "$RULES_VALUE"', False),
    ]
    cases = []
    for label, mode, command, abort in authored:
        variants = ['release', 'checked'] if label in ['pre-space', 'wrapper-expanded-space'] else ['release']
        for variant in variants:
            key = label + '-' + variant
            witness = work / (key + '-child.json')
            request = dict(id=key, mode=mode, command=command, abort=abort, environment=default,
                           cwd=str(work / 'game Ω 日本'), witness=str(witness))
            path = run / (key + '-input.json')
            write(path, request)
            result = execute(key, [binaries[variant]['path'], str(path)], allow_failure=True)
            packets = [json.loads(line) for line in (run / (key + '.stdout')).read_text().splitlines()]
            child = json.loads(witness.read_text()) if witness.exists() else None
            child_absent = None
            if child:
                try:
                    os.kill(child['pid'], 0)
                    child_absent = False
                except ProcessLookupError:
                    child_absent = True
                assert child_absent, (key, 'Owned child still exists')
            cases.append(dict(id=key, variant=variant, requestFile=path.name,
                              helperExitCode=result['exitCode'], packets=packets,
                              child=child, childAbsent=child_absent))
            write(run / 'observed.json', dict(schema=1, cases=cases))
    ps = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,command='], text=True)
    hits = [s for s in ps.splitlines() if str(work) in s and int(s.split()[0]) not in [os.getpid(), os.getppid()]]
    assert not hits
    write(run / 'receipt.json', dict(schema=1, complete=True, work=str(work), cases=len(cases),
        producerSha256=sha(run / 'probe.py'), driverSha256=sha(run / 'driver.cpp'), adapterSha256=sha(run / 'adapter.h'),
        sourceLedgerSha256=sha(ledger_path), generatedSha256=sha(work / 'main.cpp'),
        variableFunctionsSha256=hashlib.sha256(variables.encode()).hexdigest(), wrapperBlockSha256=hashlib.sha256(selected.encode()).hexdigest(),
        compiler=dict(path='/usr/bin/clang++',sha256=sha(Path('/usr/bin/clang++'))),
        moc=dict(path=moc,sha256=sha(Path(moc))), binaries=binaries,
        qt=dict(pkgVersion=(run / 'qt-version.stdout').read_text().strip(),
                framework='/opt/homebrew/lib/QtCore.framework/Versions/A/QtCore',
                sha256=sha(Path('/opt/homebrew/lib/QtCore.framework/Versions/A/QtCore'))),
        workPathProcessMatches=hits, privateAllocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),
        limits=['Real pinned Pre/Post/LoggedProcess source and Qt; adapter instance/environment/Task outcome, no Prism GUI or game.',
                'Wrapper block is unchanged; completion is an adapter, not LauncherPartLaunch game protocol.',
                'Release/checked helpers use O0; neither establishes Prism binary/build correspondence.',
                'Empty-token helper failures are isolated; core dumps disabled. No real account,instance,world,Java or shell invocation.']))
    print(json.dumps(dict(run=str(run.relative_to(ROOT)), work=str(work), cases=len(cases),
                          commands=len(commands), helperFailures=[r['id'] for r in cases if r['helperExitCode'] != 0])))


if __name__ == '__main__':
    main()
