#!/usr/bin/env python3
"""Own tiny snapshot/history fixtures and verified pack-omission copies only."""
from datetime import datetime,timezone
import hashlib,json,os,platform,secrets,shutil,signal,stat,subprocess,time
from pathlib import Path
from locks_probe import redact

ROOT=Path(__file__).resolve().parents[2]
PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
STAMP=1700000000000000000


def main():
    run=ROOT/'applications/evidence'/('restic-comparison-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work=run/'work'
    for name in ['home','cache','tmp','private','source']:(work/name).mkdir(parents=True)
    (run/'probe.py').write_bytes(PRODUCER);(run/'helper.py').write_bytes((Path(__file__).parent/'locks_probe.py').read_bytes())
    pin=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']['restic'];tool=Path(pin['path']);assert sha(tool)==pin['sha256']
    password=work/'password';password.write_text(secrets.token_urlsafe(32)+'\n');password.chmod(0o600)
    repo=work/'repository';source=work/'source'
    env=dict(PATH='/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),RESTIC_CACHE_DIR=str(work/'cache'),GOMAXPROCS='2',LANG='C.UTF-8')
    rows=[];owned=[];snapshots={};trees={};interventions=[]
    def save():
        raw=(json.dumps(rows,indent=2)+'\n').encode();(work/'private/commands.json').write_bytes(raw);(run/'commands.json').write_bytes(redact(raw))
        (run/'owned-processes.json').write_text(json.dumps([dict(pid=p.pid,retired=p.poll()is not None)for p in owned],indent=2)+'\n')
    def command(label,args,root=repo,expected=0):
        assert not any(r['case']==label for r in rows)
        prefix=[str(tool),'--repo',str(root),'--password-file',str(password),'--json','--no-cache']
        started=time.monotonic()
        with(work/'private'/(label+'.stdout')).open('xb')as out,(work/'private'/(label+'.stderr')).open('xb')as err:
            p=subprocess.Popen(prefix+args,cwd=source,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);owned.append(p);save();timed=False
            try:p.wait(timeout=30)
            except subprocess.TimeoutExpired:timed=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
        try:os.killpg(p.pid,0)
        except ProcessLookupError:absent=True
        else:absent=False
        streams={}
        for name in ['stdout','stderr']:
            raw=work/'private'/(label+'.'+name);public=run/(label+'.'+name);public.write_bytes(redact(raw.read_bytes()))
            streams[name]=dict(rawSha256=sha(raw),publicSha256=sha(public),rawPrivatePath=str(raw.relative_to(run)))
        row=dict(case=label,repository=root.name,args=args,seconds=time.monotonic()-started,streams=streams,
            outcome=dict(exitCode=p.returncode,timedOut=timed,ownedGroupAbsent=absent))
        rows.append(row);save();print(label,p.returncode,flush=True)
        assert not timed and absent,(label,'unconfirmed process retirement')
        if expected is not None:assert p.returncode==expected,(label,p.returncode,expected)
        return (work/'private'/(label+'.stdout')).read_bytes()
    def json_lines(label):return [json.loads(s)for s in(work/'private'/(label+'.stdout')).read_text().splitlines()]
    def image(root):
        return {str(p.relative_to(root)):dict(sha256=sha(p),size=p.stat().st_size)for p in sorted(root.rglob('*'))if p.is_file()}
    def source_image():
        return {str(p.relative_to(source)):dict(kind='file'if p.is_file()else'dir',mode=stat.S_IMODE(p.stat().st_mode),
            size=p.stat().st_size if p.is_file()else 0,sha256=sha(p)if p.is_file()else None,mtimeNs=p.stat().st_mtime_ns,
            ctimeNs=p.stat().st_ctime_ns,inode=p.stat().st_ino)for p in sorted(source.rglob('*'))}
    def put(name,data):
        p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);p.chmod(0o640);os.utime(p,ns=(STAMP,STAMP))
    def backup(key,date):
        before=source_image();command('backup-'+key,['backup','.','--force','--host','comparison-fixture-host','--time',date])
        assert source_image()==before
        summary=next(r for r in json_lines('backup-'+key)if r.get('message_type')=='summary');snapshots[key]=summary['snapshot_id']
        command('ls-'+key,['ls',snapshots[key]])
        sn=next(r for r in json_lines('ls-'+key)if r.get('message_type')=='snapshot');trees[key]=sn['tree']
        return before
    try:
        command('init',['init','--repository-version','2'])
        initial={'keep.txt':b'unchanged\n','copy-a.txt':b'duplicate payload\n','copy-b.txt':b'duplicate payload\n',
            'changed.txt':b'old content\n','mode.txt':b'mode stable\n','moved-old.txt':b'moved payload\n',
            'deleted.txt':b'deleted payload\n','type-change':b'was regular\n','group/leaf.txt':b'leaf\n','empty.txt':b''}
        for name,data in initial.items():put(name,data)
        source_a=backup('A','2025-01-01 00:00:00 +0000')
        put('changed.txt',b'new content\n');(source/'mode.txt').chmod(0o600)
        (source/'moved-old.txt').rename(source/'moved-new.txt');(source/'deleted.txt').unlink()
        (source/'type-change').unlink();put('type-change/child.txt',b'new child\n');put('added.txt',b'added payload\n')
        source_b=backup('B','2025-01-02 00:00:00 +0000')
        source_c=backup('C','2025-01-03 00:00:00 +0000');assert source_b==source_c and trees['B']==trees['C']
        for label,args,expected in [
            ('diff-default',['diff',snapshots['A'],snapshots['B']],0),('diff-metadata',['diff','--metadata',snapshots['A'],snapshots['B']],0),
            ('diff-reverse',['diff',snapshots['B'],snapshots['A']],0),('diff-equal-tree',['diff','--metadata',snapshots['B'],snapshots['C']],0),
            ('ls-group',['ls',snapshots['B'],'/group'],0),('ls-recursive',['ls','--recursive',snapshots['B'],'/group'],0),
            ('ls-missing',['ls',snapshots['B'],'/absent'],0),('ls-relative-filter',['ls',snapshots['B'],'group'],1),
            ('ls-sorted',['ls','--sort','size','--reverse',snapshots['B']],0),
            ('find-moved',['find','moved*'],0),('find-keep',['find','keep.txt'],0),('find-reverse',['find','--reverse','keep.txt'],0),
            ('find-case',['find','KEEP.TXT'],0),('find-insensitive',['find','--ignore-case','KEEP.TXT'],0),
            ('find-mtime',['find','--oldest','2024-01-01','keep.txt'],0),('find-selected',['find','--snapshot',snapshots['A'],'moved*'],0),
            ('find-missing',['find','never-present'],0),('stats-bad-mode',['stats','--mode','not-a-mode'],1)]:command(label,args,expected=expected)
        selections={'A':['A'],'B':['B'],'BC':['B','C'],'AB':['A','B']}
        for key,keys in selections.items():
            for mode in ['restore-size','files-by-contents','blobs-per-file','raw-data']:
                command('stats-'+key+'-'+mode,['stats','--mode',mode,*[snapshots[k]for k in keys]])
        indexes={}
        for i,p in enumerate(sorted((repo/'index').iterdir())):
            indexes[p.name]=json.loads(command('index-'+str(i),['cat','index',p.name]))
        tree_documents={}
        def tree_capture(id):
            if id in tree_documents:return
            label='tree-'+str(len(tree_documents));doc=json.loads(command(label,['cat','tree',id]));tree_documents[id]=doc
            for n in doc['nodes']:
                if n['type']=='dir':tree_capture(n['subtree'])
        for id in trees.values():tree_capture(id)
        bnodes=tree_documents[trees['B']]['nodes'];changed=next(n for n in bnodes if n['name']=='changed.txt');data_id=changed['content'][0]
        assert command('dump-B',['dump',snapshots['B'],'/changed.txt'])==b'new content\n'
        command('find-data-id',['find','--blob','--snapshot',snapshots['B'],data_id])
        command('find-tree-id',['find','--tree','--snapshot',snapshots['B'],trees['B']])
        original=image(repo)
        packs=[p for idx in indexes.values()for p in idx['packs']]
        for kind,id in [('data',data_id),('tree',trees['B'])]:
            matches=[p for p in packs if any(b['type']==kind and b['id']==id for b in p['blobs'])]
            assert matches and all(b['type']==kind for b in matches[0]['blobs']),'Cannot isolate the declared pack kind'
            pack=matches[0]['id'];clone=work/('missing-'+kind);shutil.copytree(repo,clone)
            assert image(clone)==original
            for path in original:assert(repo/path).stat().st_ino!=(clone/path).stat().st_ino,'Unexpected hardlink clone'
            relative='data/'+pack[:2]+'/'+pack;target=clone/relative;assert target.is_file()
            quarantine=work/('retained-'+kind+'-'+pack);h=sha(target);target.rename(quarantine)
            expected_image={p:v for p,v in original.items()if p!=relative};assert image(clone)==expected_image
            event=dict(kind=kind,blob=id,pack=pack,path=relative,sha256=h,cloneBefore=original,cloneAfterOmission=expected_image,retainedPath=str(quarantine.relative_to(run)))
            interventions.append(event);(run/'interventions.json').write_text(json.dumps(interventions,indent=2)+'\n')
            command(kind+'-ls',['ls',snapshots['B']],root=clone,expected=None)
            command(kind+'-find',['find','--snapshot',snapshots['B'],'keep.txt'],root=clone,expected=None)
            command(kind+'-stats',['stats','--mode','raw-data',snapshots['B']],root=clone,expected=None)
            command(kind+'-dump',['dump',snapshots['B'],'/changed.txt'],root=clone,expected=None)
            assert image(clone)==expected_image and image(repo)==original
            assert sha(quarantine)==h;quarantine.rename(target);assert image(clone)==original
            command(kind+'-restored-find',['find','--snapshot',snapshots['B'],'keep.txt'],root=clone)
            assert command(kind+'-restored-dump',['dump',snapshots['B'],'/changed.txt'],root=clone)==b'new content\n'
            assert image(clone)==image(repo)==original;event['restoredByteImage']=True
            (run/'interventions.json').write_text(json.dumps(interventions,indent=2)+'\n')
        assert source_image()==source_c and not list((repo/'locks').glob('*'))
        receipt=dict(schema=1,tool=pin,producerSha256=hashlib.sha256(PRODUCER).hexdigest(),helperSha256=sha(run/'helper.py'),
            platform=platform.platform(),architecture=platform.machine(),snapshots=snapshots,trees=trees,sourceA=source_a,sourceB=source_b,sourceC=source_c,
            commands=len(rows),treeDocuments=len(tree_documents),indexDocuments=len(indexes),repositoryImage=original,
            allOwnedProcessesRetired=all(p.poll()is not None for p in owned),finalLocks=[],
            scope='Generated regular files,three snapshots,fresh local repository and two verified byte-copy pack-omission fixtures. Originals preserved;each omitted copy pack restored and its complete byte image rechecked.',
            limits=['One local macOS profile,no live data/remote repository or GUI. No source corruption/authentication bypass or system recovery claim.',
                'Pack-loss cases run with --no-cache and inspect actual read/query results. Native dump validates changed.txt only;all payloads are not restored.',
                'Snapshot selection,time/path/pattern/sort/stat modes are selected cases,not every CLI argument or filesystem type.'])
        (run/'receipt.json').write_bytes(redact((json.dumps(receipt,indent=2)+'\n').encode()))
        (work/'private/receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    finally:
        for p in owned:
            if p.poll()is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
        save();print('capture',run,flush=True)


if __name__=='__main__':main()
