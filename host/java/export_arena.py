#!/usr/bin/env python3
"""Export the authored Java25 arena witness without JDK binaries or local paths."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('capture',type=Path);args=parser.parse_args()
    capture=args.capture.resolve();r=json.loads((capture/'receipt.json').read_text())
    assert len(r['commands'])==2 and all(c['exitCode']==0 and not c['timedOut'] and c['ownedGroupAbsent'] for c in r['commands'])
    names=list(r['sourceSha256'])
    for n,d in r['sourceSha256'].items():assert sha(capture/n)==d
    for stem,c in zip(['compile','execute'],r['commands']):
        for stream in ['stdout','stderr']:
            n=stem+'.'+stream;assert sha(capture/n)==c[stream+'Sha256'];names.append(n)
    assert sha(capture/'classes/study/host/ArenaProbe.class')==r['classSha256']
    observed=json.loads((capture/'execute.stdout').read_text());assert observed['schema']==1 and len(observed['events'])==11
    destination=HERE/'evidence'/capture.name;destination.mkdir(parents=True,exist_ok=False)
    for n in names:shutil.copyfile(capture/n,destination/n)
    public={k:v for k,v in r.items() if k not in ['tools','commands']}
    public['tools']={k:dict(executable=Path(v['path']).name,sha256=v['sha256']) for k,v in r['tools'].items()}
    public['commands']=[{k:v for k,v in c.items() if k!='argv'}|dict(argvDisclosure='Exact argv retained owner-locally; frozen collector constructs it.') for c in r['commands']]
    public['privateReceiptSha256']=sha(capture/'receipt.json')
    public['limits']=['Only confined/shared aligned long segments, sequential operations with joined workers;no simultaneous access/close race.','No raw address,FFI,JNI,GPU,game code,physical-memory measurement or application authority qualification.','Owner means creating Java thread,not human principal. Shared access is not synchronization.','FFM is stable since Java22;this witness selects Java25 without preview flags.']
    (destination/'receipt.json').write_text(json.dumps(public,indent=2)+'\n')
    print(destination)


if __name__=='__main__':main()
