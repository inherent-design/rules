#!/usr/bin/env python3
"""Replay retained source/native initializer schedules in two pure models.

No native collection: schedules come from frozen producers and receipts; expected
footprints, API results, command statuses, and lock observations stay independent.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

import initializer_observations as baseline
import initializer_mixed_observations as mixed
import initializer_temporary_observations as temporary
from root_state_conformance import parsed_record, Tokens

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
VARIANT={'current':0,'candidate':1}


def footprint(run,ref):
    p=run/ref['image'];assert sha(p)==ref['sha256']
    image=json.loads(p.read_text());raw={bytes.fromhex(k):v for k,v in image.items()}
    slots=[k for k in raw if k.startswith(b'host/project-') and k.count(b'/')==1]
    assert len(slots)<=1
    if not slots:return 0,None
    slot=slots[0];assert raw[slot]['kind']=='directory'
    children={k[len(slot)+1:]:v for k,v in raw.items() if k.startswith(slot+b'/')}
    op=meta=temp=assoc=unknown=False;marker=None
    for name,value in children.items():
        assert b'/' not in name and value['kind']=='file'
        if name==b'operation.lock':op=True;assert value['bytes']==0
        elif name==b'state.lock':meta=True;assert value['bytes']==0
        elif name.startswith(b'.empack-candidate-'):temp=True;assert value['bytes']==0
        elif name==b'root-identity.json':
            payload=bytes.fromhex(value['contentHex']);r=parsed_record(payload,Tokens().label)
            original=json.loads(payload)['original'];project=raw[b'project']
            assert project['kind']=='directory' and str(original['volume'])==project['device']
            assert str(int.from_bytes(bytes(original['object']),'little'))==project['inode']
            assert len(payload)<=1024 and r is not None and r['schema']==1 and r['original']==slot.decode().split('/',1)[1]
            assoc=True;marker=value
        else:unknown=True
    return 1+2*op+4*meta+8*temp+16*assoc+32*unknown,marker


class Trace:
    def __init__(self,run,initial,name):
        self.run=run;self.name=name;self.seed=footprint(run,initial)[0]
        assert not self.seed&8
        self.events=[];self.actors={};self.known={};self.checks=[];self.observed_writes=0
        self.last_marker=footprint(run,initial)[1]
    def actor(self,label,variant):
        if label not in self.actors:
            self.actors[label]=len(self.actors);self.known[label]=dict(variant=VARIANT[variant],api=0,command=0)
        return self.actors[label]
    def event(self,kind,label,variant='current'):
        self.events.append(dict(kind=kind,actor=self.actor(label,variant),variant=VARIANT[variant]))
    def phase(self,label,variant,point):
        self.event(0,label,variant);self.known[label]['phase']=1
        if point in ['temporary','completed']:
            self.event(1,label);self.known[label]['phase']=2
        if point=='completed':
            self.event(2,label);self.known[label].update(phase=3,api=1)
    def killed(self,label):
        self.event(3,label);self.known[label].update(phase=4,command=2)
    def call(self,label,variant,action,outcome):
        self.event(7 if action=='lookup' else 6,label,variant)
        self.result(label,outcome,action)
    def result(self,label,outcome,action='initialize'):
        # Expected values are decoded from retained native output,not the model.
        if outcome['ok']:api=1
        elif outcome.get('unassociated'):api=2
        else:
            assert 'initialization is busy' in outcome['error'];api=3
        self.known[label].update(phase=3,api=api,command=1)
        if action=='lookup' and api==1:self.known[label]['found']=2 if outcome['selected'] else 1
    def resume(self,label,outcome):
        # The source's second read precedes allocation. Use the retained last
        # view of the slot,not the expected success/failure to choose this path.
        assert self.last_marker is not None or self.known[label]['phase']==1
        if self.last_marker is None:self.event(1,label)
        self.event(2,label);self.event(4,label);self.result(label,outcome)
    def check(self,label,ref,leases=None):
        mask,marker=footprint(self.run,ref)
        if marker is not None and marker!=self.last_marker:self.observed_writes+=1
        # No image sampling can exclude unobserved intermediate rewrites. This
        # counts observed registrations/changed postimages under these schedules.
        self.last_marker=marker
        self.checks.append(dict(id=self.name+'/'+label,input=dict(initial=self.seed,actors=max(1,len(self.actors)),events=copy.deepcopy(self.events)),
            expected=dict(mask=mask,leases=leases,writes=self.observed_writes,actors={self.actors[k]:copy.deepcopy(v)for k,v in self.known.items()}),
            image=str((self.run/ref['image']).relative_to(ROOT))))


def retained_traces():
    checks=[];r=json.loads((baseline.RUN/'receipt.json').read_text());rows={c['label']:c for c in r['cases']}
    # Finish order is not start order in this receipt. The frozen producer
    # starts/pauses the first actor before the contender runs.
    for variant in VARIANT:
        c=rows[variant+'-normal'];t=Trace(baseline.RUN,c['before'],variant+'-normal');t.check('before',c['before'],0)
        for label in [variant+'-normal',variant+'-idempotent']+(['candidate-current-interop']if variant=='current'else[]):
            c=rows[label];t.check(label+'-before',c['before'],0);t.call(label,c['variant'],c['action'],c['outcome']);t.check(label+'-after',c['after'],0)
        checks+=t.checks
        c=rows[variant+'-paused'];t=Trace(baseline.RUN,c['before'],variant+'-lock');t.check('before',c['before'],0)
        t.phase(c['label'],variant,'locked');t.check('paused',c['during'],1 if variant=='current'else 2)
        contender=rows[variant+'-concurrent'];t.check('contender-before',contender['before'])
        t.call(contender['label'],variant,contender['action'],contender['outcome']);t.check('contender-after',contender['after'])
        t.killed(c['label']);t.check('killed',c['after'],0)
        for suffix in ['-after-kill-lookup','-retry']:
            c=rows[variant+suffix];t.check(c['label']+'-before',c['before'],0)
            t.call(c['label'],variant,c['action'],c['outcome']);t.check(c['label']+'-after',c['after'],0)
        checks+=t.checks
        c=rows[variant+'-after-completed'];t=Trace(baseline.RUN,c['before'],variant+'-returned');t.check('before',c['before'],0)
        t.phase(c['label'],variant,'completed');t.killed(c['label']);t.check('killed-after-return',c['after'],0)
        for suffix in ['-completed-lookup','-completed-retry']:
            c=rows[variant+suffix];t.check(c['label']+'-before',c['before'],0)
            t.call(c['label'],variant,c['action'],c['outcome']);t.check(c['label']+'-after',c['after'],0)
        checks+=t.checks
        # The producer explicitly authors unknown bytes after a no-state lookup.
        c=rows[variant+'-key'];t=Trace(baseline.RUN,c['before'],variant+'-key');t.call(c['label'],variant,c['action'],c['outcome']);t.check('lookup',c['after'],0);checks+=t.checks
        c=rows[variant+'-unknown-refusal'];t=Trace(baseline.RUN,c['before'],variant+'-unknown');t.check('authored-before',c['before'],0)
        t.call(c['label'],variant,c['action'],c['outcome']);t.check('refused',c['after'],0);checks+=t.checks
    r=json.loads((temporary.RUN/'receipt.json').read_text());rows={c['label']:c for c in r['cases']}
    for variant in VARIANT:
        c=rows[variant+'-temporary-paused'];t=Trace(temporary.RUN,c['before'],variant+'-temporary');t.check('before',c['before'],0)
        t.phase(c['label'],variant,'temporary');t.check('allocated',c['during'],1 if variant=='current'else 2)
        t.killed(c['label']);t.check('killed',c['after'],0)
        for suffix in ['-temporary-lookup','-temporary-retry']:
            c=rows[variant+suffix];t.check(c['label']+'-before',c['before'],0)
            t.call(c['label'],variant,c['action'],c['outcome']);t.check(c['label']+'-after',c['after'],0)
        checks+=t.checks
    # Explicit view/event placement follows the four frozen producer schedules;
    # views and events are separately ordered arrays,not a joined timestamp log.
    r=json.loads((mixed.RUN/'receipt.json').read_text());scenarios={s['id']:s for s in r['scenarios']}
    for name in scenarios:
        s=scenarios[name];views={v['label']:v for v in s['views']};t=Trace(mixed.RUN,s['views'][0],name)
        started={e['label']:e for e in s['events']if e['event']=='started'}
        ended={e['label']:e for e in s['events']if e['event']=='finished'}
        def view(label,leases=None):t.check(label,views[label],leases)
        def pause(label):t.phase(label,started[label]['variant'],'locked')
        def call(label):
            e=started[label];t.call(label,e['variant'],e['action'],ended[label]['outcome'])
        def resume(label):t.resume(label,ended[label]['outcome'])
        view(s['views'][0]['label'],0)
        if name=='candidate-first-current-completes':
            pause('one-candidate');view('one-candidate-paused',2)
            call('one-current');view('one-current-returned',2)
            resume('one-candidate');view('one-candidate-returned',0)
        elif name=='current-dies-candidate-completes':
            pause('two-candidate');pause('two-current');view('two-both-paused',3)
            t.killed('two-current');view('two-current-terminated',2)
            resume('two-candidate');view('two-candidate-returned',0)
            call('two-lookup');view('two-reopened',0)
        elif name=='both-die-old-footprint-remains':
            pause('three-candidate');pause('three-current');view('three-both-paused',3)
            t.killed('three-current');t.killed('three-candidate');view('three-terminated',0)
            call('three-lookup');view('three-lookup-result',0)
            call('three-retry');view('three-retry-result',0)
        else:
            assert name=='current-first-candidate-retries'
            pause('four-current');view('four-current-paused',1)
            call('four-candidate-refused');view('four-candidate-refused',1)
            resume('four-current');view('four-current-returned',0)
            call('four-candidate-retry');view('four-candidate-retried',0)
        assert {c['image']for c in t.checks}=={str((mixed.RUN/v['image']).relative_to(ROOT))for v in s['views']}
        checks+=t.checks
    return checks


def decode(text):
    fields=text.split('/');assert fields[0]in ['0','1']
    return dict(valid=int(fields[0]),mask=int(fields[1]),leases=int(fields[2]),writes=int(fields[3]),
        actors=[dict(zip(['variant','phase','api','command','scratch','found'],map(int,a.split(','))))for a in fields[4:]])
def compare(c,text):
    a=decode(text);e=c['expected'];assert a['valid']==1,(c['id'],a)
    for key in ['mask','writes']:
        assert a[key]==e[key],(c['id'],key,a[key],e[key])
    if e['leases']is not None:assert a['leases']==e['leases'],(c['id'],'leases',a,e)
    for n,partial in e['actors'].items():
        for k,v in partial.items():assert a['actors'][n][k]==v,(c['id'],n,k,a['actors'][n][k],v)


def bend_bool(b):return 'True{}'if b else 'False{}'
def bend_call(r):
    m=r['initial'];a='['+','.join('S.fresh()'for _ in range(r['actors']))+']'
    seed='S.IState{'+','.join([*(bend_bool(bool(m&b))for b in [1,2,4,16,32]),a,'0n','True{}'])+'}'
    es='['+','.join('S.IEvent{'+','.join(str(e[k])+'n'for k in ['kind','actor','variant'])+'}'for e in r['events'])+']'
    return 'S.render(S.run('+es+','+seed+'))'


def main():
    for module in ['initializer_observations.py','initializer_mixed_observations.py','initializer_temporary_observations.py']:
        p=subprocess.run(['python3',str(HERE/module)],cwd=ROOT,capture_output=True,text=True,timeout=90)
        assert p.returncode==0,p.stdout+p.stderr
    cases=retained_traces();assert len({c['id']for c in cases})==len(cases)
    generated=HERE/'generated';generated.mkdir(exist_ok=True);formal=generated/'formal'
    artifact=formal/'applications/empack/Initialization.olean';artifact.parent.mkdir(parents=True,exist_ok=True)
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    env=dict(os.environ,LEAN_PATH=str(formal),BEND_NO_TELEMETRY='1')
    p=subprocess.run([lean,'-DwarningAsError=true','-o',str(artifact),'applications/empack/Initialization.lean'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    assert p.returncode==0,p.stdout+p.stderr
    research=generated/'initializer.json'
    def replay(data):
        research.write_text(json.dumps(data)+'\n')
        return subprocess.run([lean,'--run','applications/empack/InitializationCase.lean',str(research)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    data=dict(schema=1,profile='selected-initializer-phases',cases=[c['input']for c in cases])
    p=replay(data);assert p.returncode==0,p.stdout+p.stderr
    actual=json.loads(p.stdout);assert len(actual)==len(cases)
    for c,a in zip(cases,actual):compare(c,a)
    driver=generated/'InitializationCase.bend'
    driver.write_text('import Base\nimport ../Initialization.bend as S\n\ndef main() -> IO(Unit):\n  IO.write('+ ' ++ '.join(bend_call(c['input'])+' ++ "\\n"'for c in cases)+')\n')
    p=subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    assert p.returncode==0,p.stdout+p.stderr
    assert p.stdout.splitlines()==actual,[(c['id'],a,b)for c,a,b in zip(cases,actual,p.stdout.splitlines())if a!=b]
    invalid=[]
    for name,edit in [
        ('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='full-engine')),
        ('empty-actor-set',lambda d:d['cases'][0].update(actors=0)),('actor-limit',lambda d:d['cases'][0].update(actors=17)),
        ('unowned-scratch',lambda d:d['cases'][0].update(initial=9)),('missing-slot',lambda d:d['cases'][0].update(initial=2)),
        ('bad-mask',lambda d:d['cases'][0].update(initial=64)),('unknown-event',lambda d:d['cases'][0].update(events=[dict(kind=8,actor=0,variant=0)])),
        ('bad-variant',lambda d:d['cases'][0].update(events=[dict(kind=0,actor=0,variant=2)])),
        ('missing-actor',lambda d:d['cases'][0].update(events=[dict(kind=0,actor=16,variant=0)])),
        ('event-limit',lambda d:d['cases'][0].update(events=[dict(kind=4,actor=0,variant=0)]*129))]:
        d=copy.deepcopy(data);edit(d);p=replay(d);assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);invalid.append(name)
    # Mutation controls show retained expectations can falsify a projection.
    mutations=[]
    for key in ['mask','writes','leases']:
        c=copy.deepcopy(cases[0]);c['expected'][key]=99
        try:compare(c,actual[0])
        except AssertionError:mutations.append(key)
        else:raise AssertionError('Mutation escaped: '+key)
    j=next(i for i,c in enumerate(cases)if c['expected']['actors']);c=copy.deepcopy(cases[j]);n=next(iter(c['expected']['actors']));c['expected']['actors'][n]['api']=99
    try:compare(c,actual[j])
    except AssertionError:mutations.append('api')
    else:raise AssertionError('API mutation escaped')
    out=baseline.RUN/'conformance.json'
    files=[HERE/n for n in ['Initialization.lean','Initialization.bend','InitializationCase.lean','initializer_conformance.py',
        'initializer_observations.py','initializer_mixed_observations.py','initializer_temporary_observations.py']]
    files += [ROOT/'applications/sources'/n for n in ['empack-initializer-selections.json','empack-initializer-directory-proposal.json']]
    for run in [baseline.RUN,mixed.RUN,temporary.RUN]:
        files += [p for p in run.rglob('*')if p.is_file()and 'work'not in p.relative_to(run).parts and p.name!='conformance.json']
    receipt=dict(schema=1,sourceRevision='0b4462e3032b4f09230b15329722eabefb7f574c',
        traces=len({c['id'].split('/')[0]for c in cases}),retainedProjectionComparisons=len(cases),
        researchInputRefusals=invalid,observationMutationControls=mutations,
        basisSha256={str(p.relative_to(ROOT)):sha(p)for p in sorted(set(files))},
        tools={n:dict(path=str(Path(p).resolve()),sha256=sha(Path(p)))for n,p in [('lean',lean),('bend',bend)]},
        generatedDriverSha256=sha(driver),leanResultsSha256=hashlib.sha256(json.dumps(actual,separators=(',',':')).encode()).hexdigest(),
        limits=['Pure protocol projection replay,no new native/engine execution or fixture changes.',
            'Expected file/record images and API/command results come from retained evidence;phase schedule follows frozen producers. Mixed events and views have no shared timestamp sequence.',
            'Matching-root schema1 record admission is externally decoded;native capability,root races,permissions and error-priority are not proved.',
            'Observed postimage registrations do not exclude unsampled rewrites. Successful IO is abstracted;no partial-byte,rename,fsync,power-loss or complete recovery qualification.',
            'Directory-publication admission laws are proposed only;no candidateB implementation,platform qualification,or orphan cleanup authority.'])
    out.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items()if k!='basisSha256'},indent=2))


if __name__=='__main__':main()
