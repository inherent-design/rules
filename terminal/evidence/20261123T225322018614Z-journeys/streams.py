#!/usr/bin/env python3
"""Terminal-only experiment: bounded streams, width, and marker-triggered input/signals.

Private non-controlling PTY. Never attaches to a human terminal. Marker-triggered
SIGINT targets only the new child process group; timeout is separately SIGKILL.
"""
import argparse
import base64
import errno
import fcntl
import json
import os
import pty
import selectors
import signal
import struct
import subprocess
import termios
import time


def capture(command, *, stdin='pipe', stdout='pipe', stderr='tty', width=80,
            timeout=12, marker=None, action=None):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, width, 0, 0))
    read_fd, write_fd = os.pipe()
    os.close(write_fd)
    child = subprocess.Popen(command, stdin=slave if stdin == 'tty' else read_fd,
                             stdout=slave if stdout == 'tty' else subprocess.PIPE,
                             stderr=slave if stderr == 'tty' else subprocess.PIPE,
                             start_new_session=True)
    os.close(slave)
    os.close(read_fd)
    buffers = {'stdout': bytearray(), 'stderr': bytearray()}
    # A fully terminal output profile merges channels by construction.
    pty_channel = 'combined' if stdout == stderr == 'tty' else ('stdout' if stdout == 'tty' else 'stderr')
    buffers.setdefault(pty_channel, bytearray())
    start = time.monotonic()
    events, acted, timed_out = [], False, False
    with selectors.DefaultSelector() as reader:
        if stdin == 'tty' or stdout == 'tty' or stderr == 'tty':
            reader.register(master, selectors.EVENT_READ, pty_channel)
        for channel, mode in [('stdout', stdout), ('stderr', stderr)]:
            if mode == 'pipe':
                reader.register(getattr(child, channel), selectors.EVENT_READ, channel)
        try:
            while reader.get_map():
                remaining = timeout - (time.monotonic() - start)
                if remaining <= 0:
                    timed_out = True
                    break
                for key, _ in reader.select(min(remaining, .1)):
                    try:
                        data = os.read(key.fd, 65536)
                    except OSError as error:
                        if error.errno != errno.EIO:
                            raise
                        data = b''
                    if not data:
                        reader.unregister(key.fileobj)
                        continue
                    buffers[key.data].extend(data)
                    events.append({'seconds': time.monotonic() - start, 'channel': key.data,
                                   'bytes': len(data)})
                if not acted and marker and any(marker.encode() in b for b in buffers.values()):
                    if action == 'interrupt':
                        os.killpg(child.pid, signal.SIGINT)
                    elif action is not None:
                        if stdin != 'tty':
                            raise ValueError('Injected input requires private tty stdin.')
                        os.write(master, action.encode('utf-8'))
                    acted = True
                    events.append({'seconds': time.monotonic() - start, 'action': action})
            if not timed_out:
                try:
                    child.wait(timeout=max(.01, timeout - (time.monotonic() - start)))
                except subprocess.TimeoutExpired:
                    timed_out = True
            if timed_out:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                end = time.monotonic() + 1
                while reader.get_map() and time.monotonic() < end:
                    for key, _ in reader.select(.05):
                        try:
                            data = os.read(key.fd, 65536)
                        except OSError as error:
                            if error.errno != errno.EIO:
                                raise
                            data = b''
                        if data:
                            buffers[key.data].extend(data)
                        else:
                            reader.unregister(key.fileobj)
            complete = not reader.get_map()
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
            child.wait()
            for stream in (child.stdout, child.stderr):
                if stream:
                    stream.close()
            os.close(master)
    return {'v': 1, 'surface': 'terminal-stream-experiment', 'case': 'controlled-streams',
            'observed': {'isatty': {'stdin': stdin == 'tty', 'stdout': stdout == 'tty', 'stderr': stderr == 'tty'},
                         'width': width, 'controllingTerminal': False,
                         'events': events, 'actionTriggered': acted,
                         **{k + '_b64': base64.b64encode(v).decode() for k, v in buffers.items()}},
            'outcome': {'exit_code': child.returncode if child.returncode >= 0 else None,
                        'signal': -child.returncode if child.returncode < 0 else None,
                        'timed_out': timed_out, 'capture_complete': complete}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for channel, default in [('stdin', 'pipe'), ('stdout', 'pipe'), ('stderr', 'tty')]:
        parser.add_argument('--' + channel, choices=['pipe', 'tty'], default=default)
    parser.add_argument('--width', type=int, default=80)
    parser.add_argument('--timeout', type=float, default=12)
    parser.add_argument('--marker')
    parser.add_argument('--action')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = vars(parser.parse_args())
    args['command'] = args['command'][1:] if args['command'][:1] == ['--'] else args['command']
    if not args['command'] or not 1 <= args['width'] <= 1000 or not 0 < args['timeout'] <= 60:
        parser.error('Supply a command, width 1..1000, and timeout 0..60 seconds.')
    print(json.dumps(capture(**args)))


if __name__ == '__main__':
    main()
