#!/usr/bin/env python3
"""Verify four retained mixed-protocol schedules;no native execution."""
import hashlib
import inspect
import json
from pathlib import Path

from initializer_probe import retire_owned
from root_state_observations import image

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'applications/evidence/empack-initializer-mixed-20261124T211709634681Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    r=json.loads((RUN/'receipt.json').read_text());assert len(r['scenarios'])==4 and len(r['commands'])==12
    assert sha(RUN/'probe.py')==r['producerSha256'] and sha(ROOT/r['priorReceipt'])==r['priorReceiptSha256']
    assert r['retireHelperSha256']==hashlib.sha256(inspect.getsource(retire_owned).encode()).hexdigest()
    prior=json.loads((ROOT/r['priorReceipt']).read_text());assert r['binaries']==prior['binaries']
    for v,a in r['binaries'].items():assert sha(ROOT/a['path'])==a['sha256']
    commands={c['label']:c for c in r['commands']};scenarios={s['id']:s for s in r['scenarios']}
    assert len(commands)==12
    terminations=0;results=0;successes=0;image_count=0
    for s in r['scenarios']:
        live=set();returned=set();started={};phases={}
        for e in s['events']:
            label=e['label']
            if e['event']=='started':
                assert label not in started;started[label]=e;live.add(label)
                assert commands[label]['pid']==e['pid'] and commands[label]['argv'][0]==str(ROOT/r['binaries'][e['variant']]['path'])
            elif e['event']=='phase':
                assert label in live and e['phase']=='locked' and e['pid']==started[label]['pid'];phases[label]=e
            elif e['event']=='kernel-locks-held':
                assert len(live)==2 and set(live)<=set(phases)
                assert e['names']==['state.lock','operation.lock']
                assert {started[a]['variant']for a in live}=={'current','candidate'}
            else:
                assert e['event']=='finished' and label in live and label not in returned;returned.add(label);live.remove(label)
                c=commands[label];assert e['pid']==c['pid'] and e['exitCode']==c['exitCode'] and c['ownedGroupAbsent']
                for stream in ['stdout','stderr']:assert sha(RUN/(label+'.'+stream))==c[stream+'Sha256']
                rows=[json.loads(l)for l in(RUN/(label+'.stdout')).read_text().splitlines()]
                result=next((a['outcome']for a in rows if a['event']=='result'),None)
                assert e['outcome']==result
                if c['intentionalKill']:
                    assert c['exitCode']==-9 and result is None and label in phases;terminations+=1
                else:
                    assert c['exitCode']==0 and result is not None;results+=1;successes+=int(result['ok'])
                assert all(a['pid']==c['pid']for a in rows)
        assert not live and set(started)==returned
        for v in s['views']:
            p=RUN/v['image'];assert sha(p)==v['sha256'];image_count+=1
        last=s['views'][-1];assert image(RUN/'work'/s['fixture'])==json.loads((RUN/last['image']).read_text())
    assert (terminations,results,successes)==(3,9,6)
    def view(scenario,label):
        ref=next(v for v in scenarios[scenario]['views']if v['label']==label);return ref,json.loads((RUN/ref['image']).read_text())
    def identical(scenario,a,b):assert view(scenario,a)[0]['sha256']==view(scenario,b)[0]['sha256']
    def contents(state):return{bytes.fromhex(p).decode():bytes.fromhex(v['contentHex'])for p,v in state.items()if v['kind']=='file'}
    def marker(state):
        entries=[(p,b)for p,b in contents(state).items()if p.endswith('/root-identity.json')];assert len(entries)==1
        return entries[0]
    one='candidate-first-current-completes';assert all(v['ok']for v in scenarios[one]['results'].values())
    identical(one,'one-current-returned','one-candidate-returned')
    name,raw=marker(view(one,'one-current-returned')[1]);assert json.loads(raw)['schema']==1
    two='current-dies-candidate-completes';assert all(v['ok']for v in scenarios[two]['results'].values())
    assert not any(p.endswith('/root-identity.json')for p in contents(view(two,'two-current-terminated')[1]))
    marker(view(two,'two-candidate-returned')[1]);identical(two,'two-candidate-returned','two-reopened')
    three='both-die-old-footprint-remains'
    assert all(not v['ok']and v['unassociated']for v in scenarios[three]['results'].values())
    identical(three,'three-both-paused','three-terminated');identical(three,'three-terminated','three-lookup-result');identical(three,'three-lookup-result','three-retry-result')
    files=contents(view(three,'three-terminated')[1]);assert sorted(p.rsplit('/',1)[1]for p in files if p.startswith('host/'))==['operation.lock','state.lock']
    four='current-first-candidate-retries';a=scenarios[four]['results'];assert not a['first']['ok']and a['first']['unassociated']and a['current']['ok']and a['retry']['ok']
    identical(four,'four-current-paused','four-candidate-refused');identical(four,'four-current-returned','four-candidate-retried')
    report=dict(schema=1,sourceRevision=r['sourceRevision'],scenarios=4,commands=12,intentionalTerminations=3,
        ordinaryAPIResults=9,successfulOrdinaryResults=6,refusedOrdinaryResults=3,imagesVerified=image_count,finalPrivateFixturesVerified=4,
        findings=['The current-source and private-candidate initializers can hold different kernel locks simultaneously;shared Association format does not imply shared lock exclusion.',
            'A current initializer can publish while a candidate is paused;candidate double-read accepts the existing record without rewriting.',
            'A candidate already admitted before the old footprint appears can finish after current-source termination;this is not fresh adoption of unknown state.',
            'If both die before registration,the old operation.lock remains;fresh candidate lookup/retry refuse unchanged.',
            'Current-first registration blocks a fresh candidate as unassociated;after current completion,candidate retry accepts the published record without rewriting.'],
        limits=['This checker verifies retained source/result/postimages;separate initializer_conformance.py compares formal mixed traces.',
            'Two copied-source protocol variants at the same pinned source,not independently qualified released engine versions.',
            'Four controlled same-root schedules;not general linearizability,all crash points,root replacement,malicious metadata or supported-platform qualification.',
            'Provided host Dir and selected association initializer chain,not Engine/CLI operation,project publication or recovery.',
            'OS group/lock observations are historical and do not authorize later PID actions. No Rust build or baseline repetition was performed.'])
    (ROOT/'applications/empack/initializer-mixed-observations.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
