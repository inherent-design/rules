#!/usr/bin/env python3
"""Check frozen identity outputs and snapshot encodings; no native execution."""
import collections
import hashlib
import json
from pathlib import Path
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'applications/evidence/empack-identity-20261124T193525996513Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def fingerprint(snapshot):
    data = bytearray(b'empack-native-inputs-v2')
    def integer(n, size=8): data.extend(n.to_bytes(size, 'little'))
    def text(value):
        value = value.encode(); integer(len(value)); data.extend(value)
    def object_id(value):
        if value['persistent'] is None: raise ValueError('missing durable evidence')
        assert len(value['persistent']) == 32
        data.extend(value['persistent'])
    object_id(snapshot['root']); entries = snapshot['entries']; integer(len(entries))
    assert [e['path'] for e in entries] == sorted(e['path'] for e in entries)
    for entry in entries:
        text(entry['path']); observed = entry['observation']; tag = observed['tag']
        data.append(dict(absent=0, ancestor=1, file=2, directory=3)[tag])
        if tag != 'absent': object_id(observed['object'])
        if tag == 'file':
            data.extend(observed['content']); integer(observed['bytes']); data.append(int(observed['readonly'])); integer(observed['mode'], 4)
        if tag == 'directory':
            assert observed['members'] == sorted(set(observed['members']))
            integer(len(observed['members']))
            for member in observed['members']: text(member)
    return list(hashlib.sha256(data).digest())


def main():
    receipt = json.loads((RUN / 'receipt.json').read_text()); commands = json.loads((RUN / 'commands.json').read_text())
    repo = ROOT.parent / 'empack'; assert receipt['revision'] == '0b4462e3032b4f09230b15329722eabefb7f574c'
    assert receipt['commands'] == commands and len(commands) == 2
    for row in commands:
        assert row['exitCode'] == 0 and not row['timedOut']
        for stream in ['stdout', 'stderr']: assert sha(RUN / (row['case'] + '.' + stream)) == row[stream + 'Sha256']
    assert sha(RUN / 'probe.py') == receipt['producerSha256'] and sha(RUN / 'driver.rs') == receipt['driverSha256']
    assert sha(RUN / 'work/identity-driver') == receipt['binarySha256']
    for name, digest in receipt['generatedSha256'].items(): assert sha(RUN / 'work' / name) == digest
    assert sha(Path(receipt['compiler']['path'])) == receipt['compiler']['sha256']
    for artifact in receipt['libraries'].values():
        assert sha(Path(artifact['path'])) == artifact['sha256']
        if 'fingerprint' in artifact: assert sha(Path(artifact['fingerprint'])) == artifact['fingerprintSha256']
    pins = json.loads((ROOT / 'applications/sources/empack-identity-selections.json').read_text())
    for p in pins:
        raw = subprocess.check_output(['git', '-C', str(repo), 'show', receipt['revision'] + ':' + p['path']])
        assert hashlib.sha256(raw).hexdigest() == p['sha256'] == receipt['sourceSha256'][p['path']] == sha(repo / p['path'])
    for selected in receipt['sourceSelections']:
        raw = (repo / selected['path']).read_text(); chunk = raw[raw.index(selected['start']):raw.index(selected['stop'])]
        assert hashlib.sha256(chunk.encode()).hexdigest() == selected['sha256']
        assert chunk in (RUN / 'work/main.rs').read_text()
    rows = [json.loads(line) for line in (RUN / 'observed.stdout').read_text().splitlines()]
    counts = collections.Counter(r['kind'] for r in rows); assert counts == dict(identity=12, **{'journal-optional': 9, 'journal-codec': 12, 'fingerprint': 12, 'association-predicate': 5, 'availability': 8})
    assert len(rows) == 58 and len({r['id'] for r in rows}) == 58
    by_id = {r['id']: r for r in rows}
    encoded, unsupported = 0, 0
    for row in rows:
        if row['kind'] != 'fingerprint': continue
        for side in ['left', 'right']:
            try: computed = fingerprint(row['input'][side])
            except ValueError:
                assert not row['outcome'][side + 'Ok'] and row['outcome'][side] is None and row['outcome'][side + 'Error']
                unsupported += 1
            else:
                assert row['outcome'][side + 'Ok'] and computed == row['outcome'][side]
                encoded += 1
    equalities = {r['id']: r['outcome']['equal'] for r in rows if r['kind'] == 'fingerprint'}
    assert {k for k, v in equalities.items() if v is True} == {'snapshot-identical', 'snapshot-device-counterfactual', 'snapshot-insertion-order'}
    assert {k for k, v in equalities.items() if v is None} == {'snapshot-root-unavailable', 'snapshot-file-unavailable'}
    boot = by_id['boot-device-counterfactual']; a, b = boot['input']['left'], boot['input']['right']
    assert a['volume'] != b['volume'] and a['persistent'] == b['persistent'] and not boot['outcome']['liveEqual'] and boot['outcome']['journal']['matches']
    assert not by_id['same-path-same-byte-replacement']['outcome']['journal']['matches']
    assert by_id['journal-both-absent']['outcome']['matches'] and not by_id['journal-observation-unavailable']['outcome']['matches']
    assert not by_id['journal-capture-unavailable']['outcome']['captureOk'] and by_id['journal-capture-unavailable']['outcome']['matches'] is None
    codec = [r for r in rows if r['kind'] == 'journal-codec']
    assert [r['id'] for r in codec if r['outcome']['accepted']] == ['binding-valid']
    for name in ['ENOTSUP', 'ENOTTY', 'ENOSYS', 'EACCES', 'EPERM']:
        out = by_id['availability-' + name]['outcome']; assert out['ok'] and out['available'] is False and out['error'] is None
    for name in ['ENOENT', 'EINVAL', 'EIO']:
        out = by_id['availability-' + name]['outcome']; assert not out['ok'] and out['available'] is None and out['error']
    association = by_id['association-device-counterfactual']['outcome']
    assert association['matched'] and association['name'] != association['currentKey']
    assert by_id['association-wrong-name']['outcome']['matched'] is None
    root = RUN / 'work/native-files'
    expected = {'original': (b'identical\n', None), 'copy': (b'identical\n', None),
        'renamed': (b'changed!\n', 0o400), 'folder/a': (b'member', None),
        'folder/b': (b'new member', None), 'not-present': (b'new occupant', None)}
    for name, (raw, mode) in expected.items():
        assert (root / name).read_bytes() == raw
        if mode is not None: assert stat.S_IMODE((root / name).stat().st_mode) == mode
    assert {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()} == set(expected)
    for name, label in [('original', 'same-path-same-byte-replacement'), ('renamed', 'readonly-edit-same-object'), ('copy', 'copied-same-bytes')]:
        value = by_id[label]['input']['right']; physical = (root / name).stat()
        assert str(physical.st_dev) == value['volume'] and str(physical.st_ino) == value['object']
    assert encoded == 22 and unsupported == 2
    report = dict(schema=1, cases=58, byKind=dict(counts), sourcePins=len(pins), snapshotByteEncodingsChecked=encoded,
        unsupportedFingerprintSides=unsupported,
        nativeVersusSyntheticOrigins=dict(collections.Counter(r['origin'] for r in rows)), postFixtureFilesVerified=len(expected),
        limits=['Observed/source consistency and independent Python reconstruction of snapshot hash bytes only; formal policies remain pending.',
            'Durable object tokens are opaque native outputs; this checker does not independently recompute filesystem UUID evidence.',
            'Device/creation/object-field perturbations and errno failures are injected,not observed reboots,OS identifier changes,or permission incidents.',
            'Snapshots are assembled from fixture observations,not captured through real roots/scopes/filters or revalidated. Root association is a pure predicate with a binding-only adapter.',
            'No actual recovery journal,state directory,publication,installation or live operation store is accessed. Source tests inspected but not run.'])
    (ROOT / 'applications/empack/identity-observations.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__': main()
