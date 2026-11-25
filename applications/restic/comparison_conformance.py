#!/usr/bin/env python3
"""Pure replay of frozen saved trees/indexes and CLI results; no restic runs."""
import copy,hashlib,json,os,subprocess
from pathlib import Path
import comparison_observations as observations

ROOT,HERE,RUN=observations.ROOT,Path(__file__).resolve().parent,observations.RUN
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def raw(label):return(RUN/'work/private'/(label+'.stdout')).read_bytes()
def parsed(label):return json.loads(raw(label))
def lines(label):return[json.loads(line)for line in raw(label).splitlines()]
def compare(expected,actual):assert expected==actual,(expected,actual)


def build(receipt,commands,forests,catalog):
    ids=sorted({id for _,id in catalog});labels={s:i+1 for i,s in enumerate(ids)}
    metadata=[];snapshots=[]
    for i,key in enumerate(['A','B','C']):
        nodes=[]
        for row in forests[key]:
            n=row['node'];assert not n.get('generic_attributes')
            # Selected fixture uses identical timestamp spellings for equality;
            # no general Go time.Equal, attributes, or Node JSON parser proof.
            fields={k:n.get(k,0)for k in['mode','uid','gid','inode','device_id','size','links','device']}
            fields.update({k:n.get(k,'')for k in['name','type','mtime','atime','ctime','user','group','linktarget','error']})
            attributes=n.get('extended_attributes')or[]
            assert len({a['name']for a in attributes})==len(attributes)
            fields.update(subtree=n.get('subtree'),extended_attributes=sorted(attributes,key=lambda a:a['name']))
            basis=json.dumps(fields,sort_keys=True,separators=(',',':'))
            if basis not in metadata:metadata.append(basis)
            path=row['path'].strip('/').split('/')
            nodes.append(dict(path=path,location=path+[n['name']],kind=n['type'],contentPresent=n.get('content')is not None,
                content=[labels[s]for s in(n.get('content')or[])],metadataBasis=metadata.index(basis)+1,
                subtree=labels[n['subtree']]if n.get('subtree')else None,size=n.get('size',0)))
        snapshots.append(dict(id=i+1,root=labels[receipt['trees'][key]],nodes=nodes))
    encoded_catalog=[dict(handle=dict(kind=kind,id=labels[id]),plain=b['plain'],cipher=b['cipher'],
        uncompressedCipher=b['uncompressed'],compressed=b['compressed'])for(kind,id),b in sorted(catalog.items())]
    sid={s:i+1 for i,s in enumerate(receipt['snapshots'].values())};assert list(receipt['snapshots'])==['A','B','C']
    rows=[]
    def entry(case,kind,expected,**fields):
        data=dict(kind=kind,mode='',selected=[],metadata=False,fullClosure=False,fixSearch=False,availability='present',query='')
        data.update(fields);rows.append(dict(case=case,input=data,expected=expected))
    for c in commands:
        case,args=c['case'],c['args']
        if case.startswith('stats-')and case!='stats-bad-mode':
            value=parsed(case);keys=['total_size','total_file_count','total_blob_count','snapshots_count','total_uncompressed_size']
            mode=args[2];expected=[value.get(k,0)for k in keys]+[0,0]
            if mode=='raw-data':
                selected_ids=set()
                for id in args[3:]:
                    key=next(k for k,s in receipt['snapshots'].items()if s==id)
                    selected_ids.add(('tree',receipt['trees'][key]))
                    for r in forests[key]:
                        n=r['node'];selected_ids.update(('data',s)for s in(n.get('content')or[]))
                        if n.get('subtree'):selected_ids.add(('tree',n['subtree']))
                compressed=[catalog[k]for k in selected_ids if catalog[k]['compressed']]
                expected[5:]=[sum(b['cipher']for b in compressed),sum(b['uncompressed']for b in compressed)]
                # Independent native IEEE-754 formatting checks stay outside
                # the integer models. Native percentages are not invented ints.
                assert abs(value['compression_ratio']-expected[4]/expected[0])<1e-12
                assert abs(value['compression_space_saving']-(1-expected[5]/expected[6])*100)<1e-10
                assert value['compression_progress']==100
                assert set(value)=={'total_size','total_uncompressed_size','compression_ratio','compression_progress','compression_space_saving','total_blob_count','snapshots_count'}
            else:
                allowed={'total_size','total_file_count','snapshots_count'}
                if mode=='blobs-per-file':allowed.add('total_blob_count')
                assert set(value)==allowed
            entry(case,'stats',expected,mode=mode,selected=[sid[s]for s in args[3:]])
        elif case.startswith('diff-'):
            records=lines(case);summary=records[-1]
            def delta(d):
                assert d['others']==0
                return[d[k]for k in['files','dirs','data_blobs','tree_blobs','bytes']]
            expected=dict(events=[r['path']+'|'+r['modifier']for r in records[:-1]],changedFiles=summary['changed_files'],
                added=delta(summary['added']),removed=delta(summary['removed']))
            entry(case,'diff',expected,selected=[sid[s]for s in args if s in sid],metadata='--metadata'in args)
    query_names=dict(ls='listing',find='search',stats='statistics',dump='payload')
    by={c['case']:c for c in commands}
    for kind in ['data','tree']:
        for operation,query in query_names.items():
            case=kind+'-'+operation;status=by[case]['outcome']['exitCode'];bytes_=raw(case)
            if operation=='dump':valid=True;value=status==0
            elif operation=='ls':
                decoded=[json.loads(line)for line in bytes_.splitlines()];valid=True;value=bool(decoded)
            else:
                try:value_=json.loads(bytes_);valid=True;value=value_ is not None
                except json.JSONDecodeError:
                    # Empty output on an unsuccessful stats call has no value
                    # and violates no promised emitted JSON value. Mixed human
                    # text followed by [] does violate the find array protocol.
                    valid=not bytes_.strip();value=False
            complete=status==0 and valid
            entry(case,'read',dict(exitCode=status,protocolValid=valid,complete=complete,valueAvailable=value),
                query=query,availability='missingData'if kind=='data'else'missingRootTree')
        for operation in ['find','dump']:
            case=kind+'-restored-'+operation;assert by[case]['outcome']['exitCode']==0
            entry(case,'read',dict(exitCode=0,protocolValid=True,complete=True,valueAvailable=True),query=query_names[operation])
    # Proposed outputs are independently derived from saved tree/index facts;
    # they are never relabeled as outcomes of the unchanged native executable.
    def full_refs(key):
        refs={('tree',receipt['trees'][key])}
        for r in forests[key]:
            n=r['node'];refs.update(('data',s)for s in(n.get('content')or[]))
            if n.get('subtree'):refs.add(('tree',n['subtree']))
        return refs
    for native,before,after in[('diff-default','A','B'),('diff-reverse','B','A')]:
        original=next(r for r in rows if r['case']==native);expected=copy.deepcopy(original['expected'])
        for side,refs in[('added',full_refs(after)-full_refs(before)),('removed',full_refs(before)-full_refs(after))]:
            expected[side][2:]=[sum(k[0]=='data'for k in refs),sum(k[0]=='tree'for k in refs),sum(catalog[k]['plain']for k in refs)]
        entry(native+'-closure-proposal','diff',expected,selected=original['input']['selected'],fullClosure=True)
        rows[-1]['basis']='Proposed complete-reference counters over independently read native trees; no patched CLI execution.'
    for key in['A','B']:
        nodes=[r for r in forests[key]if r['node']['type']=='file'and r['node'].get('content')]
        refs={(r['path']+'/'+r['node']['name'],s)for r in nodes for s in r['node']['content']}
        expected=[sum(catalog['data',s]['plain']for _,s in refs),len({path for path,_ in refs}),len(refs),1,0,0,0]
        entry('stats-'+key+'-path-reference-proposal','stats',expected,mode='path-references-proposal',selected=[sid[receipt['snapshots'][key]]])
        rows[-1]['basis']='Proposed strict location/reference count, not a selected replacement for rename-resilient source policy.'
    entry('tree-find-completion-proposal','read',dict(exitCode=1,protocolValid=True,complete=False,valueAvailable=True),
        query='search',availability='missingRootTree',fixSearch=True)
    rows[-1]['basis']='Proposed failure with a valid partial result array; not patched native output.'
    data=dict(schema=1,profile='restic-regular-saved-trees',catalog=encoded_catalog,snapshots=snapshots,rows=[r['input']for r in rows])
    return data,rows,dict(opaqueIds=len(labels),metadataClasses=len(metadata),
        metadataBasisSha256=hashlib.sha256(json.dumps(metadata,separators=(',',':')).encode()).hexdigest())


def bend_list(values,encode):
    out='Nil{}'
    for v in reversed(values):out='Con{'+encode(v)+','+out+'}'
    return out
def bend_call(data,row):
    b=lambda x:'True{}'if x else'False{}';n=lambda x:str(x)+'n'
    components=sorted({p for s in data['snapshots']for r in s['nodes']for p in r['path']})
    p=lambda xs:bend_list(xs,lambda x:n(components.index(x)+1))
    def node(r):return'S.CNode{'+','.join([p(r['path']),p(r['location']),b(r['kind']=='dir'),b(r['contentPresent']),bend_list(r['content'],n),
        n(r['metadataBasis']),'None{}'if r['subtree']is None else'Some{'+n(r['subtree'])+'}',n(r['size'])])+'}'
    def snap(s):return'S.CSnapshot{'+n(s['root'])+','+bend_list(s['nodes'],node)+'}'
    def blob(v):return'S.CBlob{S.CHandle{'+b(v['handle']['kind']=='tree')+','+n(v['handle']['id'])+'},'+','.join([n(v['plain']),n(v['cipher']),n(v['uncompressedCipher']),b(v['compressed'])])+'}'
    cat=bend_list(data['catalog'],blob);r=row['input'];ss=[next(s for s in data['snapshots']if s['id']==id)for id in r['selected']]
    if r['kind']=='stats':
        args=bend_list(ss,snap);mode=r['mode']
        call={'restore-size':lambda:'S.stats_text(S.restore_stats('+args+'))',
            'files-by-contents':lambda:'S.stats_text(S.content_stats('+args+'))',
            'blobs-per-file':lambda:'S.maybe_stats(S.reference_stats('+cat+','+args+',True{}))',
            'path-references-proposal':lambda:'S.maybe_stats(S.reference_stats('+cat+','+args+',False{}))',
            'raw-data':lambda:'S.maybe_stats(S.raw_stats('+cat+','+args+'))'}[mode]()
        return call,None
    if r['kind']=='read':return'S.read_outcome('+b(r['fixSearch'])+','+n(['listing','search','statistics','payload'].index(r['query']))+','+n(['present','missingData','missingRootTree'].index(r['availability']))+')',None
    # Bend checks each path's decision. The component-order traversal witness
    # is external here; Lean independently orders the paired saved paths.
    paths=sorted({tuple(v['path'])for s in ss for v in s['nodes']})
    a,c=map(snap,ss);call='S.diff_text('+cat+','+b(r['fullClosure'])+','+a+','+c+')'
    for path in paths:call+=' ++ "|" ++ S.event_modifier('+b(r['metadata'])+','+a+','+c+','+p(path)+')'
    return call,paths


def main():
    receipt,commands,forests,catalog,_=observations.inspect();data,rows,witnesses=build(receipt,commands,forests,catalog)
    generated=HERE/'generated';generated.mkdir(exist_ok=True)
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1')
    target=ROOT/'.build/formal/applications/restic/Comparison.olean';target.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.run([lean,'-DwarningAsError=true','-o',str(target),'applications/restic/Comparison.lean'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    assert p.returncode==0,p.stdout+p.stderr
    path=generated/'comparison.json'
    def replay(value):
        path.write_text(json.dumps(value)+'\n')
        return subprocess.run([lean,'--run','applications/restic/ComparisonCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    p=replay(data);assert p.returncode==0,p.stdout+p.stderr;actual=json.loads(p.stdout)
    expected=[r['expected']for r in rows];compare(expected,actual)
    calls=[bend_call(data,r)for r in rows];driver=generated/'ComparisonCase.bend'
    driver.write_text('import Base\nimport ../Comparison.bend as S\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(call+' ++ "\\n"'for call,_ in calls)+')\n')
    p=subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=120);assert p.returncode==0,p.stdout+p.stderr
    bend_rows=[]
    for row,line,(_,paths)in zip(rows,p.stdout.splitlines(),calls,strict=True):
        fields=line.split('|');r=row['input']
        if r['kind']=='stats':value=list(map(int,fields))
        elif r['kind']=='read':
            assert len(fields)==4 and all(v in['0','1']for v in fields)
            value=dict(exitCode=int(fields[0]),protocolValid=fields[1]=='1',complete=fields[2]=='1',valueAvailable=fields[3]=='1')
        else:
            assert len(fields)==11+len(paths)
            a,c=[next(s for s in data['snapshots']if s['id']==id)for id in r['selected']];events=[]
            for path_,modifier in zip(paths,fields[11:],strict=True):
                if not modifier:continue
                node=next((n for n in c['nodes']if n['path']==list(path_)),None)or next(n for n in a['nodes']if n['path']==list(path_))
                events.append('/'+'/'.join(path_)+('/'if node['kind']=='dir'else'')+'|'+modifier)
            value=dict(events=events,changedFiles=int(fields[0]),added=list(map(int,fields[1:6])),removed=list(map(int,fields[6:11])))
        bend_rows.append(value)
    compare(expected,bend_rows)
    refusals=[]
    for name,edit in [('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='arbitrary-tree')),
        ('catalog-kind',lambda d:d['catalog'][0]['handle'].update(kind='pack')),('duplicate-catalog',lambda d:d['catalog'].append(d['catalog'][0])),
        ('weight',lambda d:d['catalog'][0].update(uncompressedCipher=0)),('node-kind',lambda d:d['snapshots'][0]['nodes'][0].update(kind='symlink')),
        ('saved-path',lambda d:d['snapshots'][0]['nodes'][0].update(path=['..'])),('location',lambda d:d['snapshots'][0]['nodes'][0].update(location=['elsewhere'])),
        ('content-presence',lambda d:d['snapshots'][0]['nodes'][0].update(contentPresent=False)),
        ('duplicate-snapshot',lambda d:d['snapshots'].append(d['snapshots'][0])),('snapshot-selection',lambda d:d['rows'][0].update(selected=[4096])),
        ('count-mode',lambda d:next(r for r in d['rows']if r['kind']=='stats').update(mode='unrecognized')),
        ('read-scope',lambda d:next(r for r in d['rows']if r['kind']=='read').update(query='integrity')),
        ('field-type',lambda d:d['rows'][0].update(metadata='false')),('missing-field',lambda d:d['rows'][0].pop('metadata'))]:
        bad=copy.deepcopy(data);edit(bad);p=replay(bad);assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);refusals.append(name)
    premise_mutations=[]
    for name,edit in [('weight-basis',lambda d:d['catalog'][0].update(plain=d['catalog'][0]['plain']+1,uncompressedCipher=d['catalog'][0]['uncompressedCipher']+1,
            cipher=d['catalog'][0]['cipher']+(not d['catalog'][0]['compressed']))),
        ('snapshot-selection',lambda d:next(r for r in d['rows']if r['kind']=='stats'and r['selected']==[1]).update(selected=[2])),
        ('counter-policy',lambda d:d['rows'][0].update(fullClosure=True)),
        ('read-availability',lambda d:next(r for r in d['rows']if r['kind']=='read'and r['availability']=='missingRootTree').update(availability='present'))]:
        bad=copy.deepcopy(data);edit(bad);p=replay(bad);assert p.returncode==0,p.stdout+p.stderr
        try:compare(expected,json.loads(p.stdout))
        except AssertionError:premise_mutations.append(name)
        else:raise AssertionError('Changed premise escaped: '+name)
    mutations=[]
    for name,case,field in [('changed-counter','diff-default','added'),('event-policy','diff-default','events'),('count-basis','stats-A-restore-size',None),
        ('query-exit','tree-find','exitCode'),('query-protocol','tree-find','protocolValid'),('query-coverage','data-ls','complete')]:
        index=next(i for i,r in enumerate(rows)if r['case']==case)
        bad=copy.deepcopy(expected)
        if field is None:bad[index][0]+=1
        elif isinstance(bad[index][field],list):bad[index][field]=[]
        elif isinstance(bad[index][field],bool):bad[index][field]=not bad[index][field]
        else:bad[index][field]+=1
        try:compare(bad,actual)
        except AssertionError:mutations.append(name)
        else:raise AssertionError('Changed observation escaped: '+name)
    unknown=copy.deepcopy(data);unknown['catalog']=[];p=replay(unknown);assert p.returncode==0,p.stdout+p.stderr
    unknown_values=json.loads(p.stdout)
    for r,old,value in zip(rows,actual,unknown_values,strict=True):
        if r['input']['kind']=='diff':
            # An equal-tree diff demands no weights and legitimately retains
            # exact zeros. Missing measurements are not confused with emptiness.
            if old['added'][2:4]!=[0,0]or old['removed'][2:4]!=[0,0]:assert value is None
            else:compare(old,value)
        elif r['input']['mode']in['raw-data','blobs-per-file','path-references-proposal']:assert value is None
    sources=[HERE/name for name in ['Comparison.lean','Comparison.bend','ComparisonCase.lean','comparison_probe.py','comparison_complete.py','comparison_observations.py','comparison_conformance.py']]
    sources +=[ROOT/'applications/sources/restic-comparison-selections.json']
    sources +=[p for run in[RUN,observations.FAILED]for p in run.iterdir()if p.is_file()and p.name!='conformance.json']
    result=dict(schema=1,nativeCommands=len(commands),modelRows=len(rows),currentNativeRows=sum('basis'not in r for r in rows),proposalRows=sum('basis'in r for r in rows),comparisons=[dict(**r,model=a)for r,a in zip(rows,actual)],
        normalizedWitnesses=witnesses,normalizedBasis=dict(catalog=data['catalog'],snapshots=data['snapshots']),
        researchRefusals=refusals,normalizedPremiseMutations=premise_mutations,observationMutations=mutations,
        unavailableWeightsReturnUnknown=True,driverSha256=sha(driver),basisSha256={str(p.relative_to(ROOT)):sha(p)for p in sorted(set(sources))},
        tools={n:dict(path=str(Path(p).resolve()),sha256=sha(Path(p)))for n,p in[('lean',lean),('bend',bend)]},
        limits=['Pure replay of retained source/native observations;no native collection,backup,restore,repair,or application rerun.',
            'Two typed models compare four size modes,diff events/counters,and root-load read outcomes after argument admission.',
            'Bend receives finite saved component labels and external path-order/metadata-equality witnesses;Lean orders the saved path union itself. General Go codecs,glob/case/time parsing and cryptography remain outside both.',
            'Listing/search selection and all exported metadata fields are independently checked by the Python observer,not formally modeled selection policies in this band.',
            'Native missing-tree find output is intentionally invalid;the observer does not strip diagnostics and certify the trailing array.',
            'Full-closure and path-reference policies are proposed;current native behavior remains unchanged. Hardlinks,special files,nested faults,remote and other host profiles remain unqualified.',
            'Integer compression weights are modeled;reported floating ratios/percentages use separate numeric comparisons.'])
    (RUN/'conformance.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in['comparisons','normalizedBasis','basisSha256','tools']},indent=2))


if __name__=='__main__':main()
