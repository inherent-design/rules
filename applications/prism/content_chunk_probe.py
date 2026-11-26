"""One multichunk continuation of the private staged-copy proposal;no build."""
from datetime import datetime,timezone
import hashlib,json,os,subprocess,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'applications/evidence/prism-content-candidate-20261126T020852548554Z'
PAYLOAD='MULTICHUNK\n'+'x'*131072+'\n'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,indent=2)+'\n')


def main():
    setup=json.loads((BASE/'setup.json').read_text());receipt=json.loads((BASE/'receipt.json').read_text());binary=Path(setup['work'])/'probe'
    assert sha(binary)==receipt['binarySha256'];assert sha(Path(setup['work'])/'main.cpp')==setup['generatedSha256']
    for name,digest in json.loads((BASE/'collection-basis.json').read_text()).items():assert sha(BASE/name)==digest
    work=Path(tempfile.mkdtemp(prefix='rules-prism-content-chunk-',dir='/private/tmp'));cap=ROOT/'applications/evidence'/('prism-content-chunk-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));cap.mkdir()
    incoming=work/'cases/multichunk/incoming';installed=work/'cases/multichunk/installed';incoming.mkdir(parents=True);installed.mkdir()
    for n in ['home','tmp']:(work/n).mkdir()
    src=incoming/'item.jar';dst=installed/'item.jar';src.write_text(PAYLOAD)
    row=dict(id='staged:multichunk',baseId='multichunk',policy='staged',operation='install',source=str(src),destination=str(installed),observe=[str(src),str(dst),str(dst)+'.disabled',str(incoming/'missing.jar')],watching=True,updateResult=True,cancelBeforeCommit=False)
    write(cap/'input.json',dict(schema=1,work=str(work),cases=[row]));(cap/'probe.py').write_bytes(Path(__file__).read_bytes())
    def snapshot():
        out={}
        for p in sorted((work/'cases').rglob('*')):
            s=p.lstat();v=dict(mode=s.st_mode&0o777,mtimeNs=s.st_mtime_ns)
            if p.is_dir():v['kind']='directory'
            else:assert p.is_file()and not p.is_symlink();v.update(kind='file',bytes=s.st_size,sha256=sha(p),text=p.read_text())
            out[str(p.relative_to(work/'cases'))]=v
        return out
    write(cap/'before.json',snapshot());write(cap/'setup.json',dict(schema=1,work=str(work),base=str(BASE.relative_to(ROOT)),binary=str(binary),binarySha256=receipt['binarySha256'],generatedSha256=setup['generatedSha256'],producerSha256=sha(cap/'probe.py'),bytes=len(PAYLOAD.encode()),chunkRequestBytes=65536,scope='One fresh owned staged-copy continuation using the identical previously verified binary. Larger than two requested chunks;not a physical-read count,arbitrary-size proof,or compiler rerun.'))
    env=dict(PATH='/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8');out=cap/'observe.stdout';err=cap/'observe.stderr'
    with out.open('xb')as stdout,err.open('xb')as stderr:
        p=subprocess.Popen([str(binary),str(cap/'input.json')],cwd=work,env=env,stdout=stdout,stderr=stderr,start_new_session=True);write(cap/'current-process.json',dict(pid=p.pid,status='running'))
        try:code=p.wait(timeout=20)
        except subprocess.TimeoutExpired:
            write(cap/'current-process.json',dict(pid=p.pid,status='observation-timeout;not-terminal'));raise RuntimeError('Reconcile this PID;do not restart.')
    try:os.killpg(p.pid,0);absent=False
    except ProcessLookupError:absent=True
    write(cap/'current-process.json',dict(pid=p.pid,status='terminal',exitCode=code,groupAbsent=absent));write(cap/'commands.json',[dict(label='observe',argv=[str(binary),str(cap/'input.json')],pid=p.pid,exitCode=code,groupAbsent=absent,stdout=dict(path=out.name,sha256=sha(out)),stderr=dict(path=err.name,sha256=sha(err)))]);assert code==0 and absent
    write(cap/'after.json',snapshot());rows=[json.loads(l)for l in out.read_text().splitlines()];assert len(rows)==1 and rows[0]['id']==row['id'];assert sha(binary)==receipt['binarySha256']
    write(cap/'receipt.json',dict(schema=1,cases=1,allGroupsAbsent=absent,binarySha256=sha(binary),scope='Native proposal continuation;no production or full-launcher claim.'))
    print(json.dumps(dict(capture=str(cap),work=str(work),cases=1,allGroupsAbsent=absent)))


if __name__=='__main__':main()
