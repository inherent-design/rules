#!/usr/bin/env python3
"""Owner-local source audit and compiler drift controls; no validator/client rerun."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from compile_schemas import compile_document

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--wheels', type=Path, required=True)
    args = parser.parse_args()
    capture = args.capture.resolve()
    receipt = json.loads((capture / 'receipt.json').read_text())
    source_raw = (capture / 'sources.json').read_bytes()
    assert sha(source_raw) == receipt['sourcesSha256']
    sources = json.loads(source_raw)
    original = {}
    for source in sources:
        raw = (ROOT / '.build/minecraft/bedrock-sources/blobs' / (source['gitBlob'] + '.blob')).read_bytes()
        assert len(raw) == source['bytes'] and sha(raw) == source['sha256']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == source['gitBlob']
        original[source['id']] = json.loads(raw)
    for name, key in [('schema_probe.py', 'producerSha256'), ('schema-cases.json', 'requestsSha256'), ('observed.json', 'observedSha256'), ('tool-inputs.json', 'wheelReceiptSha256')]:
        assert sha((capture / name).read_bytes()) == receipt[key]
    tool = json.loads((capture / 'tool-inputs.json').read_text())
    for wheel in tool['wheels']:
        raw = (args.wheels / wheel['file']).read_bytes()
        assert len(raw) == wheel['bytes'] and sha(raw) == wheel['sha256']
    profiles = json.loads((HERE / 'schema-profiles.json').read_text())
    for row in profiles['profiles']:
        assert compile_document(original[row['source']]) == row['declaration']
        assert row['declaredMinecraftVersion'] == original[row['source']].get('x-minecraft-version')
    selected = next(s for s in sources if s['target'] == 'bedrock-samples-1.26.30.5' and s['path'].endswith('block/1.21.80/Culling.json'))
    for mode in range(5):
        document = copy.deepcopy(original[selected['id']])
        if mode == 0:
            document['additionalProperties'] = False
        elif mode == 1:
            document['enum'] = [{}]
        else:
            rule = next(d for d in document['definitions'].values() if 'direction' in d.get('properties', {}))
            if mode == 2:
                geometry = next(d for d in document['definitions'].values() if 'cube' in d.get('properties', {}))
                geometry['properties']['cube']['minimum'] = 1
            elif mode == 3:
                rule['properties']['condition']['enum'].pop()
            else:
                rule['properties']['cull_against_full_and_opaque']['default'] = False
        try:
            compile_document(document)
        except AssertionError:
            pass
        else:
            raise AssertionError('Unmodeled schema drift compiled')
    observations = json.loads((capture / 'observed.json').read_text())['cases']
    lookup = {(r['source'], r['case']): r for r in observations}
    findings = []
    for p in profiles['profiles']:
        if p['declaration']['kind'] == 'culling':
            findings.append(dict(source=p['source'], declaredFormat=p['declaredFormat'],
                conditionDeclared=p['declaration']['conditionDeclared'], defaultAnnotation=p['declaration']['opaqueDefaultAnnotation'],
                numericConditionAdmitted=lookup[(p['source'], 'condition-number')]['accepted'],
                stringOpaqueAdmitted=lookup[(p['source'], 'opaque-string')]['accepted'],
                missingOpaqueInputUnchanged=lookup[(p['source'], 'ordinary')]['instanceUnchanged']))
        else:
            assert lookup[(p['source'], 'empty-string')]['accepted'] and not lookup[(p['source'], 'missing')]['accepted']
    result = dict(schema=1, kind='source-schema/library findings; not Bedrock client behavior', culling=findings,
        biomeIdentifiers=dict(schemas=13, allEmptyStringsAdmitted=True, allMissingRequiredStringsRefused=True, referenceResolutionExecuted=False),
        compilerUnsupportedDriftRefusals=5,
        limits=['Unknown properties accepted by this schema need not be recognized or applied by an engine.',
                'Default annotations and instance nonmutation do not determine runtime defaults.'])
    (HERE / 'schema-findings.json').write_text(json.dumps(result, indent=2) + '\n')
    audit = dict(schema=1, status='passed-owner-local-source-audit', producerSha256=sha(Path(__file__).read_bytes()),
                 sourceSchemas=len(sources), wheelArtifacts=len(tool['wheels']), wheelLogicalBytes=tool['logicalBytes'],
                 sourceHashesAndGitBlobsRecomputed=True, validatorReruns=0, nativeClientOperations=0,
                 compilerUnsupportedDriftRefusals=5, installedLibraryInputsVerifiedAtCapture=len(receipt['installedLibraryInputsSha256']),
                 originalCaptureReceiptSha256=sha((capture / 'receipt.json').read_bytes()), findingsSha256=sha((HERE / 'schema-findings.json').read_bytes()))
    (HERE / 'schema-source-checks.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit))


if __name__ == '__main__':
    main()
