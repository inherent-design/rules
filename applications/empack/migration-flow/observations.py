"""Read retained migration effects independently; never run empack or infer game safety."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / 'applications/evidence/empack-migration-flow-20261126T054446879342Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
helper = ROOT / 'applications/empack/update-flow/observations.py'
spec = importlib.util.spec_from_file_location('prior_author_observations', helper)
prior = importlib.util.module_from_spec(spec); spec.loader.exec_module(prior)
MIGRATE = ['migrate', '--minecraft', '1.21', '--loader', 'fabric', '--loader-version', '0.16.0']
STEPS = [
    ('compatible-sync', 'compatible', ['sync'], 0),
    ('global-prefix-preview', 'compatible', ['--dry-run', *MIGRATE, '--json'], 2),
    ('compatible-preview', 'compatible', [*MIGRATE, '--dry-run', '--json'], 0),
    ('compatible-apply', 'compatible', MIGRATE, 0),
    ('compatible-check', 'compatible', ['check', '--json'], 0),
    ('incompatible-sync', 'incompatible', ['sync'], 0),
    ('incompatible-preview', 'incompatible', [*MIGRATE, '--dry-run', '--json'], 4),
    ('incompatible-apply', 'incompatible', MIGRATE, 4),
    ('explicit-unpin', 'incompatible', ['unpin', 'ferrite'], 0),
    ('automatic-preview', 'incompatible', [*MIGRATE, '--dry-run', '--json'], 0),
    ('automatic-apply', 'incompatible', MIGRATE, 0),
    ('automatic-check', 'incompatible', ['check', '--json'], 0),
]
ACTIONS = ['sync', 'prefix-preview', 'preview', 'apply', 'check', 'sync',
           'preview', 'apply', 'unpin', 'preview', 'apply', 'check']


def state(image, metadata):
    values = prior.author(image, metadata)
    assert values[2] == 0, 'Unexpected materialized payload in referenced fixture.'
    author = prior.text(image, 'empack.yml')
    game_field = r'''^  minecraft: ['"]?([0-9.]+)['"]?$'''
    games = re.findall(game_field, author, re.M)
    assert len(games) == 1 and games[0] in ['1.21.1', '1.21']
    assert "loader: {kind: fabric, pin: '0.16.0'}" in author
    assert 'java: {preferred: 21}' in author
    if 'empack.lock' in image:
        lock = prior.text(image, 'empack.lock')
        assert re.findall(game_field, lock, re.M) == games
    return dict(pin=values[0], selected=values[1], game=1 if games[0] == '1.21.1' else 2, payload=0)


def changed(before, after):
    return sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))


def packets(commands=None):
    commands = read(RUN / 'commands.json') if commands is None else commands
    assert len(commands) == len(STEPS)
    metadata = read(RUN / 'metadata.json')
    assert metadata['project'] == 'uXXizFIs' and metadata['oldGame'] == '1.21.1' and metadata['targetGame'] == '1.21'
    files = {label: next(f for f in metadata[k]['files'] if f['primary']) for label, k in [('old', 'compatible'), ('target', 'incompatible')]}
    for k in ['compatible', 'incompatible']:
        v = metadata[k]; assert v['project_id'] == metadata['project'] and v['loaders'] == ['fabric'] and v['dependencies'] == []
    assert '1.21' in metadata['compatible']['game_versions'] and '1.21' not in metadata['incompatible']['game_versions']
    fixture_meta = {k: dict(file=f) for k, f in files.items()}
    previous, outputs, sources = {}, [], {}
    for command, (label, project, args, code) in zip(commands, STEPS, strict=True):
        assert command['id'] == label and command['project'] == project
        assert command['argv'][command['argv'].index('--yes') + 1:] == args, 'Unexpected command mode/selection.'
        assert command['exitCode'] == code and not command['timedOut'] and command['groupAbsent']
        if project in previous: assert command['before'] == previous[project], 'Broken captured state continuity.'
        previous[project] = command['after']
        before = state(command['before']['project'], fixture_meta)
        after = state(command['after']['project'], fixture_meta)
        effects = {scope: changed(command['before'][scope], command['after'][scope]) for scope in ['project', 'state', 'cache']}
        assert not effects['cache']
        raw = (RUN / (label + '.stdout')).read_bytes()
        for stream in ['stdout', 'stderr']:
            assert sha(RUN / (label + '.' + stream)) == command['streams'][stream]
        facet = []
        if label in ['compatible-preview', 'automatic-preview']:
            value = json.loads(raw); assert value == read(RUN / (label + '.json'))
            assert value['schema'] == 3 and value['proposal'] == 'ready' and value['diagnostic'] is None and value['problem'] is None
            assert value['current_runtime']['minecraft'] == '1.21.1' and value['proposed_runtime']['minecraft'] == '1.21'
            assert value['references'] == ['ferrite/primary'] and not value['materialization_requested'] and not value['native_publication_performed']
            assert len(value['dependencies']) == 1
            dependency = value['dependencies'][0]
            assert dependency['key'] == 'ferrite' and not dependency['source_replaced'] and not dependency['manual_compatibility']
            assert dependency['after']['selection']['project'] == metadata['project']
            assert dependency['after']['selection']['selection'] == metadata['compatible']['id']
            assert dependency['after']['dependency_evidence'] == 'complete' and dependency['after']['reason_chain'] == ['ferrite']
            assert dependency['change'] == ('retained' if label == 'compatible-preview' else 'changed')
            assert {x['path'] for x in value['file_changes']} == {'empack.yml', 'empack.lock'}
            sources[project] = value
            facet = [1, 1, 2, 0]  # ready, proposed selection, two document replacements, no publication
        elif label.endswith('-apply') and code == 0:
            preview = sources[project]
            for file in preview['file_changes']:
                assert file['action'] == 'replace'
                for side in ['before', 'after']:
                    actual = command[side]['project'][file['path']]
                    assert actual['sha256'] == file[side]['sha256'] and actual['bytes'] == file[side]['bytes']
        elif label.endswith('-check'):
            value = json.loads(raw); assert value == read(RUN / (label + '.json'))
            assert value['scope'] == 'recorded' and value['complete'] and value['verified_files'] == 0 and value['references'] == 1
            assert value['authoring']['runtime_satisfied'] and value['authoring']['lock_status'] == 'current'
            assert all(f['state'] == 'passed' for f in value['findings'] if f['required'])
            prior.inspect(value['authoring'], [after['pin'], after['selected'], 0])
            facet = [1, 0, 1]  # complete, verified payload files, references
        elif label == 'global-prefix-preview':
            error = (RUN / (label + '.stderr')).read_text()
            assert not raw and '--dry-run' in error and 'required arguments were not provided' in error
        elif code == 4:
            assert not raw
            assert 'No provider file satisfies the requested compatibility and release policy' in (RUN / (label + '.stderr')).read_text()
        if code != 0 or 'preview' in label or label.endswith('-check'):
            assert command['before'] == command['after'], 'Captured preview/refusal/check effect.'
        else:
            assert effects['state'] and effects['project'] == (['empack.lock'] if label.endswith('-sync') else ['empack.lock', 'empack.yml'])
        outputs.append(dict(id=label, project=project, before=before, after=after, exit=code,
                            projectChanges=effects['project'], stateChanged=bool(effects['state']), cacheChanged=False, facet=facet))
    return dict(schema=1, profile='released-two-project-target-validation',
                steps=[dict(id=x[0], project=x[1], action=action) for x, action in zip(STEPS, ACTIONS, strict=True)]), outputs


def main():
    receipt, setup = read(RUN / 'receipt.json'), read(RUN / 'setup.json')
    assert receipt['complete'] and receipt['commands'] == 12 and receipt['allRecordedGroupsAbsent']
    assert sha(RUN / 'setup.json') == receipt['setupSha256'] and sha(RUN / 'metadata.json') == receipt['metadataSha256']
    assert sha(RUN / 'probe.py') == receipt['producerSha256'] == sha(Path(__file__).with_name('probe.py'))
    packet, outputs = packets()
    result = dict(schema=1, input=packet, observed=outputs, scope='Retained-data readback; no model comparison or native replay yet.',
                  producerSha256=sha(Path(__file__)), textHelperSha256=sha(helper),
                  basisSha256={p.name: sha(p) for p in sorted(RUN.iterdir()) if p.is_file()},
                  privateMetadata=setup['privateMetadataSha256'])
    out = ROOT / '.build/empack-migration-flow-review'; out.mkdir(exist_ok=True)
    (out / 'native-observations.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(commands=len(outputs), providerTargetBranches=2, parserPrefixExit=outputs[1]['exit'], migrationModelComparisons=0)))


if __name__ == '__main__':
    main()
