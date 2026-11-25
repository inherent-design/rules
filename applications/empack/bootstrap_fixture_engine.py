#!/usr/bin/env python3
"""Controlled child, not empack: exact probe responses and a cancellation peer."""
import json
import os
from pathlib import Path
import socket
import sys

args=sys.argv[1:]
log=Path(os.environ['RULES_ENGINE_LOG'])
label='distribution' if Path(__file__).parent==Path(os.environ['RULES_DISTRIBUTION']) else 'cached' if Path(__file__).name=='empack' else 'explicit'
def event(kind,**fields):
    with log.open('ab')as stream:
        stream.write((json.dumps(dict(kind=kind,pid=os.getpid(),engine=label,**fields),ensure_ascii=False)+'\n').encode())
if args==['--version']:
    event('version',controlPresent='EMPACK_BOOTSTRAP_CONTROL'in os.environ)
    version=os.environ.get('RULES_DIST_VERSION','0.8.8-beta') if label=='distribution' else os.environ.get('RULES_ENGINE_VERSION','0.8.8-beta')
    os.write(1,('empack '+version+'\n').encode());sys.exit(0)
if args==['--bootstrap-protocol']:
    event('protocol',controlPresent='EMPACK_BOOTSTRAP_CONTROL'in os.environ)
    os.write(1,(os.environ.get('RULES_ENGINE_PROTOCOL','empack-bootstrap/1')+'\n').encode());sys.exit(0)
port,nonce=os.environ['EMPACK_BOOTSTRAP_CONTROL'].split(':')
if '--fixture-wrong-peer'in args:
    with socket.create_connection(('127.0.0.1',int(port)),timeout=2)as wrong:
        wrong.sendall(b'empack-bootstrap/1 wrong\n')
        assert wrong.recv(1)==b''
    event('wrong-peer-refused')
with socket.create_connection(('127.0.0.1',int(port)),timeout=5)as peer:
    peer.sendall(('empack-bootstrap/1 '+nonce+'\n').encode('ascii'))
    ready=b''
    while len(ready)<6:ready+=peer.recv(6-len(ready))
    assert ready==b'READY\n'
    event('started',argv=args,cwd=os.getcwd(),authenticated=True)
    result=0
    if '--fixture-wait'in args:
        peer.settimeout(15)
        message=peer.recv(1)
        result=7 if message==b'C' else 6
        event('cancellation',explicit=message==b'C',parentLoss=message==b'',result=result)
    output=dict(argv=args,cwd=os.getcwd(),authenticated=True,engine=label,result=result)
    os.write(1,(json.dumps(output,ensure_ascii=False)+'\n').encode())
event('completed',result=result)
sys.exit(result)
