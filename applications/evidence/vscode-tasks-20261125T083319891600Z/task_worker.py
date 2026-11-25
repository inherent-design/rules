#!/usr/bin/env python3
"""Owned task child: records literal args, readiness and signal retirement."""
import argparse,json,os,signal,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--log',type=Path,required=True);p.add_argument('--name',required=True);p.add_argument('--mode',choices=['exit','background','wait'],required=True);p.add_argument('--gate',type=Path);p.add_argument('--value',action='append',default=[]);a=p.parse_args()
def event(kind,**kw):
    with a.log.open('ab')as f:f.write((json.dumps(dict(kind=kind,name=a.name,pid=os.getpid(),ppid=os.getppid(),pgid=os.getpgrp(),**kw),ensure_ascii=False)+'\n').encode())
def stop(n,_):
    event('signal',signal=n);event('exit',code=11);raise SystemExit(11)
for n in [signal.SIGTERM,signal.SIGINT,signal.SIGHUP]:signal.signal(n,stop)
event('start',argv=a.value,cwd=os.getcwd())
if a.mode=='exit':event('exit',code=7 if a.name=='process-seven'else 0);raise SystemExit(7 if a.name=='process-seven'else 0)
print('BEGIN',flush=True);deadline=time.monotonic()+10
while time.monotonic()<deadline:
    if a.mode=='background'and a.gate and a.gate.exists():
        print('READY',flush=True);event('ready');break
    time.sleep(0.02)
while time.monotonic()<deadline:time.sleep(0.02)
event('deadline');event('exit',code=0)
