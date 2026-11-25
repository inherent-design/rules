"""Disposable direct-content authoring, no build/game/network or host-state use."""
from datetime import datetime, timezone
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import tempfile
import time
import zipfile

ROOT=Path(__file__).resolve().parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
AUTHOR='''schema: 6
pack: {id: rules.content, name: Rules typed content, version: '1', authors: [Fixture]}
runtime: {minecraft: '1.21.1', loader: vanilla, java: {preferred: 21}}
layout: {data-pack: config/paxi/datapacks, world: saves}
dependencies: {}
build:
  default: [client]
  profiles:
    client: {target: prism, delivery: bundled, environment: client}
'''


def write(p,value):
    p.write_text(json.dumps(value,indent=2)+'\n')


def archive(entries):
    target=io.BytesIO()
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_STORED) as z:
        for name,value in entries:
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.create_system=3
            info.external_attr=(stat.S_IFREG|0o644)<<16
            z.writestr(info,value)
    return target.getvalue()


def image(root):
    result={}
    for directory,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            p=Path(directory)/name;s=p.lstat();key=p.relative_to(root).as_posix()
            if stat.S_ISLNK(s.st_mode):
                result[key]=dict(kind='link',target=os.readlink(p),mode=s.st_mode)
            elif stat.S_ISDIR(s.st_mode):
                result[key]=dict(kind='directory',mode=s.st_mode)
            else:
                assert stat.S_ISREG(s.st_mode) and s.st_size < 512 << 10
                data=p.read_bytes()
                result[key]=dict(kind='file',sha256=sha(p),bytesHex=data.hex(),mode=s.st_mode,mtimeNs=s.st_mtime_ns)
    assert len(result)<256
    return result


def main():
    binary=Path('/Users/zer0cell/.local/bin/empack')
    assert sha(binary)=='99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
    ledger=ROOT/'applications/sources/empack-content-kinds-selections.json'
    for row in json.loads(ledger.read_text()):
        assert sha(ROOT/row['cache'])==row['sha256']
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--continue-run',type=Path)
    continuation=parser.parse_args().continue_run
    rows=[]
    if continuation:
        run=continuation.resolve()
        assert run==ROOT/'applications/evidence/empack-content-kinds-20261125T200444932279Z'
        setup=json.loads((run/'setup.json').read_text());receipt=json.loads((run/'receipt.json').read_text())
        work=Path(setup['work']);project=work/'project';env=setup['environment']
        assert work==Path('/private/tmp/rules-empack-content-kinds-karvnecw')
        assert not receipt['complete'] and not (run/'continuation.json').exists()
        assert sha(run/'probe.py')==setup['producerSha256'] and sha(binary)==setup['binarySha256']
        rows=json.loads((run/'commands.json').read_text())
        assert [r['id'] for r in rows]==['initialize','implicit-module'] and rows[-1]['exitCode']==1
        assert rows[-1]['before']==rows[-1]['after']==image(project)
        assert 'Cannot read direct dependency input: No such file or directory' in (run/'implicit-module.stderr').read_text()
        for item in setup['artifacts']:
            assert sha(project/'vendor'/item['filename'])==sha(run/'inputs'/item['filename'])==item['sha256']
        for r in rows:
            for stream in ['stdout','stderr']:assert sha(run/(r['id']+'.'+stream))==r['streams'][stream]
        (run/'initial-receipt.json').write_bytes((run/'receipt.json').read_bytes())
        (run/'continue-probe.py').write_bytes(Path(__file__).read_bytes())
        write(run/'continuation.json',dict(producerSha256=sha(run/'continue-probe.py'),fromCommands=2,
              preservedSetupSha256=sha(run/'setup.json'),initialReceiptSha256=sha(run/'initial-receipt.json'),
              reason='Original fixture passed vendor-relative paths with process cwd at work root. --workdir selected the project but did not rebase direct input operands. Guarded continuation keeps the exact project/input images and uses absolute operands; old rows/streams are not rewritten. This is a harness-path error, not a classification failure.'))
    else:
        run=ROOT/'applications/evidence'/('empack-content-kinds-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        run.mkdir();(run/'inputs').mkdir();(run/'probe.py').write_bytes(Path(__file__).read_bytes())
        work=Path(tempfile.mkdtemp(prefix='rules-empack-content-kinds-',dir='/private/tmp'))
        for name in ['project','state','cache','tmp','home']:(work/name).mkdir(mode=0o700)
        project=work/'project';(project/'pack').mkdir();(project/'vendor').mkdir()
        (project/'empack.yml').write_text(AUTHOR)
        module=[('fabric.mod.json',b'{}'),('CON',b'opaque resource')]
        resource=[('pack.mcmeta',b'{}'),('assets/rules/example',b'resource')]
        shader=[('shaders/example.glsl',b'shader')]
        data=[('pack.mcmeta',b'{}'),('data/rules/example',b'data')]
        fixtures={'module.jar':module,'resource.zip':resource,'shader.zip':shader,'data.zip':data,
                  'unknown.jar':[('Example.class',b'not executable')],
                  'project.zip':[('modrinth.index.json',b'{}')],
                  'world.zip':[('Wrapped/level.dat',b'world'),('Wrapped/region/r.0.0.mca',b'region')],
                  'bad-world.zip':[('First/level.dat',b'first'),('Second/level.dat',b'second')],
                  'resource-jar.jar':resource,'resource-upper.ZIP':resource,
                  'mixed.zip':resource+[('data/rules/example',b'data')]}
        artifacts=[]
        for name,entries in fixtures.items():
            raw=archive(entries);(project/'vendor'/name).write_bytes(raw);(run/'inputs'/name).write_bytes(raw)
            artifacts.append(dict(filename=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
                                  members=[dict(path=n,bytesHex=v.hex(),sha256=hashlib.sha256(v).hexdigest()) for n,v in entries]))
        env=dict(PATH=os.environ['PATH'],HOME=str(work/'home'),LANG='en_US.UTF-8',TMPDIR=str(work/'tmp'),TMP=str(work/'tmp'),TEMP=str(work/'tmp'),
                 DO_NOT_TRACK='1',NO_COLOR='1',MISE_SKIP_RESHIM='1',HTTP_PROXY='http://127.0.0.1:9',HTTPS_PROXY='http://127.0.0.1:9',ALL_PROXY='http://127.0.0.1:9',NO_PROXY='')
        write(run/'setup.json',dict(schema=1,work=str(work),binary=str(binary),binarySha256=sha(binary),producerSha256=sha(run/'probe.py'),
              sourceLedgerSha256=sha(ledger),environment=env,author=AUTHOR,artifacts=artifacts,
              scope='Own marker archives and private author/state/cache only; no build, actual mod/world compatibility,Java,game,provider request,live channel,global tool/state change or whole-host I/O trace.'))
    def command(label,args,allowed=(0,),reason=None,preserve=False):
        if continuation:label='continued-'+label
        args=[str(project/a) if a.startswith('vendor/') else a for a in args]
        before=image(project)
        argv=[str(binary),'--state-dir',str(work/'state'),'--cache-dir',str(work/'cache'),'--workdir',str(project),'--color','never','--yes',*args]
        start=time.monotonic();child=subprocess.Popen(argv,cwd=work,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timed=False
        try:out,err=child.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(child.pid,signal.SIGTERM)
            try:out,err=child.communicate(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        for stream,raw in [('stdout',out),('stderr',err)]:(run/(label+'.'+stream)).write_bytes(raw)
        row=dict(id=label,argv=argv,exitCode=child.returncode,timedOut=timed,processGroupAbsent=absent,seconds=time.monotonic()-start,
                 before=before,after=image(project),streams={s:sha(run/(label+'.'+s)) for s in ['stdout','stderr']})
        rows.append(row);write(run/'commands.json',rows);print(label,child.returncode,flush=True)
        assert absent and not timed and child.returncode in allowed,(label,out[-1500:],err[-1500:])
        if reason is not None:assert reason in (out+err).decode(),(label,out[-1500:],err[-1500:])
        if preserve:assert before==row['after'],label
        return out
    complete=False
    try:
        if not continuation:command('initialize',['sync'])
        command('implicit-module',['add','vendor/module.jar'])
        command('ambiguous-zip',['add','vendor/resource.zip'],(1,2),reason='supply --type',preserve=True)
        command('preview-resource',['--dry-run','add','--type','resourcepack','vendor/resource.zip'],preserve=True)
        command('resource',['add','--type','resourcepack','vendor/resource.zip'])
        command('shader',['add','--type','shader','vendor/shader.zip'])
        command('datapack',['add','--type','datapack','vendor/data.zip'])
        command('unknown-module',['add','--type','mod','vendor/unknown.jar'],(1,2),reason='explicit acceptance is required',preserve=True)
        command('project-as-mod',['add','--type','mod','vendor/project.zip'],(1,2),reason='requires project/world import interpretation',preserve=True)
        command('interpreted-world',['add','--type','world','vendor/world.zip'])
        command('ambiguous-world',['add','--type','world','vendor/bad-world.zip'],(1,2),reason='exactly one nonempty level.dat',preserve=True)
        command('resource-jar',['add','--type','resourcepack','vendor/resource-jar.jar'])
        command('resource-upper',['add','--type','resourcepack','vendor/resource-upper.ZIP'])
        command('mixed-resource',['--dry-run','add','--type','resourcepack','vendor/mixed.zip'],preserve=True)
        command('mixed-datapack',['--dry-run','add','--type','datapack','vendor/mixed.zip'],preserve=True)
        document=command('read-manifest',['manifest','diff','--json'],preserve=True)
        write(run/'manifest.json',json.loads(document))
        complete=True
    finally:
        matches=[s.strip() for s in subprocess.check_output(['ps','-axo','pid=,args='],text=True).splitlines() if str(work) in s]
        allocation=int(subprocess.check_output(['/usr/bin/du','-sk',str(work)],text=True).split()[0])
        write(run/'receipt.json',dict(schema=1,complete=complete,commands=len(rows),work=str(work),workPathProcessMatches=matches,
              allRecordedGroupsAbsent=all(r['processGroupAbsent'] for r in rows),privateAllocatedKiB=allocation,
              scope='Direct add/preview/local inspection only; no distribution build, Minecraft execution or consumer suffix probe. Failed requests may have state/cache effects; preserve claims cover the captured author tree.'))
        print(json.dumps(dict(capture=str(run.relative_to(ROOT)),complete=complete,commands=len(rows),work=str(work))))


if __name__=='__main__':main()
