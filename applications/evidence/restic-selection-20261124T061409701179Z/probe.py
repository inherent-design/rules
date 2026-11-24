#!/usr/bin/env python3
"""Owner-run snapshot selection/retention previews in one private local repository."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = Path(__file__).read_bytes()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    executable = ROOT / 'applications/tools/restic-0.20.0/restic'
    pin = json.loads((ROOT / 'applications/sources/restic-tool.json').read_text())
    assert sha(executable) == pin['binarySha256']
    run = ROOT / 'applications/evidence' / ('restic-selection-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir(); (run / 'probe.py').write_bytes(PRODUCER)
    work = run / 'work'; repository = work / 'repository'
    for path in [work / 'home', work / 'cache', work / 'tmp', work / 'source-a', work / 'source-b']: path.mkdir(parents=True)
    password = work / 'password'; password.write_text(secrets.token_urlsafe(32) + '\n'); password.chmod(0o600)
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(work / 'home'), 'TMPDIR': str(work / 'tmp'),
        'RESTIC_CACHE_DIR': str(work / 'cache'), 'LANG': 'C.UTF-8', 'TZ': 'UTC', 'GOMAXPROCS': '2'}
    prefix = [str(executable), '--repo', str(repository), '--password-file', str(password), '--json']
    rows, definitions = [], []
    def state():
        return {kind: {p.relative_to(repository).as_posix(): sha(p) for p in sorted((repository / directory).rglob('*')) if p.is_file()}
            for kind, directory in [('snapshotRefs', 'snapshots'), ('packs', 'data')]}
    def command(label, args):
        before = state(); began = time.monotonic()
        child = subprocess.Popen(prefix + args, cwd=work, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timeout = False
        try: out, err = child.communicate(input=b'', timeout=60)
        except subprocess.TimeoutExpired:
            timeout = True
            try: os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            out, err = child.communicate()
        (run / (label + '.stdout')).write_bytes(out); (run / (label + '.stderr')).write_bytes(err)
        row = {'app': 'restic', 'operation': label, 'argv': prefix + args,
            'observed': {'before': before, 'after': state(), 'seconds': time.monotonic() - began,
                'stdoutSha256': hashlib.sha256(out).hexdigest(), 'stderrSha256': hashlib.sha256(err).hexdigest()},
            'outcome': {'exitCode': child.returncode, 'timedOut': timeout}}
        rows.append(row); (run / 'trace.json').write_text(json.dumps(rows, indent=2) + '\n')
        assert not timeout and child.returncode == 0, (label, child.returncode, err.decode(errors='replace'))
        return out
    command('init', ['init'])
    snapshots = [('s1', 'alpha', 'source-a', ['stable']), ('s2', 'alpha', 'source-a', ['canary']),
        ('s3', 'beta', 'source-a', ['stable']), ('s4', 'alpha', 'source-b', ['stable']),
        ('s5', 'alpha', 'source-a', ['stable']), ('s6', 'alpha', 'source-a', ['stable', 'review'])]
    for n, (label, host, directory, tags) in enumerate(snapshots, start=1):
        source = work / directory; (source / 'fixture.txt').write_text(label + ' private fixture\n')
        args = ['backup', '--host', host, '--time', f'2026-01-{n:02d} 00:00:00', '--tag', ','.join(tags), str(source)]
        events = [json.loads(line) for line in command('backup-' + label, args).splitlines()]
        summary = next(e for e in events if e.get('message_type') == 'summary')
        definitions.append({'label': label, 'host': host, 'path': str(source), 'tags': tags,
            'timeRank': n, 'snapshotPrefix': summary['snapshot_id'], 'sourceSha256': sha(source / 'fixture.txt')})
    all_snapshots = json.loads(command('snapshots-all', ['snapshots']))
    assert len(all_snapshots) == 6
    for definition in definitions:
        selected = [s for s in all_snapshots if s['id'].startswith(definition['snapshotPrefix'])]
        assert len(selected) == 1
        native = selected[0]; definition['id'] = native['id']
        assert native['hostname'] == definition['host'] and native['paths'] == [definition['path']]
        assert sorted(native['tags']) == sorted(definition['tags'])
        assert native['time'].startswith(f'2026-01-{definition["timeRank"]:02d}T00:00:00')
    before_previews = state()
    queries = [
        ('host-alpha', ['--host', 'alpha'], {'hosts': ['alpha'], 'paths': [], 'tags': []}),
        ('path-a', ['--path', str(work / 'source-a')], {'hosts': [], 'paths': [str(work / 'source-a')], 'tags': []}),
        ('tag-stable', ['--tag', 'stable'], {'hosts': [], 'paths': [], 'tags': [['stable']]}),
        ('tags-and', ['--tag', 'stable,review'], {'hosts': [], 'paths': [], 'tags': [['stable', 'review']]}),
        ('tags-or', ['--tag', 'canary', '--tag', 'review'], {'hosts': [], 'paths': [], 'tags': [['canary'], ['review']]}),
        ('host-missing', ['--host', 'missing-fixture'], {'hosts': ['missing-fixture'], 'paths': [], 'tags': []})]
    cases = []
    for label, flags, filter_value in queries:
        command(label, ['snapshots', *flags]); cases.append({'id': label, 'operation': 'select', 'filter': filter_value})
    for label, group in [('latest-groups', 'host,paths'), ('latest-global', '')]:
        command(label, ['snapshots', '--latest', '1', '--group-by', group])
        cases.append({'id': label, 'operation': 'latest', 'groupBy': group})
    for label, group, keep_tags in [('keep-default', None, []), ('keep-global', '', []),
        ('keep-tag-groups', 'host,paths,tags', []), ('keep-union-tag', None, [['canary']])]:
        args = ['forget', '--keep-last', '1', '--dry-run']
        if group is not None: args += ['--group-by', group]
        if keep_tags: args += ['--keep-tag', 'canary']
        command(label, args)
        cases.append({'id': label, 'operation': 'keep', 'groupBy': group if group is not None else 'host,paths', 'keepTags': keep_tags})
    final = json.loads(command('snapshots-after-previews', ['snapshots']))
    assert {s['id'] for s in final} == {s['id'] for s in all_snapshots}
    assert state() == before_previews
    for row in rows[8:]: assert row['observed']['before'] == row['observed']['after'] == before_previews
    (run / 'snapshots.json').write_text(json.dumps(definitions, indent=2) + '\n')
    (run / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    receipt = {'schema': 1, 'producerSha256': hashlib.sha256(PRODUCER).hexdigest(), 'tool': pin,
        'platform': platform.platform(), 'architecture': platform.machine(), 'commands': len(rows), 'snapshots': len(definitions),
        'cases': len(cases), 'scope': 'Private local repository and generated text only; all retention operations are dry runs. Snapshot-reference and encrypted-pack hashes unchanged across selection/previews.',
        'limits': ['No actual policy deletion/prune, remote backend, personal repository, corruption, concurrent writer, partial backup, calendar retention or tied timestamp qualification.',
            'Generated passwords and encrypted repository stay in ignored work; no credential value retained in public records.']}
    (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'run': str(run), 'commands': len(rows), 'snapshots': len(definitions), 'cases': len(cases), 'previewsPreserveRefsAndPacks': True}, indent=2))


if __name__ == '__main__': main()
