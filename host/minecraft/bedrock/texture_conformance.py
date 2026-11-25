#!/usr/bin/env python3
"""Compare authored source interpretations with two models; no client observation."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REVISION = '80b7b1713df821debb4a8022e32e6b0ad840a273'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def source_check(document):
    assert document['schema'] == 1 and document['edition'] == 'bedrock'
    assert document['documentationRevision'] == REVISION
    catalog = {s['id']: s for s in json.loads((HERE / 'catalog.json').read_text())['sources']}
    expected = {'texture-sets.md': '0d1d874e74031e2c0c5494ddc9ac7ec56c460a285869a2bf1e3514d827803c30',
                'vibrant-packs.md': 'bf5fca7055a0847e4f273d866e1f24372d76cab7d4aeb1963c6ccbfd587a099e'}
    assert len(document['sources']) == 5 and len(document['claims']) == 8
    for s in document['sources']:
        if s['kind'] == 'documentation':
            assert s['commit'] == REVISION and s['repository'] == 'MicrosoftDocs/minecraft-creator'
            assert s['sha256'] == expected.pop(s['id'])
            assert s['url'] == 'https://raw.githubusercontent.com/' + s['repository'] + '/' + REVISION + '/' + s['path']
        else:
            previous = catalog[s['id']]
            assert all(s[k] == previous[k] for k in ['target', 'path', 'gitBlob', 'sha256', 'bytes'])
    assert not expected
    assert all(c['status'] == 'source-interpreted; native comparison absent' for c in document['claims'])


def bend_expression(row):
    action, r = row['action'], row['data']
    b = lambda v: 'True{}' if v else 'False{}'
    n = lambda v: str(v) + 'n'
    def linked(items):
        value = 'Nil{}'
        for item in reversed(items):
            value = 'Con{' + item + ',' + value + '}'
        return value
    if action == 'issues':
        fields = [b(r[k]) for k in ['color', 'normal', 'height', 'mer', 'mers']] + [n(r['backing'])] + [b(r[k]) for k in ['vibrant', 'textureObject', 'uniformMersVariation']]
        return 'Nat.show(T.ts_issues(T.TSInput{' + ','.join(fields) + '}))'
    if action == 'channels':
        return 'bit(T.ts_channels(' + ','.join([n(r['layer']), b(r['image']), n(r['count'])]) + '))'
    if action == 'resolve':
        images = linked(['T.TSImage{' + ','.join(n(i[k]) for k in ['pack', 'name', 'extension', 'contentToken']) + '}' for i in r['images']])
        return 'optional(T.ts_resolve(' + n(r['pack']) + ',' + n(r['name']) + ',' + images + '))'
    if action == 'select':
        definitions = linked(['T.TSDefinition{' + ','.join(n(d[k]) for k in ['name', 'pack', 'layers']) + '}' for d in r['eligible']])
        return 'definition(T.ts_select(' + n(r['name']) + ',' + definitions + '))'
    if action == 'declare':
        return 'declaration(T.ts_declares(' + ','.join([b(r['pbr']), b(r['raytraced']), *(n(r[k]) for k in ['major', 'minor', 'patch'])]) + '))'
    assert action == 'material'
    return 'material(T.ts_predominant(' + n(r['metal']) + ',' + n(r['subsurface']) + '))'


RENDER = '''import Base
import ../../../host/minecraft/bedrock/TextureSets.bend as T
def bit(b: Bool) -> String:
  Bool.pick(String,b,"1","0")
def optional(v: Maybe<&2,Nat>) -> String:
  match v:
    case None{}: "none"
    case Some{n}: Nat.show(n)
def definition(v: Maybe<&2,T.TSDefinition>) -> String:
  match v:
    case None{}: "none"
    case Some{T.TSDefinition{n,p,l}}: Nat.show(n) ++ "/" ++ Nat.show(p) ++ "/" ++ Nat.show(l)
def declaration(v: T.TSDeclaration) -> String:
  match v:
    case T.TSDeclaration{p,r}: bit(p) ++ "/" ++ bit(r)
def material(v: T.TSMaterial) -> String:
  match v:
    case T.TSMaterial{m,s}: Nat.show(m) ++ "/" ++ Nat.show(s)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    source = json.loads((HERE / 'texture-sources.json').read_text())
    source_check(source)
    for mode in range(4):
        bad = copy.deepcopy(source)
        if mode == 0:
            bad['edition'] = 'java'
        elif mode == 1:
            bad['documentationRevision'] = 'earlier-sample-tag'
        elif mode == 2:
            bad['sources'][0]['sha256'] = '0' * 64
        else:
            bad['claims'][0]['status'] = 'native-qualified'
        try:
            source_check(bad)
        except AssertionError:
            pass
        else:
            raise AssertionError('Changed source identity or qualification admitted')
    cases = json.loads((HERE / 'texture-cases.json').read_text())
    assert cases['edition'] == 'bedrock' and cases['documentationRevision'] == REVISION
    rows = cases['cases']
    ids = {r['id'] for r in rows}
    assert len(ids) == len(rows) == 44
    claims = {c['id'] for c in source['claims']} | {source['researchPolicy']['id']}
    assert all(r['basis'] in claims and r['evidence'] == 'authored documentation interpretation; not native observation' for r in rows)
    expected = [r['expected'] for r in rows]
    work = ROOT / '.build/minecraft/bedrock-texture-replay'
    work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LEAN_PATH=os.environ.get('LEAN_PATH', str(ROOT / '.build/formal')), BEND_NO_TELEMETRY='1')
    envelope = lambda rs: dict(schema=1, edition='bedrock', documentationRevision=REVISION, cases=rs)
    def lean_run(request, name):
        path = work / (name + '.json')
        path.write_text(json.dumps(request) + '\n')
        return subprocess.run([os.environ.get('LEAN', 'lean'), '--run', str(HERE / 'TextureCase.lean'), str(path)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
    def bend_run(rs, name):
        path = work / (name + '.bend')
        path.write_text(RENDER + 'def main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(bend_expression(r) + ' ++ "\\n"' for r in rs) + ')\n')
        result = subprocess.run([os.environ.get('BEND', 'bend'), str(path)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout.splitlines()
    result = lean_run(envelope(rows), 'cases')
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == expected
    assert bend_run(rows, 'Cases') == expected
    negatives = [dict(envelope(rows), schema=2), dict(envelope(rows), edition='java'),
                 dict(envelope(rows), documentationRevision='earlier-sample-tag'),
                 envelope([dict(action='other', data={})])]
    for id, key, value in [('baseline', 'backing', 3), ('rgb-color-image', 'layer', 5), ('metal-wins', 'metal', 256)]:
        row = copy.deepcopy(next(r for r in rows if r['id'] == id)); row['data'][key] = value
        negatives.append(envelope([row]))
    row = copy.deepcopy(next(r for r in rows if r['id'] == 'local-png-foreign-tga'))
    row['data']['images'].append(row['data']['images'][0])
    negatives.append(envelope([row]))
    for i, bad in enumerate(negatives):
        assert lean_run(bad, 'negative-' + str(i)).returncode == 2
    changes = [('baseline', 'color', False), ('unmeasured-backing', 'backing', 1),
               ('local-png-foreign-tga', 'pack', 2), ('raytraced-alternative', 'raytraced', False),
               ('tie', 'metal', 65)]
    for i, (id, key, value) in enumerate(changes):
        rs = copy.deepcopy(rows)
        next(r for r in rs if r['id'] == id)['data'][key] = value
        result = lean_run(envelope(rs), 'premise-' + str(i))
        assert result.returncode == 0 and json.loads(result.stdout) != expected
        assert bend_run(rs, 'Premise' + str(i)) != expected
    files = ['TextureSets.lean', 'TextureSets.bend', 'TextureCase.lean', 'texture-cases.json', 'texture-sources.json', 'texture_conformance.py']
    report = dict(schema=1, status='passed-source-interpretation-cases', nativeObservations=0,
                  cases=len(rows), decoderRefusals=len(negatives), sourceScopeRefusals=4, changedPremises=len(changes),
                  documentationRevision=REVISION, basisSha256={n: sha(HERE / n) for n in files},
                  limits=['Authored expected results interpret the selected documentation; agreement is not native conformance.',
                          'Issue bits and unknown-backing holds are research policy, not existing diagnostic order or codes.',
                          'Eligible definition ordering is supplied; invalid-higher-definition fallback is not modeled.',
                          'Logical pack/name/content tokens are not physical admission, decoded bytes, rendering, or leases.'])
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
