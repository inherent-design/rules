#!/usr/bin/env python3
"""Check inventory breadth and evidence bookkeeping, not application correctness."""
import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIRED = {'empack', 'npm', 'pnpm', 'yarn', 'mo2', 'prism', 'cargo', 'restic', 'vscode'}


MODEL_PATH = re.compile(r'[A-Za-z0-9_./-]+\.(?:lean|bend)\b')
FILE_PREFIX = re.compile(r'^([A-Za-z0-9_./-]+\.(?:jsonl?|md|py|rs|lean|bend|stdout|stderr|txt|zip))(?=$|[:#; ])')
SIMPLE_LAW = re.compile(r'[A-Za-z_]\w*')


def require_file(path, owner):
    selected = ROOT / path
    assert selected.resolve().is_relative_to(ROOT.parent), (owner, 'reference escapes repository', path)
    assert selected.is_file(), (owner, 'missing evidence file', path)
    return selected


def validate_operation_references(owner, operation):
    assert not any(key in operation for key in ('components', 'componentEvidence')), (owner, 'operation component evidence must use feature operationSlices')
    models = MODEL_PATH.findall(operation.get('model') or '')
    assert not operation.get('model') or models, (owner, 'model has no declared module path')
    laws = set()
    for path in models:
        source = require_file(path, owner).read_text()
        laws.update(re.findall(r'^\s*(?:theorem|lemma|law)\s+(\w+)', source, re.MULTILINE))
    for law in operation.get('laws', []):
        if SIMPLE_LAW.fullmatch(law):
            assert law in laws, (owner, 'missing named law', law)
    for field in ['nativeEvidence', 'sourceComparison', 'negativeControls', 'uxAssessment']:
        values = operation.get(field) or []
        if isinstance(values, str):
            values = [values]
        for value in values:
            match = FILE_PREFIX.match(value)
            if field != 'negativeControls':
                assert match, (owner, 'unrecognized file reference', field, value)
            if match:
                require_file(match[1], owner)


def validate_components(owner, operation_ids=None):
    for component in owner.get('componentEvidence', []):
        assert component['status'] in {'native-observed', 'source-modeled', 'proposed'}, owner['id']
        assert component['scope'] and component['remaining'], owner['id']
        assert component['evidence'], (owner['id'], 'missing component evidence')
        for path in component['evidence']:
            require_file(path, owner['id'])
        if operation_ids is not None:
            slices = component.get('operationSlices')
            assert isinstance(slices, dict), (owner['id'], 'missing operation slice map')
            assert set(slices) <= operation_ids, (owner['id'], 'unknown component operation')
            assert all(isinstance(scope, str) and scope.strip() for scope in slices.values()), (owner['id'], 'empty operation scope')
            assert slices or component.get('relationOnly'), (owner['id'], 'unmapped component needs an explicit relation-only scope')


def validate_decisions(app):
    """Validate reference structure; a linked proposal is not an adopted design."""
    fields = {'improvementCandidates': ('status', 'document'),
              'preservationDecisions': ('decision', 'evidence'),
              'unresolvedChoices': ('question', 'document')}
    for category, (content, reference) in fields.items():
        records = app[category]
        assert isinstance(records, list), (app['id'], category, 'decision records must be a list')
        seen = set()
        for record in records:
            assert isinstance(record, dict), (app['id'], category, 'decision record must be an object')
            ident = record.get('id')
            assert isinstance(ident, str) and re.fullmatch(r'[a-z][a-z0-9-]*', ident), (app['id'], category, 'invalid decision id')
            assert ident not in seen, (app['id'], category, 'duplicate decision id', ident)
            seen.add(ident)
            owner = (app['id'], category, ident)
            assert isinstance(record.get(content), str) and record[content].strip(), (owner, 'empty decision content')
            value = record.get(reference)
            assert isinstance(value, str), (owner, 'missing decision reference')
            match = FILE_PREFIX.match(value)
            assert match, (owner, 'unrecognized decision reference', value)
            require_file(match[1], owner)


def validate(catalog, scenarios):
    apps = catalog['applications']
    assert {a['id'] for a in apps} == REQUIRED and len(apps) == len(REQUIRED), 'required application scope changed'
    ids, operations = set(), set()
    for app in apps:
        assert app['features'], app['id']
        validate_decisions(app)
        for feature in app['features']:
            fid = feature['id']
            assert fid.startswith(app['id'] + '.') and fid not in ids
            ids.add(fid)
            for field in ('title', 'domainValuesAndRelations', 'invariantQuestions', 'hostWitnesses', 'operations', 'disposition'):
                assert feature[field], (fid, field)
            validate_components(feature, {op['id'] for op in feature['operations']})
            for op in feature['operations']:
                oid = fid + '/' + op['id']
                assert oid not in operations
                operations.add(oid)
                assert op['status'] in catalog['statusVocabulary'], (oid, 'unknown status')
                validate_operation_references(oid, op)
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
        validate_components(scenario)
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
    missing = copy.deepcopy(scenarios)
    missing['scenarios'][0]['componentEvidence'] = [{'status': 'proposed', 'scope': 'Unimplemented component',
        'remaining': 'Native implementation', 'evidence': ['evidence/no-such-component-record.json']}]
    feature_missing = copy.deepcopy(catalog)
    feature_missing['applications'][0]['features'][0]['componentEvidence'] = missing['scenarios'][0]['componentEvidence']
    bad_model = copy.deepcopy(catalog)
    selected = next(op for app in bad_model['applications'] for feature in app['features'] for op in feature['operations'] if op.get('model'))
    selected['model'] = 'missing-study-model.lean'
    bad_law = copy.deepcopy(catalog)
    selected = next(op for app in bad_law['applications'] for feature in app['features'] for op in feature['operations'] if op.get('model'))
    selected['laws'].append('missing_research_law')
    bad_slice = copy.deepcopy(catalog)
    selected = next(feature for app in bad_slice['applications'] for feature in app['features'] if feature.get('componentEvidence'))
    selected['componentEvidence'][0]['operationSlices'] = {'missing-operation': 'An undeclared operation cannot acquire evidence from a component.'}
    no_scope = copy.deepcopy(catalog)
    selected = next(feature for app in no_scope['applications'] for feature in app['features'] if feature.get('componentEvidence'))
    selected['componentEvidence'][0]['operationSlices'] = {}
    selected['componentEvidence'][0].pop('relationOnly', None)
    misplaced = copy.deepcopy(catalog)
    misplaced['applications'][0]['features'][0]['operations'][0]['components'] = [
        {'scope': 'This field is ignored by the canonical feature query.'}]
    missing_decision = copy.deepcopy(catalog)
    selected = next(a for a in missing_decision['applications'] if a['improvementCandidates'])
    selected['improvementCandidates'][0]['document'] = 'missing-decision-report.md'
    duplicate_decision = copy.deepcopy(catalog)
    selected = next(a for a in duplicate_decision['applications'] if a['improvementCandidates'])
    selected['improvementCandidates'].append(copy.deepcopy(selected['improvementCandidates'][0]))
    empty_preservation = copy.deepcopy(catalog)
    selected = next(a for a in empty_preservation['applications'] if a['preservationDecisions'])
    selected['preservationDecisions'][0]['decision'] = ''
    missing_choice = copy.deepcopy(catalog)
    selected = next(a for a in missing_choice['applications'] if a['unresolvedChoices'])
    selected['unresolvedChoices'][0]['document'] = 'missing-choice-report.md'
    for name, value, joined in [('dropped-application', narrowed, scenarios), ('unsupported-completion-claim', fake, scenarios),
                               ('missing-component-evidence', catalog, missing), ('missing-feature-component-evidence', feature_missing, scenarios),
                               ('missing-model-reference', bad_model, scenarios), ('missing-law-reference', bad_law, scenarios),
                               ('unknown-operation-slice', bad_slice, scenarios), ('unmapped-component-without-scope', no_scope, scenarios),
                               ('misplaced-operation-component', misplaced, scenarios),
                               ('missing-decision-document', missing_decision, scenarios), ('duplicate-decision-id', duplicate_decision, scenarios),
                               ('empty-preservation-rationale', empty_preservation, scenarios), ('missing-choice-document', missing_choice, scenarios)]:
        try:
            validate(value, joined)
        except AssertionError as error:
            expected = {
                'dropped-application': 'required application scope changed',
                'unsupported-completion-claim': 'missing qualified evidence',
                'missing-component-evidence': 'missing evidence file',
                'missing-feature-component-evidence': 'missing evidence file',
                'missing-model-reference': 'missing evidence file',
                'missing-law-reference': 'missing named law',
                'unknown-operation-slice': 'unknown component operation',
                'unmapped-component-without-scope': 'unmapped component needs an explicit relation-only scope',
                'misplaced-operation-component': 'operation component evidence must use feature operationSlices',
                'missing-decision-document': 'missing evidence file',
                'duplicate-decision-id': 'duplicate decision id',
                'empty-preservation-rationale': 'empty decision content',
                'missing-choice-document': 'missing evidence file',
            }[name]
            assert expected in str(error), (name, 'refused for an unrelated reason', str(error))
            rejected.append(name)
        else:
            raise AssertionError('Invalid bookkeeping accepted: ' + name)
    before = hashlib.sha256((ROOT / 'inventory.json').read_bytes()).hexdigest()
    receipt = {'schema': 1, 'applications': len(REQUIRED), 'featureFamilies': features,
               'semanticOperations': operations, 'joinedScenarios': len(scenarios['scenarios']),
               'decisionReferenceRecords': {field: sum(len(a[field]) for a in catalog['applications'])
                                            for field in ['improvementCandidates', 'preservationDecisions', 'unresolvedChoices']},
               'negativeControlsRejected': rejected, 'inventorySource': 'inventory.json is canonical; one-off generator retired after initialization',
               'inventorySha256': before, 'scenarioSha256': hashlib.sha256((ROOT / 'scenarios.json').read_bytes()).hexdigest(),
               'limitation': 'Structure and bookkeeping only. This does not verify application features, source assertions, models, or native conformance.'}
    (ROOT / 'evidence/inventory-audit.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
