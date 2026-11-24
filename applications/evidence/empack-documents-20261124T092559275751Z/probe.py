#!/usr/bin/env python3
"""Private installed-CLI document/approval study; no user project or game.

Each run owns a new root/state/cache and private controlling PTY. Mutations occur
only after observing the real confirmation prompt. Never rerun a failed capture
as if its partial effects were absent.
"""
from datetime import datetime, timezone
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import select
import shutil
import signal
import stat
import struct
import subprocess
import termios
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = Path(__file__).read_bytes()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
DOCUMENTS = ['empack.yml', 'empack.bindings.yml', 'empack.lock']


def image(root, names=DOCUMENTS):
    result = {}
    for name in names:
        p = root / name
        if not p.exists():
            result[name] = None
            continue
        s = p.lstat(); assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
        result[name] = dict(sha256=sha(p), bytes=s.st_size, mode=stat.S_IMODE(s.st_mode),
                            inode=str(s.st_ino), mtimeNs=str(s.st_mtime_ns))
    return result


def main():
    source = ROOT / 'applications/evidence/empack-native-ownership-20261124T031930881554Z'
    setup = json.loads((source / 'setup.json').read_text())
    program = Path(setup['binary'])
    assert sha(program) == setup['binarySha256'] == '99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
    original = source / 'work/parent/project'
    source_names = DOCUMENTS + ['pack/config/rules.txt', 'pack/payload.txt']
    original_image = image(original, source_names)
    run = ROOT / 'applications/evidence' / ('empack-documents-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'; project = work / 'project'
    for name in ['project/pack/config', 'home', 'tmp', 'config']:
        (work / name).mkdir(parents=True)
    for name in source_names:
        if original_image[name] is not None:
            shutil.copyfile(original / name, project / name)
            assert (original / name).stat().st_ino != (project / name).stat().st_ino
    (run / 'probe.py').write_bytes(PRODUCER)
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(work / 'home'), 'TMPDIR': str(work / 'tmp'),
           'XDG_CONFIG_HOME': str(work / 'config'), 'LANG': 'en_US.UTF-8', 'TERM': 'xterm-256color'}
    base = [str(program), '--state-dir', str(work / 'state'), '--cache-dir', str(work / 'cache'),
            '--workdir', str(project), '--color', 'never']
    rows, edits = [], []

    def save():
        (run / 'commands.json').write_text(json.dumps(rows, indent=2) + '\n')
        (run / 'edits.json').write_text(json.dumps(edits, indent=2) + '\n')

    def mutate(label, name, data):
        before = image(project)
        path = project / name
        if data is None:
            path.unlink()
        else:
            path.write_bytes(data)
        after = image(project)
        edits.append(dict(case=label, path=name, before=before, after=after))
        save()

    def record(label, argv, before, started, code, out, err, extra=None):
        (run / (label + '.stdout')).write_bytes(out); (run / (label + '.stderr')).write_bytes(err)
        row = dict(case=label, argv=argv, exitCode=code, seconds=time.monotonic() - started,
                   before=before, after=image(project), stdoutSha256=sha(run / (label + '.stdout')),
                   stderrSha256=sha(run / (label + '.stderr')), control=extra or {})
        rows.append(row); save(); print(json.dumps({'case': label, 'exitCode': code}), flush=True)
        return row

    def command(label, args, expected=0):
        before, began = image(project), time.monotonic()
        argv = base + ['--yes'] + args
        child = subprocess.Popen(argv, cwd=work, env=env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            out, err = child.communicate(timeout=30)
        except BaseException:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
            child.communicate(); raise
        row = record(label, argv, before, began, child.returncode, out, err)
        assert child.returncode == expected, 'Unexpected status; preserve this capture before retry.'
        return row

    def inspect(label):
        command(label, ['manifest', 'diff', '--json'])
        report = json.loads((run / (label + '.stdout')).read_text())
        assert report['schema'] == 1
        return report

    def prompted(label, edit, answer=b'y'):
        before, began = image(project), time.monotonic()
        argv = base + ['sync']
        pid, master = pty.fork()
        if pid == 0:
            os.chdir(work)
            os.execve(program, argv, env)
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 120, 0, 0))
        data, status, prompt_seen, after_edit = bytearray(), None, False, None
        marker = b'Apply this synchronization plan?'
        deadline = began + 30
        try:
            while time.monotonic() < deadline:
                ready, _, _ = select.select([master], [], [], .05)
                if ready:
                    try:
                        chunk = os.read(master, 65536)
                    except OSError as error:
                        if error.errno != errno.EIO:
                            raise
                        chunk = b''
                    data.extend(chunk)
                if not prompt_seen and marker in data:
                    observed_pid, _ = os.waitpid(pid, os.WNOHANG)
                    assert observed_pid == 0, 'Prompt observation must occur while process remains live.'
                    prompt_seen = True
                    edit()
                    after_edit = image(project)
                    os.write(master, answer)
                observed_pid, observed_status = os.waitpid(pid, os.WNOHANG)
                if observed_pid:
                    status = observed_status
                    # Drain buffered output after actual retirement.
                    while select.select([master], [], [], 0)[0]:
                        try:
                            chunk = os.read(master, 65536)
                        except OSError as error:
                            if error.errno != errno.EIO:
                                raise
                            break
                        if not chunk:
                            break
                        data.extend(chunk)
                    break
            if status is None:
                raise RuntimeError('Private approval fixture exceeded deadline; preserve partial state.')
        finally:
            if status is None:
                try:
                    os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                os.waitpid(pid, 0)
            os.close(master)
        code = os.waitstatus_to_exitcode(status)
        row = record(label, argv, before, began, code, bytes(data), b'',
                     dict(privateControllingPTY=True, mergedOutput=True, promptMarkerObservedLive=prompt_seen,
                          marker=marker.decode(), answer=answer.decode(), afterExplicitEdit=after_edit))
        assert prompt_seen and after_edit is not None
        assert row['after'] == after_edit, 'A stale/declined approval must preserve the explicit edited state.'
        return row

    author = project / 'empack.yml'; bindings = project / 'empack.bindings.yml'; lock = project / 'empack.lock'
    try:
        assert inspect('baseline')['lock_status'] == 'current'
        command('baseline-sync', ['sync'])
        mutate('author-comment', 'empack.yml', b'# Preserved author comment.\n' + author.read_bytes())
        assert inspect('author-comment-current')['lock_status'] == 'current'
        command('comment-sync', ['sync'])
        mutate('binding-comment', 'empack.bindings.yml', b'# Preserved binding comment.\n' + bindings.read_bytes())
        assert inspect('binding-comment-current')['lock_status'] == 'current'
        command('binding-comment-sync', ['sync'])
        mutate('remove-policy-binding', 'empack.bindings.yml', None)
        assert inspect('removed-policy-stale')['lock_status'] == 'stale'
        command('sync-without-bindings', ['sync'])
        assert inspect('absent-bindings-current')['lock_status'] == 'current'
        mutate('create-empty-bindings', 'empack.bindings.yml', b'schema: 1\nbindings: {}\n')
        assert inspect('empty-bindings-current')['lock_status'] == 'current'
        command('empty-bindings-sync', ['sync'])
        # Each pending metadata edit requires a new lock write. Races at a
        # no-op plan alone would not establish publication refusal.
        for number, race in enumerate(['author', 'lock', 'binding-absence'], 1):
            if race == 'binding-absence':
                mutate('remove-empty-bindings', 'empack.bindings.yml', None)
            previous = author.read_bytes()
            name_line = next(line for line in previous.splitlines() if line.strip().startswith(b'name:'))
            replacement = name_line[:len(name_line) - len(name_line.lstrip())] + b'name: Prepared document fixture ' + str(number).encode()
            mutate('new-name-' + race, 'empack.yml', previous.replace(name_line, replacement, 1))
            assert inspect('before-race-' + race)['lock_status'] == 'stale'
            if race == 'author':
                edit = lambda: mutate('during-author-prompt', 'empack.yml', author.read_bytes() + b'# Later author comment.\n')
            elif race == 'lock':
                edit = lambda: mutate('during-lock-prompt', 'empack.lock', lock.read_bytes() + b'# Later lock comment.\n')
            else:
                edit = lambda: mutate('during-binding-prompt', 'empack.bindings.yml', b'# Later empty binding.\nschema: 1\nbindings: {}\n')
            row = prompted('race-' + race, edit)
            assert row['exitCode'] != 0, 'Observed successful stale publication requires investigation, not a rewritten expectation.'
            assert inspect('after-race-' + race)['lock_status'] == 'stale'
            command('fresh-sync-' + race, ['sync'])
            assert inspect('fresh-current-' + race)['lock_status'] == 'current'
        valid = author.read_bytes()
        mutate('unsupported-schema', 'empack.yml', valid.replace(b'schema: 6', b'schema: 999', 1))
        command('unsupported-schema-refused', ['manifest', 'diff', '--json'], expected=1)
        mutate('restore-valid-author', 'empack.yml', valid)
        assert inspect('restored-valid-current')['lock_status'] == 'current'
        assert image(original, source_names) == original_image
        assert sha(program) == setup['binarySha256']
        receipt = dict(schema=1, producerSha256=hashlib.sha256(PRODUCER).hexdigest(), binary=str(program),
                       binarySha256=sha(program), sourceCapture=str(source.relative_to(ROOT)), sourceImage=original_image,
                       sourceUnchanged=True, commands=len(rows), allOwnedProcessesRetired=True,
                       finalDocuments=image(project), allocatedKiB=int(subprocess.check_output(['du', '-sk', str(work)], text=True).split()[0]),
                       scope='Installed0.8.8binary,private existing no-dependency author root andfresh state. Semantic observations are manifest lock-status/lock revision under fixed runtime. Raw preconditions use actual three prompt-race refusals. No wrong-grant/wrong-engine public API execution,provider changes,root replacement,crash/recovery,game orglobal cache-effect qualification.')
        (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'run': str(run), 'commands': len(rows), 'allocatedKiB': receipt['allocatedKiB']}, indent=2))
    except BaseException as error:
        (run / 'failure.json').write_text(json.dumps({'error': str(error), 'commands': len(rows),
            'sourceUnchanged': image(original, source_names) == original_image}) + '\n')
        raise


if __name__ == '__main__':
    main()
