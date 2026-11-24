#!/usr/bin/env python3
"""Verify the later allocation-termination counterexample;no native execution."""
import hashlib
import json
from pathlib import Path
import subprocess

from root_state_observations import image

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'applications/evidence/empack-initializer-20261124T212854359074Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    r=json.loads((RUN/'receipt.json').read_text());assert r['profile']=='temporary-allocation-termination'
    assert len(r['commands'])==8 and len(r['cases'])==6 and len(r['sourceSha256'])==12
    assert r['sourceRevision']=='0b4462e3032b4f09230b15329722eabefb7f574c'
    assert sha(RUN/'probe.py')==r['producerSha256'] and sha(RUN/'driver.rs')==r['driverSha256']
    assert sha(ROOT/r['scaffold'])==r['scaffoldSha256'] and sha(ROOT/r['scaffoldReceipt'])==r['scaffoldReceiptSha256']
    assert sha(Path(r['compiler']['path']))==r['compiler']['sha256']
    for a in r['libraries'].values():
        assert sha(Path(a['path']))==a['sha256']
        if 'fingerprint'in a:assert sha(Path(a['fingerprint']))==a['fingerprintSha256']
    for n,h in r['generatedSha256'].items():assert sha(RUN/'work'/n)==h
    for a in r['binaries'].values():assert sha(ROOT/a['path'])==a['sha256']
    repo=ROOT.parent/'empack'
    for path,digest in r['sourceSha256'].items():
        raw=subprocess.check_output(['git','-C',str(repo),'show',r['sourceRevision']+':'+path]);assert hashlib.sha256(raw).hexdigest()==digest==sha(repo/path)
    current=(RUN/'work/current.rs').read_text();candidate=(RUN/'work/candidate.rs').read_text();p=r['candidatePatch']
    assert current.count(p['old'])==p['count']==1 and current.replace(p['old'],p['new'])==candidate
    assert 'let value=actual_staging::create_temporary(parent)?;\n fixture_phase("temporary")?;Ok(value)' in current
    for s in r['sourceSelections']:
        text=(repo/s['path']).read_text();chunk=text[text.index(s['start']):text.index(s['stop'])]
        assert hashlib.sha256(chunk.encode()).hexdigest()==s['sha256'] and chunk in current and chunk in candidate
    killed=0
    for c in r['commands']:
        assert not c['timedOut'] and c['ownedGroupAbsent'] and c['exitCode']==(-9 if c['intentionalKill']else 0)
        killed+=int(c['intentionalKill'])
        for stream in ['stdout','stderr']:assert sha(RUN/(c['label']+'.'+stream))==c[stream+'Sha256']
    assert killed==2
    cases={c['label']:c for c in r['cases']};latest={};images=set()
    def load(c,part):
        ref=c[part];p=RUN/ref['image'];assert sha(p)==ref['sha256'];images.add(ref['image']);return json.loads(p.read_text())
    for c in r['cases']:
        for part in ['before','during','after']:
            if part in c:load(c,part)
        latest[c['fixture']]=load(c,'after')
    for fixture,expected in latest.items():assert image(RUN/'work'/fixture)==expected
    for variant in ['current','candidate']:
        paused=cases[variant+'-temporary-paused'];assert paused['action']=='terminated-after-temporary-allocation'
        assert paused['during']['sha256']==paused['after']['sha256']
        state=load(paused,'after');files={bytes.fromhex(p).decode():v for p,v in state.items()if v['kind']=='file'}
        own=[(p,v)for p,v in files.items()if p.startswith('host/')]
        coordinator='operation.lock'if variant=='current'else'state.lock'
        assert sorted(p.rsplit('/',1)[1]for p,v in own)==sorted([coordinator,paused['scratchName']])
        assert paused['scratchName'].startswith('.empack-candidate-') and all(v['bytes']==0 and v['contentHex']==''for p,v in own)
        assert not any(p.endswith('/root-identity.json')for p in files)
        for suffix in ['-temporary-lookup','-temporary-retry']:
            c=cases[variant+suffix];assert not c['outcome']['ok'] and c['outcome']['unassociated']
            assert c['before']['sha256']==c['after']['sha256']==paused['after']['sha256']
    proposal=json.loads((ROOT/'applications/sources/empack-initializer-directory-proposal.json').read_text())
    assert sha(repo/proposal['path'])==proposal['sha256']
    report=dict(schema=1,sourcePins=12,commands=8,cases=6,intentionalTerminations=2,refusedOrdinaryAPIResults=4,
        capturedImagesVerified=len(images),finalPrivateFixturesVerified=len(latest),
        finding='Both current source and the metadata-lock candidate strand initialization after temporary allocation but before association write. Empty scratch is preserved;fresh lookup/retry refuse unchanged.',
        candidateDisposition='Metadata-lock-only candidate is incomplete as a general interruption fix. Its earlier post-lock improvement remains a bounded observation.',
        nextDesign='Investigate preparing a complete association-bearing private directory and publishing it with existing identity-checked no-replace directory machinery;proposed only,no implementation/native qualification.',
        limits=['This checker verifies retained source/effects;separate initializer_conformance.py compares initializer/mixed/temporary traces.',
            'Selected source chain with supplied host Dir and delegated allocation pause;not Engine/CLI startup or arbitrary crash/power-loss qualification.',
            'Owned SIGKILL after actual zero-byte allocation;no partial association bytes or post-rename/pre-fsync failure sampled.',
            'No scratch cleanup or unknown-state adoption is authorized. Candidate directory primitive source inspected only. Production and live stores unchanged.'])
    (ROOT/'applications/empack/initializer-temporary-observations.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
