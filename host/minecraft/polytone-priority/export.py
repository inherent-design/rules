#!/usr/bin/env python3
"""Export authored adapters/observations;keep the original provider class private."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);args=p.parse_args();capture=args.capture.resolve();r=json.loads((capture/'receipt.json').read_text())
    assert len(r['commands'])==2 and all(c['exitCode']==0 and c['ownedGroupAbsent'] and not c['timedOut'] for c in r['commands'])
    assert sha(capture/'original'/r['classEntry'])==r['classEntrySha256']
    observed=json.loads((capture/'execute.stdout').read_text());assert len(observed['cases'])==48 and observed['originalClassSha256']==r['classEntrySha256']
    destination=HERE.parent/'evidence'/capture.name;destination.mkdir(parents=True,exist_ok=False)
    for n,d in r['sourceSha256'].items():assert sha(capture/'src'/n)==d;shutil.copyfile(capture/'src'/n,destination/n)
    for stem,c in zip(['compile','execute'],r['commands']):
        for stream in ['stdout','stderr']:
            n=stem+'.'+stream;assert sha(capture/n)==c[stream+'Sha256'];shutil.copyfile(capture/n,destination/n)
    public={k:v for k,v in r.items() if k not in ['commands','tools']}
    public['commands']=[{k:v for k,v in c.items() if k!='argv'}|dict(argvDisclosure='Exact owner-local argv retained privately;frozen authored collector constructs it.') for c in r['commands']]
    public['tools']={k:dict(executable=Path(v['path']).name,sha256=v['sha256']) for k,v in r['tools'].items()}
    public['privateReceiptSha256']=sha(capture/'receipt.json')
    public['limits']=['One unchanged Parsed$SortedMap class,not full provider or transformed game execution.','Parsed data/isEnabled,opaque identifier equality,nonthrowing warning sink and case construction are explicit authored adapters.','No original provider/game class binary exported;only authored producers/adapters,observations and identities.','Admitted scalar states are not proof every combination is reachable through ordinary resource loading.','No condition/content decoding,folder selection,config read/write,actual logger,reload application,GUI or GPU behavior exercised.']
    (destination/'receipt.json').write_text(json.dumps(public,indent=2)+'\n');print(destination)


if __name__=='__main__':main()
