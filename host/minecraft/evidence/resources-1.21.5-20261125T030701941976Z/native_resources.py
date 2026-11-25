#!/usr/bin/env python3
"""Owner-run original resource-manager methods on generated private folders.

No acquisition, game launch, user packs, worlds, or account access. Not CI.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import zipfile
import hashlib

from mappings import read
from native_codecs import run_command, sha, JDK

HERE=Path(__file__).resolve().parent


def image(root):
    return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def fixtures(root):
    cases=[]

    def add(name, low_body="LOW", high_body=None, low_meta={"texture":{"blur":True}}, high_meta=None,
            filter_path=None, filter_namespace="fixture", reverse=False, query="fixture:defs/entry.txt", prefix="defs"):
        order=[]
        for side,body,meta in [('low',low_body,low_meta),('high',high_body,high_meta)]:
            pack=root/(name+'-'+side);pack.mkdir()
            mcmeta={"pack":{"pack_format":34,"description":"Generated study pack"}}
            if side=='high' and filter_path is not None: mcmeta['filter']={"block":[{"namespace":filter_namespace,"path":filter_path}]}
            (pack/'pack.mcmeta').write_text(json.dumps(mcmeta)+'\n')
            target=pack/'assets/fixture/defs';target.mkdir(parents=True)
            if body is not None:(target/'entry.txt').write_text(body)
            if meta is not None:(target/'entry.txt.mcmeta').write_text(meta if isinstance(meta,str) else json.dumps(meta))
            (pack/'assets/fixture/canary.txt').write_text('OWNED-CANARY')
            order.append(pack.name)
        if reverse:order.reverse()
        cases.append(dict(id=name,order=order,query=query,prefix=prefix))

    add('low-only')
    add('high-replaces',high_body='HIGH',high_meta={"texture":{"blur":False,"clamp":True}})
    add('reversed-order',high_body='HIGH',high_meta={"texture":{"blur":False,"clamp":True}},reverse=True)
    add('higher-metadata-only',high_meta={"texture":{"blur":False,"clamp":True}})
    add('lower-metadata-only',high_body='HIGH')
    add('filter-removes-lower',filter_path='defs/entry.txt')
    add('filter-keeps-own',high_body='HIGH',filter_path='defs/entry.txt')
    add('filter-other-namespace',filter_path='defs/entry.txt',filter_namespace='other')
    add('filter-other-path',filter_path='defs/other.txt')
    add('filter-metadata-only',filter_path=r'defs/entry\.txt\.mcmeta')
    add('filter-with-own-metadata',filter_path=r'defs/entry\.txt\.mcmeta',high_meta={"texture":{"blur":False,"clamp":True}})
    add('malformed-higher-metadata',high_meta='{malformed')
    add('malformed-lower-metadata',high_body='HIGH',low_meta='{malformed')
    add('no-metadata',low_meta=None)
    add('selected-invalid-content',high_body='{malformed')
    add('dot-path-identifier',query='fixture:defs/../canary.txt')
    add('empty-path-identifier',query='fixture:')
    add('trailing-directory-prefix',prefix='defs/')
    return cases


def collect(private,version):
    source_ids={s['id']:s for s in json.loads((HERE/'sources.json').read_text())['sources']}
    local=json.loads((private/'local-basis.json').read_text())
    client=Path(local['vanilla_1.21.1']['path']) if version=='1.21.1' else private/(version+'-client.jar')
    mapping_path=private/(version+'-client-mappings.txt')
    assert sha(client)==source_ids[f'mojang:{version}:client']['sha256']
    assert sha(mapping_path)==source_ids[f'mojang:{version}:client_mappings']['sha256']
    libraries=[]
    for row in json.loads((private/'library-locators.json').read_text())[version]:
        if row['cachedPath'] is None:
            assert row['name'].startswith('io.netty:netty-transport-native-epoll:') and ':linux-' in row['name'];continue
        path=Path(row['cachedPath']);assert sha(path,'sha1')==row['artifact']['sha1']
        libraries.append(dict(path=str(path),sha256=sha(path),sha1=row['artifact']['sha1']))
    directory=private/('resources-'+version+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));directory.mkdir()
    for name in ['fixtures','classes','home','tmp']:(directory/name).mkdir()
    for name in ['ResourceProbe.java','native_resources.py','native_codecs.py','mappings.py']:shutil.copyfile(HERE/name,directory/name)
    cases=fixtures(directory/'fixtures');before=image(directory/'fixtures')
    names=['net.minecraft.SharedConstants','net.minecraft.server.Bootstrap','net.minecraft.server.packs.PathPackResources',
        'net.minecraft.server.packs.PackLocationInfo','net.minecraft.network.chat.Component','net.minecraft.server.packs.repository.PackSource',
        'net.minecraft.server.packs.PackType','net.minecraft.resources.ResourceLocation','net.minecraft.server.packs.resources.MultiPackResourceManager',
        'net.minecraft.server.packs.resources.Resource','net.minecraft.server.packs.resources.ResourceMetadata',
        'net.minecraft.client.resources.metadata.texture.TextureMetadataSection',
        'net.minecraft.server.packs.metadata.MetadataSectionType' if version=='1.21.5' else 'net.minecraft.server.packs.metadata.MetadataSectionSerializer']
    mappings=read(mapping_path)
    request=dict(mappings={n:mappings[n] for n in names},successor=version=='1.21.5',fixtureRoot=str(directory/'fixtures'),cases=cases)
    (directory/'request.json').write_text(json.dumps(request,indent=2)+'\n')
    with zipfile.ZipFile(client) as z:classes={n:hashlib.sha256(z.read(mappings[n]['name'].replace('.','/')+'.class')).hexdigest() for n in names}
    receipt=dict(schema=1,minecraft=version,scope='Actual PathPackResources/MultiPackResourceManager folder lookup,stack,metadata and listing;no pack repository/UI/ZIP/reload/render.',
        clientSha256=sha(client),mappingSha256=sha(mapping_path),requestSha256=sha(directory/'request.json'),classEntrySha256=classes,
        sourceSha256={n:sha(directory/n) for n in ['ResourceProbe.java','native_resources.py','native_codecs.py','mappings.py']},
        libraries=libraries,tools={n:dict(path=str(JDK/n),sha256=sha(JDK/n)) for n in ['java','javac']},commands=[],fixturesBefore=before)
    def save():(directory/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    save();env=dict(os.environ,HOME=str(directory/'home'),TMPDIR=str(directory/'tmp'));cp=os.pathsep.join(r['path'] for r in libraries)
    compile_args=[str(JDK/'javac'),'-proc:none','-Xlint:all,-classfile','-Werror','-encoding','UTF-8','-cp',cp,'-d',str(directory/'classes'),str(directory/'ResourceProbe.java')]
    result=run_command(compile_args,directory,'compile',env);receipt['commands'].append(result);save()
    assert result['exitCode']==0 and result['ownedGroupAbsent'],directory
    execute_args=[str(JDK/'java'),'-XX:ActiveProcessorCount=2','-Xmx1G','-Djava.awt.headless=true','-Duser.home='+str(directory/'home'),'-Djava.io.tmpdir='+str(directory/'tmp'),'-cp',os.pathsep.join([str(directory/'classes'),str(client),cp]),'study.minecraft.ResourceProbe',str(directory/'request.json'),str(directory/'observed.json')]
    result=run_command(execute_args,directory,'execute',env);receipt['commands'].append(result)
    receipt['fixturesAfter']=image(directory/'fixtures');receipt['fixturesUnchanged']=before==receipt['fixturesAfter']
    if (directory/'observed.json').exists():receipt['observedSha256']=sha(directory/'observed.json')
    assert sha(client)==receipt['clientSha256'] and sha(mapping_path)==receipt['mappingSha256']
    assert all(sha(Path(x['path']))==x['sha256'] for x in libraries)
    save();print(json.dumps(dict(capture=str(directory),exitCode=result['exitCode'],fixturesUnchanged=receipt['fixturesUnchanged'])))
    assert result['exitCode']==0 and result['ownedGroupAbsent'] and receipt['fixturesUnchanged'],directory


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--private',type=Path,required=True);parser.add_argument('--version',choices=['1.21.1','1.21.5'],required=True)
    args=parser.parse_args();collect(args.private.resolve(),args.version)
