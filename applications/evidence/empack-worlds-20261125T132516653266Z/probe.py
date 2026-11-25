"""One disposable snapshot workflow; never launch Java or touch real worlds."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import stat
import subprocess
import tempfile
from datetime import datetime, timezone
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, value):
    p.write_text(json.dumps(value, indent=2) + '\n')


def snapshot(root):
    result = {}
    if not root.exists():
        return result
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            p = Path(directory) / name
            s = p.lstat(); key = p.relative_to(root).as_posix()
            if stat.S_ISLNK(s.st_mode):
                result[key] = dict(kind='symlink', target=os.readlink(p))
            elif stat.S_ISREG(s.st_mode):
                result[key] = dict(kind='file', sha256=sha(p), bytes=s.st_size,
                                   mode=stat.S_IMODE(s.st_mode), mtimeNs=str(s.st_mtime_ns))
            else:
                assert stat.S_ISDIR(s.st_mode)
                result[key] = dict(kind='directory')
    return result


def main():
    binary = Path('/Users/zer0cell/.local/bin/empack')
    assert sha(binary) == '99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
    run = ROOT / 'applications/evidence' / ('empack-worlds-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    work = Path(tempfile.mkdtemp(prefix='rules-empack-worlds-', dir='/private/tmp'))
    for p in ['project', 'state', 'cache', 'tmp', 'releases', 'instances']:
        (work / p).mkdir(mode=0o700)
    project = work / 'project'
    env = dict(PATH=os.environ['PATH'], LANG='en_US.UTF-8', TMPDIR=str(work / 'tmp'))
    shutil.copyfile(__file__, run / 'probe.py')
    setup = dict(schema=1, work=str(work), binary=str(binary), binarySha256=sha(binary),
                 producerSha256=sha(run / 'probe.py'), environment=env,
                 policy='Disposable source/world marker bytes only; no Java, game, live instance, channel, or host installation.')
    write(run / 'setup.json', setup)
    progress = dict(commands=[], observations=[])
    def save(): write(run / 'progress.json', progress)
    def command(label, cwd, args, expected=0):
        argv = [str(binary), '--state-dir', str(work / 'state'), '--cache-dir', str(work / 'cache'),
                '--workdir', str(cwd), '--color', 'never', '--yes', *args]
        p = subprocess.Popen(argv, cwd=work, env=env, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            out, err = p.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGTERM)
            try: out, err = p.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL); out, err = p.communicate(timeout=3)
            (run / (label + '.stdout')).write_bytes(out); (run / (label + '.stderr')).write_bytes(err)
            progress['commands'].append(dict(label=label, argv=argv, pid=p.pid, timedOut=True, exitCode=p.returncode))
            save(); raise RuntimeError('Owned command timed out; inspect before continuing')
        (run / (label + '.stdout')).write_bytes(out); (run / (label + '.stderr')).write_bytes(err)
        try: os.killpg(p.pid, 0); absent = False
        except ProcessLookupError: absent = True
        progress['commands'].append(dict(label=label, argv=argv, pid=p.pid, exitCode=p.returncode,
            groupAbsent=absent, stdoutSha256=sha(run / (label + '.stdout')), stderrSha256=sha(run / (label + '.stderr'))))
        save(); assert absent and p.returncode == expected, (label, p.returncode, err.decode(errors='replace'))
        return out
    def observe(label, instance):
        record = json.loads((instance / '.empack/instance.json').read_text())
        write(run / (label + '-instance.json'), record)
        item = dict(label=label, instance=str(instance), snapshot=snapshot(instance), record=record)
        progress['observations'].append(item); save(); return item
    def source(label, files):
        pack = project / 'pack'
        if pack.exists(): shutil.rmtree(pack)
        pack.mkdir()
        for path, data in files.items():
            target = pack / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(data)
        write(run / (label + '-sources.json'), files)
    def build(label, files):
        source(label, files)
        command('build-' + label, project, ['build', '--ad-hoc', 'empack', '--delivery', 'bundled',
            '--environment', 'both', '--updates', 'snapshot', '--format', 'zip'])
        archives = list((project / 'dist').iterdir()); assert len(archives) == 1
        archive = archives[0]; destination = work / 'releases' / label; destination.mkdir()
        with zipfile.ZipFile(archive) as z:
            assert len(z.infolist()) <= 64 and sum(e.file_size for e in z.infolist()) < 1024*1024
            names = set()
            for e in z.infolist():
                rel = PurePosixPath(e.filename)
                assert not rel.is_absolute() and '..' not in rel.parts and '\\' not in e.filename
                assert e.filename not in names; names.add(e.filename)
                assert stat.S_IFMT(e.external_attr >> 16) in [0, stat.S_IFREG, stat.S_IFDIR]
                target = destination.joinpath(*rel.parts)
                if e.is_dir(): target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open('xb') as f: f.write(z.read(e))
        release = destination / 'release.json'; document = json.loads(release.read_text())
        shutil.copyfile(release, run / ('release-' + label + '.json'))
        progress['observations'].append(dict(label='release-' + label, release=sha(release), archiveSha256=sha(archive), files=document['files']))
        save(); return release
    def install(label, instance, release, *extra):
        command(label, instance, ['instance', 'install', str(release), '--sha256', sha(release), *extra])
        return observe(label, instance)
    command('version', project, ['--version'])
    # A normal current author document, not an edited release descriptor.
    (project / 'empack.yml').write_text('schema: 6\npack:\n  id: pack-780ba8cb7c8e405692ce82e144d58731\n  name: Rules world fixture\n  version: same-label\n  authors: [Rules fixture]\nruntime:\n  minecraft: "1.21.1"\n  loader: vanilla\n  java:\n    preferred: 21\ndependencies: {}\n')
    shutil.copyfile(project / 'empack.yml', run / 'empack.yml')
    command('sync', project, ['sync'])
    afiles = {'world/level.dat': 'template A\n', 'world/region/a.mca': 'region A\n',
              'saves/Study/level.dat': 'client template A\n', 'payload.txt': 'managed A\n'}
    bfiles = {'world/level.dat': 'template B\n', 'world/region/a.mca': 'region B\n',
              'world/region/b.mca': 'new region B\n', 'saves/Study/level.dat': 'client template B\n',
              'payload.txt': 'managed B\n', 'config/rules.txt': 'ordinary seed B\n'}
    a = build('a', afiles); b = build('b', bfiles)
    c = build('c', {'payload.txt': 'managed C\n', 'config/rules.txt': 'ordinary seed C\n'})
    fresh = work / 'instances/fresh'; fresh.mkdir()
    install('initial-a', fresh, a)
    game = fresh / 'game'; world = game / 'world'
    assert (world / 'level.dat').read_text() == 'template A\n'
    (world / 'level.dat').write_text('played world\n'); (world / 'region/a.mca').unlink()
    (world / 'runtime-output.txt').write_text('runtime output\n')
    before = snapshot(fresh)
    command('preview-b', fresh, ['instance', 'install', str(b), '--sha256', sha(b), '--dry-run'])
    assert snapshot(fresh) == before
    write(run / 'preview-instance-files.json', dict(before=before, after=snapshot(fresh)))
    install('update-b', fresh, b)
    assert (world / 'level.dat').read_text() == 'played world\n'
    assert not (world / 'region/a.mca').exists() and not (world / 'region/b.mca').exists()
    assert (game / 'payload.txt').read_text() == 'managed B\n'
    (game / 'config/rules.txt').unlink()
    command('repair-b', fresh, ['instance', 'repair']); observe('repair-b', fresh)
    assert (game / 'config/rules.txt').read_text() == 'ordinary seed B\n'
    assert not (world / 'region/a.mca').exists()
    command('rollback-a', fresh, ['instance', 'rollback']); observe('rollback-a', fresh)
    assert (world / 'level.dat').read_text() == 'played world\n'
    assert (game / 'payload.txt').read_text() == 'managed A\n'
    shutil.rmtree(world)  # Only this private fixture's synthetic world.
    install('omit-world-c', fresh, c); install('reintroduce-b', fresh, b)
    assert not world.exists()
    command('check-fresh', fresh, ['instance', 'check', '--json'])
    for name in ['empty-world', 'world-file', 'world-link', 'blocked-ancestor']:
        instance = work / 'instances' / name; (instance / 'game').mkdir(parents=True)
        game = instance / 'game'
        if name == 'empty-world': (game / 'world').mkdir()
        elif name == 'world-file': (game / 'world').write_text('occupied regular file\n')
        elif name == 'world-link':
            outside = work / 'owned-link-target'; outside.mkdir(); (outside / 'marker.txt').write_text('outside sentinel\n')
            (game / 'world').symlink_to(outside, target_is_directory=True)
        else: (game / 'saves').write_text('blocked ancestor\n')
        initial = snapshot(game)
        install('occupied-' + name, instance, a)
        if name == 'empty-world': assert list((game / 'world').iterdir()) == []
        elif name == 'world-file': assert (game / 'world').read_text() == 'occupied regular file\n'
        elif name == 'world-link':
            assert (game / 'world').is_symlink() and list(outside.iterdir()) == [outside / 'marker.txt']
            assert (outside / 'marker.txt').read_text() == 'outside sentinel\n'
        else: assert (game / 'saves').read_text() == 'blocked ancestor\n'
        write(run / (name + '-occupancy.json'), dict(before=initial, after=snapshot(game)))
    write(run / 'completed.json', dict(schema=1, status='complete', commands=len(progress['commands']),
          commandGroupsAbsent=all(c.get('groupAbsent') for c in progress['commands']), noRuntimeLaunched=True))
    print(json.dumps(dict(run=str(run), work=str(work), commands=len(progress['commands']), status='complete')))


if __name__ == '__main__':
    main()
