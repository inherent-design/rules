"""Owner-run offline test target/harness evidence from one disposable package."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    pin = json.loads((ROOT / 'applications/sources/local-pins.json').read_text())['tools']['cargo']
    cargo = Path(pin['path'])
    assert sha(cargo) == pin['sha256']
    bins = cargo.parent
    ledger = ROOT / 'applications/sources/cargo-testing-selections.json'
    for item in json.loads(ledger.read_text()):
        assert sha(ROOT / item['cache']) == item['sha256']
    run = ROOT / 'applications/evidence' / ('cargo-testing-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    (run / 'probe.py').write_bytes(Path(__file__).read_bytes())
    work = Path(tempfile.mkdtemp(prefix='rules-cargo-testing-', dir='/private/tmp'))
    for parent in [work, *work.parents]:
        assert not any((parent / '.cargo' / name).exists() for name in ['config', 'config.toml'])
    for name in ['home', 'cargo-home', 'tmp', 'project/src', 'project/tests', 'project/examples', 'traces']:
        (work / name).mkdir(parents=True, exist_ok=True)
    project = work / 'project'
    env = dict(PATH=str(bins) + ':/usr/bin:/bin', HOME=str(work / 'home'), CARGO_HOME=str(work / 'cargo-home'),
               CARGO_TARGET_DIR=str(work / 'target'), RUSTC=str(bins / 'rustc'), RUSTDOC=str(bins / 'rustdoc'),
               TMPDIR=str(work / 'tmp'), LANG='en_US.UTF-8', CARGO_BUILD_JOBS='2', CARGO_INCREMENTAL='0',
               CARGO_NET_OFFLINE='true', CARGO_TERM_COLOR='never')
    tools = {name: dict(path=str(bins / name), sha256=sha(bins / name),
                       version=subprocess.check_output([str(bins / name), '--version', '--verbose'], env=env, text=True))
             for name in ['cargo', 'rustc', 'rustdoc']}
    assert '344c4567c634a25837e3c3476aac08af84cf9203' in tools['cargo']['version']
    sources = {
        'Cargo.toml': '''[package]
name = "fixture-test-contract"
version = "0.1.0"
edition = "2021"
[workspace]
[[test]]
name = "custom"
path = "tests/custom.rs"
harness = false
[profile.dev]
debug = 0
[profile.test]
debug = 0
''',
        'src/lib.rs': '''//! Runnable public API example:
//! ```
//! fixture_test_contract::mark("doc:run");
//! assert_eq!(fixture_test_contract::answer(), 42);
//! ```
//! Compile, but do not execute this body:
//! ```no_run
//! fixture_test_contract::mark("doc:no-run");
//! ```
//! Expected compiler rejection:
//! ```compile_fail
//! let number: u32 = "not a number";
//! ```
//! Deliberately uncompiled example:
//! ```ignore
//! this is not valid Rust;
//! ```
pub fn answer() -> u32 { 42 }
pub fn mark(value: &str) {
    use std::io::Write;
    let path = std::env::var("FIXTURE_TRACE").unwrap();
    let mut file = std::fs::OpenOptions::new().create(true).append(true).open(path).unwrap();
    writeln!(file, "{}", value).unwrap();
}
#[cfg(test)]
mod tests {
    #[test]
    fn a_conditional_failure() {
        super::mark("unit:a");
        assert!(std::env::var("FIXTURE_FAIL_UNIT").unwrap() != "1");
    }
    #[test]
    fn b_public() { super::mark("unit:b"); assert_eq!(super::answer(), 42); }
    #[test]
    #[ignore = "selected only by an explicit harness request"]
    fn c_ignored() { super::mark("unit:ignored"); assert_eq!(super::answer(), 42); }
}
''',
        'tests/a_api.rs': '''#[test]
fn public_api() { fixture_test_contract::mark("integration:a"); assert_eq!(fixture_test_contract::answer(), 42); }
''',
        'tests/b_api.rs': '''#[test]
fn public_api() { fixture_test_contract::mark("integration:b"); assert_eq!(fixture_test_contract::answer(), 42); }
''',
        'tests/custom.rs': '''fn main() {
    fixture_test_contract::mark("custom:main");
    println!("FIXTURE_CUSTOM_ARGS:{}", std::env::args().skip(1).collect::<Vec<_>>().join("|"));
    assert_eq!(fixture_test_contract::answer(), 42);
}
''',
        'examples/demo.rs': '''fn main() { fixture_test_contract::mark("example:main"); }
''',
    }
    for name, text in sources.items():
        (project / name).write_text(text)
    write(run / 'sources.json', sources)
    write(run / 'setup.json', dict(schema=1, work=str(work), environment=env, tools=tools,
          producerSha256=sha(run / 'probe.py'), sourceLedgerSha256=sha(ledger), platform=platform.platform(),
          purpose='Separate target compilation, harness invocation, body execution, filter/ignore policy, and final status.'))
    rows = []
    def command(label, args, expected=0, fail=False):
        trace = work / 'traces' / (label + '.txt')
        current_env = dict(env, FIXTURE_TRACE=str(trace), FIXTURE_FAIL_UNIT='1' if fail else '0')
        before = {p: sha(project / p) for p in sources}
        started = time.monotonic()
        child = subprocess.Popen([str(cargo), '--offline', *args], cwd=project, env=current_env,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 start_new_session=True)
        timed = False
        try:
            out, err = child.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            timed = True
            os.killpg(child.pid, signal.SIGTERM)
            try:
                out, err = child.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                out, err = child.communicate()
        try:
            os.killpg(child.pid, 0)
            absent = False
        except ProcessLookupError:
            absent = True
        for stream, raw in [('stdout', out), ('stderr', err)]:
            (run / (label + '.' + stream)).write_bytes(raw)
        body = trace.read_text().splitlines() if trace.exists() else []
        write(run / (label + '-bodies.json'), body)
        after = {p: sha(project / p) for p in sources}
        row = dict(id=label, argv=[str(cargo), '--offline', *args], failUnit=fail, expectedExit=expected,
                   exitCode=child.returncode, timedOut=timed, processGroupAbsent=absent,
                   seconds=time.monotonic() - started, bodyTrace=body, authoredBefore=before, authoredAfter=after,
                   stdoutSha256=sha(run / (label + '.stdout')), stderrSha256=sha(run / (label + '.stderr')))
        rows.append(row)
        write(run / 'commands.json', rows)
        assert not timed and absent and child.returncode == expected, (label, child.returncode, err[-2000:])
        assert before == after
    try:
        command('metadata', ['metadata', '--no-deps', '--format-version=1'])
        command('compile-only', ['test', '--no-run', '--message-format=json'])
        command('empty-filter', ['test', '--lib', 'nothing_matches', '--', '--test-threads=1'])
        command('selected-unit', ['test', '--lib', 'tests::b_public', '--', '--exact', '--test-threads=1'])
        command('ignored-only', ['test', '--lib', '--', '--ignored', '--test-threads=1'])
        command('custom-filter', ['test', '--test', 'custom', 'nothing_matches'])
        command('default', ['test', '--', '--test-threads=1'])
        command('fail-fast', ['test', '--', '--test-threads=1'], expected=101, fail=True)
        command('continue', ['test', '--no-fail-fast', '--', '--test-threads=1'], expected=101, fail=True)
        command('doctest', ['test', '--doc', '--', '--test-threads=1'])
        command('doctest-no-run-refusal', ['test', '--doc', '--no-run'], expected=101)
        command('all-targets', ['test', '--all-targets', '--', '--test-threads=1'])
        peak = int(subprocess.check_output(['du', '-sk', str(work / 'target')], text=True).split()[0])
        artifacts = []
        for raw in (run / 'compile-only.stdout').read_text().splitlines():
            value = json.loads(raw)
            if value.get('reason') == 'compiler-artifact' and value.get('executable'):
                path = Path(value['executable'])
                assert path.resolve().is_relative_to(work / 'target')
                artifacts.append(dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size, record=value))
        write(run / 'compiled-artifacts.json', artifacts)
        command('clean', ['clean'])
        assert not (work / 'target').exists()
        assert all(sha(Path(t['path'])) == t['sha256'] for t in tools.values())
        ps = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,command='], text=True)
        hits = [line for line in ps.splitlines() if str(work) in line and int(line.split()[0]) not in [os.getpid(), os.getppid()]]
        assert not hits
        write(run / 'receipt.json', dict(schema=1, complete=True, work=str(work), commands=len(rows),
              sourceLedgerSha256=sha(ledger), peakTargetAllocatedKiB=peak, targetCleaned=True,
              workPathProcessMatches=hits, allRecordedGroupsAbsent=True,
              scope='One std-only offline fixture on pinned Cargo/Rust macOS; no empack test execution, benchmark, Windows, registry or general test-validity claim.'))
    except BaseException as error:
        write(run / 'incomplete.json', dict(schema=1, commands=len(rows), work=str(work),
              errorType=type(error).__name__, message=str(error)))
        raise
    print(json.dumps(dict(run=str(run.relative_to(ROOT)), commands=len(rows), peakTargetAllocatedKiB=peak)))


if __name__ == '__main__':
    main()
