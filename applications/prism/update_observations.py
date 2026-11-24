#!/usr/bin/env python3
"""Verify retained Qt cleanup/override observations without rerunning the probe."""
import base64
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / 'applications/evidence/prism-update-20261124T185142536633Z'
FIRST = ROOT / 'applications/evidence/prism-update-20261124T185030965131Z'
sha = lambda b: hashlib.sha256(b).hexdigest()


def image(root):
    result = {}
    def visit(parent):
        for path in sorted(parent.iterdir()):
            name = str(path.relative_to(root))
            if path.is_symlink():
                target = os.readlink(path)
                target = os.path.normpath(str(path.parent / target))
                assert Path(target).is_relative_to(root)
                result[name] = dict(kind='symlink', target=target, exists=path.exists())
            elif path.is_dir(): result[name] = dict(kind='directory'); visit(path)
            else:
                assert path.is_file()
                raw = path.read_bytes()
                result[name] = dict(kind='file', bytes=base64.b64encode(raw).decode(), sha256=sha(raw))
    visit(root)
    return result


def main():
    ledger = json.loads((ROOT / 'applications/sources/prism-update-selections.json').read_text())
    for pin in ledger: assert sha((ROOT / pin['cache']).read_bytes()) == pin['sha256']
    receipts = {}
    for capture, count in [(FIRST, 28), (CAPTURE, 30)]:
        receipt = json.loads((capture / 'receipt.json').read_text()); receipts[capture.name] = receipt
        assert receipt['compileExit'] == receipt['executeExit'] == 0
        assert receipt['qtVersion'] == '6.12.0'
        assert receipt['sourceRevision'] == '7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4'
        assert receipt['sources'] == {p['path']: p['sha256'] for p in ledger}
        for name, key in [('probe.py', 'producerSha256'), ('input.json', 'inputSha256'),
            ('observed.stdout', 'stdoutSha256'), ('observed.stderr', 'stderrSha256')]: assert sha((capture / name).read_bytes()) == receipt[key]
        assert sha((capture / 'work/probe').read_bytes()) == receipt['binarySha256']
        for name, digest in receipt['generatedSha256'].items(): assert sha((capture / 'work' / name).read_bytes()) == digest
        rows = [json.loads(line) for line in (capture / 'observed.stdout').read_text().splitlines()]
        assert len(rows) == count and {r['qtRuntime'] for r in rows} == {receipt['qtVersion']}
    assert receipts[FIRST.name]['fragmentsSha256'] == receipts[CAPTURE.name]['fragmentsSha256']
    receipt = receipts[CAPTURE.name]
    source = (CAPTURE / 'work/main.cpp').read_text()
    creation = next(p for p in ledger if p['path'] == 'launcher/InstanceCreationTask.cpp')
    original = (ROOT / creation['cache']).read_text()
    schedule = original[original.index('void InstanceCreationTask::scheduleToDelete('):]
    cleanup = original[original.index('    if (shouldOverride()) {'):original.index('\n    if (!m_abort) {')]
    assert sha(schedule.encode()) == receipt['fragmentsSha256']['schedule'] and schedule in source
    assert sha(cleanup.encode()) == receipt['fragmentsSha256']['cleanup'] and cleanup in source
    spec = json.loads((CAPTURE / 'input.json').read_text())
    rows = [json.loads(line) for line in (CAPTURE / 'observed.stdout').read_text().splitlines()]
    by_id = {r['id']: r for r in rows}; assert len(by_id) == len(rows)
    cases = CAPTURE / 'work/cases'
    def file_matches(row, text):
        raw = text.encode(); assert row == dict(kind='file', bytes=base64.b64encode(raw).decode(), sha256=sha(raw))
    for case in spec['cleanup']:
        row = by_id[case['id']]; base = cases / case['id'] / 'game'
        assert row['kind'] == 'cleanup' and image(base) == row['after']
        for path, text in case['files'].items(): file_matches(row['before'][path], text)
        for path in case['directories']: assert row['before'][path]['kind'] == 'directory'
        for path, target in case['links'].items(): assert row['before'][path]['target'] == str(base / target)
        assert row['prompts'] <= len(case['answers'])
        assert row['cleanupPassed'] == (not row['failure'])
        assert row['failure'] in ['', 'Failed to remove old conflicting files.']
        assert len(row['normalized']) == len(row['scheduled'])
        for raw, normal in zip(row['scheduled'], row['normalized'], strict=True):
            assert os.path.relpath(os.path.normpath(raw), base) == normal
    losses = []
    for case in spec['overrides']:
        row = by_id[case['id']]; base = cases / case['id']; stage = base / case['name']; game = base / 'installed-game'
        assert row['kind'] == 'overrides' and row['before'] == row['after'] == image(stage)
        for path, text in case['files'].items():
            file_matches(row['before'][path], text); file_matches(row['gameBefore'][path], 'installed:' + text)
        for path, text in case['canaries'].items(): file_matches(row['gameBefore'][path], text)
        assert row['gameAfter'] == image(game)
        manifest = base / 'mrpack' / (case['name'] + '.txt')
        assert manifest.read_bytes() == base64.b64decode(row['listBase64'])
        assert row['read'][-1] == '' and row['prompts'] == 0 and row['cleanupPassed'] and not row['failure']
        old_paths = set(case['files']); recorded = set(row['read']) - {''}
        lost_canaries = sorted(set(case['canaries']) - set(row['gameAfter']))
        if old_paths != recorded:
            assert old_paths <= set(row['gameAfter']) and lost_canaries
            losses.append(dict(case=case['id'], original=sorted(old_paths), recorded=sorted(recorded), removedUnrelated=lost_canaries))
    assert len(losses) == 6
    for label in ['save-dot-prefix', 'save-parent-prefix', 'save-dot-cached-no', 'save-parent-cached-no']:
        row = by_id[label]; assert row['prompts'] == 0 and 'saves/world/level.dat' not in row['after']
    assert by_id['save-dot-cached-no']['saveChoice'] == by_id['save-parent-cached-no']['saveChoice'] == 'No'
    assert by_id['save-refused']['before'] == by_id['save-refused']['after']
    row = by_id['partial-batch-continues']
    assert row['failure'] and 'first.txt' not in row['after'] and 'last.txt' not in row['after'] and 'config' in row['after']
    assert by_id['broken-link-skipped']['before'] == by_id['broken-link-skipped']['after']
    row = by_id['valid-link-only']; assert 'mods/link.jar' not in row['after'] and row['before']['payload.jar'] == row['after']['payload.jar']
    report = dict(schema=1, primaryCases=30, cleanupCases=22, joinedOverrideCases=8,
        priorCaptureCases=28, unchangedFragmentHashes=True, sourcePins=len(ledger),
        saveEquivalentPathCases=4, overridePathLossCases=losses, partialCleanupFailurePreserved=True,
        notes=['Native observations verified against preserved fixtures and source fragments; Lean/Bend policy comparison remains pending.',
            'Unchanged primitive hashes across two runs; earlier capture predates joined override cleanup and two cached-No cases.',
            'Directory traversal order is not qualified; override path bags and scoped effects require separate formal comparison.',
            'Dialog state is explicitly initialized by fixture. Native constructor/initialization, whole archive import/update, downloads, publication and platform qualification remain open.'])
    (ROOT / 'applications/prism/update-observations.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
