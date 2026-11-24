#!/usr/bin/env python3
"""Owner-run association initializer/termination study on private native fixtures."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import selectors
import signal
import subprocess
import time

from root_state_observations import image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REV = '0b4462e3032b4f09230b15329722eabefb7f574c'
PRODUCER = Path(__file__).read_bytes()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert platform.system() == 'Darwin', 'Selected macOS profile only.'
    repo = ROOT.parent / 'empack'
    assert subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip() == REV
    ledger = json.loads((ROOT / 'applications/sources/empack-initializer-selections.json').read_text()); sources = {}
    for pin in ledger:
        raw = subprocess.check_output(['git', '-C', str(repo), 'show', REV + ':' + pin['path']])
        assert hashlib.sha256(raw).hexdigest() == pin['sha256'] == sha(repo / pin['path'])
        sources[pin['path']] = raw.decode()
    previous = ROOT / 'applications/evidence/empack-root-state-20261124T201907525187Z'
    old = json.loads((previous / 'receipt.json').read_text()); scaffold = previous / 'work/main.rs'
    assert sha(scaffold) == old['generatedSha256']['main.rs']
    run = ROOT / 'applications/evidence' / ('empack-initializer-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'
    for name in ['home', 'tmp', 'fixtures']: (work / name).mkdir(parents=True)
    (run / 'images').mkdir(); (run / 'probe.py').write_bytes(PRODUCER); (run / 'driver.rs').write_bytes((HERE / 'initializer_oracle.rs').read_bytes())
    selections = []
    def cut(path, start, stop):
        text = sources[path]; assert text.count(start) == text.count(stop) == 1, (path, start, stop)
        a, b = text.index(start), text.index(stop); value = text[a:b]
        selections.append(dict(path=path, start=start, stop=stop, sha256=hashlib.sha256(value.encode()).hexdigest()))
        return value
    base = 'crates/empack-lib/src/engine/'
    pub, native, staging, state = [base + p for p in ['publication.rs', 'native.rs', 'staging.rs', 'publication/root_state.rs']]
    parent = scaffold.read_text().split('pub(crate) mod root_state {')[0]
    # Old scaffold contains exact, attributed read/root/lock primitives. Add the
    # real readable-directory function;only the wrapper module name changes.
    insertion = cut(native, '#[cfg(unix)]\npub(super) fn readable_directory(', '\n#[cfg(all(test, unix))]')
    anchor = '#[path=' + json.dumps(str(previous / 'work/persistent.rs')) + ']mod persistent;'
    assert parent.count(anchor) == 1; parent = parent.replace(anchor, insertion + '\n' + anchor)
    assert parent.count('mod instance_runtime {') == 1
    parent = parent.replace('mod instance_runtime {', 'mod actual_instance_runtime {')
    parent += '''
use std::{io::Write,sync::atomic::{AtomicU64,Ordering}};
use cap_fs_ext::{FollowSymlinks,OpenOptionsFollowExt};
const JOURNAL_LIMIT:u64=16*1024*1024;
static NEXT_TEMP:AtomicU64=AtomicU64::new(0);
fn fixture_phase(name:&str)->Result<()> {
 if std::env::args().nth(3).as_deref()==Some(name) {
  println!("{}",serde_json::json!({"event":"phase","phase":name,"pid":std::process::id()}));
  std::io::stdout().flush()?;let mut answer=[0u8];
  std::io::Read::read_exact(&mut std::io::stdin(),&mut answer)?;
  ensure!(answer[0]==b'C',"Fixture phase not resumed");
 }
 Ok(())
}
// Instrumentation delegates the actual predicate before a controlled pause.
mod instance_runtime {use super::*;pub(super) fn ensure_stopped(state:&Dir)->Result<()> {
 actual_instance_runtime::ensure_stopped(state)?;fixture_phase("locked")
}}
// Proposed metadata-only coordination;not a production implementation.
fn association_lock(state:&Dir)->Result<File> {
 let file=lock_file(state,"state.lock")?;
 file.try_lock().context("Native root association initialization is busy")?;
 instance_runtime::ensure_stopped(state)?;Ok(file)
}
'''
    parent += cut(pub, 'fn private_directory(', '\nfn lock(directory:')
    parent += cut(pub, 'fn sync_directory(', '\nfn write_journal(')
    parent += cut(pub, 'fn write_record(', '\nfn load_journal(')
    parent += cut(staging, 'pub(super) fn create_temporary(', '\n/// Private seekable scratch storage')
    parent += 'impl Publisher {\n' + cut(pub, '    fn project_state(', '\n}\n\nfn candidate_name(') + '\n}\n'
    root_source = sources[state]
    old_call = 'let _lock = lock(state)?;'; new_call = 'let _lock = association_lock(state)?;'
    assert root_source.count(old_call) == 1
    variants = {'current': root_source, 'candidate': root_source.replace(old_call, new_call)}
    binaries = {}
    for name, body in variants.items():
        code = parent + 'pub(crate) mod root_state {\n' + body + '\ninclude!(' + json.dumps(str(run / 'driver.rs')) + ');\n}\n}\n}\n'
        code += 'fn main()->anyhow::Result<()>{let base=std::env::args_os().nth(1).expect("Private root required");let mode=std::env::args().nth(2).unwrap();engine::publication::root_state::run(std::path::Path::new(&base),&mode)}\n'
        (work / (name + '.rs')).write_text(code); binaries[name] = work / (name + '-initializer')
    rustc = Path(old['compiler']['path']); assert sha(rustc) == old['compiler']['sha256']
    for a in old['libraries'].values(): assert sha(Path(a['path'])) == a['sha256']
    env = dict(PATH=str(rustc.parent) + ':/usr/bin:/bin', HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'), LANG='en_US.UTF-8')
    commands, cases = [], []
    def finish(label, proc, prefix=b'', interrupted=False):
        timed_out = False
        try: out, err = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            timed_out = True
            try: os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            out, err = proc.communicate()
        out = prefix + out
        for stream, raw in [('stdout', out), ('stderr', err)]: (run / (label + '.' + stream)).write_bytes(raw)
        group_absent = None
        try: os.killpg(proc.pid, 0)
        except ProcessLookupError: group_absent = True
        else: group_absent = False
        row = dict(label=label, pid=proc.pid, argv=proc.args, exitCode=proc.returncode, timedOut=timed_out, intentionalKill=interrupted,
            ownedGroupAbsent=group_absent, stdoutSha256=sha(run / (label + '.stdout')), stderrSha256=sha(run / (label + '.stderr')))
        commands.append(row); (run / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        assert not timed_out and group_absent, label
        return row, [json.loads(l) for l in out.splitlines()] if not label.startswith('compile') else []
    for name, binary in binaries.items():
        argv = [str(rustc), '--edition=2024', '-Cdebuginfo=0', '-Cstrip=debuginfo', str(work / (name + '.rs')), '-Ldependency=' + str(repo / 'target/debug/deps')]
        for lib, value in old['libraries'].items(): argv += ['--extern', lib + '=' + value['path']]
        argv += ['-o', str(binary)]
        proc = subprocess.Popen(argv, cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        result, _ = finish('compile-' + name, proc)
        print(result['label'], result['exitCode'], flush=True)
        if result['exitCode'] != 0: break
    receipt = dict(schema=1, sourceRevision=REV, scaffold=str(scaffold.relative_to(ROOT)), scaffoldSha256=sha(scaffold),
        scaffoldReceipt=str((previous / 'receipt.json').relative_to(ROOT)), scaffoldReceiptSha256=sha(previous / 'receipt.json'),
        sourceSha256={p['path']: p['sha256'] for p in ledger}, sourceSelections=selections, compiler=old['compiler'], libraries=old['libraries'],
        producerSha256=sha(run / 'probe.py'), driverSha256=sha(run / 'driver.rs'), generatedSha256={p.name: sha(p) for p in work.glob('*.rs')},
        candidatePatch=dict(path=state, old=old_call, new=new_call, count=1), platform=platform.platform(), commands=commands,
        limits=['Complete selected association initialization chain with supplied host Dir;not Publisher::open,Engine/CLI operation or project publication.',
            'Injected post-lock pause wraps and delegates actual ensure_stopped;completed pause is after successful source method return. SIGKILL is owned child termination,not reboot or power-loss durability.',
            'Candidate copied source changes only association-lock call;new helper uses dedicated state.lock with actual no-follow lock primitive and runtime predicate. No production edits.',
            'All roots and state are disposable private fixtures;no live operation store,user project,Moment recovery,launcher,game or network accessed.'])
    def save():
        receipt.update(commands=commands, cases=cases, binaries={k: dict(path=str(p.relative_to(ROOT)), sha256=sha(p), bytes=p.stat().st_size) for k,p in binaries.items() if p.exists()})
        (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    save(); assert len(commands) == 2 and all(c['exitCode'] == 0 for c in commands), 'Keep failed compile.'
    def fixture(name):
        p = work / 'fixtures' / name; (p / 'project').mkdir(parents=True, mode=0o700); (p / 'host').mkdir(mode=0o700)
        (p / 'project/document.txt').write_bytes(b'unchanged author input')
        return p
    def snapshot(label, p):
        target = run / 'images' / (label + '.json'); target.write_text(json.dumps(image(p), sort_keys=True, separators=(',', ':')))
        return dict(image=str(target.relative_to(run)), sha256=sha(target))
    def invoke(label, variant, p, action='initialize', point=''):
        return subprocess.Popen([str(binaries[variant]), str(p), action, point], cwd=work, env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    def completed(label, variant, p, action='initialize'):
        before = snapshot(label + '-before', p); proc = invoke(label, variant, p, action)
        cmd, rows = finish(label, proc); assert cmd['exitCode'] == 0 and len(rows) == 1 and rows[0]['event'] == 'result', label
        row = dict(label=label, variant=variant, fixture=str(p.relative_to(work)), action=action, before=before,
                   after=snapshot(label + '-after', p), outcome=rows[0]['outcome']); cases.append(row); save(); return row
    def paused(label, variant, p, point):
        before = snapshot(label + '-before', p); proc = invoke(label, variant, p, point=point)
        selector = selectors.DefaultSelector(); selector.register(proc.stdout, selectors.EVENT_READ)
        if not selector.select(timeout=10):
            selector.close(); os.killpg(proc.pid, signal.SIGKILL); finish(label, proc, interrupted=True); save(); raise AssertionError('Missing phase: ' + label)
        ready = proc.stdout.readline(); selector.close(); event = json.loads(ready)
        assert event == dict(event='phase', phase=point, pid=proc.pid) and proc.poll() is None, (label, ready)
        return proc, ready, before
    for variant in ['current', 'candidate']:
        p = fixture(variant + '-normal'); completed(variant + '-normal', variant, p); completed(variant + '-idempotent', variant, p)
        p = fixture(variant + '-locked-interruption')
        label = variant + '-paused'; proc, ready, before = paused(label, variant, p, 'locked')
        during = snapshot(label + '-during', p)
        # A second real process cannot complete while the first owns this phase.
        completed(variant + '-concurrent', variant, p)
        lock_path = next((p / 'host').glob('project-*')) / ('operation.lock' if variant == 'current' else 'state.lock')
        with lock_path.open('r+b') as f:
            try: fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: held = True
            else: held = False; fcntl.flock(f, fcntl.LOCK_UN)
        assert held
        os.killpg(proc.pid, signal.SIGKILL); cmd, rows = finish(label, proc, ready, interrupted=True)
        assert cmd['exitCode'] == -signal.SIGKILL and rows[0]['phase'] == 'locked'
        with lock_path.open('r+b') as f: fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB); fcntl.flock(f, fcntl.LOCK_UN)
        cases.append(dict(label=label, variant=variant, fixture=str(p.relative_to(work)), action='terminated-after-lock',
            before=before, during=during, after=snapshot(label + '-after', p), phase=json.loads(ready), kernelLockHeldBeforeKill=True, kernelLockAvailableAfterKill=True)); save()
        completed(variant + '-after-kill-lookup', variant, p, 'lookup'); completed(variant + '-retry', variant, p)
        p = fixture(variant + '-completed-interruption'); label = variant + '-after-completed'; proc, ready, before = paused(label, variant, p, 'completed')
        os.killpg(proc.pid, signal.SIGKILL); cmd, rows = finish(label, proc, ready, interrupted=True)
        assert cmd['exitCode'] == -signal.SIGKILL
        cases.append(dict(label=label, variant=variant, fixture=str(p.relative_to(work)), action='terminated-after-initializer-return', before=before,
            after=snapshot(label + '-after', p), phase=json.loads(ready))); save()
        completed(variant + '-completed-lookup', variant, p, 'lookup'); completed(variant + '-completed-retry', variant, p)
    # A candidate may read existing published associations without rewriting them.
    completed('candidate-current-interop', 'candidate', work / 'fixtures/current-normal')
    for variant in ['current', 'candidate']:
        p = fixture(variant + '-unknown-state'); lookup = completed(variant + '-key', variant, p, 'lookup'); key = lookup['outcome']['key']
        d = p / 'host' / key; d.mkdir(); (d / 'operation.lock').write_bytes(b''); (d / 'journal.json').write_bytes(b'unknown retained fixture')
        completed(variant + '-unknown-refusal', variant, p)
    save(); print(json.dumps(dict(run=str(run), cases=len(cases), commands=len(commands), binaries=receipt['binaries']), indent=2))


if __name__ == '__main__': main()
