#!/usr/bin/env python3
"""Compile selected unchanged channel source, reusing existing dependencies.

No Cargo/engine build, network, real publisher key, instance, or installation.
Release decoding and diagnostic Display are explicit unqualified adapters.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REVISION = '0b4462e3032b4f09230b15329722eabefb7f574c'
PRODUCER = Path(__file__).read_bytes()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    repo = ROOT.parent / 'empack'
    assert subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip() == REVISION
    paths = ['crates/empack-lib/src/engine/release/trust.rs', 'crates/empack-lib/src/engine/release.rs',
             'crates/empack-lib/src/engine/diagnostics.rs']
    sources = {}
    for name in paths:
        data = subprocess.check_output(['git', '-C', str(repo), 'show', REVISION + ':' + name])
        assert data == (repo / name).read_bytes()
        sources[name] = data
    run = ROOT / 'applications/evidence' / ('empack-channels-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'
    for name in ['home', 'tmp']:
        (work / name).mkdir(parents=True)
    (run / 'probe.py').write_bytes(PRODUCER)
    (run / 'driver.rs').write_bytes((HERE / 'channel_oracle.rs').read_bytes())
    parts = []

    def cut(source, start, stop):
        data = sources[source].decode()
        assert data.count(start) == 1 and data.count(stop) == 1, (source, start, stop)
        a, b = data.index(start), data.index(stop)
        assert a < b
        selected = data[a:b]
        parts.append(dict(source=source, startMarker=start, stopMarker=stop,
            firstLine=data[:a].count('\n') + 1, lastLine=data[:b].count('\n') + 1,
            sha256=hashlib.sha256(selected.encode()).hexdigest(), bytes=len(selected.encode())))
        return selected

    trust_path, release_path, diagnostic_path = paths
    trust = sources[trust_path].decode()
    first_stop = '    /// Signature, expected identity, pack and engine compatibility are all checked before use.'
    first = trust[:trust.index(first_stop)]
    parts.append(dict(source=trust_path, firstLine=1, lastLine=trust[:trust.index(first_stop)].count('\n') + 1,
                      sha256=hashlib.sha256(first.encode()).hexdigest(), bytes=len(first.encode())))
    selected_trust = first + cut(trust_path, '    /// Authenticate publisher state for sequence ordering only.', 'fn compatible(')
    selected_trust += cut(trust_path, 'fn compatible(', 'fn check_identity(')
    selected_trust += cut(trust_path, '/// A signed, nonexpiring channel offer.', '    /// Release must satisfy this channel\'s exact identity and envelope bound.')
    selected_trust += '}\n'  # Close the omitted release-selection portion of AuthenticatedChannel.
    (work / 'selected_trust.rs').write_text(selected_trust)
    helpers = cut(release_path, 'pub(super) fn identifier(', 'fn label(')
    helpers += cut(release_path, 'pub(super) fn https(', '#[cfg(test)]')
    release = sources[release_path].decode()
    limit_line, = [line for line in release.splitlines() if line.startswith('pub const MAX_RELEASE_BYTES:')]
    diagnostic = sources[diagnostic_path].decode()
    definitions = diagnostic[:diagnostic.index('// Display is supplemental human context.')]
    parts.append(dict(source=diagnostic_path, firstLine=1, lastLine=definitions.count('\n') + 1,
                      sha256=hashlib.sha256(definitions.encode()).hexdigest(), bytes=len(definitions.encode())))
    constructor = cut(diagnostic_path, '    pub fn new(code:', '    /// Inspect typed causes only;')
    # Keep actual diagnostic fields and constructor. The production Display/error
    # classifier depends on terminal and operation types outside this fixture.
    (work / 'diagnostics.rs').write_text(definitions + '\nimpl std::fmt::Display for Diagnostic {\n'
        'fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result { write!(f, "fixture diagnostic {:?}", self.code) }\n}\n'
        'impl std::error::Error for Diagnostic {}\nimpl Diagnostic {\n' + constructor + '}\n')
    scaffold = 'mod engine {\n#[path=' + json.dumps(str(work / 'diagnostics.rs')) + '] pub mod diagnostics;\n'
    scaffold += 'pub mod release {\nuse anyhow::{Context, Result, ensure};\nuse serde::{Serialize, Deserialize};\n'
    scaffold += 'use sha2::{Digest, Sha256};\nuse std::collections::BTreeSet;\n' + limit_line + '\n'
    scaffold += 'pub struct DecodedRelease;\nimpl DecodedRelease { pub fn decode(_: &[u8]) -> Result<Self> { anyhow::bail!("Release decoding is outside this channel-only fixture") } }\n'
    scaffold += helpers + '\npub mod trust {\n' + selected_trust + '\n}\n}\n}\n'
    scaffold += 'include!(' + json.dumps(str(run / 'driver.rs')) + ');\n'
    (work / 'main.rs').write_text(scaffold)
    deps = repo / 'target/debug/deps'
    libraries = {}
    for name in ['anyhow', 'serde', 'serde_json', 'ed25519_dalek', 'reqwest', 'semver', 'sha2']:
        files = list(deps.glob('lib' + name + '-*.rlib'))
        assert len(files) == 1, (name, 'Ambiguous or unavailable existing dependency artifact.')
        libraries[name] = dict(path=str(files[0]), sha256=sha(files[0]), bytes=files[0].stat().st_size)
    rustc = Path('/Users/zer0cell/.rustup/toolchains/1.99.1-aarch64-apple-darwin/bin/rustc')
    assert rustc.is_file()
    env = dict(PATH=str(rustc.parent) + ':/usr/bin:/bin', HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'), LANG='en_US.UTF-8')
    compiler_version = subprocess.check_output([str(rustc), '-vV'], env=env, text=True)
    rows = []

    def command(name, argv):
        started = time.monotonic()
        child = subprocess.Popen(argv, cwd=work, env=env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timeout = False
        try:
            out, err = child.communicate(timeout=90)
        except subprocess.TimeoutExpired:
            timeout = True
            os.killpg(child.pid, signal.SIGKILL)
            out, err = child.communicate()
        (run / (name + '.stdout')).write_bytes(out)
        (run / (name + '.stderr')).write_bytes(err)
        row = dict(case=name, argv=argv, pid=child.pid, seconds=time.monotonic() - started,
            stdoutSha256=sha(run / (name + '.stdout')), stderrSha256=sha(run / (name + '.stderr')),
            exitCode=child.returncode, timedOut=timeout)
        rows.append(row)
        (run / 'commands.json').write_text(json.dumps(rows, indent=2) + '\n')
        print(name, child.returncode, flush=True)
        assert not timeout
        return child.returncode

    receipt = dict(schema=1, revision=REVISION, sourceSha256={name: hashlib.sha256(data).hexdigest() for name, data in sources.items()},
        sourceSelections=parts, compiler=dict(path=str(rustc), sha256=sha(rustc), version=compiler_version),
        libraries=libraries, dependencyResolutionDirectory=str(deps), cargoLockSha256=sha(repo / 'Cargo.lock'),
        producerSha256=hashlib.sha256(PRODUCER).hexdigest(), driverSha256=sha(run / 'driver.rs'),
        generatedSha256={p.name: sha(p) for p in work.glob('*.rs')}, platform=platform.platform(), architecture=platform.machine(),
        limits=['Selected unchanged engine channel functions with actual signature/URL/JSON/SemVer dependencies; not pure-core or installed CLI/full engine execution.',
            'Release decoding is a rejecting fixture stub; release authentication/acquisition/installation are not executed.',
            'Diagnostic definitions/new constructor are selected source; Display is a fixture adapter and production terminal/error classifier are excluded.',
            'Direct existing library identities recorded; transitive reproducible-build/source correspondence not established.',
            'Fixed public test signing seeds, fictional HTTPS addresses, no network/real keys/root/instance changes.'])
    try:
        binary = work / 'channel-oracle'
        argv = [str(rustc), '--edition=2024', '-C', 'debuginfo=0', '-A', 'dead_code', '-A', 'unused_imports',
                '-L', 'dependency=' + str(deps), str(work / 'main.rs'), '-o', str(binary)]
        for name, item in libraries.items():
            argv += ['--extern', name + '=' + item['path']]
        if command('compile', argv) != 0:
            receipt['disposition'] = 'Excluded build: no oracle observations. Preserve original diagnostics.'
            return
        receipt['binarySha256'] = sha(binary)
        assert command('observe', [str(binary)]) == 0
        observed = [json.loads(line) for line in (run / 'observe.stdout').read_text().splitlines()]
        receipt.update(disposition='Selected source observations completed; no full engine qualification.', records=len(observed),
                       observedSha256=sha(run / 'observe.stdout'))
    finally:
        (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print('capture', run, flush=True)


if __name__ == '__main__':
    main()
