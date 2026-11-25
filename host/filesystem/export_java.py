#!/usr/bin/env python3
"""Verify Java same-file inputs/programs and export authored evidence only."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--check',action='store_true');a=p.parse_args();cap=a.capture.resolve()
    r=json.loads((cap/'receipt.json').read_text())
    for n,h in r['sourcesSha256'].items():assert sha(cap/n)==h
    for t in r['tools'].values():assert sha(Path(t['path']))==t['sha256']
    jdk=Path(r['tools']['java']['path']).parent.parent;assert sha(jdk/'release')==r['jdkReleaseSha256']
    program=cap/'classes/study/host/SameFileProbe.class';assert sha(program)==r['classSha256']
    assert program.read_bytes()[:4]==b'\xca\xfe\xba\xbe'and int.from_bytes(program.read_bytes()[6:8],'big')==61
    dest=HERE/'evidence'/cap.name
    if a.check:assert dest.is_dir()
    else:dest.mkdir(exist_ok=False)
    def copy(n):
        if a.check:assert(cap/n).read_bytes()==(dest/n).read_bytes()
        else:shutil.copyfile(cap/n,dest/n)
    for n in r['sourcesSha256']:copy(n)
    for stem,c in zip(['compile','execute'],r['commands']):
        assert c['exitCode']==0 and c['ownedGroupAbsent']and not c['timedOut']
        for channel in ['stdout','stderr']:
            n=stem+'.'+channel;assert sha(cap/n)==c[channel+'Sha256'];copy(n)
    public={k:v for k,v in r.items()if k not in ['commands','tools']}
    public['commands']=[{k:v for k,v in c.items()if k!='argv'}|dict(argvDisclosure='Exact private argv retained;frozen producer selects explicit JDK and owned work root.')for c in r['commands']]
    public['tools']={n:dict(executable=Path(v['path']).name,sha256=v['sha256'])for n,v in r['tools'].items()}
    public.update(privateReceiptSha256=sha(cap/'receipt.json'),classMajor=61)
    if a.check:assert json.loads((dest/'receipt.json').read_text())==public
    else:(dest/'receipt.json').write_text(json.dumps(public,indent=2)+'\n')
    print(json.dumps(dict(capture=dest.name,feature=r['feature'],calls=5,checked=a.check)))


if __name__=='__main__':main()
