"""Retained native forensic comparison using the existing Channels models.

No empack/OpenSSL execution, key reads, or patched engine. Only cached-current
admission is compared with CLI previews. Exact-saved is a separate proposal;
the existing research driver's selected-floor wrapper is not a native guard.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
CAP=ROOT/'applications/evidence/empack-saved-offer-20261125T225128247208Z'
PRIOR=ROOT/'applications/evidence/empack-subscribed-flow-20261125T222928929810Z'
FORMAL=ROOT/'.build/empack-saved-offer-formal'
HERE=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,x:p.write_text(json.dumps(x,indent=2)+'\n')


def decoded(item):
    raw=bytes.fromhex(item['bytesHex']);assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
    return json.loads(raw)


def evidence(owner_local):
    setup=load(CAP/'setup.json');receipt=load(CAP/'receipt.json');rows=load(CAP/'commands.json');edits=load(CAP/'authored-edits.json');unavailable=[]
    assert receipt['complete'] and receipt['commands']==len(rows)==9 and receipt['authoredEdits']==len(edits)==3 and receipt['allRecordedGroupsAbsent']
    assert sha(CAP/'probe.py')==receipt['producerSha256']==setup['producerSha256']
    assert sha(CAP/'setup.json')==receipt['setupSha256']
    assert sha(PRIOR/'receipt.json')==setup['priorReceiptSha256'] and sha(PRIOR/'public-context.json')==setup['publicContextSha256']
    for n,h in setup['signedInputs'].items():assert sha(PRIOR/n)==h
    expected={'enroll':0,'observe-valid-b':0,'consistent-preview':0,'mismatched-preview':0,'mismatched-apply':0,'mismatched-check':0,'same-sequence-preview':1,'explicit-valid-observation-repair':0,'repaired-preview':0}
    assert [r['id'] for r in rows]==list(expected)
    for r in rows:
        assert r['exitCode']==expected[r['id']] and r['groupAbsent'] and not r['timedOut']
        assert r['argv'][0]==setup['binary']
        for field,tail in [('--state-dir','/state'),('--cache-dir','/cache'),('--workdir','/recipient')]:assert r['argv'][r['argv'].index(field)+1]==setup['work']+tail
        for n in ['stdout','stderr']:assert sha(CAP/(r['id']+'.'+n))==r['streams'][n]
        for image in [r['before'],r['after']]:
            for item in image.values():
                if 'bytesHex' in item:
                    b=bytes.fromhex(item['bytesHex']);assert len(b)==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256']
        if r['id'] in ['consistent-preview','mismatched-preview','mismatched-check','same-sequence-preview','repaired-preview']:assert r['before']==r['after']
    for e in edits:
        assert e['authored']
        changed={p for p in e['before'].keys()|e['after'].keys() if e['before'].get(p)!=e['after'].get(p)}
        assert changed=={'.empack/subscription.json'}
        before=decoded(e['before']['.empack/subscription.json']);after=decoded(e['after']['.empack/subscription.json'])
        assert {k:v for k,v in before.items() if k!='floor'}=={k:v for k,v in after.items() if k!='floor'}
    # Exact event lineage, including explicitly authored mutations between calls.
    joins={2:edits[0],5:edits[1],6:edits[2]}
    for i,(left,right) in enumerate(zip(rows,rows[1:])):
        if i in joins:assert left['after']==joins[i]['before'] and joins[i]['after']==right['before']
        else:assert left['after']==right['before']
    signed=setup['work']+'/signed/'
    pub=load(PRIOR/'public-context.json')['publicKey'];pack=load(PRIOR/'setup.json')['exports']['b']['pack']
    args={
      'enroll':['instance','subscribe','--pack',pack,'--channel','stable','https://publisher.invalid/channels/stable.json','--key',pub],
      'observe-valid-b':['instance','check-updates',signed+'channel-b.json'],
      'explicit-valid-observation-repair':['instance','check-updates',signed+'channel-b.json'],
      'mismatched-apply':['instance','update',signed+'release.json','--apply'],
      'mismatched-check':['instance','check','--json','--quiet']}
    for r in rows:
        actual=r['argv'][r['argv'].index('--yes')+1:]
        assert actual==args.get(r['id'],['instance','update',signed+'release.json'])
    applied=rows[4];before=decoded(applied['before']['.empack/subscription.json']);after=decoded(applied['after']['.empack/subscription.json'])
    assert before==after and before['floor']['sequence']==1
    observed=json.loads(before['observed']);assert json.loads(bytes.fromhex(observed['payload']))['sequence']==2
    installed=decoded(applied['after']['.empack/instance.json']);assert installed['release']==setup['selectedRelease'] and installed['root']==after['root']
    release=json.loads(bytes.fromhex(load(PRIOR/'release-b.envelope.json')['payload']))
    for f in release['files']:
        item=applied['after']['game/'+f['destination']];assert item['sha256']==f['sha256'] and item['bytes']==f['bytes']
    checked=load(CAP/'mismatched-check.json');assert checked==json.loads((CAP/'mismatched-check.stdout').read_text())
    assert checked['complete'] and checked['release']==setup['selectedRelease']
    subscription_finding=next(f for f in checked['findings'] if f['subject']=='Subscription state')
    assert subscription_finding['state']=='passed'
    repair=rows[7];changed={p for p in repair['before'].keys()|repair['after'].keys() if repair['before'].get(p)!=repair['after'].get(p)}
    assert changed=={'.empack/subscription.json'} and decoded(repair['after']['.empack/subscription.json'])['floor']['sequence']==2
    # Reuse exact earlier kernel-checked models; the decoder is executed fresh.
    proof=load(PRIOR/'proof-gate.json');assert proof['observedExitCode']==0
    for p in ['applications/empack/Channels.lean','applications/empack/Channels.bend']:assert sha(ROOT/p)==proof['sourceSha256'][p]
    for source in load(ROOT/'applications/sources/empack-saved-offer-selections.json'):
        p=ROOT/source['cache']
        if owner_local and p.exists():
            b=p.read_bytes();assert sha(p)==source['sha256']
            assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==source['gitBlob']
        else:unavailable.append(str(p))
    if owner_local:
        binary=Path(setup['binary']);root=Path(setup['work'])/'recipient'
        if binary.exists():assert sha(binary)==setup['binarySha256']
        else:unavailable.append(str(binary))
        if root.exists():
            spec=importlib.util.spec_from_file_location('saved_offer_frozen',CAP/'probe.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);assert m.image(root)==rows[-1]['after']
        else:unavailable.append(str(root))
    else:unavailable+=['installed executable identity','latest recipient image']
    return unavailable


def packets():
    rows=load(CAP/'commands.json');context=load(PRIOR/'public-context.json');cases=[];native=[]
    hashes={hashlib.sha256(bytes.fromhex(load(PRIOR/('channel-'+name+'.json'))['payload'])).hexdigest():i for i,name in enumerate(['a','b'],1)}
    binding=dict(pack=1,origin=1,channel=1)
    for label in ['consistent-preview','mismatched-preview','same-sequence-preview','repaired-preview']:
        r=next(r for r in rows if r['id']==label);saved=decoded(r['before']['.empack/subscription.json'])
        assert saved['keys']==[context['publicKey']] and saved['url']=='https://publisher.invalid/channels/stable.json'
        env=json.loads(saved['observed']);assert env==load(PRIOR/'channel-b.json')
        assert env['signatures'][0]['key']==context['keyFingerprint']
        document=json.loads(bytes.fromhex(env['payload']));f=saved['floor']
        assert document['pack']==f['pack']==saved['pack'] and document['channel']==f['channel']==saved['channel']=='stable' and f['origin']=='https://publisher.invalid'
        floor=dict(binding=binding,sequence=f['sequence'],payload=hashes[f['payload']])
        request=dict(operation='channel',keys=[1],enrollmentShape=True,envelopeShape=True,documentShape=True,
          signatures=[dict(key=1,algorithmKnown=True,canonical=True,valid=True)],expected=binding,document=binding,
          authoredBounds=True,prereleaseAdmitted=True,sequence=document['sequence'],payload=hashes[hashlib.sha256(bytes.fromhex(env['payload'])).hexdigest()],floor=floor)
        cases.append(dict(recordShape=True,observed=request,stored=floor,selected=floor))
        native.append(r['exitCode']==0)
    return dict(schema=1,cases=[],saved=cases),native


def bend_requests(inputs):
    def binding(b):return 'C.Binding{'+','.join(str(b[k])+'n' for k in ['pack','origin','channel'])+'}'
    def floor(f):return 'C.Floor{'+binding(f['binding'])+','+str(f['sequence'])+'n,'+str(f['payload'])+'n}'
    out=[]
    for s in inputs['saved']:
        r=s['observed'];out.append('C.Request{Con{1n,Nil{}},True{},True{},True{},Con{C.Signature{1n,True{},True{},True{}},Nil{}},'+binding(r['expected'])+','+binding(r['document'])+',True{},True{},'+str(r['sequence'])+'n,'+str(r['payload'])+'n,Some{'+floor(r['floor'])+'}}')
    return out


def main():
    assert sys.argv[1:] in [[],['--public-only']]
    unavailable=evidence(not sys.argv[1:]);inputs,native=packets();FORMAL.mkdir(parents=True,exist_ok=True)
    write(CAP/'model-input.json',inputs);write(CAP/'observed-admission.json',native)
    env={**os.environ,'LEAN_PATH':str(FORMAL),'BEND_NO_TELEMETRY':'1'};lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend')
    artifact=FORMAL/'applications/empack/Channels.olean';artifact.parent.mkdir(parents=True,exist_ok=True)
    compile_command=[lean,'-DwarningAsError=true','-o',str(artifact),'applications/empack/Channels.lean']
    compiled=subprocess.run(compile_command,cwd=ROOT,env=env,capture_output=True,text=True);assert compiled.returncode==0,compiled.stdout+compiled.stderr
    formal_build=dict(sourceSha256=sha(ROOT/'applications/empack/Channels.lean'),artifactSha256=sha(artifact),command=compile_command,observedExitCode=compiled.returncode,
                      tools={name:dict(path=tool,sha256=sha(Path(tool)) if Path(tool).is_file() else None) for name,tool in [('lean',lean),('bend',bend)]})
    command=[lean,'--run','applications/empack/ChannelsCase.lean']
    run=subprocess.run(command+[str(CAP/'model-input.json')],cwd=ROOT,env=env,capture_output=True,text=True,check=True)
    values=json.loads(run.stdout);current=[r.split('/')[2]=='1' for r in values['saved']];proposed=[r.split('/')[3]=='1' for r in values['saved']]
    assert current==native==[True,True,False,True] and proposed==[True,False,False,True]
    # Wrapper columns selectedGuard/currentSelectionChecks are NOT native local-
    # release guards. Do not count them as observed fields or whole-flow proof.
    expressions=[]
    for r in bend_requests(inputs):expressions += ['Bool.show(C.cached_current(True{},True{},'+r+'))','Bool.show(C.cached_exact(True{},True{},'+r+'))']
    p=FORMAL/'Replay.bend';p.write_text('import ../../applications/empack/Channels.bend as C\nimport Base\ndef main() -> IO(Unit):\n  IO.write('+' ++ "\\n" ++ '.join(expressions)+' ++ "\\n")\n')
    result=subprocess.run([bend,str(p)],cwd=ROOT,env=env,capture_output=True,text=True,check=True)
    assert result.stdout.splitlines()==[str(v) for pair in zip(current,proposed) for v in pair]
    controls=[]
    for name,index in [('mismatch-refused-by-current',1),('same-sequence-accepted',2),('consistent-refused',0),('repair-refused',3)]:
        changed=list(native);changed[index]=not changed[index];assert current!=changed;controls.append(name)
    for name,mutate in [('schema',lambda x:x.update(schema=2)),
                        ('record-floor-not-request-floor',lambda x:x['saved'][1]['observed'].update(floor={**x['saved'][1]['observed']['floor'],'sequence':2})),
                        ('unknown-key-witness',lambda x:x['saved'][0]['observed'].update(keys=[3]))]:
        changed=copy.deepcopy(inputs);mutate(changed);p=FORMAL/(name+'.json');write(p,changed)
        outcome=subprocess.run(command+[str(p)],cwd=ROOT,env=env,capture_output=True,text=True);assert outcome.returncode==2;controls.append(name)
    paths=[p for p in CAP.iterdir() if p.is_file() and p.name not in ['basis.json','conformance.json']]+[p for p in HERE.iterdir() if p.is_file()]
    paths += [ROOT/'applications/empack/Channels.lean',ROOT/'applications/empack/Channels.bend',ROOT/'applications/empack/ChannelsCase.lean']
    paths += [ROOT/'applications/sources/empack-saved-offer-selections.json']
    write(CAP/'basis.json',{str(p.relative_to(ROOT)):sha(p) for p in paths})
    report=dict(schema=1,replayProfile='public-retained-only' if sys.argv[1:] else 'owner-local',nativeCommands=9,authoredEdits=3,previewBoundaries=4,distinctPairProfiles=3,dualNativeAdmissionValues=4,modelOnlyProposedValues=4,newFormalModules=0,reusedModels=['Channels.lean','Channels.bend'],controls=controls,basisFiles=len(paths),unavailableArtifacts=unavailable,
        currentAdmission=current,proposedExactSavedAdmission=proposed,formalBuild=formal_build,
        observedPublication='Native application installed signed release B while saved floor 1 and observed envelope B/sequence 2 remained. Instance checking reported complete and subscription consistency. Explicit observation of valid B repaired only the subscription.',
        limits=['Authored corrupt inputs,not normal producer/crash-generated state or remoteattack. No full-engine patch or fault-origin reproduction.',
                'Only cachedCurrent admission is matched to native preview status. Proposed exactness is model-only;selectedGuard wrapper fields are not exercised by this local-release CLI route.',
                'Publication/check/repair effects are independently captured,not proved by the cached-admission predicate. No HTTP/runtime/world/platform or writer-failure qualification.'])
    write(CAP/'conformance.json',report);print(json.dumps(report,indent=2))


if __name__=='__main__':main()
