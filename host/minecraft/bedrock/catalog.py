#!/usr/bin/env python3
"""Derive an attributable source map, not a Bedrock schema/runtime validator."""
import argparse
from collections import Counter, defaultdict
import hashlib
import gzip
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ESCAPE = lambda s: str(s).replace('~', '~0').replace('/', '~1')
ANNOTATIONS = ['type', 'required', 'enum', 'const', 'minimum', 'maximum', 'exclusiveMinimum',
               'exclusiveMaximum', 'minItems', 'maxItems', 'minLength', 'maxLength', 'uniqueItems']


def nodes(value, pointer=''):
    if isinstance(value, dict):
        yield pointer, value
        for key, child in value.items():
            yield from nodes(child, pointer + '/' + ESCAPE(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from nodes(child, pointer + '/' + str(index))


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def schema_nodes(value, pointer=''):
    """Visit schema locations; property names such as 'type' are ordinary data."""
    if type(value) is bool:
        yield pointer, value
        return
    assert isinstance(value, dict), pointer
    yield pointer, value
    for key in ['definitions', '$defs', 'properties', 'patternProperties']:
        for name, child in value.get(key, {}).items():
            yield from schema_nodes(child, pointer + '/' + key + '/' + ESCAPE(name))
    for key in ['additionalProperties', 'additionalItems', 'contains', 'propertyNames', 'not', 'if', 'then', 'else']:
        if key in value:
            yield from schema_nodes(value[key], pointer + '/' + key)
    for key in ['allOf', 'oneOf', 'anyOf']:
        for index, child in enumerate(value.get(key, [])):
            yield from schema_nodes(child, pointer + '/' + key + '/' + str(index))
    if 'items' in value:
        if isinstance(value['items'], list):
            for index, child in enumerate(value['items']):
                yield from schema_nodes(child, pointer + '/items/' + str(index))
        else:
            yield from schema_nodes(value['items'], pointer + '/items')
    for name, child in value.get('dependencies', {}).items():
        if not isinstance(child, list):
            yield from schema_nodes(child, pointer + '/dependencies/' + ESCAPE(name))


def schema_facts(document):
    records = []
    for pointer, node in schema_nodes(document):
        if type(node) is bool:
            records.append(dict(pointer=pointer, booleanSchema=node))
            continue
        r = dict(pointer=pointer, keywordNames=list(node), **{k: node[k] for k in ANNOTATIONS if k in node})
        if 'properties' in node:
            r['propertyNames'] = list(node['properties'])
        if '$ref' in node:
            r['reference'] = node['$ref']
        if 'default' in node:
            r['defaultAnnotation'] = node['default'] if not isinstance(node['default'], (dict, list)) else dict(valueSha256=fingerprint(node['default']))
        if 'additionalProperties' in node:
            r['additionalProperties'] = node['additionalProperties'] if type(node['additionalProperties']) is bool else 'nested-schema'
        records.append(r)
    return dict(title=document.get('title'), id=document.get('$id'), formatVersion=document.get('x-format-version'),
                dialect=document.get('$schema'), nodes=records,
                qualification='Structural declaration facts;composition,reference validation and actual client behavior are not executed.')


def doc_facts(document):
    sections, sketches = [], []
    declarations = defaultdict(lambda: dict(types=set(), optionalMarkers=set(), occurrences=0))
    for pointer, node in nodes(document):
        if not isinstance(node.get('name'), str):
            continue
        sections.append(dict(pointer=pointer, name=node['name']))
        lines = node.get('description', [])
        if not isinstance(lines, list):
            continue
        for index, line in enumerate(lines):
            if not isinstance(line, str):
                continue
            header = re.match(r'^\s*([A-Za-z_][\w-]*):([\d.]+):\{', line)
            if header:
                sketches.append(dict(pointer=pointer + '/description/' + str(index), family=header[1], declaredVersion=header[2]))
            field = re.match(r'^\s*([A-Za-z_][\w]*)\s+"([^"]+)"', line)
            if field:
                r = declarations[field[2]]
                r['types'].add(field[1]); r['optionalMarkers'].add(': opt' in line); r['occurrences'] += 1
    return dict(name=document.get('name'), sections=sections, schemaSketches=sketches,
        declarationCandidates=[dict(key=k, types=sorted(v['types']), optionalMarkers=sorted(v['optionalMarkers']), occurrences=v['occurrences']) for k, v in sorted(declarations.items())],
        qualification='Documentation names/declaration candidates;not complete grammar,scoped field ownership,defaults or engine implementation.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--private', type=Path, required=True)
    args = p.parse_args()
    private = args.private.resolve()
    capture = Path(json.loads((private / 'latest.json').read_text())['capture'])
    receipt = json.loads((capture / 'receipt.json').read_text())
    assert receipt['complete'] and sha(capture / 'plan.json') == receipt['planSha256']
    plan = json.loads((capture / 'plan.json').read_text())
    expected = {r['gitBlob']: r for r in receipt['results']}
    sources, schemas, docs, samples, parsed = [], {}, {}, {}, {}
    for row in plan['files']:
        path = private / 'blobs' / (row['gitBlob'] + '.blob')
        raw = path.read_bytes()
        assert len(raw) == row['bytes'] == expected[row['gitBlob']]['bytes'] and sha(path) == expected[row['gitBlob']]['sha256']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['gitBlob']
        kind = ('client-json-schema' if row['path'].startswith('metadata/json_schemas/client/') else
                'doc-module' if row['path'].startswith('metadata/doc_modules/') else
                'sample-json' if row['path'].startswith('resource_pack/') else 'source-context')
        source_id = row['target'] + ':' + row['path']
        sources.append(dict(id=source_id, **row, sha256=sha(path), kind=kind))
        if row['gitBlob'] not in parsed:
            try:
                parsed[row['gitBlob']] = (json.loads(raw.decode('utf-8-sig')), 'utf8-bom-removed' if raw.startswith(b'\xef\xbb\xbf') else 'strict-json')
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                parsed[row['gitBlob']] = (None, 'not-parsed-by-strict-study-reader:' + type(error).__name__)
        document, syntax = parsed[row['gitBlob']]
        if kind in ['client-json-schema', 'doc-module']:
            assert isinstance(document, dict), (source_id, syntax)
        if kind == 'client-json-schema':
            schemas.setdefault(row['gitBlob'], schema_facts(document))
        elif kind == 'doc-module':
            docs.setdefault(row['gitBlob'], doc_facts(document))
        elif kind == 'sample-json':
            sample = dict(syntax=syntax, rootKeys=list(document) if isinstance(document, dict) else None,
                          formatVersion=document.get('format_version') if isinstance(document, dict) else None,
                          qualification='One source example;not a normative schema or successful runtime admission.')
            if row['path'] == 'resource_pack/manifest.json':
                sample['minEngineVersion'] = document.get('header', {}).get('min_engine_version')
                sample['capabilities'] = document.get('capabilities', [])
            samples.setdefault(row['gitBlob'], sample)

    edges = []
    for source in sources:
        if source['kind'] != 'client-json-schema':
            continue
        fact = schemas[source['gitBlob']]
        for node in fact['nodes']:
            if 'reference' not in node:
                continue
            ref = node['reference']
            if ref.startswith('#/'):
                document = parsed[source['gitBlob']][0]
                try:
                    value = document
                    for token in ref[2:].split('/'):
                        value = value[token.replace('~1', '/').replace('~0', '~')]
                    matches = [source['id'] + ref]
                except (KeyError, TypeError):
                    matches = []
            else:
                matches = [s['id'] for s in sources if s['target'] == source['target'] and s['kind'] == 'client-json-schema' and schemas[s['gitBlob']]['id'] == ref]
            edges.append(dict(source=source['id'], pointer=node['pointer'], reference=ref,
                              candidates=matches, status='unique-source-candidate' if len(matches) == 1 else 'missing' if not matches else 'ambiguous'))
    profiles = []
    for plan_row in plan['plans']:
        selected = [s for s in sources if s['target'] == plan_row['target']]
        profiles.append(dict(**plan_row, kinds=dict(Counter(s['kind'] for s in selected)),
                             qualifiedNativeOperations=0, status='source map;semantic review incomplete'))
    facts = dict(schema=1, schemaFacts=schemas, docFacts=docs, sampleFacts=samples, referenceCandidates=edges)
    artifact = HERE / 'source-facts.json.gz'
    artifact.write_bytes(gzip.compress((json.dumps(facts, separators=(',', ':'), ensure_ascii=False) + '\n').encode(), mtime=0))
    result = dict(schema=1, status='source breadth map;not schema validation or client qualification',
        producerSha256=sha(Path(__file__)), acquisitionProducerSha256=receipt['producerSha256'],
        privateAcquisitionReceiptSha256=sha(capture / 'receipt.json'), profiles=profiles,
        sources=sources, factsFile=artifact.name, factsSha256=sha(artifact),
        counts=dict(schemaFiles=sum(s['kind'] == 'client-json-schema' for s in sources),
                    schemaNodeRecords=sum(len(s['nodes']) for s in schemas.values()),
                    docModules=sum(s['kind'] == 'doc-module' for s in sources), referenceCandidates=len(edges),
                    referenceStatuses=dict(Counter(e['status'] for e in edges))),
        limits=['Exact sample tags remain distinct from executable client versions and documentation chronology.',
                'No original text,code,schemas,artwork,audio or binaries are redistributed;public rows are attributed structural facts/candidates.',
                'Default annotations do not establish value insertion;required/properties and combinators need their original schema scope.',
                'Reference candidates are scoped source lookups,not a URI resolver or successful JSON Schema validation.',
                'Strict study-reader refusal or BOM normalization is not a native client parse result.',
                'Documentation candidates may repeat fields from different nested scopes;they must not be merged into one object schema.',
                'One sample per resource family is an anchor,not complete resource/asset coverage or renderer evidence.'])
    (HERE / 'catalog.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(profiles=len(profiles), sourceFiles=len(sources), uniqueBlobs=len(expected),
        schemaFiles=sum(s['kind'] == 'client-json-schema' for s in sources), schemaNodeRecords=sum(len(s['nodes']) for s in schemas.values()),
        docModules=sum(s['kind'] == 'doc-module' for s in sources), referenceCandidates=len(edges),
        referenceStatuses=dict(Counter(e['status'] for e in edges)))))


if __name__ == '__main__':
    main()
