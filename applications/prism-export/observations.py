"""Read retained source-component observations. Never launch Prism or a compiler."""
import hashlib
import json
from pathlib import Path
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'applications/evidence/prism-export-headless-20261126T075341047978Z'
load = lambda p: json.loads(p.read_text())
sha = lambda b: hashlib.sha256(b).hexdigest()


def packets(run=RUN):
    inputs, before, after = (load(run / n) for n in ['input.json', 'before.json', 'after.json'])
    native = [json.loads(s) for s in (run / 'observe.stdout').read_text().splitlines()]
    assert native[0] == {'kind': 'backend', 'qt': '6.12.0', 'archive': 'libarchive 3.8.11'}
    assert len(native) == len(inputs['cases']) + 1 == 9
    observed = {r['id']: r for r in native[1:]}
    artifacts = {r['id']: r for r in load(run / 'artifacts.json')}
    label_names = sorted({'.minecraft/' + n for n in ['config/.hidden-dir/inside.txt', 'config/.hidden-file', 'config/linked.txt', 'config/visible.txt', 'logs/latest.log', 'saves/world/README.txt']} | {'.hidden-root', 'instance.cfg'} |
                         {'config/.hidden-dir/inside.txt', 'config/.hidden-file', 'config/linked.txt', 'config/visible.txt', 'logs/latest.log', 'saves/world/README.txt', 'metadata.json'})
    labels = {n: i for i, n in enumerate(label_names)}
    model, views, contents = [], [], []
    for r in inputs['cases']:
        case, raw, artifact = r['id'], observed[r['id']], artifacts[r['id']]
        root_relative = Path(r['root']).relative_to(Path(load(run / 'setup.json')['work']) / 'cases').as_posix()
        root_exists = root_relative in before and before[root_relative]['kind'] == 'directory'
        prefix = root_relative + '/'
        entries = []
        # Independent traversal of the frozen preimage. This fixture uses ASCII names
        # with no case-equivalent ties; directories precede files, as in QDir defaults.
        def traverse(directory):
            children = [(p, v) for p, v in before.items() if Path(p).parent.as_posix() == directory]
            for p, v in sorted(children):
                if v['kind'] == 'directory':
                    traverse(p)
            for p, v in sorted(children):
                if v['kind'] in ['file', 'link']:
                    name = p[len(prefix):]
                    entries.append(dict(id=labels[name], leafHidden=Path(name).name.startswith('.'),
                                        excluded=r['filter'] and name in r['excludeAtCollect'],
                                        missingAtWrite=name == r.get('removeAfterCollect'), link=v['kind'] == 'link'))
        if root_exists:
            traverse(root_relative)
        eligible = [e for e in entries if not e['leafHidden']]
        assert raw['filterCalls'] == ([label_names[e['id']] for e in eligible] if r['filter'] else [])
        output_before = before[case + '/output.zip']
        output_after = after[case + '/output.zip']
        directory_output = output_before['kind'] == 'directory'
        selected_ids = [labels[n] for n in raw['files']]
        if not raw['collected']:
            assert raw['methodInvoked'] is False and not raw['files'] and raw['methodError'] is None
            state = 0
        elif raw['methodError'] == 'Could not create file':
            state = 1
        elif raw['methodError'] is not None:
            assert raw['methodError'] == 'Could not read and compress config/visible.txt'
            state = 3
        elif raw['canceledWitness']:
            assert raw['statuses'] == []
            state = 4
        else:
            state = 2
        assert raw['canceledWitness'] == r['canceled']
        assert raw['methodInvoked'] == raw['collected']
        assert raw['outputExists'] and artifact['exists']
        members, raw_members = [], []
        output = run / 'outputs' / (case + '.zip')
        if artifact['isFile']:
            assert output.stat().st_size == artifact['bytes'] and sha(output.read_bytes()) == artifact['sha256'] == output_after['sha256']
            if artifact.get('notZip'):
                assert state == 0 and output.read_bytes() == b'PREVIOUS OUTPUT\n'
            else:
                with zipfile.ZipFile(output) as z:
                    assert z.testzip() is None
                    for m in z.infolist():
                        payload = z.read(m)
                        raw_members.append(dict(name=m.filename, mode=m.external_attr >> 16, bytes=m.file_size, sha256=sha(payload)))
                        is_extra = m.filename in r['extra']
                        name = m.filename if is_extra else m.filename.removeprefix(r['prefix'])
                        assert is_extra or m.filename == r['prefix'] + name
                        link = stat.S_ISLNK(m.external_attr >> 16)
                        members.append(dict(id=labels[name], placement=0 if is_extra else int(bool(r['prefix'])), link=link))
                        if is_extra:
                            wanted = r['extra'][name].encode()
                            assert payload == wanted and not link
                        else:
                            source = before[prefix + name]
                            if source['kind'] == 'link':
                                if r['follow']:
                                    target = Path(source['target']).relative_to(Path(load(run / 'setup.json')['work']) / 'cases').as_posix()
                                    assert sha(payload) == before[target]['sha256'] and not link
                                else:
                                    assert payload == source['target'].encode() and link
                            else:
                                assert sha(payload) == source['sha256'] and not link
                        contents.append(dict(case=case, member=m.filename, bytes=m.file_size, link=link))
                assert raw_members == artifact['members']
        else:
            assert directory_output and output_after == output_before and not output.exists()
        model.append(dict(id=case, rootExists=root_exists, outputDirectory=directory_output, canceled=r['canceled'], follow=r['follow'],
                          placement=int(bool(r['prefix'])), entries=entries, extras=[labels[n] for n in sorted(r['extra'])]))
        views.append(dict(id=case, selected=selected_ids, state=state, members=members,
                          errorPresent=raw['methodError'] is not None, outputReplaced=output_before != output_after,
                          completed=state == 2 and not raw['canceledWitness']))
        # Only the explicitly requested vanished-input mutation and output may change.
        changes = [k for k in before.keys() | after.keys() if before.get(k) != after.get(k) and k.startswith(case + '/')]
        allowed = {case + '/output.zip'}
        if 'removeAfterCollect' in r:
            allowed.add(root_relative + '/' + r['removeAfterCollect'])
        assert set(changes) <= allowed
        if 'removeAfterCollect' in r:
            assert root_relative + '/' + r['removeAfterCollect'] not in after
    return {'schema': 1, 'cases': model}, views, dict(labels=label_names, contents=contents)
