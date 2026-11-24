#!/usr/bin/env python3
"""Verify retained study/browser/native facts;no new browser or CLI execution."""
import hashlib
import json
from pathlib import Path
import zipfile

from portable_study_native import decode

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'applications/evidence/empack-portable-storage-20261124T222835992Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    r=json.loads((RUN/'receipt.json').read_text());native=json.loads((RUN/'native.json').read_text());backend=json.loads((RUN/'backend-inspection.json').read_text())
    assert not r.get('error')and r['serverClosed']and len(r['profiles'])==2
    for p,h in r['sourceSha256'].items():assert sha(RUN/p)==h==sha(ROOT/'applications/empack/portable-study'/p)
    assert sha(RUN/'probe.mjs')==r['producerSha256']
    assert sha(RUN/'native-probe.py')==native['producerSha256']and sha(RUN/'backend-inspection.mjs')==backend['producerSha256']
    assert sha(RUN/'receipt.json')==native['browserReceiptSha256']==backend['browserReceiptSha256']
    assert backend['serverClosed']and backend['contextsClosed']and not backend.get('error')
    assert sha(Path(r['package']['path']))==r['package']['sha256']
    assert sha(Path(r['package']['path']).with_name('browsers.json'))==r['package']['browserManifestSha256']
    assert sha(Path(native['binary']))==native['binarySha256']=='99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
    rows={b['engine']:b for b in backend['rows']};native_rows={b['engine']:b for b in native['profiles']}
    for p in r['profiles']:
        name=p['engine'];assert p['contextClosed']and p['firstContextClosed']and not p['errors']and len(p['events'])==14
        assert p['browserVersion']==rows[name]['browserVersion']and all(p['capabilities'].values())
        assert sha(Path(p['executable']))==p['executableSha256']
        events=p['events'];first=events[1]['record'];second=events[2]['record']
        assert first['revision']=='1'and second['revision']=='2'and first['image']==second['image']
        assert first['draft']['author']['id']!=second['draft']['author']['id']and first['draft']['author']['sha256']==second['draft']['author']['sha256']
        stale=events[3];assert stale['code']=='STALE_REVISION'and stale['current']['revision']=='2'and stale['state']['savedRevision']=='1'
        losses=[e for e in events if e['kind']=='worker-loss'];assert [e['hold']for e in losses]==['asset-created','assets-retained','metadata-committed']
        for e,expected in zip(losses,['2','3','4']):
            assert e['terminationRequested']and e['current']['revision']==expected and e['completion']['code']=='OUTCOME_UNKNOWN'
            assert e['before']['draft']==e['state']['draft']and e['before']['savedRevision']==e['state']['savedRevision']
        assert events[6]['kind']=='retry-after-unpublished-file'and events[6]['record']['revision']=='3'
        assert events[10]['kind']=='reconcile-after-loss'and events[10]['record']['revision']=='4'
        assert events[11]['record']['revision']=='5'and events[12]['record']['revision']=='5'and events[11]['record']['image']==events[12]['record']['image']
        corruption=events[13];assert corruption['openError']==corruption['saveError']=='Retained digest mismatch'
        assert corruption['current']['revision']=='5'and rows[name]['record']==corruption['current']
        assert len(rows[name]['assets'])==12 and len(rows[name]['emptyUnreferenced'])==1 and len(rows[name]['unreferenced'])==8
        assert rows[name]['emptyUnreferenced']==['asset-'+losses[0]['phase']['detail']['asset']]
        assert [x['id']for x in rows[name]['referenced']if not x['valid']]==[corruption['entry']['asset']['id']]
        assert len(p['downloads'])==2
        for d in p['downloads']:
            f=RUN/d['file'];assert sha(f)==d['sha256']and f.stat().st_size==d['bytes']and d['completed']
            bundle,files=decode(f.read_bytes())
            assert hashlib.sha256(files['pack/mods/Sample Ω 日本.jar']).hexdigest()==r['inputSha256']['jar']
            assert hashlib.sha256(files['pack/config/renamed-rules.json']).hexdigest()==r['inputSha256']['config']
            assert len(bundle['record']['draft']['missing'])==(1 if d['label']=='invalid-backup'else 0)
        archive=native_rows[name]['archive'];copies=json.loads((RUN/'retained-archives.json').read_text());copy=next(x for x in copies['files']if x['engine']==name)
        assert copy['original']==archive['path']and copy['sha256']==archive['sha256']and sha(RUN/copy['retained'])==archive['sha256']
        assert sha(RUN/archive['path'])==archive['sha256']
        with zipfile.ZipFile(RUN/copy['retained'])as z:
            found={m.filename:dict(bytes=m.file_size,sha256=hashlib.sha256(z.read(m)).hexdigest(),mode=(m.external_attr>>16)&0o777)for m in z.infolist()if not m.is_dir()}
        assert found==archive['inventory']and len(found)==5
    assert native_rows['chromium']['archive']['inventory']==native_rows['webkit']['archive']['inventory']
    assert len(native['commands'])==6 and [c['exitCode']for c in native['commands']]==[2,0,0,2,0,0]
    for c in native['commands']:
        assert c['ownedGroupAbsent']
        for stream in ['stdout','stderr']:assert sha(RUN/(c['label']+'.'+stream))==c[stream+'Sha256']
    assert len(native['decoderRefusals'])==6
    controls=json.loads((RUN/'decoder-scalar-controls.json').read_text())
    assert sha(RUN/controls['input'])==controls['inputSha256']
    assert sha(RUN/'native-probe.py')==controls['sourceBeforeSha256']
    assert sha(ROOT/'applications/empack/portable_study_native.py')==controls['sourceAfterSha256']
    for row in controls['after']:
        value=json.loads((RUN/controls['input']).read_text());value['record']['schema']=row['value']
        try:decode(json.dumps(value,ensure_ascii=False).encode())
        except (ValueError,TypeError):accepted=False
        else:accepted=True
        assert accepted==row['accepted']
    report=dict(schema=1,status='Executed research prototype observations;formal comparison recorded separately in capture/conformance.json',
        browserProfiles=2,browserEvents=28,completedDownloads=4,browserRelaunches=2,workerLossBoundaries=6,
        nativeCommands=6,equalNativePrismInventory=True,nativeArchiveFiles=5,decoderRefusals=native['decoderRefusals'],
        backendAssetsPerEngine=12,backendUnreferencedPerEngine=8,backendEmptyUnreferencedPerEngine=1,
        findings=['Invalid raw authoring and explicit missing input survive actual browser storage and backup;native sync separately refuses the invalid author file.',
            'Same semantic image can use different opaque backing;storage revision,content observation,source identity and UI caption are distinct.',
            'A stale tab refuses;loss before metadata retains old root,loss after commit can leave new saved metadata without a UI receipt.',
            'Raw independent storage inspection finds an empty private orphan and exactly the explicit referenced corruption;retries succeeded without adopting the empty file.',
            'Completed backups from both browsers restore selected source inventories into the same native exporter and produce identical5filePrism inventories.'],
        limits=['No portable production engine or browser distribution exporter. Study schema is not a full native project backup.',
            'Formal model/replay is a separate source-bound check. No complete parent-scenario or feature-status promotion.',
            'No OS picker/permission,CORS/provider,GC/history/plan-retention,quota,eviction,reboot,power-loss or real game/Prism qualification.',
            'No new browser/native execution by this checker;future generator/source changes require their own attribution.'])
    (ROOT/'applications/empack/portable-storage-observations.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
