#!/usr/bin/env python3
"""Replay retained validator observations; never import the validator or a client."""
import argparse
import copy
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
CAPTURE = 'evidence/bedrock-schema-20261125T090157538761Z'


def verify_profiles(document, catalog, facts):
    assert document['schema'] == 1 and document['compilerSha256'] == sha(HERE / 'compile_schemas.py')
    by_id = {s['id']: s for s in catalog['sources']}
    assert len(document['sources']) == len(document['profiles']) == 18
    assert len({p['source'] for p in document['profiles']}) == 18
    for s in document['sources']:
        assert s == by_id[s['id']]
    for p in document['profiles']:
        source = by_id[p['source']]
        f = facts['schemaFacts'][source['gitBlob']]
        nodes = {n['pointer']: n for n in f['nodes']}
        assert p['declaredFormat'] == f['formatVersion']
        assert (p['declaredMinecraftVersion'] is not None) == ('x-minecraft-version' in nodes['']['keywordNames'])
        d = p['declaration']
        assert d['openProperties'] is True
        assert all('additionalProperties' not in n['keywordNames'] for n in nodes.values())
        if d['kind'] == 'culling':
            assert nodes['']['type'] == 'object' and set(nodes['']['required']) == {'description', 'rules'}
            assert nodes['/properties/rules']['type'] == 'array'
            description = nodes[nodes['/properties/description']['reference'][1:]]
            assert description['type'] == 'object' and description['required'] == ['identifier']
            assert nodes[description['pointer'] + '/properties/identifier']['type'] == 'string'
            ref = nodes['/properties/rules/items']['reference'][1:]
            rule = nodes[ref]
            assert rule['type'] == 'object' and set(rule['required']) == {'direction', 'geometry_part'}
            geometry = nodes[nodes[ref + '/properties/geometry_part']['reference'][1:]]
            assert geometry['type'] == 'object' and geometry['required'] == ['bone']
            assert nodes[geometry['pointer'] + '/properties/bone']['type'] == 'string'
            cube = nodes[geometry['pointer'] + '/properties/cube']
            assert cube['type'] == 'integer' and cube['minimum'] == d['cubeMinimum'] == 0
            assert nodes[geometry['pointer'] + '/properties/face']['enum'] == d['directions']
            declared = 'condition' in rule['propertyNames']
            assert d['conditionDeclared'] == d['opaqueDeclared'] == declared
            opaque = nodes.get(ref + '/properties/cull_against_full_and_opaque', {})
            assert d['opaqueDefaultAnnotation'] == (opaque.get('defaultAnnotation') is True)
            assert nodes[ref + '/properties/direction']['enum'] == d['directions']
            if declared:
                assert nodes[ref + '/properties/condition']['enum'] == d['conditions']
            else:
                assert d['conditions'] == []
        else:
            assert d['kind'] == 'biome-identifier'
            assert nodes['']['required'] == [d['field']]
            field = nodes['/properties/' + d['field']]
            field = nodes[field['reference'][1:]] if 'reference' in field else field
            assert field['type'] == 'string'


def project(row, declaration):
    raw = row['input']
    profile = {k: declaration.get(k, False) for k in ['conditionDeclared', 'opaqueDeclared', 'opaqueDefaultAnnotation']}
    if row['kind'] == 'biome-identifier':
        data = dict(object=type(raw) is dict, requiredString=type(raw) is dict and type(raw.get(declaration['field'])) is str)
    else:
        assert row['kind'] == 'culling'
        obj = type(raw) is dict
        description = raw.get('description') if obj else None
        rules = raw.get('rules') if obj else None
        values = []
        if type(rules) is list:
            assert len(rules) <= 2
            for r in rules:
                rule = r if type(r) is dict else {}
                geometry = rule.get('geometry_part')
                geo = geometry if type(geometry) is dict else {}
                cube = geo.get('cube')
                cube_ok = 'cube' not in geo or (type(cube) in (int, float) and math.isfinite(cube) and cube >= 0 and int(cube) == cube)
                values.append(dict(object=type(r) is dict, direction=rule.get('direction') in declaration['directions'],
                    geometry=type(geometry) is dict, bone=type(geo.get('bone')) is str, cube=cube_ok,
                    face='face' not in geo or geo['face'] in declaration['directions'],
                    condition=0 if 'condition' not in rule else 1 if rule['condition'] in ['same_culling_layer', 'same_block', 'same_block_permutation'] else 2,
                    opaqueState=0 if 'cull_against_full_and_opaque' not in rule else 1 if rule['cull_against_full_and_opaque'] is True else 2 if rule['cull_against_full_and_opaque'] is False else 3))
        data = dict(object=obj, description=type(description) is dict,
                    identifier=type(description) is dict and type(description.get('identifier')) is str,
                    rulesArray=type(rules) is list, rules=values)
    return dict(kind=row['kind'], profile=profile, input=data)


def bend_expression(row):
    b = lambda v: 'True{}' if v else 'False{}'
    r = row['input']
    if row['kind'] == 'biome-identifier':
        return 'S.bs_biome(' + b(r['object']) + ',' + b(r['requiredString']) + ')'
    p = row['profile']
    spec = 'S.BSCullingSchema{' + ','.join(b(p[k]) for k in ['conditionDeclared', 'opaqueDeclared', 'opaqueDefaultAnnotation']) + '}'
    rules = 'Nil{}'
    for x in reversed(r['rules']):
        fields = [b(x[k]) for k in ['object', 'direction', 'geometry', 'bone', 'cube', 'face']] + [str(x[k]) + 'n' for k in ['condition', 'opaqueState']]
        rules = 'Con{S.BSRule{' + ','.join(fields) + '},' + rules + '}'
    data = 'S.BSCulling{' + ','.join([b(r[k]) for k in ['object', 'description', 'identifier', 'rulesArray']] + [rules]) + '}'
    return 'S.bs_culling(' + spec + ',' + data + ')'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    catalog = json.loads((HERE / 'catalog.json').read_text())
    facts = json.loads(gzip.decompress((HERE / 'source-facts.json.gz').read_bytes()))
    assert sha(HERE / 'source-facts.json.gz') == catalog['factsSha256']
    profiles = json.loads((HERE / 'schema-profiles.json').read_text())
    verify_profiles(profiles, catalog, facts)
    for mode in range(3):
        changed = copy.deepcopy(profiles)
        c = next(p for p in changed['profiles'] if p['declaration']['kind'] == 'culling')
        if mode == 0:
            c['declaration']['conditionDeclared'] = not c['declaration']['conditionDeclared']
        elif mode == 1:
            c['declaration']['opaqueDefaultAnnotation'] = not c['declaration']['opaqueDefaultAnnotation']
        else:
            c['declaredFormat'] = 'other'
        try:
            verify_profiles(changed, catalog, facts)
        except AssertionError:
            pass
        else:
            raise AssertionError('Changed declaration/identity admitted')
    capture = HERE / CAPTURE
    receipt = json.loads((capture / 'receipt.json').read_text())
    assert receipt['validatorVersion'] == '4.26.0' and receipt['nativeClientOperations'] == 0 and receipt['allInstancesUnchanged']
    for name, key in [('observed.json', 'observedSha256'), ('sources.json', 'sourcesSha256'), ('schema_probe.py', 'producerSha256'), ('schema-cases.json', 'requestsSha256'), ('tool-inputs.json', 'wheelReceiptSha256')]:
        assert sha(capture / name) == receipt[key]
    assert json.loads((capture / 'sources.json').read_text()) == profiles['sources']
    observations = json.loads((capture / 'observed.json').read_text())['cases']
    assert len(observations) == receipt['cases'] == 274
    assert all(type(r['accepted']) is bool and r['accepted'] == (not r['errors']) and r['instanceUnchanged'] for r in observations)
    by_id = {p['source']: p['declaration'] for p in profiles['profiles']}
    rows = [project(r, by_id[r['source']]) for r in observations]
    answers = [r['accepted'] for r in observations]
    work = ROOT / '.build/minecraft/bedrock-schema-replay'
    work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LEAN_PATH=os.environ.get('LEAN_PATH', str(ROOT / '.build/formal')), BEND_NO_TELEMETRY='1')
    envelope = lambda rs: dict(schema=1, edition='bedrock', oracle='jsonschema-4.26.0-draft7', cases=rs)
    def lean_run(request, name):
        path = work / (name + '.json'); path.write_text(json.dumps(request) + '\n')
        return subprocess.run([os.environ.get('LEAN', 'lean'), '--run', str(HERE / 'SchemaCase.lean'), str(path)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=40)
    def bend_run(rs, name):
        path = work / (name + '.bend')
        path.write_text('import Base\nimport ../../../host/minecraft/bedrock/SchemaContracts.bend as S\ndef bit(b: Bool) -> String:\n  Bool.pick(String,b,"1","0")\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join('bit(' + bend_expression(r) + ') ++ "\\n"' for r in rs) + ')\n')
        result = subprocess.run([os.environ.get('BEND', 'bend'), str(path)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=40)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout.splitlines()
    result = lean_run(envelope(rows), 'cases')
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == answers
    assert bend_run(rows, 'Cases') == ['1' if a else '0' for a in answers]
    negatives = [dict(envelope(rows), edition='java'), dict(envelope(rows), schema=2), dict(envelope(rows), oracle='bedrock-client'), envelope([dict(rows[0], kind='other')])]
    for field, value in [('condition', 3), ('opaqueState', 4)]:
        row = copy.deepcopy(rows[0]); row['input']['rules'][0][field] = value
        negatives.append(envelope([row]))
    row = copy.deepcopy(rows[0]); row['input']['rules'] *= 3; negatives.append(envelope([row]))
    for i, request in enumerate(negatives):
        assert lean_run(request, 'negative-' + str(i)).returncode == 2
    changes = []
    for case, key, value in [('ordinary', 'bone', False), ('cube-negative', 'cube', True), ('face-uppercase', 'face', True)]:
        i = next(i for i, r in enumerate(observations) if r['case'] == case and r['kind'] == 'culling')
        row = copy.deepcopy(rows[i]); row['input']['rules'][0][key] = value
        changes.append((i, row))
    i = next(i for i, r in enumerate(observations) if r['case'] == 'condition-number' and by_id[r['source']].get('conditionDeclared') is True)
    row = copy.deepcopy(rows[i]); row['profile']['conditionDeclared'] = False; changes.append((i, row))
    i = next(i for i, r in enumerate(observations) if r['case'] == 'missing' and r['kind'] == 'biome-identifier')
    row = copy.deepcopy(rows[i]); row['input']['requiredString'] = True; changes.append((i, row))
    for j, (i, row) in enumerate(changes):
        result = lean_run(envelope([row]), 'premise-' + str(j)); assert result.returncode == 0 and json.loads(result.stdout) != [answers[i]]
        assert bend_run([row], 'Premise' + str(j)) != ['1' if answers[i] else '0']
    basis = [HERE / n for n in ['SchemaContracts.lean', 'SchemaContracts.bend', 'SchemaCase.lean', 'schema-profiles.json', 'compile_schemas.py', 'schema_conformance.py', 'source-facts.json.gz', 'catalog.json']] + sorted(capture.iterdir())
    report = dict(schema=1, status='passed-retained-validator-comparisons', validatorObservations=274, sourceSchemas=18,
        nativeClientObservations=0, decoderRefusals=len(negatives), changedSourceProfiles=3, changedPremises=len(changes),
        basisSha256={str(p.relative_to(ROOT)): sha(p) for p in basis if p.is_file()},
        limits=['Original Draft 7 schemas evaluated by jsonschema4.26.0, not by a Bedrock executable.',
                'Projected parsed-JSON field/type states; no general wire grammar or complete schema engine proof.',
                'Validation does not insert defaults, resolve geometry/settings, cull faces, or apply a rendering pipeline.'])
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['status', 'validatorObservations', 'sourceSchemas', 'nativeClientObservations', 'decoderRefusals', 'changedSourceProfiles', 'changedPremises']}))


if __name__ == '__main__':
    main()
