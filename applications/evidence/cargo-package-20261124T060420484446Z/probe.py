#!/usr/bin/env python3
"""Owner-run, offline Cargo package fixtures; no registry or external source."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = Path(__file__).read_bytes()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def main():
    pin = json.loads((ROOT / 'applications/sources/local-pins.json').read_text())['tools']['cargo']
    cargo = Path(pin['path']); assert sha(cargo) == pin['sha256']
    run = ROOT / 'applications/evidence' / ('cargo-package-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir(); (run / 'probe.py').write_bytes(PRODUCER)
    work = Path(tempfile.mkdtemp(prefix='rules-cargo-package-', dir='/private/tmp'))
    for parent in [work, *work.parents]:
        assert not any((parent / '.cargo' / name).exists() for name in ['config', 'config.toml'])
    rows, cases = [], []
    env = {'PATH': str(cargo.parent) + ':/usr/bin:/bin', 'HOME': str(work / 'home'),
        'CARGO_HOME': str(work / 'cargo-home'), 'TMPDIR': str(work / 'tmp'),
        'RUSTC': str(cargo.parent / 'rustc'), 'RUSTDOC': str(cargo.parent / 'rustdoc'),
        'CARGO_NET_OFFLINE': 'true', 'CARGO_TERM_COLOR': 'never', 'CARGO_BUILD_JOBS': '1',
        'LANG': 'en_US.UTF-8', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'}
    for name in ['home', 'cargo-home', 'tmp', 'hooks']: (work / name).mkdir()
    versions = {name: {'sha256': sha(cargo.parent / name), 'version': subprocess.check_output([str(cargo.parent / name), '--version', '--verbose'], env=env, text=True)} for name in ['cargo', 'rustc']}
    assert '344c4567c634a25837e3c3476aac08af84cf9203' in versions['cargo']['version']
    policies = [('default', ''), ('exclude', 'exclude=["data/drop.txt"]\n'),
        ('include', 'include=["src/**","data/keep.txt","ignored.txt"]\n'),
        ('both', 'include=["src/**","data/keep.txt","ignored.txt"]\nexclude=["data/keep.txt"]\n'),
        ('invalid-source', '')]
    try:
        for case, policy in policies:
            base = work / case; project = base / 'project'; project.mkdir(parents=True)
            env['CARGO_TARGET_DIR'] = str(base / 'target')
            contents = {'Cargo.toml': '[package]\nname="fixture-package"\nversion="0.1.0"\nedition="2021"\npublish=false\nlicense-file="LICENSE.txt"\nreadme="README.md"\n' + policy,
                'src/lib.rs': 'this is deliberately not valid Rust\n' if case == 'invalid-source' else 'pub fn answer() -> u32 { 42 }\n',
                'data/keep.txt': 'keep fixture\n', 'data/drop.txt': 'drop fixture\n', 'ignored.txt': 'harmless ignored fixture\n',
                'README.md': 'Generated private fixture.\n', 'LICENSE.txt': 'Generated study fixture.\n',
                '.gitignore': 'ignored.txt\ntarget/\n', 'target/never.txt': 'must not ship\n',
                'nested/Cargo.toml': '[package]\nname="nested-fixture"\nversion="0.1.0"\nedition="2021"\n',
                'nested/src/lib.rs': 'pub fn nested() {}\n'}
            for name, data in contents.items():
                path = project / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(data)
            git = ['/usr/bin/git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'core.hooksPath=' + str(work / 'hooks'), '-c', 'commit.gpgsign=false']
            for args in [['init', '--quiet', '--template='], ['add', '.'], ['commit', '--quiet', '-m', 'fixture']]:
                subprocess.run(git + args, cwd=project, env=env, check=True, capture_output=True, timeout=15)
            inputs = {name: sha(project / name) for name in contents}
            (run / (case + '-Cargo.toml')).write_bytes((project / 'Cargo.toml').read_bytes())
            (run / (case + '-lib.rs')).write_bytes((project / 'src/lib.rs').read_bytes())
            archive = base / 'target/package/fixture-package-0.1.0.crate'
            def state():
                return {'inputsSha256': {name: sha(project / name) for name in contents},
                    'lockSha256': sha(project / 'Cargo.lock'), 'archiveSha256': sha(archive)}
            def command(label, flags):
                argv = [str(cargo), 'package', '--offline', '--allow-dirty', *flags]
                before = state(); began = time.monotonic()
                child = subprocess.Popen(argv, cwd=project, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
                timed_out = False
                try: out, err = child.communicate(input=b'', timeout=60)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    try: os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    out, err = child.communicate()
                stem = case + '-' + label
                (run / (stem + '.stdout')).write_bytes(out); (run / (stem + '.stderr')).write_bytes(err)
                inventory = None
                if archive.exists():
                    shutil.copyfile(archive, run / (stem + '.crate'))
                    inventory = []
                    with tarfile.open(archive, 'r:gz') as tar:
                        for entry in tar:
                            assert entry.isfile() and entry.name.startswith('fixture-package-0.1.0/')
                            name = entry.name.removeprefix('fixture-package-0.1.0/')
                            assert '..' not in Path(name).parts
                            data = tar.extractfile(entry).read()
                            inventory.append({'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'text': data.decode('utf-8')})
                row = {'app': 'cargo', 'case': case, 'operation': label, 'argv': argv,
                    'observed': {'before': before, 'after': state(), 'archiveEntries': inventory, 'seconds': time.monotonic() - began,
                        'stdoutSha256': hashlib.sha256(out).hexdigest(), 'stderrSha256': hashlib.sha256(err).hexdigest()},
                    'outcome': {'exitCode': child.returncode, 'timedOut': timed_out}}
                rows.append(row); (run / 'trace.json').write_text(json.dumps(rows, indent=2) + '\n')
                assert row['observed']['after']['inputsSha256'] == inputs, 'Original source inputs changed.'
                if timed_out: raise RuntimeError('Owned command timed out and retired; preserve records before retry.')
                return row
            if case != 'invalid-source':
                command('list', ['--list']); command('unchecked', ['--no-verify'])
                if case == 'default':
                    command('verified', []); command('without-lock', ['--no-verify', '--exclude-lockfile'])
            else:
                command('verification-fails', []); command('unchecked', ['--no-verify'])
            cases.append({'id': case, 'manifest': contents['Cargo.toml'], 'inputsSha256': inputs})
        (run / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
        receipt = {'schema': 1, 'producerSha256': hashlib.sha256(PRODUCER).hexdigest(), 'platform': platform.platform(), 'architecture': platform.machine(),
            'tools': versions, 'cargoPin': pin, 'commands': len(rows), 'cases': len(cases), 'originalWork': str(work),
            'scope': 'Generated no-dependency private Git crates; offline local archive listing/creation and one tiny successful/failed verification. No registry, third-party source, external project, or publication.',
            'limits': ['No general glob/gitignore implementation, registry/credential path, workspace packages, dependency rewrite, symlink/native-platform or reproducible build qualification.',
                'Only original named input hashes are checked; logs/cache/lock/target changes are independently scoped. Cargo verification is a selected build, not exhaustive runtime/testing evidence.']}
        (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'run': str(run), 'commands': len(rows), 'summary': [{'case': r['case'], 'operation': r['operation'], 'exit': r['outcome']['exitCode'], 'archivePresent': r['observed']['after']['archiveSha256'] is not None, 'entries': len(r['observed']['archiveEntries'] or [])} for r in rows]}, indent=2))
    finally:
        shutil.move(str(work), str(run / 'work'))


if __name__ == '__main__': main()
