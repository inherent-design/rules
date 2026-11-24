#!/usr/bin/env python3
"""Compare captured archive inventories and outcomes without running Cargo."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tomllib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    receipt = json.loads((run / 'receipt.json').read_text()); trace = json.loads((run / 'trace.json').read_text())
    native = {r['id']: r for r in json.loads((run / 'cases.json').read_text())}
    assert len(trace) == receipt['commands'] == 12 and len(native) == receipt['cases'] == 5
    assert sha(run / 'probe.py') == receipt['producerSha256']
    inputs = [HERE / p for p in ['Package.lean', 'Package.bend', 'PackageCase.lean']]
    inputs += [ROOT / 'applications/sources/cargo-package-selections.json']
    inputs += [run / p for p in ['receipt.json', 'trace.json', 'cases.json', 'probe.py']]
    for path in run.iterdir():
        if path.suffix in ['.stdout', '.stderr', '.crate', '.toml', '.rs']: inputs.append(path)
    basis = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    for source in json.loads((ROOT / 'applications/sources/cargo-package-selections.json').read_text())['sources']:
        assert sha(ROOT / source['cache']) == source['sha256']
    cases, expected, facts, decisions = [], [], [], []
    profiles = {'default': False, 'exclude': False, 'include': True, 'both': True, 'invalid-source': False}
    for row in trace:
        case, operation = row['case'], row['operation']; spec = native[case]
        stem = case + '-' + operation
        assert not row['outcome']['timedOut']
        for stream in ['stdout', 'stderr']:
            assert sha(run / (stem + '.' + stream)) == row['observed'][stream + 'Sha256']
        assert row['observed']['before']['inputsSha256'] == row['observed']['after']['inputsSha256'] == spec['inputsSha256']
        assert (run / (case + '-Cargo.toml')).read_text() == spec['manifest']
        source = (run / (case + '-lib.rs')).read_text()
        assert source == ('this is deliberately not valid Rust\n' if case == 'invalid-source' else 'pub fn answer() -> u32 { 42 }\n')
        assert sha(run / (case + '-Cargo.toml')) == spec['inputsSha256']['Cargo.toml']
        assert sha(run / (case + '-lib.rs')) == spec['inputsSha256']['src/lib.rs']
        stderr = (run / (stem + '.stderr')).read_text()
        checked = 'Verifying fixture-package' in stderr
        archive_present = row['observed']['after']['archiveSha256'] is not None
        observed_entries = row['observed']['archiveEntries']
        if archive_present:
            archive = run / (stem + '.crate')
            assert sha(archive) == row['observed']['after']['archiveSha256']
            actual = []
            with tarfile.open(archive, 'r:gz') as tar:
                for entry in tar:
                    assert entry.isfile() and entry.name.startswith('fixture-package-0.1.0/')
                    name = entry.name.removeprefix('fixture-package-0.1.0/'); assert '..' not in Path(name).parts
                    data = tar.extractfile(entry).read()
                    actual.append({'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'text': data.decode('utf-8')})
            assert actual == observed_entries
            entries = {entry['path']: entry for entry in actual}
            assert len(entries) == len(actual)
            assert entries['Cargo.toml.orig']['text'] == spec['manifest']
            normalized = tomllib.loads(entries['Cargo.toml']['text'])
            original = tomllib.loads(spec['manifest'])
            for field in ['name', 'version', 'edition', 'publish', 'readme', 'license-file']:
                assert normalized['package'][field] == original['package'][field]
            assert normalized['lib']['path'] == 'src/lib.rs' and normalized['package']['autolib'] is False
            assert entries['Cargo.toml']['sha256'] != entries['Cargo.toml.orig']['sha256']
            for name in ['src/lib.rs', 'LICENSE.txt', 'README.md', 'data/keep.txt', 'data/drop.txt', 'ignored.txt', '.gitignore']:
                if name in entries: assert entries[name]['sha256'] == spec['inputsSha256'][name]
            assert not any(name.startswith(('nested/', 'target/')) for name in entries)
            files = sorted(entries)
        else:
            assert observed_entries is None and row['observed']['before']['archiveSha256'] is None
            assert operation == 'list'
            files = (run / (stem + '.stdout')).read_text().splitlines()
        request = dict(profile=case, request=operation, includeLock=operation != 'without-lock', compiles=case != 'invalid-source')
        cases.append(request)
        expected.append(dict(files=files, archiveCreated=archive_present, buildChecked=checked,
            buildSucceeded=checked and row['outcome']['exitCode'] == 0, commandSucceeded=row['outcome']['exitCode'] == 0))
        decisions.append((operation, case != 'invalid-source'))
        # Compare every modeled source role, including inputs correctly absent.
        for name in spec['inputsSha256']:
            required = name in ['Cargo.toml', 'LICENSE.txt', 'README.md']
            prohibited = name.startswith(('nested/', 'target/'))
            facts.append((profiles[case], prohibited, required, name == 'ignored.txt',
                name in ['src/lib.rs', 'data/keep.txt', 'ignored.txt'],
                (case == 'exclude' and name == 'data/drop.txt') or (case == 'both' and name == 'data/keep.txt'), name in files))
        if operation == 'verification-fails':
            assert row['outcome']['exitCode'] == 101 and checked and archive_present
            assert row['observed']['before']['archiveSha256'] is None
            assert 'failed to verify package tarball' in stderr
    generated = HERE / 'generated'; generated.mkdir(exist_ok=True)
    path = generated / 'package.json'
    env = dict(os.environ, LEAN_PATH=os.pathsep.join(str(ROOT / p) for p in ['.build', '.build/formal']), BEND_NO_TELEMETRY='1')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    def replay(data):
        path.write_text(json.dumps(data) + '\n')
        return subprocess.run([lean, '--run', 'applications/cargo/PackageCase.lean', str(path)], cwd=ROOT, env=env, capture_output=True, text=True)
    result = replay({'schema': 1, 'cases': cases}); assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == expected
    bit = lambda x: 'True{}' if x else 'False{}'
    calls = ['bit(P.selected(P.FileFacts{' + ','.join(bit(b) for b in fact[1:6]) + '},' + bit(fact[0]) + ')) ++ "\\n"' for fact in facts]
    for operation, compiles in decisions:
        request = 'ListOnly' if operation == 'list' else 'Unchecked' if operation in ['unchecked', 'without-lock'] else 'Verify'
        calls.append('render(P.outcome(P.' + request + '{},' + bit(compiles) + ')) ++ "\\n"')
    runner = generated / 'PackageCase.bend'
    runner.write_text('import Base\nimport ../Package.bend as P\n\ndef bit(b: Bool) -> String:\n  match b:\n    case True{}: "1"\n    case False{}: "0"\n\ndef render(out: P.Outcome) -> String:\n  match out:\n    case P.Outcome{archive,checked,build_ok,command_ok}: bit(archive) ++ bit(checked) ++ bit(build_ok) ++ bit(command_ok)\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(calls) + ')\n')
    result = subprocess.run([bend, str(runner)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    expected_bend = [str(int(f[-1])) for f in facts] + [''.join(str(int(row[key])) for key in ['archiveCreated', 'buildChecked', 'buildSucceeded', 'commandSucceeded']) for row in expected]
    assert result.stdout.splitlines() == expected_bend
    refused = []
    for label, data, diagnostic in [('schema', {'schema': 2, 'cases': cases}, 'Unsupported Cargo package schema'),
        ('profile', {'schema': 1, 'cases': [dict(cases[0], profile='other')]}, 'Unknown package-selection profile'),
        ('request', {'schema': 1, 'cases': [dict(cases[0], request='publish')]}, 'Unknown package request')]:
        result = replay(data); assert result.returncode == 2 and diagnostic in result.stderr; refused.append(label)
    path.write_text(json.dumps({'schema': 1, 'cases': cases}, indent=2) + '\n')
    assert all(sha(ROOT / p) == digest for p, digest in basis.items()), 'Inputs changed during comparison.'
    report = {'schema': 1, 'adapterSha256': sha(Path(__file__)), 'basisSha256': basis, 'nativeCommands': 12,
        'leanInventoriesAndOutcomes': len(cases), 'bendSourceMemberships': len(facts), 'bendOutcomes': len(decisions),
        'bothModelsMatch': True, 'refusedInputs': refused,
        'rejectedInterpretations': ['A listed file is already archived.', 'An existing .crate proves successful verification.',
            'A successful --no-verify proves compilability.', 'Explicit include is still restricted by Git ignore and exclude.',
            'A packaged manifest is byte-identical to the author manifest.', 'Local packaging is registry publication.'],
        'limits': ['Generated no-dependency crates, selected Git/include/exclude patterns and declared root metadata only.',
            'Lean predicts exact controlled inventories and build outcomes; Bend compares matched source facts and controlled outcomes, not glob/Git/archive implementations.',
            'Cargo build verification is one selected compile; no exhaustive tests, runtime, dependency rewrite, registry/credential, publication, symlink, workspace, interrupted IO or platform qualification.',
            'Source input hashes remain unchanged, not every cache/target/log/lock. Creation precedes verification; a failure may retain the local archive.']}
    (run / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'basisSha256'}, indent=2))


if __name__ == '__main__': main()
