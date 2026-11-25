#!/usr/bin/env python3
"""Owner-run discovery index over pinned private Java inspection views.

Extract registered names and associated source-file field candidates. This is
not a Java parser, schema verifier, runtime capability test, or semantic proof.
No original source text is exported. Missing views fail instead of implying an
unsupported feature. Ordinary CI need not acquire these private inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from mappings import read as read_mappings

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
VANILLA={
    'items.nodes':'net.minecraft.client.renderer.item.ItemModels',
    'items.conditions':'net.minecraft.client.renderer.item.properties.conditional.ConditionalItemModelProperties',
    'items.select':'net.minecraft.client.renderer.item.properties.select.SelectItemModelProperties',
    'items.numeric':'net.minecraft.client.renderer.item.properties.numeric.RangeSelectItemModelProperties',
    'items.tints':'net.minecraft.client.color.item.ItemTintSources',
    'items.special':'net.minecraft.client.renderer.special.SpecialModelRenderers',
    'textures.atlases':'net.minecraft.client.renderer.texture.atlas.SpriteSources',
    'fonts.definitions':'net.minecraft.client.gui.font.providers.GlyphProviderType',
}


class Views:
    def __init__(self,roots,label,sources):
        self.paths={};self.label=label;self.sources=sources
        for root in roots:
            for p in sorted(root.rglob('*.java')):
                package=re.search(r'^package ([\w.]+);',p.read_text(),re.M)
                if package:self.paths.setdefault(package[1]+'.'+p.stem,p)

    def locate(self,name):
        while name not in self.paths and '.' in name:name=name.rsplit('.',1)[0]
        if name not in self.paths:raise ValueError('Missing inspection view: '+self.label+':'+name)
        return self.paths[name]

    def remember(self,p):
        text=p.read_text();package=re.search(r'^package ([\w.]+);',text,re.M)[1]
        canonical=package+'.'+p.stem;key=self.label+':'+canonical
        self.sources[key]=dict(profileSource=self.label,className=canonical,readableViewSha256=sha(p),
            evidence='Private inspected/decompiled source view;not translation equivalence or native conformance.')
        return key

    def target(self,owner,expression):
        text=owner.read_text();expression=re.sub(r'\(.*','',expression).rsplit('.',1)[0]
        first,*tail=expression.split('.')
        imports={x.rsplit('.',1)[-1]:x for x in re.findall(r'^import ([\w.]+);',text,re.M)}
        package=re.search(r'^package ([\w.]+);',text,re.M)[1]
        name=imports.get(first,package+'.'+first)+(''.join('.'+x for x in tail))
        p=self.locate(name);key=self.remember(p)
        # Candidates from the entire associated file may include nested records
        # or helper codecs. Never label this a complete per-registered-type schema.
        candidates=sorted(set(re.findall(r'\.(?:fieldOf|optionalFieldOf|lenientOptionalFieldOf)\("([^"\n]+)"',p.read_text())))
        return dict(targetClass=name,source=key,sourceFileFieldCandidates=candidates,
            semanticReview='pending;whole associated file candidates are not a per-type schema')


def vanilla(views,version):
    result={}
    for category,name in VANILLA.items():
        if version=='1.21.1' and category.startswith('items.'):
            result[category]=dict(status='No corresponding modern registry in this baseline;legacy item predicates are separate.',entries=[])
            continue
        p=views.locate(name);text=p.read_text();source=views.remember(p)
        raw=re.findall(r'ID_MAPPER\.put\(ResourceLocation\.withDefaultNamespace\("([^"]+)"\),\s*([\w.$]+(?:\(\))?)\)',text)
        if category=='textures.atlases' and version=='1.21.1':raw=re.findall(r'= register\("([^"]+)",\s*([\w.$]+)\)',text)
        if category=='fonts.definitions':raw=re.findall(r'\b[A-Z_]+\("([^"]+)",\s*([\w.$]+)\)',text)
        assert raw,(version,category,'No discovered registry entries')
        entries=[dict(id='minecraft:'+key,**views.target(p,target)) for key,target in raw]
        assert len({x['id'] for x in entries})==len(entries)
        result[category]=dict(status='source-extracted registrations;semantics pending',registrationSource=source,entries=entries)
    return result


def modefite(views):
    result={};base='timmychips.modefiteitemdefinitions.property.'
    p=views.locate(base+'type.ItemModelTypes');source=views.remember(p)
    targets=re.findall(r'ID_MAPPER\.put\(([\w.]+)\.TYPE,',p.read_text())
    entries=[]
    for target in targets:
        binding=views.target(p,target+'.CODEC');file=views.locate(binding['targetClass'])
        ids=re.findall(r'\bTYPE = ResourceLocation\.parse\("([^"]+)"\)',file.read_text())
        assert len(ids)==1,(target,ids)
        entries.append(dict(id=ids[0],**binding))
    assert len(entries)==6
    result['items.nodes']=dict(status='source-extracted registrations;semantics pending',registrationSource=source,entries=entries)
    for category,name in [('items.conditions','ConditionPropertyRegistry'),('items.select','SelectPropertyRegistry'),('items.numeric','RangePropertyRegistry')]:
        p=views.locate(base+'registry.'+name);text=p.read_text();source=views.remember(p)
        raw=re.findall(r'register\(ResourceLocation\.parse\("([^"]+)"\), new ([\w.]+)\(\)\)',text)
        raw += [(ns+':'+key,target) for ns,key,target in re.findall(r'register\(ResourceLocation\.fromNamespaceAndPath\("([^"]+)", "([^"]+)"\), new ([\w.]+)\(\)\)',text)]
        assert raw,name
        entries=[dict(id=key,**views.target(p,target+'.HANDLER')) for key,target in raw]
        assert len(entries)==len({x['id'] for x in entries})
        result[category]=dict(status='source-extracted registrations;semantics pending',registrationSource=source,entries=entries)
    return result


def compat(views):
    prefix='design.inherent.skyweavecompat.client.model.';result={}
    p=views.locate(prefix+'NativeResourceValues');text=p.read_text();source=views.remember(p)
    for category,label,extra in [('items.conditions','CONDITIONS','minecraft:component'),('items.select','SELECT','minecraft:component'),('items.numeric','RANGES',None)]:
        values=re.search(r'\b'+label+r' = Set\.of\((.*?)\);',text,re.S)
        assert values,label
        ids=re.findall(r'"([^"]+)"',values[1])+([extra] if extra else [])
        result[category]=dict(status='source-extracted allowlists and explicit extra branch;semantics pending',registrationSource=source,
            entries=[dict(id=key,source=source,semanticReview='pending;unchanged branches delegate to pinned Modefite handlers') for key in ids])
    p=views.locate(prefix+'ResourceDefinitions');source=views.remember(p);text=p.read_text()
    block=text[text.index('switch (type)'):text.index('return switch (type)')]
    rows=re.findall(r'case "([^"]+)" -> Set\.of\(([^;]+)\);',block,re.S)
    assert len(rows)==6
    result['items.nodes']=dict(status='source-extracted accepted fields;types/defaults/constraints/consumers pending',registrationSource=source,
        entries=[dict(id=key,source=source,acceptedFieldNames=re.findall(r'"([^"]+)"',fields),semanticReview='pending') for key,fields in rows])
    p=views.locate(prefix+'ResourceComponents');text=p.read_text();source=views.remember(p)
    body=text[text.index(' tint(String type'):text.index('private static ResourceDefinitions.Selector')]
    ids=re.findall(r'case "([^"]+)" ->',body);assert len(ids)==3
    result['items.tints']=dict(status='source-extracted dispatch cases;semantics pending',registrationSource=source,
        entries=[dict(id=key,source=source,semanticReview='pending') for key in ids])
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--private',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    private=args.private.resolve();sources={}
    pins={s['id']:s for s in json.loads((HERE/'sources.json').read_text())['sources']}
    for version in ['1.21.1','1.21.5']:
        mapping=private/(version+'-client-mappings.txt')
        assert sha(mapping)==pins['mojang:'+version+':client_mappings']['sha256']
    baseline=read_mappings(private/'1.21.1-client-mappings.txt')
    assert all(name not in baseline for category,name in VANILLA.items() if category.startswith('items.'))
    assert sha(private/'inputs/modefite-959272d5a7acc809.jar')==pins['modefite:cy8BkRZc']['sha256']
    assert sha(private/'inputs/compat_delivered-4ae402eaa858eef4.jar')==pins['skyweave-compat:4ae402eaa858eef4']['sha256']
    v={version:Views([private/(version+'-source'),private/(version+'-extension-source')],'mojang:'+version,sources) for version in ['1.21.1','1.21.5']}
    m=Views([private/'modefite-decompiled'],'modefite:959272d5a7acc809',sources)
    c=Views([private/'compat-decompiled'],'compat:4ae402eaa858eef4',sources)
    profiles={
        'minecraft-1.21.1':dict(refines=None,categories=vanilla(v['1.21.1'],'1.21.1')),
        'minecraft-1.21.1+1.21.5':dict(refines='minecraft-1.21.1',categories=vanilla(v['1.21.5'],'1.21.5')),
        'minecraft-1.21.1+modefite':dict(refines='minecraft-1.21.1',categories=modefite(m)),
        'minecraft-1.21.1+modefite+skyweave-compat':dict(refines='minecraft-1.21.1+modefite',categories=compat(c)),
    }
    result=dict(schema=1,status='discovery index,not semantic or capability qualification',producerSha256=sha(Path(__file__)),
        artifactSourceIds=['mojang:1.21.1:client','mojang:1.21.1:client_mappings','mojang:1.21.5:client','mojang:1.21.5:client_mappings','modefite:cy8BkRZc','skyweave-compat:4ae402eaa858eef4'],
        profiles=profiles,sources=sources,limits=[
            'Category omissions are not unsupported capability claims;inheritance and startup gates require explicit semantic resolution.',
            'A registered name does not establish compatible schema,game context,asset availability,rendering or equivalent behavior.',
            'Field candidates cover whole associated source files and may include helper/nested codecs. They are not complete per-type schemas.',
            'No original Java source,game/artwork bytes,mapping payload or mod binary is redistributed.',
        ])
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({p:{k:len(v['entries']) for k,v in data['categories'].items()} for p,data in profiles.items()}))


if __name__=='__main__':main()
