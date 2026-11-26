"""Retained source comparison and pure models; never compile/run Rust or OpenSSL."""
from pathlib import Path
import argparse
import ast
import copy
import hashlib
import json
import os
import subprocess

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
RUN=ROOT/'applications/evidence/empack-channel-publication-20261126T112857119598Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda b:hashlib.sha256(b).hexdigest()
compact=lambda d:json.dumps(d,separators=(',',':')).encode()


def inspect(public):
    receipt=json.loads((RUN/'receipt.json').read_text());crypto=json.loads((RUN/'crypto-verification.json').read_text())
    commands=json.loads((RUN/'commands.json').read_text());assert len(commands)==2 and receipt['records']==11
    for row in commands+crypto['commands']:
        assert row['ownedGroupAbsent'] and not row['timedOut']
        assert row['exitCode']==0 or (row in crypto['commands'] and row['exitCode']==1)
        for stream in row['streams'].values():assert sha(RUN/stream['file'])==stream['sha256']
    assert receipt['allOwnedGroupsAbsent'] and crypto['allOwnedGroupsAbsent']
    assert sha(RUN/'probe.py')==receipt['producerSha256']==sha(HERE/'probe.py')
    assert sha(RUN/'driver.rs')==receipt['driverSha256']==sha(HERE/'oracle.rs')
    assert sha(RUN/'crypto/producer.py')==crypto['producerSha256']==sha(HERE/'verify_crypto.py')
    assert sha(RUN/'observe.stdout')==crypto['observeSha256']
    prior=ROOT/receipt['priorCapture'];assert sha(prior/'receipt.json')==receipt['priorReceiptSha256']
    if not public:
        work=Path(receipt['work']);assert work.parent==Path('/private/tmp') and work.name.startswith('rules-empack-channel-publication-')
        assert sha(work/'main.rs')==receipt['generatedSha256'] and sha(work/'oracle')==receipt['binarySha256']
        assert sha(Path(receipt['compiler']['path']))==receipt['compiler']['sha256']
        for x in receipt['libraries'].values():assert sha(Path(x['path']))==x['sha256']
        for p,h in receipt['priorGenerated'].items():assert sha(prior/'work'/p)==h
        source=ROOT/'.build/empack-channel-producer-sources'/receipt['publisherGuard']['path']
        assert sha(source)==receipt['publisherGuard']['sha256']
        text=source.read_text();start=text.index('        ensure!(\n            channel.sequence > prior.sequence');end=text.index('\n        );',start)+len('\n        );');guard=text[start:end]
        assert digest(guard.encode())==receipt['publisherGuard']['cutSha256']
        tree=ast.parse((RUN/'probe.py').read_text());assignment=next(n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='wrapper' for t in n.targets))
        assert isinstance(assignment.value,ast.Call) and isinstance(assignment.value.func,ast.Attribute) and assignment.value.func.attr=='replace'
        wrapper=ast.literal_eval(assignment.value.func.value).replace('SOURCE_GUARD',guard)
        head=(prior/'work/main.rs').read_text();head=head[:head.rindex('include!(')];at=head.rindex('}')
        rebuilt=head[:at]+wrapper+head[at:]+'include!('+json.dumps(str(RUN/'driver.rs'))+');\n'
        assert digest(rebuilt.encode())==receipt['generatedSha256']
        assert sha(Path(crypto['tool']['path']))==crypto['tool']['sha256']
    return receipt,crypto,[json.loads(x) for x in (RUN/'observe.stdout').read_text().splitlines()]


def observe(rows,crypto):
    associations={(x['case'],x['role']):x['check'] for x in crypto['associations']}
    assert len(associations)==22 and len(crypto['checks'])==9
    by_label={x['label']:x for x in crypto['commands']}
    for identity,check in crypto['checks'].items():
        command=by_label[check['label']];assert check['verified']==(command['exitCode']==0)
        expected=b'Signature Verified Successfully' if check['verified'] else b'Signature Verification Failure'
        assert expected in (RUN/command['streams']['stdout']['file']).read_bytes()
    scenarios=[];outcomes=[]
    for row in rows:
        request=row['request'];seen=row['observed'];payloads={};envelopes={};proofs={}
        for role in ['prior','candidate']:
            document=request[role];assert set(document)=={'schema','pack','channel','sequence','release','minimum_engine'}
            assert document['schema']==2 and document['pack']=='fixture-pack' and document['channel']=='stable'
            assert document['release']['url']=='https://publisher.invalid/releases/fixture/release.json'
            assert request['candidateEngine']=='0.8.8-beta'
            # This is the selected ASCII struct codec, not arbitrary JSON equivalence.
            doc={k:document[k] for k in ['schema','pack','channel','sequence']}
            doc['release']={k:document['release'][k] for k in ['id','url','maximum_bytes']};doc['minimum_engine']=document['minimum_engine']
            raw=compact(doc)
            if role=='prior' and row['case'] in ['prior-payload-whitespace','advanced-after-whitespace']:raw=b' \n'+raw+b'\n'
            if role=='prior' and row['case']=='prior-payload-key-order':raw=json.dumps(doc,sort_keys=True,separators=(',',':')).encode()
            assert raw.decode()==request[role+'PayloadUtf8'] and digest(raw)==request[role+'PayloadSha256']
            envelope=request[role+'Envelope'];assert bytes.fromhex(envelope['payload'])==raw
            assert envelope['kind']=='channel' and envelope['schema']==1 and len(envelope['signatures'])==1
            sig=envelope['signatures'][0];assert sig['algorithm']=='ed25519'
            public=bytes.fromhex(request['publicKey']);signature=bytes.fromhex(sig['signature'])
            assert sig['key']==digest(public) and len(public)==32 and len(signature)==64
            identity=digest(public+raw+signature);assert associations[row['case'],role]==identity
            proof=crypto['checks'][identity];assert proof['payloadSha256']==digest(raw) and proof['messageSha256']==digest(b'empack.channel.v1\0'+raw)
            assert proof['signatureSha256']==digest(signature) and proof['publicKeySha256']==digest(public)
            proofs[role]=proof['verified']
            data=compact(dict(schema=1,kind='channel',payload=envelope['payload'],signatures=[{k:sig[k] for k in ['algorithm','key','signature']}]))
            if role=='prior' and row['case']=='prior-envelope-whitespace':data=b' \n'+data+b'\n'
            if role=='prior' and row['case']=='invalid-prior-signature':data=json.dumps(envelope,sort_keys=True,separators=(',',':')).encode()
            assert digest(data)==request[role+'EnvelopeSha256']
            payloads[role]=raw;envelopes[role]=data
        assert proofs['candidate']
        wire=dict(id=row['case'],priorAuthenticated=proofs['prior'],oldSequence=request['prior']['sequence'],sequence=request['candidate']['sequence'],sameDocument=request['prior']==request['candidate'],samePayload=payloads['prior']==payloads['candidate'],sameEnvelope=envelopes['prior']==envelopes['candidate'])
        assert seen['sameDocument']==wire['sameDocument'] and seen['samePayload']==wire['samePayload'] and seen['sameEnvelope']==wire['sameEnvelope']
        assert seen['priorAuthenticated']==wire['priorAuthenticated']
        if wire['priorAuthenticated']:
            floor=seen['priorFloor'];assert floor['sequence']==wire['oldSequence'] and floor['payload']==digest(payloads['prior'])
            assert floor['pack']=='fixture-pack' and floor['channel']=='stable' and floor['origin']=='https://publisher.invalid'
        else:assert seen['priorFloor'] is None and seen['subscriberAccepted'] is None
        if seen['subscriberAccepted']:
            assert isinstance(seen['nextFloor'],dict), 'Accepted subscriber needs its recorded next floor'
            assert seen['nextFloor']['sequence']==wire['sequence'] and seen['nextFloor']['payload']==digest(payloads['candidate'])
        else:assert seen['nextFloor'] is None
        scenarios.append(wire);outcomes.append(dict(publisher=seen['publisherAccepted'],subscriber=seen['subscriberAccepted']))
    return scenarios,outcomes


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--public-only',action='store_true');args=parser.parse_args()
    receipt,crypto,rows=inspect(args.public_only);scenarios,outcomes=observe(rows,crypto)
    packet=dict(schema=1,profile='source-publisher-payload-floor',candidateAdmitted=True,identityAndOriginAdmitted=True,scenarios=scenarios)
    work=ROOT/'.build/empack-channel-publication-formal';out=work/'applications/empack/channel-publication';out.mkdir(parents=True,exist_ok=True)
    lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend');env=dict(os.environ,LEAN_PATH=str(work),BEND_NO_TELEMETRY='1')
    p=subprocess.run([lean,'-DwarningAsError=true','-o',str(out/'Publication.olean'),'applications/empack/channel-publication/Publication.lean'],cwd=ROOT,env=env,text=True,capture_output=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    def replay(data):
        path=work/'input.json';path.write_text(json.dumps(data)+'\n')
        return subprocess.run([lean,'--run','applications/empack/channel-publication/PublicationCase.lean',str(path)],cwd=ROOT,env=env,text=True,capture_output=True,timeout=90)
    p=replay(packet);assert p.returncode==0,p.stdout+p.stderr;actual=json.loads(p.stdout)
    assert [{k:x[k] for k in ['publisher','subscriber']} for x in actual]==outcomes
    flag=lambda b:'True{}' if b else 'False{}';calls=[]
    for r in scenarios:calls.append('R.render('+','.join([flag(r['priorAuthenticated']),str(r['oldSequence'])+'n',str(r['sequence'])+'n',flag(r['sameDocument']),flag(r['samePayload'])])+') ++ "\\n"')
    driver=work/'driver.bend';driver.write_text('import Base\nimport ../../applications/empack/channel-publication/Publication.bend as R\n\ndef main() -> IO(Unit):\n  IO.write('+ ' ++ '.join(calls)+')\n')
    p=subprocess.run([bend,str(driver)],cwd=ROOT,env=env,text=True,capture_output=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    assert [json.loads(x) for x in p.stdout.splitlines()]==actual
    refusals=[]
    for name,edit,message in [
      ('schema',lambda d:d.update(schema=2),'Unsupported channel publication research profile.'),
      ('profile',lambda d:d.update(profile='full-publisher'),'Unsupported channel publication research profile.'),
      ('candidate',lambda d:d.update(candidateAdmitted=False),'Unsupported channel publication research profile.'),
      ('binding',lambda d:d.update(identityAndOriginAdmitted=False),'Unsupported channel publication research profile.'),
      ('empty',lambda d:d.update(scenarios=[]),'Unsupported channel publication scenario count.'),
      ('limit',lambda d:d.update(scenarios=d['scenarios']*3),'Unsupported channel publication scenario count.'),
      ('zero-sequence',lambda d:d['scenarios'][0].update(sequence=0),'Unsupported channel publication sequence or identity.'),
      ('payload-vs-document',lambda d:d['scenarios'][0].update(sameDocument=False),'Inconsistent channel identity witnesses.'),
      ('envelope-vs-payload',lambda d:d['scenarios'][1].update(sameEnvelope=True),'Inconsistent channel identity witnesses.')]:
        bad=copy.deepcopy(packet);edit(bad);p=replay(bad);assert p.returncode==2 and not p.stdout and message in p.stderr,(name,p.stdout,p.stderr);refusals.append(name)
    mutations=[]
    for name,edit in [
      ('publisher-result',lambda d:d[1]['observed'].update(publisherAccepted=False)),
      ('subscriber-result',lambda d:d[1]['observed'].update(subscriberAccepted=True)),
      ('same-payload',lambda d:d[1]['observed'].update(samePayload=True)),
      ('next-floor',lambda d:d[0]['observed']['nextFloor'].update(payload='0'*64)),
      ('hidden-signature-failure',lambda d:d[-1]['observed'].update(priorAuthenticated=True))]:
        bad=copy.deepcopy(rows);edit(bad)
        try:
            _,changed=observe(bad,crypto);assert changed==outcomes
        except AssertionError:mutations.append(name)
        else:raise RuntimeError('Changed observation escaped: '+name)
    (work/'input.json').write_text(json.dumps(packet)+'\n')
    result=dict(schema=1,requests=scenarios,observed=outcomes,model=actual,decoderRefusals=refusals,changedObservationControls=mutations,comparisonFields=22,independentSignatureAssociations=22,uniqueIndependentSignatureVerifications=9,modelIdentities=[dict(path='applications/empack/channel-publication/'+n,sha256=sha(HERE/n)) for n in ['Publication.lean','PublicationCase.lean','Publication.bend']],excludedPrivateChecks=['old-generated-source-and-new-reconstruction','compiler-binary-and-direct-dependencies','current-openssl-binary'] if args.public_only else [],limits=['Prior authentication comes from independent retained public-signature verification plus closed fixture codec/origin/engine premises, not publisher output.','Publisher rule is exact source guard plus old-pointer authentication; no staged asset/HTTPS/publication or installed CLI.','Proposed stricter guard is model-only; crypto/diff/hashing/transport/durability are not formalized.'])
    (RUN/('comparison-public.json' if args.public_only else 'comparison.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(sourceCases=11,comparedFields=22,decoderRefusals=len(refusals),changedControls=len(mutations),modelCandidateCases=len(actual))))

if __name__=='__main__':main()
