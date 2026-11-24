#!/usr/bin/env python3
"""Owner-run unchanged discovery source methods on private native directories."""
import argparse
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
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--prefix-only', action='store_true')
    options = parser.parse_args()
    assert platform.system() == 'Darwin', 'macOS collection profile only.'
    repo = ROOT.parent / 'empack'
    assert subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip() == REVISION
    ledger = json.loads((ROOT / 'applications/sources/empack-root-state-selections.json').read_text()); sources = {}
    for p in ledger:
        raw = subprocess.check_output(['git', '-C', str(repo), 'show', REVISION + ':' + p['path']])
        assert hashlib.sha256(raw).hexdigest() == p['sha256'] == sha(repo / p['path'])
        sources[p['path']] = raw
    run = ROOT / 'applications/evidence' / ('empack-root-state-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'
    for name in ['home', 'tmp']: (work / name).mkdir(parents=True)
    (run / 'probe.py').write_bytes(PRODUCER)
    (run / 'driver.rs').write_bytes((HERE / 'root_state_oracle.rs').read_bytes())
    selections = []
    def cut(path, start, stop):
        text = sources[path].decode(); assert text.count(start) == text.count(stop) == 1, (path, start, stop)
        a, b = text.index(start), text.index(stop); value = text[a:b]
        selections.append(dict(path=path, start=start, stop=stop, firstLine=text[:a].count('\n') + 1,
            lastLine=text[:b].count('\n') + 1, sha256=hashlib.sha256(value.encode()).hexdigest()))
        return value
    base = 'crates/empack-lib/src/'
    native = base + 'engine/native.rs'; snapshot = base + 'engine/snapshot.rs'
    publication = base + 'engine/publication.rs'; root = base + 'engine/publication/root_state.rs'
    cancel = base + 'application/process_runtime.rs'; io = base + 'engine/io.rs'
    literal = lambda p: json.dumps(str(p), ensure_ascii=False)
    for name, path in [('persistent.rs', base + 'engine/native/persistent.rs'), ('path.rs', 'crates/empack-core/src/path.rs')]:
        (work / name).write_bytes(sources[path])
    text = '#![allow(dead_code,unused_imports)]\nextern crate alloc;\n'
    text += '#[path=' + literal(work / 'path.rs') + ']mod portable_path;\n'
    text += 'mod application {pub mod process_runtime {use anyhow::Result;use std::sync::{Arc,atomic::{AtomicBool,Ordering}};\n'
    text += cut(cancel, '#[derive(Debug, thiserror::Error)]\n#[error("Operation interrupted")]', '\n/// A completed instance runtime')
    text += cut(cancel, '#[derive(Clone, Default)]\npub struct Cancellation', '    pub(crate) async fn cancelled(') + '}\n}}\n'
    text += 'mod engine {mod native {use anyhow::{Result,ensure};use cap_fs_ext::{DirExt,FollowSymlinks,OpenOptionsFollowExt};use cap_std::fs::{Dir,OpenOptions};use std::fs::File;\n'
    text += cut(native, '#[derive(Debug, Clone, Copy, PartialEq, Eq)]\npub(super) struct ObjectIdentity', '\n/// Walk one component')
    text += cut(native, 'pub(super) fn open_file(', '\n/// Linux capability directories')
    text += '#[path=' + literal(work / 'persistent.rs') + ']mod persistent;\n}\n'
    text += 'mod io {\n' + cut(io, 'use crate::application::process_runtime::Cancellation;', '\n#[cfg(test)]') + '\n}\n'
    text += 'mod snapshot {use super::native::{self,ObjectIdentity};use anyhow::{Context,Result,ensure};use cap_fs_ext::DirExt;use cap_std::fs::Dir;use crate::portable_path::{PortableRelPath,PathSyntax};use std::path::{Path,PathBuf};\n'
    text += cut(snapshot, '/// An opened project root grants reads only through this adapter.', '\n    /// Observe only selected managed paths.') + '}\n}\n'
    text += 'pub(crate) mod publication {use super::{native::{self,ObjectIdentity},snapshot::ProjectReadRoot,io::copy_bounded};use crate::application::process_runtime::Cancellation;use anyhow::{Context,Result,ensure};use cap_std::fs::{Dir,OpenOptions};use cap_fs_ext::DirExt;use serde::{Serialize,Deserialize};\n'
    text += cut(publication, '/// Private host state is separate from project data', '\n/// Read-only coordinates for recovery presentation')
    text += cut(publication, '#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]\n#[serde(deny_unknown_fields)]\nstruct Binding', '#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]\n#[serde(deny_unknown_fields)]\nstruct Fingerprint')
    text += cut(publication, 'pub(super) fn root_key(', '\nfn discard_sibling(')
    text += cut(publication, 'fn lock_file(', '\nfn new_retained_file(')
    text += 'pub(crate) mod root_state {\n'
    text += cut(root, 'use super::*;', '\nimpl Publisher {')
    text += 'impl Publisher {\n'
    text += cut(root, '    /// Read-only discovery never creates', '    /// Retain only root identity')
    text += cut(root, '    /// An association\'s opaque original key', '    pub(super) fn associate_project_state(') + '}\n'
    text += 'include!(' + literal(run / 'driver.rs') + ');\n}\n}\n}\n'
    text += 'fn main()->anyhow::Result<()> {let root=std::env::args_os().nth(1).expect("Private fixture root required");engine::publication::root_state::run(std::path::Path::new(&root),std::env::args().nth(2).as_deref()==Some("prefix"))}\n'
    (work / 'main.rs').write_text(text)
    prior = ROOT / 'applications/evidence/empack-identity-20261124T193525996513Z/receipt.json'
    previous = json.loads(prior.read_text()); compiler = previous['compiler']; rustc = Path(compiler['path'])
    assert sha(rustc) == compiler['sha256']
    deps = repo / 'target/debug/deps'
    libraries = dict(previous['libraries'])
    rustc_id = libraries['libc']['rustcFingerprint']
    for name, package, features in [('cap_std', 'cap-std', ['default']), ('cap_fs_ext', 'cap-fs-ext', ['cap-std', 'default', 'std']), ('thiserror', 'thiserror', ['default', 'std'])]:
        candidates = []
        for path in deps.glob('lib' + name + '-*.rlib'):
            tag = package + '-' + path.stem.rsplit('-', 1)[1]
            meta = deps.parent / '.fingerprint' / tag / ('lib-' + name + '.json')
            if not meta.is_file(): continue
            info = json.loads(meta.read_text())
            if info['rustc'] == rustc_id and json.loads(info['features']) == features:
                candidates.append(dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size, fingerprint=str(meta), fingerprintSha256=sha(meta), features=info['features'], rustcFingerprint=rustc_id))
        assert len(candidates) == 1, (name, 'Need one matching existing compiler/feature artifact.')
        libraries[name] = candidates[0]
    for value in libraries.values(): assert sha(Path(value['path'])) == value['sha256']
    env = dict(PATH=str(rustc.parent) + ':/usr/bin:/bin', HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'), LANG='en_US.UTF-8')
    commands = []
    def command(label, argv):
        started = time.monotonic(); child = subprocess.Popen(argv, cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timed_out = False
        try: out, err = child.communicate(timeout=90)
        except subprocess.TimeoutExpired:
            timed_out = True
            try: os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            out, err = child.communicate()
        for name, raw in [('stdout', out), ('stderr', err)]: (run / (label + '.' + name)).write_bytes(raw)
        row = dict(case=label, argv=argv, exitCode=child.returncode, timedOut=timed_out, seconds=time.monotonic()-started,
            stdoutSha256=sha(run / (label + '.stdout')), stderrSha256=sha(run / (label + '.stderr')))
        commands.append(row); (run / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        print(label, row['exitCode'], flush=True); return row
    binary = work / 'discovery-driver'; link_map = work / 'link-map.txt'
    argv = [str(rustc), '--edition=2024', '-Cdebuginfo=0', '-Cstrip=debuginfo', str(work / 'main.rs'), '-Ldependency=' + str(deps)]
    for name, value in libraries.items(): argv += ['--extern', name + '=' + value['path']]
    argv += ['-Clink-arg=-Wl,-map,' + str(link_map), '-o', str(binary)]
    first = command('compile', argv)
    receipt = dict(schema=1, profile='writer-prefix' if options.prefix_only else 'read-only-discovery', revision=REVISION, priorReceipt=str(prior.relative_to(ROOT)), priorReceiptSha256=sha(prior), compiler=compiler, libraries=libraries,
        sourceSelections=selections, sourceSha256={p['path']: p['sha256'] for p in ledger}, cargoLockSha256=sha(repo / 'Cargo.lock'),
        producerSha256=sha(run / 'probe.py'), driverSha256=sha(run / 'driver.rs'), generatedSha256={p.name: sha(p) for p in work.glob('*.rs')},
        platform=platform.platform(), architecture=platform.machine(), commands=commands,
        limits=['Selected unchanged actual methods on private macOS capabilities;no Cargo/full engine build.',
            'Publisher struct,ProjectReadRoot open/selected/check_binding,discovery reader/predicates,cap_std+cap_fs_ext,native open/identity and bounded IO are actual source selections.',
            'Cancellation synchronous source methods included;only fresh uncancelled default is used. Async supervision/full initialization/publication/recovery/continuation are not exercised. Optional prefix-only profile creates/acquires/releases one source operation.lock before discovery;it is not an actual crash or complete writer.',
            'Old-device association fields are synthetic fixture setup;no actual reboot/remount or Linux/Windows provider qualification.',
            'Private fixture associations/journal-named sentinels are authored,not engine-generated operations. They grant no publication/recovery authority.',
            'No live project,operation store,Moment recovery,evidence retention,launcher or game accessed.'])
    (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    assert first['exitCode'] == 0 and not first['timedOut'], 'Retain failed compile before changing fixture.'
    second = command('observed', [str(binary), str(work / 'cases')] + (['prefix'] if options.prefix_only else []))
    receipt.update(binarySha256=sha(binary), binaryBytes=binary.stat().st_size, linkMapSha256=sha(link_map), commands=commands)
    (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    assert second['exitCode'] == 0 and not second['timedOut'], 'Retain failed run before changing fixture.'
    observed = [json.loads(line) for line in (run / 'observed.stdout').read_text().splitlines()]
    assert observed and len({r['id'] for r in observed}) == len(observed)
    for p in ledger: assert sha(repo / p['path']) == p['sha256']
    for lib in libraries.values(): assert sha(Path(lib['path'])) == lib['sha256']
    print(json.dumps(dict(run=str(run), cases=len(observed), nativeCases=sum(not r.get('setupUnavailable', False) for r in observed), binaryBytes=receipt['binaryBytes']), indent=2))


if __name__ == '__main__': main()
