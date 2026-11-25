#!/usr/bin/env python3
"""Attribute selected server-pack inspection views; original classes remain private."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from mappings import read

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
VIEWS={
 '1.21.1':'1.21.1-source',
 '1.21.4':'java1214-views-20261125T092129786486Z/source',
 '1.21.5':'1.21.5-source',
 '1.21.11':'java12111-views-20261125T074851157569Z/source',
 '26.3':'java263-server-packs-20261125T115411478002Z/source'}
ANCHORS={
 'ServerPackManager':['pushPack(','pushLocalPack(','allowServerPacks(','rejectServerPacks(','resetPromptStatus(','tick(','cleanupRemovedPacks(','onDownload(','updateDownloads(','triggerReloadIfNeeded('],
 'DownloadedPackSource':['createDownloadHeaders(','download(','runAllUpdates(','loadRequestedPacks(','startReload(','onRecovery(','onRecoveryFailure(','onReloadSuccess(','tryParseSha1Hash(','createPackResponseSender(','configureForServerControl(','cleanupAfterDisconnect(','close('],
 'PackDownloader':['download('], 'PackLoadFeedback':['reportUpdate(','reportFinalResult('],
 'PackReloadConfig':['scheduleReload(','onSuccess(','onFailure(','packsToLoad(']}


def build(private):
    targets=json.loads((HERE/'targets.json').read_text())['javaReferences'];rows=[]
    for version,sub in VIEWS.items():
        cap=Path(json.loads((private/('latest-server-packs-'+version+'.json')).read_text())['capture'])
        receipt=json.loads((cap/'receipt.json').read_text());target=next(t for t in targets if t['release']==version)
        # The exact original client is the middle classpath element, not an inspected/remapped JAR.
        argv=receipt['commands'][1]['argv'];cp=argv[argv.index('-cp')+1].split(':');client=Path(cp[1])
        assert sha(client)==target['source']['clientSha256']==receipt['clientSha256']
        mapping=None
        if version!='26.3':
            mp=private/(version+'-client-mappings.txt') if version in ['1.21.1','1.21.5'] else next((private/'inputs').glob('java-'+version+'-client_mappings-*.txt'))
            assert sha(mp)==receipt['mappingSha256'];mapping=read(mp)
        sources={}
        with zipfile.ZipFile(client) as archive:
            for name,anchors in ANCHORS.items():
                original='net.minecraft.client.resources.server.'+name
                binary=original if mapping is None else mapping[original]['name']
                file=Path('net/minecraft/client/resources/server')/(name+'.java');path=private/sub/file
                lines=path.read_text().splitlines();locators={}
                for anchor in anchors:
                    # Locate declarations, not earlier call sites. This is an inspection locator.
                    found=[i+1 for i,line in enumerate(lines) if anchor in line and ('public ' in line or 'private ' in line or ('void '+anchor) in line or ('List<PackReloadConfig.IdAndPath> '+anchor) in line)]
                    assert found,(version,name,anchor)
                    locators[anchor]=found
                member=binary.replace('.','/')+'.class'
                sources[str(file)]=dict(viewSha256=sha(path),originalMember=member,originalClassSha256=hashlib.sha256(archive.read(member)).hexdigest(),methodDeclarationLines=locators)
        rows.append(dict(target=target['id'],clientSha256=sha(client),mappingSha256=receipt['mappingSha256'],sources=sources))
    return dict(schema=1,status='selected source contracts;not full client/transport/render qualification',targets=rows,
        reviewedContracts=['Per-pack prompt acceptance is distinct from mutable global prompt policy.',
            'Download result and resource activation have separate states,callbacks and feedback.',
            'First removal reason wins;inactive manager cleanup is distinct from held download callbacks and backing files.',
            'Reload failure and recovery-failure have distinct state/update effects.',
            'Wrapper validates optional40hex SHA1 syntax,constructs identity/version headers and a262144000byte request limit.',
            'Wrapper schedules downloader completion onto its main executor;serial fixture does not implement that executor.',
            'Wrapper maps local feedback to outbound packet actions;delivery/peer receipt is independently unqualified.',
            'Disconnect pops records,resets prompt and substitutes logging feedback;close delegates download-queue close.'],
        limits=['Private decompiled/remapped views are inspection evidence,not original upstream source or a verified translation.',
            'Method line locators/hash identities attribute review;presence does not prove cross-version semantic equivalence.',
            'No protocol prompt UI,actual HTTP/cache/integrity,exceptional callback,full reload or renderer execution.',
            'No modded-provider,concurrent/reentrant,resource file deletion or download cancellation claim.'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--private',type=Path,required=True);p.add_argument('--check',action='store_true');a=p.parse_args()
    report=build(a.private.resolve());dest=HERE/'server-pack-sources.json'
    if a.check:assert json.loads(dest.read_text())==report
    else:dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(targets=len(report['targets']),sourceViews=sum(len(r['sources']) for r in report['targets']),checked=a.check)))


if __name__=='__main__':main()
