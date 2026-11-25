"""Read byte-bound native state; inputs contain actions, never native after-values."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
CAP=ROOT/'applications/evidence/empack-subscribed-flow-20261125T222928929810Z'
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
LABELS=['subscribe','offer-a-preview','observe-a','install-signed-a','player-edit',
        'offer-b-preview','observe-b','install-b-preview','missing-input-b','install-signed-b',
        'check-b','ensure-old-consumer','rollback-a','stale-offer-a','invalid-signature','check-rollback']
OPS=['enroll','previewA','observeA','installA','playerEdit','previewB','observeB','previewInstallB',
     'missingInputB','installB','checkB','ensureOld','rollbackA','staleA','badSignature','checkRollback']


def raw(item):
    value=bytes.fromhex(item['bytesHex'])
    assert len(value)==item['bytes'] and hashlib.sha256(value).hexdigest()==item['sha256']
    return value


def body(image,path):
    return json.loads(raw(image[path])) if path in image else None


def packets(rows=None,edit=None):
    rows=rows if rows is not None else load(CAP/'commands.json')
    edit=edit if edit is not None else load(CAP/'player-edit.json')
    setup=load(CAP/'setup.json');exports=setup['exports']
    public=load(CAP/'public-context.json')
    ids={v['digest']:i for i,v in enumerate(exports.values(),1)}
    assert list(exports)==['a','b'] and len(ids)==2
    channels={label:bytes.fromhex(load(CAP/('channel-'+label+'.json'))['payload']) for label in ['a','b']}
    payloads={hashlib.sha256(b).hexdigest():i for i,b in enumerate(channels.values(),1)}
    seedA=next(f for f in exports['a']['files'] if f['policy']=='seed')['sha256']
    managed={next(f for f in exports[label]['files'] if f['policy']=='managed')['sha256']:i for i,label in enumerate(['a','b'],1)}
    expected=[]
    for label in LABELS:
        if label=='player-edit':image=edit['after'];exit_code=0
        else:
            command=next(r for r in rows if r['id']==label)
            image=command['after'];exit_code=command['exitCode']
        sub=body(image,'.empack/subscription.json');completed=body(image,'.empack/instance.json')
        enrolled=int(bool(sub and sub['keys']))
        if sub:
            assert sub['keys']==[public['publicKey']]
            assert sub['pack']==exports['a']['pack'] and sub['channel']=='stable'
            assert sub['url']=='https://publisher.invalid/channels/stable.json'
        floor=sub.get('floor') if sub else None
        sequence=floor['sequence'] if floor else 0
        payload=payloads[floor['payload']] if floor else 0
        if floor:
            assert floor['pack']==exports['a']['pack'] and floor['origin']=='https://publisher.invalid' and floor['channel']=='stable'
            saved=bytes.fromhex(json.loads(sub['observed'])['payload'])
            assert hashlib.sha256(saved).hexdigest()==floor['payload']
        selected=ids[completed['release']] if completed else 0
        if completed:
            assert sub and completed['root']==sub['root']
            assert completed['pack']==exports['a']['pack'] and completed['layout']=='game' and completed['side']=='client'
            descriptor=image['.empack/releases/'+completed['release']+'.json']
            assert descriptor['sha256']==completed['release']
        physical=managed[image['game/payload.txt']['sha256']] if 'game/payload.txt' in image else 0
        if 'game/config/rules.txt' in image:
            seed=1 if image['game/config/rules.txt']['sha256']==seedA else 2
            if seed==2:assert raw(image['game/config/rules.txt'])==b'own player setting\n'
        else:seed=0
        note=int('game/note.txt' in image)
        if note:assert raw(image['game/note.txt'])==b'own unowned note\n'
        expected.append([enrolled,sequence,payload,selected,physical,seed,note,exit_code])
    inputs=dict(schema=1,profile='local-signed-inputs-current-engine/1',operations=OPS,
                channelWitness='native-valid-A-B-forged-B-and-stale-A')
    return inputs,expected
