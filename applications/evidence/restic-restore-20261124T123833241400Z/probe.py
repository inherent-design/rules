#!/usr/bin/env python3
"""Owner-run restore target fixtures; only generated files and a new repository."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import shutil
import signal
import stat
import subprocess
import time
from locks_probe import redact

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = Path(__file__).read_bytes()
STAMP = 1700000000000000000
FILES = {'alpha.txt': b'publisher alpha\n', 'options.txt': b'publisher options\n', 'sub/beta.txt': b'publisher beta\n'}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def image(root):
    values = {}
    for p in sorted(root.rglob('*')):
        s = p.lstat()
        value = dict(mode=stat.S_IMODE(s.st_mode), mtimeNs=s.st_mtime_ns)
        if p.is_symlink():
            value.update(kind='symlink', link=os.readlink(p))
        elif p.is_file():
            value.update(kind='file', bytes=s.st_size, sha256=sha(p))
        elif p.is_dir():
            value.update(kind='directory')
        else:
            raise AssertionError('Unexpected fixture node.')
        values[str(p.relative_to(root))] = value
    return values


def main():
    run = ROOT / 'applications/evidence' / ('restic-restore-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'
    for name in ['home', 'cache', 'tmp', 'private', 'source', 'targets']:
        (work / name).mkdir(parents=True)
    (run / 'probe.py').write_bytes(PRODUCER)
    (run / 'helper.py').write_bytes((HERE / 'locks_probe.py').read_bytes())
    password = work / 'password'
    password.write_text(secrets.token_urlsafe(32) + '\n')
    password.chmod(0o600)
    pin = json.loads((ROOT / 'applications/sources/local-pins.json').read_text())['tools']['restic']
    tool = Path(pin['path'])
    assert sha(tool) == pin['sha256']
    repo, source = work / 'repository', work / 'source'
    for name, data in FILES.items():
        p = source / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        p.chmod(0o640)
        os.utime(p, ns=(STAMP, STAMP))
    source_image = image(source)
    (run / 'source-image.json').write_text(json.dumps(source_image, indent=2) + '\n')
    prefix = [str(tool), '--repo', str(repo), '--password-file', str(password), '--json']
    env = dict(PATH='/usr/bin:/bin', HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'),
               RESTIC_CACHE_DIR=str(work / 'cache'), GOMAXPROCS='2', LANG='C.UTF-8')
    rows, owned = [], []

    def command(label, args, target=None, request=None):
        before = image(target) if target else None
        started = time.monotonic()
        with (work / 'private' / (label + '.stdout')).open('wb') as out, (work / 'private' / (label + '.stderr')).open('wb') as err:
            child = subprocess.Popen(prefix + args, cwd=source, env=env, stdin=subprocess.DEVNULL,
                                     stdout=out, stderr=err, start_new_session=True)
            owned.append(child)
            timed_out = False
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        streams = {}
        for stream in ['stdout', 'stderr']:
            raw_path = work / 'private' / (label + '.' + stream)
            raw = raw_path.read_bytes()
            public_path = run / (label + '.' + stream)
            public_path.write_bytes(redact(raw))
            streams[stream] = dict(rawSha256=sha(raw_path), publicSha256=sha(public_path),
                rawPrivatePath=str(raw_path.relative_to(run)), redacted=raw != public_path.read_bytes())
        row = dict(case=label, argv=prefix + args, pid=child.pid, seconds=time.monotonic() - started,
            request=request, observed=dict(before=before, after=image(target) if target else None, streams=streams),
            outcome=dict(exitCode=child.returncode, timedOut=timed_out))
        rows.append(row)
        (run / 'trace.json').write_text(json.dumps(rows, indent=2) + '\n')
        print(label, child.returncode, flush=True)
        assert not timed_out, 'Preserve this timeout before any retry.'
        return row

    try:
        assert command('help', ['restore', '--help'])['outcome']['exitCode'] == 0
        assert command('init', ['init', '--repository-version', '2'])['outcome']['exitCode'] == 0
        assert command('backup', ['backup', str(source), '--host', 'restore-fixture-host', '--tag', 'restore-policy'])['outcome']['exitCode'] == 0
        summary = [json.loads(line) for line in (work / 'private/backup.stdout').read_text().splitlines()]
        snapshot = next(r['snapshot_id'] for r in summary if r.get('message_type') == 'summary')
        selection = snapshot + ':' + str(source)
        cases = [
            ('empty-always', 'empty', 'always', ['--verify']),
            ('existing-never', 'same-mtime-changed-bytes', 'never', ['--verify']),
            ('same-metadata-if-changed', 'same-mtime-changed-bytes', 'if-changed', ['--verify']),
            ('same-metadata-always', 'same-mtime-changed-bytes', 'always', ['--verify']),
            ('older-if-newer', 'older-changed-bytes', 'if-newer', ['--verify']),
            ('newer-if-newer', 'newer-changed-bytes', 'if-newer', ['--verify']),
            ('equal-if-newer', 'same-mtime-changed-bytes', 'if-newer', ['--verify']),
            ('changed-mtime-if-changed', 'newer-changed-bytes', 'if-changed', ['--verify']),
            ('delete-extra', 'extra', 'always', ['--delete', '--verify']),
            ('delete-exclude-root-file', 'extra', 'always', ['--delete', '--exclude', '/extra.txt', '--verify']),
            ('delete-exclude-nested-file', 'extra', 'always', ['--delete', '--exclude', '/extra/protected.txt', '--verify']),
            ('delete-exclude-extra-directory', 'extra', 'always', ['--delete', '--exclude', '/extra', '--verify']),
            ('dry-delete-exclude-nested', 'extra', 'always', ['--delete', '--exclude', '/extra/protected.txt', '--dry-run', '-vv']),
            ('include-only-alpha', 'extra', 'always', ['--delete', '--include', '/alpha.txt', '--verify']),
            ('mutually-exclusive-filters', 'extra', 'always', ['--include', '/alpha.txt', '--exclude', '/options.txt']),
            ('mutually-exclusive-dry-verify', 'extra', 'always', ['--dry-run', '--verify']),
            ('symlink-owned-canary', 'symlink', 'always', ['--verify']),
        ]
        for label, setup, overwrite, flags in cases:
            target = work / 'targets' / label
            if setup == 'empty':
                target.mkdir()
            else:
                shutil.copytree(source, target)
            if setup.endswith('changed-bytes'):
                p = target / 'alpha.txt'
                p.write_bytes(b'X' * len(FILES['alpha.txt']))
                stamp = STAMP + (-1000000000 if setup.startswith('older') else 1000000000 if setup.startswith('newer') else 0)
                os.utime(p, ns=(stamp, stamp))
            if setup == 'extra':
                (target / 'extra').mkdir()
                for name in ['extra.txt', 'extra/protected.txt', 'extra/unselected.txt']:
                    (target / name).write_text('owned extra file\n')
            canary = work / 'canary.txt'
            if setup == 'symlink':
                canary.write_text('owned outside-target canary\n')
                (target / 'alpha.txt').unlink()
                (target / 'alpha.txt').symlink_to(canary)
                canary_before = sha(canary)
            row = command(label, ['restore', selection, '--target', str(target), '--overwrite', overwrite, *flags], target,
                          dict(setup=setup, overwrite=overwrite, flags=flags, snapshot=snapshot, subtree=str(source)))
            if setup == 'symlink':
                row['observed']['canary'] = dict(beforeSha256=canary_before, afterSha256=sha(canary))
                (run / 'trace.json').write_text(json.dumps(rows, indent=2) + '\n')
            if label == 'empty-always':
                assert row['outcome']['exitCode'] == 0
                assert all((target / name).read_bytes() == data for name, data in FILES.items()), 'Subtree restore precondition failed.'
        assert image(source) == source_image
        assert not list((repo / 'locks').glob('*'))
        receipt = dict(schema=1, tool=pin, platform=platform.platform(), architecture=platform.machine(),
            producerSha256=hashlib.sha256(PRODUCER).hexdigest(), helperSha256=sha(run / 'helper.py'), snapshot=snapshot,
            commands=len(rows), allOwnedProcessesRetired=all(p.poll() is not None for p in owned), finalLocks=[],
            sourceUnchanged=True, sourceImageSha256=sha(run / 'source-image.json'),
            scope='One generated three-file snapshot/subtree; private repository/cache/HOME and distinct fresh target per restore. Size/mtime tampering is an explicit fixture control, not arbitrary corruption. Exclusions and deletion operate only on owned targets. No real backup, user files, remote service or production mutation.')
        (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    finally:
        for child in owned:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        print('capture', run, flush=True)


if __name__ == '__main__':
    main()
