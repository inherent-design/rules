"""Read-only native evidence checks and pure world-group model replay."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUN = ROOT / 'applications/evidence/empack-worlds-20261125T132516653266Z'
GROUPS = ['saves/Study', 'world']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def text_digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def check_effects(progress):
    rows = {o['label']: o for o in progress['observations']}
    for row in rows.values():
        if 'record' in row:
            assert row['record']['initialized_worlds'] == GROUPS
    def file(label, path, text):
        item = rows[label]['snapshot'][path]
        assert item['kind'] == 'file' and item['sha256'] == text_digest(text)
    file('initial-a', 'game/world/level.dat', 'template A\n')
    file('initial-a', 'game/world/region/a.mca', 'region A\n')
    for label in ['update-b', 'repair-b', 'rollback-a-selected']:
        file(label, 'game/world/level.dat', 'played world\n')
        file(label, 'game/world/runtime-output.txt', 'runtime output\n')
        assert 'game/world/region/a.mca' not in rows[label]['snapshot']
        assert 'game/world/region/b.mca' not in rows[label]['snapshot']
    file('update-b', 'game/payload.txt', 'managed B\n')
    file('repair-b', 'game/config/rules.txt', 'ordinary seed B\n')
    file('rollback-a-selected', 'game/payload.txt', 'managed A\n')
    for label in ['omit-world-c', 'reintroduce-b']:
        assert not any(k == 'game/world' or k.startswith('game/world/') for k in rows[label]['snapshot'])
    for label in ['update-b', 'repair-b', 'rollback-a-selected', 'omit-world-c', 'reintroduce-b']:
        file(label, 'game/saves/Study/level.dat', 'client template A\n')
    assert rows['occupied-empty-world']['snapshot']['game/world'] == dict(kind='directory')
    assert not any(k.startswith('game/world/') for k in rows['occupied-empty-world']['snapshot'])
    file('occupied-world-file', 'game/world', 'occupied regular file\n')
    file('occupied-blocked-ancestor', 'game/saves', 'blocked ancestor\n')
    assert rows['occupied-world-link']['snapshot']['game/world']['kind'] == 'symlink'
    return rows


def occupancy(snapshot, group):
    parts = ('game/' + group).split('/')
    for index in range(len(parts)):
        item = snapshot.get('/'.join(parts[:index+1]))
        if item is None: return False
        if index == len(parts)-1 or item['kind'] != 'directory': return True
    raise AssertionError('Nonempty group required')


def main():
    setup, progress = load(RUN / 'setup.json'), load(RUN / 'progress.json')
    assert sha(RUN / 'probe.py') == setup['producerSha256']
    assert sha(RUN / 'continuation-probe.py') == progress['continuations'][0]['producerSha256']
    assert progress['continuations'][0]['fromCommandCount'] == 10
    assert setup['binarySha256'] == '99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
    assert list(setup['environment']) == ['PATH', 'LANG', 'TMPDIR']
    assert load(RUN / 'completed.json')['commandGroupsAbsent'] is True
    commands = progress['commands']; assert len(commands) == 18
    for c in commands:
        assert c['groupAbsent'] and not c.get('timedOut')
        assert c['exitCode'] == (2 if c['label'] == 'rollback-a' else 0)
        for stream in ['stdout', 'stderr']:
            assert sha(RUN / (c['label'] + '.' + stream)) == c[stream + 'Sha256']
    assert '<RELEASE>' in (RUN / 'rollback-a.stderr').read_text()
    assert 'Exact SHA-256 of a retained completed release' in (RUN / 'rollback-help.stdout').read_text()
    rows = check_effects(progress)
    preview = load(RUN / 'preview-instance-files.json'); assert preview['before'] == preview['after']
    releases = {}
    for name in ['a', 'b', 'c']:
        path = RUN / ('release-' + name + '.json'); doc = load(path); releases[name] = doc
        assert sha(path) == rows['release-' + name]['release']
        assert doc['schema'] == 2 and doc['version'] == 'same-label'
        assert doc['files'] == rows['release-' + name]['files']
        for f in doc['files']:
            group = next((g for g in GROUPS if f['destination'].startswith(g + '/')), None)
            assert f.get('world_root') == group
            if group: assert f['policy'] == 'seed'
    assert len({rows['release-' + n]['release'] for n in releases}) == 3
    assert len({d['pack'] for d in releases.values()}) == 1
    # Native result retains player ownership instead of comparing absent world
    # members with publisher hashes. This checks the API result, not syscalls.
    check = load(RUN / 'check-fresh.stdout')
    assert check['complete'] and not check.get('diagnostics')
    world_findings = [v for v in check['findings'] if v['subject'].startswith('world/')]
    assert len(world_findings) == 3 and all(v['state'] == 'player-owned' and not v['required'] for v in world_findings)
    for name in ['empty-world', 'world-file', 'world-link', 'blocked-ancestor']:
        value = load(RUN / (name + '-occupancy.json'))
        before, after = value['before'], value['after']
        root = 'saves' if name == 'blocked-ancestor' else 'world'
        assert before[root] == after[root]
        assert not any(k.startswith(root + '/') for k in after)
    # The producer checked the private symlink target directly. Its separate
    # content inventory was not exported: don't invent that as independent data.
    assert "list(outside.iterdir()) == [outside / 'marker.txt']" in (RUN / 'continuation-probe.py').read_text()
    inputs, expected, provenance = [], [], []
    sequence = [('initial-a', 'a'), ('update-b', 'b'), ('repair-b', 'b'),
                ('rollback-a-selected', 'a'), ('omit-world-c', 'c'), ('reintroduce-b', 'b')]
    previous = None; previous_release = None
    for label, name in sequence + [('occupied-' + n, 'a') for n in ['empty-world', 'world-file', 'world-link', 'blocked-ancestor']]:
        if label.startswith('occupied-'): previous = None; previous_release = None
        for group in GROUPS:
            incoming = any(f.get('world_root') == group for f in releases[name]['files'])
            recorded = previous is not None and group in previous['initialized_worlds']
            old = previous_release is not None and any(f.get('world_root') == group for f in previous_release['files'])
            observed_occupancy = None
            if not recorded and not old and incoming:
                if label == 'initial-a': occupied = False; basis = 'Frozen producer creates a new empty instance; no independent before-image retained.'
                else:
                    before = load(RUN / (label.removeprefix('occupied-') + '-occupancy.json'))['before']
                    occupied = occupancy({'game': {'kind': 'directory'}, **{'game/'+k:v for k,v in before.items()}}, group)
                    basis = 'Native pre-install occupancy snapshot.'
                observed_occupancy = occupied
            else: basis = 'Protection or omission bypasses occupancy; no absence inference.'
            item = dict(id=label + ':' + group, recorded=recorded, oldGroup=old, incoming=incoming,
                        overlapsProtected=False, occupied=observed_occupancy,
                        capturedAbsent=observed_occupancy is False, stillCurrent=True)
            protected = recorded or old or (incoming and observed_occupancy is True)
            # initialized is the native field. Protection/planning are source
            # projections, checked against concrete effect invariants above.
            expected.append(dict(id=item['id'], initializedAfterSuccess=group in rows[label]['record']['initialized_worlds'],
                                 protectedGroup=protected, planMembers=incoming and not protected,
                                 maySeedNewGroup=incoming and not protected))
            inputs.append(item); provenance.append(dict(id=item['id'], occupancyBasis=basis,
                nativeFields=['initializedAfterSuccess'], sourceProjected=['protectedGroup', 'planMembers', 'maySeedNewGroup']))
        previous, previous_release = rows[label]['record'], releases[name]
    model_only = [
        dict(id='old-inventory-fallback', recorded=False, oldGroup=True, incoming=True, overlapsProtected=False, occupied=None, capturedAbsent=False, stillCurrent=True),
        dict(id='overlapping-root', recorded=False, oldGroup=False, incoming=True, overlapsProtected=True, occupied=None, capturedAbsent=False, stillCurrent=True),
        dict(id='late-creation-premise', recorded=False, oldGroup=False, incoming=True, overlapsProtected=False, occupied=False, capturedAbsent=True, stillCurrent=False),
        dict(id='uncaptured-absence', recorded=False, oldGroup=False, incoming=True, overlapsProtected=False, occupied=False, capturedAbsent=False, stillCurrent=True)]
    for item in model_only:
        plan = item['id'] in ['late-creation-premise', 'uncaptured-absence']
        expected.append(dict(id=item['id'], initializedAfterSuccess=True, protectedGroup=not plan, planMembers=plan, maySeedNewGroup=False))
    inputs += model_only
    write(RUN / 'model-input.json', dict(schema=1, cases=inputs)); write(RUN / 'model-provenance.json', provenance)
    generated = ROOT / '.build/empack-worlds-formal'; generated.mkdir(exist_ok=True)
    env = dict(os.environ, LEAN_PATH=str(generated), BEND_NO_TELEMETRY='1')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    command = [lean, '--run', 'applications/empack/WorldsCase.lean', str(RUN / 'model-input.json')]
    result = subprocess.run(command, env=env, cwd=ROOT, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == expected
    def bo(value): return 'True{}' if value else 'False{}'
    pieces, wanted = [], []
    for r, out in zip(inputs, expected, strict=True):
        args = [r[k] for k in ['recorded', 'oldGroup', 'incoming', 'overlapsProtected', 'occupied']]
        for fn, fields, value in [('initialized', args[:3], out['initializedAfterSuccess']),
            ('protected_group', args, out['protectedGroup']), ('plan_members', args, out['planMembers']),
            ('may_seed', args + [r['capturedAbsent'], r['stillCurrent']], out['maySeedNewGroup'])]:
            pieces.append('Bool.show(W.' + fn + '(' + ','.join(map(bo, fields)) + ')) ++ "\\n"')
            wanted.append(str(value))
    case = generated / 'WorldsCase.bend'
    case.write_text('import Base\nimport ../../applications/empack/Worlds.bend as W\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(pieces) + ')\n')
    result = subprocess.run([bend, str(case)], env=env, capture_output=True, text=True, check=True)
    assert result.stdout == '\n'.join(wanted) + '\n'
    negatives = [dict(schema=2, cases=[]), dict(schema=1, cases=[dict(model_only[2], occupied=None)]), dict(schema=1, cases=[{'id': 'missing-input'}])]
    for bad in negatives:
        write(generated / 'invalid.json', bad)
        result = subprocess.run(command[:-1] + [str(generated / 'invalid.json')], env=env, cwd=ROOT, capture_output=True)
        assert result.returncode == 2
    mutated = 0
    for label, path, change in [('update-b', 'game/world/region/b.mca', dict(kind='file', sha256='0'*64)),
            ('reintroduce-b', 'game/world', dict(kind='directory')),
            ('repair-b', 'game/world/level.dat', dict(kind='file', sha256=text_digest('template B\n'))),
            ('occupied-empty-world', 'game/world/level.dat', dict(kind='file', sha256=text_digest('template A\n')))]:
        bad = copy.deepcopy(progress)
        next(o for o in bad['observations']if o['label'] == label)['snapshot'][path] = change
        try: check_effects(bad)
        except AssertionError: mutated += 1
        else: raise AssertionError('Changed effect escaped: ' + label)
    source = ROOT / 'applications/sources/empack-worlds-selections.json'
    for s in load(source)['sources']:
        path = Path('/Users/zer0cell/production/empack') / s['path']
        assert sha(path) == s['sha256']
    files = [p for p in RUN.iterdir()if p.is_file()and p.name not in ['basis.json', 'conformance.json']]
    files += [source] + [HERE / n for n in ['Worlds.lean', 'WorldsCase.lean', 'Worlds.bend', 'worlds_probe.py', Path(__file__).name]]
    write(RUN / 'basis.json', {str(p.relative_to(ROOT)):sha(p)for p in files})
    report = dict(schema=1, loggedWorkflowCommands=18, successful=17, retainedUsageFailure=1,
        additionalHelpQuery=True, modeledNativeGroupRows=20, nativeFieldsPerRow=['initializedAfterSuccess'],
        sourceProjectedFieldsPerRow=['protectedGroup','planMembers','maySeedNewGroup'],
        modelOnlyRows=4, scalarComparisons=96, leanLaws=9, bendLaws=5,
        schemaAndUnknownRefusals=3, changedEffectRefusals=mutated, basisFiles=len(files),
        limits=['No Minecraft/Java/gameplay or EULA test; marker bytes are not playable world data.',
                'Source0b4462e and installed0.8.8 are distinct; no reproducible build correspondence.',
                'Late creation/overlap/fallback controls are model-only; existing native tests were read,not run.',
                'Only initialized fields are native structured model outputs; planning states are source projections checked against effects.',
                'No general crash/concurrency/case-folding/custom-world-provider/consumer qualification.',
                'Preview equality is retained entries/bytes/modes/mtimes,not all metadata or transient effects.'])
    write(RUN / 'conformance.json', report); print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
