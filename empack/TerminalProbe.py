"""Capture terminal policy inputs as one JSON object, or replay a fixture.

Supply console's colors_enabled_stderr decision explicitly. This adapter
observes the current terminal without changing tty state or invoking a shell.
"""
import argparse
import json
import locale
import os
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--colors-enabled", choices=["yes", "no"])
parser.add_argument("--fixture")
args = parser.parse_args()
if args.fixture:
    with open(args.fixture) as source:
        print(json.dumps(json.load(source)))
else:
    if args.colors_enabled is None:
        parser.error("capture requires an explicit --colors-enabled yes/no")
    try:
        columns = os.get_terminal_size(2).columns
    except OSError:
        columns = 80
    print(json.dumps(dict(tty=sys.stderr.isatty(), enabled=args.colors_enabled == "yes",
                          colorterm=os.getenv("COLORTERM", ""), lcAll=os.getenv("LC_ALL"),
                          lcCtype=os.getenv("LC_CTYPE"), lang=os.getenv("LANG"),
                          osUtf="utf" in locale.getpreferredencoding(False).lower(), cols=columns)))
