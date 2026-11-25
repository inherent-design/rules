#!/usr/bin/env python3
"""Inspect linked-filesystem definitions and selected actual resource consumers;never link game classes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile
from mappings import read

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'java'))
from arena_probe import command
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ROOTS = {
    'linkfs': ['net.minecraft.server.packs.linkfs.'+n for n in
        ['LinkFileSystem','LinkFSPath','LinkFSProvider','LinkFSFileStore','PathContents']],
    'callers': ['net.minecraft.client.resources.IndexedAssetSource',
        'net.minecraft.client.resources.ClientPackSource',
        'net.minecraft.server.packs.repository.FolderRepositorySource'],
    'attributes': ['net.minecraft.util.DummyFileAttributes','net.minecraft.server.packs.linkfs.DummyFileAttributes'],
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', choices=['1.21.1', '1.21.4', '1.21.5', '1.21.11', '26.3'], required=True)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--private', type=Path, required=True)
    a = p.parse_args()
    plan = json.loads(a.inputs.read_text())
    assert plan['schema'] == 1
    selected = plan['profiles'][a.version]
    paths = {k: Path(v).resolve() for k, v in selected.items()}
    target = next(t for t in json.loads((HERE/'targets.json').read_text())['javaReferences'] if t['release'] == a.version)
    assert sha(paths['client']) == target['source']['clientSha256']
    assert sha(paths['metadata']) == target['source']['metadataSha256']
    meta = json.loads(paths['metadata'].read_text())
    mapping = None
    if a.version != '26.3':
        assert hashlib.sha1(paths['mappings'].read_bytes()).hexdigest() == meta['downloads']['client_mappings']['sha1']
        mapping = read(paths['mappings'])
    else:
        assert paths['named'] == paths['client'] and 'mappings' not in paths
    assert sha(paths['decompiler']) == '1dfcfe974395734fa467ce620661c7623d05ba83670de0529b1fbd63ff548b9d'
    assert 'JAVA_VERSION="25.' in (paths['jdk']/'release').read_text()
    cap = a.private.resolve()/('linkfs-views-'+a.version+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    cap.mkdir(parents=True)
    for n in ['classes', 'source', 'tmp', 'home']:
        (cap/n).mkdir()
    for src in [Path(__file__), HERE/'mappings.py', HERE.parent/'java/arena_probe.py']:
        shutil.copyfile(src, cap/src.name)
    shutil.copyfile(a.inputs, cap/'inputs.json')
    original = {}; inspection = {}; categories = {k: [] for k in ROOTS}
    with zipfile.ZipFile(paths['client']) as client, zipfile.ZipFile(paths['named']) as named:
        for member in named.namelist():
            if not member.endswith('.class'):
                continue
            name = member[:-6].replace('/', '.')
            groups = [g for g, roots in ROOTS.items() if any(name == r or name.startswith(r+'$') for r in roots)]
            if not groups:
                continue
            binary = mapping[name]['name'].replace('.', '/')+'.class' if mapping else member
            original[name] = dict(member=binary, sha256=hashlib.sha256(client.read(binary)).hexdigest())
            out = cap/'classes'/member; out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(named.read(member))
            inspection[member] = sha(out)
            for group in groups:
                categories[group].append(name)
    assert 3 <= len(original) <= 80
    assert all(categories.values())
    receipt = dict(schema=1, target=target['id'], selectedRelease=a.version, categories=categories,
        inputsSha256=sha(cap/'inputs.json'), clientSha256=sha(paths['client']), metadataSha256=sha(paths['metadata']),
        mappingSha256=sha(paths['mappings']) if mapping else None, namedJarSha256=sha(paths['named']),
        toolSha256=sha(paths['decompiler']), javaSha256=sha(paths['jdk']/'bin/java'), jdkReleaseSha256=sha(paths['jdk']/'release'),
        producersSha256={n: sha(cap/n) for n in ['inspect_linkfs_sources.py', 'mappings.py', 'arena_probe.py']},
        originalClassMembers=original, inspectionClassSha256=inspection,
        limits=['Private bounded source inspection only;no original game class linking or initialization,GUI,provider,game,device or renderer execution.',
                'Named/original class pairing and decompiler views are attributable,not verified translations.',
                'Selected linked-filesystem/resource consumers are not complete pack-provider/native effect closure.',
                'Missing selected root is not a general feature-absence claim;decompiled field candidates are not runtime codec acceptance.'])
    save = lambda: (cap/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    save()
    argv = [str(paths['jdk']/'bin/java'), '-XX:ActiveProcessorCount=2', '-Xmx384m', '-Djava.awt.headless=true',
        '-Duser.home='+str(cap/'home'), '-Djava.io.tmpdir='+str(cap/'tmp'), '-jar', str(paths['decompiler']),
        '--folder', '--log-level=WARN', '--add-external='+str(paths['named']), str(cap/'classes'), str(cap/'source')]
    receipt['command'] = command(argv, cap, 'inspect', dict(os.environ, TMPDIR=str(cap/'tmp')), 120)
    receipt['viewsSha256'] = {str(f.relative_to(cap/'source')): sha(f) for f in (cap/'source').rglob('*.java')}
    save()
    r = receipt['command']; assert r['exitCode'] == 0 and r['ownedGroupAbsent'] and not r['timedOut']
    assert sha(a.inputs) == receipt['inputsSha256'] and sha(paths['client']) == receipt['clientSha256']
    assert sha(paths['named']) == receipt['namedJarSha256']
    assert all(sha(cap/n) == h for n, h in receipt['producersSha256'].items())
    (a.private/('latest-linkfs-views-'+a.version+'.json')).write_text(json.dumps(dict(capture=str(cap)))+'\n')
    print(json.dumps(dict(capture=str(cap), originalClasses=len(original), views=len(receipt['viewsSha256']), groupAbsent=True)))


if __name__ == '__main__':
    main()
