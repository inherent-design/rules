#!/usr/bin/env python3
"""Export authored class-lookup traces; compiled classes and exact local paths stay private."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def export(capture,check):
    r=json.loads((capture/'receipt.json').read_text())
    assert r['cases']==19 and r['profile']['JAVA_VERSION'].split('.')[0] in ['17','21','25']
    for name,digest in r['sourcesSha256'].items():assert sha(capture/name)==digest
    for name,digest in r['classesSha256'].items():assert sha(capture/'classes'/name)==digest
    for tool in r['tools'].values():assert sha(Path(tool['path']))==tool['sha256']
    assert sha(Path(r['tools']['java']['path']).parent.parent/'release')==r['jdkReleaseSha256']
    assert sha(capture/'execute.stdout')==r['observedSha256']
    records=[json.loads(l) for l in (capture/'execute.stdout').read_text().splitlines()]
    assert len([r for r in records if 'case' in r])==19
    assert {r['runtimeClass']:r['sha256'] for r in records if 'runtimeClass' in r}==r['runtimeClassesSha256']
    destination=HERE/'evidence'/capture.name
    if check:assert destination.is_dir()
    else:destination.mkdir(exist_ok=False)
    def copy(name):
        if check:assert (capture/name).read_bytes()==(destination/name).read_bytes(),name
        else:shutil.copyfile(capture/name,destination/name)
    for name in r['sourcesSha256']:copy(name)
    for stem,command in zip(['compile','execute'],r['commands']):
        assert command['exitCode']==0 and command['ownedGroupAbsent'] and not command['timedOut']
        for stream in ['stdout','stderr']:
            name=stem+'.'+stream;assert sha(capture/name)==command[stream+'Sha256'];copy(name)
    public={k:v for k,v in r.items() if k not in ['tools','commands']}
    public['tools']={n:dict(executable=Path(t['path']).name,sha256=t['sha256']) for n,t in r['tools'].items()}
    public['commands']=[{k:v for k,v in c.items() if k!='argv'}|dict(argvDisclosure='Exact owner-local argv retained privately; frozen producer constructs it.') for c in r['commands']]
    public['privateReceiptSha256']=sha(capture/'receipt.json')
    public['limits']=r['limits']+['JVM heap/CPU settings and group retirement do not measure total host memory or global reclamation.',
        'Stdout contains authored target/counter observations and hashes of actual runtime Class/ClassLoader bytes, not every VM/native dependency.']
    if check:assert json.loads((destination/'receipt.json').read_text())==public
    else:(destination/'receipt.json').write_text(json.dumps(public,indent=2)+'\n')
    return dict(capture='evidence/'+capture.name,java=r['profile']['JAVA_VERSION'],cases=19)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('captures',type=Path,nargs='+');parser.add_argument('--check',action='store_true');args=parser.parse_args()
    print(json.dumps([export(p.resolve(),args.check) for p in args.captures]))


if __name__=='__main__':main()
