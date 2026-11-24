#!/usr/bin/env python3
"""Run bounded actual-core removal and request-merge calls; no engine or file publication."""
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
    provenance = json.loads((prior / 'receipt.json').read_text())
    library = prior / 'work/libempack_core.rlib'
    assert provenance['revision'] == REVISION and sha(library) == provenance['librarySha256']
    for path, digest in provenance['sourceSha256'].items():
        payload = subprocess.check_output(['git', '-C', str(repo), 'show', REVISION + ':' + path])
        assert hashlib.sha256(payload).hexdigest() == digest == sha(repo / path)
    run = ROOT / 'applications/evidence' / ('empack-removal-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'
    for name in ['home', 'tmp']:
        (work / name).mkdir(parents=True)
    (run / 'probe.py').write_bytes(PRODUCER)
    (run / 'driver.rs').write_bytes((HERE / 'removal_oracle.rs').read_bytes())
    rustc = Path(provenance['tool']['path'])
    assert sha(rustc) == provenance['tool']['sha256']
    env = {'PATH': str(rustc.parent) + ':/usr/bin:/bin', 'HOME': str(work / 'home'),
           'TMPDIR': str(work / 'tmp'), 'LANG': 'en_US.UTF-8'}
    rows = []

    def command(label, argv):
        began = time.monotonic()
        child = subprocess.Popen(argv, cwd=work, env=env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timed_out = False
        try:
            out, err = child.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(child.pid, signal.SIGKILL); out, err = child.communicate()
        (run / (label + '.stdout')).write_bytes(out); (run / (label + '.stderr')).write_bytes(err)
        rows.append(dict(case=label, argv=argv, pid=child.pid, exitCode=child.returncode, timedOut=timed_out,
                         seconds=time.monotonic() - began, stdoutSha256=sha(run / (label + '.stdout')),
                         stderrSha256=sha(run / (label + '.stderr'))))
        (run / 'commands.json').write_text(json.dumps(rows, indent=2) + '\n')
        assert child.returncode == 0 and not timed_out, 'Retain failed compilation/execution before retry.'
        return out

    try:
        binary = work / 'removal-driver'
        command('compile-driver', [str(rustc), '--edition=2024', str(run / 'driver.rs'),
                                  '--extern', 'empack_core=' + str(library), '-o', str(binary)])
        raw = command('observed', [str(binary)])
        cases = [json.loads(line) for line in raw.decode().splitlines()]
        assert len(cases) == len({r['case'] for r in cases}) == 25
        for path, digest in provenance['sourceSha256'].items():
            assert sha(repo / path) == digest
        assert sha(library) == provenance['librarySha256']
        receipt = dict(schema=1, revision=REVISION, producerSha256=hashlib.sha256(PRODUCER).hexdigest(),
            driverSha256=sha(run / 'driver.rs'), binarySha256=sha(binary), observedSha256=hashlib.sha256(raw).hexdigest(),
            priorCoreCapture=str(prior.relative_to(ROOT)), priorCoreReceiptSha256=sha(prior / 'receipt.json'),
            librarySha256=sha(library), sourceSha256=provenance['sourceSha256'], compiler=provenance['tool'],
            platform=platform.platform(), cases=len(cases), allOwnedProcessesRetired=True,
            allocatedKiB=int(subprocess.check_output(['du', '-sk', str(work)], text=True).split()[0]),
            scope='Actual unchanged core removal/addition calls over fictional provider projects,pins,file assertions and synthetic semantic revisions. rejectExistingWouldAllow is a source-interpreted caller predicate,not executed engine admission. No codec,provider lookup,native file observation/publication,CLI or full workflow test.')
        (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'run': str(run), 'cases': len(cases), 'allocatedKiB': receipt['allocatedKiB']}, indent=2))
    except BaseException as error:
        (run / 'failure.json').write_text(json.dumps({'error': str(error), 'commands': len(rows)}) + '\n')
        raise


if __name__ == '__main__':
    main()
