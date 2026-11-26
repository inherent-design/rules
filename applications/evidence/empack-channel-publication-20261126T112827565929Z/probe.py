"""Compare selected publisher guard and authenticated subscriber with existing libs.

No full engine build, network, real private key, publisher files or installation.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
PRIOR = ROOT/'applications/evidence/empack-channels-20261124T130523942359Z'
REVISION = '0b4462e3032b4f09230b15329722eabefb7f574c'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    previous = json.loads((PRIOR/'receipt.json').read_text())
    for name, identity in previous['generatedSha256'].items():
        assert sha(PRIOR/'work'/name) == identity
    compiler = Path(previous['compiler']['path'])
    assert sha(compiler) == previous['compiler']['sha256']
    for item in previous['libraries'].values():
        assert sha(Path(item['path'])) == item['sha256']
    source_path = 'crates/empack-lib/src/engine/api/release_publication/channel.rs'
    source = subprocess.check_output(['git','-C',str(ROOT.parent/'empack'),'show',REVISION+':'+source_path]).decode()
    start = source.index('        ensure!(\n            channel.sequence > prior.sequence')
    end = source.index('\n        );', start) + len('\n        );')
    guard = source[start:end]
    assert 'channel.sequence == prior.sequence && channel == prior' in guard
    run = ROOT/'applications/evidence'/('empack-channel-publication-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    work = Path(tempfile.mkdtemp(prefix='rules-empack-channel-publication-',dir='/private/tmp'))
    (work/'home').mkdir();(work/'tmp').mkdir()
    (run/'probe.py').write_bytes(Path(__file__).read_bytes())
    (run/'driver.rs').write_bytes((Path(__file__).parent/'oracle.rs').read_bytes())
    old = (PRIOR/'work/main.rs').read_text()
    head = old[:old.rindex('include!(')]
    at = head.rindex('}')
    wrapper = '''pub fn fixture_publisher(previous: &[u8], channel: release::trust::ChannelDocument,
        public: ed25519_dalek::VerifyingKey) -> anyhow::Result<release::trust::ChannelDocument> {
        let previous_trust = release::trust::PublisherTrust::enroll(channel.pack.clone(), "https://publisher.invalid", vec![public])?;
        let prior = previous_trust.previous_channel(previous, &channel.channel)?;
SOURCE_GUARD
        Ok(prior)
    }
'''.replace('SOURCE_GUARD', guard)
    (work/'main.rs').write_text(head[:at]+wrapper+head[at:]+'include!('+json.dumps(str(run/'driver.rs'))+');\n')
    generated = (work/'main.rs').read_bytes()
    receipt = dict(schema=1,revision=REVISION,work=str(work),priorCapture=str(PRIOR.relative_to(ROOT)),
        priorReceiptSha256=sha(PRIOR/'receipt.json'),priorGenerated=previous['generatedSha256'],
        compiler=previous['compiler'],libraries=previous['libraries'],dependencyResolutionDirectory=previous['dependencyResolutionDirectory'],
        producerSha256=sha(run/'probe.py'),driverSha256=sha(run/'driver.rs'),generatedSha256=hashlib.sha256(generated).hexdigest(),
        publisherGuard=dict(path=source_path,sha256=hashlib.sha256(source.encode()).hexdigest(),firstLine=source[:start].count('\n')+1,lastLine=source[:end].count('\n')+1,cutSha256=hashlib.sha256(guard.encode()).hexdigest()),
        limits=['Exact prior channel crypto/codec functions plus unchanged publisher sequence guard; guard wrapper supplies admitted local channel/key context.',
                'Not full producer preparation, hosted verification, asset transfer, publication or installed CLI.',
                'Release decoder and diagnostic Display remain prior rejecting/format adapters; public fixed test seed is not publisher key custody.',
                'Seven direct reused dependencies checked; full transitive build/source correspondence unproved.'])
    (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    env=dict(PATH=str(compiler.parent)+':/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8')
    commands=[]
    def command(name,args):
        child=subprocess.Popen(args,cwd=work,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        started=time.monotonic();timed=False
        try:out,err=child.communicate(timeout=90)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
        streams={}
        for kind,data in [('stdout',out),('stderr',err)]:
            file=name+'.'+kind;(run/file).write_bytes(data);streams[kind]=dict(file=file,sha256=hashlib.sha256(data).hexdigest())
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        row=dict(name=name,argv=[str(x) for x in args],pid=child.pid,exitCode=child.returncode,timedOut=timed,seconds=time.monotonic()-started,ownedGroupAbsent=absent,streams=streams);commands.append(row)
        (run/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');print(json.dumps(dict(command=name,exit=child.returncode,groupAbsent=absent)),flush=True)
        assert not timed and absent and child.returncode==0
    try:
        binary=work/'oracle';args=[str(compiler),'--edition=2024','-C','debuginfo=0','-A','dead_code','-A','unused_imports','-L','dependency='+previous['dependencyResolutionDirectory'],str(work/'main.rs'),'-o',str(binary)]
        for name,item in previous['libraries'].items():args+=['--extern',name+'='+item['path']]
        command('compile',args);receipt['binarySha256']=sha(binary)
        command('observe',[str(binary)])
        rows=[json.loads(x) for x in (run/'observe.stdout').read_text().splitlines()];assert len(rows)==11
        receipt['records']=len(rows);receipt['allOwnedGroupsAbsent']=all(x['ownedGroupAbsent'] for x in commands)
        for item in previous['libraries'].values():assert sha(Path(item['path']))==item['sha256']
        receipt['directLibrariesUnchanged']=True
    finally:
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        (ROOT/'.build/empack-channel-publication-capture.json').write_text(json.dumps(dict(capture=str(run.relative_to(ROOT))))+'\n')
    print(json.dumps(dict(capture=str(run.relative_to(ROOT)),records=receipt.get('records',0))))


if __name__=='__main__':
    main()
