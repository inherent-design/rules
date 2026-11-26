"""Decode retained package/Node observations without executing tools or reading private roots."""
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
RUNS = [ROOT / 'applications/evidence' / n for n in [
    'js-overrides-20261126T061550178588Z',
    'js-overrides-20261126T062133072880Z',
    'js-overrides-20261126T062409912906Z',
]]
LEAF, LEFT, RIGHT = 'rules-override-leaf', 'rules-override-left', 'rules-override-right'
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def content(run, entry):
    path = (run / entry['captured']).resolve()
    assert path.is_relative_to((run / 'states').resolve()), 'Unadmitted captured payload path.'
    body = path.read_bytes()
    assert len(body) == entry['bytes'] and hashlib.sha256(body).hexdigest() == entry['sha256']
    return body


def file_body(run, image, path):
    entry = image[path]; assert entry['kind'] == 'file'
    return content(run, entry)


def policy(run, command, side):
    image = command[side]
    if command['manager'] == 'pnpm':
        text = file_body(run, image, 'pnpm-workspace.yaml').decode()
        if '\noverrides:\n' not in text: return []
        result = []
        for line in text.split('\noverrides:\n', 1)[1].splitlines():
            assert line.startswith('  ')
            key, end = json.JSONDecoder().raw_decode(line[2:]); rest = line[2+end:].strip()
            assert rest.startswith(':'); value = json.loads(rest[1:].strip())
            assert isinstance(key, str) and isinstance(value, str)
            result.append([key, value])
        return result
    manifest = json.loads(file_body(run, image, 'package.json'))
    field = 'overrides' if command['manager'] == 'npm' else 'resolutions'
    return list(map(list, manifest.get(field, {}).items()))


def inspect():
    outputs, native, bases, counters = [], [], {}, dict(operations=0, queries=0, mutations=0, requests=0, selfMetadata404s=0)
    for run, count in zip(RUNS, [46,9,6], strict=True):
        receipt = read(run / 'receipt.json'); commands = read(run / 'commands.json'); mutations = read(run / 'mutations.json')
        assert receipt['complete'] and receipt['commands'] == len(commands) == count
        assert receipt['registryThreadRetired'] and receipt['allRecordedGroupsAbsent'] and not receipt['authorizationSeen']
        assert sha(run / 'probe.py') == receipt['producerSha256']
        archives = read(run / 'archives.json'); package = {}
        for item in archives:
            raw = (run / 'archives' / item['filename']).read_bytes()
            assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256']
            assert item['integrity'] == 'sha512-' + base64.b64encode(hashlib.sha512(raw).digest()).decode()
            assert hashlib.sha1(raw).hexdigest() == item['shasum']
            with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
                assert set(archive.getnames()) == {'package/package.json', 'package/index.js'}
                for member in archive.getmembers():
                    assert member.isfile() and not member.issym() and not member.islnk()
                    body = archive.extractfile(member).read(); expected = item['files'][member.name.removeprefix('package/')]
                    assert len(body) == expected['bytes'] and hashlib.sha256(body).hexdigest() == expected['sha256']
                    if member.name == 'package/package.json':
                        manifest = json.loads(body); assert manifest == item['manifest']
                        assert manifest['name'] == item['name'] and manifest['version'] == item['version']
                        assert manifest['dependencies'] == ({} if item['name']==LEAF else {LEAF:'^1.0.0'})
            package[item['name'], item['version']] = item
        assert set(package) == {(LEAF,v)for v in ['1.0.0','1.1.0','2.0.0']} | {(LEFT,'1.0.0'),(RIGHT,'1.0.0')}
        for event in read(run / 'events.json'):
            response = (run / event['response']).resolve(); assert response.is_relative_to((run / 'responses').resolve())
            assert sha(response) == event['sha256'] and not event['authorizationPresent']
            assert event['status'] in [200,404]
            if event['status'] == 404:
                assert event['path'] == '/pnpm'; counters['selfMetadata404s'] += 1
            elif event['path'] in ['/'+LEAF,'/'+LEFT,'/'+RIGHT]:
                metadata = read(response); name=event['path'][1:]
                versions={v for n,v in package if n==name}
                assert metadata['name']==name and set(metadata['versions'])==versions
                assert metadata['dist-tags']['latest']==('2.0.0'if name==LEAF else'1.0.0')
                for version,manifest in metadata['versions'].items():
                    item=package[name,version];dist=manifest['dist']
                    assert all(manifest[k]==v for k,v in item['manifest'].items())
                    assert dist['integrity']==item['integrity'] and dist['shasum']==item['shasum']
                    url=urlsplit(dist['tarball']); assert url.scheme=='http'and url.hostname=='127.0.0.1'
                    assert url.path=='/'+name+'/-/'+item['filename']
            else:
                item=next(i for i in archives if event['path']=='/'+i['name']+'/-/'+i['filename'])
                assert event['sha256']==item['sha256']
            counters['requests'] += 1
        previous, used = {}, set()
        for command in commands:
            key = (command['manager'], command['profile'])
            assert command['groupAbsent'] and not command['timedOut']
            for stream in ['stdout','stderr']:
                assert sha(run / (command['id'] + '.' + stream)) == command[stream + 'Sha256']
            for side in ['before','after']:
                for entry in command[side].values():
                    if entry['kind'] == 'file': content(run, entry)
            if key in previous and command['before'] != previous[key]:
                match = [i for i,m in enumerate(mutations) if (m['manager'],m['profile']) == key
                         and m['before'] == previous[key] and m['after'] == command['before']]
                assert len(match) == 1 and match[0] not in used, 'Unexplained project transition.'
                used.add(match[0])
            previous[key] = command['after']
            before = file_body(run, command['before'], 'package.json')
            after = file_body(run, command['after'], 'package.json')
            assert before == after, 'Native command changed the declared fixture manifest.'
            manifest = json.loads(after)
            assert manifest['dependencies'] == ({LEFT:'1.0.0',RIGHT:'1.0.0'} if command['profile'] in ['graph','range'] else {LEAF:'^1.0.0'})
            if command['query']:
                assert command['before'] == command['after'] and command['exitCode'] == 0
                counters['queries'] += 1
                result = read(run / (command['id'] + '.stdout'))
                assert set(result) == set(manifest['dependencies'])
                versions = {}
                project = Path(receipt['work']) / (command['manager'] + '-' + command['profile']) / 'project'
                def node(value):
                    item = package[value['name'],value['version']]
                    path = Path(value['file']); assert path.is_relative_to(project) and '..' not in path.parts
                    rel = path.relative_to(project).as_posix()
                    code = command['after'][rel]; assert code['sha256'] == item['files']['index.js']['sha256']
                    declaration = command['after'][str(Path(rel).parent / 'package.json')]
                    assert declaration['sha256'] == item['files']['package.json']['sha256']
                    if value['name'] != LEAF:
                        assert value['name'] in [LEFT,RIGHT] and value['version'] == '1.0.0'
                        assert value['leaf']['name'] == LEAF; node(value['leaf'])
                for name, observed in result.items():
                    assert observed['resolved'] == observed['value']['file'] and observed['value']['name'] == name
                    node(observed['value']); versions[name] = observed['value'].get('leaf',observed['value'])['version']
                outputs.append(dict(capture=run.name,id=command['id'],manager=command['manager'],profile=command['profile'],
                                    versions=versions,policy=policy(run, command,'after'),manifestUnchanged=True))
            else:
                counters['operations'] += 1
                changed = sorted(p for p in set(command['before']) | set(command['after']) if command['before'].get(p) != command['after'].get(p))
                if command['id'] == 'npm-direct-force-direct':
                    assert command['exitCode'] == 1 and not changed
                    assert 'EOVERRIDE' in (run / (command['id']+'.stderr')).read_text()
                elif command['id'] == 'yarn-manual-manual-check':
                    assert command['exitCode'] == 1 and not changed
                    assert 'YN0078' in (run / (command['id']+'.stdout')).read_text()
                else: assert command['exitCode'] == 0
                native.append(dict(capture=run.name,id=command['id'],manager=command['manager'],profile=command['profile'],
                                   exit=command['exitCode'],projectChanges=changed,policy=policy(run,command,'after')))
        assert len(used) == len(mutations); counters['mutations'] += len(used)
        for p in sorted(run.rglob('*')):
            if p.is_file(): bases[str(p.relative_to(ROOT))] = sha(p)
    assert counters['operations'] == 31 and counters['queries'] == 30 and counters['mutations'] == 18
    return dict(schema=1,counters=counters,installed=outputs,native=native,basisSha256=bases,
                limitation='Independent native stream/archive/project readback only; no Lean/Bend comparison, full lock parser, resolver proof or final publication qualification yet.')


def main():
    result = inspect(); out = ROOT / '.build/js-overrides-review'; out.mkdir(exist_ok=True)
    (out / 'native-observations.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['counters']))


if __name__ == '__main__': main()
