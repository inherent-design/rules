"""Retained-data/proof replay. Never run empack, OpenSSL, network, or read a key."""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from observations import ROOT,CAP,LABELS,OPS,load,sha,raw,packets

HERE=Path(__file__).resolve().parent
FORMAL=ROOT/'.build/empack-subscribed-formal'
write=lambda p,x:p.write_text(json.dumps(x,indent=2)+'\n')


def evidence(owner_local):
    unavailable=[];rows=load(CAP/'commands.json');setup=load(CAP/'setup.json');receipt=load(CAP/'receipt.json');context=load(CAP/'public-context.json')
    assert len(rows)==receipt['commands']==24 and receipt['nativeCommands']==18
    assert receipt['complete'] and receipt['allRecordedGroupsAbsent']
    assert sha(CAP/'setup.json')==receipt['setupSha256']
    assert sha(CAP/'probe.py')==receipt['producerSha256']==setup['producerSha256']
    assert sha(CAP/'public-context.json')==receipt['publicContextSha256']
    assert sha(ROOT/setup['priorCapture']/'progress.json')==setup['priorProgressSha256']
    assert hashlib.sha256(bytes.fromhex(context['publicKey'])).hexdigest()==context['keyFingerprint']
    for row in rows:
        assert row['groupAbsent'] and not row['timedOut']
        assert row['exitCode']==(1 if row['id'] in ['missing-input-b','stale-offer-a','invalid-signature'] else 0)
        for name in ['stdout','stderr']:assert sha(CAP/(row['id']+'.'+name))==row['streams'][name]
        if row['kind']=='openssl':assert row['before'] is None and row['after'] is None
        else:
            assert row['argv'][0]==setup['binary']
            assert row['argv'][row['argv'].index('--state-dir')+1]==setup['work']+'/state'
            assert row['argv'][row['argv'].index('--cache-dir')+1]==setup['work']+'/cache'
        for image in [row['before'],row['after']]:
            if image:
                assert not any('private-keys' in p for p in image)
                for item in image.values():
                    if 'bytesHex' in item:raw(item)
    # Bind the adapter's event names to actual native commands/selected inputs.
    recipient=[r for r in rows if r['kind']=='empack' and r['root']==setup['work']+'/recipient']
    assert [r['id'] for r in recipient]==[n for n in LABELS if n!='player-edit']
    prefix=lambda r:r['argv'][r['argv'].index('--yes')+1:]
    channel=lambda n:setup['work']+'/channels/channel-'+n+'.json'
    staged=lambda n:setup['work']+'/publisher/dist/releases/'+setup['exports'][n]['digest']+'/release.json'
    expected={
      'subscribe':['instance','subscribe','--pack',setup['exports']['a']['pack'],'--channel','stable','https://publisher.invalid/channels/stable.json','--key',context['publicKey']],
      'offer-a-preview':['instance','update','--channel-file',channel('a')],
      'observe-a':['instance','check-updates',channel('a')],
      'install-signed-a':['instance','update',staged('a'),'--apply'],
      'offer-b-preview':['instance','update','--channel-file',channel('b')],
      'observe-b':['instance','check-updates',channel('b')],
      'install-b-preview':['instance','update',staged('b')],
      'install-signed-b':['instance','update',staged('b'),'--apply'],
      'check-b':['instance','check','--json','--quiet'],
      'ensure-old-consumer':['instance','ensure',setup['work']+'/exports/a/release.json','--sha256',setup['exports']['a']['digest']],
      'rollback-a':['instance','rollback',setup['exports']['a']['digest'],'--assets',setup['work']+'/exports/a'],
      'stale-offer-a':['instance','check-updates',channel('a')],
      'invalid-signature':['instance','check-updates',setup['work']+'/channels/invalid-signature.json'],
      'check-rollback':['instance','check','--json','--quiet']}
    key=next(f['key'] for f in setup['exports']['b']['files'] if f['policy']=='managed')
    expected['missing-input-b']=['instance','update',staged('b'),'--apply','--file',key+'='+setup['work']+'/absent-input.txt']
    for r in recipient:assert prefix(r)==expected[r['id']]
    edit=load(CAP/'player-edit.json')
    for left,right in zip(recipient,recipient[1:]):
        if left['id']=='install-signed-a':assert left['after']==edit['before'] and right['before']==edit['after']
        else:assert left['after']==right['before']
    readonly={'offer-a-preview','offer-b-preview','install-b-preview','missing-input-b','check-b','ensure-old-consumer','stale-offer-a','invalid-signature','check-rollback'}
    for row in recipient:
        if row['id'] in readonly:assert row['before']==row['after']
        if row['id'] not in ['subscribe','offer-a-preview','observe-a','install-signed-a']:
            for p in ['game/config/rules.txt','game/note.txt']:assert row['after'][p]==edit['after'][p]
    # Offer saves change only subscription bytes; installation/rollback keep them.
    for row in recipient:
        changed={p for p in row['before'].keys()|row['after'].keys() if row['before'].get(p)!=row['after'].get(p)}
        if row['id'] in ['observe-a','observe-b']:assert changed=={'.empack/subscription.json'}
        if row['id'] in ['install-signed-a','install-signed-b','rollback-a']:
            assert row['before']['.empack/subscription.json']==row['after']['.empack/subscription.json']
    for label in ['a','b']:
        channel_envelope=load(CAP/('channel-'+label+'.json'));payload=bytes.fromhex(channel_envelope['payload']);document=json.loads(payload)
        envelope=load(CAP/('release-'+label+'.envelope.json'));release_payload=bytes.fromhex(envelope['payload']);release=json.loads(release_payload)
        assert channel_envelope['schema']==envelope['schema']==1
        assert channel_envelope['kind']=='channel' and envelope['kind']=='release'
        assert hashlib.sha256(release_payload).hexdigest()==setup['exports'][label]['digest']==document['release']['id']
        assert release['files']==setup['exports'][label]['files'] and document['release']['maximum_bytes']==(CAP/('release-'+label+'.envelope.json')).stat().st_size
        assert document['pack']==release['pack']==setup['exports'][label]['pack']
        assert document['sequence']==(1 if label=='a' else 2)
        assert document['release']['url']=='https://publisher.invalid/releases/'+document['release']['id']+'/release.json'
        assert channel_envelope['signatures'][0]['key']==context['keyFingerprint']==envelope['signatures'][0]['key']
        assert (CAP/('verify-channel-'+label+'.stdout')).read_text().strip()=='Signature Verified Successfully'
        original=ROOT/setup['priorCapture']/('release-'+label+'.json')
        assert original.read_bytes()==release_payload
    forged=load(CAP/'invalid-signature.json');valid=load(CAP/'channel-b.json')
    assert forged['payload']==valid['payload'] and forged['signatures'][0]['key']==valid['signatures'][0]['key']
    assert forged['signatures'][0]['signature']!=valid['signatures'][0]['signature']
    for name in ['check-b','check-rollback']:
        value=load(CAP/(name+'.json'));assert value==json.loads((CAP/(name+'.stdout')).read_text())
        assert value['complete'] and value['verified_files']==1 and value['player_owned_entries']==1 and value['verified_overrides']==0
    if owner_local:
        # Public outputs and stat-only key permissions. NEVER open private seed/DER.
        for name,field in [('binary','binarySha256'),('openssl','opensslSha256')]:
            p=Path(setup[name])
            if p.exists():assert sha(p)==setup[field]
            else:unavailable.append(str(p))
        import importlib.util
        spec=importlib.util.spec_from_file_location('frozen_subscribed',CAP/'probe.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
        p=Path(setup['work'])/'recipient'
        if p.exists():assert helper.image(p)==recipient[-1]['after']
        else:unavailable.append(str(p))
        keydir=Path(setup['work'])/'private-keys'
        if keydir.exists():
            assert stat.S_IMODE(keydir.stat().st_mode)==0o700
            assert stat.S_IMODE((keydir/'publisher.key').stat().st_mode)==stat.S_IMODE((keydir/'publisher.der').stat().st_mode)==0o600
        else:unavailable.append(str(keydir)+' (permissions only)')
    else:unavailable += ['owner-local executable identities','latest recipient image','private-key permission observations']
    for source in load(ROOT/'applications/sources/empack-subscribed-flow-selections.json'):
        p=ROOT/source['cache']
        if owner_local and p.exists():
            data=p.read_bytes();assert sha(p)==source['sha256']
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==source['gitBlob']
        else:unavailable.append(str(p))
    return unavailable


def bend(inputs,expected,env,tool):
    defs=['def e0() -> Nat: 0n','def f0() -> Nat: 0n','def h0() -> Nat: 0n','def i0() -> Nat: 0n','def p0() -> Nat: 0n','def s0() -> Nat: 0n','def n0() -> Nat: 0n']
    lines=[]
    for k,_ in enumerate(inputs['operations'],1):
        code=str(k-1)+'n';j=str(k-1)
        expr={'e':f'P.enrolled({code},e{j}())','f':f'P.floor({code},f{j}(),h{j}())',
              'h':f'P.floor_payload({code},f{j}(),h{j}())','i':f'P.installed({code},i{j}())',
              'p':f'P.installed({code},p{j}())','s':f'P.seed({code},s{j}())','n':f'P.note({code},n{j}())'}
        defs += [f'def {name}{k}() -> Nat: {value}' for name,value in expr.items()]
        scalars=[f'{name}{k}()' for name in ['e','f','h','i','p','s','n']]+[f'P.exit({code},f{j}(),h{j}())']
        lines.append('"[" ++ '+' ++ "," ++ '.join('Nat.show('+s+')' for s in scalars)+' ++ "]"')
    p=FORMAL/'Replay.bend';p.write_text('import ../../applications/empack/subscribed-flow/SubscribedFlow.bend as P\nimport Base\n'+'\n'.join(defs)+'\ndef main() -> IO(Unit):\n  IO.write("[" ++ '+' ++ "," ++ '.join(lines)+' ++ "]")\n')
    actual=subprocess.run([tool,str(p)],cwd=ROOT,env=env,capture_output=True,text=True,check=True)
    assert json.loads(actual.stdout)==expected


def main():
    assert sys.argv[1:] in [[],['--public-only']]
    unavailable=evidence(not sys.argv[1:]);inputs,observed=packets()
    write(CAP/'model-input.json',inputs);write(CAP/'observed-model-values.json',observed)
    gate=load(CAP/'proof-gate.json');assert gate['observedExitCode']==0
    for p,h in gate['sourceSha256'].items():assert sha(ROOT/p)==h
    env={**os.environ,'LEAN_PATH':str(FORMAL),'BEND_NO_TELEMETRY':'1'}
    lean=os.environ.get('LEAN','lean');b=os.environ.get('BEND','bend')
    command=[lean,'--run','applications/empack/subscribed-flow/SubscribedFlowCase.lean']
    actual=json.loads(subprocess.check_output(command+[str(CAP/'model-input.json')],cwd=ROOT,env=env,text=True));assert actual==observed
    bend(inputs,observed,env,b)
    controls=[]
    for name,row,column,value in [('preview-persisted',1,1,1),('offer-installed',2,3,1),('new-offer-replaced-old-install',6,3,2),
        ('failed-acquisition-lowered-floor',8,1,1),('failed-acquisition-replaced-payload',8,4,2),('apply-lost-seed',9,5,1),
        ('apply-lost-unowned',9,6,0),('old-consumer-reverted',11,3,1),('rollback-lowered-floor',12,1,1),
        ('rollback-missed-payload',12,4,2),('stale-accepted',13,7,0),('forged-accepted',14,7,0)]:
        altered=copy.deepcopy(observed);altered[row][column]=value;assert actual!=altered;controls.append(name)
    for name,change in [('schema',lambda x:x.update(schema=2)),('profile',lambda x:x.update(profile='arbitrary-http-production')),
        ('crypto-witness',lambda x:x.update(channelWitness='nonzero-signatures')),
        ('order',lambda x:x['operations'].__setitem__(2,'installA')),('missing-event',lambda x:x['operations'].pop())]:
        altered=copy.deepcopy(inputs);change(altered);p=FORMAL/(name+'.json');write(p,altered)
        result=subprocess.run(command+[str(p)],cwd=ROOT,env=env,text=True,capture_output=True)
        assert result.returncode==2 and 'research' in result.stderr;controls.append(name)
    for name,kind in [('raw-root-binding','root'),('raw-seed-preservation','seed'),('raw-exit-status','exit')]:
        rows=load(CAP/'commands.json');row=next(r for r in rows if r['id']=='install-signed-b')
        if kind=='root':
            item=row['after']['.empack/instance.json'];j=json.loads(raw(item));j['root']='foreign-root';value=json.dumps(j).encode();item.update(bytesHex=value.hex(),bytes=len(value),sha256=hashlib.sha256(value).hexdigest())
        elif kind=='seed':row['after']['game/config/rules.txt']['sha256']='0'*64
        else:row['exitCode']=1
        try:_,altered=packets(rows)
        except AssertionError:pass
        else:assert actual!=altered
        controls.append(name)
    paths=[p for p in CAP.iterdir() if p.is_file() and p.name not in ['basis.json','conformance.json']]+[p for p in HERE.iterdir() if p.is_file()]
    paths += [ROOT/'applications/empack/Channels.lean',ROOT/'applications/empack/Channels.bend',ROOT/'applications/sources/empack-subscribed-flow-selections.json']
    write(CAP/'basis.json',{str(p.relative_to(ROOT)):sha(p) for p in paths})
    result=dict(schema=1,replayProfile='public-retained-only' if sys.argv[1:] else 'owner-local',nativeCommands=18,opensslCommands=6,joinedWorkflows=1,recipientNativeCommands=15,explicitPlayerEdits=1,traceRows=16,dualScalarComparisons=128,leanLaws=21,bendLaws=16,controls=controls,basisFiles=len(paths),unavailableArtifacts=unavailable,
                limits=['Authored local signed channel fixtures and native staged releases; no release-channel-create/HTTP/deployment/runtime/game/concurrency/crash qualification.',
                        'Existing Channels models supply signature/floor admission; witnesses are closed native/OpenSSL observations, not a cryptographic proof.',
                        'Successful commits and selected explicit refusals on one Mac fixture; no arbitrary graph, key rotation, malformed saved record or failed native writer qualification.',
                        'Replay never executes empack/OpenSSL or reads private key bytes.'])
    write(CAP/'conformance.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
