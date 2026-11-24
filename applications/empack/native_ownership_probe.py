#!/usr/bin/env python3
"""Continue the explicitly prepared private ownership fixture once; no games/network."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    setup = json.loads((run / 'setup.json').read_text())
    work, project = run / 'work', run / 'work/parent/project'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(Path(setup['binary'])) == setup['binarySha256'] == '99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
    assert (project / 'pack/config/rules.txt').read_text() == 'publisher seed A\n'
    assert (project / 'pack/payload.txt').read_text() == 'publisher managed A\n'
    assert not (work / 'instance').exists() and not (run / 'ownership-started.json').exists()
    # This is deliberately a one-shot continuation of an inspected fixture.
    # A failed/unknown run requires inspection; it is never silently restarted.
    (run / 'ownership-started.json').write_text(json.dumps({'schema': 1, 'probeSha256': sha(Path(__file__))}, indent=2) + '\n')
    shutil.copyfile(__file__, run / 'ownership-probe.py')
    commands, observations = [], []
    instance = work / 'instance'
    instance.mkdir(mode=0o700)

    def record():
        (run / 'progress.json').write_text(json.dumps({'commands': commands, 'observations': observations}, indent=2) + '\n')

    def command(label, root, args, expected=0):
        argv = [setup['binary'], '--state-dir', str(work / 'state'), '--cache-dir', str(work / 'cache'),
                '--workdir', str(root), '--color', 'never', '--yes', *args]
        result = subprocess.run(argv, cwd=work, env=setup['environment'], input=b'', capture_output=True, timeout=30)
        (run / (label + '.stdout')).write_bytes(result.stdout)
        (run / (label + '.stderr')).write_bytes(result.stderr)
        commands.append({'label': label, 'argv': argv, 'exitCode': result.returncode,
                         'stdoutSha256': sha(run / (label + '.stdout')), 'stderrSha256': sha(run / (label + '.stderr'))})
        record()
        assert result.returncode == expected, (label, result.returncode, result.stderr.decode(errors='replace'))
        return result

    def snapshot():
        result = {}
        for p in sorted(instance.rglob('*')):
            s = p.lstat()
            assert not stat.S_ISLNK(s.st_mode), p
            if p.is_file():
                result[p.relative_to(instance).as_posix()] = {'sha256': sha(p), 'bytes': s.st_size,
                    'mode': stat.S_IMODE(s.st_mode), 'mtimeNs': str(s.st_mtime_ns)}
        return result

    def extract(label):
        archives = [p for p in (project / 'dist').iterdir() if p.is_file()]
        assert len(archives) == 1 and zipfile.is_zipfile(archives[0])
        destination = work / 'releases' / label
        destination.mkdir(parents=True)
        total = 0
        with zipfile.ZipFile(archives[0]) as archive:
            assert len(archive.infolist()) <= 64
            names = set()
            for entry in archive.infolist():
                path = PurePosixPath(entry.filename)
                assert not path.is_absolute() and '..' not in path.parts and '\\' not in entry.filename
                assert entry.filename not in names
                names.add(entry.filename)
                assert stat.S_IFMT(entry.external_attr >> 16) in [0, stat.S_IFREG, stat.S_IFDIR]
                total += entry.file_size
                assert entry.file_size <= 2 * 1024 * 1024 and total <= 16 * 1024 * 1024
                target = destination.joinpath(*path.parts)
                if entry.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open('xb') as output:
                        output.write(archive.read(entry))
        manifest = destination / 'release.json'
        data = json.loads(manifest.read_text())
        assert data['schema'] == 2
        policies = {f['destination']: f['policy'] for f in data['files']}
        assert set(policies) == {'config/rules.txt', 'payload.txt'}
        assert policies['config/rules.txt'] == 'seed'
        shutil.copyfile(manifest, run / ('release-' + label + '.json'))
        result = {'label': label, 'release': sha(manifest), 'archiveSha256': sha(archives[0]),
                  'policies': policies, 'pack': data['pack'], 'version': data['version']}
        observations.append({'kind': 'produced-release', **result})
        record()
        return manifest, result

    build = ['build', '--ad-hoc', 'empack', '--delivery', 'bundled', '--environment', 'both', '--updates', 'snapshot', '--format', 'zip']
    a, aid = extract('a')
    assert aid['policies']['payload.txt'] == 'managed'
    command('install-a', instance, ['instance', 'install', str(a), '--sha256', aid['release']])
    assert (instance / 'game/config/rules.txt').read_text() == 'publisher seed A\n'
    assert (instance / 'game/payload.txt').read_text() == 'publisher managed A\n'
    (instance / 'game/config/rules.txt').write_text('player seed choice\n')
    (instance / 'game/player-note.txt').write_text('unowned player note\n')
    (project / 'pack/config/rules.txt').write_text('publisher seed B\n')
    (project / 'pack/payload.txt').write_text('publisher managed B\n')
    command('build-b', project, build)
    b, bid = extract('b')
    assert aid['pack'] == bid['pack'] and aid['release'] != bid['release']
    before = snapshot()
    command('preview-b', instance, ['instance', 'install', str(b), '--sha256', bid['release'], '--dry-run'])
    assert snapshot() == before
    observations.append({'kind': 'preview-preserves-instance-files', 'before': before, 'after': snapshot()})
    command('install-b', instance, ['instance', 'install', str(b), '--sha256', bid['release']])
    assert (instance / 'game/config/rules.txt').read_text() == 'player seed choice\n'
    assert (instance / 'game/player-note.txt').read_text() == 'unowned player note\n'
    assert (instance / 'game/payload.txt').read_text() == 'publisher managed B\n'
    observations.append({'kind': 'ordinary-update', 'seed': 'preserved', 'unowned': 'preserved', 'managed': 'updated'})
    (instance / 'game/payload.txt').write_text('local managed edit\n')
    before = snapshot()
    command('modified-managed-refused', instance, ['instance', 'install', str(b), '--sha256', bid['release']], expected=1)
    assert snapshot() == before
    observations.append({'kind': 'modified-managed-refusal', 'before': before, 'after': snapshot()})
    command('preserve-managed', instance, ['instance', 'install', str(b), '--sha256', bid['release'], '--preserve', 'payload.txt'])
    assert (instance / 'game/payload.txt').read_text() == 'local managed edit\n'
    command('check-accepted-override', instance, ['instance', 'check', '--json'])
    (project / 'empack.bindings.yml').write_text('schema: 1\nbindings: {}\npolicies:\n  payload.txt: seed\n')
    command('sync-seed-policy', project, ['sync'])
    command('build-c', project, build)
    c, cid = extract('c')
    assert cid['policies']['payload.txt'] == 'seed'
    command('managed-to-seed', instance, ['instance', 'install', str(c), '--sha256', cid['release']])
    assert (instance / 'game/payload.txt').read_text() == 'local managed edit\n'
    observations.append({'kind': 'managed-to-seed', 'existingModifiedBytes': 'preserved without override'})
    before = snapshot()
    command('seed-to-managed-refused', instance, ['instance', 'install', str(b), '--sha256', bid['release']], expected=1)
    assert snapshot() == before
    observations.append({'kind': 'seed-to-managed-refusal', 'before': before, 'after': snapshot()})
    command('seed-to-managed-approved', instance, ['instance', 'install', str(b), '--sha256', bid['release'], '--replace', 'payload.txt'])
    assert (instance / 'game/payload.txt').read_text() == 'publisher managed B\n'
    (instance / 'game/payload.txt').unlink()
    command('repair-missing-managed', instance, ['instance', 'repair'])
    assert (instance / 'game/payload.txt').read_text() == 'publisher managed B\n'
    assert (instance / 'game/config/rules.txt').read_text() == 'player seed choice\n'
    assert (instance / 'game/player-note.txt').read_text() == 'unowned player note\n'
    command('check-repaired', instance, ['instance', 'check', '--json'])
    command('inspect-final', instance, ['instance', 'inspect'])
    observations.append({'kind': 'final', 'instanceFiles': snapshot(), 'release': bid['release']})
    record()
    (run / 'receipt.json').write_text(json.dumps({'schema': 1, 'kind': 'Native CLI producer/instance ownership flow',
        'binarySha256': setup['binarySha256'], 'probeSha256': sha(run / 'ownership-probe.py'),
        'progressSha256': sha(run / 'progress.json'), 'commands': len(commands), 'releaseIds': [aid['release'], bid['release'], cid['release']],
        'limits': ['One installed0.8.8macOSbinary,two tiny custom files,Vanilla metadata;no runtime/game/GUI/network qualification.',
            'Local digest-pinned snapshots;no publisher signatures or channel update/authentication tested.',
            'Preview/refusal equality compares instance regular-file bytes,mode,mtime;not global caches,host logs,or every native attribute.',
            'Initial explicit0700state refusal and .empack archive-suffix fixture correction retained separately.']}, indent=2) + '\n')
    print(json.dumps({'run': str(run), 'commands': len(commands), 'releaseIds': [aid['release'], bid['release'], cid['release']]}, indent=2))


if __name__ == '__main__':
    main()
