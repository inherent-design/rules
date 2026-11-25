#!/usr/bin/env python3
"""Read-only projection of frozen CLI streams and independent filesystem images."""
import hashlib
import json
from pathlib import Path

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def project(run, overrides=None):
    overrides = overrides or {}
    def load(name):
        return overrides[name] if name in overrides else json.loads((run/name).read_text())
    def read_stream(name):
        return overrides[name] if name in overrides else (run/name).read_text()
    assets=load('assets.json')
    # JSON author preserves first,second order, but never trust iteration for identity.
    digests={assets['first']['sha256']:1,assets['second']['sha256']:2}
    initial=load('baseline.json')['publicOperation']
    retained=load('partial-retained-list.stdout')['operations'][0]
    state_at_report=[load(n) for n in ['pending-after.json','partial-retained-list-after.json']]
    def record_hash(image):
        found=[v['sha256'] for p,v in (image['state'] or {}).items()
               if p.startswith('pending-builds/') and p.count('/')==1 and p.endswith('.json')]
        assert len(found)<=1
        return found[0] if found else None
    hashes={record_hash(state_at_report[0]):1,record_hash(state_at_report[1]):2}
    assert len(hashes)==2 and None not in hashes
    ids={initial['id']:1,retained['id']:2}
    assert len(ids)==2
    assert [i['verification'] for i in initial['inputs']]==['not supplied; verification required']*2
    assert [i['verification'] for i in retained['inputs']]==['retained; verification required','not supplied; verification required']
    assert all(i['supplied_candidate'] is None for o in [initial,retained] for i in o['inputs'])

    def state(image):
        h=record_hash(image); revision=0 if h is None else hashes[h]
        store=image['state'] or {}
        def backing(name):
            p='pending-content/'+assets[name]['sha256']+'.blob'
            return digests.get(store.get(p,{}).get('sha256'),0)
        product=any(p.endswith('.mrpack') and p.startswith('dist/')for p in image['project'])
        return dict(record=revision,first=revision==2,second=False,firstBacking=backing('first'),secondBacking=backing('second'),published=product)

    commands=[]
    for phase in ['','partial-','retained-','finish-']:
        filename=phase+'commands.json'
        for c in load(filename):
            assert not c['timedOut'] and c['ownedGroupAbsent']
            for stream in ['stdout','stderr']:
                assert sha(run/(c['case']+'.'+stream))==c['streams'][stream]
            if phase=='' and c['case']!='pending':
                continue
            name=c['case']
            before=load('build-after.json' if name=='pending' else name+'-before.json')
            after=load(name+'-after.json')
            argv=c['argv'];start=argv.index('pending');args=argv[start+1:]
            action={'list':0,'show':1,'resume':3}[args[0]]
            if '--dry-run' in argv:action=2
            selected=0 if action==0 else ids[args[1]]
            files=[]
            for index,arg in enumerate(args):
                if arg!='--file':continue
                key,path=args[index+1].split('=',1)
                key={'locked:first:primary':0,'locked:second:primary':1}.get(key,9)
                local=Path(path).relative_to(run/'work/downloads').as_posix()
                content=digests.get(before['downloads'][local]['sha256'],0)
                files.append(dict(key=key,content=content))
            discovered=[]
            if action==3 and '--downloads-dir' in args:
                # Only direct regular children. Content equivalence, not names,
                # is projected; native scan counters remain a separate receipt.
                discovered=[digests.get(v['sha256'],0)for p,v in before['downloads'].items()
                            if '/' not in p and v['kind']=='file']
            err=read_stream(name+'.stderr')
            if c['exitCode']==0: code=6 if action==3 else 1 if action==2 else 0
            elif 'No pending operation matches this ID' in err:code=2
            elif 'Pending key' in err:code=3
            elif 'checksum does not match' in err:code=3 if files else 4
            elif 'continuation was saved' in err:code=5
            else:raise AssertionError((name,err))
            pre,post=state(before),state(after)
            expected='/'.join(str(v)for v in [code,post['record'],int(post['first']),int(post['second']),post['firstBacking'],post['secondBacking'],int(post['published'])])
            commands.append(dict(case=name,input=dict(state=pre,action=action,selected=selected,files=files,discovered=discovered),
                expected=expected,exitCode=c['exitCode'],changedScopes=[k for k in before if before[k]!=after[k]]))
    assert len(commands)==17
    return commands
