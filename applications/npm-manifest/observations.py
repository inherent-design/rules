"""Closed manifest/argv interpretation; saved effects and wire facts come from capture."""
import copy
import json


def same_json(a, b):
    """Python equality conflates false and zero; the JSON contract must not."""
    return json.dumps(a, sort_keys=True, separators=(',', ':')) == json.dumps(b, sort_keys=True, separators=(',', ':'))


def truthy(value):
    # JSON containers are truthy in JavaScript, including empty containers.
    return isinstance(value, (dict, list)) or bool(value)


def lookup(value, path):
    if path is None:
        return True, True, value
    if path == 'contributors.name':
        return True, True, {f'contributors[{i}].name': item['name'] for i, item in enumerate(value['contributors'])}
    if path == 'exports[.].default':
        return True, True, value['exports']['.']['default']
    assert path.startswith('custom.') or path in ['custom', 'name', 'contributors'], path
    for key in path.split('.'):
        if not isinstance(value, dict):
            return False, False, None
        if key not in value:
            return True, False, None
        value = value[key]
    return True, True, value


def prepare(value, args):
    """Only the literal edit paths/types in the frozen producer, not a JSON-path engine."""
    original = copy.deepcopy(value)
    current = copy.deepcopy(value)
    if '--global' in args:
        return False, original
    command = args[0]
    if command == 'get':
        selectors = [a for a in args[1:] if not a.startswith('--')]
        assert len(selectors) <= 1
        ok, _, _ = lookup(current, selectors[0] if selectors else None)
        return ok, original
    if command == 'delete':
        assert args[1:] == ['contributors[0]']
        del current['contributors'][0]
        return True, current
    assert command == 'set'
    for arg in args[1:]:
        if arg in ['--json', '--force', '--workspaces']:
            continue
        key, sep, text = arg.partition('=')
        assert sep and text, arg
        if key == 'custom.__proto__.owned':
            return False, original
        try:
            new = json.loads(text) if '--json' in args else text
        except json.JSONDecodeError:
            return False, original
        if key in ['name', 'version']:
            current[key] = new
        elif key in ['custom.flag', 'custom.first']:
            current['custom'][key.split('.')[1]] = new
        elif key in ['custom.scalar.child', 'custom.mode']:
            parent = current['custom']['scalar'] if key == 'custom.scalar.child' else current['custom']
            if not isinstance(parent, dict) and '--force' not in args:
                return False, original
            if key == 'custom.scalar.child':
                current['custom']['scalar'] = dict(child=new)
            else:
                current['custom']['mode'] = new
        elif key == 'scripts.test':
            current['scripts']['test'] = new
        elif key == 'contributors[].name':
            if not isinstance(current.get('contributors'), list):
                return False, original
            current['contributors'].append(dict(name=new))
        else:
            raise AssertionError(('Outside literal manifest-edit profile', key))
    if any(not isinstance(v, str) for v in current.get('scripts', {}).values()):
        return False, original
    return True, current


def packets(runs, query_only_runs=()):
    queries, expected_queries, saves, expected_saves, appends, expected_appends = [], [], [], [], [], []
    facts = []
    for run in runs:
        for row in json.loads((run / 'commands.json').read_text()):
            args = row['argv'][4:]
            assert row['argv'][3] == 'pkg'
            before, after = row['before'], row['after']
            for saved in before.values():
                canonical = (json.dumps(saved['semantic'], indent='\t') + '\n').replace('\n', '\r\n').encode()
                assert bytes.fromhex(saved['bytesHex']) == canonical, 'Outside canonical ASCII/tab/CRLF fixture profile'
            root = before['package.json']['semantic']
            paths = [name + '/package.json' for name in root['workspaces']] if '--workspaces' in args else ['package.json']
            predicted = {name: v['semantic'] for name, v in before.items()}
            steps, failed = [], False
            for name in paths:
                old = before[name]['semantic']
                valid, desired = prepare(old, args)
                steps.append(dict(valid=valid, changes=valid and desired != old))
                if not failed:
                    predicted[name] = desired
                if not valid:
                    failed = True
            assert same_json(predicted, {name: v['semantic'] for name, v in after.items()}), row['id']
            saves.append(dict(id=row['id'], steps=steps))
            expected_saves.append(dict(id=row['id'], changedFiles=sum(before[name]['sha256'] != after[name]['sha256'] for name in before),
                                       successful=row['exitCode'] == 0))
            raw = (run / (row['id'] + '.stdout')).read_bytes()
            parsed = json.loads(raw) if raw else None
            if args[0] == 'get' and '--global' not in args:
                if '--workspaces' in args:
                    ok, present = True, True
                    value = {}
                    for name in paths:
                        child_ok, child_present, child = lookup(before[name]['semantic'], args[1])
                        assert child_ok and child_present
                        if isinstance(child, list) and len(child) <= 1:
                            child = child[0] if child else None
                        value[before[name]['semantic']['name']] = child
                else:
                    ok, present, value = lookup(root, args[1])
                array = present and isinstance(value, list)
                length = len(value) if array else 0
                # This profile excludes singleton arrays containing another array.
                assert not (array and length == 1 and isinstance(value[0], list))
                leaf_truthy = truthy(value[0]) if array and length == 1 else truthy(value)
                queries.append(dict(id=row['id'], preserveArrays=False, wrapped=False, querySucceeded=ok, fieldPresent=present, isArray=array,
                                    length=length, leafTruthy=leaf_truthy))
                emitted = row['exitCode'] == 0 and bool(raw)
                expected_queries.append(dict(id=row['id'], dataWritten=emitted,
                                             currentIsArray=emitted and isinstance(parsed, list)))
                # Content checks remain separate from the model's presence/type predicates.
                if emitted:
                    expected = {} if not present else value[0] if array and length == 1 else value
                    assert same_json(parsed, expected), row['id']
                if not ok:
                    assert row['exitCode'] == 1 and 'Cannot convert undefined or null to object' in parsed['error']['summary']
            if args[0] == 'set' and 'contributors[].name=Appended' in args:
                prior_failed = False
                for name, step in zip(paths, steps, strict=True):
                    if not prior_failed and step['valid']:
                        key = row['id'] if len(paths) == 1 else row['id'] + ':' + name
                        appends.append(dict(id=key, countBefore=len(before[name]['semantic']['contributors'])))
                        expected_appends.append(dict(id=key, countAfter=len(after[name]['semantic']['contributors'])))
                    prior_failed = prior_failed or not step['valid']
            facts.append(dict(id=row['id'], observedChangedFiles=expected_saves[-1]['changedFiles'],
                              stdoutBytes=len(raw), exitCode=row['exitCode'],
                              byteStable=all(before[name]['sha256'] == after[name]['sha256'] for name in before),
                              mtimeStable=all(before[name]['mtimeNs'] == after[name]['mtimeNs'] for name in before)))
    for run in query_only_runs:
        setup = json.loads((run / 'setup.json').read_text())
        for row in json.loads((run / 'commands.json').read_text()):
            assert row['before'] == row['after']
            raw = (run / (row['id'] + '.stdout')).read_bytes()
            facts.append(dict(id=row['id'], observedChangedFiles=0, stdoutBytes=len(raw), exitCode=row['exitCode'],
                              byteStable=True, mtimeStable=True, configuredMode='json' if '--json' in row['argv'] else 'text'))
            if 'pkg' not in row['argv']:
                assert row['id'] == 'version' and raw.decode().strip() == setup['version']
                continue
            args = row['argv'][row['argv'].index('pkg') + 1:]
            assert args[0] == 'get'
            if '--json' not in args:
                # These pinned Node26 display strings are native facts, not JSON mode.
                wanted_text = {'raw-false':'false\n', 'raw-null':'null\n', 'raw-single-array':"[ 'one' ]\n"}
                assert raw.decode() == wanted_text[row['id']]
                if row['id'] == 'raw-single-array':
                    try:
                        json.loads(raw)
                    except json.JSONDecodeError:
                        pass
                    else:
                        raise AssertionError('Raw singleton unexpectedly treated as JSON')
                continue
            selectors = [a for a in args[1:] if not a.startswith('--')]
            assert len(selectors) <= 1
            selector = selectors[0] if selectors else None
            value = row['before']['package.json']['semantic']
            ok, present, leaf = lookup(value, selector)
            modern = row['id'] != 'npm11-document'
            wrapped = modern and selector is not None
            array = present and isinstance(leaf, list)
            length = len(leaf) if array else 0
            assert not (array and length == 1 and isinstance(leaf[0], list))
            leaf_truthy = truthy(leaf[0]) if array and length == 1 else truthy(leaf)
            queries.append(dict(id=row['id'], preserveArrays=modern, wrapped=wrapped, querySucceeded=ok,
                                fieldPresent=present, isArray=array, length=length, leafTruthy=leaf_truthy))
            emitted = row['exitCode'] == 0 and bool(raw)
            parsed = json.loads(raw) if raw else None
            expected_queries.append(dict(id=row['id'], dataWritten=emitted,
                                         currentIsArray=emitted and isinstance(parsed,list)))
            if ok:
                wanted = ({} if not present else {selector:leaf}) if wrapped else leaf
                assert same_json(parsed, wanted), row['id']
            else:
                assert row['exitCode'] == 1 and 'Cannot convert undefined or null to object' in parsed['error']['summary']
    return (dict(schema=1, queries=queries, saves=saves, appends=appends),
            dict(queries=expected_queries, saves=expected_saves, appends=expected_appends), facts)
