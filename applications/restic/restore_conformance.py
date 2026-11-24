#!/usr/bin/env python3
"""Pure replay of frozen restore target images; no restic or deletion runs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ADAPTER = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    capture = parser.parse_args().run.resolve()
    receipt = json.loads((capture / 'receipt.json').read_text())
    rows = json.loads((capture / 'trace.json').read_text())
    assert len(rows) == receipt['commands'] == 20
    assert receipt['allOwnedProcessesRetired'] and not receipt['finalLocks'] and receipt['sourceUnchanged']
    assert sha(capture / 'probe.py') == receipt['producerSha256']
    assert sha(capture / 'helper.py') == receipt['helperSha256']
    source = json.loads((capture / 'source-image.json').read_text())
    assert sha(capture / 'source-image.json') == receipt['sourceImageSha256']
    assert {p for p, value in source.items() if value['kind'] == 'file'} == {'alpha.txt', 'options.txt', 'sub/beta.txt'}
    sources_path = ROOT / 'applications/sources/restic-restore-selections.json'
    sources = json.loads(sources_path.read_text())['sources']
    for row in sources:
        assert sha(ROOT / row['cache']) == row['sha256']
    inputs = [HERE / name for name in ['Restore.lean', 'RestoreCase.lean', 'Restore.bend']]
    inputs.append(sources_path)
    inputs += [p for p in sorted(capture.rglob('*')) if p.is_file() and 'work' not in p.relative_to(capture).parts
               and p.name != 'conformance.json']
    basis = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    cases, expected, observed_scope, private_streams = [], [], [], []
    for row in rows:
        for stream, identity in row['observed']['streams'].items():
            public = capture / (row['case'] + '.' + stream)
            assert sha(public) == identity['publicSha256']
            private = capture / identity['rawPrivatePath']
            assert private.is_relative_to(capture / 'work/private')
            assert sha(private) == identity['rawSha256']
            private_streams.append(str(private.relative_to(capture)))
        assert not row['outcome']['timedOut']
        if not row['request']:
            assert row['outcome']['exitCode'] == 0
            continue
        r = row['request']
        b, a = row['observed']['before'], row['observed']['after']
        assert r['snapshot'] == receipt['snapshot']
        before = b.get('alpha.txt')
        if before is None:
            prior, order, size = 'missing', 'equal', False
        elif before['kind'] == 'symlink':
            prior, order, size = 'symlink', 'equal', False
        else:
            assert before['kind'] == 'file'
            prior = 'correct' if before['sha256'] == source['alpha.txt']['sha256'] else 'different'
            order = 'older' if before['mtimeNs'] < source['alpha.txt']['mtimeNs'] else (
                'newer' if before['mtimeNs'] > source['alpha.txt']['mtimeNs'] else 'equal')
            size = before['bytes'] == source['alpha.txt']['bytes']
        flags = r['flags']
        assert set(flags) <= {'--verify', '--delete', '--exclude', '--include', '--dry-run', '-vv',
                             '/extra.txt', '/extra/protected.txt', '/extra', '/alpha.txt', '/options.txt'}
        valid = not ('--include' in flags and '--exclude' in flags or '--dry-run' in flags and '--verify' in flags)
        filter_name = 'all'
        if '--include' in flags:
            filter_name = 'include-alpha'
        elif '--exclude' in flags:
            filter_name = {'/extra.txt': 'exclude-root', '/extra/protected.txt': 'exclude-child',
                           '/extra': 'exclude-directory'}[flags[flags.index('--exclude') + 1]]
        case = dict(policy=r['overwrite'], existing=prior, time=order, sameSize=size,
            selected=True, dry='--dry-run' in flags, verify='--verify' in flags, valid=valid,
            extras='extra.txt' in b, delete='--delete' in flags, filter=filter_name)
        cases.append(case)
        target = a.get('alpha.txt')
        final = 'missing' if target is None else 'symlink' if target['kind'] == 'symlink' else (
            'correct' if target['sha256'] == source['alpha.txt']['sha256'] else 'different')
        present = [name in a for name in ['extra.txt', 'extra', 'extra/protected.txt', 'extra/unselected.txt']]
        expected.append('/'.join([final, *[str(int(v)) for v in present], str(row['outcome']['exitCode'])]))
        for path in ['options.txt', 'sub/beta.txt']:
            # Every nonempty target starts with the correct non-alpha bytes.
            if path in b:
                assert a[path]['sha256'] == b[path]['sha256'] == source[path]['sha256']
        if case['dry'] or not valid:
            assert b == a
        if row['case'] == 'empty-always':
            assert all(a[name]['sha256'] == value['sha256'] for name, value in source.items() if value['kind'] == 'file')
        if row['case'] == 'symlink-owned-canary':
            assert row['observed']['canary']['beforeSha256'] == row['observed']['canary']['afterSha256']
        if row['case'] == 'same-metadata-if-changed':
            assert before['sha256'] != source['alpha.txt']['sha256'] and a['alpha.txt']['sha256'] == before['sha256']
            assert '--verify' in flags and row['outcome']['exitCode'] == 0
        observed_scope.append(dict(case=row['case'], beforeKind=prior, afterKind=final,
            extrasAfter=present, targetImageUnchanged=b == a,
            verificationRequested=case['verify'], exitCode=row['outcome']['exitCode']))
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)
    path = generated / 'restore.json'
    path.write_text(json.dumps(dict(schema=1, cases=cases), indent=2) + '\n')
    env = dict(os.environ, LEAN_PATH=str(ROOT / '.build/formal'), BEND_NO_TELEMETRY='1')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')

    def lean_run(path):
        return subprocess.run([lean, '--run', 'applications/restic/RestoreCase.lean', str(path)],
                              env=env, cwd=ROOT, text=True, capture_output=True)

    result = lean_run(path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == expected
    bit = lambda value: 'True{}' if value else 'False{}'
    calls = []
    for c in cases:
        policy = {'always': 'Always', 'if-changed': 'IfChanged', 'if-newer': 'IfNewer', 'never': 'Never'}[c['policy']]
        prior = {'missing': 'Missing', 'correct': 'Correct', 'different': 'Different', 'symlink': 'Symlink'}[c['existing']]
        order = {'older': 'Older', 'equal': 'Equal', 'newer': 'Newer'}[c['time']]
        f = {'all': 'All', 'exclude-root': 'ExcludeRoot', 'exclude-child': 'ExcludeChild',
             'exclude-directory': 'ExcludeDirectory', 'include-alpha': 'IncludeAlpha'}[c['filter']]
        file_args = ','.join([f'M.{policy}{{}}', f'M.{prior}{{}}', f'M.{order}{{}}',
                              *[bit(c[k]) for k in ['sameSize', 'selected', 'dry', 'verify', 'valid']]])
        extra = ','.join([bit(c['delete']), bit(c['dry']), bit(c['valid']), f'M.{f}{{}}',
                          'M.ExtraState{' + ','.join([bit(c['extras'])] * 4) + '}'])
        calls.append(f'render(M.after(M.FileRequest{{{file_args}}}),M.delete_current({extra}),{bit(c["valid"])}) ++ "\\n"')
    runner = generated / 'RestoreCase.bend'
    runner.write_text('import Base\nimport ../Restore.bend as M\n\ndef bit(b: Bool) -> String:\n  match b:\n    case True{}: "1"\n    case False{}: "0"\n\ndef content(c: M.Existing) -> String:\n  match c:\n    case M.Missing{}: "missing"\n    case M.Correct{}: "correct"\n    case M.Different{}: "different"\n    case M.Symlink{}: "symlink"\n\ndef render(c: M.Existing, s: M.ExtraState, valid: Bool) -> String:\n  match s:\n    case M.ExtraState{root,directory,child,other}: content(c) ++ "/" ++ bit(root) ++ "/" ++ bit(directory) ++ "/" ++ bit(child) ++ "/" ++ bit(other) ++ "/" ++ bit(Bool.not(valid))\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(calls) + ')\n')
    result = subprocess.run([bend, str(runner)], env=env, cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == expected
    negatives = [dict(schema=2, cases=cases), *[dict(schema=1, cases=[dict(cases[0], **change)]) for change in
        [dict(policy='merge'), dict(existing='directory'), dict(time='unknown'), dict(filter='glob'),
         dict(existing='missing', sameSize=True), dict(dry=True, verify=True, valid=True)]]]
    for i, negative in enumerate(negatives):
        path = generated / f'restore-negative-{i}.json'
        path.write_text(json.dumps(negative))
        result = lean_run(path)
        assert result.returncode == 2 and result.stderr
    assert all(sha(ROOT / name) == value for name, value in basis.items())
    report = dict(schema=1, nativeCommands=len(rows), modeledRestoreOutcomes=len(cases),
        bothModelsMatch=True, unsupportedResearchInputsRefused=len(negatives), observedScope=observed_scope,
        adapterSha256=ADAPTER, basisSha256=basis, ownerLocalPrivateStreams=len(private_streams),
        rejectedInterpretations=['verify request checks every retained existing file',
            'if-changed always compares payload bytes', 'a child exclusion necessarily protects it from recursive parent deletion',
            'dry-run deleted action means removal occurred', 'restore success proves application consistency'],
        limits=['Generated three-file subtree and fresh private targets; not a general restic restore implementation.',
            'Verification eligibility and proposed child-preserving deletion are source/model claims, not native read counters or adopted changes.',
            'Current upstream tests explicitly allow selected unexpected directory deletion without selecting each child.',
            'Canary result is one owned leaf-symlink case, not general path/permission/hardlink/platform security qualification.',
            'Raw/public stream attribution requires retained owner-local originals; no real user backup or remote service used.'])
    (capture / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['basisSha256', 'observedScope']}, indent=2))


if __name__ == '__main__':
    main()
