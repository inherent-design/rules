#!/usr/bin/env python3
"""Attribute a bounded item-definition/consumer map, not a complete codec or parser."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
PREFIX = 'net.minecraft.client.renderer.item.'
CONTRACTS = {
    'ClientItem': dict(fields={'model': 'required item graph', 'hand_animation_on_swap': 'optional flattened Boolean, source default true'},
                       consumer='ClientItemInfoLoader parses the outer descriptor; record Properties does not imply a nested JSON properties object.'),
    'ItemModels': dict(fields={'type': 'registered graph discriminator'},
                      consumer='bootstrap installs eight literal mappings; actual startup/provider hook ordering remains pending.'),
    'EmptyModel': dict(fields={}, consumer='Unit Unbaked codec; bake returns the empty model. Current fixture does not execute update/bake.'),
    'BlockModelWrapper': dict(fields={'model': 'required resource identifier', 'tints': 'optional tint list, source default empty'},
                             consumer='Dependency resolver visits model; bake requests it; later update evaluates tints and sets the render layer.'),
    'CompositeModel': dict(fields={'models': 'required child graph list'},
                           consumer='Dependency resolution and bake visit children; source listOf has no explicit nonempty wrapper here.'),
    'ConditionalItemModel': dict(fields={'property': 'conditional-property dispatch', 'on_true': 'required graph', 'on_false': 'required graph'},
                                 consumer='Both child graphs resolve/bake; later update evaluates the property with item/level/entity/seed context.'),
    'SelectItemModel': dict(fields={'property': 'select-property dispatch', 'cases': 'required case list', 'fallback': 'optional graph', 'cases[].when': 'nonempty compact scalar/list values', 'cases[].model': 'required graph'},
                            consumer='Case value codec depends on property; bake puts values into a map and uses missing-model fallback when absent. No runtime selection observed.'),
    'RangeSelectItemModel': dict(fields={'property': 'numeric-property dispatch', 'scale': 'optional float, source default1', 'entries': 'required threshold/model list', 'fallback': 'optional graph'},
                                 consumer='Bake sorts a copy by threshold; update evaluates property*scale, handles NaN, then selects a model. Only private sorted-array index helper is native-observed.'),
    'SpecialModelWrapper': dict(fields={'base': 'required resource identifier', 'model': 'required special-renderer specification'},
                                consumer='Base dependency and entity-model-set consumer are separate; a null renderer bake takes missing-model fallback in the inspected source.'),
    'BundleSelectedItemSpecialRenderer': dict(fields={}, consumer='Unit Unbaked codec; later rendering needs selected bundle contents and item resolver context.'),
    'ItemModel': dict(fields={}, consumer='Unbaked dependency resolution, bake context, and update context are separate interfaces/phases.'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('views', type=Path)
    args = parser.parse_args()
    capture = args.views.resolve()
    receipt = json.loads((capture / 'receipt.json').read_text())
    catalog = json.loads((HERE / 'java1214-registry-catalog.json').read_text())
    assert receipt['target'] == catalog['target'] == 'java-1.21.4-vanilla'
    assert receipt['clientSha256'] == catalog['clientSha256']
    contracts = {}
    selected = [(PREFIX + k, v) for k, v in CONTRACTS.items()]
    selected.append(('net.minecraft.client.resources.model.ClientItemInfoLoader',
        dict(fields={'directory': 'items', 'suffix': '.json'},
             consumer='List resources asynchronously, schedule per-resource reads, close each reader, log parse/open failures inside the try, omit null results after sequence. Discovery, task rejection, pre-try conversion, errors and final publication remain separate.')))
    for name, interpretation in selected:
        relative = name.replace('.', '/') + '.java'
        view = capture / 'source' / relative
        assert sha(view) == receipt['viewsSha256'][relative]
        original = receipt['originalClassMembers'][name]
        contracts[name] = dict(original=original, privateViewSha256=sha(view), **interpretation,
                               qualification='Source interpretation; not translation equivalence or whole consumer execution.')
    older = catalog['categories']
    later = json.loads((HERE / 'registry-catalog.json').read_text())['profiles']['minecraft-1.21.1+1.21.5']['categories']
    comparisons = []
    for category, record in older.items():
        a = {r['id'] for r in record['entries']}; b = {r['id'] for r in later[category]['entries']}
        comparisons.append(dict(category=category, counts={'1.21.4':len(a),'1.21.5':len(b)},
                                onlySelected1214=sorted(a-b), onlySelected1215=sorted(b-a)))
    result = dict(schema=1,target=catalog['target'],clientSha256=receipt['clientSha256'],mappingSha256=receipt['mappingSha256'],
        generatorSha256=sha(Path(__file__)),inspectedSources=contracts,registrationComparisons=comparisons,
        limits=['Field map covers the eight graph-node family and outer descriptor/loader/interface; per-property/tint/renderer grammars remain incomplete.',
                'The same model field has different graph/resource/special-renderer meanings in different objects.',
                'Reader handles and selected resource descriptors are not proof of immutable backing bytes.',
                'Per-resource errors inside the loader try do not establish that every scheduling/discovery/conversion failure is skipped.',
                'No item graph decoding, actual resource manager load, property evaluation, bake, render or modded provider qualification.'])
    (HERE / 'java1214-findings.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='source-interpreted-not-native-codec',contracts=len(contracts),categories=len(comparisons))))


if __name__ == '__main__':
    main()
