"""Scoped projection of raw owned-fixture observations;not a production path guard."""
import copy
import unicodedata

FLAGS=['policyAllows','complete','identityCurrent','scopeMatches','authority','boundaryBound']


def token(info):
    assert type(info)is dict and type(info.get('available'))is bool
    if not info['available']:
        assert type(info.get('error'))is str
        return None
    assert set(info)=={'available','device','inode'}
    assert type(info['device'])is str and info['device'].isdigit()
    assert type(info['inode'])is str and info['inode'].isdigit()and int(info['inode'])>0
    return info['device'],info['inode']


def facts(relation,complete,current=True,scope=True):
    return dict(policyAllows=True,relation=relation,complete=complete,identityCurrent=current,
                scopeMatches=scope,authority=False,boundaryBound=False)


def key(row):
    assert set(row)==set(FLAGS)|{'relation'}
    assert all(type(row[k])is bool for k in FLAGS)
    assert type(row['relation'])is int and 0<=row['relation']<=2
    return ':'.join(str(int(row[k]))for k in ['policyAllows','relation','complete','identityCurrent','scopeMatches','authority','boundaryBound'])


def project(record):
    assert record['schema']==1 and record['contract']=='owned-path-observations-v1'
    assert record['ownedSourcePreserved']is True and record['ownedRebindRestored']is True
    rows=record['cases'];assert 9<=len(rows)<=11 and len({r['case']for r in rows})==len(rows)
    required={'exact-object','case-alias-first-lookup','separate-sibling','target-contains-source','target-inside-source',
              'missing-target','unicode-normalization-first-lookup','preflight-binding-replaced'}
    assert required<={r['case']for r in rows}
    assert {r['case']for r in rows}<=required|{'case-distinct-created','unicode-distinct-created','symlink-alias','symlink-unavailable'}
    assert len([r for r in rows if r['case']in ['symlink-alias','symlink-unavailable']])==1
    result=[];root=None;pairs={}
    for row in rows:
        name=row['case'];o=row['observed']
        if row['kind']=='unavailable':
            assert name=='symlink-unavailable'and type(o['error'])is str
            result.append(dict(case=name,input=facts(0,False,current=False)));continue
        if row['kind']=='rebound':
            assert name=='preflight-binding-replaced'
            before=o['before'];s,t=token(before['source']),token(before['target']);now=token(o['nowTarget'])
            assert s and t and s!=t and now==s and now!=t
            assert token(o['oldSource'])is None and o['sourcePayloadPreserved']is True
            assert pairs['separate-sibling']==(s,t)
            result.append(dict(case=name+'/stale',input=facts(2,True,current=now==t)))
            # The observed rename retains the captured protected object;this is
            # not an identity token that survives arbitrary deletion/ID reuse.
            result.append(dict(case=name+'/now',input=facts(1,True)));continue
        assert row['kind']=='pair'and row['request']['operation']=='protected-tree-preflight'
        request=row['request'];assert type(request['source'])is str and type(request['target'])is str
        assert type(o['exactSpellingEqual'])is bool and o['exactSpellingEqual']==(request['source']==request['target'])
        assert type(o['nfcSpellingEqual'])is bool and o['nfcSpellingEqual']==(unicodedata.normalize('NFC',request['source'])==unicodedata.normalize('NFC',request['target']))
        s,t=token(o['source']),token(o['target']);same=o['samefile']
        assert same is None or type(same)is bool
        if s and t:assert same==(s==t)
        else:assert same is None
        chains=[]
        for label,first in [('source',s),('target',t)]:
            c=o[label+'Chain'];assert type(c['complete'])is bool
            ids=[token(i)for i in c['entries']];assert all(ids)
            if c['complete']:
                assert ids and ids[0]==first
                if root is None:root=ids[-1]
                else:assert ids[-1]==root
            chains.append(ids)
        complete=bool(s and t and o['sourceChain']['complete']and o['targetChain']['complete'])
        if s and t and same:relation=1
        elif complete:relation=1 if t in chains[0]or s in chains[1]else 2
        else:relation=0
        pairs[name]=(s,t)
        result.append(dict(case=name,input=facts(relation,complete)))
    assert root
    return result


def changed(record,case):
    r=copy.deepcopy(record)
    return r,next(x for x in r['cases']if x['case']==case)
