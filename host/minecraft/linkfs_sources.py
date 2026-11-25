#!/usr/bin/env python3
"""Verify retained private source inputs and export identities/locators,not original code."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
CAPTURES=[
    'linkfs-views-1.21.1-20261125T163339271195Z',
    'linkfs-views-1.21.4-20261125T163340369446Z',
    'linkfs-views-1.21.5-20261125T163341499645Z',
    'linkfs-views-1.21.11-20261125T163342656896Z',
    'linkfs-views-26.3-20261125T163343314696Z',
]
METHODS=['isSameFile(', 'checkAccess(', 'newByteChannel(', 'newDirectoryStream(',
    'readAttributes(', 'getBasicAttributes(', 'boolean equals(', 'boolean exists(',
    'toRealPath(', 'normalize(', 'toFile(', 'void close(', 'boolean isOpen(',
    'boolean isReadOnly(', 'long size(', 'Object fileKey(', 'createIndexFs(',
    'createVanillaPackSource(', 'createZipPack(', 'createDirectoryPack(', 'Builder put(', 'FileSystem build(']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--private',type=Path,default=ROOT/'.build/minecraft')
    p.add_argument('--check',action='store_true');a=p.parse_args()
    targets=json.loads((HERE/'targets.json').read_text())['javaReferences'];profiles=[]
    for name in CAPTURES:
        cap=a.private/name;r=json.loads((cap/'receipt.json').read_text())
        target=next(t for t in targets if t['id']==r['target'])
        assert r['clientSha256']==target['source']['clientSha256']and r['metadataSha256']==target['source']['metadataSha256']
        inputs=cap/'inputs.json';assert sha(inputs)==r['inputsSha256']
        paths={k:Path(v)for k,v in json.loads(inputs.read_text())['profiles'][r['selectedRelease']].items()}
        for n,key in [('client','clientSha256'),('metadata','metadataSha256'),('named','namedJarSha256'),('decompiler','toolSha256')]:assert sha(paths[n])==r[key]
        assert sha(paths['jdk']/'bin/java')==r['javaSha256']and sha(paths['jdk']/'release')==r['jdkReleaseSha256']
        if r['mappingSha256']is not None:
            assert sha(paths['mappings'])==r['mappingSha256']
            assert hashlib.sha1(paths['mappings'].read_bytes()).hexdigest()==json.loads(paths['metadata'].read_text())['downloads']['client_mappings']['sha1']
        for n,h in r['producersSha256'].items():assert sha(cap/n)==h
        with zipfile.ZipFile(paths['client'])as client,zipfile.ZipFile(paths['named'])as named:
            for record in r['originalClassMembers'].values():assert hashlib.sha256(client.read(record['member'])).hexdigest()==record['sha256']
            for member,h in r['inspectionClassSha256'].items():
                assert sha(cap/'classes'/member)==h and hashlib.sha256(named.read(member)).hexdigest()==h
        c=r['command'];assert c['exitCode']==0 and c['ownedGroupAbsent']and not c['timedOut']
        for channel in ['stdout','stderr']:assert sha(cap/('inspect.'+channel))==c[channel+'Sha256']
        views={}
        for n,h in sorted(r['viewsSha256'].items()):
            source=cap/'source'/n;assert sha(source)==h
            root=n[:-5].replace('/','.')
            views[n]=dict(viewSha256=h,
                originalClasses={k:v for k,v in r['originalClassMembers'].items()if k==root or k.startswith(root+'$')},
                locators=[dict(line=i,kind='selected method/call locator;not an executed consumer')for i,line in enumerate(source.read_text().splitlines(),1)if any(m in line for m in METHODS)])
        assert len(views)==9 and len(r['originalClassMembers'])==21
        profiles.append({k:r[k]for k in ['target','selectedRelease','clientSha256','metadataSha256','mappingSha256','namedJarSha256','inputsSha256','toolSha256','javaSha256','jdkReleaseSha256','producersSha256']}|
            dict(privateCapture=name,privateReceiptSha256=sha(cap/'receipt.json'),categories=r['categories'],sources=views))
    out=dict(schema=1,status='attributable source inspection;selected original API collection is separate',
        helperSha256=sha(Path(__file__)),profiles=profiles,
        limits=['105 original/named class pairings and45decompiler views;not formally verified translations.',
                'Original code,client archives,inspection JDK and decompiler outputs stay private.',
                'Actual resource consumers are source locators;index parsing,pack loading,provider coexistence and rendering were not executed.'])
    dest=HERE/'linkfs-sources.json'
    if a.check:assert json.loads(dest.read_text())==out
    else:dest.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(profiles=len(profiles),originalClassPairings=105,sourceViews=45,checked=a.check)))


if __name__=='__main__':main()
