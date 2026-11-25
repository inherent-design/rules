#!/usr/bin/env python3
"""Run one bounded standard-library filesystem fixture and retain its raw CI record."""
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
output=ROOT/'.build/filesystem/current.json';output.parent.mkdir(parents=True,exist_ok=True)
with output.open('wb')as stream:
    subprocess.run([sys.executable,str(HERE/'native.py')],stdout=stream,cwd=ROOT,check=True,timeout=30)
subprocess.run([sys.executable,str(HERE/'verify.py'),str(output),'--controls'],cwd=ROOT,check=True,timeout=30)
print('filesystem-native-v1='+json.dumps(json.loads(output.read_text()),separators=(',',':')))
