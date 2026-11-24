#!/usr/bin/env python3
"""Exercise only the collector's owned-child cleanup guard."""
import hashlib
import inspect
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'applications/empack'))
from initializer_probe import retire_owned

results = []
for isolated in [True, False]:
    child = subprocess.Popen([sys.executable, '-c', 'import time;print("ready",flush=True);time.sleep(60)'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=isolated)
    try:
        assert child.stdout.readline() == b'ready\n'
        if isolated:
            assert retire_owned(child) == (b'', b'') and child.returncode == -signal.SIGKILL
            try: os.killpg(child.pid, 0)
            except ProcessLookupError: absent = True
            else: absent = False
            assert absent and retire_owned(child) is None
            results.append(dict(case='owned-isolated-child', exitCode=child.returncode, ownedGroupAbsent=True, secondCallIsNoop=True))
        else:
            try: retire_owned(child)
            except ValueError as e: assert str(e) == 'Child does not lead an isolated process group'
            else: raise AssertionError('Nonisolated process-group kill allowed')
            assert child.poll() is None
            child.kill(); child.communicate(); assert child.returncode == -signal.SIGKILL
            results.append(dict(case='nonisolated-child', groupKillRefused=True, childWasStillAlive=True, explicitChildOnlyCleanupExit=child.returncode))
    finally:
        if child.poll() is None: child.kill(); child.communicate()
helper = inspect.getsource(retire_owned)
result = dict(schema=1, scope='Collector cleanup helper only; not an empack initializer case or general subprocess-tree proof.',
    helperSha256=hashlib.sha256(helper.encode()).hexdigest(), testSourceSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    cases=results)
print(json.dumps(result, indent=2))
