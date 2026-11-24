#!/usr/bin/env python3
"""Run a bounded POSIX child fixture with piped stdout and a private PTY on stderr."""
import argparse
import base64
import errno
import json
import os
import pty
import selectors
import signal
import subprocess
import time
from contextlib import ExitStack

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--stdin", choices=("pipe", "tty"), required=True)
parser.add_argument("--timeout", type=float, default=30)
parser.add_argument("command", nargs=argparse.REMAINDER)
args = parser.parse_args()
command = args.command[1:] if args.command[:1] == ["--"] else args.command
if not command or not 0 < args.timeout <= 3600:
    parser.error("Supply a command and a positive timeout of at most 3600 seconds.")

with ExitStack() as resources:
    def keep(fd):
        resources.callback(os.close, fd)
        return fd

    master, slave = pty.openpty()
    keep(master)
    slave_file = resources.enter_context(os.fdopen(slave, "wb", buffering=0))
    if args.stdin == "tty":
        input_fd = slave
    else:
        read_fd, write_fd = os.pipe()
        input_fd = keep(read_fd)
        os.close(write_fd)  # The child sees a pipe at EOF.
    facts = dict(stdin=os.isatty(input_fd), stdout=False, stderr=os.isatty(slave))
    child = subprocess.Popen(command, stdin=input_fd, stdout=subprocess.PIPE,
                             stderr=slave, start_new_session=True)
    resources.callback(child.stdout.close)
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time.monotonic() + args.timeout
    timed_out = False
    def consume(fd, channel):
        try:
            data = os.read(fd, 65536)
        except OSError as error:
            if error.errno != errno.EIO:
                raise
            data = b""
        buffers[channel].extend(data)
        return bool(data)

    # Keep the PTY master through capture, but drop the parent's slave so EOF
    # becomes observable even if a grandchild inherited the child's stderr.
    slave_file.close()
    try:
        with selectors.DefaultSelector() as reader:
            reader.register(master, selectors.EVENT_READ, "stderr")
            reader.register(child.stdout, selectors.EVENT_READ, "stdout")
            while reader.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    break
                for key, _ in reader.select(remaining):
                    if not consume(key.fd, key.data):
                        reader.unregister(key.fileobj)
            if not timed_out:
                try:
                    child.wait(timeout=max(0, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    timed_out = True
            if timed_out:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                # Drain already written bytes; a detached descendant may still own an fd.
                end = time.monotonic() + 1
                while reader.get_map() and time.monotonic() < end:
                    for key, _ in reader.select(max(0, end - time.monotonic())):
                        if not consume(key.fd, key.data):
                            reader.unregister(key.fileobj)
            capture_complete = not reader.get_map()
    finally:
        if child.poll() is None:
            child.kill()
        child.wait()
    code = child.returncode
    print(json.dumps(dict(v=1, surface="streams", case="stdout-pipe-stderr-pty",
        observed=dict(isatty=facts, **{k+"_b64":base64.b64encode(v).decode() for k,v in buffers.items()}),
        outcome=dict(exit_code=code if code >= 0 else None, signal=-code if code < 0 else None,
                     timed_out=timed_out, capture_complete=capture_complete))))
