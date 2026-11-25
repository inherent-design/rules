#!/usr/bin/env python3
"""Check retained versioned registration/source identities, not source semantics."""
import copy
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def verify(catalog,findings,older,later,classes,target):
    assert catalog['schema']==findings['schema']==1 and catalog['target']==findings['target']==target['id']
    assert catalog['clientSha256']==findings['clientSha256']==target['source']['clientSha256']
    assert catalog['mappingSha256']==findings['mappingSha256']
    sources=catalog['sources']
    assert len(sources)==80 and len(catalog['categories'])==8
    for key,s in sources.items():
        assert key==target['id']+':'+s['className'] and s['profileSource']==target['id']
        assert classes[s['originalClassMember']]==s['originalClassSha256']
    comparisons={r['category']:r for r in findings['registrationComparisons']}
    total=0
    for category,group in catalog['categories'].items():
        entries=group['entries'];ids={e['id'] for e in entries};assert len(ids)==len(entries)
        assert group['registrationSource'] in sources
        assert all(e['source'] in sources and e['semanticReview'].startswith('pending') for e in entries)
        a={e['id'] for e in older[category]['entries']};c={e['id'] for e in later[category]['entries']};r=comparisons[category]
        assert r['counts']=={'1.21.5':len(a),'1.21.11':len(ids),'26.3':len(c)}
        assert r['addedInSelected12111']==sorted(ids-a) and r['absentFromSelected12111']==sorted(a-ids)
        assert r['addedInSelected263']==sorted(c-ids) and r['absentFromSelected263']==sorted(ids-c)
        total+=len(entries)
    assert total==72
    for s in findings['inspectedSources'].values():
        assert classes[s['original']['member']]==s['original']['sha256']
    return total


def main():
    catalog=json.loads((HERE/'java12111-registry-catalog.json').read_text());findings=json.loads((HERE/'java12111-findings.json').read_text())
    older=json.loads((HERE/'registry-catalog.json').read_text())['profiles']['minecraft-1.21.1+1.21.5']['categories'];later=json.loads((HERE/'later-registry-catalog.json').read_text())['categories']
    static=json.loads((HERE/'host-api-1.21.11.json').read_text());capture=HERE/static['capture'];r=json.loads((capture/'receipt.json').read_text());path=capture/'invoke-facts.jsonl.gz'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==r['compressedFactsSha256']
    records=[json.loads(v) for v in gzip.decompress(path.read_bytes()).splitlines()];classes={v['entry']:v['sha256'] for v in records if v['kind']=='class'}
    target=next(t for t in json.loads((HERE/'targets.json').read_text())['javaReferences'] if t['id']==catalog['target'])
    count=verify(catalog,findings,older,later,classes,target)
    for mode in range(4):
        c,f=copy.deepcopy(catalog),copy.deepcopy(findings)
        if mode==0:c['clientSha256']='0'*64
        elif mode==1:next(iter(c['categories'].values()))['entries'].pop()
        elif mode==2:next(iter(c['sources'].values()))['originalClassSha256']='0'*64
        else:next(iter(c['categories'].values()))['entries'][0]['semanticReview']='native-qualified'
        try:verify(c,f,older,later,classes,target)
        except (AssertionError,KeyError):pass
        else:raise AssertionError('Altered source attribution/scope admitted')
    print(json.dumps(dict(status='passed',registrations=count,sourceFiles=len(catalog['sources']),sourceIdentityAndScopeRefusals=4,nativeExecution=False,limits='Retained identity/set checks,not source translation or complete schemas.')))


if __name__=='__main__':main()
