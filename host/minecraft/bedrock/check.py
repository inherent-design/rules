#!/usr/bin/env python3
"""Check the retained source map; no download, engine or schema validator."""
import copy
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import urllib.parse

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def verify(catalog, facts, targets):
    assert catalog['schema'] == facts['schema'] == 1
    expected = {t['id']: t for t in targets['bedrockReferences']}
    assert {p['target'] for p in catalog['profiles']} == set(expected)
    sources = {s['id']: s for s in catalog['sources']}
    assert len(sources) == len(catalog['sources'])
    for source in sources.values():
        target = expected[source['target']]
        assert source['id'] == source['target'] + ':' + source['path']
        assert re.fullmatch('[0-9a-f]{40}', source['gitBlob']) and re.fullmatch('[0-9a-f]{64}', source['sha256'])
        assert source['url'] == 'https://raw.githubusercontent.com/Mojang/bedrock-samples/' + target['source']['commit'] + '/' + urllib.parse.quote(source['path'], safe='/')
        assert type(source['bytes']) is int and source['bytes'] >= 0
        if source['kind'] == 'client-json-schema':
            assert source['gitBlob'] in facts['schemaFacts']
        elif source['kind'] == 'doc-module':
            assert source['gitBlob'] in facts['docFacts']
        elif source['kind'] == 'sample-json':
            assert source['gitBlob'] in facts['sampleFacts']
        else:
            assert source['kind'] == 'source-context'
    for profile in catalog['profiles']:
        target = expected[profile['target']]
        assert profile['commit'] == target['source']['commit']
        assert profile['treeResponseSha256'] == target['source']['treeResponseSha256']
        selected = [s for s in sources.values() if s['target'] == profile['target']]
        assert profile['kinds'] == dict(Counter(s['kind'] for s in selected))
        assert len(selected) == profile['selectedFiles'] and profile['qualifiedNativeOperations'] == 0
        for name in profile['exampleAnchors'].values():
            assert sources[profile['target'] + ':' + name]['kind'] == 'sample-json'
    for value in facts['schemaFacts'].values():
        assert len({n['pointer'] for n in value['nodes']}) == len(value['nodes'])
        for node in value['nodes']:
            if 'type' in node:
                assert isinstance(node['type'], str) or (isinstance(node['type'], list) and all(isinstance(t, str) for t in node['type']))
            for key in ['required', 'propertyNames']:
                if key in node:
                    assert isinstance(node[key], list) and all(isinstance(k, str) for k in node[key])
            if 'enum' in node:
                assert isinstance(node['enum'], list)
    for edge in facts['referenceCandidates']:
        source = sources[edge['source']]
        schema = facts['schemaFacts'][source['gitBlob']]
        assert any(n.get('reference') == edge['reference'] and n['pointer'] == edge['pointer'] for n in schema['nodes'])
        assert edge['status'] == ('unique-source-candidate' if len(edge['candidates']) == 1 else 'missing' if not edge['candidates'] else 'ambiguous')
        for name in edge['candidates']:
            other = sources[name.split('#', 1)[0]]
            assert other['target'] == source['target']
            assert other['kind'] == 'client-json-schema'
        ref = edge['reference']
        if ref.startswith('#/'):
            assert edge['candidates'] == [source['id'] + ref]
            assert any(n['pointer'] == ref[1:] for n in schema['nodes'])
        else:
            expected_candidates = [s['id'] for s in sources.values() if s['target'] == source['target'] and s['kind'] == 'client-json-schema' and facts['schemaFacts'][s['gitBlob']]['id'] == ref]
            assert edge['candidates'] == expected_candidates
    counts = catalog['counts']
    assert counts['schemaFiles'] == sum(s['kind'] == 'client-json-schema' for s in sources.values())
    assert counts['schemaNodeRecords'] == sum(len(s['nodes']) for s in facts['schemaFacts'].values())
    assert counts['docModules'] == sum(s['kind'] == 'doc-module' for s in sources.values())
    assert counts['referenceCandidates'] == len(facts['referenceCandidates'])
    assert counts['referenceStatuses'] == dict(Counter(e['status'] for e in facts['referenceCandidates']))


def main():
    catalog = json.loads((HERE / 'catalog.json').read_text())
    assert catalog['factsFile'] == 'source-facts.json.gz'
    artifact = HERE / catalog['factsFile']
    assert sha(artifact) == catalog['factsSha256']
    facts = json.loads(gzip.decompress(artifact.read_bytes()))
    targets = json.loads((HERE.parent / 'targets.json').read_text())
    verify(catalog, facts, targets)
    negative = []
    for operation in range(5):
        c, f = copy.deepcopy(catalog), copy.deepcopy(facts)
        if operation == 0:
            c['sources'][0]['target'] = 'java-26.3-vanilla'
        elif operation == 1:
            c['sources'][0]['sha256'] = 'not-a-digest'
        elif operation == 2:
            c['sources'].append(c['sources'][0])
        elif operation == 3:
            first = next(iter(f['schemaFacts'].values()))
            first['nodes'][0]['type'] = {'type': 'string'}
        else:
            f['referenceCandidates'][0]['candidates'] = ['unavailable-source']
        try:
            verify(c, f, targets)
        except (AssertionError, KeyError):
            negative.append('refused')
        else:
            raise AssertionError('Broken source map admitted')
    # A property named type/required must not be interpreted as a schema keyword.
    from catalog import schema_facts
    witness = schema_facts({'type': 'object', 'properties': {'type': {'type': 'string'}, 'required': {'type': 'boolean'}}, 'required': ['type']})
    assert [(n['pointer'], n.get('type')) for n in witness['nodes']] == [('', 'object'), ('/properties/type', 'string'), ('/properties/required', 'boolean')]
    assert witness['nodes'][0]['required'] == ['type']
    print(json.dumps(dict(status='passed', profiles=len(catalog['profiles']), sourceFiles=len(catalog['sources']),
                          **catalog['counts'], changedSourceMapRefusals=len(negative), schemaLocationControl='passed',
                          limits='Integrity/census only;not native client,JSON Schema conformance or complete semantic coverage.')))


if __name__ == '__main__':
    main()
