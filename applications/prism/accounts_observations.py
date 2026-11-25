#!/usr/bin/env python3
"""Read synthetic account method-chain evidence; no Qt/app/auth execution."""
import hashlib,json,uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'applications/evidence/prism-accounts-20261125T020020403602Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda b:hashlib.sha256(b).hexdigest()


def original_method(text,signature,expected):
    # Independent of the producer's brace/comment parser: find the exact hashed
    # substring from its unique signature to a candidate closing brace.
    assert text.count(signature)==1;start=text.index(signature)
    for end in range(start,min(start+24000,len(text))):
        if text[end]=='}'and digest(text[start:end+1].encode())==expected:return text[start:end+1]
    raise AssertionError('Selected method no longer matches its captured digest: '+signature)


def offline_uuid(name):
    # Name UUID algorithm is identity derivation, not authentication/security.
    return uuid.UUID(bytes=hashlib.md5(('OfflinePlayer:'+name).encode()).digest(),version=3).hex


def inspect():
    receipt=json.loads((RUN/'receipt.json').read_text());inputs=json.loads((RUN/'input.json').read_text())['cases']
    outputs=[json.loads(s)for s in(RUN/'observe.stdout').read_text().splitlines()];by={r['id']:r for r in outputs}
    assert len(inputs)==len(outputs)==receipt['cases']==30 and len(by)==30
    assert [i['id']for i in inputs]==[r['id']for r in outputs]
    assert sha(RUN/'probe.py')==receipt['producerSha256']and receipt['allOwnedGroupsAbsent']
    assert all(p['retired']for p in json.loads((RUN/'owned-processes.json').read_text()))
    commands=json.loads((RUN/'commands.json').read_text());assert [c['case']for c in commands]==['compile','observe']
    for c in commands:
        assert c['exitCode']==0 and not c['timedOut']and c['ownedGroupAbsent']
        for stream,h in c['streams'].items():assert sha(RUN/(c['case']+'.'+stream))==h
    work=RUN/'work';assert sha(work/'main.cpp')==receipt['generatedSourceSha256']and sha(work/'probe')==receipt['binarySha256']
    generated=(work/'main.cpp').read_text()
    ledger=json.loads((ROOT/'applications/sources/prism-accounts-selections.json').read_text());source={s['path']:s for s in ledger['sources']}
    tree={r['path']:r for r in json.loads((ROOT/'applications/tools/source-cache/prism-accounts/tree.json').read_text())['tree']}
    for path,s in source.items():
        p=ROOT/s['cache'];data=p.read_bytes();assert digest(data)==s['sha256']
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest();assert blob==s['gitBlobSha1']==tree[path]['sha']
    for path,h in receipt['copiedSources'].items():assert sha(work/Path(path).name)==h==source[path]['sha256']
    clocks=0
    for item in receipt['excerpts']:
        text=(ROOT/source[item['path']]['cache']).read_text();original=original_method(text,item['signature'],item['originalSha256'])
        if item['transformation']=='one fixed-clock call replacement':
            clocks+=1;assert original.count('QDateTime::currentDateTimeUtc()')==1
            adapted=original.replace('QDateTime::currentDateTimeUtc()','fixtureNow()')
        else:assert item['transformation']=='none';adapted=original
        assert digest(adapted.encode())==item['adaptedSha256']and generated.count(adapted)==1
    assert clocks==1 and len(receipt['excerpts'])==18
    readback=json.loads((RUN/'toolchain-readback.json').read_text());assert readback['qtVersion']==receipt['qtVersion']=='6.12.0'
    assert readback['frameworkSha256']==receipt['frameworkSha256']
    # Verify recorded after-run identities without claiming a frozen SDK image.
    for field in ['compilerShim','compilerResolved']:
        p=Path(readback[field]['path']);assert sha(p)==readback[field]['sha256']
    for name,h in receipt['frameworkSha256'].items():assert sha(Path(readback['qtLibdir'])/(name+'.framework')/'Versions/A'/name)==h
    for row in outputs:
        assert row['kind']==next(c['kind']for c in inputs if c['id']==row['id'])
    # These are observations of the compiled methods, not full app/GUI claims.
    collision=by['name-collision'];reverse=by['name-collision-reversed']
    assert collision['claimed']=='A'and reverse['claimed']=='B'
    assert collision['candidateClaimed']==reverse['candidateClaimed']=='B'
    assert next(a for a in collision['held']if a['id']=='B')==dict(id='B',uses=0,refresh=True)
    assert next(a for a in collision['candidateHeld']if a['id']=='B')==dict(id='B',uses=2,refresh=False)
    for row in outputs:
        if row['kind']=='claim':
            assert all(a['uses']==0 for a in row['before']+row['finalized']+row['candidateFinalized'])
            assert max(a['uses']for a in row['oneFinalized'])==(1 if row['claimed']else 0)
    accepted=by['new-profile-accepted'];bad=by['invalid-success-body']
    for row in [accepted,bad]:
        assert row['current']==row['refillOnly']
        assert row['current']['launches']==1 and row['current']['account']['profileId']==''
        assert row['current']['session']['name']=='No Minecraft profile'
        assert row['current']['session']['uuid']==offline_uuid('No Minecraft profile')
        assert row['current']['session']['session']=='token:fixture:'
    assert accepted['admittedThenRefill']['account']['profileId']=='2'*32
    assert accepted['admittedThenRefill']['session']['name']=='Fresh_Player'
    assert accepted['admittedThenRefill']['session']['uuid']=='2'*32
    assert bad['admittedThenRefill']['launches']==0 and bad['admittedThenRefill']['error']
    for id in ['new-profile-rejected','existing-profile','offline-existing','demo']:
        row=by[id];assert row['current']==row['refillOnly']==row['admittedThenRefill']
    assert by['new-profile-rejected']['current']['aborted']and by['new-profile-rejected']['current']['launches']==0
    assert by['inside-12h']['refresh']and not by['exact-12h']['refresh']and by['missing-timestamps']['remaining']is None
    # Source-only caller-admission observations, added after the native cohort.
    profile=(ROOT/source['launcher/minecraft/auth/steps/MinecraftProfileStep.cpp']['cache']).read_text()
    assert 'ContentNotFoundError'in profile and 'Succeed even if we do not have a profile'in profile
    skin=(ROOT/source['launcher/minecraft/auth/steps/GetSkinStep.cpp']['cache']).read_text()
    assert 'emit finished(AccountTaskState::STATE_WORKING'in skin
    return receipt,inputs,outputs


if __name__=='__main__':
    r,i,o=inspect();print(json.dumps(dict(cases=len(o),sourceExcerpts=len(r['excerpts']),copiedSources=len(r['copiedSources']),fixedClockReplacements=1,fullApplicationQualification=False)))
