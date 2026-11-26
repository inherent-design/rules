"""One-shot independent public-signature readback. Never reads a signing key."""
from pathlib import Path
import hashlib
import json
import os
import signal
import subprocess
import time

ROOT=Path(__file__).resolve().parents[3]
TOOL=Path('/opt/homebrew/bin/openssl')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    locator=json.loads((ROOT/'.build/empack-channel-publication-capture.json').read_text())
    run=ROOT/locator['capture'];receipt=json.loads((run/'receipt.json').read_text())
    assert receipt['records']==11 and not (run/'crypto-verification.json').exists()
    work=Path(receipt['work'])/'public-crypto';work.mkdir();(run/'crypto').mkdir()
    (run/'crypto'/'producer.py').write_bytes(Path(__file__).read_bytes())
    rows=[json.loads(x) for x in (run/'observe.stdout').read_text().splitlines()]
    checks={};associations=[];commands=[]
    env=dict(PATH='/usr/bin:/bin',HOME=str(work),OPENSSL_CONF='/dev/null',LANG='en_US.UTF-8')
    def call(label,args):
        start=time.monotonic();p=subprocess.Popen([str(TOOL),*args],cwd=work,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timed=False
        try:out,err=p.communicate(timeout=15)
        except subprocess.TimeoutExpired:timed=True;os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate()
        streams={}
        for suffix,raw in [('stdout',out),('stderr',err)]:
            name=label+'.'+suffix;(run/'crypto'/name).write_bytes(raw);streams[suffix]=dict(file='crypto/'+name,sha256=hashlib.sha256(raw).hexdigest())
        try:os.killpg(p.pid,0);absent=False
        except ProcessLookupError:absent=True
        commands.append(dict(label=label,argv=[str(TOOL),*args],pid=p.pid,exitCode=p.returncode,timedOut=timed,ownedGroupAbsent=absent,seconds=time.monotonic()-start,streams=streams))
        assert not timed and absent
        return p.returncode
    tool_hash=sha(TOOL);assert call('version',['version','-a'])==0
    for row in rows:
        request=row['request'];public=bytes.fromhex(request['publicKey'])
        assert len(public)==32
        for role in ['prior','candidate']:
            envelope=request[role+'Envelope'];payload=bytes.fromhex(envelope['payload']);signature=bytes.fromhex(envelope['signatures'][0]['signature'])
            assert len(signature)==64 and envelope['kind']=='channel' and envelope['schema']==1
            assert payload.decode()==request[role+'PayloadUtf8']
            assert hashlib.sha256(payload).hexdigest()==request[role+'PayloadSha256']
            assert envelope['signatures'][0]['key']==hashlib.sha256(public).hexdigest()
            assert envelope['signatures'][0]['algorithm']=='ed25519'
            identity=hashlib.sha256(public+payload+signature).hexdigest()
            if identity not in checks:
                n=len(checks);prefix='check-'+str(n);key=work/(prefix+'.public.der');message=work/(prefix+'.message');sig=work/(prefix+'.signature')
                key.write_bytes(bytes.fromhex('302a300506032b6570032100')+public);message.write_bytes(b'empack.channel.v1\0'+payload);sig.write_bytes(signature)
                result=call(prefix,['pkeyutl','-verify','-rawin','-pubin','-keyform','DER','-inkey',str(key),'-in',str(message),'-sigfile',str(sig)])
                assert result in [0,1]
                checks[identity]=dict(label=prefix,verified=result==0,publicKeySha256=hashlib.sha256(public).hexdigest(),messageSha256=sha(message),signatureSha256=sha(sig),payloadSha256=hashlib.sha256(payload).hexdigest())
            associations.append(dict(case=row['case'],role=role,check=identity))
            assert checks[identity]['verified']==(not (row['case']=='invalid-prior-signature' and role=='prior'))
    assert sha(TOOL)==tool_hash
    out=dict(schema=1,tool=dict(path=str(TOOL),sha256=tool_hash),producerSha256=sha(run/'crypto/producer.py'),observeSha256=sha(run/'observe.stdout'),checks=checks,associations=associations,commands=commands,allOwnedGroupsAbsent=all(x['ownedGroupAbsent'] for x in commands),limits=['Independent OpenSSL verification of public fixture signatures only; not key custody, origin, JSON/engine policy, hosted bytes or production publication.','22 envelope associations deduplicate identical cryptographic inputs; they are not22independent workflows.'])
    (run/'crypto-verification.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(uniqueVerifications=len(checks),associations=len(associations),commands=len(commands),allGroupsAbsent=True)))

if __name__=='__main__':main()
