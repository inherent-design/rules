#!/usr/bin/env python3
"""Export generated static facts, not client class files or executable bodies."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def aggregate(records):
    classes=[r for r in records if r['kind']=='class'];calls=[r for r in records if r['kind']=='invoke'];end=records[-1]
    assert end['kind']=='summary' and len(classes)==end['classes'] and len(calls)==end['selectedInvokeInstructions']
    assert len({r['entry'] for r in classes})==len(classes)
    families={}
    for family in sorted({r['family'] for r in calls}):
        rows=[r for r in calls if r['family']==family]
        owners=Counter(r['owner'] for r in rows)
        families[family]=dict(instructions=len(rows),callerClasses=len({r['caller'] for r in rows}),targetMembers=len({(r['owner'],r['name'],r['type']) for r in rows}),ownerCounts=dict(sorted(owners.items())),sample=rows[0])
    return dict(schema=1,target='java-26.3-vanilla',summary=end,classVersions=[dict(major=a,minor=b,count=n) for (a,b),n in sorted(Counter((r['major'],r['minor']) for r in classes).items())],nativeDeclarations=sum(r['kind']=='native-declaration' for r in records),families=families,nonObservedDirectCallFamilies=[f for f in ['foreign-memory','unsafe'] if f not in families])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--metadata',type=Path,required=True);args=p.parse_args()
    capture=args.capture.resolve();r=json.loads((capture/'receipt.json').read_text());targets=json.loads((HERE/'targets.json').read_text());target=next(t for t in targets['javaReferences'] if t['id']==r['target'])
    assert r['clientSha256']==target['source']['clientSha256']
    for stem,c in zip(['compile','execute'],r['commands']):
        assert c['exitCode']==0 and not c['timedOut'] and c['ownedGroupAbsent']
        for s in ['stdout','stderr']:assert sha(capture/(stem+'.'+s))==c[s+'Sha256']
    for n,d in r['sourcesSha256'].items():assert sha(capture/n)==d
    assert sha(capture/'classes/study/host/HostApiScan.class')==r['classSha256']
    assert sha(args.metadata)==target['source']['metadataSha256']
    meta=json.loads(args.metadata.read_text());raw=(capture/'execute.stdout').read_bytes();facts=aggregate([json.loads(l) for l in raw.splitlines()])
    destination=HERE/'evidence'/capture.name;destination.mkdir(parents=True,exist_ok=False)
    for n in list(r['sourcesSha256'])+['compile.stdout','compile.stderr','execute.stderr']:shutil.copyfile(capture/n,destination/n)
    (destination/'invoke-facts.jsonl.gz').write_bytes(gzip.compress(raw,mtime=0))
    public={k:v for k,v in r.items() if k not in ['commands','tools']}
    public['tools']={k:dict(executable=Path(v['path']).name,sha256=v['sha256']) for k,v in r['tools'].items()}
    public['commands']=[{k:v for k,v in c.items() if k!='argv'}|dict(argvDisclosure='Exact local argv retained privately; frozen collector constructs it.') for c in r['commands']]
    public['privateReceiptSha256']=sha(capture/'receipt.json');public['compressedFactsSha256']=sha(destination/'invoke-facts.jsonl.gz')
    public['limits']=['Static direct invoke instructions in the original client JAR only;not call-graph reachability or runtime execution.','Reflection,invokedynamic targets,dependencies external to this JAR,native libraries and driver calls are not resolved.','Counts include constructors,accessors and exception construction;they are not counts of side effects.','No observed direct FFM call in this client is not proof of no FFM use anywhere in its dependencies.','All native/backend/runtime/resource-lifecycle qualification remains independently pending.']
    (destination/'receipt.json').write_text(json.dumps(public,indent=2)+'\n')
    facts['capture']='evidence/'+capture.name;facts['libraries']=meta['libraries'];facts['libraryScope']='Exact launcher declarations,including their original rule predicates;not evaluated platform availability or downloaded/loaded native artifacts.'
    facts['limits']=public['limits']
    (HERE/'host-api-26.3.json').write_text(json.dumps(facts,indent=2)+'\n')
    print(json.dumps(dict(destination=str(destination),compressedBytes=(destination/'invoke-facts.jsonl.gz').stat().st_size,summary=facts['summary'])))


if __name__=='__main__':main()
