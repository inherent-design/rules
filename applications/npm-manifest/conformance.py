"""Read captured npm manifests/streams; execute only Lean and Bend research models."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

from observations import packets, same_json

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'applications/evidence/npm-manifest-20261125T183326087674Z'
LEGACY = [RUN, ROOT / 'applications/evidence/npm-manifest-output-20261125T183512208581Z',
          ROOT / 'applications/evidence/npm-manifest-retry-20261125T185049329242Z']
MODERN = [ROOT / 'applications/evidence/npm-manifest-latest-20261125T190613068581Z',
          ROOT / 'applications/evidence/npm-manifest-document-20261125T190954001477Z']
SOURCE_NAMES = ['selections', 'output-selections', 'test-context', 'upstream-selections']
load = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, value):
    p.write_text(json.dumps(value, indent=2) + '\n')


def compare(actual, expected):
    assert actual == expected, 'Manifest interpretation differs from retained observation'


def snapshots(images):
    for item in images.values():
        raw = bytes.fromhex(item['bytesHex'])
        assert hashlib.sha256(raw).hexdigest() == item['sha256']
        assert same_json(json.loads(raw), item['semantic'])
        assert item['mode'] == 0o100644 and item['mtimeNs'] > 0


def evidence():
    """Original capture integrity and available source/tool readbacks, without reexecution."""
    available, unavailable, checked = [], [], set()

    def artifact(path, digest):
        p = Path(path)
        if not p.exists():
            unavailable.append(str(p))
        elif (str(p), digest) not in checked:
            assert sha(p) == digest, str(p)
            checked.add((str(p), digest))
            available.append(str(p))

    for name in SOURCE_NAMES:
        for item in load(ROOT / f'applications/sources/npm-manifest-{name}.json'):
            p = ROOT / item['cache']
            artifact(p, item['sha256'])
            if p.exists():
                raw = p.read_bytes()
                assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == item['gitBlob']
            if 'installedCorrespondence' in item:
                artifact(item['installedCorrespondence']['path'], item['sha256'])
    pin_path = ROOT / 'applications/sources/npm-manifest-npm12-tool.json'
    pin = load(pin_path)
    tool = ROOT / pin['toolCache']
    receipt_path = tool / 'tool-acquisition.json'
    artifact(receipt_path, pin['acquisitionReceiptSha256'])
    if receipt_path.exists():
        receipt = load(receipt_path)
        artifact(tool / 'acquisition-producer.py', receipt['producerSha256'])
        artifact(tool / 'npm.tgz', pin['archiveSha256'])
        archive = tool / 'npm.tgz'
        if archive.exists():
            assert archive.stat().st_size == pin['archiveBytes']
            assert 'sha512-' + base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode() == pin['integrity']
        assert len(receipt['members']) == pin['files'] == 1943
        assert sum(r['bytes'] for r in receipt['members']) == pin['unpackedBytes']
        for member in receipt['members']:
            rel = Path(member['path'])
            assert not rel.is_absolute() and '..' not in rel.parts and rel.parts[0] == 'package'
            p = tool / rel
            if p.exists():
                assert not p.is_symlink() and p.stat().st_size == member['bytes'] and sha(p) == member['sha256']
            else:
                unavailable.append(str(p))
    total, live_images = 0, {}
    for run, count in zip(LEGACY + MODERN, [24, 4, 3, 13, 2], strict=True):
        setup, receipt = load(run / 'setup.json'), load(run / 'receipt.json')
        assert receipt['complete'] and receipt['commands'] == count and receipt['allRecordedGroupsAbsent']
        assert not receipt['workPathProcessMatches']
        assert sha(run / 'probe.py') == setup['producerSha256']
        if run in LEGACY:
            assert setup['sourceLedgerSha256'] == sha(ROOT / 'applications/sources/npm-manifest-selections.json')
            for item in setup['tools'].values():
                artifact(item['path'], item['sha256'])
        else:
            for filename, key in [('fixture.py', 'fixtureSha256'), ('acquisition-producer.py', 'acquisitionProducerSha256'),
                                  ('tool-pin.json', 'toolPinSha256')]:
                assert sha(run / filename) == setup[key]
            assert sha(pin_path) == setup['toolPinSha256']
            artifact(setup['node']['path'], setup['node']['sha256'])
            artifact(setup['entry'], setup['entrySha256'])
            assert setup['acquisitionReceiptSha256'] == pin['acquisitionReceiptSha256']
        rows = load(run / 'commands.json')
        assert len(rows) == count and len({r['id'] for r in rows}) == count
        for row in rows:
            assert row['processGroupAbsent'] and not row['timedOut'] and row['exitCode'] in [0, 1]
            assert not any(s in row['argv'] for s in ['install', 'publish', 'run', 'exec'])
            for stream in ['stdout', 'stderr']:
                assert sha(run / (row['id'] + '.' + stream)) == row['streams'][stream]
            snapshots(row['before']); snapshots(row['after'])
            for name, image in row['after'].items():
                live_images[Path(row.get('project', str(Path(setup['work']) / 'project'))) / name] = image
        total += count
    for p, image in live_images.items():
        if p.exists():
            assert not p.is_symlink() and sha(p) == image['sha256']
            assert p.stat().st_mode == image['mode'] and p.stat().st_mtime_ns == image['mtimeNs']
        else:
            unavailable.append(str(p))
    retry = load(LEGACY[2] / 'commands.json')
    repair, = load(LEGACY[2] / 'owner-edits.json')
    assert retry[0]['after'] == repair['before'] and repair['after'] == retry[1]['before']
    snapshots(repair['before']); snapshots(repair['after'])
    for name in ['package.json', 'alpha/package.json']:
        assert repair['before'][name] == repair['after'][name]
    before, after = repair['before']['omega/package.json']['semantic'], repair['after']['omega/package.json']['semantic']
    want = copy.deepcopy(before); want['contributors'] = []
    assert want == after and before['contributors'] == 'fixed'
    assert total == 46
    return dict(nativeCommands=total, availableArtifacts=len(checked), unavailableArtifacts=unavailable,
                privateLastImages=len(live_images), npm12VendorMembers=pin['files'])


def main():
    identities = evidence()
    inputs, expected, facts = packets(LEGACY, MODERN)
    assert [len(inputs[k]) for k in ['queries', 'saves', 'appends']] == [26, 31, 5]
    assert len(facts) == 46
    for name, value in [('model-input.json', inputs), ('observed-model-values.json', expected), ('effect-facts.json', facts)]:
        write(RUN / name, value)
    proof = load(RUN / 'proof-gate.json')
    assert proof['observedExitCode'] == 0
    for path, digest in proof['sourceSha256'].items():
        assert sha(ROOT / path) == digest
    formal = ROOT / '.build/npm-manifest-formal'
    formal.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LEAN_PATH=str(formal), BEND_NO_TELEMETRY='1')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    command = [lean, '--run', 'applications/npm-manifest/ManifestCase.lean']
    actual = json.loads(subprocess.check_output(command + [str(RUN / 'model-input.json')], cwd=ROOT, env=env, text=True))
    # Compare only observed fields. Attempted steps and candidate outputs are not native observations.
    for kind in expected:
        for observed, result in zip(expected[kind], actual[kind], strict=True):
            compare({k: result[k] for k in observed}, observed)
    calls, wanted = [], []
    boolarg = lambda v: 'True{}' if v else 'False{}'
    for q, out in zip(inputs['queries'], actual['queries'], strict=True):
        s, p, w, f, a, leaf = [boolarg(q[k]) for k in
                               ['querySucceeded', 'preserveArrays', 'wrapped', 'fieldPresent', 'isArray', 'leafTruthy']]
        n = str(q['length']) + 'n'
        exprs = [f'policy_current({s},{p},{w},{f},{a},{n},{leaf})', f'policy_array({s},{p},{w},{f},{a},{n})',
                 f'policy_display_candidate({s},{p},{w},{f},{a},{n})', f'shape_candidate({s})',
                 f'policy_array({s},True{{}},{w},{f},{a},{n})']
        calls += ['Bool.show(P.' + e + ')' for e in exprs]
        wanted += [str(out[k]) for k in ['dataWritten', 'currentIsArray', 'displayCandidateWritten',
                                         'shapeCandidateWritten', 'shapeCandidateIsArray']]
    for row, out in zip(inputs['saves'], actual['saves'], strict=True):
        steps = '[' + ','.join(str(0 if not s['valid'] else 2 if s['changes'] else 1) + 'n' for s in row['steps']) + ']'
        calls += [f'Nat.show(P.attempted({steps}))', f'Nat.show(P.changed({steps}))', f'Bool.show(P.successful({steps}))']
        wanted += [str(out[k]) for k in ['attempted', 'changedFiles', 'successful']]
    for row, out in zip(inputs['appends'], actual['appends'], strict=True):
        calls.append(f'Nat.show(P.append_count({row["countBefore"]}n))'); wanted.append(str(out['countAfter']))
    target = formal / 'Replay.bend'
    target.write_text('import ../../applications/npm-manifest/Manifest.bend as P\nimport Base\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ "\\n" ++ '.join(calls) + ' ++ "\\n")\n')
    result = subprocess.run([bend, str(target)], cwd=ROOT, env=env, capture_output=True, text=True, check=True)
    compare(result.stdout.splitlines(), wanted)
    assert len(wanted) == 228
    controls = []
    for label, kind, identity, key in [
        ('legacy-falsy-is-not-a-written-result', 'queries', 'get-false', 'dataWritten'),
        ('legacy-singleton-is-not-an-array', 'queries', 'get-single', 'currentIsArray'),
        ('modern-json-writes-false', 'queries', 'json-false', 'dataWritten'),
        ('single-semantic-refusal-preserves-file', 'saves', 'late-override-refusal', 'changedFiles'),
        ('workspace-failure-retains-prefix', 'saves', 'workspace-partial', 'changedFiles'),
        ('workspace-failure-is-not-success', 'saves', 'workspace-partial', 'successful'),
        ('retry-append-is-not-idempotent', 'appends', 'workspace-append-retry:alpha/package.json', 'countAfter')]:
        changed = copy.deepcopy(expected[kind])
        row = next(r for r in changed if r['id'] == identity)
        row[key] = not row[key] if isinstance(row[key], bool) else row[key] + 1
        try:
            compare([{k:r[k] for k in changed[0]} for r in actual[kind]], changed)
        except AssertionError:
            controls.append(label)
        else:
            raise AssertionError('Changed observation escaped comparison')
    for label, change in [('schema', lambda d:d.update(schema=2)),
                          ('missing-field-has-array', lambda d:d['queries'][0].update(fieldPresent=False, isArray=True)),
                          ('scalar-has-array-length', lambda d:d['queries'][0].update(isArray=False, length=1))]:
        changed = copy.deepcopy(inputs); change(changed)
        path = formal / (label + '.json'); write(path, changed)
        r = subprocess.run(command + [str(path)], cwd=ROOT, env=env, capture_output=True, text=True)
        assert r.returncode == 2 and 'research' in r.stderr
        controls.append(label)
    # Existing output guards alone cannot restore a value already discarded by lookup.
    empty = next(r for r in actual['queries'] if r['id'] == 'get-empty')
    false = next(r for r in actual['queries'] if r['id'] == 'get-false')
    assert not empty['displayCandidateWritten'] and empty['shapeCandidateWritten']
    assert false['displayCandidateWritten'] and false['shapeCandidateWritten']
    assert not same_json(False, 0) and not same_json({'value': False}, {'value': 0})
    assert not same_json(None, '') and not same_json([], None)
    controls += ['display-alone-does-not-restore-empty-array', 'separate-presence-retains-falsy', 'typed-json-does-not-conflate-false-and-zero']
    files = [p for run in LEGACY + MODERN for p in run.iterdir()
             if p.is_file() and p.name not in ['basis.json', 'conformance.json', 'initial-comparison.json']]
    files += [p for p in (ROOT / 'applications/npm-manifest').iterdir() if p.is_file()]
    files += [ROOT / f'applications/sources/npm-manifest-{name}.json' for name in SOURCE_NAMES]
    files += [ROOT / 'applications/sources/npm-manifest-npm12-tool.json']
    write(RUN / 'basis.json', {str(p.relative_to(ROOT)):sha(p) for p in files})
    report = dict(schema=1, **identities, queryFrames=26, effectFrames=31, appendTransitions=5,
                  nativeFieldComparisons=119, sourceDerivedAttemptFields=31, proposalOnlyFields=78,
                  bendFieldComparisons=228, leanLaws=24, bendLaws=16, controls=controls, basisFiles=len(files),
                  limits=['Literal paths and ASCII/tab/CRLF authored manifests, not a general JSON-path or filesystem engine.',
                          'npm12 query modes only; legacy writes/workspace retry were not rerun under npm12.',
                          'Semantic refusal and successful save effects do not qualify I/O failure, crash atomicity, concurrent writers, hooks or publication.',
                          'Attempt counts are source-derived; candidate rendering fields are models, not native patched-program outcomes.',
                          'Upstream tests were inspected for scope, not executed. No whole-feature or whole-major conformance.'])
    write(RUN / 'conformance.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
