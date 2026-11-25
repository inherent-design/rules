#!/usr/bin/env python3
"""Source-discovery extension for selected later references. Never starts a game."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile
from catalog_sources import Views,vanilla

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


class LaterViews(Views):
    def target(self,owner,expression):
        try:return super().target(owner,expression)
        except ValueError as error:
            if not str(error).startswith('Missing inspection view:'):raise
            return dict(targetExpression=expression,source=None,sourceFileFieldCandidates=[],semanticReview='missing associated view;not an unsupported-feature finding',missingView=str(error))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--views',type=Path,required=True);p.add_argument('--client',type=Path,required=True);args=p.parse_args()
    capture=args.views.resolve();receipt=json.loads((capture/'receipt.json').read_text());root=capture/'source'
    assert receipt['target']=='java-26.3-vanilla' and receipt['exitCode']==0 and receipt['ownedGroupAbsent']
    assert sha(args.client)==receipt['clientSha256']=='4508d006323f24fa02876310c192d739af56516eb259000ac50f0909a68c9a2d'
    assert {str(p.relative_to(root)) for p in root.rglob('*.java')}==set(receipt['viewsSha256'])
    for n,d in receipt['viewsSha256'].items():assert sha(root/n)==d
    sources={};views=LaterViews([root],'java-26.3-vanilla',sources)
    categories=vanilla(views,'26.3')
    with zipfile.ZipFile(args.client) as binary:
        for source in sources.values():
            entry=source['className'].replace('.','/')+'.class';raw=binary.read(entry)
            source.update(originalClassMember=entry,originalClassSha256=hashlib.sha256(raw).hexdigest())
    manifest=json.loads((HERE/'targets.json').read_text());target=next(t for t in manifest['javaReferences'] if t['id']=='java-26.3-vanilla');assert target['source']['clientSha256']==receipt['clientSha256']
    missing=[dict(category=c,id=e['id'],expression=e.get('targetExpression'),missing=e['missingView']) for c,v in categories.items() for e in v['entries'] if e.get('source') is None]
    result=dict(schema=1,status='later registry source discovery;not semantic or runtime qualification',target=target['id'],clientSha256=receipt['clientSha256'],privateViewReceiptSha256=sha(capture/'receipt.json'),generatorSha256=sha(Path(__file__)),sharedReaderSha256=sha(HERE/'catalog_sources.py'),categories=categories,sources=sources,missingViews=missing,limits=['Literal registrations only;bootstrap reachability,active consumer behavior,decoding and rendering remain unqualified.','Whole associated-file field candidates can include nested/helper records;not complete per-type schemas.','Missing inspection views are explicit pending work,not evidence a feature is unsupported.','Identifier and ResourceLocation syntax are different qualified API surfaces;recognizing literal registration spelling does not prove semantic equivalence.','Private decompiled views are not matching upstream sources or a proved compiler inverse.','Earlier profile/source/native records remain independent;no pin or runtime guarantee is advanced by this index.'])
    (HERE/'later-registry-catalog.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(target=target['id'],registrations=sum(len(v['entries']) for v in categories.values()),categories={c:len(v['entries']) for c,v in categories.items()},missingViews=len(missing),sourceFiles=len(sources))))


if __name__=='__main__':main()
