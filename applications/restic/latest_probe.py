#!/usr/bin/env python3
"""One read-only follow-up against this owner's completed local selection fixture."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = Path(__file__).read_bytes()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    assert run.parent == (ROOT / 'applications/evidence').resolve() and run.name.startswith('restic-selection-')
    work = run / 'work'; repository = work / 'repository'; password = work / 'password'
    tool = ROOT / 'applications/tools/restic-0.20.0/restic'
    assert sha(tool) == json.loads((run / 'receipt.json').read_text())['tool']['binarySha256']
    capture = run / 'latest-selector'; capture.mkdir(); (capture / 'probe.py').write_bytes(PRODUCER)
    def state():
        return {kind: {p.relative_to(repository).as_posix(): sha(p) for p in sorted((repository / directory).rglob('*')) if p.is_file()}
            for kind, directory in [('snapshotRefs', 'snapshots'), ('packs', 'data')]}
    before = state(); assert before == json.loads((run / 'trace.json').read_text())[-1]['observed']['after']
    argv = [str(tool), '--repo', str(repository), '--password-file', str(password), '--json', 'snapshots', 'latest']
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(work / 'home'), 'TMPDIR': str(work / 'tmp'), 'RESTIC_CACHE_DIR': str(work / 'cache'), 'LANG': 'C.UTF-8', 'TZ': 'UTC', 'GOMAXPROCS': '2'}
    child = subprocess.Popen(argv, cwd=work, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timeout = False
    try: out, err = child.communicate(input=b'', timeout=60)
    except subprocess.TimeoutExpired:
        timeout = True
        try: os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        out, err = child.communicate()
    (capture / 'stdout').write_bytes(out); (capture / 'stderr').write_bytes(err)
    row = {'schema': 1, 'producerSha256': hashlib.sha256(PRODUCER).hexdigest(), 'basisReceiptSha256': sha(run / 'receipt.json'),
        'argv': argv, 'observed': {'before': before, 'after': state(), 'stdoutSha256': hashlib.sha256(out).hexdigest(), 'stderrSha256': hashlib.sha256(err).hexdigest()},
        'outcome': {'exitCode': child.returncode, 'timedOut': timeout}, 'scope': 'One later read-only command; does not change or replace the original 21-command receipt.'}
    (capture / 'receipt.json').write_text(json.dumps(row, indent=2) + '\n')
    assert not timeout and child.returncode == 0 and before == state()
    print(json.dumps({'capture': str(capture), 'selectedIds': [s['id'] for s in json.loads(out)], 'refsAndPacksUnchanged': True}, indent=2))


if __name__ == '__main__': main()
