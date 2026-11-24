#!/usr/bin/env python3
"""Verify retained discovery observations and private fixture postimages only."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'applications/evidence/empack-root-state-20261124T201312610313Z'
FAILED = ROOT / 'applications/evidence/empack-root-state-20261124T201230642889Z'
PREFIX = ROOT / 'applications/evidence/empack-root-state-20261124T201907525187Z'
COMPILE_FAILURE = ROOT / 'applications/evidence/empack-root-state-20261124T201809705356Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def image(base):
    base = os.fsencode(base); rows = {}
    def visit(path):
        m = os.lstat(path); relative = os.path.relpath(path, base)
        if relative == b'.': relative = b''
        row = dict(mode=m.st_mode, inode=str(m.st_ino), device=str(m.st_dev),
            mtime=[m.st_mtime_ns // 10**9, m.st_mtime_ns % 10**9], bytes=m.st_size)
        if stat.S_ISLNK(m.st_mode): row.update(kind='symlink', targetHex=os.readlink(path).hex())
        elif stat.S_ISREG(m.st_mode):
            with open(path, 'rb') as f: row.update(kind='file', contentHex=f.read().hex())
        elif stat.S_ISDIR(m.st_mode): row.update(kind='directory')
        else: row.update(kind='special')
        rows[relative.hex()] = row
        if stat.S_ISDIR(m.st_mode):
            for name in os.listdir(path): visit(os.path.join(path, name))
    visit(base); return rows


def verify_receipt(run, failed=False):
    receipt = json.loads((run / 'receipt.json').read_text()); commands = json.loads((run / 'commands.json').read_text())
    assert receipt['revision'] == '0b4462e3032b4f09230b15329722eabefb7f574c' and receipt['commands'] == commands
    assert len(commands) == 2 and commands[0]['case'] == 'compile' and commands[0]['exitCode'] == 0
    assert commands[1]['case'] == 'observed' and commands[1]['exitCode'] == (1 if failed else 0)
    for c in commands:
        assert not c['timedOut']
        for stream in ['stdout', 'stderr']: assert sha(run / (c['case'] + '.' + stream)) == c[stream + 'Sha256']
    assert sha(run / 'probe.py') == receipt['producerSha256'] and sha(run / 'driver.rs') == receipt['driverSha256']
    assert sha(Path(receipt['compiler']['path'])) == receipt['compiler']['sha256']
    for artifact in receipt['libraries'].values():
        assert sha(Path(artifact['path'])) == artifact['sha256']
        if 'fingerprint' in artifact: assert sha(Path(artifact['fingerprint'])) == artifact['fingerprintSha256']
    for name, digest in receipt['generatedSha256'].items(): assert sha(run / 'work' / name) == digest
    assert sha(run / 'work/discovery-driver') == receipt['binarySha256']
    assert sha(run / 'work/link-map.txt') == receipt['linkMapSha256']
    assert sha(ROOT / receipt['priorReceipt']) == receipt['priorReceiptSha256']
    repo = ROOT.parent / 'empack'
    for path, digest in receipt['sourceSha256'].items():
        raw = subprocess.check_output(['git', '-C', str(repo), 'show', receipt['revision'] + ':' + path])
        assert hashlib.sha256(raw).hexdigest() == digest == sha(repo / path)
    for selected in receipt['sourceSelections']:
        raw = (repo / selected['path']).read_text(); value = raw[raw.index(selected['start']):raw.index(selected['stop'])]
        assert hashlib.sha256(value.encode()).hexdigest() == selected['sha256']
        assert value in (run / 'work/main.rs').read_text()
    rows = [json.loads(line) for line in (run / 'observed.stdout').read_text().splitlines()]
    assert len({r['id'] for r in rows}) == len(rows)
    latest = {}
    for row in rows:
        p = run / 'images' / row['image']; state = json.loads(p.read_text())
        digest = sha(p)
        if row.get('setupUnavailable'):
            assert row['sourceCalls'] == 0 and digest == row['imageSha256'] and row['errno'] == 92
        else:
            assert digest == row['beforeSha256'] == row['afterSha256'] and len(state) == row['entries']
            a, b, c = row['resolved'], row['found'], row['bound']
            assert a['ok'] == b['ok'] == c['ok']
            if a['ok']:
                assert b['found'] == (a['selected'] is not None)
                assert c['key'] == (a['selected'] or row['currentKey'])
                assert a['error'] is b['error'] is c['error'] is None
            else:
                assert a['error'] == b['error'] == c['error'] and b['found'] is None and c['key'] is None
        latest[row['fixture']] = state
    # limit4096 and limit4097 intentionally share one fixture. Only its last
    # observed image is a current postimage; the former image remains historical.
    for fixture, expected in latest.items(): assert image(run / 'work/cases' / fixture) == expected, fixture
    return receipt, rows, latest


def main():
    old, partial, old_images = verify_receipt(FAILED, True)
    assert len(partial) == 28 and 'Illegal byte sequence' in (FAILED / 'observed.stderr').read_text()
    receipt, rows, images = verify_receipt(RUN)
    assert len(rows) == 35 and len(receipt['sourceSha256']) == 10
    available = [r for r in rows if not r.get('setupUnavailable')]; assert len(available) == 34
    unavailable = [r for r in rows if r.get('setupUnavailable')]; assert [r['id'] for r in unavailable] == ['nonutf8']
    by_id = {r['id']: r for r in available}
    assert by_id['valid-prior-device']['resolved']['selected'] != by_id['valid-prior-device']['currentKey']
    assert by_id['current-empty']['resolved']['selected'] is None and by_id['current-state-lock']['resolved']['selected'] is None
    for key in ['current-operation-lock', 'current-unassociated', 'prior-empty', 'prior-unassociated', 'selected-plus-unassociated', 'escaped-coordinates']:
        assert by_id[key]['resolved']['error']['unassociated']
    assert by_id['locked-discovery']['found']['found']
    assert by_id['limit4096']['found']['found'] and not by_id['limit4097']['found']['ok']
    assert 'entry limit' in by_id['limit4097']['found']['error']['message']
    msg = by_id['escaped-coordinates']['resolved']['error']['message']
    assert '\\nfalse heading' in msg and '\nfalse heading' not in msg
    assert by_id['exact-limit']['found']['found']
    hosts = {}
    for key in ['limit4096', 'limit4097']:
        state = json.loads((RUN / 'images' / by_id[key]['image']).read_text())
        children = [bytes.fromhex(path) for path in state if bytes.fromhex(path).startswith(b'host/') and bytes.fromhex(path).count(b'/') == 1]
        hosts[key] = len(children)
    assert hosts == dict(limit4096=4096, limit4097=4097)
    prefix_receipt, prefix_rows, prefix_images = verify_receipt(PREFIX)
    assert len(prefix_rows) == 1 and len(prefix_receipt['sourceSha256']) == 11
    prefix = prefix_rows[0]; assert prefix['id'] == 'writer-lock-prefix' and prefix['resolved']['error']['unassociated']
    pre = prefix['prefixBefore']; path = PREFIX / 'images' / pre['image']; assert sha(path) == pre['sha256']
    before = json.loads(path.read_text()); after = prefix_images[prefix['fixture']]
    added = set(after) - set(before); assert len(added) == 1 and set(before) <= set(after)
    added_path = next(iter(added)); assert bytes.fromhex(added_path).endswith(b'/operation.lock')
    assert after[added_path]['kind'] == 'file' and after[added_path]['contentHex'] == ''
    changed = [p for p in before if before[p] != after[p]]
    assert len(changed) == 1 and before[changed[0]]['kind'] == after[changed[0]]['kind'] == 'directory'
    assert bytes.fromhex(added_path).rsplit(b'/', 1)[0] == bytes.fromhex(changed[0])
    a, b = dict(before[changed[0]]), dict(after[changed[0]])
    # Directory byte length is filesystem metadata, not a user-file payload.
    for field in ['mtime', 'bytes']: a.pop(field); b.pop(field)
    assert a == b and not any(bytes.fromhex(p).endswith(b'/root-identity.json') for p in after)
    failure = json.loads((COMPILE_FAILURE / 'receipt.json').read_text())
    assert len(failure['commands']) == 1 and failure['commands'][0]['exitCode'] == 1 and not failure['commands'][0]['timedOut']
    for stream in ['stdout', 'stderr']:
        assert sha(COMPILE_FAILURE / ('compile.' + stream)) == failure['commands'][0][stream + 'Sha256']
    assert 'cannot find type `File`' in (COMPILE_FAILURE / 'compile.stderr').read_text()
    assert not (COMPILE_FAILURE / 'observed.stdout').exists()
    report = dict(schema=1, sourceRevision=receipt['revision'], sourcePins=10, availableCases=34,
        entrypointsPerAvailableCase=['resolve_project_state', 'find_project_state', 'bound_root_key'],
        outcomes=dict(Counter('error' if not r['resolved']['ok'] else 'selected' if r['resolved']['selected'] else 'none' for r in available)),
        privateCurrentPostimagesVerified=len(images), historicalPhaseImages=1, exactGlobalEntryBoundary=hosts,
        unavailableCases=[dict(id=r['id'], errno=r['errno'], reason=r['error'], sourceCalls=0) for r in unavailable],
        priorFailedCollection=dict(capture=str(FAILED.relative_to(ROOT)), reason='Fixture non-UTF-8 filename rejected before lookup;not an empack failure.', retainedCompletedCases=len(partial), postimagesVerified=len(old_images)),
        writerPrefix=dict(capture=str(PREFIX.relative_to(ROOT)), sourcePins=11, discoveryCases=1,
            beforeImage=pre, exactAddedFile=bytes.fromhex(added_path).decode(),
            changedParentMetadataOnly=bytes.fromhex(changed[0]).decode(), outcome='unassociated;not a full writer/crash/recovery test'),
        failedPrefixCompilation=dict(capture=str(COMPILE_FAILURE.relative_to(ROOT)), cause='Fixture scaffold omitted File import;no native execution;fixed before new prefix capture.'),
        sourceFacts=['Old synthetic device-label association is selected without renaming/rebinding the physical state slot.',
            'Current empty/state.lock-only slot is not selected;old empty and operation.lock-only unassociated slots refuse.',
            'A matching candidate does not bypass another unresolved claim,duplicate ownership,bad records or the global entry cap.',
            'Read-only discovery succeeds while a fixture operation.lock is held;this does not qualify publication/recovery coordination.',
            'Root disappearance/replacement refuse;nonregular association/state entries are not followed or accepted.'],
        limits=['These checks verify retained observations,source/artifacts and private postimages;formal comparisons are separately recorded by root_state_conformance.py.',
            'Actual unchanged source methods on macOS;provided Publisher capability,not Publisher::open/private-state initialization.',
            'Synthetic old-device records,authored journal/runtime sentinels and held fixture lock;no real reboot,operation/recovery or interrupted engine write.',
            'Images compare bytes,shape,inode/device,mode andmtime;access time is excluded. At the limit,all immediate host entries count,not only matching project names.',
            'Actual lock/lock_file/ensure_stopped prefix creates operation.lock then discovery refuses;the full association writer/interruption lifecycle remains unqualified,current reader refusal must not be weakened.',
            'No live operation store,production project,legacy-state sweep or Moment recovery payload accessed.'])
    (ROOT / 'applications/empack/root-state-observations.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
