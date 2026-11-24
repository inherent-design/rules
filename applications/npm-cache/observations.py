#!/usr/bin/env python3
"""Validate the owned cache/installation capture; no npm or Node execution."""
import base64,hashlib,json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'applications/evidence/npm-cache-20261124T235228248707Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def inspect():
    receipt=json.loads((RUN/'receipt.json').read_text());commands=json.loads((RUN/'commands.json').read_text());by={c['case']:c for c in commands}
    assert len(commands)==receipt['commands']==14 and receipt['producerSha256']==sha(RUN/'probe.py')
    for pin in receipt['tools'].values():assert sha(Path(pin['path']))==pin['sha256']
    closed=json.loads((RUN/'closed.json').read_text());assert closed['serverClosed']and closed['allOwnedProcessesRetired']
    assert receipt['allOwnedGroupsAbsent']and all(p['retired']for p in json.loads((RUN/'owned-processes.json').read_text()))
    for c in commands:
        assert c['outcome']['ownedGroupAbsent']and not c['outcome']['timedOut']
        for s in c['streams'].values():assert sha(RUN/s['file'])==s['sha256']
        if c['case']!='install':assert c['before']['authored']==c['after']['authored']
        if c['kind']=='observer' or c['case'].startswith('verify-'):assert c['before']['installed']==c['after']['installed']
        if c['kind']=='observer':assert c['before']==c['after']
    requests=json.loads((RUN/'requests.json').read_text());assert requests==[q for c in commands for q in c['requests']]
    assert [(q['path'],q['status'])for q in requests]==[('/fixture-cache',200),('/fixture-cache/-/fixture-cache-1.0.0.tgz',200),('/fixture-cache/-/fixture-cache-1.0.0.tgz',200)]
    assert len(by['install']['requests'])==2 and len(by['ci-origin-recovery']['requests'])==1
    assert all(not c['requests']for c in commands if c['case']not in ['install','ci-origin-recovery'])
    assert [c['outcome']['exitCode']for c in commands if c['kind']=='npm']==[0,0,0,1,0,0,0]
    tar=RUN/'fixture.tgz';assert sha(tar)==receipt['fixtureSha256']
    assert 'sha512-'+base64.b64encode(hashlib.sha512(tar.read_bytes()).digest()).decode()==receipt['fixtureIntegrity']
    with tarfile.open(tar,'r:gz')as archive:
        assert archive.getnames()==['package/package.json','package/index.js']and all(m.isfile()for m in archive.getmembers())
        original_index=archive.extractfile('package/index.js').read();original_hash=hashlib.sha256(original_index).hexdigest()
    corrupt=json.loads((RUN/'cache-corruption.json').read_text());edit=json.loads((RUN/'installed-edit.json').read_text())
    assert corrupt['nlinkBefore']==1 and corrupt['expectedIntegrity']==receipt['fixtureIntegrity']
    assert corrupt['originalSha256']==sha(RUN/'work/originals/cache-tar.tgz')==receipt['fixtureSha256']
    bad=bytearray(tar.read_bytes());bad[0]^=1;assert hashlib.sha256(bad).hexdigest()==corrupt['mutatedSha256']
    target=corrupt['target'].removeprefix('cache/_cacache/');assert target.startswith('content-v2/sha512/')
    assert corrupt['before']==by['verify-valid']['after']and corrupt['after']==by['runtime-after-cache-corruption']['before']
    assert corrupt['before']['cache'][target]['sha256']==receipt['fixtureSha256']and corrupt['after']['cache'][target]['sha256']==corrupt['mutatedSha256']
    assert target not in by['verify-corrupt']['after']['cache']
    output=(RUN/'verify-corrupt.stdout').read_text();assert all(s in output for s in ['Corrupted content removed: 1','Missing content: 1','Index entries: 1'])
    failed=by['ci-offline-missing'];assert failed['before']['installed']and not failed['after']['installed']
    assert 'ENOTCACHED'in (RUN/'ci-offline-missing.stderr').read_text()
    assert edit['before']==by['runtime-after-recovery']['after']and edit['after']==by['verify-with-installed-edit']['before']
    assert edit['originalSha256']==sha(RUN/'work/originals/installed-index.js')==original_hash
    assert edit['after']['installed']['fixture-cache/index.js']['sha256']==edit['editedSha256']!=original_hash
    expected={'runtime-initial':dict(available=True,value='original fixture'),'runtime-after-cache-corruption':dict(available=True,value='original fixture'),
              'runtime-after-verify':dict(available=True,value='original fixture'),'runtime-after-failed-ci':dict(available=False,code='MODULE_NOT_FOUND'),
              'runtime-after-recovery':dict(available=True,value='original fixture'),'runtime-edited-installation':dict(available=True,value='edited installation'),'runtime-final':dict(available=True,value='original fixture')}
    for label,value in expected.items():assert json.loads((RUN/(label+'.stdout')).read_text())==value and by[label]['outcome']['exitCode']==0
    assert by['ci-offline-valid']['after']['installed']['fixture-cache/index.js']['sha256']==original_hash
    return receipt,commands,corrupt,edit


def main():
    receipt,commands,corrupt,edit=inspect()
    report=dict(schema=1,status='Intermediate source/native observations;formal models pending.',nativeCommands=14,npmCommands=7,nodeAvailabilityObservers=7,registryRequests=3,allocatedKiB=receipt['allocatedKiB'],
        allOwnedGroupsAbsent=True,serverClosed=True,
        findings=['Cache verification successfully removes one corrupt cached tar and reports missing content;it does not validate or rewrite the installed module.',
            'An offline clean install fails after removing the old installed tree;manifest/lock/configuration remain unchanged. Status1 is not absence of installed-tree effects.',
            'Own-origin reacquisition restores the module;valid offline cache can later rebuild an edited installation. Cache verification alone preserves that installed edit.',
            'The Node observer returns0 for a well-formed availability report even when the module is missing;the report field,not process status alone,describes availability.'],
        limits=['One generated two-file package,one local project/private cache,one loopback registry. No global cache,real dependency graph,external service,shared writer,remote trust or durability qualification.',
                'Captured cache snapshots are file/hash views,not a general semantic cache-index decoder. Availability beyond this closed fixture needs index/read/lease evidence.',
                'Source flatOptions/cacache verification and ci stage order are inspected;this fixture does not make every acquisition failure post-clear or claim a clean-install correctness defect.',
                'No new npm/Node execution by this checker. Formal comparison and improvement proposals remain separate;no complete feature or production change.'])
    (RUN/'observations.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
