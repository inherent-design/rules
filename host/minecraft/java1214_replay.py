#!/usr/bin/env python3
"""Retained source/census identity checks, without acquiring or executing Java."""
import copy
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def verify(catalog, findings, classes, target, later):
    assert catalog['schema'] == findings['schema'] == 1
    assert catalog['target'] == findings['target'] == target['id'] == 'java-1.21.4-vanilla'
    assert catalog['clientSha256'] == findings['clientSha256'] == target['source']['clientSha256']
    assert catalog['mappingSha256'] == findings['mappingSha256']
    assert len(catalog['sources']) == 76 and len(catalog['categories']) == 8 and len(findings['inspectedSources']) == 12
    for key, r in catalog['sources'].items():
        assert key == target['id'] + ':' + r['className'] and r['profileSource'] == target['id']
        assert classes[r['originalClassMember']] == r['originalClassSha256']
    comparison = {r['category']:r for r in findings['registrationComparisons']}
    total = 0
    for kind, group in catalog['categories'].items():
        rows = group['entries']; ids = {r['id'] for r in rows}
        assert len(ids) == len(rows) and group['registrationSource'] in catalog['sources']
        assert all(r['source'] in catalog['sources'] and r['semanticReview'].startswith('pending') for r in rows)
        selected = {r['id'] for r in later[kind]['entries']}; c = comparison[kind]
        assert c['counts'] == {'1.21.4':len(ids),'1.21.5':len(selected)}
        assert c['onlySelected1214'] == sorted(ids-selected) and c['onlySelected1215'] == sorted(selected-ids)
        total += len(rows)
    assert total == 68
    for record in findings['inspectedSources'].values():
        assert classes[record['original']['member']] == record['original']['sha256']
        assert record['qualification'].startswith('Source interpretation;')


def main():
    catalog = json.loads((HERE / 'java1214-registry-catalog.json').read_text())
    findings = json.loads((HERE / 'java1214-findings.json').read_text())
    static = json.loads((HERE / 'host-api-1.21.4.json').read_text())
    capture = HERE / static['capture']; receipt = json.loads((capture / 'receipt.json').read_text())
    raw = capture / 'invoke-facts.jsonl.gz'; assert sha(raw) == receipt['compressedFactsSha256']
    classes = {r['entry']:r['sha256'] for r in map(json.loads,gzip.decompress(raw.read_bytes()).splitlines()) if r['kind'] == 'class'}
    target = next(t for t in json.loads((HERE / 'targets.json').read_text())['javaReferences'] if t['id'] == catalog['target'])
    later = json.loads((HERE / 'registry-catalog.json').read_text())['profiles']['minecraft-1.21.1+1.21.5']['categories']
    verify(catalog,findings,classes,target,later)
    for mode in range(4):
        c,f = copy.deepcopy(catalog),copy.deepcopy(findings)
        if mode == 0:c['target'] = 'java-1.21.5-vanilla'
        elif mode == 1:next(iter(c['sources'].values()))['originalClassSha256'] = '0'*64
        elif mode == 2:next(iter(c['categories'].values()))['entries'].pop()
        else:next(iter(c['categories'].values()))['entries'][0]['semanticReview'] = 'native-qualified'
        try:verify(c,f,classes,target,later)
        except (AssertionError,KeyError):pass
        else:raise AssertionError('Changed source/scope admitted')
    print(json.dumps(dict(status='passed',registrations=68,associatedSources=76,interpretedContracts=12,sourceIdentityAndScopeRefusals=4,nativeExecution=False)))


if __name__ == '__main__':main()
