#!/usr/bin/env python3
"""Small local restic lifecycle. Owns only its newly created disposable repository.

No remote backend, user repository, or personal data is used. Password/key files
stay in ignored work; public observations contain no password or decrypted key.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import time

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pack_state(repository):
    return {p.relative_to(repository).as_posix(): {'bytes': p.stat().st_size,
             'allocatedBytes': p.stat().st_blocks * 512, 'sha256': sha(p)}
            for p in sorted((repository / 'data').rglob('*')) if p.is_file()}


def main():
    run = ROOT / 'evidence' / ('restic-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'
    source, repository = work / 'source', work / 'repository'
    for p in (source, work / 'home', work / 'cache', work / 'tmp'):
        p.mkdir(parents=True)
    password = work / 'password'
    password.write_text(secrets.token_urlsafe(32) + '\n')
    password.chmod(0o600)
    executable = ROOT / 'tools/restic-0.20.0/restic'
    pin = json.loads((ROOT / 'sources/restic-tool.json').read_text())
    assert sha(executable) == pin['binarySha256']
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(work / 'home'),
           'TMPDIR': str(work / 'tmp'), 'RESTIC_CACHE_DIR': str(work / 'cache'),
           'GOMAXPROCS': '2', 'LANG': 'C.UTF-8'}
    prefix = [str(executable), '--repo', str(repository), '--password-file', str(password), '--json']
    rows = []

    def run_command(label, feature, args, expected_exit=0):
        before = pack_state(repository) if repository.exists() else {}
        start = time.monotonic()
        result = subprocess.run(prefix + args, cwd=work, env=env, capture_output=True, timeout=60)
        after = pack_state(repository) if repository.exists() else {}
        (run / (label + '.stdout')).write_bytes(result.stdout)
        (run / (label + '.stderr')).write_bytes(result.stderr)
        row = {'v': 2, 'app': 'restic', 'feature': feature, 'operationId': str(len(rows)) + '-' + label,
               'profile': 'restic-0.20.0-darwin-arm64-local-repository', 'target': str(repository),
               'basis': str(len(rows)), 'request': {'argv': prefix + args},
               'observed': {'beforePacks': before, 'afterPacks': after, 'seconds': time.monotonic() - start,
                            'stdoutSha256': hashlib.sha256(result.stdout).hexdigest(),
                            'stderrSha256': hashlib.sha256(result.stderr).hexdigest()},
               'outcome': {'exitCode': result.returncode},
               'interpretation': {'status': 'native-observed', 'model': None, 'expectedExit': expected_exit,
                                  'hostMapping': 'Domain trace; not admitted as a shared host predicate until explicitly mapped.'}}
        rows.append(row)
        (run / 'trace.json').write_text(json.dumps(rows, indent=2) + '\n')
        assert result.returncode == expected_exit, (label, result.stderr.decode(errors='replace'))
        return result.stdout

    def snapshots(label):
        return json.loads(run_command(label, 'restic.snapshot-selection', ['snapshots']))

    run_command('init', 'restic.repository', ['init'])
    config = json.loads(run_command('config', 'restic.repository', ['cat', 'config']))
    (source / 'shared.txt').write_bytes(b'shared payload\n' * 256)
    (source / 'changed.txt').write_bytes(b'old payload\n' * 512)
    old_content = {p.name: sha(p) for p in source.iterdir()}
    run_command('backup-a', 'restic.backup', ['backup', '--host', 'rules-fixture', '--tag', 'fixture', str(source)])
    first = snapshots('snapshots-a')[0]['id']
    (source / 'changed.txt').write_bytes(b'new, longer payload\n' * 512)
    new_content = {p.name: sha(p) for p in source.iterdir()}
    run_command('backup-b', 'restic.backup', ['backup', '--host', 'rules-fixture', '--tag', 'fixture', str(source)])
    both = snapshots('snapshots-b')
    assert len(both) == 2
    second = next(s['id'] for s in both if s['id'] != first)
    meta = json.loads(run_command('snapshot-b', 'restic.snapshot-selection', ['cat', 'snapshot', second]))
    for label, identity in [('old', old_content['changed.txt']), ('shared', new_content['shared.txt']), ('new', new_content['changed.txt'])]:
        payload = run_command(label + '-blob-before', 'restic.backup', ['cat', 'blob', identity])
        assert hashlib.sha256(payload).hexdigest() == identity
    initial_packs = pack_state(repository)
    run_command('forget-preview', 'restic.retention', ['forget', first, '--dry-run'])
    assert {s['id'] for s in snapshots('snapshots-after-preview')} == {first, second}
    assert pack_state(repository) == initial_packs
    run_command('forget-a', 'restic.retention', ['forget', first])
    assert {s['id'] for s in snapshots('snapshots-after-forget')} == {second}
    assert pack_state(repository) == initial_packs
    run_command('prune', 'restic.prune', ['prune', '--max-unused', '0'])
    pruned_packs = pack_state(repository)
    run_command('old-blob-after', 'restic.prune', ['cat', 'blob', old_content['changed.txt']], expected_exit=1)
    old_error = (run / 'old-blob-after.stderr').read_text()
    assert 'blob not found' in old_error
    for label, identity in [('shared', new_content['shared.txt']), ('new', new_content['changed.txt'])]:
        payload = run_command(label + '-blob-after', 'restic.prune', ['cat', 'blob', identity])
        assert hashlib.sha256(payload).hexdigest() == identity
    run_command('check-read-data', 'restic.integrity', ['check', '--read-data'])
    target = work / 'restored'
    run_command('restore-b', 'restic.restore', ['restore', second, '--target', str(target)])
    restored = target / source.as_posix().lstrip('/')
    actual = {p.name: sha(p) for p in restored.iterdir() if p.is_file()}
    assert actual == new_content
    assert {p.name: sha(p) for p in source.iterdir()} == new_content
    findings = {'v': 1, 'repositoryId': config['id'], 'repositoryFormat': config['version'],
                'snapshotA': first, 'snapshotB': second, 'snapshotBParent': meta.get('parent'),
                'parentIsForgottenSnapshot': meta.get('parent') == first,
                'forgetRemovedReferenceButKeptExactPackBytes': True,
                'beforePrunePacks': len(initial_packs), 'afterPrunePacks': len(pruned_packs),
                'beforePruneAllocatedPackBytes': sum(p['allocatedBytes'] for p in initial_packs.values()),
                'afterPruneAllocatedPackBytes': sum(p['allocatedBytes'] for p in pruned_packs.values()),
                'expectedNewContent': new_content, 'restoredContent': actual,
                'oldContent': old_content, 'allExpectedOutcomes': True,
                'oldBlobAvailableBeforeAndMissingAfterPrune': True,
                'sharedAndNewBlobAvailableBeforeAndAfterPrune': True,
                'limits': ['Small local repository; no concurrent writer, partial backup, corruption, key rotation, or remote backend test.',
                           'Pack allocated bytes are sampled filesystem metadata, not a whole-volume free-space claim.',
                           'A native observation does not establish the reachability proof or all retention policies.']}
    (run / 'findings.json').write_text(json.dumps(findings, indent=2) + '\n')
    (run / 'receipt.json').write_text(json.dumps({'v': 2, 'entrypointSha256': sha(Path(__file__)),
                     'tool': pin, 'requests': len(rows), 'findings': 'findings.json',
                     'protection': 'Generated password and encrypted repository remain in ignored work; no key/password exported.'}, indent=2) + '\n')
    print(json.dumps({'run': str(run), **findings}, indent=2))


if __name__ == '__main__':
    main()
