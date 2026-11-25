#!/usr/bin/env python3
"""Export authored inputs/observers and original-method observations,not game payloads."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def export(capture,canonical):
    r=json.loads((capture/'receipt.json').read_text())
    assert len(r['commands'])==2 and all(c['ownedGroupAbsent'] and not c['timedOut'] for c in r['commands'])
    assert r['commands'][0]['exitCode']==0
    observed=json.loads((capture/'observed.json').read_text());assert sha(capture/'observed.json')==r['observedSha256'] and observed['observerErrors']==r['observerErrors']
    if canonical:assert r['commands'][1]['exitCode']==0 and observed['observerErrors']==0 and len(observed['cases'])==40
    destination=HERE/'evidence'/capture.name;destination.mkdir(parents=True,exist_ok=False)
    for n,d in r['sourceSha256'].items():assert sha(capture/n)==d;shutil.copyfile(capture/n,destination/n)
    for stem,c in zip(['compile','execute'],r['commands']):
        for stream in ['stdout','stderr']:
            n=stem+'.'+stream;assert sha(capture/n)==c[stream+'Sha256'];shutil.copyfile(capture/n,destination/n)
    shutil.copyfile(capture/'observed.json',destination/'observed.json')
    for n in ['disposition.json','comparison-to-retained-prefixes.json']:
        if (capture/n).exists():shutil.copyfile(capture/n,destination/n)
    original=capture/'library-input.json'
    if not original.exists():original=capture/'library-receipt-preserved-after-run.json'
    assert sha(original)==r['libraryReceiptSha256']
    public={k:v for k,v in r.items() if k not in ['commands','tools','libraries']}
    public['tools']={k:dict(executable=Path(v['path']).name,sha256=v['sha256']) for k,v in r['tools'].items()}
    public['libraries']=[{k:v for k,v in row.items() if k!='path'}|dict(file=Path(row['path']).name) for row in r['libraries']]
    public['commands']=[{k:v for k,v in c.items() if k!='argv'}|dict(argvDisclosure='Exact owner-local argv retained privately; frozen authored collector constructs it.') for c in r['commands']]
    public['privateReceiptSha256']=sha(capture/'receipt.json');public['comparisonEligibility']='canonical-selected-method-scope' if canonical else 'retained-harness-history;not-comparison-basis'
    public['limits']=['Original unmodified client JAR;only the authored observer is compiled. No original class,library,mapping or artwork payload exported.','Selected private decoder methods/public format codecs,not complete model/pack parsing,resource lookup,bootstrap/world/render/provider behavior.','Matrices are retained native values;the decision model does not prove general float/trigonometric geometry or rendered equivalence.','JVM heap128MiB/activeprocessors2 are process settings,not a total physical-memory bound.','Process-group retirement records do not imply global host memory reclamation.']
    (destination/'receipt.json').write_text(json.dumps(public,indent=2)+'\n')
    return dict(capture='evidence/'+capture.name,receiptSha256=sha(destination/'receipt.json'),eligible=canonical,cases=len(observed['cases']),observerErrors=observed['observerErrors'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--private',type=Path,required=True);args=p.parse_args();private=args.private.resolve()
    names=['later-codecs-26.3-20261125T063014804828Z','later-codecs-26.3-20261125T063217201221Z','later-codecs-26.3-20261125T063616185829Z','later-codecs-26.3-20261125T064027971144Z']
    records=[export(private/name,i==3) for i,name in enumerate(names)]
    (HERE/'evidence/later-collector-dispositions.json').write_text(json.dumps(dict(schema=1,records=records,canonical=records[-1]['capture'],reason='Early missing dependencies caused initialization failures. A clean full JVM supplies one consistent comparison basis;prior partial/completion records are unchanged and retained.',limits=['Four executions contain125method/codec calls;comparison counts40unique canonical inputs,not125independentqualified cases.','No first/partial observer error is a product refusal.']),indent=2)+'\n')
    print(json.dumps(dict(exportedCaptures=len(records),canonicalCases=40,retainedObserverErrors=[r['observerErrors'] for r in records])))


if __name__=='__main__':main()
