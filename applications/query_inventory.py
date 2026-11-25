#!/usr/bin/env python3
"""Query canonical inventory links without inferring conformance or completion."""
import argparse
from collections import Counter
import json
from pathlib import Path
from check_inventory import validate

ROOT = Path(__file__).resolve().parent
REFERENCE_FIELDS = ['model', 'laws', 'nativeEvidence', 'sourceComparison', 'negativeControls', 'uxAssessment']


def describe_feature(app, feature):
    operations = []
    for operation in feature['operations']:
        direct = {key: operation.get(key) for key in REFERENCE_FIELDS if operation.get(key)}
        slices = []
        for index, component in enumerate(feature.get('componentEvidence', [])):
            scope = component['operationSlices'].get(operation['id'])
            if scope:
                slices.append(dict(component=index, scope=scope))
        operations.append(dict(id=operation['id'], status=operation['status'],
                               directReferences=direct, scopedReferences=slices))
    return dict(application=app['id'], id=feature['id'], title=feature['title'],
                disposition=feature['disposition'], operations=operations, components=feature.get('componentEvidence', []))


def build_report(catalog, scenarios, app_id=None, feature_id=None):
    validate(catalog, scenarios)
    features = [describe_feature(app, feature) for app in catalog['applications']
                if app_id is None or app['id'] == app_id
                for feature in app['features'] if feature_id is None or feature['id'] == feature_id]
    if not features:
        raise ValueError('No inventory feature matches the selected application or feature.')
    summaries = []
    for app in catalog['applications']:
        selected = [f for f in features if f['application'] == app['id']]
        if not selected:
            continue
        ops = [o for f in selected for o in f['operations']]
        linked = sum(bool(o['directReferences'] or o['scopedReferences']) for o in ops)
        summaries.append(dict(application=app['id'], features=len(selected), operations=len(ops),
                              linkedOperations=linked, operationsWithoutLinks=len(ops)-linked,
                              statuses=dict(sorted(Counter(o['status'] for o in ops).items()))))
    return dict(schema=1, meaning='Reference bookkeeping only. Existing files, named laws, or scoped links do not prove semantic conformance or completion.',
                applications=summaries, features=features)


def render(report, detail=False):
    lines = ['Inventory references', '', f'{"Application":<14}{"Features":>10}{"Operations":>12}{"With links":>12}{"Without links":>16}']
    for app in report['applications']:
        lines.append(f'{app["application"]:<14}{app["features"]:>10}{app["operations"]:>12}{app["linkedOperations"]:>12}{app["operationsWithoutLinks"]:>16}')
    lines += ['', report['meaning']]
    if not detail:
        lines += ['Use --feature ID to inspect operation scopes and remaining work.']
        return '\n'.join(lines)
    for feature in report['features']:
        lines += ['', f'{feature["title"]} ({feature["id"]})']
        for op in feature['operations']:
            kinds = []
            if op['directReferences']:
                kinds.append('direct references')
            if op['scopedReferences']:
                kinds.append('scoped evidence')
            label = ' and '.join(kinds) if kinds else 'no inventory references'
            lines.append(f'  {op["id"]}: {op["status"]} ({label})')
        for index, component in enumerate(feature['components']):
            lines += ['', f'  Component {index + 1}: {component["status"]}']
            for operation, scope in component['operationSlices'].items():
                lines.append(f'    {operation}: {scope}')
            if not component['operationSlices']:
                lines.append(f'    Related evidence only: {component["relationOnly"]}')
            lines += [f'    Evidence: {", ".join(component["evidence"])}', f'    Remaining: {component["remaining"]}']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', help='Application ID, such as cargo or empack.')
    parser.add_argument('--feature', help='Exact feature ID, such as cargo.freshness.')
    parser.add_argument('--json', action='store_true', help='Print the same reference facts as JSON.')
    args = parser.parse_args()
    catalog = json.loads((ROOT/'inventory.json').read_text())
    scenarios = json.loads((ROOT/'scenarios.json').read_text())
    try:
        report = build_report(catalog, scenarios, args.app, args.feature)
    except ValueError as error:
        parser.error(str(error))
    except AssertionError as error:
        parser.exit(1, 'Inventory validation failed: ' + str(error) + '\n')
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render(report, bool(args.feature)))


if __name__ == '__main__':
    main()
