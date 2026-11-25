#!/usr/bin/env python3
"""Hash Git tree entry metadata, preserving object kind independently of a name."""
import hashlib


def tree_hash(entries):
    allowed = {'tree': {'040000', '40000'}, 'blob': {'100644', '100755', '120000'}, 'commit': {'160000'}}
    assert len({r['path'] for r in entries}) == len(entries)
    for r in entries:
        assert r['type'] in allowed and r['mode'] in allowed[r['type']]
        assert '/' not in r['path'] and r['path'] not in ['', '.', '..']
        assert len(bytes.fromhex(r['sha'])) == 20
    ordered = sorted(entries, key=lambda r: r['path'].encode() + (b'/' if r['type'] == 'tree' else b''))
    body = b''.join(r['mode'].lstrip('0').encode() + b' ' + r['path'].encode() + b'\0' + bytes.fromhex(r['sha']) for r in ordered)
    return hashlib.sha1(b'tree ' + str(len(body)).encode() + b'\0' + body).hexdigest()


def verify_recursive(document):
    assert not document.get('truncated')
    groups = {}
    declared = {}
    for r in document['tree']:
        parent, _, name = r['path'].rpartition('/')
        groups.setdefault(parent, []).append(dict(path=name, mode=r['mode'], type=r['type'], sha=r['sha']))
        if r['type'] == 'tree':
            declared[r['path']] = r['sha']
    for path, expected in declared.items():
        assert tree_hash(groups.get(path, [])) == expected, path
    return tree_hash(groups.get('', [])), groups.get('', []), len(declared)


def verify_receipt(receipt, targets):
    expected = {t['id']: t for t in targets['bedrockReferences']}
    assert receipt['schema'] == 1 and {r['target'] for r in receipt['records']} == set(expected)
    for r in receipt['records']:
        s = expected[r['target']]['source']
        assert r['commit'] == s['commit']
        assert tree_hash(r['rootEntries']) == r['gitTree'] == s['gitTree']
        assert r['treeResponseName'] == s['treeResponseName'] == r['previouslyMislabeledTree']
        assert r['gitTree'] != r['commit']
        assert r['commitApiUrl'] == s['gitCommitApiUrl']
        assert r['commitResponseSha256'] == s['gitCommitResponseSha256']
        assert r['recursiveTreeResponseSha256'] == s['treeResponseSha256']
