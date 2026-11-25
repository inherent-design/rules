"""One generated reference snapshot -> original Prism INI/command parsers; no game/Java."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'empack'))
from pending_probe import BINARY, BINARY_SHA, REVISION, fingerprint, fixture

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, value):
    p.write_text(json.dumps(value, indent=2) + '\n')


def main():
    ledger = json.loads((ROOT / 'applications/sources/prism-command-paths-selections.json').read_text())
    source_bytes = {}
    for row in ledger['prism']:
        p = ROOT / row['cache']
        b = p.read_bytes()
        assert sha(p) == row['sha256']
        assert hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest() == row['gitBlob']
        source_bytes[row['path']] = b
    repo = ROOT.parent / 'empack'
    for row in ledger['empack']:
        b = subprocess.check_output(['git', '-C', str(repo), 'show', row['revision'] + ':' + row['path']])
        assert hashlib.sha256(b).hexdigest() == row['sha256']
        source_bytes[row['path']] = b
    assert sha(BINARY) == BINARY_SHA
    prior = ROOT / 'applications/evidence/prism-commands-20261125T165137028675Z'
    previous = json.loads((prior / 'receipt.json').read_text())
    parser = Path(previous['binaries']['release']['path'])
    assert sha(parser) == previous['binaries']['release']['sha256']
    continuing = len(sys.argv) == 2
    assert len(sys.argv) <= 2
    if continuing:
        run = Path(sys.argv[1]).resolve()
        assert run.parent == ROOT / 'applications/evidence' and run.name.startswith('prism-command-paths-')
        setup = json.loads((run / 'setup.json').read_text())
        assert sha(run / 'probe.py') == setup['producerSha256']
        assert sha(run / 'fixture.py') == setup['fixtureProducerSha256']
        assert sha(parser) == setup['parserSha256']
        assert not (run / 'continuation-probe.py').exists(), 'Inspect an existing continuation; never restart it'
        work = Path(setup['work'])
        (run / 'continuation-probe.py').write_bytes(Path(__file__).read_bytes())
        write(run / 'continuation.json', dict(schema=1,producerSha256=sha(run / 'continuation-probe.py'),
            correction='After successful check/build,the original collector stopped on an assumed2MiB artifact bound. Actual bootstrap JAR is3,104,749B and source allows8MiB. Continue existing artifact with8MiB JAR+1MiB remaining-byte bounds; native check/build are not repeated.'))
    else:
        run = ROOT / 'applications/evidence' / ('prism-command-paths-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        run.mkdir()
        work = Path(tempfile.mkdtemp(prefix='rules-prism-command-paths-', dir='/private/tmp'))
        for n in ['project', 'home', 'tmp', 'state', 'cache', 'source', 'source/settings']:
            (work / n).mkdir(mode=0o700, parents=True, exist_ok=True)
        (run / 'probe.py').write_bytes(Path(__file__).read_bytes())
        (run / 'fixture.py').write_bytes((ROOT / 'applications/empack/pending_probe.py').read_bytes())
        canonical, _ = fixture(work / 'project')
        author = json.loads((work / 'project/empack.yml').read_text())
        lock = json.loads((work / 'project/empack.lock').read_text())
        for doc in [author, canonical, lock]:
            doc['dependencies'] = {}
        lock['coverage'], lock['required-edges'] = {}, {}
        lock['intent-revision'] = fingerprint(canonical)
        write(work / 'project/empack.yml', author)
        write(work / 'project/empack.lock', lock)
        write(run / 'author.json', author)
        write(run / 'lock.json', lock)
        write(run / 'canonical.json', canonical)
        (work / 'project/pack/config').mkdir(parents=True)
        (work / 'project/pack/config/marker.txt').write_bytes(b'owned fixture\n')
    copied = []
    for path, b in source_bytes.items():
        if path.startswith('launcher/'):
            target = work / 'source' / path.removeprefix('launcher/')
            target.parent.mkdir(parents=True, exist_ok=True)
            if continuing:
                assert sha(target) == hashlib.sha256(b).hexdigest()
            else:
                target.write_bytes(b)
            copied.append(dict(path=path, relative=str(target.relative_to(work)), sha256=sha(target)))
    reader_source = source_bytes['scripts/consumer/prism-config-probe.cpp']
    if continuing:
        assert sha(work / 'reader.cpp') == setup['readerSourceSha256']
    else:
        (work / 'reader.cpp').write_bytes(reader_source)
        write(run / 'setup.json', dict(schema=1, work=str(work), binary=str(BINARY), binarySha256=BINARY_SHA,
        sourceRevision=REVISION, sourceLedgerSha256=sha(ROOT / 'applications/sources/prism-command-paths-selections.json'),
        producerSha256=sha(run / 'probe.py'), fixtureProducerSha256=sha(run / 'fixture.py'),
        priorParserReceipt=str(prior.relative_to(ROOT) / 'receipt.json'), priorParserReceiptSha256=sha(prior / 'receipt.json'),
        parser=str(parser), parserSha256=sha(parser), copiedSources=copied,
        readerSourceSha256=hashlib.sha256(reader_source).hexdigest(),
        limits='Installed engine generates an empty-dependency reference Prism snapshot; no bootstrap/game/Java/Windows executable launch. Proxies refuse outbound acquisition, not an OS sandbox.'))
    env = dict(PATH='/usr/bin:/bin', HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'), LANG='en_US.UTF-8',
               EMPACK_NET_TIMEOUT='1', HTTP_PROXY='http://127.0.0.1:9', HTTPS_PROXY='http://127.0.0.1:9',
               ALL_PROXY='http://127.0.0.1:9', NO_PROXY='', EMPACK_COLOR='never')
    commands = json.loads((run / 'commands.json').read_text()) if continuing else []
    if continuing:
        assert [(r['label'],r['exitCode']) for r in commands] == [('native-check',0),('native-build',0)]
    def command(label, argv):
        start = time.monotonic()
        with (run / (label + '.stdout')).open('xb') as out, (run / (label + '.stderr')).open('xb') as err:
            p = subprocess.Popen(argv, cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
            timed = False
            try:
                p.wait(timeout=45)
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
        row = dict(label=label, argv=argv, exitCode=p.returncode, pid=p.pid, processGroupAbsent=absent,
                   timedOut=timed, seconds=time.monotonic()-start,
                   streams={s:sha(run / (label + '.' + s)) for s in ['stdout', 'stderr']})
        commands.append(row)
        write(run / 'commands.json', commands)
        assert not timed and absent and p.returncode == 0, (label, (run / (label + '.stderr')).read_text()[-2400:])
        return row
    try:
        prefix = [str(BINARY), '--state-dir', str(work / 'state'), '--cache-dir', str(work / 'cache'),
                  '--workdir', str(work / 'project'), '--yes', '--color', 'never']
        if not continuing:
            command('native-check', prefix + ['check', '--json'])
            command('native-build', prefix + ['build', '--ad-hoc', 'prism', '--delivery', 'references',
                                             '--environment', 'client', '--updates', 'snapshot', '--format', 'zip'])
        archives = list((work / 'project/dist').glob('*.zip'))
        assert len(archives) == 1
        archive = archives[0]
        if continuing:
            assert sha(run / 'reference.zip') == sha(archive)
        else:
            (run / 'reference.zip').write_bytes(archive.read_bytes())
        with zipfile.ZipFile(archive) as z:
            assert len(z.infolist()) < 64
            assert z.getinfo('.empack-tools/empack-bootstrap.jar').file_size <= 8 << 20
            assert sum(n.file_size for n in z.infolist() if n.filename != '.empack-tools/empack-bootstrap.jar') <= 1 << 20
            config = z.read('instance.cfg')
            members = [dict(path=n.filename,bytes=n.file_size,sha256=hashlib.sha256(z.read(n)).hexdigest()) for n in z.infolist()]
        (run / 'instance.cfg').write_bytes(config)
        (work / 'instance.cfg').write_bytes(config)
        command('qt-flags', ['/opt/homebrew/bin/pkg-config','--cflags','--libs','Qt6Core','Qt6Network'])
        flags = shlex.split((run / 'qt-flags.stdout').read_text())
        reader = work / 'ini-reader'
        command('compile-reader', ['/usr/bin/clang++','-std=c++20','-O0','-DQT_NO_DEBUG','-ffunction-sections','-fdata-sections',
                                  '-I'+str(work/'source'),str(work/'reader.cpp'),str(work/'source/settings/INIFile.cpp'),
                                  str(work/'source/Json.cpp'),'-o',str(reader),*flags,'-Wl,-dead_strip','-Wl,-rpath,/opt/homebrew/lib'])
        command('reader-environment', [str(reader),'--environment'])
        command('read-generated', [str(reader),str(work/'instance.cfg')])
        decoded = json.loads((run / 'read-generated.stdout').read_text())
        assert decoded['loaded'] and decoded['override'] and decoded['prepare'] and decoded['wrapper']
        assert decoded['prepare'].startswith('"$INST_JAVA" ') and decoded['wrapper'].startswith('"$INST_JAVA" ')
        observed = []
        for name, java in [('posix','/opt/Java Runtime/bin/java'),
                           ('windows-native',r'C:\Program Files\Java\bin\javaw.exe'),
                           ('windows-forward','C:/Program Files/Java/bin/javaw.exe')]:
            for role in ['prepare','wrapper']:
                label = name + '-' + role
                request = dict(mode='parse',command=decoded[role],abort=False,environment=dict(INST_JAVA=java,PATH='/usr/bin:/bin'),
                               cwd=str(work/'project'),witness=str(work/(label+'-unused.json')))
                path = run / (label + '-input.json')
                write(path,request)
                command(label,[str(parser),str(path)])
                rows = [json.loads(s) for s in (run/(label+'.stdout')).read_text().splitlines()]
                assert len(rows) == 1 and rows[0]['phase'] == 'before'
                packet = rows[0]
                actual = packet['hookArgs'] if role == 'prepare' else packet['wrapperArgs']
                assert actual
                observed.append(dict(id=label,role=role,expectedProgram=java,actualProgram=actual[0],preserved=actual[0]==java,
                                     consumerArgs=actual,qtVersion=packet['qtVersion']))
        write(run/'observed.json',dict(schema=1,cases=observed))
        assert [r['id'] for r in observed if not r['preserved']] == ['windows-native-wrapper']
        ps=subprocess.check_output(['ps','-axo','pid=,ppid=,command='],text=True)
        hits=[s for s in ps.splitlines() if str(work) in s and int(s.split()[0]) not in [os.getpid(),os.getppid()]]
        assert not hits
        write(run/'receipt.json',dict(schema=1,complete=True,work=str(work),commands=len(commands),cases=len(observed),
            archiveSha256=sha(run/'reference.zip'),configSha256=sha(run/'instance.cfg'),members=members,
            iniReaderSha256=sha(reader),workPathProcessMatches=hits,
            privateAllocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),
            scope='Actual installed-engine reference export and unchanged Prism INI/variable/command parser stages on Mac;Windows-style paths are data,not a Windows process-launch test.'))
    except BaseException as error:
        write(run/('continuation-incomplete.json' if continuing else 'incomplete.json'),dict(schema=1,errorType=type(error).__name__,message=str(error),completedCommands=len(commands)))
        raise
    print(json.dumps(dict(run=str(run.relative_to(ROOT)),work=str(work),commands=len(commands),cases=len(observed),
                          programLoss=[r['id'] for r in observed if not r['preserved']])))


if __name__ == '__main__':
    main()
