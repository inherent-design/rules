#!/usr/bin/env python3
"""Export authored element probes, selected locators and observations, not game payloads."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);args=p.parse_args();capture=args.capture.resolve()
    r=json.loads((capture/'receipt.json').read_text());assert r['target']=='java-1.21.11-vanilla' and r['observerErrors']==0
    assert len(r['commands'])==2 and all(c['exitCode']==0 and c['ownedGroupAbsent'] and not c['timedOut'] for c in r['commands'])
    assert sha(capture/'observed.json')==r['observedSha256'] and sha(capture/'bindings.json')==r['bindingsSha256']
    assert sha(capture/'library-input.json')==r['libraryReceiptSha256']
    destination=HERE/'evidence'/capture.name;destination.mkdir(parents=True,exist_ok=False)
    for n,d in r['sourcesSha256'].items():assert sha(capture/n)==d;shutil.copyfile(capture/n,destination/n)
    for stem,c in zip(['compile','execute'],r['commands']):
        for s in ['stdout','stderr']:
            n=stem+'.'+s;assert sha(capture/n)==c[s+'Sha256'];shutil.copyfile(capture/n,destination/n)
    for n in ['bindings.json','observed.json']:shutil.copyfile(capture/n,destination/n)
    public={k:v for k,v in r.items() if k not in ['commands','tools','libraries']}
    public['tools']={n:dict(executable=Path(v['path']).name,sha256=v['sha256']) for n,v in r['tools'].items()}
    public['libraries']=[{k:v for k,v in row.items() if k!='path'}|dict(file=Path(row['path']).name) for row in r['libraries']]
    public['commands']=[{k:v for k,v in c.items() if k!='argv'}|dict(argvDisclosure='Exact argv remains owner-local;frozen authored collector constructs it.') for c in r['commands']]
    public['privateReceiptSha256']=sha(capture/'receipt.json')
    public['limits']=['Original unmodified signed client JAR. Only authored observer classes are compiled.','Selected class/getter locators are metadata,not a wholesale mapping or method-body export.','No original client/class/mapping/library/artwork payload exported.','Gson receives parsed authored JSON values;not arbitrary wire syntax or duplicate-key qualification.','Controlled consumer adapters intercept texture resolution;not full bake,renderer,game or provider execution.','Native process settings are not a physical-memory bound or host-wide reclamation claim.']
    (destination/'receipt.json').write_text(json.dumps(public,indent=2)+'\n')
    print(json.dumps(dict(capture='evidence/'+capture.name,cases=r['cases'],observerErrors=r['observerErrors'],receiptSha256=sha(destination/'receipt.json'))))


if __name__=='__main__':main()
