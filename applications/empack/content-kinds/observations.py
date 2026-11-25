"""Decode the owned ZIPs and captured author trees; never invoke empack."""
import hashlib
import io
import json
from pathlib import PurePosixPath
import zipfile

KINDS={'mod':0,'resource-pack':1,'shader-pack':2,'data-pack':3,'world':4}
CLI={'mod':0,'resourcepack':1,'shader':2,'datapack':3,'world':4}
FILENAMES={'module':'module.jar','resource':'resource.zip','shader':'shader.zip','data':'data.zip','world':'world.zip',
           'resource-jar':'resource-jar.jar','resource-upper':'resource-upper.ZIP','unknown':'unknown.jar'}
BASES={0:'mods',1:'resourcepacks',2:'shaderpacks',3:'config/paxi/datapacks',4:'saves'}


def raw(item):
    return bytes.fromhex(item['bytesHex'])


def zip_facts(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        assert z.testzip() is None
        entries=z.infolist();assert all(not e.is_dir() for e in entries)
        assert len({e.filename for e in entries})==len(entries)
        members={e.filename:z.read(e) for e in entries}
    names=set(members)
    markers=dict(module=bool(names&{'fabric.mod.json','quilt.mod.json','META-INF/mods.toml','META-INF/neoforge.mods.toml','mcmod.info'}),
                 pack='pack.mcmeta' in names,assets=any(n.startswith('assets/') for n in names),
                 data=any(n.startswith('data/') for n in names),shaders=any(n.startswith('shaders/') for n in names),
                 projectRoot='modrinth.index.json' in names,worldRoot='level.dat' in names)
    roots=[n for n in names if n=='level.dat' or n.endswith('/level.dat')]
    nonempty=bool(members[roots[0]]) if len(roots)==1 else None
    prefix=roots[0][:-len('level.dat')] if len(roots)==1 else None
    inside=all(n.startswith(prefix) for n in names) if prefix is not None and nonempty else None
    relative={n[len(prefix):]:v for n,v in members.items()} if inside else {}
    return dict(markers=markers,worldRoots=len(roots),worldNonempty=nonempty,worldInside=inside,
                worldMembers=len(members),members=members,relative=relative)


def request(identity,payload,filename,explicit,dry,accept):
    facts=zip_facts(payload)
    chosen=explicit if explicit is not None else 0 if filename.lower().endswith('.jar') else None
    # These literals are source premises from the frozen AUTHOR layout; not a YAML decoder.
    override=BASES[chosen] if chosen in [3,4] else None
    r=dict(id=identity,explicit=explicit,jar=filename.lower().endswith('.jar'),override=override,
           validArchive=True,acceptUnknown=accept,dryRun=dry,**{k:v for k,v in facts.items() if k not in ['members','relative']})
    return r,facts


def pack_files(images):
    return {p[5:]:r for p,r in images.items() if p.startswith('pack/') and r['kind']=='file'}


def message_reason(row,run):
    if row['exitCode']==0:return 0
    text=(run/(row['id']+'.stdout')).read_text()+(run/(row['id']+'.stderr')).read_text()
    if 'supply --type' in text:
        assert row['exitCode']==2
        return 1
    assert row['exitCode']==1
    for message,code in [('requires project/world import interpretation',4),('explicit acceptance is required',5),
                         ('exactly one nonempty level.dat',6)]:
        if message in text:return code
    raise AssertionError(('Unqualified failure cause',row['id']))


def changed_pack(row):
    before,after=pack_files(row['before']),pack_files(row['after'])
    assert not(set(before)-set(after)),row['id']
    changed={p:r for p,r in after.items() if p not in before or before[p]['sha256']!=r['sha256']}
    return changed


def root_projection(document,images,key,identity,intended_kind):
    row=next(r for r in document['dependencies'] if r['key']==key)
    effective=row['effective'];assert effective['content'] in KINDS
    kind=intended_kind
    assert row['explicit'] and row['selection_satisfied']
    assert effective['environment']['client']=='required'
    env=effective['environment']['server'];assert env in ['required','unsupported']
    placement=effective['placement']
    filename=FILENAMES[key]
    payload=raw(images['vendor/'+filename])
    facts=zip_facts(payload)
    if placement=='automatic':
        digest=hashlib.sha256(payload).hexdigest()
        destinations=[p for p,r in pack_files(images).items() if r['sha256']==digest]
        assert len(destinations)==1
    elif isinstance(placement,list):
        assert all(p['environment']==effective['environment'] and p['layer']=='common' for p in placement)
        destinations=[p['destination'] for p in placement]
    else:
        assert kind==4 and list(placement)==['files']
        destinations=[]
        for member,values in placement['files'].items():
            assert member in facts['relative'] and len(values)==1
            assert values[0]['environment']==effective['environment'] and values[0]['layer']=='common'
            destinations.append(values[0]['destination'])
    if kind==4:
        assert effective['source']['kind']=='local-files'
        for member,source in effective['source']['members'].items():
            assert source.startswith('pack/') and source[5:] in destinations
            assert raw(images[source])==facts['relative'][member]
        assert sorted(effective['source']['members'])==sorted(facts['relative'])
    else:
        assert effective['source']==dict(kind='local',path='vendor/'+filename)
        for path in destinations:assert raw(images['pack/'+path])==payload
    return dict(id=identity,kind=kind,base=BASES[kind],filename=filename,key=key,members=sorted(facts['relative']) if kind==4 else []),\
           dict(id=identity,content=effective['content'],serverRequired=env=='required',sourceKind=effective['source']['kind'],destinations=sorted(destinations))


def packets(primary,sync,layout):
    admissions=[];observed=[];metadata=[];metadata_out=[];intended_kinds={}
    rows=json.loads((primary/'commands.json').read_text())
    for row in rows:
        if not row['id'].startswith('continued-') or 'add' not in row['argv']:continue
        args=row['argv'][row['argv'].index('add')+1:]
        filename=PurePosixPath(args[-1]).name
        assert args[-1]==str(PurePosixPath(json.loads((primary/'setup.json').read_text())['work'])/'project/vendor'/filename)
        explicit=CLI[args[args.index('--type')+1]] if '--type' in args else None
        dry='--dry-run' in row['argv']
        payload=raw(row['before']['vendor/'+filename])
        value,facts=request(row['id'],payload,filename,explicit,dry,False)
        admissions.append(value)
        added=changed_pack(row)
        reason=message_reason(row,primary)
        observed.append(dict(id=row['id'],admitted=row['exitCode']==0,reason=reason,materialized=bool(added),outputs=len(added)))
        if reason or dry:assert row['before']==row['after']
        if added:
            chosen=explicit if explicit is not None else 0
            key=PurePosixPath(filename).stem
            assert key not in intended_kinds
            intended_kinds[key]=chosen
            if chosen==4:
                assert sorted(p.rsplit('/world/',1)[-1] for p in added)==sorted(facts['relative'])
                for p,r in added.items():assert raw(r)==facts['relative'][p.rsplit('/world/',1)[-1]]
            else:
                assert len(added)==1 and raw(next(iter(added.values())))==payload
    sync_rows=json.loads((sync/'commands.json').read_text());row=sync_rows[1]
    assert row['id']=='sync-declared-unknown'
    value,_=request(row['id'],raw(row['before']['vendor/unknown.jar']),'unknown.jar',0,False,True)
    admissions.append(value)
    added=changed_pack(row);assert len(added)==1 and raw(next(iter(added.values())))==raw(row['before']['vendor/unknown.jar'])
    observed.append(dict(id=row['id'],admitted=row['exitCode']==0,reason=0,materialized=True,outputs=1))
    document=json.loads((primary/'manifest.json').read_text())
    assert document['lock_status']=='current' and document['runtime_satisfied'] is True
    assert len(document['dependencies'])==len(intended_kinds)
    assert {r['key'] for r in document['dependencies']}==set(intended_kinds)
    for r in document['dependencies']:
        value,out=root_projection(document,rows[-1]['after'],r['key'],'stored:'+r['key'],intended_kinds[r['key']]);metadata.append(value);metadata_out.append(out)
    document=json.loads((sync/'after-manifest.json').read_text())
    assert document['lock_status']=='current'
    value,out=root_projection(document,sync_rows[-1]['after'],'unknown','stored:unknown',0);metadata.append(value);metadata_out.append(out)
    layout_rows=json.loads((layout/'commands.json').read_text());current=layout_rows[-1]['after']
    edits,=json.loads((layout/'owner-edits.json').read_text())
    before=raw(edits['before']['empack.yml']).decode();after=raw(edits['after']['empack.yml']).decode()
    assert after==before.replace('layout: {data-pack:','layout: {mod: custom-mods, data-pack:')
    placements=[];placement_out=[]
    prior={r['key']:r['effective']['placement'] for r in document['dependencies']}
    later={r['key']:r['effective']['placement'] for r in json.loads((layout/'after-manifest.json').read_text())['dependencies']}
    assert isinstance(prior['module'],list) and prior['module'][0]['destination']=='mods/module.jar'
    assert prior['unknown']=='automatic'
    assert prior['module']==later['module'] and prior['unknown']==later['unknown']
    for key,automatic in [('module',False),('unknown',True)]:
        filename=FILENAMES[key];digest=hashlib.sha256(raw(current['vendor/'+filename])).hexdigest()
        paths=[p for p,r in pack_files(current).items() if r['sha256']==digest];assert len(paths)==1
        placements.append(dict(id='layout:'+key,automatic=automatic,fixed='mods/'+filename,base='custom-mods',filename=filename))
        placement_out.append(dict(id='layout:'+key,destination=paths[0]))
    assert 'pack/mods/unknown.jar' not in current
    suffixes=[];suffix_out=[]
    for key in ['resource','resource-jar','resource-upper']:
        filename=FILENAMES[key];item=current['pack/resourcepacks/'+filename];assert item['kind']=='file'
        suffixes.append(dict(id='vanilla-source:'+key,regular=True,filename=filename))
        suffix_out.append(dict(id='vanilla-source:'+key,candidate=filename.endswith('.zip')))
    return dict(schema=1,admissions=admissions,metadata=metadata,placements=placements,suffixes=suffixes),\
           dict(admissions=observed,metadata=metadata_out,placements=placement_out,suffixes=suffix_out)
