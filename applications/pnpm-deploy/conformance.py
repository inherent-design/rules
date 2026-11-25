"""Pure retained-data/model replay. Never execute pnpm, Node, or a deploy."""
import copy
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUN = ROOT / 'applications/evidence/pnpm-deploy-20261125T152000035565Z'
ALIAS = ROOT / 'applications/evidence/pnpm-deploy-alias-20261125T152635252659Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())
NAMES = ['rules-deploy-app', 'rules-deploy-lib', 'rules-deploy-leaf', 'rules-deploy-ext', 'rules-deploy-opt', 'rules-deploy-dev']


def write(p, value):
    p.write_text(json.dumps(value, indent=2) + '\n')


def compare(actual, expected):
    assert actual == expected, 'Deploy model differs from retained outcome or effects'


def verify(folder):
    receipt = load(folder / 'receipt.json')
    assert receipt['complete'] and sha(folder / 'probe.py') == receipt['producerSha256']
    for row in receipt['commands']:
        assert row['groupAbsent'] and not row['timedOut']
        for stream in ['stdout', 'stderr']:
            assert sha(folder / (row['label'] + '.' + stream)) == row[stream + 'Sha256']
    for name, tool in receipt['tools'].items():
        path = Path(tool['path'])
        if path.exists():
            assert sha(path) == tool['sha256']
    return receipt


def target_facts(target, project, selected, force, occupied, unsafe_link):
    target, project, selected = map(lambda p: Path(os.path.normpath(p)), [target, project, selected])
    ancestor_or_same = lambda a, b: a == b or a in b.parents
    return dict(unsafeTarget=ancestor_or_same(target, project) or ancestor_or_same(target, selected),
        force=force, inside=project in target.parents, unsafeLink=unsafe_link, occupied=occupied)


def stage(folder, identity, code):
    if code == 0:
        return 0
    assert code == 1
    text = (folder / (identity + '.stderr')).read_text()
    for diagnostic, tag in [('ERR_PNPM_NOTHING_TO_DEPLOY', 1), ('ERR_PNPM_CANNOT_DEPLOY_MANY', 2),
            ('ERR_PNPM_INVALID_DEPLOY_TARGET', 3), ('ERR_PNPM_DEPLOY_DIR_NOT_EMPTY', 4),
            ('ERR_PNPM_TARBALL_READ_LOCAL_TARBALL', 5)]:
        if diagnostic in text:
            return tag
    raise AssertionError('Refusal outside this admitted deploy corpus')


def effects(before, after, payload_sha, native_code, source_preserved):
    original = before.get('index.cjs')
    current = after.get('index.cjs')
    copied = bool(current and current.get('sha256') == payload_sha and current != original)
    removed = any(key not in after or (item.get('sha256') and item.get('sha256') != after[key].get('sha256'))
        for key, item in before.items() if item['kind'] == 'file')
    return dict(payloadCopied=copied, priorRemoved=removed, commandSucceeded=native_code == 0,
        sourcePreserved=source_preserved)


def observed_alias(row, payload_sha):
    before = {key.removeprefix('packages/app/'): value for key, value in row['before'].items() if key.startswith('packages/app/')}
    return dict(id=row['id'], code=stage(ALIAS, row['id'], row['exitCode']),
        **effects(before, row['sourceSnapshot'], payload_sha, row['exitCode'], row['before'] == row['after']),
        direct=[], closure=[])


def contained_links(snapshot):
    """Resolve the selected relative-link corpus without opening the host FS."""
    for origin, item in snapshot.items():
        if item['kind'] != 'symlink':
            continue
        pending = origin
        for _ in range(len(snapshot) + 1):
            parts = PurePosixPath(pending).parts
            replacement = None
            for count in range(1, len(parts) + 1):
                prefix = '/'.join(parts[:count])
                entry = snapshot.get(prefix)
                if entry and entry['kind'] == 'symlink':
                    target = entry['target']
                    assert not target.startswith('/'), (origin, 'absolute backing')
                    replacement = posixpath.normpath(posixpath.join(posixpath.dirname(prefix), target, *parts[count:]))
                    assert replacement != '..' and not replacement.startswith('../'), (origin, 'escaped backing')
                    break
            if replacement is None:
                assert pending in snapshot, (origin, 'missing backing')
                break
            pending = replacement
        else:
            raise AssertionError('Cyclic or excessive link chain')


def graph_from_sources(metadata):
    manifests = {json.loads(text)['name']: json.loads(text) for path, text in metadata.items() if path.endswith('package.json')}
    with tarfile.open(RUN / 'external.tgz') as archive:
        assert archive.getnames() == ['package/package.json', 'package/index.cjs']
        manifests['rules-deploy-ext'] = json.load(archive.extractfile('package/package.json'))
    assert set(manifests) == set(NAMES)
    roots, edges = [], []
    for group, field in enumerate(['dependencies', 'optionalDependencies', 'devDependencies']):
        roots += [dict(target=NAMES.index(name), group=group) for name in manifests[NAMES[0]].get(field, {})]
    for owner, manifest in manifests.items():
        if owner == NAMES[0]:
            continue
        assert not manifest.get('devDependencies') and not manifest.get('optionalDependencies') and not manifest.get('peerDependencies')
        edges += [dict(owner=NAMES.index(owner), target=NAMES.index(name)) for name in manifest.get('dependencies', {})]
    return roots, edges


def main():
    receipt, alias = verify(RUN), verify(ALIAS)
    assert sha(ALIAS / 'helpers.py') == alias['helperSha256']
    assert receipt['externalRestored'] and sha(RUN / 'external.tgz') == receipt['externalSha256']
    retained = load(RUN / 'retained-metadata.json')
    source_files = load(RUN / 'source-inputs.json')
    for path, text in retained['sourcePackageText'].items():
        assert hashlib.sha256(text.encode()).hexdigest() == source_files[path]['sha256']
    roots, edges = graph_from_sources(retained['sourcePackageText'])
    workspace_names = ['rules-deploy-root'] + [json.loads(text)['name'] for path, text in retained['sourcePackageText'].items() if path.endswith('package.json')]
    input_rows, expected = [], []
    closure_evidence = []
    project = Path(receipt['work']) / 'project'
    payload_sha = source_files['app/index.cjs']['sha256']
    for row in receipt['cases']:
        assert row['beforeSource'] == row['afterSource']
        selected = {name for name in workspace_names if any(fnmatch.fnmatchcase(name, selector) for selector in row['filters'])}
        facts = target_facts(row['target'], project, project / 'packages/app', '--force' in row['flags'],
            bool(row['beforeTarget']), str(row['target']).startswith(str(project / 'through-link') + '/'))
        actual_code = stage(RUN, row['id'], row['exitCode'])
        # An unreached install is unknown, not a successful availability lookup.
        available = None if actual_code in [1, 2, 3, 4] else row['id'] != 'missing-archive'
        if available is False:
            assert '--store-dir' in row['flags'] and row['id'] == 'missing-archive'
            assert not (row['afterTarget'].get('marker.txt'))
        item = dict(id=row['id'], selected=len(selected), **facts, aliasesSource=False,
            installAvailable=available, production='--prod' in row['flags'], optional='--no-optional' not in row['flags'])
        input_rows.append(item)
        outcome = dict(id=row['id'], code=actual_code, **effects(row['beforeTarget'], row['afterTarget'], payload_sha, row['exitCode'], True), direct=[], closure=[])
        texts = retained['targetMetadataText'].get(row['id'], {})
        for path, text in texts.items():
            assert hashlib.sha256(text.encode()).hexdigest() == row['afterTarget'][path]['sha256']
        if row['exitCode'] == 0:
            assert row['sourceRestored'] and 'private.txt' not in row['afterTarget']
            assert row['afterTarget']['index.cjs']['sha256'] == payload_sha
            contained_links(row['portableSnapshot'])
            installed = [json.loads(text)['name'] for path, text in texts.items() if path.endswith('package.json')]
            assert len(installed) == len(set(installed))
            outcome['closure'] = sorted(NAMES.index(name) for name in installed)
            for suffix in ['runtime', 'portable']:
                runtime = load(RUN / (row['id'] + '-' + suffix + '.stdout'))
                assert runtime['app'] == dict(app='app', lib=dict(lib='lib', leaf='leaf'), ext='external-v1')
                exposed = sorted(NAMES.index(name) for name in NAMES[1:] if 'value' in runtime[name])
                if suffix == 'runtime':
                    outcome['direct'] = exposed
                else:
                    assert exposed == outcome['direct']
                root = Path(row['target']) if suffix == 'runtime' else Path(receipt['work']) / 'portable' / row['id']
                for name in NAMES[1:]:
                    if 'value' in runtime[name]:
                        assert Path(runtime[name]['realpath']).is_relative_to(root)
                    else:
                        assert runtime[name]['error'] == 'MODULE_NOT_FOUND'
            assert runtime[NAMES[2]] == dict(error='MODULE_NOT_FOUND')
            closure_evidence.append(dict(id=row['id'], installed=installed, exposed=outcome['direct'],
                runtimeApp=runtime['app'], backing='All recorded relative symlinks resolve within the copied output snapshot.',
                manifestSourceReferences=[spec for field in ['dependencies', 'optionalDependencies', 'devDependencies']
                    for spec in json.loads(texts['package.json']).get(field, {}).values()]))
        expected.append(outcome)
    main_input = dict(schema=1, nodes=len(NAMES), roots=roots, edges=edges, rows=input_rows)
    alias_inputs, alias_outputs = [], []
    alias_project = Path(alias['work']) / 'project'
    original_app = alias_project / 'packages/app'
    original_payload = ALIAS / 'preimage/packages/app/index.cjs'
    alias_payload_sha = sha(original_payload)
    for row in alias['cases']:
        assert row['available'] and row['sameSourceObjectBefore']
        assert row['identityBefore']['original'] == row['identityBefore']['alias']
        before_target = {key.removeprefix('packages/app/'): value for key, value in row['before'].items() if key.startswith('packages/app/')}
        for name in ['package.json', 'index.cjs', 'private.txt']:
            assert sha(ALIAS / 'preimage/packages/app' / name) == before_target[name]['sha256']
        facts = target_facts(row['target'], alias_project, original_app, True, True, False)
        code = stage(ALIAS, row['id'], row['exitCode'])
        alias_inputs.append(dict(id=row['id'], selected=1, **facts, aliasesSource=True,
            installAvailable=None if code == 3 else True, production=False, optional=True))
        outcome = observed_alias(row, alias_payload_sha)
        alias_outputs.append(outcome)
    assert alias_outputs[0]['sourcePreserved'] and alias_outputs[1]['commandSucceeded'] and not alias_outputs[1]['payloadCopied']
    assert not alias_outputs[1]['sourcePreserved'] and 'private.txt' not in alias['cases'][1]['sourceSnapshot']
    assert sha(ALIAS / 'postimage-package.json') == alias['cases'][1]['sourceSnapshot']['package.json']['sha256']
    assert load(ALIAS / 'postimage-package.json')['main'] == 'index.cjs'
    proof = load(RUN / 'proof-gate.json')
    assert proof['observedExitCode'] == 0 and proof['observedSummary'] == 'Checked 2 Lean modules and 1 Bend files.'
    for path, digest in proof['sourceSha256'].items():
        assert sha(ROOT / path) == digest
    alias_input = dict(schema=1, nodes=1, roots=[], edges=[], rows=alias_inputs)
    formal = ROOT / '.build/pnpm-deploy-formal'
    env = {**os.environ, 'LEAN_PATH': str(formal), 'BEND_NO_TELEMETRY': '1'}
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    command = [lean, '--run', 'applications/pnpm-deploy/DeployCase.lean']
    for label, inputs, outputs in [('main', main_input, expected), ('alias', alias_input, alias_outputs)]:
        path = RUN / (label + '-model-input.json')
        write(path, inputs)
        actual = json.loads(subprocess.run(command + [str(path)], cwd=ROOT, env=env, check=True, capture_output=True, text=True).stdout)
        compare(actual, outputs)
    write(RUN / 'closure-evidence.json', closure_evidence)
    write(RUN / 'observed-model-values.json', dict(main=expected, alias=alias_outputs))
    bo = lambda b: 'True{}' if b else 'False{}'
    opt = lambda b: 'None{}' if b is None else 'Some{' + bo(b) + '}'
    calls, wanted = [], []
    for inputs, outputs in [(main_input, expected), (alias_input, alias_outputs)]:
        universe = '[' + ','.join(str(n) + 'n' for n in range(inputs['nodes'])) + ']'
        deps = '[' + ','.join('D.Root{' + str(r['target']) + 'n,' + str(r['group']) + 'n}' for r in inputs['roots']) + ']'
        arcs = '[' + ','.join('D.Edge{' + str(e['owner']) + 'n,' + str(e['target']) + 'n}' for e in inputs['edges']) + ']'
        for row, out in zip(inputs['rows'], outputs, strict=True):
            admitted = 'D.admission(' + str(row['selected']) + 'n,' + ','.join(bo(row[k]) for k in ['unsafeTarget', 'force', 'inside', 'unsafeLink', 'occupied']) + ')'
            outcome = 'D.finish(' + admitted + ',' + ','.join(bo(row[k]) for k in ['force', 'occupied', 'aliasesSource']) + ',' + opt(row['installAvailable']) + ')'
            selected = 'D.roots(' + deps + ',' + bo(row['production']) + ',' + bo(row['optional']) + ')'
            calls += ['D.show_outcome(' + outcome + ')',
                'D.show_list(D.runtime_direct(' + outcome + ',' + universe + ',' + selected + '))',
                'D.show_list(D.runtime_closure(' + outcome + ',' + str(inputs['nodes']) + 'n,' + universe + ',' + arcs + ',' + selected + '))']
            wanted += [str(out['code']) + ':' + ':'.join(str(out[k]) for k in ['payloadCopied', 'priorRemoved', 'commandSucceeded', 'sourcePreserved']),
                ''.join(str(n) + ',' for n in out['direct']), ''.join(str(n) + ',' for n in out['closure'])]
    case = formal / 'Replay.bend'
    case.write_text('import ../../applications/pnpm-deploy/Deploy.bend as D\nimport Base\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ "\\n" ++ '.join(calls) + ' ++ "\\n")\n')
    result = subprocess.run([bend, str(case)], cwd=ROOT, env=env, check=True, capture_output=True, text=True)
    compare(result.stdout.splitlines(), wanted)
    controls = []
    for key in ['payloadCopied', 'priorRemoved', 'commandSucceeded', 'sourcePreserved']:
        changed = copy.deepcopy(alias['cases'][1])
        original_target = {k.removeprefix('packages/app/'): v for k, v in changed['before'].items() if k.startswith('packages/app/')}
        if key == 'payloadCopied':
            changed['sourceSnapshot']['index.cjs'] = dict(original_target['index.cjs'], mtimeNs='changed-observation')
        elif key == 'priorRemoved':
            changed['sourceSnapshot'] = original_target
        elif key == 'commandSucceeded':
            changed['exitCode'] = 1
        else:
            changed['after'] = copy.deepcopy(changed['before'])
        try:
            compare(alias_outputs[1], observed_alias(changed, alias_payload_sha))
        except AssertionError:
            controls.append('changed-alias-' + key)
        else:
            raise AssertionError('Altered source-loss observation escaped')
    for label, alter, cause in [('schema', lambda d: d.update(schema=2), 'Unsupported deploy study schema'),
            ('unknown-install', lambda d: d['rows'][4].update(installAvailable=None), 'installation evidence is unknown'),
            ('outside-graph', lambda d: d['edges'][0].update(target=d['nodes']), 'outside the admitted universe or groups'),
            ('unknown-group', lambda d: d['roots'][0].update(group=3), 'outside the admitted universe or groups'),
            ('duplicate-root', lambda d: d['roots'].append(dict(d['roots'][0])), 'Duplicate root target')]:
        changed = copy.deepcopy(main_input)
        alter(changed)
        path = formal / (label + '.json')
        write(path, changed)
        error = subprocess.run(command + [str(path)], cwd=ROOT, env=env, capture_output=True, text=True)
        assert error.returncode == 2 and cause in error.stderr, (label, error.stderr)
        controls.append(label)
    ledger = load(ROOT / 'applications/sources/pnpm-deploy-selections.json')
    verified_sources, unavailable_sources = [], []
    for source in ledger['sources']:
        path = ROOT / source['cache']
        if path.exists():
            data = path.read_bytes()
            assert sha(path) == source['sha256']
            assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == source['gitBlob']
            verified_sources.append(source['path'])
        else:
            unavailable_sources.append(source['path'])
    files = [p for folder in [RUN, ALIAS] for p in folder.rglob('*') if p.is_file() and p.name not in ['basis.json', 'conformance.json']]
    files += list(HERE.glob('*.py')) + list(HERE.glob('*.lean')) + list(HERE.glob('*.bend')) + [ROOT / 'applications/sources/pnpm-deploy-selections.json']
    write(RUN / 'basis.json', {str(p.relative_to(ROOT)): sha(p) for p in files})
    report = dict(schema=1, deployCommands=14, ordinaryDeploys=12, aliasControls=2, ordinaryRuntimeReads=10,
        ordinarySuccesses=5, ordinaryRefusals=7, aliasCommandSuccessWithSourceLoss=True,
        modelOutcomeRecords=len(expected) + len(alias_outputs), directAndClosureRecords=10,
        leanLaws=20, bendLaws=9, negativeControls=controls, basisFiles=len(files),
        cachedSourcesVerified=verified_sources, unavailableSourceCaches=unavailable_sources,
        limits=['Own macOS workspace;exact pinned12.21 executable/source support a bounded defect,not latest-upstream or all filesystem claims.',
            'Current lexical admission and proposed physical-conflict guard are separate;no candidate patch or atomic filesystem proof.',
            'Ordinary graph has root runtime/optional/development groups and one transitive runtime edge;no peers/platform/addons/scripts.',
            'Runtime copyability is distinct from source-referenced manifests being reinstallable.',
            'Availability facts are admitted for executed installs only;early guards retain unknown.',
            'No registry/network service,publication,crash,rollback,other-host or full package-manager qualification.'])
    write(RUN / 'conformance.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
