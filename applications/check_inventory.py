#!/usr/bin/env python3
"""Check inventory breadth and evidence bookkeeping, not application correctness."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIRED = {'empack', 'npm', 'pnpm', 'yarn', 'mo2', 'prism', 'cargo', 'restic', 'vscode'}


def validate(catalog, scenarios):
    apps = catalog['applications']
    assert {a['id'] for a in apps} == REQUIRED and len(apps) == len(REQUIRED)
    ids, operations = set(), set()
    for app in apps:
        assert app['features'], app['id']
        for feature in app['features']:
            fid = feature['id']
            assert fid.startswith(app['id'] + '.') and fid not in ids
            ids.add(fid)
            for field in ('title', 'domainValuesAndRelations', 'invariantQuestions', 'hostWitnesses', 'operations', 'disposition'):
                assert feature[field], (fid, field)
            for op in feature['operations']:
                oid = fid + '/' + op['id']
                assert oid not in operations
                operations.add(oid)
                assert op['status'] in catalog['statusVocabulary'], (oid, 'unknown status')
                if op['status'] == 'verified-bounded':
                    for field in ('model', 'laws', 'sourceComparison', 'negativeControls', 'uxAssessment', 'verificationPlan', 'proofPremises'):
                        assert op.get(field), (oid, 'missing qualified evidence', field)
                    assert op['nativeEvidence'] or op.get('unavailableNativeObligation'), (oid, 'native gap hidden')
    scenario_ids = set()
    for scenario in scenarios['scenarios']:
        assert scenario['id'] not in scenario_ids
        scenario_ids.add(scenario['id'])
        assert scenario['features'] and set(scenario['features']) <= ids, scenario['id']
        assert scenario['counterexamples'] and scenario['hostWitnesses'] and scenario['status']
    return len(ids), len(operations)


def main():
    catalog = json.loads((ROOT / 'inventory.json').read_text())
    scenarios = json.loads((ROOT / 'scenarios.json').read_text())
    features, operations = validate(catalog, scenarios)
    rejected = []
    narrowed = copy.deepcopy(catalog)
    narrowed['applications'] = [a for a in narrowed['applications'] if a['id'] != 'mo2']
    fake = copy.deepcopy(catalog)
    fake['applications'][0]['features'][0]['operations'][0]['status'] = 'verified-bounded'
    for name, value in [('dropped-application', narrowed), ('unsupported-completion-claim', fake)]:
        try:
            validate(value, scenarios)
        except AssertionError:
            rejected.append(name)
        else:
            raise AssertionError('Invalid bookkeeping accepted: ' + name)
    before = hashlib.sha256((ROOT / 'inventory.json').read_bytes()).hexdigest()
    receipt = {'schema': 1, 'applications': len(REQUIRED), 'featureFamilies': features,
               'semanticOperations': operations, 'joinedScenarios': len(scenarios['scenarios']),
               'negativeControlsRejected': rejected, 'inventorySource': 'inventory.json is canonical; one-off generator retired after initialization',
               'inventorySha256': before, 'scenarioSha256': hashlib.sha256((ROOT / 'scenarios.json').read_bytes()).hexdigest(),
               'limitation': 'Structure and bookkeeping only. This does not verify application features, source assertions, models, or native conformance.'}
    (ROOT / 'evidence/inventory-audit.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
