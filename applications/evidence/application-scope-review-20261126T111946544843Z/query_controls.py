"""Exercise reference classification against canonical records; no application run."""
from pathlib import Path
import collections
import copy
import hashlib
import json
import sys

root = Path.cwd()
sys.path.insert(0, str(root / 'applications'))
from query_inventory import build_report, render

catalog = json.loads((root / 'applications/inventory.json').read_text())
scenarios = json.loads((root / 'applications/scenarios.json').read_text())
report = build_report(catalog, scenarios)
feature_id = 'prism.pack-import'
base = build_report(catalog, scenarios, feature_id=feature_id)
summary = base['applications'][0]
assert summary['proposalOnlyOperations'] == 2
assert all(o['status'] == 'pending' for o in base['features'][0]['operations'])

related = copy.deepcopy(catalog)
feature = next(f for a in related['applications'] for f in a['features'] if f['id'] == feature_id)
for component in feature['componentEvidence']:
    if component['status'] == 'proposed':
        component['operationSlices'] = {}
        component['relationOnly'] = 'Control: related proposal performs none of the declared operations.'
value = build_report(related, scenarios, feature_id=feature_id)
assert value['applications'][0]['proposalOnlyOperations'] == 0
assert value['applications'][0]['linkedOperations'] == 0
assert value['applications'][0]['statuses'] == summary['statuses']

reclassified = copy.deepcopy(catalog)
feature = next(f for a in reclassified['applications'] for f in a['features'] if f['id'] == feature_id)
for component in feature['componentEvidence']:
    if component['status'] == 'proposed':
        component['status'] = 'source-modeled'
value = build_report(reclassified, scenarios, feature_id=feature_id)
assert value['applications'][0]['proposalOnlyOperations'] == 0
assert value['applications'][0]['linkedOperations'] == summary['linkedOperations']
assert value['applications'][0]['statuses'] == summary['statuses']
assert 'scoped references: source-modeled' in render(value, True)
assert any(o['directReferences'] and any(s['status'] == 'proposed' for s in o['scopedReferences'])
           for f in report['features'] for o in f['operations'])

# Independently count proposal-only links from raw feature/operation records.
raw_only = 0
for application in catalog['applications']:
    for feature in application['features']:
        for operation in feature['operations']:
            direct = any(operation.get(k) for k in ['model', 'laws', 'nativeEvidence', 'sourceComparison', 'negativeControls', 'uxAssessment'])
            slices = [c for c in feature.get('componentEvidence', []) if operation['id'] in c['operationSlices']]
            raw_only += not direct and bool(slices) and all(c['status'] == 'proposed' for c in slices)
for application in report['applications']:
    assert application['proposalOnlyOperations'] <= application['linkedOperations'] <= application['operations']
    assert sum(application['statuses'].values()) == application['operations']
operations = [o for a in catalog['applications'] for f in a['features'] for o in f['operations']]
linked = sum(a['linkedOperations'] for a in report['applications'])
only = sum(a['proposalOnlyOperations'] for a in report['applications'])
assert only == raw_only
assert len(operations) == 974
receipt = dict(
    inventorySha256=hashlib.sha256((root / 'applications/inventory.json').read_bytes()).hexdigest(),
    scenariosSha256=hashlib.sha256((root / 'applications/scenarios.json').read_bytes()).hexdigest(),
    querySha256=hashlib.sha256((root / 'applications/query_inventory.py').read_bytes()).hexdigest(),
    applications=report['applications'], statuses=dict(collections.Counter(o['status'] for o in operations)),
    linkedOperations=linked, proposalOnlyOperations=only, operationsWithoutLinks=len(operations)-linked,
    familiesWithOperationLinks=sum(any(o['directReferences'] or o['scopedReferences'] for o in f['operations']) for f in report['features']),
    familiesRelatedOnly=sum(not any(o['directReferences'] or o['scopedReferences'] for o in f['operations']) and bool(f['components']) for f in report['features']),
    scenarioCount=len(scenarios['scenarios']),
    controls=['Existing proposal-only operations remain pending.', 'Relation-only components do not create operation links.',
              'Synthetic component status change affects classification but not operation states or total links.',
              'Direct references plus proposals remain direct-reference relationships.',
              'Summary partitions and independently derived raw proposal count agree.'],
    limits=['Reference metadata only, not application correctness or completion.', 'Synthetic controls do not rewrite native evidence or real catalog.'])
print(json.dumps(receipt, indent=2))
