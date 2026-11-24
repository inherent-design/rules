#!/usr/bin/env python3
"""Owner-run backup capture: new repository and generated files only."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import signal
import stat
import subprocess
import time
from locks_probe import redact

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = Path(__file__).read_bytes()
STAMP = 1700000000000000000
ORIGINAL = b"original bytes\n"
CHANGED = b"modified bytes\n"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def image(root):
    result = {}
    for p in sorted(root.iterdir()):
        s = p.lstat()
        assert stat.S_ISREG(s.st_mode)
        row = dict(bytes=s.st_size, mode=stat.S_IMODE(s.st_mode), mtimeNs=s.st_mtime_ns,
                   ctimeNs=s.st_ctime_ns, inode=s.st_ino)
        if row['mode'] & 0o400:
            row['sha256'] = sha(p)
        else:
            row['sha256'] = None
        result[p.name] = row
    return result


def main():
    run = ROOT / 'applications/evidence' / ('restic-backup-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'
    for name in ['home', 'cache', 'tmp', 'private', 'source']:
        (work / name).mkdir(parents=True)
    (run / 'probe.py').write_bytes(PRODUCER)
    (run / 'helper.py').write_bytes((HERE / 'locks_probe.py').read_bytes())
    pin = json.loads((ROOT / 'applications/sources/local-pins.json').read_text())['tools']['restic']
    tool = Path(pin['path'])
    assert sha(tool) == pin['sha256']
    password = work / 'password'
    password.write_text(secrets.token_urlsafe(32) + '\n')
    password.chmod(0o600)
    repo, source = work / 'repository', work / 'source'
    mainfile = source / 'main.txt'
    mainfile.write_bytes(ORIGINAL)
    mainfile.chmod(0o640)
    os.utime(mainfile, ns=(STAMP, STAMP))
    env = dict(PATH='/usr/bin:/bin', HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'),
               RESTIC_CACHE_DIR=str(work / 'cache'), GOMAXPROCS='2', LANG='C.UTF-8')
    prefix = [str(tool), '--repo', str(repo), '--password-file', str(password), '--json']
    rows, observations, owned = [], [], []

    def snapshots():
        return sorted(p.name for p in (repo / 'snapshots').glob('*') if p.is_file())

    def command(label, args):
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
            public_path = run / (label + '.' + stream)
            public_path.write_bytes(redact(raw_path.read_bytes()))
            streams[stream] = dict(rawSha256=sha(raw_path), publicSha256=sha(public_path),
                                  rawPrivatePath=str(raw_path.relative_to(run)))
        rows.append(dict(case=label, argv=prefix + args, pid=child.pid, seconds=time.monotonic() - started,
                         streams=streams, outcome=dict(exitCode=child.returncode, timedOut=timed_out)))
        (run / 'trace.json').write_text(json.dumps(rows, indent=2) + '\n')
        print(label, child.returncode, flush=True)
        assert not timed_out, 'Preserve timeout before any retry.'
        return child.returncode

    def json_lines(label):
        return [json.loads(line) for line in (work / 'private' / (label + '.stdout')).read_text().splitlines()]

    def backup(label, flags=(), parent=None, expected=0, target='.'):
        before, source_before = snapshots(), image(source)
        args = ['backup', target, '--host', 'backup-fixture-host'] + list(flags)
        if parent is not None:
            args += ['--parent', parent]
        code = command(label, args)
        after, source_after = snapshots(), image(source)
        assert source_before == source_after, 'Backup changed measured source bytes or metadata.'
        events = json_lines(label)
        summary = next((r for r in events if r.get('message_type') == 'summary'), None)
        new = sorted(set(after) - set(before))
        assert set(before) <= set(after)
        row = dict(case=label, request=dict(flags=list(flags), parent=parent, target=target),
                   sourceBefore=source_before, sourceAfter=source_after, snapshotIdsBefore=before,
                   snapshotIdsAfter=after, newSnapshots=new, summary=summary, exitCode=code)
        if new:
            assert len(new) == 1 and summary is not None and summary['snapshot_id'] == new[0]
            assert command(label + '-ls', ['ls', new[0]]) == 0
            nodes = json_lines(label + '-ls')
            row['nodes'] = nodes
            main_path = next(n['path'] for n in nodes if n.get('type') == 'file' and n.get('name') == 'main.txt')
            assert command(label + '-dump', ['dump', new[0], main_path]) == 0
            row['mainBytesHex'] = (work / 'private' / (label + '-dump.stdout')).read_bytes().hex()
        observations.append(row)
        (run / 'observations.json').write_text(json.dumps(observations, indent=2) + '\n')
        assert code == expected, (label, code, expected)
        return new[0] if new else None

    try:
        assert command('help', ['backup', '--help']) == 0
        assert command('init', ['init', '--repository-version', '2']) == 0
        baseline = backup('baseline')
        assert baseline
        baseline_image = image(source)
        backup('unchanged', parent=baseline)
        mainfile.write_bytes(CHANGED)
        os.utime(mainfile, ns=(STAMP, STAMP))
        assert image(source)['main.txt']['ctimeNs'] != baseline_image['main.txt']['ctimeNs']
        assert image(source)['main.txt']['inode'] == baseline_image['main.txt']['inode']
        backup('changed-default', parent=baseline)
        backup('changed-ignore-ctime', ['--ignore-ctime'], parent=baseline)
        backup('changed-forced', ['--force', '--ignore-ctime'], parent=baseline)
        replacement = source / 'replacement'
        replacement.write_bytes(CHANGED)
        replacement.chmod(0o640)
        os.utime(replacement, ns=(STAMP, STAMP))
        os.replace(replacement, mainfile)
        assert image(source)['main.txt']['inode'] != baseline_image['main.txt']['inode']
        backup('replacement-ignore-ctime', ['--ignore-ctime'], parent=baseline)
        backup('replacement-ignore-inode', ['--ignore-inode'], parent=baseline)
        os.utime(mainfile, ns=(STAMP + 1000000000, STAMP + 1000000000))
        backup('new-mtime-ignore-inode', ['--ignore-inode'], parent=baseline)
        bad = source / 'unreadable.txt'
        bad.write_bytes(b'generated unreadable payload\n')
        bad.chmod(0)
        try:
            bad.read_bytes()
        except PermissionError:
            pass
        else:
            raise AssertionError('This host does not enforce the intended unreadable-file control.')
        backup('partial-unreadable', parent=baseline, expected=3)
        backup('excluded-unreadable', ['--exclude', 'unreadable.txt'], parent=baseline)
        bad.chmod(0o600)
        bad.unlink()
        backup('dry-run-forced', ['--force', '--dry-run'], parent=baseline)
        new_parent = backup('new-baseline', ['--force'])
        backup('skip-unchanged', ['--skip-if-unchanged'], parent=new_parent)
        backup('missing-root', expected=1, target='absent-root')
        assert not list((repo / 'locks').glob('*'))
        receipt = dict(schema=1, tool=pin, platform=platform.platform(), architecture=platform.machine(),
                       producerSha256=hashlib.sha256(PRODUCER).hexdigest(), helperSha256=sha(run / 'helper.py'),
                       commands=len(rows), backupCases=len(observations), finalLocks=[],
                       allOwnedProcessesRetired=all(p.poll() is not None for p in owned),
                       sourceScope='Generated main.txt; only the producer makes controlled equal-size/mtime edits, inode replacement, and temporary unreadable-file changes. No existing repository or user file opened.',
                       limits=['Source reads inferred from original versus modified snapshot content and source control, not syscall counts.',
                               'One local macOS regular-file profile; no remote backend, live filesystem race, chunking proof, permissions/metadata portability, or crash recovery.'])
        (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    finally:
        if (source / 'unreadable.txt').exists():
            (source / 'unreadable.txt').chmod(0o600)
        for child in owned:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        print('capture', run, flush=True)


if __name__ == '__main__':
    main()
