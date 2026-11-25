#!/usr/bin/env python3
"""Compare the full finite filesystem guard table with Lean and Bend;no native IO fixture."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
from protocol import FLAGS,key

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
BASIS=['common/FilesystemGuard.lean','common/FilesystemGuard.bend','host/FilesystemGuardCase.lean','host/filesystem/protocol.py','host/filesystem/compare.py']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');a=p.parse_args()
    work=ROOT/'.build/filesystem/replay';work.mkdir(parents=True,exist_ok=True)
    rows=[dict(zip(FLAGS,values))|dict(relation=relation)for values in itertools.product([False,True],repeat=len(FLAGS))for relation in range(3)]
    env=dict(os.environ,LEAN_PATH=os.environ.get('LEAN_PATH',str(ROOT/'.build/formal')),BEND_NO_TELEMETRY='1')
    def lean(data,label):
        f=work/(label+'.json');f.write_text(json.dumps(data)+'\n')
        return subprocess.run([os.environ.get('LEAN','lean'),'--run',str(ROOT/'host/FilesystemGuardCase.lean'),str(f)],env=env,cwd=ROOT,text=True,capture_output=True,timeout=30)
    data=dict(schema=1,contract='protected-tree-preflight-v1',rows=rows);r=lean(data,'all')
    assert r.returncode==0,r.stdout+r.stderr;actual=json.loads(r.stdout)
    calls=[]
    for row in rows:
        args=['True{}'if row['policyAllows']else'False{}',str(row['relation'])+'n']+['True{}'if row[k]else'False{}'for k in FLAGS[1:]]
        calls.append('Nat.show(M.fs_preflight('+','.join(args[:5])+')) ++ ":" ++ Nat.show(Bool.pick(Nat,M.fs_may_mutate('+','.join(args)+'),1n,0n)) ++ "\\n"')
    f=work/'all.bend';f.write_text('import Base\nimport ../../../common/FilesystemGuard.bend as M\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
    r=subprocess.run([os.environ.get('BEND','bend'),str(f)],env=env,cwd=ROOT,text=True,capture_output=True,timeout=30)
    assert r.returncode==0,r.stdout+r.stderr;other=[[int(x)for x in line.split(':')]for line in r.stdout.splitlines()];assert actual==other and len(actual)==192
    row=rows[-1];negatives=[dict(data,schema=2),dict(data,contract='writer-authority'),dict(data,rows=rows*2)]
    for change in [dict(relation=3),dict(policyAllows=1),dict(identityCurrent=None),dict(relation=-1)]:negatives.append(dict(data,rows=[row|change]))
    missing=dict(row);del missing['complete'];negatives.append(dict(data,rows=[missing]))
    for i,bad in enumerate(negatives):assert lean(bad,'negative-'+str(i)).returncode==2
    table=dict(schema=1,contract='protected-tree-preflight-v1',sourceSha256={n:sha(ROOT/n)for n in BASIS},
        table={key(row):out for row,out in zip(rows,actual)},
        limits=['Complete finite rule-input universe only;host identity/coverage/currentness/boundary facts are premises,not proven by this table.',
                'Native projection is separately inspected/tested;agreement between models does not prove that Python adapter or a production writer.',
                'Only proof tools execute;no studied application,native filesystem fixture or concurrent mutation is started.'])
    output=HERE/'vectors.json'
    if a.write:output.write_text(json.dumps(table,indent=2)+'\n')
    else:assert json.loads(output.read_text())==table,'Filesystem vectors do not match current models/source.'
    print(json.dumps(dict(status='passed-finite-filesystem-guard',combinations=192,decoderRefusals=len(negatives),written=a.write)))


if __name__=='__main__':main()
