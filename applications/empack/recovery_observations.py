#!/usr/bin/env python3
"""Verify retained private recovery fixture provenance and scoped observations."""
import hashlib
import inspect
import json
from pathlib import Path
import subprocess

from initializer_probe import retire_owned
from root_state_observations import image

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'applications/evidence/empack-recovery-20261124T215915036620Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    r=json.loads((RUN/'receipt.json').read_text());commands={c['label']:c for c in r['commands']}
    assert len(commands)==len(r['commands'])==65 and len(r['cases'])==19
    assert r['sourceRevision']=='0b4462e3032b4f09230b15329722eabefb7f574c'
    assert sha(RUN/'probe.py')==r['producerSha256'] and sha(RUN/'driver.rs')==r['driverSha256']
    prior=ROOT/r['priorReceipt'];assert sha(prior)==r['priorReceiptSha256'];old=json.loads(prior.read_text())
    scaffold=ROOT/r['scaffold'];assert sha(scaffold)==r['scaffoldSha256']==old['generatedSha256']['current.rs']
    for path,digest in old['sourceSha256'].items():
        raw=subprocess.check_output(['git','-C',str(ROOT.parent/'empack'),'show',old['sourceRevision']+':'+path])
        assert hashlib.sha256(raw).hexdigest()==digest
    current=scaffold.read_text();literal='include!("'+str(prior.parent/'driver.rs')+'");'
    assert current.count(literal)==1
    generated=RUN/'work/main.rs';assert sha(generated)==r['generatedSha256']
    assert generated.read_text()==current.replace(literal,'include!("'+str(RUN/'driver.rs')+'");')
    for info in [r['compiler'],*r['libraries'].values(),r['helper']]:
        p=Path(info['path']);p=p if p.is_absolute()else ROOT/p;assert sha(p)==info['sha256']
        if 'fingerprint'in info:assert sha(Path(info['fingerprint']))==info['fingerprintSha256']
    assert sha(Path(r['binary']))==r['binarySha256']=='99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
    assert r['retireHelperSha256']==hashlib.sha256(inspect.getsource(retire_owned).encode()).hexdigest()
    repo=ROOT.parent/'empack'
    for p,digest in r['sourceSha256'].items():
        raw=(repo/p).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
        for revision in [r['sourceRevision'],r['releaseTag']]:assert subprocess.check_output(['git','-C',str(repo),'show',revision+':'+p])==raw
    images=set();project_unchanged=[];full_unchanged=[];cli=[]
    def at(ref):
        p=RUN/ref['image'];assert sha(p)==ref['sha256'];images.add(ref['image']);return json.loads(p.read_text())
    def project(view):return{k:v for k,v in view.items()if bytes.fromhex(k)==b'project'or bytes.fromhex(k).startswith(b'project/')}
    for c in r['commands']:
        assert c['ownedGroupAbsent'] and c['exitCode']in [0,1]
        for s in ['stdout','stderr']:assert sha(RUN/(c['label']+'.'+s))==c[s+'Sha256']
        if c.get('before'):at(c['before']);at(c['after'])
        if c.get('privateControllingPTY'):
            assert c['mergedOutput'] and c['promptObservedLive'] and c['answer']in ['y','n']
            at(c['afterExplicitEdit']);raw=(RUN/(c['label']+'.stdout')).read_bytes();assert b'Apply this recovery plan?'in raw
        if str(c['argv'][0])==r['binary']:
            assert '--state-dir'in c['argv'] and '--cache-dir'in c['argv'] and '--workdir'in c['argv']
            assert c['argv'][c['argv'].index('--state-dir')+1].startswith(str(RUN/'work/fixtures')+'/')
            before=at(c.get('afterExplicitEdit',c['before']));after=at(c['after']);cli.append(c)
            if project(before)==project(after):project_unchanged.append(c['label'])
            if before==after:full_unchanged.append(c['label'])
    assert len(cli)==45
    rows={c['id']:c for c in r['cases']}
    for c in r['cases']:
        base=RUN/'work'/c['fixture'];assert image(base)==at(c['final'])
        initial=at(c['initial']);state=b'host/'+c['evidence']['key'].encode();marker=initial[(state+b'/root-identity.json').hex()]
        association=json.loads(bytes.fromhex(marker['contentHex']));assert association['persistent']==c['evidence']['root']['persistent']
        assert json.loads(bytes.fromhex(initial[(state+b'/journal.json').hex()]['contentHex']))==c['journal']
        assert all(name in commands for name in c['commands'])
    assert commands['finish-before-apply']['exitCode']==0
    assert commands['restore-bad-before-preview']['exitCode']==0 and commands['restore-bad-before-apply']['exitCode']==1
    assert commands['restore-noop-bad-before-apply']['exitCode']==0
    assert commands['finish-already-after-apply']['exitCode']==0
    for label in ['late-target-prompt','late-object-prompt','late-journal-prompt','late-candidate-prompt']:
        assert commands[label]['exitCode']==1 and label in project_unchanged
    assert commands['late-format-prompt']['exitCode']==0 and commands['declined-prompt']['exitCode']==0
    assert 'declined-prompt'in full_unchanged
    # Execution can add retained scratch while preserving project and journal.
    case=rows['restore-bad-before'];cmd=commands['restore-bad-before-apply'];before=at(cmd['before']);after=at(cmd['after'])
    journal=(b'host/'+case['evidence']['key'].encode()+b'/journal.json').hex()
    assert before[journal]==after[journal] and cmd['label']in project_unchanged and cmd['label']not in full_unchanged
    scratch=(b'host/'+case['evidence']['key'].encode()+b'/'+case['operation'].encode()+b'/restore-0').hex()
    assert scratch not in before and bytes.fromhex(after[scratch]['contentHex'])==b'bad\n'
    report=dict(schema=1,cases=19,commands=65,compilations=1,setupIdentityCommands=19,installedCLICommands=45,privateApprovalPTYs=6,
        imagesVerified=len(images),privatePostimagesVerified=19,projectUnchangedCLICommands=len(project_unchanged),capturedFixtureUnchangedCLICommands=len(full_unchanged),capturedScopes=['project','host','cache','originals'],
        sourcePins=len(r['sourceSha256']),
        findings=['Finish follows the saved journal direction;already-restoring Finish and Restore both complete its after-image.',
            'Preparation can preview restoration with a corrupt before-image;execution refuses while leaving target/journal unchanged and a new retained restore scratch file.',
            'An already-before no-op restoration does not need the corrupt before-image. Already-after Finish does not need a missing candidate.',
            'Actual approval rejects changed target bytes,same-byte object replacement,and typed journal progress. Raw JSON reformatting preserves semantic revision and succeeds.',
            'Corruption after preparation is detected at execution. Refusal does not imply zero host-state effects;decline is an independently observed unchanged case.'],
        limits=['Authored forensic one-file journals,not real producer interruption or power-loss evidence.',
            'One installed macOS0.8.8CLI identity;selected source files match tag,but no reproducible full-build correspondence.',
            'Source helper only supplies native root/file identity and association setup. It is not the recovery implementation.',
            'This checker verifies retained observations;separate model replay,full creation/multi-file/concurrent/root-replacement recovery remain obligations.',
            'Snapshots cover each fixture project,host,cache and retained original handles;not process-wide write tracing or unrelated HOME/tmp changes.'])
    (ROOT/'applications/empack/recovery-observations.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
