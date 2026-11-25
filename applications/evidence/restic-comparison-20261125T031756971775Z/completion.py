#!/usr/bin/env python3
"""Complete retained fixture reads/copy controls without rerunning its prefix."""
from datetime import datetime,timezone
import hashlib,json,os,platform,re,shutil,signal,subprocess,time
from pathlib import Path
from locks_probe import redact

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'applications/evidence/restic-comparison-20261125T031756971775Z'
PRODUCER=Path(__file__).read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda x:hashlib.sha256((json.dumps(x,sort_keys=True,separators=(',',':'))+'\n').encode()).hexdigest()


def main():
    work=RUN/'work';source=work/'source';repo=work/'repository'
    assert not(RUN/'completion.py').exists(),'A completion attempt already owns these paths;inspect before retry.'
    original=json.loads((RUN/'commands.json').read_text());assert len(original)==44 and original[-1]['case']=='tree-0'and original[-1]['outcome']['exitCode']==1
    assert all(c['retired']for c in json.loads((RUN/'owned-processes.json').read_text()))
    assert all(c['outcome']['ownedGroupAbsent']and not c['outcome']['timedOut']for c in original)
    assert not list((repo/'locks').glob('*'))
    frozen=dict(commands=sha(RUN/'commands.json'),owned=sha(RUN/'owned-processes.json'),probe=sha(RUN/'probe.py'))
    (RUN/'completion.py').write_bytes(PRODUCER);(RUN/'completion-helper.py').write_bytes((Path(__file__).parent/'locks_probe.py').read_bytes())
    pin=json.loads((ROOT/'applications/sources/local-pins.json').read_text())['tools']['restic'];tool=Path(pin['path']);assert sha(tool)==pin['sha256']
    env=dict(PATH='/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),RESTIC_CACHE_DIR=str(work/'cache'),GOMAXPROCS='2',LANG='C.UTF-8',TZ='UTC')
    owned=[];rows=[];interventions=[]
    def save():
        raw=(json.dumps(rows,indent=2)+'\n').encode();(work/'private/completion-commands.json').write_bytes(raw);(RUN/'completion-commands.json').write_bytes(redact(raw))
        (RUN/'completion-owned-processes.json').write_text(json.dumps([dict(pid=p.pid,retired=p.poll()is not None)for p in owned],indent=2)+'\n')
    def command(label,args,root=repo,expected=0):
        assert not any(r['case']==label for r in rows)and not(RUN/(label+'.stdout')).exists()
        prefix=[str(tool),'--repo',str(root),'--password-file',str(work/'password'),'--json','--no-cache']
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
            raw=work/'private'/(label+'.'+name);public=RUN/(label+'.'+name);public.write_bytes(redact(raw.read_bytes()))
            streams[name]=dict(rawSha256=sha(raw),publicSha256=sha(public),rawPrivatePath=str(raw.relative_to(RUN)))
        rows.append(dict(case=label,repository=root.name,args=args,seconds=time.monotonic()-started,streams=streams,
            outcome=dict(exitCode=p.returncode,timedOut=timed,ownedGroupAbsent=absent)));save();print(label,p.returncode,flush=True)
        assert not timed and absent,(label,'unconfirmed retirement')
        if expected is not None:assert p.returncode==expected,(label,p.returncode,expected)
        return(work/'private'/(label+'.stdout')).read_bytes()
    def original_lines(label):return [json.loads(s)for s in(work/'private'/(label+'.stdout')).read_text().splitlines()]
    snapshots={k:next(r for r in original_lines('backup-'+k)if r.get('message_type')=='summary')['snapshot_id']for k in ['A','B','C']}
    trees={k:next(r for r in original_lines('ls-'+k)if r.get('message_type')=='snapshot')['tree']for k in snapshots}
    assert trees['B']==trees['C']
    def image(root):return {str(p.relative_to(root)):dict(sha256=sha(p),size=p.stat().st_size)for p in sorted(root.rglob('*'))if p.is_file()}
    source_before=image(source);repository_before=image(repo)
    (work/'private/primary-repository-image.json').write_text(json.dumps(repository_before,indent=2)+'\n')
    indexes=[json.loads((work/'private'/(c['case']+'.stdout')).read_text())for c in original if c['case'].startswith('index-')]
    documents={};dumps={}
    try:
        def tree_capture(id):
            assert re.fullmatch('[0-9a-f]{64}',id)
            if id in documents:return
            label='treeblob-'+str(len(documents));doc=json.loads(command(label,['cat','blob',id]));documents[id]=dict(case=label,nodes=doc['nodes'])
            for n in doc['nodes']:
                if n['type']=='dir':tree_capture(n['subtree'])
        for id in trees.values():tree_capture(id)
        initial={'keep.txt':b'unchanged\n','copy-a.txt':b'duplicate payload\n','copy-b.txt':b'duplicate payload\n',
            'changed.txt':b'old content\n','mode.txt':b'mode stable\n','moved-old.txt':b'moved payload\n',
            'deleted.txt':b'deleted payload\n','type-change':b'was regular\n','group/leaf.txt':b'leaf\n',
            'group/deeper/note.txt':b'deeper\n','empty.txt':b''}
        after=dict(initial);after['changed.txt']=b'new content\n';after['moved-new.txt']=after.pop('moved-old.txt');after.pop('deleted.txt');after.pop('type-change')
        after.update({'type-change/child.txt':b'new child\n','added.txt':b'added payload\n'})
        for key,payloads in [('A',initial),('B',after)]:
            observed={n['path'].removeprefix('/')for n in original_lines('ls-'+key)if n.get('type')=='file'};assert observed==set(payloads)
            for i,(path,payload)in enumerate(sorted(payloads.items())):
                label='payload-'+key+'-'+str(i);actual=command(label,['dump',snapshots[key],'/'+path]);assert actual==payload
                dumps[key+'/'+path]=dict(case=label,sha256=hashlib.sha256(actual).hexdigest(),bytes=len(actual))
        changed=next(n for n in documents[trees['B']]['nodes']if n['name']=='changed.txt');data_id=changed['content'][0]
        command('find-data-id',['find','--blob','--snapshot',snapshots['B'],data_id])
        command('find-tree-id',['find','--tree','--snapshot',snapshots['B'],trees['B']])
        assert image(source)==source_before and image(repo)==repository_before
        packs=[p for idx in indexes for p in idx['packs']]
        for kind,id in [('data',data_id),('tree',trees['B'])]:
            candidates=[p for p in packs if any(b['type']==kind and b['id']==id for b in p['blobs'])]
            assert candidates and all(b['type']==kind for b in candidates[0]['blobs']),'No isolated pack of declared kind'
            pack=candidates[0]['id'];assert re.fullmatch('[0-9a-f]{64}',pack)
            clone=work/('omitted-'+kind);assert not clone.exists();shutil.copytree(repo,clone);assert image(clone)==repository_before
            for path in repository_before:assert(repo/path).stat().st_ino!=(clone/path).stat().st_ino,'Unexpected hardlink copy'
            relative='data/'+pack[:2]+'/'+pack;target=clone/relative;assert target.is_file();quarantine=work/('retained-'+kind+'-'+pack)
            h=sha(target);target.rename(quarantine)
            omitted={p:v for p,v in repository_before.items()if p!=relative};assert image(clone)==omitted
            event=dict(kind=kind,blob=id,pack=pack,path=relative,sha256=h,cloneBeforeSha256=digest(repository_before),cloneAfterOmissionSha256=digest(omitted),
                omittedPaths=[relative],retainedPath=str(quarantine.relative_to(RUN)),restoreCompleted=False)
            interventions.append(event);(RUN/'interventions.json').write_text(json.dumps(interventions,indent=2)+'\n')
            for action,args in [('ls',['ls',snapshots['B']]),('find',['find','--snapshot',snapshots['B'],'keep.txt']),
                ('stats',['stats','--mode','raw-data',snapshots['B']]),('dump',['dump',snapshots['B'],'/changed.txt'])]:
                command(kind+'-'+action,args,root=clone,expected=None)
            assert image(clone)==omitted and image(repo)==repository_before and sha(quarantine)==h
            quarantine.rename(target);assert image(clone)==repository_before
            command(kind+'-restored-find',['find','--snapshot',snapshots['B'],'keep.txt'],root=clone)
            assert command(kind+'-restored-dump',['dump',snapshots['B'],'/changed.txt'],root=clone)==after['changed.txt']
            assert image(clone)==image(repo)==repository_before;event.update(restoreCompleted=True,restoredRepositorySha256=digest(image(clone)))
            (RUN/'interventions.json').write_text(json.dumps(interventions,indent=2)+'\n')
        assert image(source)==source_before and image(repo)==repository_before
        assert sha(RUN/'commands.json')==frozen['commands']and sha(RUN/'owned-processes.json')==frozen['owned']and sha(RUN/'probe.py')==frozen['probe']
        assert not list((repo/'locks').glob('*'))
        receipt=dict(schema=1,attribution='Original collector stopped at44commands after mistaken cat tree role. This separate continuation performs remaining reads/controlled copies;original producer,commands and outputs unchanged.',
            producerSha256=hashlib.sha256(PRODUCER).hexdigest(),helperSha256=sha(RUN/'completion-helper.py'),originalPrefixSha256=frozen,
            platform=platform.platform(),tool=pin,snapshots=snapshots,trees=trees,treeDocuments=documents,dumps=dumps,
            originalCommands=len(original),completionCommands=len(rows),sourceBefore=source_before,sourceAfter=image(source),
            repositoryImageSha256=digest(repository_before),repositoryImagePrivatePath='work/private/primary-repository-image.json',
            allOwnedProcessesRetired=all(p.poll()is not None for p in owned),finalLocks=[],
            limits=['No rerun/reclassification of original44commands;one recorded cat tree misuse remains failure. Original source preimages held only in terminated process were not recovered or invented.',
                'Actual saved A/B payloads are independently dumped/checked. This does not requalify physical filesystem metadata preservation or backup race handling.',
                'Only generated local regular-file fixtures and two verified non-hardlinked repository copies. All omitted packs restored and full byte images rechecked;no live repository or recovery authority.',
                'Query/error/count semantics on this macOS build,not remote/backend/platform durability,all flags,hardlinks or corruption repair proof.'])
        (RUN/'completion-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    finally:
        for p in owned:
            if p.poll()is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
        save();print('completion capture',RUN,flush=True)


if __name__=='__main__':main()
