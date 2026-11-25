#!/usr/bin/env python3
"""Read frozen comparison/query/control evidence; no restic or mutation."""
import hashlib,importlib.util,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'applications/evidence/restic-comparison-20261125T031756971775Z'
FAILED=ROOT/'applications/evidence/restic-comparison-20261125T031620264871Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda x:hashlib.sha256((json.dumps(x,sort_keys=True,separators=(',',':'))+'\n').encode()).hexdigest()


def inspect():
    work=RUN/'work'
    receipt=json.loads((work/'private/completion-receipt.json').read_text())
    privacy=json.loads((RUN/'receipt-privacy-readback.json').read_text())
    spec=importlib.util.spec_from_file_location('comparison_frozen_redact',RUN/'completion-helper.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    raw=(work/'private/completion-receipt.json').read_bytes();public=(RUN/'completion-receipt.json').read_bytes()
    assert sha(work/'private/completion-receipt.json')==privacy['rawSha256']and sha(RUN/'completion-receipt.json')==privacy['publicSha256']
    assert helper.redact(raw)==public and sha(RUN/'completion-helper.py')==privacy['helperSha256']==receipt['helperSha256']
    assert sha(RUN/'completion.py')==receipt['producerSha256']
    assert sha(RUN/'commands.json')==receipt['originalPrefixSha256']['commands']and sha(RUN/'probe.py')==receipt['originalPrefixSha256']['probe']
    assert sha(RUN/'owned-processes.json')==receipt['originalPrefixSha256']['owned']
    originals=json.loads((RUN/'commands.json').read_text());completion=json.loads((RUN/'completion-commands.json').read_text())
    assert len(originals)==receipt['originalCommands']==44 and len(completion)==receipt['completionCommands']==41
    assert originals[-1]['case']=='tree-0'and originals[-1]['outcome']['exitCode']==1
    assert receipt['allOwnedProcessesRetired']and receipt['finalLocks']==[]
    for name in ['owned-processes.json','completion-owned-processes.json']:
        assert all(p['retired']for p in json.loads((RUN/name).read_text()))
    commands=originals+completion;assert len({c['case']for c in commands})==len(commands)
    for c in commands:
        assert not c['outcome']['timedOut']and c['outcome']['ownedGroupAbsent']
        for stream,s in c['streams'].items():
            raw=RUN/s['rawPrivatePath'];public=RUN/(c['case']+'.'+stream)
            assert sha(raw)==s['rawSha256']and sha(public)==s['publicSha256']and helper.redact(raw.read_bytes())==public.read_bytes()
    def raw_bytes(label):return(work/'private'/(label+'.stdout')).read_bytes()
    def lines(label):return[json.loads(s)for s in raw_bytes(label).splitlines()]
    by={c['case']:c for c in commands}
    snapshots=receipt['snapshots'];trees=receipt['trees'];documents=receipt['treeDocuments']
    assert len(set(snapshots.values()))==3 and trees['B']==trees['C']and trees['A']!=trees['B']
    for key in snapshots:
        assert next(r for r in lines('backup-'+key)if r.get('message_type')=='summary')['snapshot_id']==snapshots[key]
        header=next(r for r in lines('ls-'+key)if r.get('message_type')=='snapshot')
        assert header['tree']==trees[key]and header['id']==snapshots[key]
    for id,d in documents.items():
        raw=raw_bytes(d['case']);assert hashlib.sha256(raw).hexdigest()==id
        assert json.loads(raw)['nodes']==d['nodes']
        names=[n['name']for n in d['nodes']]
        assert names==sorted(names)and len(names)==len(set(names))
    def walk(id,prefix=''):
        output=[]
        for n in documents[id]['nodes']:
            assert n['type']in['file','dir']and n['name']not in['.','..']and'/'not in n['name']
            if n['type']=='file':assert n.get('links',0)==1,'Hardlink profile is outside the model'
            path=prefix+'/'+n['name'];output.append(dict(path=path,parentTree=id,node=n))
            if n['type']=='dir':output += walk(n['subtree'],path)
        return output
    forests={k:walk(trees[k])for k in snapshots}
    def permissions(n):
        mode=n.get('mode',0)
        assert mode & ~((1<<31)|0o777)==0,'Special mode is outside this profile'
        return ('d'if n['type']=='dir'else'-')+''.join(c if mode & bit else'-'for c,bit in zip('rwxrwxrwx',[256,128,64,32,16,8,4,2,1]))
    def check_listing(label,key):
        records=lines(label)
        header=next(r for r in lines('ls-'+key)if r.get('message_type')=='snapshot')
        assert records[0]==header
        source_by_path={r['path']:r['node']for r in forests[key]}
        for row in records[1:]:
            assert row['message_type']==row['struct_type']=='node'
            n=source_by_path[row['path']]
            expected=dict(name=n['name'],type=n['type'],path=row['path'],uid=n.get('uid',0),gid=n.get('gid',0),
                mtime=n['mtime'],atime=n['atime'],ctime=n['ctime'],message_type='node',struct_type='node')
            if n['type']=='file':expected['size']=n.get('size',0)
            if n.get('mode',0):expected['mode']=n['mode']
            if n.get('inode',0):expected['inode']=n['inode']
            expected['permissions']=permissions(n)
            assert row==expected,(label,row['path'],'listing projection')
    for k,nodes in forests.items():
        listed=[n for n in lines('ls-'+k)if n.get('message_type')=='node']
        assert[(r['path'],r['type'],r.get('size',0))for r in listed]==[(r['path'],r['node']['type'],r['node'].get('size',0))for r in nodes]
        check_listing('ls-'+k,k)
    for label in ['ls-group','ls-recursive','ls-missing','ls-sorted','data-ls','tree-ls']:check_listing(label,'B')
    def listing_paths(label):return[r['path']for r in lines(label)[1:]]
    group=[r['path']for r in forests['B']if r['path']=='/group'or r['path'].startswith('/group/')]
    assert by['ls-group']['args']==['ls',snapshots['B'],'/group']
    assert listing_paths('ls-group')==[p for p in group if p.count('/')<=2]
    assert by['ls-recursive']['args']==['ls','--recursive',snapshots['B'],'/group']
    assert listing_paths('ls-recursive')==group
    assert by['ls-missing']['args']==['ls',snapshots['B'],'/absent']and listing_paths('ls-missing')==[]
    assert by['ls-sorted']['args']==['ls','--sort','size','--reverse',snapshots['B']]
    assert listing_paths('ls-sorted')==[r['path']for r in sorted(forests['B'],key=lambda r:(r['node'].get('size',0),r['path']),reverse=True)]
    assert listing_paths('data-ls')==[r['path']for r in forests['B']]and listing_paths('tree-ls')==[]
    assert by['ls-relative-filter']['args']==['ls',snapshots['B'],'group']and by['ls-relative-filter']['outcome']['exitCode']==1
    sid_to_key={id:k for k,id in snapshots.items()}
    for label in ['find-moved','find-keep','find-reverse','find-case','find-insensitive','find-mtime','find-selected','find-missing',
        'data-find','data-restored-find','tree-restored-find']:
        for group in json.loads(raw_bytes(label)):
            assert group['hits']==len(group['matches'])and group['snapshot']in sid_to_key
            nodes={r['path']:r['node']for r in forests[sid_to_key[group['snapshot']]]}
            for match in group['matches']:
                n=nodes[match['path']]
                hidden={'name','extended_attributes','generic_attributes','device','content','subtree'}
                expected={k:v for k,v in n.items()if k not in hidden}
                expected.update(path=match['path'],permissions=permissions(n))
                assert match==expected,(label,match['path'],'find projection')
    def matches(label):return[(r['snapshot'],[m['path']for m in r['matches']])for r in json.loads(raw_bytes(label))]
    descending=['C','B','A']
    assert by['find-moved']['args']==['find','moved*']
    assert matches('find-moved')==[(snapshots[k],['/moved-old.txt'if k=='A'else'/moved-new.txt'])for k in descending]
    assert by['find-keep']['args']==['find','keep.txt']and by['find-reverse']['args']==['find','--reverse','keep.txt']
    assert matches('find-keep')==[(snapshots[k],['/keep.txt'])for k in descending]
    assert matches('find-reverse')==[(snapshots[k],['/keep.txt'])for k in reversed(descending)]
    assert by['find-case']['args']==['find','KEEP.TXT']and matches('find-case')==[]
    assert by['find-insensitive']['args']==['find','--ignore-case','KEEP.TXT']
    assert matches('find-insensitive')==matches('find-keep')
    assert by['find-mtime']['args']==['find','--oldest','2024-01-01','keep.txt']and matches('find-mtime')==[]
    assert by['find-selected']['args']==['find','--snapshot',snapshots['A'],'moved*']
    assert matches('find-selected')==[(snapshots['A'],['/moved-old.txt'])]
    assert by['find-missing']['args']==['find','never-present']and matches('find-missing')==[]
    for label in['data-find','data-restored-find','tree-restored-find']:
        assert matches(label)==[(snapshots['B'],['/keep.txt'])]
    changed=next(r for r in forests['B']if r['path']=='/changed.txt');blob=changed['node']['content'][0]
    assert by['find-data-id']['args']==['find','--blob','--snapshot',snapshots['B'],blob]
    assert json.loads(raw_bytes('find-data-id'))==[dict(object_type='blob',id=blob,path=changed['path'],parent_tree=changed['parentTree'],snapshot=snapshots['B'],time='2025-01-02T00:00:00Z')]
    assert by['find-tree-id']['args']==['find','--tree','--snapshot',snapshots['B'],trees['B']]
    assert json.loads(raw_bytes('find-tree-id'))==[dict(object_type='tree',id=trees['B'],path='/',snapshot=snapshots['B'],time='2025-01-02T00:00:00Z')]
    for key,d in receipt['dumps'].items():
        raw=raw_bytes(d['case']);assert len(raw)==d['bytes']and hashlib.sha256(raw).hexdigest()==d['sha256']
        snap,path=key.split('/',1);n=next(r['node']for r in forests[snap]if r['path']=='/'+path)
        # Pinned data.Node.Size is uint64 with json omitempty: an absent size
        # in these successfully decoded nodes is the schema's zero, not an
        # unobserved payload. The separate native dump checks actual bytes.
        assert n.get('size',0)==len(raw)
        if raw:assert n['content']==[hashlib.sha256(raw).hexdigest()]
        else:assert not n.get('content')
    assert len(receipt['dumps'])==22
    catalog={}
    for c in originals:
        if not c['case'].startswith('index-'):continue
        for pack in json.loads(raw_bytes(c['case']))['packs']:
            for b in pack['blobs']:
                key=(b['type'],b['id']);plain=b.get('uncompressed_length',0)or b['length']-32
                value=dict(plain=plain,cipher=b['length'],uncompressed=plain+32,compressed=b.get('uncompressed_length',0)>0)
                if key in catalog:assert catalog[key]==value
                catalog[key]=value
    for id,d in documents.items():assert catalog['tree',id]['plain']==len(raw_bytes(d['case']))
    for key,d in receipt['dumps'].items():
        snap,path=key.split('/',1);n=next(r['node']for r in forests[snap]if r['path']=='/'+path)
        for id in n.get('content',[]):assert catalog['data',id]['plain']==d['bytes']
    def refs(key):
        result={('tree',trees[key])}
        for r in forests[key]:
            n=r['node']
            # Go range over nil content has no elements. This reachability
            # projection may merge nil/empty; Node.sameContent for diff may not.
            if n['type']=='file':result.update(('data',id)for id in(n.get('content')or[]))
            if n['type']=='dir':result.add(('tree',n['subtree']))
        return result
    # Independent full reachability is corroborated by a different native
    # command, not copied from diff's partial traversal/counters.
    for label,keys in [('A',['A']),('B',['B']),('BC',['B','C']),('AB',['A','B'])]:
        selected=set().union(*(refs(k)for k in keys));raw=json.loads(raw_bytes('stats-'+label+'-raw-data'))
        assert raw['total_blob_count']==len(selected)and raw['snapshots_count']==len(keys)
        assert raw['total_size']==sum(catalog[k]['cipher']for k in selected)
        assert raw['total_uncompressed_size']==sum(catalog[k]['uncompressed']for k in selected)
    added,removed=refs('B')-refs('A'),refs('A')-refs('B')
    full_added=dict(data=sum(k[0]=='data'for k in added),tree=sum(k[0]=='tree'for k in added),plain=sum(catalog[k]['plain']for k in added))
    diff=lines('diff-default')[-1]
    assert full_added['data']==3 and diff['added']['data_blobs']==2
    assert full_added['tree']==diff['added']['tree_blobs']==2 and full_added['plain']==diff['added']['bytes']+10
    assert ('/type-change/','T')in[(r['path'],r['modifier'])for r in lines('diff-default')if r.get('message_type')=='change']
    assert all(r.get('path')!='/type-change/child.txt'for r in lines('diff-default'))
    # Runtime counters prove distinct count bases; directory entries are included
    # in restore-size's historically named total_file_count field.
    assert json.loads(raw_bytes('stats-B-restore-size'))==dict(total_size=120,total_file_count=14,snapshots_count=1)
    assert json.loads(raw_bytes('stats-B-blobs-per-file'))==dict(total_size=102,total_file_count=9,total_blob_count=9,snapshots_count=1)
    assert json.loads(raw_bytes('stats-BC-restore-size'))['total_size']==240
    for field in ['total_size','total_blob_count']:assert json.loads(raw_bytes('stats-B-raw-data'))[field]==json.loads(raw_bytes('stats-BC-raw-data'))[field]
    assert json.loads(raw_bytes('find-mtime'))==json.loads(raw_bytes('find-missing'))==[]
    assert [r['snapshot']for r in json.loads(raw_bytes('find-keep'))]==[snapshots[k]for k in['C','B','A']]
    assert [r['snapshot']for r in json.loads(raw_bytes('find-reverse'))]==[snapshots[k]for k in['A','B','C']]
    assert len([r for r in lines('ls-group')if r.get('message_type')=='node'])==3
    assert len([r for r in lines('ls-recursive')if r.get('message_type')=='node'])==4
    manifest=json.loads((RUN/receipt['repositoryImagePrivatePath']).read_text());assert digest(manifest)==receipt['repositoryImageSha256']
    def image(root):return{str(p.relative_to(root)):dict(sha256=sha(p),size=p.stat().st_size)for p in root.rglob('*')if p.is_file()}
    assert image(work/'repository')==manifest and image(work/'source')==receipt['sourceBefore']==receipt['sourceAfter']
    for event in json.loads((RUN/'interventions.json').read_text()):
        kind=event['kind'];assert event['restoreCompleted']and event['restoredRepositorySha256']==event['cloneBeforeSha256']==digest(manifest)
        omitted={p:v for p,v in manifest.items()if p not in event['omittedPaths']};assert len(omitted)==len(manifest)-1 and digest(omitted)==event['cloneAfterOmissionSha256']
        assert event['sha256']==manifest[event['path']]['sha256']and not(RUN/event['retainedPath']).exists()
        assert image(work/('omitted-'+kind))==manifest
        for path in manifest:assert(work/'repository'/path).stat().st_ino!=(work/('omitted-'+kind)/path).stat().st_ino
        assert by[kind+'-restored-find']['outcome']['exitCode']==0 and json.loads(raw_bytes(kind+'-restored-find'))
        assert by[kind+'-restored-dump']['outcome']['exitCode']==0 and raw_bytes(kind+'-restored-dump')==b'new content\n'
    assert [by['data-'+k]['outcome']['exitCode']for k in ['ls','find','stats','dump']]==[0,0,0,1]
    assert [by['tree-'+k]['outcome']['exitCode']for k in ['ls','find','stats','dump']]==[1,0,1,1]
    try:json.loads(raw_bytes('tree-find'))
    except json.JSONDecodeError:pass
    else:raise AssertionError('Expected observed invalid mixed JSON stdout')
    assert raw_bytes('tree-find').endswith(b'[]\n')and b'Unable to load tree'in raw_bytes('tree-find')
    for root in ['repository','omitted-data','omitted-tree']:assert not list((work/root/'locks').glob('*'))
    pin=receipt['tool'];assert sha(Path(pin['path']))==pin['sha256']
    tree={r['path']:r for r in json.loads((ROOT/'applications/tools/source-cache/restic-restore-tree.json').read_text())['tree']}
    ledger=json.loads((ROOT/'applications/sources/restic-comparison-selections.json').read_text())
    for r in ledger['sources']:
        p=ROOT/r['cache'];b=p.read_bytes();assert sha(p)==r['sha256']and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['gitBlobSha1']==tree[r['path']]['sha']
    failed=json.loads((FAILED/'commands.json').read_text())
    assert[(c['case'],c['outcome']['exitCode'])for c in failed]==[('init',0),('backup-A',1)]
    assert all(c['outcome']['ownedGroupAbsent']and not c['outcome']['timedOut']for c in failed)
    assert all(p['retired']for p in json.loads((FAILED/'owned-processes.json').read_text()))
    for c in failed:
        for stream,s in c['streams'].items():
            raw=FAILED/s['rawPrivatePath'];public=FAILED/(c['case']+'.'+stream)
            assert sha(raw)==s['rawSha256']and sha(public)==s['publicSha256']and helper.redact(raw.read_bytes())==public.read_bytes()
    refusal=json.loads((FAILED/'backup-A.stderr').read_text())
    assert refusal['message_type']=='exit_error'and refusal['code']==1 and'extra text'in refusal['message']
    assert not list((FAILED/'work/repository/snapshots').glob('*'))
    return receipt,commands,forests,catalog,refs


if __name__=='__main__':
    r,c,f,_,_=inspect();print(json.dumps(dict(originalCommands=r['originalCommands'],completionCommands=r['completionCommands'],snapshots=len(f),dumpedFiles=len(r['dumps']),
        allCopiesRestored=True,findMixedJsonFailureConfirmed=True,diffMissingChildDataBytes=10,modelComparison=False)))
