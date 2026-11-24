#!/usr/bin/env python3
"""Owner-run identity/fingerprint source fragments with private files, no engine build."""
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
    assert platform.system() == 'Darwin', 'This acquisition profile is macOS only.'
    repo = ROOT.parent / 'empack'
    assert subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip() == REVISION
    ledger = json.loads((ROOT / 'applications/sources/empack-identity-selections.json').read_text())
    sources = {}
    for row in ledger:
        raw = subprocess.check_output(['git', '-C', str(repo), 'show', REVISION + ':' + row['path']])
        assert hashlib.sha256(raw).hexdigest() == row['sha256'] == sha(repo / row['path'])
        sources[row['path']] = raw
    run = ROOT / 'applications/evidence' / ('empack-identity-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'
    for name in ['home', 'tmp']: (work / name).mkdir(parents=True)
    (run / 'probe.py').write_bytes(PRODUCER)
    (run / 'driver.rs').write_bytes((HERE / 'identity_oracle.rs').read_bytes())
    selections = []
    def cut(path, start, stop):
        text = sources[path].decode()
        assert text.count(start) == 1 and text.count(stop) == 1, (path, start, stop)
        begin, end = text.index(start), text.index(stop)
        result = text[begin:end]
        selections.append(dict(path=path, start=start, stop=stop, firstLine=text[:begin].count('\n') + 1,
            lastLine=text[:end].count('\n') + 1, sha256=hashlib.sha256(result.encode()).hexdigest()))
        return result
    native_path = 'crates/empack-lib/src/engine/native.rs'
    snapshot_path = 'crates/empack-lib/src/engine/snapshot.rs'
    publication_path = 'crates/empack-lib/src/engine/publication.rs'
    root_path = 'crates/empack-lib/src/engine/publication/root_state.rs'
    native = cut(native_path, '#[derive(Debug, Clone, Copy, PartialEq, Eq)]\npub(super) struct ObjectIdentity', '\npub(super) fn directory_identity(')
    observation_types = cut(snapshot_path, '/// Observed bytes, including raw document bytes.', '#[derive(Debug)]\npub(super) struct CaptureGroup')
    snapshot_type = cut(snapshot_path, '/// Immutable native evidence bound to one retained project root.', '\nimpl NativeSnapshot {')
    fingerprint = cut(snapshot_path, '    /// Persisted comparison data only.', '    /// Filtered directory membership')
    binding = cut(publication_path, '#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]\n#[serde(deny_unknown_fields)]\nstruct Binding', '#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]\n#[serde(deny_unknown_fields)]\nstruct Fingerprint')
    binding_key = cut(publication_path, 'fn binding_key(', '\nfn discard_sibling(')
    association = cut(root_path, '#[derive(Serialize, Deserialize)]', '\nfn read(')
    association_matches = cut(root_path, 'fn matches(', '\nimpl Publisher {')
    persistent_path = 'crates/empack-lib/src/engine/native/persistent.rs'
    journal_path = 'crates/empack-lib/src/engine/publication/journal_identity.rs'
    path_path = 'crates/empack-core/src/path.rs'
    (work / 'persistent.rs').write_bytes(sources[persistent_path] + b'\npub(super) fn fixture_error(errno:i32)->anyhow::Result<Option<[u8;32]>>{unsupported_or_error(std::io::Error::from_raw_os_error(errno))}\n')
    (work / 'journal_identity.rs').write_bytes(sources[journal_path])
    (work / 'path.rs').write_bytes(sources[path_path])
    literal = lambda p: json.dumps(str(p), ensure_ascii=False)
    scaffold = '#![allow(dead_code,unused_imports)]\nextern crate alloc;\n'
    scaffold += '#[path=' + literal(work / 'path.rs') + ']mod portable_path;\nmod engine {\n'
    scaffold += 'mod native {use anyhow::{Result,ensure};use std::fs::File;\n' + native
    scaffold += '#[path=' + literal(work / 'persistent.rs') + ']mod persistent;\n'
    scaffold += '''
pub(super) fn retokenize(file:&File,mut observed:ObjectIdentity,field:&str)->Result<ObjectIdentity>{
 match field {"volume"=>observed.volume^=1,"object"=>observed.object^=1,
 "created"=>{if let Some((s,n))=observed.created{observed.created=Some((s,n^1));}},
 "missing-created"=>observed.created=None,_=>anyhow::bail!("Unknown fixture perturbation")}
 observed.persistent=persistent::identity(file,&observed)?;Ok(observed)
}
pub(super) fn injected_error(errno:i32)->Result<Option<[u8;32]>>{persistent::fixture_error(errno)}
}\nmod publication {
use super::native::ObjectIdentity;use anyhow::{Context,Result,ensure};use serde::{Serialize,Deserialize};
'''
    scaffold += '#[path=' + literal(work / 'journal_identity.rs') + ']mod journal_identity;\n'
    scaffold += binding + binding_key + association
    scaffold += 'struct ProjectReadRoot {binding:ObjectIdentity}\n' + association_matches
    scaffold += '''
pub(super) fn journal_result(saved:Option<ObjectIdentity>,observed:Option<ObjectIdentity>)->serde_json::Value{
 let saved=match saved.map(journal_identity::JournalBinding::capture).transpose(){Ok(v)=>v,
 Err(e)=>return serde_json::json!({"captureOk":false,"matches":null,"error":format!("{e:#}")})};
 serde_json::json!({"captureOk":true,"matches":journal_identity::matches_optional(saved.as_ref(),observed),"error":null})
}
pub(super) fn wire(object:ObjectIdentity)->Result<Vec<u8>>{Ok(serde_json::to_vec(&journal_identity::JournalBinding::capture(object)?)?)}
pub(super) fn decode(wire:&[u8])->serde_json::Value{
 match serde_json::from_slice::<journal_identity::JournalBinding>(wire){Ok(v)=>serde_json::json!({"accepted":true,"value":v}),
 Err(e)=>serde_json::json!({"accepted":false,"error":e.to_string()})}
}
pub(super) fn key(object:ObjectIdentity)->Result<String>{binding_key(&object.into())}
pub(super) fn association_result(saved:ObjectIdentity,observed:ObjectIdentity,wrong_name:bool)->Result<serde_json::Value>{
 let record=Association{schema:1,persistent:saved.persistent.context("Fixture saved identity unavailable")?,original:saved.into()};
 let original=key(saved)?;let selected=if wrong_name{format!("{original}-wrong")}else{original.clone()};
 let verdict=matches(&record,&selected,&ProjectReadRoot{binding:observed});
 Ok(serde_json::json!({"record":record,"name":selected,"currentKey":key(observed).ok(),
 "matched":verdict.as_ref().ok(),"error":verdict.err().map(|e|format!("{e:#}"))}))
}
}\n pub(crate) mod snapshot {
use super::native::{self,ObjectIdentity};use super::publication;
use crate::portable_path::{PortableRelPath,PathSyntax};use anyhow::{Result,Context,ensure};
use std::collections::{BTreeMap,BTreeSet};use std::fs::{self,File};
use std::io::{Read,Seek,SeekFrom};use std::path::Path;use std::os::unix::fs::PermissionsExt;
use sha2::{Digest,Sha256};use serde_json::{Value,json};
'''
    scaffold += observation_types + '#[derive(Debug)]struct CaptureGroup;\n' + snapshot_type
    scaffold += 'impl NativeSnapshot {\n' + fingerprint + '}\n'
    scaffold += 'include!(' + literal(run / 'driver.rs') + ');\n}\n}\n'
    scaffold += 'fn main()->anyhow::Result<()>{let root=std::env::args_os().nth(1).context("Supply owned fixture root")?;engine::snapshot::run(std::path::Path::new(&root))}\nuse anyhow::Context;\n'
    (work / 'main.rs').write_text(scaffold)
    previous = json.loads((ROOT / 'applications/evidence/empack-channels-20261124T133716623327Z/receipt.json').read_text())
    compiler = previous['compiler']; rustc = Path(compiler['path']); assert sha(rustc) == compiler['sha256']
    deps = repo / 'target/debug/deps'
    libraries = {n: previous['libraries'][n] for n in ['anyhow', 'serde', 'serde_json', 'sha2']}
    for value in libraries.values(): assert sha(Path(value['path'])) == value['sha256']
    # Select explicitly by recorded feature/compiler profile, not filename age.
    candidates = []
    rustc_id = json.loads((deps.parent / '.fingerprint/sha2-fb3e67ad47f9ad90/lib-sha2.json').read_text())['rustc']
    for path in deps.glob('liblibc-*.rlib'):
        tag = path.stem.removeprefix('lib'); meta = deps.parent / '.fingerprint' / tag / 'lib-libc.json'
        if not meta.is_file(): continue
        info = json.loads(meta.read_text())
        if info['rustc'] == rustc_id and json.loads(info['features']) == ['default', 'extra_traits', 'std']:
            candidates.append(dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size,
                fingerprint=str(meta), fingerprintSha256=sha(meta), features=info['features'], rustcFingerprint=rustc_id))
    assert len(candidates) == 1, 'Need an unambiguous attributed libc artifact.'
    libraries['libc'] = candidates[0]
    env = dict(PATH=str(rustc.parent) + ':/usr/bin:/bin', HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'), LANG='en_US.UTF-8')
    rows = []
    def command(label, argv):
        started = time.monotonic(); child = subprocess.Popen(argv, cwd=work, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timed_out = False
        try: out, err = child.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            timed_out = True
            try: os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            out, err = child.communicate()
        for stream, payload in [('stdout', out), ('stderr', err)]: (run / (label + '.' + stream)).write_bytes(payload)
        row = dict(case=label, argv=argv, exitCode=child.returncode, timedOut=timed_out, seconds=time.monotonic()-started,
            stdoutSha256=sha(run/(label+'.stdout')), stderrSha256=sha(run/(label+'.stderr')))
        rows.append(row); (run/'commands.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(label, child.returncode, flush=True)
        return row
    binary = work / 'identity-driver'
    compile_argv = [str(rustc), '--edition=2024', '-Cdebuginfo=0', '-Cstrip=debuginfo', str(work/'main.rs'), '-Ldependency='+str(deps)]
    for name, value in libraries.items(): compile_argv += ['--extern', name+'='+value['path']]
    compile_argv += ['-o', str(binary)]
    first = command('compile', compile_argv)
    receipt = dict(schema=1, revision=REVISION, compiler=compiler, libraries=libraries, sourceSelections=selections,
        sourceSha256={p['path']:p['sha256']for p in ledger}, cargoLockSha256=sha(repo/'Cargo.lock'),
        producerSha256=sha(run/'probe.py'), driverSha256=sha(run/'driver.rs'),
        generatedSha256={p.name:sha(p)for p in work.glob('*.rs')}, platform=platform.platform(), architecture=platform.machine(),
        limits=['Selected unchanged source functions/types with existing dependencies; no Cargo or full engine build.',
            'Native macOS files/FFI plus explicitly marked synthetic field and errno inputs; no actual reboot or Linux/Windows execution.',
            'Snapshot entries are assembled by fixture,with unused CaptureGroup marker. Capture/scopes/filtering/revalidation/write authority are not executed.',
            'Association matches uses a binding-only root adapter and valid schema1 typed record; real discovery/schema read/locks/state migration are excluded.',
            'No actual user project,state/operation store,retained production journal,publication,installation,creation or recovery is accessed.'])
    (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    assert not first['timedOut'] and first['exitCode']==0, 'Retain failed compile before changing the fixture.'
    second = command('observed', [str(binary), str(work/'native-files')])
    receipt['binarySha256'] = sha(binary); receipt['binaryBytes'] = binary.stat().st_size
    receipt['commands'] = rows
    (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    assert not second['timedOut'] and second['exitCode']==0, 'Retain failed execution before changing the fixture.'
    observed = [json.loads(line)for line in (run/'observed.stdout').read_text().splitlines()]
    assert observed and len({r['id']for r in observed})==len(observed)
    for row in ledger: assert sha(repo/row['path'])==row['sha256']
    for value in libraries.values(): assert sha(Path(value['path']))==value['sha256']
    print(json.dumps(dict(run=str(run),cases=len(observed),binaryBytes=receipt['binaryBytes']),indent=2))


if __name__=='__main__': main()
