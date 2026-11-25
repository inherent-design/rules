#!/usr/bin/env python3
"""Compare native identity facts with source-bound finite rules;no application execution."""
import argparse
import hashlib
import json
from pathlib import Path
from protocol import project,key,changed

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def vectors():
    v=json.loads((HERE/'vectors.json').read_text());assert v['schema']==1 and v['contract']=='protected-tree-preflight-v1'
    for name,h in v['sourceSha256'].items():assert sha(ROOT/name)==h,('Stale filesystem rule table',name)
    assert len(v['table'])==192
    return v['table']


def verify(raw,table):
    facts=project(raw);decisions={r['case']:table[key(r['input'])]for r in facts}
    assert all(value[1]==0 for value in decisions.values()),'Native fixture supplies no boundary-bound mutation grant.'
    for name in ['exact-object','target-contains-source','target-inside-source']:
        assert decisions[name][0]==2
    assert decisions['separate-sibling'][0]==3 and decisions['missing-target'][0]==1
    assert decisions['preflight-binding-replaced/stale'][0]==1
    assert decisions['preflight-binding-replaced/now'][0]==2
    for row in raw['cases']:
        if row['kind']=='pair'and row['observed']['samefile']is True:
            assert decisions[row['case']][0]==2
    return decisions


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('observations',type=Path,nargs='+');p.add_argument('--controls',action='store_true');a=p.parse_args()
    table=vectors();results=[]
    for path in a.observations:
        raw=json.loads(path.read_text());assert raw['producerSha256']==sha(HERE/'native.py'),'Unselected native producer.'
        decisions=verify(raw,table);controls=[]
        if a.controls:
            candidates=[]
            r,row=changed(raw,'exact-object');row['observed']['samefile']=False;candidates.append(('same-object-denied',r))
            r,row=changed(raw,'target-contains-source');row['observed']['sourceChain']['complete']=False;candidates.append(('ancestry-unconfirmed',r))
            r,row=changed(raw,'exact-object');row['observed']['target']['inode']='0';candidates.append(('invalid-identity',r))
            r,row=changed(raw,'preflight-binding-replaced');row['observed']['before']['target']=row['observed']['nowTarget'];candidates.append(('stale-token-forged-current',r))
            r=dict(raw,ownedSourcePreserved=False);candidates.append(('source-preservation-lost',r))
            r=dict(raw,schema=2);candidates.append(('unsupported-schema',r))
            for label,bad in candidates:
                try:verify(bad,table)
                except (AssertionError,KeyError):controls.append(label)
                else:raise AssertionError('Changed native observation admitted: '+label)
        results.append(dict(profile=raw['profile'],rawCases=len(raw['cases']),ruleComparisons=len(decisions),controls=controls,
                            preflight=decisions,nativeMutationAuthority=False))
    print(json.dumps(dict(schema=1,status='passed-owned-path-observations',results=results),indent=2))


if __name__=='__main__':main()
