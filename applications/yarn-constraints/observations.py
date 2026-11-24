#!/usr/bin/env python3
"""Check captured constraints effects and callback visits; no Yarn execution."""
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'applications/evidence/yarn-constraints-20261124T232837924143Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def presentation(c):
    lines=(RUN/c['streams']['stdout']['file']).read_text().splitlines();parsed=0;unparsed=[]
    for line in lines:
        if not line.strip():continue
        try:json.loads(line);parsed+=1
        except json.JSONDecodeError:unparsed.append(line)
    guidance=[line for line in unparsed if 'constraints --fix'in line and ('Those errors'in line or 'Errors prefixed'in line)]
    return dict(jsonRows=parsed,nonJsonRows=len(unparsed),humanGuidance=bool(guidance))


def inspect():
    receipt=json.loads((RUN/'receipt.json').read_text());rows=json.loads((RUN/'commands.json').read_text())
    assert receipt['producerSha256']==sha(RUN/'probe.py')and receipt['commands']==len(rows)==23
    for pin in receipt['tools'].values():assert sha(Path(pin['path']))==pin['sha256']
    assert receipt['allOwnedGroupsAbsent']and all(p['retired']for p in json.loads((RUN/'owned-processes.json').read_text()))
    by={(c['case'],c['label']):c for c in rows}
    for c in rows:
        assert c['outcome']['ownedGroupAbsent']and not c['outcome']['timedOut']
        for s in c['streams'].values():assert sha(RUN/s['file'])==s['sha256']
        if c['label']!='install':
            for p in ['yarn.lock','yarn.config.cjs']:assert c['before'][p]==c['after'][p]
            if '--fix'not in c['argv']:assert c['before']==c['after']
    for case in ['simple','mixed','chain','late-throw','same-object','equal-objects']:
        visits=[v for c in rows if c['case']==case for v in c['ruleVisits']]
        assert visits==[json.loads(line)for line in (RUN/'work'/case/'project/rule-calls.ndjson').read_text().splitlines()]
    def state(c,phase='after',path='package.json'):return json.loads(c[phase][path]['text'])
    def passes(c):return len({v['pass']for v in c['ruleVisits']})
    simple=by['simple','fix'];assert simple['outcome']['exitCode']==0 and passes(simple)==10
    assert state(simple)['license']=='MIT'and state(simple,path='packages/child/package.json')['license']=='MIT'
    assert all(v['license']=='MIT'for v in simple['ruleVisits']if v['pass']>1)
    mixed=by['mixed','fix'];assert mixed['outcome']['exitCode']==1 and passes(mixed)==10
    assert 'license'not in state(mixed)and state(mixed,path='packages/child/package.json')['license']=='MIT'
    chain=by['chain','fix'];assert chain['outcome']['exitCode']==0 and passes(chain)==10 and state(chain)['studyCounter']==10
    assert [v['counter']for v in chain['ruleVisits']if v['workspace']=='.']==list(range(10))
    post=by['chain','post-cap-check'];assert post['outcome']['exitCode']==1 and post['before']==post['after']and state(post)['studyCounter']==10
    finish=by['chain','finish-fix'];assert finish['outcome']['exitCode']==0 and passes(finish)==10 and state(finish)['studyCounter']==12
    assert by['chain','recheck']['outcome']['exitCode']==0
    thrown=by['late-throw','fix'];assert thrown['outcome']['exitCode']==1 and passes(thrown)==2 and state(thrown)['studyCounter']==1
    assert [(v['pass'],v['workspace'],v['counter'])for v in thrown['ruleVisits']]==[(1,'.',0),(1,'packages/child',0),(2,'.',1)]
    same=by['same-object','fix'];different=by['equal-objects','fix']
    assert same['outcome']['exitCode']==0 and state(same)['studyObject']=={'mode':'plain'}
    assert different['outcome']['exitCode']==1 and different['before']==different['after']
    assert 'Conflict detected in constraint targeting studyObject'in (RUN/'equal-objects-fix.stdout').read_text()
    shapes=[presentation(c)for c in rows if c['label']!='install']
    assert sum(s['humanGuidance']for s in shapes)==6
    assert all(s['jsonRows']>0 and s['nonJsonRows']==1 for s in shapes if s['humanGuidance'])
    correction=json.loads((RUN/'setup-correction.json').read_text());old=ROOT/correction['failedCapture']
    assert sha(old/'probe.py')==correction['originalProducerSha256']and sha(RUN/'probe.py')==correction['correctedProducerSha256']
    assert sha(old/'commands.json')==correction['failedCommandsSha256']and sha(old/'simple-install.stdout')==correction['failedStdoutSha256']and sha(old/'simple-install.stderr')==correction['failedStderrSha256']
    failed=json.loads((old/'commands.json').read_text());assert len(failed)==1 and failed[0]['before']==failed[0]['after']and failed[0]['outcome']['exitCode']==1
    assert not failed[0]['ruleCalls']and correction['allOldGroupsRetired']and failed[0]['outcome']['ownedGroupAbsent']
    return receipt,rows


def main():
    receipt,rows=inspect()
    report=dict(schema=1,status='Native/source observations;separate scoped formal comparison retained in conformance.json.',capture=str(RUN.relative_to(ROOT)),nativeCommands=23,constraintCommands=17,callbackWorkspaceVisits=143,
        profiles=6,allocatedKiB=receipt['allocatedKiB'],allOwnedGroupsAbsent=True,
        stdoutPresentation=[dict(case=c['case'],label=c['label'],**presentation(c))for c in rows if c['label']!='install'],
        observations=['A chain needing12 increments returns0 at counter10 after --fix;immediate ordinary check returns1 with the saved counter10 unchanged.',
            'Stable simple rules and converged chain still receive ten callback invocations under --fix.',
            'Mixed conflict preserves an independently fixed child manifest with status1. A later callback throw leaves the earlier counter1 persisted,status1.',
            'Two identical object proposals at distinct JS identities conflict;using one shared object reference succeeds. This is reference-identity admission versus manifest JSON equality.',
            'Six --json checks prepend one human guidance line before NDJSON diagnostics. A later callback exception emits a separate non-JSON stack;its outer CLI formatting remains unmodeled.'],
        limits=['Only generated Modern JS constraint rules on one local macOS profile;no Prolog,dependency compatibility,arbitrary project rules,remote or concurrent-editor qualification.',
                'Owned callback instrumentation observes its own visits,not process-wide IO or a disk snapshot at every pass. Final manifest and lock/configuration observations are independent.',
                'Check does not write measured manifest/lock/configuration here;the callback deliberately appends a trace,so arbitrary code side-effect freedom is not claimed.',
                'One earlier invalid --mode=skip-builds setup was rejected before any rule ran;frozen original and correction are separate. No production patch,upstream report or complete feature claim.'])
    (RUN/'observations.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
