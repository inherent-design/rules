"""Disposable installed-CLI imports; no game execution or live project changes."""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')


def archive(entries):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED)as z:
        for name,body,mode in entries:
            info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=mode<<16
            z.writestr(info,body)
    return out.getvalue()


def snapshot(root):
    result={}
    if not root.exists():return result
    for directory,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            p=Path(directory)/name;s=p.lstat();key=p.relative_to(root).as_posix()
            if stat.S_ISLNK(s.st_mode):result[key]=dict(kind='symlink',target=os.readlink(p))
            elif stat.S_ISREG(s.st_mode):result[key]=dict(kind='file',sha256=sha(p),bytes=s.st_size,mode=stat.S_IMODE(s.st_mode))
            else:assert stat.S_ISDIR(s.st_mode);result[key]=dict(kind='directory')
    return result


def main():
    binary=Path('/Users/zer0cell/.local/bin/empack');assert sha(binary)=='99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
    run=ROOT/'applications/evidence'/('empack-archive-import-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir();(run/'inputs').mkdir()
    work=Path(tempfile.mkdtemp(prefix='rules-archive-import-',dir='/private/tmp'))
    for name in ['parent','state','cache','tmp']:(work/name).mkdir(mode=0o700)
    (work/'sentinel.txt').write_text('owned external sentinel\n')
    env=dict(PATH=os.environ['PATH'],TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8')
    shutil.copyfile(__file__,run/'probe.py')
    manifest=json.dumps(dict(formatVersion=1,game='minecraft',versionId='same-label',name='Rules archive fixture',files=[],dependencies={'minecraft':'1.21.1'})).encode()
    base=[('modrinth.index.json',manifest,0o100644)]
    regular=lambda name,data:(name,data,0o100644)
    jar=archive([regular('fabric.mod.json',json.dumps(dict(schemaVersion=1,id='rules_archive_fixture',version='1.0.0',name='Rules archive fixture',environment='*')).encode()),
                 regular('CON',b'opaque device resource'),regular('resource:name',b'opaque punctuation'),
                 regular('A.class',b'not runnable'),regular('a.class',b'distinct exact resource')])
    choices=[('valid-config',[regular('overrides/config/rules.txt',b'configuration\n')],0),
        ('opaque-jar',[regular('overrides/mods/fixture.jar',jar)],0),
        ('unused-traversal',[regular('../escape-marker',b'unsafe member')],1),
        ('unused-reserved',[regular('unused/CON',b'nonportable')],1),
        ('unused-case-aliases',[regular('unused/A.txt',b'A'),regular('unused/a.txt',b'a')],1),
        ('unused-unicode-aliases',[regular('unused/é.txt',b'A'),regular('unused/e\u0301.txt',b'B')],1),
        ('unused-file-ancestor',[regular('unused',b'file'),regular('unused/nested.txt',b'member')],1),
        ('unused-duplicate',[regular('unused/same.txt',b'A'),regular('unused/same.txt',b'B')],1),
        ('unused-symlink',[('unused/link',b'../owned-target',0o120777)],1),
        ('corrupt-override',[regular('overrides/config/rules.txt',b'configuration\n')],1)]
    receipt=dict(schema=1,work=str(work),binary=str(binary),binarySha256=sha(binary),producerSha256=sha(run/'probe.py'),environment=env,cases=[],
        limits=['Own text/opaque marker archives,not playable mods or worlds.','Only local imports;no game,Java,installer,channel,or live project.','Failed author publication does not imply no state/cache effects.'])
    write(run/'receipt.json',receipt)
    for name,entries,expected in choices:
        data=archive(base+entries)
        if name=='corrupt-override':
            changed=bytearray(data);offset=data.index(b'configuration\n');changed[offset]^=1;data=bytes(changed)
        path=run/'inputs'/(name+'.mrpack');path.write_bytes(data)
        destination=work/'parent'/name;assert not destination.exists()
        before=snapshot(work/'parent')
        argv=[str(binary),'--state-dir',str(work/'state'),'--cache-dir',str(work/'cache'),'--workdir',str(work/'parent'),'--color','never','--yes',
              'init',name,'--from',str(path),'--author','Rules fixture']
        p=subprocess.Popen(argv,env=env,cwd=work,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timed_out=False
        try:out,err=p.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(p.pid,signal.SIGTERM)
            try:out,err=p.communicate(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate(timeout=3)
        (run/(name+'.stdout')).write_bytes(out);(run/(name+'.stderr')).write_bytes(err)
        try:os.killpg(p.pid,0);absent=False
        except ProcessLookupError:absent=True
        row=dict(id=name,argv=argv,pid=p.pid,exitCode=p.returncode,expectedExit=expected,timedOut=timed_out,groupAbsent=absent,
                 archiveSha256=sha(path),archiveBytes=len(data),stdoutSha256=sha(run/(name+'.stdout')),stderrSha256=sha(run/(name+'.stderr')),
                 beforeParent=before,afterParent=snapshot(work/'parent'),destinationSnapshot=snapshot(destination),authorPublished=(destination/'empack.yml').is_file(),sentinelSha256=sha(work/'sentinel.txt'))
        receipt['cases'].append(row);write(run/'receipt.json',receipt)
        assert not timed_out and absent and p.returncode==expected,(name,p.returncode,err.decode(errors='replace'))
        assert (destination/'empack.yml').is_file()==(expected==0)
        assert not(work/'parent/escape-marker').exists()and not(work/'escape-marker').exists()
        assert sha(work/'sentinel.txt')==hashlib.sha256(b'owned external sentinel\n').hexdigest()
    receipt['complete']=True;receipt['allGroupsAbsent']=all(r['groupAbsent']for r in receipt['cases']);write(run/'receipt.json',receipt)
    print(json.dumps(dict(run=str(run),work=str(work),cases=len(choices),complete=True)))


if __name__=='__main__':main()
