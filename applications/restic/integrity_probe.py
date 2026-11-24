#!/usr/bin/env python3
"""Inject one body fault and one missing-index fault in a new private copy.

The completed source capture is never opened by restic. Preserve raw streams,
pristine bytes, and the encrypted repository under ignored work, even on failure.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import pwd
import shutil
import signal
import socket
import stat
import subprocess
import time
from locks_probe import redact

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = Path(__file__).read_bytes()
PAYLOAD = b'Completed held A input.\n'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image(root):
    return {p.relative_to(root).as_posix(): {'sha256': sha(p), 'bytes': p.stat().st_size}
            for p in sorted(root.rglob('*')) if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_capture', type=Path)
    source = parser.parse_args().source_capture.resolve()
    assert source.is_relative_to(ROOT / 'applications/evidence')
    source_receipt = json.loads((source / 'receipt.json').read_text())
    assert source_receipt['allOwnedProcessesRetired'] and not source_receipt['finalLocks']
    original = source / 'work/repository'
    original_image = image(original)
    assert original_image and not any(p.startswith('locks/') for p in original_image)
    run = ROOT / 'applications/evidence' / ('restic-integrity-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'
    for name in ['home', 'cache', 'tmp', 'private', 'private/pristine-index']:
        (work / name).mkdir(parents=True)
    repo = work / 'repository'
    shutil.copytree(original, repo)
    shutil.copyfile(source / 'work/password', work / 'password')
    (work / 'password').chmod(0o600)
    assert image(repo) == original_image
    for name in original_image:
        assert (repo / name).stat().st_ino != (original / name).stat().st_ino
        assert (repo / name).stat().st_nlink == 1
    (run / 'probe.py').write_bytes(PRODUCER)
    (run / 'helper.py').write_bytes((HERE / 'locks_probe.py').read_bytes())
    (work / 'private/redaction-inputs.json').write_text(json.dumps({
        'hostname': socket.gethostname(), 'username': pwd.getpwuid(os.getuid()).pw_name}) + '\n')
    tool = ROOT / 'applications/tools/restic-0.20.0/restic'
    assert sha(tool) == source_receipt['tool']['binarySha256']
    base = [str(tool), '--repo', str(repo), '--password-file', str(work / 'password')]
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(work / 'home'), 'TMPDIR': str(work / 'tmp'),
           'RESTIC_CACHE_DIR': str(work / 'cache'), 'GOMAXPROCS': '2', 'LANG': 'C.UTF-8'}
    rows, owned, controls = [], [], []

    def command(label, args, expected=None):
        before, started = image(repo), time.monotonic()
        with (work / 'private' / (label + '.stdout')).open('wb') as out, (work / 'private' / (label + '.stderr')).open('wb') as err:
            child = subprocess.Popen(base + args, cwd=work, env=env, stdin=subprocess.DEVNULL,
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
            public = redact(raw)
            public_path = run / (label + '.' + stream)
            public_path.write_bytes(public)
            streams[stream] = {'rawPrivatePath': str(raw_path.relative_to(run)), 'rawSha256': sha(raw_path),
                               'publicSha256': sha(public_path), 'redacted': raw != public}
        row = {'case': label, 'argv': base + args, 'pid': child.pid, 'seconds': time.monotonic() - started,
               'exitCode': child.returncode, 'timedOut': timed_out, 'streams': streams,
               'beforeImage': before, 'afterImage': image(repo)}
        rows.append(row)
        (run / 'trace.json').write_text(json.dumps(rows, indent=2) + '\n')
        print(json.dumps({'case': label, 'exitCode': child.returncode}), flush=True)
        assert not timed_out, 'Preserve the timed-out operation; do not infer completion.'
        if expected is not None:
            assert child.returncode == expected, 'Unexpected status; retain the observed result.'
        return row

    def dump(label):
        return command(label, ['dump', source_receipt['completedASnapshot'], '/held-a.txt'])

    def save_controls():
        (run / 'controls.json').write_text(json.dumps(controls, indent=2) + '\n')

    try:
        command('baseline-structure', ['check'], 0)
        command('baseline-read-all', ['check', '--read-data'], 0)
        assert dump('baseline-dump')['exitCode'] == 0
        assert (work / 'private/baseline-dump.stdout').read_bytes() == PAYLOAD
        candidates = []
        blob_id = hashlib.sha256(PAYLOAD).hexdigest()
        for i, path in enumerate(sorted((repo / 'index').iterdir())):
            command('index-' + str(i), ['cat', 'index', path.name], 0)
            index = json.loads((work / 'private' / ('index-' + str(i) + '.stdout')).read_text())
            for pack in index['packs']:
                for blob in pack['blobs']:
                    if blob['type'] == 'data' and blob['id'] == blob_id:
                        candidates.append((pack, blob))
        assert len(candidates) == 1, 'The fixture must identify exactly one actual content blob.'
        pack, blob = candidates[0]
        target = repo / 'data' / pack['id'][:2] / pack['id']
        pristine = target.read_bytes()
        assert sha(target) == pack['id'] and blob['length'] > 32
        offset = blob['offset'] + blob['length'] // 2
        assert blob['offset'] <= offset < blob['offset'] + blob['length'] <= len(pristine)
        (work / 'private/pristine-pack').write_bytes(pristine)
        damaged = bytearray(pristine)
        damaged[offset] ^= 1
        target_mode = stat.S_IMODE(target.stat().st_mode)
        target.chmod(target_mode | stat.S_IWUSR)
        try:
            target.write_bytes(damaged)
        finally:
            target.chmod(target_mode)
        controls.append({'kind': 'body-byte-flip', 'path': str(target.relative_to(repo)),
                         'blob': blob, 'byteOffset': offset, 'xor': 1, 'bytes': len(pristine),
                         'beforeSha256': pack['id'], 'afterSha256': sha(target), 'preservedMode': target_mode,
                         'source': 'One exact known data blob from native cat index, not an assumed pack offset.'})
        save_controls()
        command('damaged-structure', ['check'])
        command('damaged-read-all', ['check', '--read-data'])
        command('damaged-subset-1', ['check', '--read-data-subset', '1/2'])
        command('damaged-subset-2', ['check', '--read-data-subset', '2/2'])
        dump('damaged-dump')
        command('damaged-repair-index', ['repair', 'index', '--read-all-packs'])
        command('after-repair-structure', ['check'])
        command('after-repair-read-all', ['check', '--read-data'])
        dump('after-repair-dump')
        assert sha(target) == controls[0]['afterSha256'], 'Index repair must not be assumed to restore payload.'
        target.chmod(target_mode | stat.S_IWUSR)
        try:
            target.write_bytes(pristine)
        finally:
            target.chmod(target_mode)
        controls.append({'kind': 'external-known-good-byte-restoration', 'path': str(target.relative_to(repo)),
                         'sha256': sha(target), 'notResticRecovery': True})
        save_controls()
        command('restored-read-all', ['check', '--read-data'], 0)
        assert dump('restored-dump')['exitCode'] == 0
        assert (work / 'private/restored-dump.stdout').read_bytes() == PAYLOAD
        index_image = image(repo / 'index')
        assert index_image
        for name in index_image:
            path = repo / 'index' / name
            shutil.copyfile(path, work / 'private/pristine-index' / name)
            path.unlink()
        controls.append({'kind': 'remove-clone-index-only', 'removedImage': index_image})
        save_controls()
        command('missing-index-structure', ['check'])
        command('missing-index-repair', ['repair', 'index', '--read-all-packs'], 0)
        command('rebuilt-index-read-all', ['check', '--read-data'], 0)
        assert dump('rebuilt-index-dump')['exitCode'] == 0
        assert (work / 'private/rebuilt-index-dump.stdout').read_bytes() == PAYLOAD
        assert image(original) == original_image
        final_image = image(repo)
        assert {k: v for k, v in final_image.items() if k.startswith('snapshots/')} == {
            k: v for k, v in original_image.items() if k.startswith('snapshots/')}
        assert not any(k.startswith('locks/') for k in final_image)
        receipt = {'schema': 1, 'producerSha256': hashlib.sha256(PRODUCER).hexdigest(),
                   'helperSha256': sha(run / 'helper.py'), 'sourceCapture': str(source.relative_to(ROOT)),
                   'sourceReceiptSha256': sha(source / 'receipt.json'), 'tool': source_receipt['tool'],
                   'platform': platform.platform(), 'sourceRepositoryImage': original_image,
                   'sourceRepoUnchanged': True, 'copyBytesVerified': True, 'copyDistinctInodes': True,
                   'expectedPayloadSha256': blob_id, 'expectedPayloadBytes': len(PAYLOAD),
                   'finalImage': final_image, 'snapshotsUnchanged': True, 'commands': len(rows),
                   'allOwnedProcessesRetired': all(c.poll() is not None for c in owned),
                   'allocatedKiB': int(subprocess.check_output(['du', '-sk', str(work)], text=True).split()[0]),
                   'cacheProfile': 'Default check temporary cache; no --with-cache or --no-cache. Other commands use private normal cache.',
                   'scope': 'One same-size data-body bit flip, deterministic half subsets, index rebuild, external pristine-byte restore, then lost-index rebuild. No repair snapshots/forget, remote failures or general restore qualification.'}
        (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'run': str(run), 'commands': len(rows), 'allocatedKiB': receipt['allocatedKiB']}), flush=True)
    except BaseException as error:
        (run / 'failure.json').write_text(json.dumps({'error': str(error), 'commands': len(rows),
            'sourceRepoUnchanged': image(original) == original_image}) + '\n')
        raise
    finally:
        for child in owned:
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()


if __name__ == '__main__':
    main()
