#!/usr/bin/env python3
"""Bind selected presentation field and consumer locators to original artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import zipfile
from text_shader_sources import clauses
from polytone_contracts import mask, closing

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
VERSIONS=['1.21.1','1.21.4','1.21.5','1.21.11','26.3']


def layer_types(text):
    clean=mask(text);m=re.search(r'\benum\s+LayerType\b',clean)
    assert m
    start=clean.index('{',m.end());end=closing(clean,start)
    return re.findall(r'\b[A-Z][A-Z_0-9]*\("([a-z_]+)"\)',text[start:end])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--private',type=Path,required=True);p.add_argument('--check',action='store_true');a=p.parse_args()
    profiles=[];targets=json.loads((HERE/'targets.json').read_text())['javaReferences']
    helper_hashes={n:sha(HERE/n)for n in ['presentation_sources.py','text_shader_sources.py','polytone_contracts.py']}
    for version in VERSIONS:
        cap=Path(json.loads((a.private/('latest-presentation-views-'+version+'.json')).read_text())['capture']);r=json.loads((cap/'receipt.json').read_text())
        assert sha(cap/'inputs.json')==r['inputsSha256']
        paths={k:Path(v)for k,v in json.loads((cap/'inputs.json').read_text())['profiles'][version].items()}
        t=next(t for t in targets if t['release']==version);assert t['id']==r['target']and sha(paths['client'])==r['clientSha256']==t['source']['clientSha256']
        assert sha(paths['metadata'])==r['metadataSha256']==t['source']['metadataSha256']and sha(paths['named'])==r['namedJarSha256']
        assert sha(paths['decompiler'])==r['toolSha256']and sha(paths['jdk']/'bin/java')==r['javaSha256']and sha(paths['jdk']/'release')==r['jdkReleaseSha256']
        for n,h in r['producersSha256'].items():assert sha(cap/n)==h
        c=r['command'];assert c['exitCode']==0 and c['ownedGroupAbsent']and not c['timedOut']
        for channel in ['stdout','stderr']:assert sha(cap/('inspect.'+channel))==c[channel+'Sha256']
        sources={};assets=[]
        with zipfile.ZipFile(paths['client'])as z,zipfile.ZipFile(paths['named'])as named:
            for n,h in r['inspectionClassSha256'].items():assert hashlib.sha256(named.read(n)).hexdigest()==h
            for v in r['originalClassMembers'].values():assert hashlib.sha256(z.read(v['member'])).hexdigest()==v['sha256']
            for rel,h in r['viewsSha256'].items():
                view=cap/'source'/rel;assert sha(view)==h;text=view.read_text();name=rel[:-5].replace('/','.')
                original=[v for k,v in r['originalClassMembers'].items()if k==name or k.startswith(name+'$')];assert original
                groups=[k for k,values in r['categories'].items()if any(n==name or n.startswith(name+'$')for n in values)]
                row=dict(viewSha256=h,originalClasses=original,categories=groups,fieldClauses=clauses(text),
                    consumerLocators=[dict(line=i,kind='selected declaration/call discovery locator')for i,line in enumerate(text.splitlines(),1)
                        if any(s in line for s in [' prepare(', ' apply(', ' init(', 'bakeLayer(', 'createRoots(', 'renderLayers(', 'renderArmorPiece(', 'getColorForLayer(',
                            'Math.min(', 'getSpriteScaling(', 'createRenderState(', 'submitModel(', 'getBlockTint(', 'onResourceManagerReload(', 'trimOverrides()', '.paletteId().orElse(null)'])])
                if name.endswith('.EquipmentClientInfo'):row['layerTypeLabels']=layer_types(text)
                sources[rel]=row
            for name in z.namelist():
                if not name.startswith('assets/minecraft/'):
                    continue
                if name.startswith('assets/minecraft/equipment/')and name.endswith('.json'):
                    raw=z.read(name);d=json.loads(raw);asset=dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),kind='equipment JSON structure only',topKeys=sorted(d))
                    asset['layerLengths']={k:len(v)for k,v in d.get('layers',{}).items()}
                    asset['trimOverrideKeys']=[sorted(v)for v in d.get('trim_overrides',[])]
                    assets.append(asset)
                elif name.endswith('.png.mcmeta'):
                    raw=z.read(name);d=json.loads(raw)
                    if 'gui'in d:assets.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),kind='GUI metadata structure only',guiKeys=sorted(d['gui']),scalingKeys=sorted(d['gui'].get('scaling',{}))))
                elif name.startswith('assets/minecraft/textures/colormap/')and name.endswith('.png'):
                    raw=z.read(name);assert raw[:8]==b'\x89PNG\r\n\x1a\n'and raw[12:16]==b'IHDR'
                    w,h=struct.unpack('>II',raw[16:24]);assets.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),kind='PNG IHDR only;not decoded pixels',width=w,height=h))
        gui=next(v for k,v in sources.items()if k.endswith('/GuiSpriteScaling.java'))
        scopes={}
        for f in gui['fieldClauses']:scopes.setdefault(f['scope'],set()).add(f['field'])
        assert scopes['GuiSpriteScaling.Tile']=={'width','height'}
        assert scopes['GuiSpriteScaling.NineSlice']==({'width','height','border'}|({'stretch_inner'}if version!='1.21.1'else set()))
        assert scopes['GuiSpriteScaling.NineSlice.Border']=={'left','top','right','bottom'}
        eq=next((v for k,v in sources.items()if k.endswith('/EquipmentClientInfo.java')),None)
        if eq:
            roots={f['field']for f in eq['fieldClauses']if f['scope']=='EquipmentClientInfo'}
            assert roots==({'layers','trim_overrides'}if version=='26.3'else{'layers'})
        profiles.append(dict(target=r['target'],clientSha256=r['clientSha256'],metadataSha256=r['metadataSha256'],
            inspectionReceiptSha256=sha(cap/'receipt.json'),inputsSha256=r['inputsSha256'],producersSha256=r['producersSha256'],
            toolSha256=r['toolSha256'],javaSha256=r['javaSha256'],jdkReleaseSha256=r['jdkReleaseSha256'],
            originalClasses=len(r['originalClassMembers']),categories={k:len(v)for k,v in r['categories'].items()},sources=sources,assets=assets))
    report=dict(schema=1,status='bounded source/field/consumer linework;not full grammar or actual rendering',helpersSha256=helper_hashes,profiles=profiles,
        limits=['GUI/equipment/entity/biome entry-point slice,not every renderer/entity/registry/custom-provider consumer.',
                'Original/named pairing and private decompilation identities do not establish translation correctness.',
                'Field clauses are type-scoped discovery locators;delegated codec/default/reference/operation semantics need individual review.',
                'Built-in JSON structure and PNG headers are artifact facts,not original decoder/image/GPU/visible-output qualification.',
                'No application/game/GUI/device/provider execution;original code/assets/binaries/views remain private.'])
    output=HERE/'presentation-sources.json'
    if a.check:assert json.loads(output.read_text())==report
    else:output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(profiles=len(profiles),originalClasses=sum(p['originalClasses']for p in profiles),sourceViews=sum(len(p['sources'])for p in profiles),fieldClauses=sum(len(v['fieldClauses'])for p in profiles for v in p['sources'].values()),assets=sum(len(p['assets'])for p in profiles),checked=a.check)))


if __name__=='__main__':main()
