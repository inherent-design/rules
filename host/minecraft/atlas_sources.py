#!/usr/bin/env python3
"""Attribute five-version atlas definitions/consumers; no game bytes are exported."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile
from mappings import read

HERE=Path(__file__).resolve().parent
VIEWS={'1.21.1':'1.21.1-source','1.21.4':'java1214-views-20261125T092129786486Z/source','1.21.5':'1.21.5-source',
       '1.21.11':'java12111-views-20261125T074851157569Z/source','26.3':'java263-views-20261125T053304419681Z/source'}
FAMILIES=['SingleFile','DirectoryLister','SourceFilter','Unstitcher','PalettedPermutations','LazyLoadedImage']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--private',type=Path,required=True);p.add_argument('--check',action='store_true');a=p.parse_args();private=a.private.resolve();rows=[]
    targets=json.loads((HERE/'targets.json').read_text())['javaReferences']
    for v,view in VIEWS.items():
        cap=Path(json.loads((private/('latest-atlas-'+v+'.json')).read_text())['capture']);receipt=json.loads((cap/'receipt.json').read_text())
        assert receipt['observerErrors']==0
        argv=receipt['commands'][1]['argv'];client=Path(argv[argv.index('-cp')+1].split(':')[1]);target=next(t for t in targets if t['release']==v)
        assert sha(client)==receipt['clientSha256']==target['source']['clientSha256']
        mappings=None
        if v!='26.3':
            mp=private/(v+'-client-mappings.txt')if v in ['1.21.1','1.21.5']else next((private/'inputs').glob('java-'+v+'-client_mappings-*.txt'))
            assert sha(mp)==receipt['mappingSha256'];mappings=read(mp)
        sources={}
        with zipfile.ZipFile(client) as archive:
            for part in ['SpriteSource','SpriteSourceList','SpriteSources']+['sources/'+n for n in FAMILIES]:
                rel='net/minecraft/client/renderer/texture/atlas/'+part+'.java';path=private/view/rel;original=rel[:-5].replace('/','.')
                binary=mappings[original]['name'] if mappings else original;member=binary.replace('.','/')+'.class';text=path.read_text()
                entries={n:hashlib.sha256(archive.read(n)).hexdigest()for n in archive.namelist()if n==member or(n.startswith(member[:-6]+'$')and n.endswith('.class'))}
                sources[rel]=dict(viewSha256=sha(path),originalClassesSha256=entries,
                    declaredFieldCandidates=[dict(field=m[2],optional=m[1]=='optionalFieldOf',line=text[:m.start()].count('\n')+1)
                        for m in re.finditer(r'\b(optionalFieldOf|fieldOf)\("([^"\n]+)"',text)],
                    consumerLocators=[dict(line=i,textKind='declaration/call candidate')for i,l in enumerate(text.splitlines(),1)
                        if any(s in l for s in ['void run(',' list(',' load(','void discard(','void release(','SpriteContents get(','SpriteContents apply(','NativeImage get('])])
        rows.append(dict(target=target['id'],clientSha256=sha(client),mappingSha256=receipt['mappingSha256'],sources=sources,
            supplierInterface='DiscardableLoader/Loader.get'if v in ['1.21.11','26.3']else'SpriteSupplier/Function.apply',
            paletteSeparatorFieldPresent=any(r['field']=='separator'for r in sources['net/minecraft/client/renderer/texture/atlas/sources/PalettedPermutations.java']['declaredFieldCandidates'])))
    report=dict(schema=1,status='45 attributed source views and bounded output-control comparisons;not full atlas/provider qualification',targets=rows,
        contracts=['Source-list load concatenates successfully parsed stack definitions;per-entry parse exceptions log and skip that entry.',
            'List executes sources in order;add installs the new supplier before discarding the prior one;remove discards before deleting its map entry.',
            'Returned results prepend a missing-texture loader;remaining supplier order comes from HashMap,not declared source order.',
            'Single/directory sources select resources and register deferred loading;filter affects currently accumulated entries,not future additions.',
            'Unstitch regions share a lazy source image and release on evaluation finally or discard;pixel decode/crop/fallback remain independent.',
            'Paletted permutations defer palette/image work and share counted base images;later selected versions add an optional separator field.',
            'LazyLoadedImage release decrements a count and closes an already cached image at count<=0;this does not prove all caller/cross-thread ownership obligations.'],
        limits=['Field candidates include nested structures;they are source locators,not a complete schema,parser proof or admission policy.',
            'Original class identities plus private transformed/decompiled views attribute inspection,not verified translation.',
            'Native comparisons execute list/output coordination with authored sources/loaders only;no real source run,codec,image,GPU,render or provider reachability.',
            'No stable survivor/discard order or universal cleanup/exception/concurrency guarantee is inferred.'])
    dest=HERE/'atlas-sources.json'
    if a.check:assert json.loads(dest.read_text())==report
    else:dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(targets=5,sourceViews=sum(len(r['sources'])for r in rows),checked=a.check)))


if __name__=='__main__':main()
