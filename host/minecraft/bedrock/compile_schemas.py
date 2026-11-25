#!/usr/bin/env python3
"""Compile only the inspected culling/biome declaration subset; refuse drift."""
import argparse
import hashlib
import json
from pathlib import Path
from catalog import schema_nodes

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
DIRECTIONS = ['down', 'up', 'north', 'south', 'west', 'east']
CONDITIONS = ['same_culling_layer', 'same_block', 'same_block_permutation']
DOMAINS = {'atmosphere_identifier': 'atmospherics', 'color_grading_identifier': 'color_grading',
           'lighting_identifier': 'lighting', 'water_identifier': 'water', 'cubemap_identifier': 'cubemaps'}
KEYS = {'$id', '$schema', '$ref', 'definitions', 'type', 'properties', 'required', 'items', 'minimum',
        'enum', 'default', 'title', 'description', 'x-format-version', 'x-minecraft-version'}


def compile_document(document):
    assert document['$schema'] == 'http://json-schema.org/draft-07/schema#'
    for _, node in schema_nodes(document):
        assert type(node) is dict and not set(node) - KEYS
    def deref(node):
        if '$ref' not in node:
            return node
        assert not set(node) - {'$ref', 'description', 'title'}
        reference = node['$ref']
        assert reference.startswith('#/definitions/') and reference.count('/') == 2
        result = document['definitions'][reference.split('/')[-1]]
        assert '$ref' not in result
        return result
    def obj(node, required, fields):
        assert not set(node) - {'$id', '$schema', 'definitions', 'type', 'properties', 'required', 'title', 'description', 'x-format-version', 'x-minecraft-version'}
        assert node['type'] == 'object' and set(node['required']) == set(required)
        assert set(node['properties']) == set(fields)
    def string(node):
        node = deref(node)
        assert node['type'] == 'string'
        assert not set(node) - {'type', 'title', 'description'}
    if document['title'] != 'Block Culling':
        field, = document['required']
        assert field in DOMAINS and document['title'] == 'minecraft:' + field
        obj(document, [field], [field])
        string(document['properties'][field])
        domain = DOMAINS[field]
        assert '"' + domain + '" directory' in document['description']
        assert 'without this component will have default' in document['description']
        return dict(kind='biome-identifier', field=field, referenceDomain=domain, openProperties=True,
                    absenceDescription='documented default settings; not inserted by schema validation',
                    contextQualification='Identifier string is not resolved or pipeline-applied by this schema.')
    obj(document, ['description', 'rules'], ['description', 'rules'])
    description = deref(document['properties']['description'])
    obj(description, ['identifier'], ['identifier'])
    string(description['properties']['identifier'])
    array = document['properties']['rules']
    assert array['type'] == 'array' and set(array) == {'type', 'items'}
    rule = deref(array['items'])
    fields = rule['properties']
    declared = 'condition' in fields
    obj(rule, ['direction', 'geometry_part'], ['direction', 'geometry_part'] + (['condition', 'cull_against_full_and_opaque'] if declared else []))
    direction = fields['direction']
    assert direction['type'] == 'string' and direction['enum'] == DIRECTIONS and not set(direction) - {'type', 'enum', 'title'}
    geometry = deref(fields['geometry_part'])
    obj(geometry, ['bone'], ['bone', 'cube', 'face'])
    string(geometry['properties']['bone'])
    cube = geometry['properties']['cube']
    assert cube == {'type': 'integer', 'minimum': 0}
    face = geometry['properties']['face']
    assert face['type'] == 'string' and face['enum'] == DIRECTIONS and not set(face) - {'type', 'enum', 'title'}
    default = False
    if declared:
        condition = fields['condition']
        assert condition['type'] == 'string' and condition['enum'] == CONDITIONS and not set(condition) - {'type', 'enum', 'title'}
        opaque = fields['cull_against_full_and_opaque']
        assert opaque['type'] == 'boolean' and not set(opaque) - {'type', 'default'}
        if 'default' in opaque:
            assert opaque['default'] is True
            default = True
    return dict(kind='culling', conditionDeclared=declared, opaqueDeclared=declared,
                opaqueDefaultAnnotation=default, openProperties=True, directions=DIRECTIONS,
                conditions=CONDITIONS if declared else [], cubeMinimum=0,
                contextQualification='Bone/cube/face existence and actual neighbor culling remain unresolved.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    capture = args.capture.resolve()
    receipt = json.loads((capture / 'receipt.json').read_text())
    sources_raw = (capture / 'sources.json').read_bytes()
    assert sha(sources_raw) == receipt['sourcesSha256']
    sources = json.loads(sources_raw)
    records = []
    for source in sources:
        raw = (ROOT / '.build/minecraft/bedrock-sources/blobs' / (source['gitBlob'] + '.blob')).read_bytes()
        assert sha(raw) == source['sha256']
        document = json.loads(raw)
        records.append(dict(source=source['id'], declaredFormat=document['x-format-version'],
                            declaredMinecraftVersion=document.get('x-minecraft-version'),
                            declaration=compile_document(document)))
    result = dict(schema=1, compilerSha256=sha(Path(__file__).read_bytes()), profiles=records, sources=sources,
                  scope='Inspected Draft 7 declaration subset; not runtime schemas, actual culling, or reference resolution.')
    (HERE / 'schema-profiles.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status='compiled-inspected-declaration-subset', profiles=len(records))))


if __name__ == '__main__':
    main()
