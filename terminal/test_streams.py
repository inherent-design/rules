"""Checks the study boundary against real subprocesses, independently of tool models."""
import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest

from streams import capture


class Streams(unittest.TestCase):
    def test_independent_descriptors_and_utf8(self):
        code = "import os,json,sys; print(json.dumps([os.isatty(i) for i in range(3)]));print('Ω 日本',file=sys.stderr)"
        for inp in ('pipe', 'tty'):
            for err in ('pipe', 'tty'):
                r = capture([sys.executable, '-c', code], stdin=inp, stderr=err)
                self.assertEqual(json.loads(base64.b64decode(r['observed']['stdout_b64'])), [inp == 'tty', False, err == 'tty'])
                self.assertIn('Ω 日本', base64.b64decode(r['observed']['stderr_b64']).decode())
                self.assertEqual(r['outcome']['exit_code'], 0)
                self.assertTrue(r['outcome']['capture_complete'])

    def test_width_and_noncontrolling_terminal_are_observed(self):
        code = "import os,json; print(json.dumps(list(os.get_terminal_size(2))))\ntry: os.open('/dev/tty',os.O_RDONLY)\nexcept OSError as e: print(e.errno)"
        r = capture([sys.executable, '-c', code], width=28)
        lines = base64.b64decode(r['observed']['stdout_b64']).splitlines()
        self.assertEqual(json.loads(lines[0]), [28, 24])
        self.assertEqual(int(lines[1]), 6)  # ENXIO on the tested macOS host.

    def test_controlled_tty_input_is_not_a_human(self):
        code = "import sys;print('READY',file=sys.stderr,flush=True);print(input())"
        r = capture([sys.executable, '-c', code], stdin='tty', marker='READY', action='answer\n')
        self.assertEqual(base64.b64decode(r['observed']['stdout_b64']), b'answer\n')
        self.assertTrue(r['observed']['actionTriggered'])

    def test_interrupt_retains_a_completed_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'effect'
            code = "import pathlib,time,sys;pathlib.Path(sys.argv[1]).write_text('saved');print('READY',file=sys.stderr,flush=True);time.sleep(10)"
            r = capture([sys.executable, '-c', code, str(path)], marker='READY', action='interrupt')
            self.assertEqual(path.read_text(), 'saved')
            self.assertEqual(r['outcome']['signal'], 2)
            self.assertFalse(r['outcome']['timed_out'])

    def test_timeout_is_distinct_from_interrupt(self):
        r = capture([sys.executable, '-c', 'import time;time.sleep(5)'], timeout=.15)
        self.assertTrue(r['outcome']['timed_out'])
        self.assertEqual(r['outcome']['signal'], 9)


if __name__ == '__main__':
    unittest.main()
