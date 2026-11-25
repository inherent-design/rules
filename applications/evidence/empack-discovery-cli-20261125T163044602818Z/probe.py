"""One-shot installed-CLI discovery controls using private fictional pack documents."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import tempfile
import time
import zipfile

from pending_probe import BINARY, BINARY_SHA, REVISION, fingerprint, fixture

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def snapshot(root):
    if not root.exists():
        return None
    rows = {}
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            p = Path(base) / name
            s = p.lstat()
            row = dict(mode=stat.S_IMODE(s.st_mode), device=s.st_dev, inode=s.st_ino,
                       mtimeNs=s.st_mtime_ns, ctimeNs=s.st_ctime_ns)
            if stat.S_ISLNK(s.st_mode):
                row.update(kind='link', target=os.readlink(p))
            elif stat.S_ISDIR(s.st_mode):
                row.update(kind='directory')
            elif stat.S_ISREG(s.st_mode):
                row.update(kind='file', bytes=s.st_size, sha256=sha(p))
            else:
                raise AssertionError('Unexpected special fixture entry')
            rows[str(p.relative_to(root))] = row
    return rows


def main():
    repo = ROOT.parent / 'empack'
    assert subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip() == REVISION
    assert sha(BINARY) == BINARY_SHA
    vectors_path = ROOT / 'applications/sources/md5-collision-inputs.json'
    vectors = json.loads(vectors_path.read_text())
    payloads = {p['id']: bytes.fromhex(p['hex']) for p in vectors['payloads']}
    assert payloads['a'] != payloads['b']
    assert {hashlib.md5(b).hexdigest() for b in payloads.values()} == {'79054025255fb1a26e4bc422aef54eb4'}
    run = ROOT / 'applications/evidence' / ('empack-discovery-cli-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    work = Path(tempfile.mkdtemp(prefix='rules-empack-discovery-', dir='/private/tmp'))
    (run / 'probe.py').write_bytes(Path(__file__).read_bytes())
    (run / 'fixture.py').write_bytes((Path(__file__).parent / 'pending_probe.py').read_bytes())
    write(run / 'vectors.json', vectors)
    source_paths = ['crates/empack-lib/src/engine/acquisition/discovery.rs',
                    'crates/empack-lib/src/engine/acquisition/discovery/tests.rs',
                    'crates/empack-lib/src/engine/content.rs',
                    'crates/empack-lib/src/application/engine_host/pending.rs',
                    'crates/empack-lib/src/application/engine_host/build.rs',
                    'crates/empack-lib/src/application/engine_host/build/assistance.rs']
    pins = []
    for p in source_paths:
        b = subprocess.check_output(['git', '-C', str(repo), 'show', REVISION + ':' + p])
        assert b == (repo / p).read_bytes()
        pins.append(dict(path=p,sha256=hashlib.sha256(b).hexdigest(),revision=REVISION,
                         url=f'https://github.com/inherent-design/empack/blob/{REVISION}/{p}'))
    commands, cases, groups = [], [], []
    write(run / 'setup.json', dict(schema=1, work=str(work), binary=str(BINARY), binarySha256=BINARY_SHA,
        producerSha256=sha(run / 'probe.py'), fixtureProducerSha256=sha(run / 'fixture.py'),
        vectorsSha256=sha(run / 'vectors.json'), sources=pins,
        limits='Installed0.8.8binary;current source correspondence not established. Fictional manual selections and inert payloads,not provider/game evidence. Proxies refuse outbound acquisition,not an OS network sandbox.'))

    def capture(base):
        return {n: snapshot(base / n) for n in ['project', 'state', 'cache', 'downloads', 'outside']}

    def save_image(name, image):
        encoded = json.dumps(image, sort_keys=True, separators=(',', ':')).encode()
        target = run / (name + '.json.gz')
        target.write_bytes(gzip.compress(encoded, mtime=0))
        return dict(file=target.name, sha256=sha(target), decodedSha256=hashlib.sha256(encoded).hexdigest())

    def command(base, label, args):
        before = capture(base)
        argv = [str(BINARY), '--state-dir', str(base / 'state'), '--cache-dir', str(base / 'cache'),
                '--workdir', str(base / 'project'), '--yes', '--color', 'never', *args]
        env = dict(PATH='/usr/bin:/bin', HOME=str(base / 'home'), TMPDIR=str(base / 'tmp'),
                   LANG='en_US.UTF-8', EMPACK_NET_TIMEOUT='1', HTTP_PROXY='http://127.0.0.1:9',
                   HTTPS_PROXY='http://127.0.0.1:9', ALL_PROXY='http://127.0.0.1:9', NO_PROXY='', EMPACK_COLOR='never')
        start = time.monotonic()
        with (run / (label + '.stdout')).open('xb') as out, (run / (label + '.stderr')).open('xb') as err:
            p = subprocess.Popen(argv, cwd=base, env=env, stdin=subprocess.DEVNULL,
                                 stdout=out, stderr=err, start_new_session=True)
            groups.append(p.pid)
            write(run / 'owned-groups.json', groups)
            timed = False
            try:
                p.wait(timeout=40)
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
        after = capture(base)
        result = dict(label=label, argv=argv, exitCode=p.returncode, timedOut=timed,
                      pid=p.pid, processGroupAbsent=absent, seconds=time.monotonic()-start,
                      changedScopes=[n for n in before if before[n] != after[n]],
                      before=save_image(label + '-before', before), after=save_image(label + '-after', after),
                      streams={s: sha(run / (label + '.' + s)) for s in ['stdout', 'stderr']})
        commands.append(result)
        write(run / 'commands.json', commands)
        assert not timed and absent, label
        return result

    def prepare(name, strong=False):
        base = work / name
        for n in ['project', 'downloads', 'outside', 'home', 'tmp']:
            (base / n).mkdir(parents=True)
        canonical, _ = fixture(base / 'project')
        author = json.loads((base / 'project/empack.yml').read_text())
        lock = json.loads((base / 'project/empack.lock').read_text())
        for doc in [author, canonical, lock]:
            del doc['dependencies']['second']
        del lock['coverage']['second']
        del lock['required-edges']['second']
        digests = dict(md5=vectors['payloads'][0]['md5'])
        if strong:
            digests['sha256'] = vectors['payloads'][0]['sha256']
        selected = lock['dependencies']['first']['files'][0]
        selected['expected'] = dict(digests=digests, size=128, **{'accepted-observation': None})
        selected['provenance']['declared-digests'] = digests
        lock['intent-revision'] = fingerprint(canonical)
        write(base / 'project/empack.yml', author)
        write(base / 'project/empack.lock', lock)
        write(run / (name + '-author.json'), author)
        write(run / (name + '-lock.json'), lock)
        write(run / (name + '-canonical.json'), canonical)
        result = command(base, name + '-check', ['check', '--json'])
        assert result['exitCode'] == 0, 'Authored fixture must be admitted first'
        result = command(base, name + '-suspend', ['build', '--ad-hoc', 'modrinth'])
        assert result['exitCode'] != 0 and not list((base / 'project').rglob('*.mrpack'))
        result = command(base, name + '-list', ['pending', 'list', '--json'])
        assert result['exitCode'] == 0
        report = json.loads((run / (name + '-list.stdout')).read_text())
        assert len(report['operations']) == 1
        op = report['operations'][0]
        return base, op['id'], op['inputs'][0]['key']

    def product(base):
        products = list((base / 'project').rglob('*.mrpack'))
        if not products:
            return None
        assert len(products) == 1
        path = products[0]
        with zipfile.ZipFile(path) as z:
            data = z.read('overrides/resourcepacks/first.zip')
            result = dict(path=str(path.relative_to(base)), sha256=sha(path),
                          members=z.namelist(), payloadSha256=hashlib.sha256(data).hexdigest(),
                          payloadHex=data.hex(), bytes=len(data))
        return result

    try:
        base, selected, key = prepare('ambiguous')
        for name in ['a', 'b']:
            (base / 'downloads' / (name + '.bin')).write_bytes(payloads[name])
        result = command(base, 'ambiguous-scan', ['pending', 'resume', selected, '--downloads-dir', str(base / 'downloads')])
        assert result['exitCode'] != 0 and product(base) is None
        assert 'ambiguous' in (run / 'ambiguous-scan.stderr').read_text().lower()
        cases.append(dict(id='ambiguous', scan='ambiguous-scan', product=None))
        result = command(base, 'explicit-b', ['pending', 'resume', selected, '--file', key + '=' + str(base / 'downloads/b.bin')])
        assert result['exitCode'] == 0
        out = product(base)
        assert out and out['payloadSha256'] == vectors['payloads'][1]['sha256']
        cases.append(dict(id='explicit-b', scan='explicit-b', product=out))

        base, selected, _ = prepare('duplicates')
        for name in ['a', 'copy']:
            (base / 'downloads' / name).write_bytes(payloads['a'])
        result = command(base, 'duplicates-scan', ['pending', 'resume', selected, '--downloads-dir', str(base / 'downloads')])
        assert result['exitCode'] == 0
        out = product(base)
        assert out and out['payloadSha256'] == vectors['payloads'][0]['sha256']
        cases.append(dict(id='duplicates', scan='duplicates-scan', product=out))

        base, selected, _ = prepare('strong', strong=True)
        for name in ['a', 'b']:
            (base / 'downloads' / name).write_bytes(payloads[name])
        result = command(base, 'strong-scan', ['pending', 'resume', selected, '--downloads-dir', str(base / 'downloads')])
        assert result['exitCode'] == 0
        out = product(base)
        assert out and out['payloadSha256'] == vectors['payloads'][0]['sha256']
        cases.append(dict(id='strong', scan='strong-scan', product=out))

        base, selected, key = prepare('entries')
        (base / 'downloads/payload').write_bytes(payloads['a'])
        for n in range(10000):
            (base / 'downloads' / f'empty-{n:05}').touch()
        result = command(base, 'entries-scan', ['pending', 'resume', selected, '--downloads-dir', str(base / 'downloads')])
        assert result['exitCode'] != 0 and product(base) is None
        assert 'entry limit exceeded' in (run / 'entries-scan.stderr').read_text().lower()
        cases.append(dict(id='entries', scan='entries-scan', product=None, entries=10001))
        result = command(base, 'entries-explicit', ['pending', 'resume', selected, '--file', key + '=' + str(base / 'downloads/payload')])
        assert result['exitCode'] == 0
        out = product(base)
        assert out and out['payloadSha256'] == vectors['payloads'][0]['sha256']
        cases.append(dict(id='entries-explicit', scan='entries-explicit', product=out))
        write(run / 'results.json', dict(schema=1, complete=True, cases=cases))
    except BaseException as error:
        write(run / 'incomplete.json', dict(type=type(error).__name__, message=str(error), cases=cases,
                                           commandsCompleted=len(commands)))
        raise
    finally:
        rows = []
        for pid in groups:
            try:
                os.killpg(pid, 0)
                absent = False
            except ProcessLookupError:
                absent = True
            rows.append(dict(group=pid, absent=absent))
        ps = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,command='], text=True)
        hits = [s for s in ps.splitlines() if str(work) in s and int(s.split()[0]) not in [os.getpid(), os.getppid()]]
        write(run / 'closure.json', dict(schema=1, groups=rows, workPathProcessMatches=hits,
              privateAllocatedKiB=int(subprocess.check_output(['du', '-sk', str(work)], text=True).split()[0]),
              limitations='Only owned command groups/exact fixture-path scan. Private inputs, state and cache remain retained.'))
    print(json.dumps(dict(run=str(run.relative_to(ROOT)), work=str(work), commands=len(commands), cases=len(cases))))


if __name__ == '__main__':
    main()
