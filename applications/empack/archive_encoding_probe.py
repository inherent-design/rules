"""Two disposable imports to distinguish CP437 support from decoded-name collision."""
from datetime import datetime,timezone
import hashlib,json,os,shutil,signal,subprocess,tempfile,zipfile,io
from pathlib import Path
from archive_import_probe import archive,snapshot

ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')


def main():
    binary=Path('/Users/zer0cell/.local/bin/empack');assert sha(binary)=='99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
    run=ROOT/'applications/evidence'/('empack-archive-encoding-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));run.mkdir()
    work=Path(tempfile.mkdtemp(prefix='rules-archive-encoding-',dir='/private/tmp'))
    for name in ['parent','state','cache','tmp']:(work/name).mkdir(mode=0o700)
    env=dict(PATH=os.environ['PATH'],LANG='en_US.UTF-8',TMPDIR=str(work/'tmp'))
    shutil.copyfile(__file__,run/'probe.py');helper=Path(__file__).with_name('archive_import_probe.py');shutil.copyfile(helper,run/'helpers.py')
    manifest=json.dumps(dict(formatVersion=1,game='minecraft',versionId='same-label',name='Rules encoding fixture',files=[],dependencies={'minecraft':'1.21.1'})).encode()
    receipt=dict(schema=1,work=str(work),binary=str(binary),binarySha256=sha(binary),producerSha256=sha(run/'probe.py'),helperSha256=sha(run/'helpers.py'),environment=env,cases=[],
        purpose='Controlled byte encodings,not traversal or live content. No Java/game/installer. Observations are not preset acceptance expectations.')
    write(run/'receipt.json',receipt)
    for identity,mixed in [('single-cp437',False),('mixed-decoded-duplicate',True)]:
        entries=[('modrinth.index.json',manifest,0o100644),('overrides/config/cafx.txt',b'CP437 body\n',0o100644)]
        if mixed:entries.append(('overrides/config/café.txt',b'UTF-8 body\n',0o100644))
        raw=archive(entries);old=b'overrides/config/cafx.txt';new=b'overrides/config/caf\x82.txt'
        assert len(old)==len(new)and raw.count(old)==2
        data=raw.replace(old,new);path=run/(identity+'.mrpack');path.write_bytes(data)
        with zipfile.ZipFile(io.BytesIO(data))as z:
            independent=[dict(name=i.filename,flags=i.flag_bits,crc=i.CRC,bodySha256=hashlib.sha256(z.read(i)).hexdigest())for i in z.infolist()]
        destination=work/'parent'/identity;before=snapshot(work/'parent')
        argv=[str(binary),'--state-dir',str(work/'state'),'--cache-dir',str(work/'cache'),'--workdir',str(work/'parent'),'--color','never','--yes','init',identity,'--from',str(path),'--author','Rules fixture']
        p=subprocess.Popen(argv,env=env,cwd=work,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timed=False
        try:out,err=p.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(p.pid,signal.SIGTERM)
            try:out,err=p.communicate(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate(timeout=3)
        (run/(identity+'.stdout')).write_bytes(out);(run/(identity+'.stderr')).write_bytes(err)
        try:os.killpg(p.pid,0);absent=False
        except ProcessLookupError:absent=True
        item=dict(id=identity,argv=argv,pid=p.pid,exitCode=p.returncode,groupAbsent=absent,timedOut=timed,inputSha256=sha(path),inputBytes=len(data),
            independentNames=independent,beforeParent=before,afterParent=snapshot(work/'parent'),destinationSnapshot=snapshot(destination),
            authorPublished=(destination/'empack.yml').is_file(),stdoutSha256=sha(run/(identity+'.stdout')),stderrSha256=sha(run/(identity+'.stderr')))
        receipt['cases'].append(item);write(run/'receipt.json',receipt)
        assert absent and not timed and p.returncode in [0,1,2],(identity,p.returncode)
    receipt['complete']=True;write(run/'receipt.json',receipt)
    print(json.dumps(dict(run=str(run),work=str(work),outcomes=[(r['id'],r['exitCode'],r['authorPublished'])for r in receipt['cases']])) )


if __name__=='__main__':main()
