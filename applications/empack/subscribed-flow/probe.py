"""One local signed-offer/install/rollback join. No HTTP, engine build, Java, or game.

Reuse two verified historical native exports without modifying their originals.
The released CLI creates its own disposable signing key and signed releases.
OpenSSL signs authored channel fixtures, NOT release-channel-create/deployment.
Private key material stays exclusively in the private fixture, never a receipt.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
BINARY = Path('/Users/zer0cell/.local/bin/empack')
EXPECTED = '99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
OPENSSL = Path('/opt/homebrew/bin/openssl')
PRIOR = ROOT/'applications/evidence/empack-native-ownership-20261124T031930881554Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
write = lambda p, x: p.write_text(json.dumps(x, indent=2)+'\n')


def image(root):
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs+files):
            p=Path(directory)/name; st=p.lstat(); rel=p.relative_to(root).as_posix()
            assert not stat.S_ISLNK(st.st_mode), 'Unexpected fixture link'
            if stat.S_ISDIR(st.st_mode): result[rel]=dict(kind='directory',mode=st.st_mode)
            else:
                assert stat.S_ISREG(st.st_mode)
                raw=p.read_bytes();value=dict(kind='file',mode=st.st_mode,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),mtimeNs=st.st_mtime_ns)
                if p.suffix=='.json' or p.suffix=='.txt': value['bytesHex']=raw.hex()
                result[rel]=value
    return result


def main():
    assert sha(BINARY)==EXPECTED and OPENSSL.is_file()
    history=json.loads((PRIOR/'progress.json').read_text())
    products={r['label']:r for r in history['observations'] if r.get('kind')=='produced-release'}
    # Validate original descriptors/assets BEFORE any new operation or copying.
    selected={}
    for label in ['a','b']:
        src=PRIOR/'work/releases'/label;raw=(src/'release.json').read_bytes()
        assert raw==(PRIOR/('release-'+label+'.json')).read_bytes()
        assert sha(src/'release.json')==products[label]['release']
        document=json.loads(raw);assert len(document['files'])==2
        for f in document['files']:
            assert f['source']['kind']=='asset' and f['source']['path']=='assets/'+f['sha256']
            p=src/f['source']['path'];assert not p.is_symlink() and sha(p)==f['sha256'] and p.stat().st_size==f['bytes']
        selected[label]=dict(source=src,document=document,digest=sha(src/'release.json'))
    assert selected['a']['digest']!=selected['b']['digest']
    assert selected['a']['document']['pack']==selected['b']['document']['pack']
    work=Path(tempfile.mkdtemp(prefix='rules-empack-subscribed-',dir='/private/tmp'))
    for name in ['publisher','recipient','state','cache','tmp','private-keys','exports','channels']:
        (work/name).mkdir(mode=0o700)
    for label, item in selected.items():
        target=work/'exports'/label;target.mkdir();(target/'assets').mkdir()
        shutil.copyfile(item['source']/'release.json',target/'release.json')
        for f in item['document']['files']:shutil.copyfile(item['source']/f['source']['path'],target/f['source']['path'])
    run=ROOT/'applications/evidence'/('empack-subscribed-flow-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir()
    (run/'probe.py').write_bytes(Path(__file__).read_bytes())
    setup=dict(schema=1,work=str(work),binary=str(BINARY),binarySha256=EXPECTED,openssl=str(OPENSSL),opensslSha256=sha(OPENSSL),producerSha256=sha(run/'probe.py'),
        priorCapture=str(PRIOR.relative_to(ROOT)),priorProgressSha256=sha(PRIOR/'progress.json'),
        exports={label:dict(digest=v['digest'],pack=v['document']['pack'],version=v['document']['version'],files=v['document']['files']) for label,v in selected.items()},
        scope='Own local publisher, native-key setup, staged signed releases, OpenSSL-authored channel fixtures, native enrollment/observation/installation/rollback. No HTTPS channel creation/deployment or transport, no public write, private preexisting key, engine build,Java,launcher or game. Private key directory intentionally excluded from every image/receipt.')
    write(run/'setup.json',setup)
    env=dict(PATH=os.environ['PATH'],LANG='en_US.UTF-8',TMPDIR=str(work/'tmp'),NO_COLOR='1',DO_NOT_TRACK='1')
    rows=[]
    def command(label,root,args,expected=0,tool=False):
        argv=([str(OPENSSL)]+args if tool else [str(BINARY),'--state-dir',str(work/'state'),'--cache-dir',str(work/'cache'),'--workdir',str(root),'--net-timeout','10','--color','never','--yes']+args)
        before=image(root) if not tool else None
        began=time.monotonic();child=subprocess.Popen(argv,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timed=False;print(json.dumps(dict(start=label,pid=child.pid)),flush=True)
        try:out,err=child.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
        (run/(label+'.stdout')).write_bytes(out);(run/(label+'.stderr')).write_bytes(err)
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        row=dict(id=label,kind='openssl' if tool else 'empack',root=str(root),argv=argv,pid=child.pid,exitCode=child.returncode,timedOut=timed,groupAbsent=absent,seconds=time.monotonic()-began,
                 before=before,after=image(root) if not tool else None,streams={n:sha(run/(label+'.'+n)) for n in ['stdout','stderr']})
        rows.append(row);write(run/'commands.json',rows)
        print(json.dumps(dict(finish=label,exitCode=child.returncode,seconds=row['seconds'])),flush=True)
        assert not timed and absent and child.returncode==expected, 'Preserve unexpected result; do not automatically rerun'
        return out+err if label=='key-init' else out

    try:
        publisher=work/'publisher';recipient=work/'recipient';private=work/'private-keys'
        command('openssl-version',private,['version','-a'],tool=True)
        key=private/'publisher.key'
        output=command('key-init',publisher,['release','init','--key-file',str(key)])
        publics=re.findall(rb'Public key: ([0-9a-f]{64})',output);assert len(publics)==1
        public=publics[0].decode();assert stat.S_IMODE(key.stat().st_mode)==0o600
        # Conversion uses only the key JUST CREATED for this study. No seed,
        # DER private bytes, or private digest is printed or recorded.
        encoded=key.read_text().strip();assert re.fullmatch('[0-9a-f]{64}',encoded)
        der=bytes.fromhex('302e020100300506032b657004220420')+bytes.fromhex(encoded)
        with (private/'publisher.der').open('xb') as f:f.write(der)
        (private/'publisher.der').chmod(0o600)
        del encoded,der
        command('openssl-public',private,['pkey','-inform','DER','-in',str(private/'publisher.der'),'-pubout','-outform','DER','-out',str(private/'public.der')],tool=True)
        assert (private/'public.der').read_bytes()==bytes.fromhex('302a300506032b6570032100'+public)
        for label,item in selected.items():
            command('stage-'+label,publisher,['release','stage',str(work/'exports'/label),'--key-file',str(key)])
            staged=publisher/'dist/releases'/item['digest']/'release.json';assert staged.is_file()
            envelope=json.loads(staged.read_text());assert envelope['kind']=='release'
            assert bytes.fromhex(envelope['payload'])==(work/'exports'/label/'release.json').read_bytes()
            (run/('release-'+label+'.envelope.json')).write_bytes(staged.read_bytes())
        channels={}
        for label,sequence in [('a',1),('b',2)]:
            item=selected[label];staged=publisher/'dist/releases'/item['digest']/'release.json'
            document=dict(schema=2,pack=item['document']['pack'],channel='stable',sequence=sequence,
                release=dict(id=item['digest'],url='https://publisher.invalid/releases/'+item['digest']+'/release.json',maximum_bytes=staged.stat().st_size),minimum_engine='>=0.8.4-beta')
            payload=json.dumps(document,separators=(',',':')).encode()
            message=work/'channels'/('message-'+label+'.bin');message.write_bytes(b'empack.channel.v1\0'+payload)
            signature=work/'channels'/('signature-'+label+'.bin')
            command('sign-channel-'+label,private,['pkeyutl','-sign','-rawin','-keyform','DER','-inkey',str(private/'publisher.der'),'-in',str(message),'-out',str(signature)],tool=True)
            command('verify-channel-'+label,private,['pkeyutl','-verify','-rawin','-pubin','-keyform','DER','-inkey',str(private/'public.der'),'-in',str(message),'-sigfile',str(signature)],tool=True)
            envelope=dict(schema=1,kind='channel',payload=payload.hex(),signatures=[dict(algorithm='ed25519',key=hashlib.sha256(bytes.fromhex(public)).hexdigest(),signature=signature.read_bytes().hex())])
            assert len(signature.read_bytes())==64
            path=work/'channels'/('channel-'+label+'.json');write(path,envelope)
            (run/('channel-'+label+'.json')).write_bytes(path.read_bytes());channels[label]=path
        write(run/'public-context.json',dict(publicKey=public,keyFingerprint=hashlib.sha256(bytes.fromhex(public)).hexdigest(),channelDocuments='OpenSSL-authored, independently signature-verified fixture payloads; native release-channel-create/host verification NOT exercised',releaseEnvelopes='Native release stage outputs from verified prior native exports',privateKey='Created only for study; raw/DER bytes and their hashes excluded from evidence'))
        pack=selected['a']['document']['pack'];url='https://publisher.invalid/channels/stable.json'
        command('subscribe',recipient,['instance','subscribe','--pack',pack,'--channel','stable',url,'--key',public])
        command('offer-a-preview',recipient,['instance','update','--channel-file',str(channels['a'])])
        command('observe-a',recipient,['instance','check-updates',str(channels['a'])])
        staged=lambda label: publisher/'dist/releases'/selected[label]['digest']/'release.json'
        command('install-signed-a',recipient,['instance','update',str(staged('a')),'--apply'])
        # Deliberate own player-side writes, captured as a distinct operation.
        before=image(recipient);(recipient/'game/config/rules.txt').write_text('own player setting\n');(recipient/'game/note.txt').write_text('own unowned note\n')
        write(run/'player-edit.json',dict(before=before,after=image(recipient),scope='Own test seed and unowned note only; no personal settings'))
        command('offer-b-preview',recipient,['instance','update','--channel-file',str(channels['b'])])
        command('observe-b',recipient,['instance','check-updates',str(channels['b'])])
        command('install-b-preview',recipient,['instance','update',str(staged('b'))])
        managed=next(f for f in selected['b']['document']['files'] if f['destination']=='payload.txt')
        command('missing-input-b',recipient,['instance','update',str(staged('b')),'--apply','--file',managed['key']+'='+str(work/'absent-input.txt')],expected=1)
        command('install-signed-b',recipient,['instance','update',str(staged('b')),'--apply'])
        out=command('check-b',recipient,['instance','check','--json','--quiet']);write(run/'check-b.json',json.loads(out))
        command('ensure-old-consumer',recipient,['instance','ensure',str(work/'exports/a/release.json'),'--sha256',selected['a']['digest']])
        command('rollback-a',recipient,['instance','rollback',selected['a']['digest'],'--assets',str(work/'exports/a')])
        command('stale-offer-a',recipient,['instance','check-updates',str(channels['a'])],expected=1)
        bad=json.loads(channels['b'].read_text());sig=bad['signatures'][0]['signature'];bad['signatures'][0]['signature']=('00' if sig[:2]!='00' else '01')+sig[2:]
        invalid=work/'channels/invalid-signature.json';write(invalid,bad);(run/'invalid-signature.json').write_bytes(invalid.read_bytes())
        command('invalid-signature',recipient,['instance','check-updates',str(invalid)],expected=1)
        out=command('check-rollback',recipient,['instance','check','--json','--quiet']);write(run/'check-rollback.json',json.loads(out))
        assert sha(BINARY)==EXPECTED
        write(run/'receipt.json',dict(schema=1,complete=True,commands=len(rows),nativeCommands=sum(r['kind']=='empack' for r in rows),allRecordedGroupsAbsent=all(r['groupAbsent'] for r in rows),setupSha256=sha(run/'setup.json'),producerSha256=sha(run/'probe.py'),publicContextSha256=sha(run/'public-context.json'),allocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),scope='Local explicit signed inputs through native enrollment,offer preview/save,local envelope selection,failed explicit acquisition,apply,ensure,rollback and replay/signature refusals. No hosted channel production/HTTP/Java/game/platform/crash qualification. Semantics need independent readback/model comparison.'))
        print(json.dumps(dict(run=str(run),work=str(work),complete=True)),flush=True)
    except BaseException as error:
        write(run/'failure.json',dict(error=str(error),commands=len(rows),allRecordedGroupsAbsent=all(r['groupAbsent'] for r in rows)));print(json.dumps(dict(run=str(run),work=str(work),complete=False)),flush=True);raise


if __name__=='__main__':main()
