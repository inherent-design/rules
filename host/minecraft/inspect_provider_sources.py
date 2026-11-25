#!/usr/bin/env python3
"""Private selected provider source inspection;original classes are data,not executed."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'java'))
from arena_probe import command
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
PLANS={
    'modefite':dict(id='modefite-cy8BkRZc',file='modefite-959272d5a7acc809.jar',roots=['']),
    'compat':dict(id='compat-4ae402eaa858eef4',file='compat_delivered-4ae402eaa858eef4.jar',roots=[
        'design.inherent.skyweavecompat.'+n for n in ['Feature','FeatureSettings','FeatureSelection','DependencyVersions','OptionalIntegrations','OptionalMixinPlugin',
            'client.model.','mixin.client.definitions.','mixin.client.MultiAxisModelMixin']]),
    'polytone':dict(id='polytone-Ty5Aowoi',file='polytone-7c78b6f425d84a85.jar',roots=[
        'net.mehvahdjukaar.polytone.'+n for n in ['mixins.BlockElementDeserializerMixin','mixins.BlockElementRotationMixin','mixins.FaceBakeryMixin',
            'common.IExtendedBlockElementRotation','content.item.','content.model.']]),
}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--provider',choices=list(PLANS),required=True)
    p.add_argument('--inputs',type=Path,required=True,help='Existing presentation tool manifest;read-only.')
    p.add_argument('--private',type=Path,required=True);a=p.parse_args();private=a.private.resolve();plan=PLANS[a.provider]
    pins=json.loads((HERE/'targets.json').read_text())['providers'];pin=next(t for t in pins if t['id']==plan['id'])
    artifact=private/'inputs'/plan['file'];assert sha(artifact)==pin['sha256']
    paths={k:Path(v)for k,v in json.loads(a.inputs.read_text())['profiles']['26.3'].items()}
    jdk=paths['jdk'];tool=paths['decompiler'];assert sha(tool)=='1dfcfe974395734fa467ce620661c7623d05ba83670de0529b1fbd63ff548b9d'
    assert 'JAVA_VERSION="25.'in(jdk/'release').read_text()
    cap=private/('provider-views-'+a.provider+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));cap.mkdir()
    for n in ['classes','source','home','tmp']:(cap/n).mkdir()
    for src in [Path(__file__),HERE.parent/'java/arena_probe.py']:shutil.copyfile(src,cap/src.name)
    shutil.copyfile(a.inputs,cap/'inputs.json');original={};descriptors={}
    with zipfile.ZipFile(artifact)as archive:
        for member in archive.namelist():
            if member.endswith('.mixins.json'):
                descriptors[member]=dict(sha256=hashlib.sha256(archive.read(member)).hexdigest(),value=json.loads(archive.read(member)))
            if not member.endswith('.class'):continue
            name=member[:-6].replace('/','.')
            if not any(not r or name==r or name.startswith(r if r.endswith('.')else r+'$')for r in plan['roots']):continue
            raw=archive.read(member);original[member]=hashlib.sha256(raw).hexdigest();out=cap/'classes'/member;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
    assert 1<=len(original)<=128
    r=dict(schema=1,provider=pin['id'],artifactSha256=sha(artifact),selectedRoots=plan['roots'],originalClassSha256=original,mixinDescriptors=descriptors,
        toolSha256=sha(tool),javaSha256=sha(jdk/'bin/java'),jdkReleaseSha256=sha(jdk/'release'),inputsSha256=sha(cap/'inputs.json'),
        producersSha256={n:sha(cap/n)for n in ['inspect_provider_sources.py','arena_probe.py']},
        limits=['Original provider archives/class bytes read as private data;no class linking,mod loader/plugin/Mixin application,game or renderer execution.',
            'Decompiler views and selected roots do not prove translation fidelity,complete feature semantics or actual hook application.',
            'All Modefite outer classes selected;Compat/Polytone selected policy/model/item roots only,with existing broader Polytone maps remaining separate.'])
    save=lambda:(cap/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');save()
    argv=[str(jdk/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx384m','-Djava.awt.headless=true','-Duser.home='+str(cap/'home'),'-Djava.io.tmpdir='+str(cap/'tmp'),'-jar',str(tool),
        '--folder','--log-level=WARN','--add-external='+str(artifact),str(cap/'classes'),str(cap/'source')]
    r['command']=command(argv,cap,'inspect',dict(os.environ,TMPDIR=str(cap/'tmp')),120)
    r['viewsSha256']={str(p.relative_to(cap/'source')):sha(p)for p in(cap/'source').rglob('*.java')};save()
    assert r['command']['exitCode']==0 and r['command']['ownedGroupAbsent']and not r['command']['timedOut']
    assert r['viewsSha256']and sha(artifact)==r['artifactSha256']and all(sha(cap/n)==h for n,h in r['producersSha256'].items())
    (private/('latest-provider-views-'+a.provider+'.json')).write_text(json.dumps(dict(capture=str(cap)))+'\n')
    print(json.dumps(dict(capture=str(cap),originalClasses=len(original),views=len(r['viewsSha256']),ownedGroupAbsent=True)))


if __name__=='__main__':main()
