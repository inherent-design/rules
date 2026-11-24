#!/usr/bin/env python3
"""Offline, disposable Cargo workspace; no installed project or registry is used.

The initial build script deliberately omits an input and writes outside OUT_DIR.
These are fixture violations of Cargo's guidance, not alleged Cargo defects.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
BIN = Path('/Users/zer0cell/.rustup/toolchains/stable-aarch64-apple-darwin/bin')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def main():
    run = HERE / 'evidence' / ('cargo-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir(parents=True)
    shutil.copyfile(Path(__file__), run / 'probe.py')
    # CWD ancestry matters: private CARGO_HOME alone does not exclude ancestor config.
    work = Path(tempfile.mkdtemp(prefix='rules-cargo-', dir='/private/tmp'))
    for parent in [work, *work.parents]:
        assert not any((parent / '.cargo' / f).exists() for f in ['config', 'config.toml']), parent
    project = work / 'project'
    for p in [project, work / 'home', work / 'cargo-home', work / 'tmp']:
        p.mkdir()
    for pkg in ['app', 'tool', 'library']:
        (project / pkg / 'src').mkdir(parents=True)
    def write(path, data):
        (project / path).write_text(data)
    write('Cargo.toml', '[workspace]\nmembers=["app","tool","library"]\ndefault-members=["app"]\nresolver="2"\n')
    write('library/Cargo.toml', '[package]\nname="fixture-library"\nversion="0.1.0"\nedition="2021"\n[features]\nred=[]\nblue=[]\n')
    for pkg, feature in [('app', 'red'), ('tool', 'blue')]:
        write(pkg + '/Cargo.toml', f'[package]\nname="fixture-{pkg}"\nversion="0.1.0"\nedition="2021"\n[dependencies]\nfixture-library={{path="../library",features=["{feature}"]}}\n')
        write(pkg + '/src/main.rs', 'fn main() { println!("{}", fixture_library::report()); }\n')
    write('library/src/lib.rs', 'pub fn report() -> String { format!(r#"{{"red":{},"blue":{},"input":"{}"}}"#, cfg!(feature="red"), cfg!(feature="blue"), env!("FIXTURE_INPUT")) }\n')
    script = '''fn main() {
    println!("cargo::rerun-if-changed=build.rs");
    let value = std::fs::read_to_string("../input.txt").unwrap();
    println!("cargo::rustc-env=FIXTURE_INPUT={}", value.trim());
    // Deliberate negative fixture: Cargo recommends all outputs stay in OUT_DIR.
    std::fs::write("../script-side-effect.txt", value).unwrap();
}
'''
    write('library/build.rs', script)
    write('input.txt', 'first\n')
    env = {'PATH': str(BIN) + ':/usr/bin:/bin', 'HOME': str(work / 'home'),
           'CARGO_HOME': str(work / 'cargo-home'), 'CARGO_TARGET_DIR': str(work / 'target'),
           'RUSTC': str(BIN / 'rustc'), 'RUSTDOC': str(BIN / 'rustdoc'),
           'TMPDIR': str(work / 'tmp'), 'LANG': 'en_US.UTF-8', 'CARGO_BUILD_JOBS': '2',
           'CARGO_NET_OFFLINE': 'true', 'CARGO_TERM_COLOR': 'never'}
    versions = {name: {'sha256': sha(BIN / name), 'version': subprocess.check_output([str(BIN / name), '--version', '--verbose'], env=env, text=True)} for name in ['cargo', 'rustc']}
    pin = json.loads((HERE / 'sources/local-pins.json').read_text())['tools']['cargo']
    assert versions['cargo']['sha256'] == pin['sha256']
    assert '344c4567c634a25837e3c3476aac08af84cf9203' in versions['cargo']['version']
    rows = []
    def state():
        return {'lockSha256': sha(project / 'Cargo.lock'), 'inputSha256': sha(project / 'input.txt'),
                'inputText': (project / 'input.txt').read_text().strip(),
                'buildScriptSha256': sha(project / 'library/build.rs'),
                'declaresInput': 'rerun-if-changed=../input.txt' in (project / 'library/build.rs').read_text(),
                'sideEffectSha256': sha(project / 'script-side-effect.txt'), 'targetExists': (work / 'target').exists()}
    def command(label, args, direct=False):
        argv = args if direct else [str(BIN / 'cargo'), *args, '--offline']
        before = state()
        start = time.monotonic()
        result = subprocess.run(argv, cwd=project, env=env, capture_output=True, timeout=90)
        (run / (label + '.stdout')).write_bytes(result.stdout)
        (run / (label + '.stderr')).write_bytes(result.stderr)
        feature = ('graph-inspection' if label == 'metadata' else 'artifact-cleanup' if label == 'clean'
                   else 'execution-tests' if direct else 'freshness' if 'input' in label else 'build-units')
        rows.append({'v': 2, 'app': 'cargo', 'feature': 'cargo.' + feature, 'operationId': label,
                     'profile': 'cargo-1.92-darwin-arm64-offline-path-workspace', 'target': str(project),
                     'basis': str(len(rows)), 'request': {'argv': argv},
                     'observed': {'before': before, 'after': state(), 'seconds': time.monotonic() - start,
                                  'stdoutSha256': hashlib.sha256(result.stdout).hexdigest(),
                                  'stderrSha256': hashlib.sha256(result.stderr).hexdigest()},
                     'outcome': {'exitCode': result.returncode}})
        (run / 'trace.json').write_text(json.dumps(rows, indent=2) + '\n')
        assert result.returncode == 0, (label, result.stderr.decode(errors='replace'))
        return result.stdout
    def app(label):
        command(label + '-build', ['build', '-p', 'fixture-app', '--message-format=json'])
        return json.loads(command(label + '-run', [str(work / 'target/debug/fixture-app')], direct=True))
    try:
        metadata = json.loads(command('metadata', ['metadata', '--format-version=1']))
        lib_id = next(p['id'] for p in metadata['packages'] if p['name'] == 'fixture-library')
        features = next(n['features'] for n in metadata['resolve']['nodes'] if n['id'] == lib_id)
        assert features == ['blue', 'red'], features
        lock = sha(project / 'Cargo.lock')
        red = app('red')
        assert red == {'red': True, 'blue': False, 'input': 'first'}, red
        command('workspace-build', ['build', '--workspace', '--message-format=json'])
        union = json.loads(command('workspace-run', [str(work / 'target/debug/fixture-app')], direct=True))
        assert union == {'red': True, 'blue': True, 'input': 'first'}, union
        red_again = app('red-again')
        assert red_again == red
        write('input.txt', 'second\n')
        stale = app('undeclared-input')
        assert stale == red, stale
        events = [json.loads(s) for s in (run / 'undeclared-input-build.stdout').read_text().splitlines()]
        artifacts = [e for e in events if e['reason'] == 'compiler-artifact']
        assert artifacts and all(e['fresh'] for e in artifacts)
        write('library/build.rs', script.replace('    let value', '    println!("cargo::rerun-if-changed=../input.txt");\n    let value'))
        declared = app('declared-input')
        assert declared['input'] == 'second', declared
        write('input.txt', 'third\n')
        changed = app('declared-input-change')
        assert changed['input'] == 'third', changed
        assert sha(project / 'Cargo.lock') == lock
        before_clean = state()
        command('clean', ['clean'])
        assert not (work / 'target').exists()
        assert state()['sideEffectSha256'] == before_clean['sideEffectSha256']
        findings = {'schema': 1, 'metadataLibraryFeatures': features, 'appOnly': red,
                    'workspaceApp': union, 'appOnlyAgain': red_again,
                    'undeclaredInput': stale, 'declaredInput': declared, 'declaredChangedInput': changed,
                    'lockStableAcrossBuilds': True, 'coldMetadataCreatedLock': rows[0]['observed']['before']['lockSha256'] is None and lock is not None,
                    'allCompilerArtifactsFreshWithUndeclaredChange': True,
                    'cleanRemovedTargetButKeptScriptSideEffect': True,
                    'limits': ['Three local packages; no registry, cross-compilation, build-dependency feature split, unsafe environment, or concurrent cargo process.',
                               'The fixture intentionally violates input/output guidance before the corrected-input phase.',
                               'Observed fresh flags are not a proof that every build input was declared.']}
        (run / 'findings.json').write_text(json.dumps(findings, indent=2) + '\n')
        (run / 'receipt.json').write_text(json.dumps({'schema': 1, 'entrypointSha256': sha(Path(__file__)),
            'tools': versions, 'platform': platform.platform(), 'architecture': platform.machine(),
            'workOriginalPath': str(work), 'workRetainedAs': 'work', 'ancestryConfigAbsent': True,
            'environment': env, 'commands': len(rows)}, indent=2) + '\n')
        print(json.dumps({'run': str(run), 'findings': findings}, indent=2))
    finally:
        shutil.move(str(work), str(run / 'work'))


if __name__ == '__main__':
    main()
