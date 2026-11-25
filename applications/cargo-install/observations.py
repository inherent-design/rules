#!/usr/bin/env python3
"""Read captured install/catalog/runtime effects; never invoke Cargo or binaries."""
import hashlib,json,re,tomllib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'applications/evidence/cargo-install-20261125T003504421536Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
NAMES=['rules-install-a','rules-install-b']


def inspect():
    receipt=json.loads((RUN/'receipt.json').read_text());commands=json.loads((RUN/'commands.json').read_text());controls=json.loads((RUN/'controls.json').read_text())
    follow=json.loads((RUN/'new-bin-followup.json').read_text());location=json.loads((RUN/'locations.json').read_text())
    assert receipt['producerSha256']==sha(RUN/'probe.py') and follow['producerSha256']==sha(RUN/'new-bin-followup.py')
    assert len(commands)==receipt['commands']==27 and len(controls)==receipt['controls']==6 and len(follow['commands'])==3
    assert receipt['allOwnedGroupsAbsent'] and all(p['retired']for p in json.loads((RUN/'owned-processes.json').read_text()))
    active=json.loads((RUN/'followup-active.json').read_text());assert active['retired']and active['ownedGroupAbsent']
    for pin in receipt['tools'].values():assert sha(Path(pin['path']))==pin['sha256']
    ledger=json.loads((ROOT/'applications/sources/cargo-install-selections.json').read_text())
    assert ('commit-hash: '+ledger['revision'])in(RUN/'cargo-version.stdout').read_text()
    assert 'release: 1.92.0'in(RUN/'cargo-version.stdout').read_text()
    for pin in ledger['sources']:
        p=ROOT/pin['cache'];assert sha(p)==pin['sha256']and p.stat().st_size==pin['bytes']
    by={r['case']:r for r in commands};cb={r['case']:r for r in controls}
    hashes={}
    for i,name in enumerate(NAMES):
        hashes[name]={by['force-initial']['after']['bin/'+name]['sha256']:1,by['complete-replacement']['after']['bin/'+name]['sha256']:2}
    hashes[NAMES[0]][cb['manual-a']['after']['bin/'+NAMES[0]]['sha256']]=3
    assert cb['manual-a-v2']['after']['bin/'+NAMES[0]]['sha256']in hashes[NAMES[0]]
    hashes[NAMES[0]][commands[0]['before']['bin/'+NAMES[0]]['sha256']]=4
    identities={f"rules-install-ownership {v} (path+file://{location['source']})":i for i,v in [(1,'0.1.0'),(2,'0.2.0')]}
    def state(image):
        for value in image.values():
            if 'text'in value:
                data=value['text'].encode();assert hashlib.sha256(data).hexdigest()==value['sha256']and len(data)==value['bytes']
        present='.crates.toml'in image
        assert present==('.crates2.json'in image)
        owners={name:0 for name in NAMES}
        if present:
            old=tomllib.loads(image['.crates.toml']['text']).get('v1',{})
            text=image['.crates2.json']['text'];new=json.loads(text)['installs']if text else{}
            assert set(old)==set(new)
            for key,bins in old.items():
                assert key in identities and bins==new[key]['bins']and len(set(bins))==len(bins)
                assert all(n in NAMES and owners[n]==0 for n in bins)
                for n in bins:owners[n]=identities[key]
                assert new[key]['rustc']==(RUN/'rustc-version.stdout').read_text()
        values=[]
        for name in NAMES:
            value=image.get('bin/'+name)
            if value is None:body=0
            elif value['kind']=='directory':body=5
            else:
                assert value['kind']=='file'and value['sha256']in hashes[name],('Unknown is not absent',name,value)
                body=hashes[name][value['sha256']]
            values +=[body,owners[name]]
        return dict(zip(['aBody','aOwner','bBody','bOwner','metadata'],values+[present]))
    def catalog(row):
        text=(RUN/row['streams']['stdout']['file']).read_text();found={};owner=None
        for line in text.splitlines():
            if line.startswith('    '):
                name=line.strip();assert name in NAMES and name not in found and owner is not None;found[name]=owner
            else:
                owner=next((v for v,s in [(1,'0.1.0'),(2,'0.2.0')]if line==f"rules-install-ownership v{s} ({location['source']}):"),None)
                assert owner is not None,line
        s=state(row['after']);assert found=={n:s[k]for n,k in zip(NAMES,['aOwner','bOwner'])if s[k]}
    allcommands=commands+follow['commands']
    for row in allcommands:
        assert row['outcome']['ownedGroupAbsent']and not row['outcome'].get('timedOut',False)
        for stream in row['streams'].values():assert sha(RUN/stream['file'])==stream['sha256']
        state(row['before']);state(row['after'])
        if row in commands:
            for image in [row['before'],row['after']]:assert image['bin/unrelated-study-file']['sha256']==receipt['unrelatedMarkerSha256']
        if row['case'].startswith('catalog-')or row['case']=='new-bin-catalog':
            assert row['before']==row['after']and row['outcome']['exitCode']==0;catalog(row)
        if row['case'].startswith('runtime-'):
            assert row['before']==row['after']and row['outcome']['exitCode']==0
            name=Path(row['argv'][0]).name;v=state(row['before'])['aBody'if name==NAMES[0]else'bBody']
            expected='manual replacement\n'if v==3 else f"0.{v}.0-{name[-1]}\n"
            assert (RUN/row['streams']['stdout']['file']).read_text()==expected
    assert by['untracked-collision']['before']!=by['untracked-collision']['after']
    assert state(by['untracked-collision']['after'])==dict(aBody=4,aOwner=0,bBody=0,bOwner=0,metadata=True)
    assert by['compile-refusal']['before']==by['compile-refusal']['after']
    assert by['uninstall-a-with-missing-b']['before']==by['uninstall-a-with-missing-b']['after']
    for c in controls:
        state(c['before']);state(c['after'])
        for k in ['.crates.toml','.crates2.json']:assert c['before'][k]==c['after'][k]
    missing=follow['commands'][0];assert state(missing['before'])==dict(aBody=5,aOwner=0,bBody=0,bOwner=0,metadata=False)
    assert state(missing['after'])==dict(aBody=5,aOwner=0,bBody=0,bOwner=2,metadata=True)
    assert missing['before']['bin/rules-install-a/owned-marker']==missing['after']['bin/rules-install-a/owned-marker']
    err=(RUN/'new-bin-replace-failure.stderr').read_text()
    assert 'Installing'in err and 'rules-install-b'in err and 'Replacing'in err and 'failed to move'in err
    assert 'corrupt metadata'in(RUN/'new-bin-uninstall.stderr').read_text()
    for prev,nxt in zip(follow['commands'],follow['commands'][1:]):assert prev['after']==nxt['before']
    # Link actual command images across each explicitly recorded intervention.
    links={'catalog-manual':'manual-a','partial-replacement':'block-b-directory','complete-replacement':'restore-b-for-retry',
           'uninstall-a-with-missing-b':'remove-b-for-preflight','uninstall-manual-a':'manual-a-v2'}
    for previous,current in zip(commands,commands[1:]):
        if current['case']in links:
            c=cb[links[current['case']]]
            if current['case']=='uninstall-manual-a':
                restore=cb['restore-b-for-uninstall'];assert previous['after']==restore['before']and restore['after']==c['before']
            else:assert previous['after']==c['before']
            assert current['before']==c['after']
        else:assert previous['after']==current['before']
    failed=ROOT/'applications/evidence/cargo-install-20261125T003303650622Z'
    assert 'AssertionError'in(failed/'setup.stderr').read_text()
    # A separate retained copy verifies final source bytes/modes/kinds. Historical
    # before/after source snapshots remain the evidence for earlier versions.
    retained=RUN/'work/project-retained';source=Path(location['source'])
    if source.exists()and retained.exists():
        def image(root):return {str(p.relative_to(root)):(p.is_dir(),p.stat().st_mode & 0o777,sha(p)if p.is_file()else None)for p in root.rglob('*')}
        assert image(source)==image(retained)
    return receipt,commands,controls,follow,state


if __name__=='__main__':
    receipt,commands,controls,follow,_=inspect()
    print(json.dumps(dict(commands=len(commands)+len(follow['commands']),controls=len(controls),allOwnedGroupsAbsent=True)))
