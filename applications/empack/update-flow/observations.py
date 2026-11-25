"""Decode retained bytes and outputs; never execute empack or use its after-state as model input."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
NAMES = [
    'empack-update-flow-20261125T213429298820Z',
    'empack-update-materialize-20261125T213701918141Z',
    'empack-update-build-20261125T214901703343Z',
    'empack-update-recipient-20261125T215429093315Z',
]
RUNS = [ROOT / 'applications/evidence' / n for n in NAMES]
OPERATIONS = ['syncOld','inspect','held','unpin','inspect','automaticPreview','exactPreview',
              'applyExact','inspect','held','checkRecorded','materialize','checkRecorded',
              'checkOnline','inspect','bundled','references','ensure','ensure','checkRecipient']
IDS = {None: 0, 'wmIZ4wP4': 1, 'sOzRw3CG': 2}
ARGS = [
    ['sync','--materialize'], ['manifest','diff','--json'], ['update','--all','--json','--quiet'],
    ['unpin','ferrite'], ['manifest','diff','--json'], ['update','--all','--json','--quiet'],
    ['update','--all','--pin','ferrite=sOzRw3CG','--json','--quiet'],
    ['update','--all','--pin','ferrite=sOzRw3CG','--apply','--quiet'],
    ['manifest','diff','--json'], ['update','--all','--json','--quiet'],
    ['check','--json','--quiet'], ['sync','--materialize'], ['check','--json','--quiet'],
    ['check','--online','--json','--quiet'], ['manifest','diff','--json'],
    ['build','--profile','client'],
    ['build','--ad-hoc','prism','--environment','client','--delivery','references','--updates','snapshot'],
]
load = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def text(image, path):
    row = image[path]
    raw = bytes.fromhex(row['bytesHex'])
    assert row['kind'] == 'file' and len(raw) == row['bytes']
    assert hashlib.sha256(raw).hexdigest() == row['sha256']
    assert hashlib.sha512(raw).hexdigest() == row['sha512']
    return raw.decode('utf-8')


def author(image, metadata):
    """Deliberately bounded YAML profile, not a replacement YAML parser."""
    yml = text(image, 'empack.yml')
    assert '    source: modrinth:uXXizFIs\n' in yml and '    type: mod\n' in yml
    matches = re.findall(r"^    pin: '?([A-Za-z0-9]+)'?$", yml, re.M)
    assert len(matches) <= 1 and yml.count('    pin:') == len(matches)
    pin = IDS[matches[0] if matches else None]
    lock = text(image, 'empack.lock') if 'empack.lock' in image else None
    if lock is None:
        selection = 0
    else:
        values = re.findall(r'^\s+id: ([A-Za-z0-9]+)$', lock, re.M)
        assert len(values) == 2 and len(set(values)) == 1
        selection = IDS[values[0]]
        item = metadata['old' if selection == 1 else 'target']['file']
        assert 'schema: 3\n' in lock and 'required-edges: {}\n' in lock
        assert item['hashes']['sha512'] in lock and f"size: {item['size']}" in lock
    payload = 0
    for name, number in [('old', 1), ('target', 2)]:
        f = metadata[name]['file']; path = 'pack/mods/' + f['filename']
        if path in image:
            row = image[path]
            assert row['bytes'] == f['size'] and row['sha512'] == f['hashes']['sha512']
            assert payload == 0
            payload = number
    assert {p for p in image if p.startswith('pack/mods/') and image[p]['kind'] == 'file'} <= {
        'pack/mods/' + metadata[n]['file']['filename'] for n in ['old','target']}
    return [pin, selection, payload]


def inspect(value, state):
    assert value['schema'] == 1 and value['lock_status'] == 'current'
    assert value['runtime_satisfied'] and len(value['dependencies']) == 1
    d = value['dependencies'][0]
    assert d['key'] == 'ferrite' and d['explicit'] and d['source_binding_current']
    s = d['effective']['selection']
    assert (IDS[s['pin']['id']] if s['mode'] == 'provider-pin' else 0) == state[0]
    assert IDS[d['locked_selection']['id']] == state[1]


def packets(rows=None, jsons=None, artifacts=None):
    rows = rows if rows is not None else [load(r / 'commands.json') for r in RUNS]
    jsons = jsons if jsons is not None else [{p.stem: load(p) for p in r.glob('*.json')} for r in RUNS]
    artifacts = artifacts if artifacts is not None else load(RUNS[2] / 'artifacts.json')
    metadata = load(RUNS[0] / 'independent-metadata.json')
    expected = []
    index = 0
    for section, commands in enumerate(rows):
        for command in commands:
            label = command['id']; facets = []
            args = command['argv'][command['argv'].index('--yes')+1:]
            if section < 3:
                assert args == ARGS[index], 'Outside captured research command profile'
            else:
                assert args == (jsons[3]['setup']['approvedArguments'][3:] if label.startswith('ensure')
                                else ['instance','check','--json','--quiet'])
            index += 1
            if section < 3:
                state = author(command['after'], metadata)
                if label.startswith('inspect'):
                    inspect(jsons[section][label], state)
                elif label in ['held-old', 'held-new', 'automatic-preview', 'exact-preview']:
                    v = jsons[section][label]; d = v['discovery']; dep = d['dependencies'][0]
                    assert d['complete'] and d['required_dependencies'] == 'validated'
                    assert not d['declared_incompatibilities'] and d['declarations_complete']
                    assert dep['compatible']['selection'] == metadata['target']['id']
                    if label.startswith('held'):
                        facets = [d['summary']['held'], IDS[dep['permitted']['selection']]]
                        assert v['proposal'] == 'unchanged' and not v['file_changes']
                    else:
                        facets = [IDS[dep['permitted']['selection']], v['references']]
                        assert v['proposal'] == 'ready'
                        pins = v['author_pin_changes']
                        assert pins == ([] if label == 'automatic-preview' else [dict(dependency='ferrite',selection=metadata['target']['id'])])
                elif label.startswith('check-'):
                    v = jsons[section][label]
                    assert v['scope'] == ('online' if label == 'check-online-materialized' else 'recorded')
                    facets = [int(v['complete']), v['verified_files'], v['references']]
                    assert all(f['state'] == 'passed' for f in v['findings'] if f['required'])
                    inspect(v['authoring'], state)
                elif label.startswith('prism-'):
                    artifact = next(a for a in artifacts if a['command'] == label)
                    entries = {e['path']: e for e in artifact['entries']}
                    mod = '.minecraft/mods/' + metadata['target']['file']['filename']
                    embedded = mod in entries
                    if embedded: assert entries[mod]['sha512'] == metadata['target']['file']['hashes']['sha512']
                    subscription = False
                    if label == 'prism-references':
                        release = json.loads(entries['.minecraft/.empack-consumer/release.json']['text'])
                        subscription = release['require_subscription']
                        assertions = {a['algorithm']: a['value'] for a in release['files'][0]['assertions']}
                        assert assertions['sha512'] == metadata['target']['file']['hashes']['sha512']
                    facets = [int(embedded), int('.empack-tools/empack-bootstrap.jar' in entries), int(subscription)]
                expected.append(state + facets)
            else:
                image = command['after']; setup = jsons[3]['setup']
                setting = setup['unownedSetting']['path']
                preserved = image[setting] == setup['initialImage'][setting]
                mod = '.minecraft/mods/' + metadata['target']['file']['filename']
                installed = mod in image
                if installed: assert image[mod]['sha512'] == metadata['target']['file']['hashes']['sha512']
                if label.startswith('ensure'):
                    facets = [2 if installed else 0, int(preserved)]
                else:
                    v = jsons[3][label]
                    assert v['scope'] == 'instance' and v['release'] == setup['releaseSha256']
                    assert v['verified_overrides'] == 0
                    facets = [int(v['complete']), v['verified_files'], v['player_owned_entries'], int(preserved)]
                expected.append(facets)
    assert len(expected) == len(OPERATIONS) == 20
    inputs = dict(schema=1, profile='ferrite-one-root-snapshot-success/1',
                  old=metadata['old']['id'], target=metadata['target']['id'], operations=OPERATIONS)
    return inputs, expected
