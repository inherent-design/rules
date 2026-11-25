#!/usr/bin/env python3
"""Retain a collector correction, then fault only its owned private content blob."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
from pending_continue_probe import Runner, ROOT, digest

PRODUCER = Path(__file__).read_bytes()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('run',type=Path)
    a=p.parse_args();run=a.run.resolve()
    assert run.parent == ROOT/'applications/evidence'
    (run/'retained-probe.py').write_bytes(PRODUCER)
    r=Runner(run,'retained')
    try:
        initial=json.loads((run/'baseline.json').read_text())['publicOperation']
        captured=json.loads((run/'partial-retained-list.stdout').read_text())['operations'][0]
        assert not (run/'partial-result.json').exists()
        assert r.operation('readback') == [captured]
        # The interrupted producer looked at the wrong field. Retained is the
        # public verification label, not a saved user-supplied host pathname.
        first=next(i for i in captured['inputs'] if i['key']=='locked:first:primary')
        assert first['verification']=='retained; verification required'
        assert first['supplied_candidate'] is None
        old=r.command('old-id',['pending','show',initial['id']])
        assert old['exitCode'] != 0 and not old['changedScopes']
        r.write('collector-correction.json',dict(schema=1,
            failedProducer='continuation-probe.py',failedPhase='partial',
            failure='AssertionError at supplied_candidate is not None; field represents a supplied path, not retained verified content.',
            nativeCommandsComplete=8,nativeFailure=False,
            correction='Read the recorded verification label; preserve the original failed collector and all eight command outcomes. No rerun.'))
        r.write('partial-result.json',dict(schema=1,status='complete-with-separate-collector-correction',
            initial=initial,current=captured,correction='collector-correction.json'))
        asset=json.loads((run/'assets.json').read_text())['first']
        blob=r.work/'state/pending-content'/(asset['sha256']+'.blob')
        assert blob.is_file() and not blob.is_symlink() and digest(blob)==asset['sha256']
        assert blob.stat().st_nlink == 1
        original=blob.read_bytes();s=blob.stat()
        (run/'retained-original.bin').write_bytes(original)
        r.write('retained-fault-preimage.json',dict(relativePath=str(blob.relative_to(r.work)),
            sha256=digest(blob),bytes=len(original),mode=stat.S_IMODE(s.st_mode),inode=str(s.st_ino),
            mtimeNs=str(s.st_mtime_ns),atimeNs=str(s.st_atime_ns),
            scope='Only this owned isolated fixture store, after all prior command groups retired. No live/shared/recovery content.'))
        try:
            os.chmod(blob,stat.S_IMODE(s.st_mode)|stat.S_IWUSR)
            blob.write_bytes(b'X'*len(original))
            os.chmod(blob,stat.S_IMODE(s.st_mode))
            assert digest(blob) != asset['sha256']
            inspected=r.operation('corrupt-list')
            assert inspected == [captured]
            resume=r.command('corrupt-resume',['pending','resume',captured['id']])
            assert resume['exitCode'] != 0 and 'project' not in resume['changedScopes'],resume
            r.write('retained-fault-observed.json',dict(command=resume,listedOperation=inspected[0],
                blobStillPresent=blob.exists(),blobSha256=digest(blob) if blob.exists() else None))
        finally:
            assert blob.exists() and not blob.is_symlink(),'Keep original; do not guess recovery after a replaced/missing target.'
            assert str(blob.stat().st_ino)==str(s.st_ino),'Keep original; native target identity changed.'
            os.chmod(blob,stat.S_IMODE(s.st_mode)|stat.S_IWUSR)
            blob.write_bytes(original)
            os.chmod(blob,stat.S_IMODE(s.st_mode))
            os.utime(blob,ns=(s.st_atime_ns,s.st_mtime_ns))
            assert digest(blob)==asset['sha256'] and stat.S_IMODE(blob.stat().st_mode)==stat.S_IMODE(s.st_mode)
            assert blob.stat().st_ino==s.st_ino and blob.stat().st_mtime_ns==s.st_mtime_ns
            r.write('retained-restoration.json',dict(schema=1,path=str(blob.relative_to(r.work)),sha256=digest(blob),
                originalBytesModeInodeMtimeRestored=True,ctimeNotPreserved=True,originalCopy='retained-original.bin'))
        assert r.operation('restored-list') == [captured]
        print(json.dumps(dict(run=str(run.relative_to(ROOT)),phase='retained',status='complete',commands=len(r.commands))))
    finally:
        r.close()

if __name__=='__main__':
    main()
