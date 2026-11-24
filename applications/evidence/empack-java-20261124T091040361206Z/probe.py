#!/usr/bin/env python3
"""Reuse an attributed unchanged-core artifact; compile one small policy caller.

No engine build, author project, game, installer, network request, or JDK change.
Selected installed JVM property streams remain private; public observations keep
only the unique Java specification major, process status, and byte identities.
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
PRODUCER = Path(__file__).read_bytes()
REVISION = '0b4462e3032b4f09230b15329722eabefb7f574c'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    repo = ROOT.parent / 'empack'
    assert subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip() == REVISION
    prior = ROOT / 'applications/evidence/empack-projection-20261124T063515339963Z'
    receipt = json.loads((prior / 'receipt.json').read_text())
    assert receipt['revision'] == REVISION
    library = prior / 'work/libempack_core.rlib'
    assert sha(library) == receipt['librarySha256']
    for name, digest in receipt['sourceSha256'].items():
        data = subprocess.check_output(['git', '-C', str(repo), 'show', REVISION + ':' + name])
        assert hashlib.sha256(data).hexdigest() == digest == sha(repo / name)
    run = ROOT / 'applications/evidence' / ('empack-java-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'
    for name in ['home', 'tmp', 'private']:
        (work / name).mkdir(parents=True)
    (run / 'probe.py').write_bytes(PRODUCER)
    (run / 'driver.rs').write_bytes((HERE / 'java_oracle.rs').read_bytes())
    (run / 'profiles.csv').write_bytes((repo / 'crates/empack-core/src/java_profiles.csv').read_bytes())
    rustc = Path('/Users/zer0cell/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
    assert sha(rustc) == receipt['tool']['sha256']
    env = {'PATH': str(rustc.parent) + ':/usr/bin:/bin', 'HOME': str(work / 'home'),
           'TMPDIR': str(work / 'tmp'), 'LANG': 'en_US.UTF-8'}
    rows = []

    def command(label, argv, private=False):
        started = time.monotonic()
        child = subprocess.Popen(argv, cwd=work, env=env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timed_out = False
        try:
            out, err = child.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            out, err = child.communicate()
        directory = work / 'private' if private else run
        streams = {}
        for stream, payload in [('stdout', out), ('stderr', err)]:
            path = directory / (label + '.' + stream); path.write_bytes(payload)
            streams[stream] = {'path': str(path.relative_to(run)), 'sha256': sha(path), 'bytes': len(payload)}
        row = {'case': label, 'argv': argv, 'exitCode': child.returncode, 'seconds': time.monotonic() - started,
               'timedOut': timed_out, 'streams': streams, 'private': private}
        rows.append(row)
        (run / 'commands.json').write_text(json.dumps(rows, indent=2) + '\n')
        assert not timed_out and child.returncode == 0, 'Preserve failed command before any retry.'
        return out, err

    binary = work / 'java-policy-driver'
    command('compile-driver', [str(rustc), '--edition=2024', str(run / 'driver.rs'),
                              '--extern', 'empack_core=' + str(library), '-o', str(binary)])
    output, _ = command('observed-core', [str(binary)])
    lines = output.decode().splitlines()
    assert lines and len({line.split('\t')[0] for line in lines}) == len(lines)
    observed = []
    # Fixed workload: discover only two explicitly selected installed majors.
    for requested in [21, 27]:
        home = subprocess.check_output(['/usr/libexec/java_home', '-v', str(requested)], env=env, text=True).strip()
        program = Path(home) / 'bin/java'
        out, err = command('jdk-' + str(requested), [str(program), '-XshowSettings:properties', '-version'], private=True)
        values = []
        for line in (out + b'\n' + err).decode('utf-8').splitlines():
            key, separator, value = line.partition('=')
            if separator and key.strip() == 'java.specification.version':
                values.append(value.strip())
        assert len(values) == 1
        value = values[0].removeprefix('1.')
        assert value.isascii() and value.isdecimal()
        major = int(value); assert major == requested
        observed.append({'requested': requested, 'actualMajor': major, 'program': str(program),
                         'programSha256': sha(program), 'source': 'Unique property in private native output; fixture decoder, not the engine parser.'})
    for name, digest in receipt['sourceSha256'].items():
        assert sha(repo / name) == digest
    assert sha(library) == receipt['librarySha256'] and sha(HERE / 'java_oracle.rs') == sha(run / 'driver.rs')
    result = {'schema': 1, 'revision': REVISION, 'platform': platform.platform(), 'architecture': platform.machine(),
        'producerSha256': hashlib.sha256(PRODUCER).hexdigest(), 'driverSha256': sha(run / 'driver.rs'),
        'profilesSha256': sha(run / 'profiles.csv'), 'sourceSha256': receipt['sourceSha256'],
        'priorCoreCapture': str(prior.relative_to(ROOT)), 'priorCoreReceiptSha256': sha(prior / 'receipt.json'),
        'librarySha256': sha(library), 'binarySha256': sha(binary), 'observedSha256': hashlib.sha256(output).hexdigest(),
        'compiler': receipt['tool'], 'cases': len(lines), 'commands': len(rows), 'jdkObservations': observed,
        'allOwnedProcessesRetired': True, 'allocatedKiB': int(subprocess.check_output(['du', '-sk', str(work)], text=True).split()[0]),
        'scope': 'Actual current pure JavaPolicy methods with reused attributed core artifact; two local JVM property observations only. No installed empack CLI, release deserialization, engine Java parser, approval/lease, game/loader/mod launch or whole-stack compatibility evidence.'}
    (run / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'run': str(run), 'cases': len(lines), 'jdkMajors': [x['actualMajor'] for x in observed],
                      'commands': len(rows), 'allocatedKiB': result['allocatedKiB']}, indent=2))


if __name__ == '__main__':
    main()
