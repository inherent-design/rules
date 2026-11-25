#!/usr/bin/env python3
"""Attribute font/language/shader fields, consumer locators and built-in asset structure."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import zipfile
from polytone_contracts import mask, closing

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
EXPECTED = {
    'BitmapProvider.Definition': {'file','height','ascent','chars'},
    'TrueTypeGlyphProviderDefinition': {'file','size','oversample','shift','skip'},
    'SpaceProvider.Definition': {'advances'},
    'UnihexProvider.Definition': {'hex_file','size_overrides'},
    'UnihexProvider.Dimensions': {'left','right'},
    'UnihexProvider.OverrideRange': {'from','to'},
    'ProviderReferenceDefinition': {'id'},
    'GlyphProviderDefinition.Conditional': {'filter'},
    'FontManager.FontDefinitionFile': {'providers'},
    'LanguageInfo': {'region','name','bidirectional'},
}
TYPES = {
    'BitmapProvider.Definition': {'file':'runtime identifier','height':'int','ascent':'int','chars':'list of Java strings converted to a code-point grid'},
    'TrueTypeGlyphProviderDefinition': {'file':'runtime identifier','size':'float','oversample':'float','shift':'two floats in declared range[-512,512]','skip':'string or list of strings concatenated'},
    'SpaceProvider.Definition': {'advances':'map<runtime code-point codec,float>'},
    'UnihexProvider.Definition': {'hex_file':'runtime identifier','size_overrides':'list<OverrideRange>'},
    'UnihexProvider.Dimensions': {'left':'int','right':'int'},
    'UnihexProvider.OverrideRange': {'from':'runtime code-point codec','to':'runtime code-point codec'},
    'ProviderReferenceDefinition': {'id':'font identifier reference'},
    'GlyphProviderDefinition.Conditional': {'filter':'map<FontOption,bool>,flattened beside provider dispatch'},
    'FontManager.FontDefinitionFile': {'providers':'list<conditional provider definitions>'},
    'LanguageInfo': {'region':'nonempty string codec','name':'nonempty string codec','bidirectional':'bool'},
}
DEFAULTS = {'BitmapProvider.Definition':{'height':8},'TrueTypeGlyphProviderDefinition':{'size':11.0,'oversample':1.0,'shift':[0,0],'skip':''},
            'GlyphProviderDefinition.Conditional':{'filter':{}},'LanguageInfo':{'bidirectional':False}}
RULES = {
    'BitmapProvider.Definition':['Grid must be nonempty,have a nonempty first row,and have equal Java code-point counts per row. Ascent may not exceed height.',
        'No new independent positivity or pixel/native-load guarantee is supplied by the declared INT fields. Image resource is resolved under textures/.'],
    'TrueTypeGlyphProviderDefinition':['Shift has fixed length2 and declared float range[-512,512]. File is loaded under font/.',
        'Definition decoding is separate from FreeType library/face creation,native memory,and successful rasterization.'],
    'SpaceProvider.Definition':['Selected loader creates advance-only glyphs from the map;no image/font file is required by that loader.',
        'No positivity rule is declared here. Later glyph selection/fishy-width behavior and floating-point edges remain separate.'],
    'UnihexProvider.Definition':['The loader opens hex_file directly as a resource and scans ZIP entries ending.hex. This differs from automatic font/ prefixing.',
        'Archive parsing,hex line grammar,allocation,overrides and glyph/native resource lifetime remain independent obligations.'],
    'UnihexProvider.Dimensions':['INT declarations are separate from later packed-dimension interpretation and glyph width.'],
    'UnihexProvider.OverrideRange':['The declared validation requires from<to. Dimensions fields are flattened through Dimensions.MAP_CODEC.',
        'Iteration endpoint behavior and delegated code-point grammar are not inferred from field names.'],
    'ProviderReferenceDefinition':['Reference resolves another font provider list through the manager dependency resolver,not a file loader.',
        'Missing/failed references,dependency cycles and final fallback/publication require their own consumer contract.'],
    'GlyphProviderDefinition.Conditional':['Type dispatch and option filter are separate. The selected two-option merge uses receiver precedence,not conjunction.',
        'Filters select active providers after preparation/loading;the filter predicate alone is not a no-I/O or no-allocation promise.'],
    'FontManager.FontDefinitionFile':['Provider declarations are read from resource stacks with ordering/reversal at the loader and publication boundaries.',
        'Per-resource parse failure logs/continues in the inspected loader;whole-font resolution and later apply may still fail.'],
    'LanguageInfo':['Language metadata map keys use the runtime bounded string codec1..16. Display values are literal components in this selected record.',
        'Metadata availability,selected language code,translation stack,injected language and rendered glyphs are distinct states.'],
}


def clauses(text):
    clean = mask(text); types = []
    for m in re.finditer(r'\b(?:class|record|interface|enum)\s+([A-Za-z_$][\w$]*)',clean):
        start = clean.find('{',m.end())
        if start >= 0: types.append((start,closing(clean,start),m[1]))
    fields = []
    for m in re.finditer(r'\b(optionalFieldOf|fieldOf)\s*\(\s*"([^"\n]+)"',text):
        if clean[m.start():m.start()+len(m[1])] != m[1]: continue
        scope = '.'.join(t[2] for t in sorted(types) if t[0] < m.start() < t[1])
        item=dict(scope=scope,field=m[2],optional=m[1]=='optionalFieldOf',line=text[:m.start()].count('\n')+1)
        ref=re.search(r'([A-Za-z_$][\w$.]*)\s*\.\s*$',text[max(0,m.start()-180):m.start()])
        if ref:item['codecReference']=ref[1]
        if item['optional']:
            literal=re.match(r'\s*,\s*(true|false|[-+]?\d+(?:\.\d+)?[fFdD]?|"(?:\\.|[^"\\])*")\s*\)',text[m.end():])
            if literal:
                token=literal[1]
                item['defaultLiteral']=json.loads(token[:-1]if token[-1:]in 'fFdD'else token)
            else:
                ref=re.match(r'\s*,\s*([A-Za-z_$][\w$.]*(?:\(\))?)\s*\)',text[m.end():])
                if ref:item['defaultReference']=ref[1]
        fields.append(item)
    return fields


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--private',type=Path,required=True); p.add_argument('--check',action='store_true'); a = p.parse_args(); private=a.private.resolve()
    targets=json.loads((HERE/'targets.json').read_text())['javaReferences']; profiles=[]
    for version in ['1.21.1','1.21.4','1.21.5','1.21.11','26.3']:
        target=next(t for t in targets if t['release']==version)
        native=Path(json.loads((private/('latest-font-filter-'+version+'.json')).read_text())['capture']); nr=json.loads((native/'receipt.json').read_text()); argv=nr['commands'][1]['argv']; client=Path(argv[argv.index('-cp')+1].split(':')[1])
        assert sha(client)==target['source']['clientSha256']==nr['clientSha256'] and nr['observerErrors']==0
        captures=[Path(json.loads((private/('latest-font-shader-views-'+version+'.json')).read_text())['capture'])]
        dep=private/('latest-font-shader-dependencies-'+version+'.json')
        if version in ['1.21.4','1.21.11','26.3']:assert dep.exists(),version
        if dep.exists():captures.append(Path(json.loads(dep.read_text())['capture']))
        if version=='26.3':
            life=private/('latest-font-shader-lifetimes-'+version+'.json');assert life.exists()
            captures.append(Path(json.loads(life.read_text())['capture']))
        textViews=private/('latest-text-description-views-'+version+'.json');assert textViews.exists()
        captures.append(Path(json.loads(textViews.read_text())['capture']))
        sources={}; receipts=[]; scopes={}; originalCount=0
        with zipfile.ZipFile(client) as archive:
            for cap in captures:
                r=json.loads((cap/'receipt.json').read_text());assert r['clientSha256']==sha(client)
                assert r['command']['exitCode']==0 and r['command']['ownedGroupAbsent'] and not r['command']['timedOut']
                for f,h in r['producersSha256'].items():assert sha(cap/f)==h
                named=Path(next(v.split('=',1)[1]for v in r['command']['argv']if v.startswith('--add-external=')))
                assert sha(named)==r['namedJarSha256']
                with zipfile.ZipFile(named)as namedArchive:
                    for member,h in r['inspectionClassSha256'].items():assert hashlib.sha256(namedArchive.read(member)).hexdigest()==h
                for item in r['originalClassMembers'].values():assert hashlib.sha256(archive.read(item['member'])).hexdigest()==item['sha256']
                receipts.append(dict(receiptSha256=sha(cap/'receipt.json'),producerSha256=r['producersSha256']['inspect_font_shader_sources.py'],originalClasses=len(r['originalClassMembers']),views=len(r['viewsSha256'])))
                originalCount+=len(r['originalClassMembers'])
                for rel,h in r['viewsSha256'].items():
                    path=cap/'source'/rel;assert sha(path)==h;name=rel[:-5].replace('/','.')
                    original={v['member']:v['sha256']for k,v in r['originalClassMembers'].items()if k==name or k.startswith(name+'$')};assert original,name
                    text=path.read_text();fields=clauses(text)
                    for field in fields:scopes.setdefault(field['scope'],set()).add(field['field'])
                    row=dict(viewSha256=h,originalClassesSha256=original,fields=fields,
                        consumerLocators=[dict(line=i,kind='source declaration/call candidate')for i,line in enumerate(text.splitlines(),1)
                            if any(s in line for s in ['void close(', 'void apply(', 'reload(', 'resolve(', 'loadFrom(', 'getGlyph(', 'compilePipeline(', 'finishCompile', 'loadResourceStack(', 'thenCompose(', 'preparationBarrier', 'putAll(this.values)', 'fieldOf("filter"'])])
                    if rel in sources:assert sources[rel]==row
                    sources[rel]=row
            for scope,expected in EXPECTED.items():assert scopes.get(scope)==expected,(version,scope,scopes.get(scope),expected)
            assets=[];groups=Counter()
            for member in archive.namelist():
                if member.endswith('/') or not member.startswith('assets/minecraft/'):continue
                rel=member[len('assets/minecraft/'):]
                if not rel.startswith(('font/','lang/','shaders/','post_effect/')):continue
                extension=Path(member).suffix;group=rel.split('/')[0];groups[group+':'+extension]+=1
                if extension!='.json' or group=='lang':continue
                data=archive.read(member);value=json.loads(data);assert type(value)is dict
                item=dict(path=member,sha256=hashlib.sha256(data).hexdigest(),rootFields=sorted(value))
                if group=='font':
                    item['providerTypes']=dict(Counter(p.get('type','<absent>')for p in value.get('providers',[])if type(p)is dict))
                    item['providerFieldSets']=[sorted(p)for p in value.get('providers',[])if type(p)is dict]
                assets.append(item)
        contracts={}
        for scope in EXPECTED:
            evidence=[dict(path=path,viewSha256=s['viewSha256'],field=field['field'],line=field['line'])for path,s in sources.items()for field in s['fields']if field['scope']==scope]
            fields={}
            for f in sorted(EXPECTED[scope]):
                matching=[field for s in sources.values()for field in s['fields']if field['scope']==scope and field['field']==f]
                assert len(matching)==1
                fields[f]=dict(type=TYPES[scope][f],presence='optional'if matching[0]['optional']else'required')
                if f in DEFAULTS.get(scope,{}):
                    assert matching[0]['optional']
                    if f not in ['shift','filter']:assert matching[0].get('defaultLiteral')==DEFAULTS[scope][f],(version,scope,f,matching[0])
                    elif f=='shift':
                        assert matching[0].get('defaultReference','').endswith('Shift.NONE')
                        text=(captures[0]/'source/net/minecraft/client/gui/font/providers/TrueTypeGlyphProviderDefinition.java').read_text()
                        assert re.search(r'NONE\s*=\s*new\s+[\w$.]*Shift\(0\.0F,\s*0\.0F\)',text)
                        assert 'Codec.floatRange(-512.0F,512.0F)'in re.sub(r'\s+','',text)
                    else:
                        assert matching[0].get('defaultReference','').endswith('FontOption.Filter.ALWAYS_PASS')
                        option=(captures[0]/'source/net/minecraft/client/gui/font/FontOption.java').read_text()
                        assert re.search(r'ALWAYS_PASS\s*=\s*new\s+(?:FontOption\.)?Filter\s*\(\s*Map\.of\(\)\s*\)',option)
                    fields[f]['default']=DEFAULTS[scope][f]
            contracts[scope]=dict(status='reviewed selected source semantics;delegated grammar/runtime unqualified',fields=fields,rules=RULES[scope],evidence=evidence)
        style='net/minecraft/network/chat/Style.java';assert style in sources
        fontField=[f for f in sources[style]['fields']if f['field']=='font'];assert len(fontField)==1
        description='net/minecraft/network/chat/FontDescription.java';rich=version in ['1.21.11','26.3']
        assert (description in sources)==rich
        if rich:
            actualText=(captures[-1]/'source'/description).read_text()
            assert 'flatComapMap' in actualText and 'Unsupported font description type' in actualText and 'FontDescription.Resource' in actualText
        main=captures[0]/'source'
        providerText=(main/'net/minecraft/client/gui/font/providers/GlyphProviderType.java').read_text()
        providerNames=re.findall(r'\b[A-Z_]+\s*\(\s*"([^"\n]+)"',providerText)
        assert set(providerNames)=={'bitmap','ttf','space','unihex','reference'} and len(providerNames)==5
        optionText=(main/'net/minecraft/client/gui/font/FontOption.java').read_text()
        optionNames=dict(re.findall(r'\b(UNIFORM|JAPANESE_VARIANTS)\s*\(\s*"([^"\n]+)"',optionText))
        assert optionNames=={'UNIFORM':'uniform','JAPANESE_VARIANTS':'jp'}
        selector=dict(status='selected source interpretation;no native description codec or glyph rendering comparison',
            styleFontField=fontField[0],styleSourceSha256=sources[style]['viewSha256'],
            wire='runtime identifier codec for resource font;later FontDescription codec also accepts/encodes only Resource',
            runtimeVariants=['resource','atlas sprite','player sprite']if rich else['resource identifier on this selected FontManager/Style path'],
            warning='Internal rich variants do not establish user-authored JSON support. Other older UI/render paths are not declared absent.',
            descriptionSourceSha256=sources[description]['viewSha256']if rich else None)
        profile=dict(target=target['id'],clientSha256=sha(client),inspectionReceipts=receipts,originalClassPairings=originalCount,
            sources=sources,reviewedFontLanguageContracts=contracts,assetStructure=assets,assetCounts=dict(sorted(groups.items())))
        profile['textFontSelector']=selector
        profile['registeredFontProviderNames']=providerNames
        profile['fontOptionNames']=optionNames
        if version=='26.3':
            base=HERE/'evidence/host-api-26.3-20261125T044400945429Z';fr=json.loads((base/'receipt.json').read_text());fp=base/'invoke-facts.jsonl.gz'
            assert fr['clientSha256']==sha(client) and fr['compressedFactsSha256']==sha(fp)
            wanted={'com/mojang/renderpearl/api/pipeline/ShaderSource$CachedIncludeSource','com/mojang/renderpearl/frontend/shaders/GlslCompiler',
                    'com/mojang/blaze3d/pipeline/PipelineCache','net/minecraft/client/renderer/ShaderManager'}
            identities={k:v for s in sources.values()for k,v in s['originalClassesSha256'].items()};calls=[];classes={}
            with gzip.open(fp,'rt')as f:
                for line in f:
                    fact=json.loads(line)
                    if fact['kind']=='class' and fact['name']in wanted:
                        assert identities[fact['entry']]==fact['sha256'];classes[fact['name']]=fact['sha256']
                    if fact['kind']=='invoke' and fact['caller']in wanted:calls.append(fact)
            assert set(classes)==wanted
            assert any(r['name']=='memUTF8'and r['method']=='create'for r in calls)
            assert any(r['name']=='nmemFree'and r['method']=='close'for r in calls)
            assert any(r['name']=='getInclude'and r['method']=='processInclude'for r in calls)
            profile['nativeInvokeEvidence']=dict(facts='host/minecraft/evidence/host-api-26.3-20261125T044400945429Z/invoke-facts.jsonl.gz',
                factsSha256=sha(fp),classes=classes,calls=calls,limits='Selected direct invoke facts,not executed native calls or complete control/effect/lifetime closure.')
        profiles.append(profile)
    result=dict(schema=1,status='selected source field/consumer linework and built-in asset structure;not complete grammar or runtime qualification',profiles=profiles,
        reviewedRules=[
            'Bitmap file/height/ascent/chars,TTF file/size/oversample/shift/skip,space advances,unihex archive/overrides and reference id have separately scoped definitions.',
            'Conditional filter is optional and the original two-option merge uses receiver precedence;the separate native/model band qualifies that finite predicate only.',
            'Font provider loading,prewarming,active filtering,glyph lookup,baking,texture ownership and final provider close are separate operations.',
            'Language metadata discovery,resource stack presence,translation parsing,global injection,bidi/layout and rendered glyphs are different evidence states.',
            'Shader JSON declarations,stage/include text,pipeline descriptors,compilation,finish,cache publication and native completion are separately versioned.'],
        limits=['Type-scoped field clauses are syntactic locators with reviewed selected semantics,not complete delegated codec grammars or all consumer/effect closure.',
                'Built-in asset fields/counts are Python structural inspection,not original decoder acceptance,pack overlay or rendered observation.',
                'Private decompiled/named views are attributed but not verified translations. No original source text,assets,binaries or mappings are exported.',
                'Font glyph/rasterizer,language UI,shader/device/provider/coexistence and cross-platform execution remain unqualified by this source band.',
                'Selected native filter observations are separate from all font-schema,language,shader and rendering claims.'])
    dest=HERE/'text-shader-sources.json'
    if a.check:assert json.loads(dest.read_text())==result
    else:dest.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(targets=5,sourceViews=sum(len(p['sources'])for p in profiles),fieldClauses=sum(len(s['fields'])for p in profiles for s in p['sources'].values()),fontLanguageScopes=5*len(EXPECTED),assetJsonStructures=sum(len(p['assetStructure'])for p in profiles),checked=a.check)))


if __name__=='__main__':main()
