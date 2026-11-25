#!/usr/bin/env python3
"""Owner-run Draft 7 library observations on original culling/biome schemas."""
import argparse
import copy
import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validator', type=Path, required=True)
    parser.add_argument('--wheels', type=Path, required=True)
    args = parser.parse_args()
    producer = Path(__file__).read_bytes()
    requests = (HERE / 'schema-cases.json').read_bytes()
    catalog_bytes = (HERE / 'catalog.json').read_bytes()
    catalog = json.loads(catalog_bytes)
    wheels = args.wheels.resolve()
    validator_path = args.validator.resolve()
    tool_receipt_bytes = (wheels / 'verified.json').read_bytes()
    tool_receipt = json.loads(tool_receipt_bytes)
    library_inputs = {}
    for wheel in tool_receipt['wheels']:
        artifact = wheels / wheel['file']
        assert sha(artifact.read_bytes()) == wheel['sha256']
        with zipfile.ZipFile(artifact) as archive:
            for name in archive.namelist():
                if name.endswith('/') or '.dist-info/' in name:
                    continue
                assert '..' not in Path(name).parts
                expected = archive.read(name)
                actual = (validator_path / name).read_bytes()
                assert expected == actual, name
                library_inputs[name] = sha(actual)
    sys.path.insert(0, str(validator_path))
    from jsonschema import Draft7Validator
    from referencing import Registry
    from referencing.exceptions import NoSuchResource
    assert importlib.metadata.version('jsonschema') == '4.26.0'
    assert Path(sys.modules['jsonschema'].__file__).resolve().is_relative_to(validator_path)
    def deny(uri):
        raise NoSuchResource(ref=uri)
    registry = Registry(retrieve=deny)
    selected = [s for s in catalog['sources'] if s['kind'] == 'client-json-schema' and
                (s['path'].endswith('/Culling.json') or 'Identifier Client Biome Component.json' in s['path'])]
    assert len(selected) == 18
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    capture = ROOT / '.build/minecraft' / ('bedrock-schema-' + stamp)
    capture.mkdir(parents=True, exist_ok=False)
    for name, raw in [('schema_probe.py', producer), ('schema-cases.json', requests), ('tool-inputs.json', tool_receipt_bytes)]:
        (capture / name).write_bytes(raw)
    inputs = json.loads(requests)
    observations, source_records = [], []
    for source in selected:
        path = ROOT / '.build/minecraft/bedrock-sources/blobs' / (source['gitBlob'] + '.blob')
        raw = path.read_bytes()
        assert sha(raw) == source['sha256'] and len(raw) == source['bytes']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == source['gitBlob']
        schema = json.loads(raw)
        assert schema['$schema'] == 'http://json-schema.org/draft-07/schema#'
        assert all('$ref' not in n or n['$ref'].startswith('#/definitions/') for n in walk(schema))
        Draft7Validator.check_schema(schema)
        validator = Draft7Validator(schema, registry=registry)
        culling = source['path'].endswith('/Culling.json')
        if culling:
            cases = inputs['culling']
        else:
            field, = schema['required']
            assert field in schema['properties']
            cases = []
            for r in inputs['biome']:
                value = {} if r.get('missing') else {'unrelated': 'study:settings'} if r.get('wrongField') else {field: r.get('value')}
                if r.get('extra'):
                    value['unknown_property'] = {'nested': None}
                if r.get('notObject'):
                    value = []
                cases.append(dict(id=r['id'], input=value))
        for request in cases:
            value = copy.deepcopy(request['input'])
            before = json.dumps(value, sort_keys=True, separators=(',', ':'))
            errors = list(validator.iter_errors(value))
            unchanged = before == json.dumps(value, sort_keys=True, separators=(',', ':'))
            observations.append(dict(source=source['id'], case=request['id'], kind='culling' if culling else 'biome-identifier',
                input=request['input'], accepted=not errors, instanceUnchanged=unchanged,
                errors=[dict(keyword=e.validator, instancePath=list(e.absolute_path), schemaPath=list(e.absolute_schema_path)) for e in errors]))
        source_records.append(source)
    assert Path(__file__).read_bytes() == producer and (HERE / 'schema-cases.json').read_bytes() == requests
    result = dict(schema=1, kind='Draft7Validator library observations; not Bedrock client', cases=observations)
    result_bytes = (json.dumps(result, indent=2) + '\n').encode()
    (capture / 'observed.json').write_bytes(result_bytes)
    (capture / 'sources.json').write_text(json.dumps(source_records, indent=2) + '\n')
    receipt = dict(schema=1, validator='jsonschema.Draft7Validator', validatorVersion='4.26.0',
        python=platform.python_version(), host=dict(system=platform.system(), release=platform.release(), machine=platform.machine()),
        producerSha256=sha(producer), requestsSha256=sha(requests), catalogSha256=sha(catalog_bytes),
        wheelReceiptSha256=sha(tool_receipt_bytes), installedLibraryInputsSha256=library_inputs,
        observedSha256=sha(result_bytes), sourcesSha256=sha((capture / 'sources.json').read_bytes()),
        schemas=len(selected), cases=len(observations), nativeClientOperations=0, subprocesses=0,
        networkDuringValidation='No remote references admitted; registry retrieval rejects every URI.',
        allInstancesUnchanged=all(o['instanceUnchanged'] for o in observations),
        limits=['Original source schemas and selected standard validator; not a Bedrock parser or engine.',
                'No context/reference existence, mesh culling, pipeline application, defaults inserted by an engine, or rendering qualification.'])
    (capture / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (ROOT / '.build/minecraft/latest-bedrock-schema.json').write_text(json.dumps(dict(capture=str(capture))) + '\n')
    print(json.dumps(dict(capture=str(capture.relative_to(ROOT)), schemas=len(selected), cases=len(observations), allInstancesUnchanged=receipt['allInstancesUnchanged'], nativeClientOperations=0)))


if __name__ == '__main__':
    main()
