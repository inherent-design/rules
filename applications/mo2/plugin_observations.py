"""Finite name adapter and raw stream projection; this does not execute MO2."""
NAMES = ['A.esm', 'B.esp', 'C.esp', 'ABSENT.esp', 'ABSENT.esm', 'OLD.esm']
KINDS = ['set-state', 'enable', 'all', 'order', 'sync', 'masters']


def identity(name):
    assert name in NAMES, 'Name outside the canonical exact-name fixture'
    return NAMES.index(name)


def model_input(packet):
    assert packet['schema'] == 1
    output = []
    for row in packet['cases']:
        plugins = []
        for p in row['plugins']:
            plugins.append(dict(id=identity(p['name']), enabled=p['enabled'], loaded=p['forceLoaded'],
                forced=p['forceEnabled'], disabled=p['forceDisabled'], priority=p['priority'],
                loadOrder=p['loadOrder'], masters=[identity(v) for v in sorted(set(p['masters']))],
                missing=[identity(v) for v in sorted(set(p['missing']))]))
        actions = []
        for action in row['actions']:
            assert action['kind'] in KINDS
            actions.append(dict(kind=KINDS.index(action['kind']), target=identity(action['name']) if 'name' in action else 0,
                active=action.get('active', False), names=[identity(v) for v in action.get('names', [])]))
        output.append(dict(id=row['id'], plugins=plugins, actions=actions))
    return dict(schema=1, cases=output)


def view(raw):
    plugins = []
    expected_map = {}
    for p in raw['plugins']:
        key = identity(p['name'])
        indexed = p['queriedState'] != 'missing'
        assert p['queriedState'] in ['missing', 'active', 'inactive']
        if indexed:
            assert p['queriedState'] == ('active' if p['enabled'] else 'inactive')
            expected_map[p['name']] = key
        plugins.append(dict(id=key, enabled=p['enabled'], priority=p['priority'], loadOrder=p['loadOrder'],
            missing=[identity(v) for v in p['missing']], indexed=indexed))
    assert raw['byName'] == expected_map, 'Queried states and native name index disagree'
    events = []
    for event in raw['events']:
        if event['kind'] == 'write':
            events.append(dict(kind=0, ids=[], active=False))
        else:
            assert event['kind'] == 'state' and event['values']
            values = set(event['values'].values())
            assert len(values) == 1 and values.issubset({'active', 'inactive'})
            events.append(dict(kind=1, ids=sorted(identity(v) for v in event['values']), active=values == {'active'}))
    return dict(plugins=plugins, byPriority=raw['byPriority'], writeRequests=raw['writes'], indexCalls=raw['generated'],
        events=events, errors=raw['errors'], warnings=raw['warnings'])


def model_output(rows):
    return [dict(id=row['id'], before=view(row['before']), steps=[view(s) for s in row['steps']]) for row in rows]
