#!/usr/bin/env python3
"""Validate the retained static host/API discovery census without Java or a game."""
import gzip
import hashlib
import json
from pathlib import Path
from export_host_api import aggregate

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def check(release):
    facts=json.loads((HERE/('host-api-'+release+'.json')).read_text());capture=HERE/facts['capture'];receipt=json.loads((capture/'receipt.json').read_text())
    compressed=capture/'invoke-facts.jsonl.gz';assert sha(compressed)==receipt['compressedFactsSha256']
    raw=gzip.decompress(compressed.read_bytes());assert hashlib.sha256(raw).hexdigest()==receipt['commands'][1]['stdoutSha256']
    records=[json.loads(line) for line in raw.splitlines()];computed=aggregate(records,receipt['target'])
    for k,v in computed.items():assert facts[k]==v,k
    classes={r['name']:r for r in records if r['kind']=='class'}
    for r in records:
        if r['kind']=='invoke':assert r['caller'] in classes and r['elementOrdinal']>=0
    for n,d in receipt['sourcesSha256'].items():assert sha(capture/n)==d
    assert all(c['exitCode']==0 and c['ownedGroupAbsent'] and not c['timedOut'] for c in receipt['commands'])
    targets=json.loads((HERE/'targets.json').read_text());target=next(t for t in targets['javaReferences'] if t['id']==facts['target']);assert target['source']['clientSha256']==receipt['clientSha256']
    assert facts['classVersions']==[dict(major=69 if release=='26.3' else 65,minor=0,count={'1.21.4':8857,'1.21.11':10291,'26.3':11383}[release])]
    assert len(facts['libraries'])==len({l['name'] for l in facts['libraries']})
    # These are identity/census checks. This replay does not infer method behavior.
    print(json.dumps(dict(status='passed',release=release,classes=len(classes),selectedInvokeInstructions=computed['summary']['selectedInvokeInstructions'],families=len(computed['families']),libraryDeclarations=len(facts['libraries']),nativeExecution=False)))


def main():
    for release in ['1.21.4','1.21.11','26.3']:check(release)


if __name__=='__main__':main()
