#!/usr/bin/env python3
"""Read-only native projection; no Cargo invocation or Cargo fingerprint encoder."""
import hashlib
import json
from pathlib import Path
import re

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
key=lambda v:json.dumps(v,separators=(',',':'))
def option(text):
    if text=='None':return None
    assert text.startswith('Some(')and text.endswith(')')
    return json.loads(text[5:-1])
def data(text):
    m=re.fullmatch(r'tracked=(None|Some\(.*\));hidden=(None|Some\(.*\));file=(first|second|third);fail=(false|true)',text)
    assert m,text
    return [option(m[1]),option(m[2]),m[3],m[4]=='true']
def signature(value):return [value[0],value[2],value[3]]
def journal(text):
    lines=text.splitlines();assert len(lines)%3==0
    records=[]
    for i in range(0,len(lines),3):
        assert lines[i].startswith('start ')and lines[i+1].startswith('wrote ')and lines[i+2]in ['success','failed']
        records.append(dict(data=data(lines[i][6:]),success=lines[i+2]=='success'))
    return records

def project(run,overrides=None):
    overrides=overrides or {};rows=overrides.get('commands.json',json.loads((run/'commands.json').read_text()))
    runtime={};values={};bases={};requests={}
    for c in rows:
        assert not c['timedOut']and c['ownedGroupAbsent']
        for s in ['stdout','stderr']:assert sha(run/(c['case']+'.'+s))==c['streams'][s]
        if c['kind']=='run':
            assert c['before']==c['after']and c['exitCode']==0
            output=(run/(c['case']+'.stdout')).read_text().strip();v,macro=output.split('|macro=')
            decoded=(data(v),option(macro));h=c['after']['binary']
            if h in runtime:assert runtime[h]==decoded
            runtime[h]=decoded;values[key(decoded[0])]=decoded[0]
        for side in ['before','after']:
            s=c[side]
            for e in journal(s['journal']):
                v=e['data'];values[key(v)]=v;bases[key(signature(v))]=signature(v)
            if s['generated']is not None:values[key(data(s['generated']))]=data(s['generated'])
        if c['kind']=='build':
            image=c['before']['project']['input.txt'];matched=[v for v in ['first','second','third']if hashlib.sha256((v+'\n').encode()).hexdigest()==image['sha256']];assert len(matched)==1
            env=c['environment'];v=[env['RULES_TRACKED'],env['RULES_HIDDEN'],matched[0],env['RULES_FAIL']is not None]
            values[key(v)]=v;bases[key(signature(v))]=signature(v);requests[c['case']]=v
    value_ids={k:i+1 for i,k in enumerate(sorted(values))};basis_ids={k:i+1 for i,k in enumerate(sorted(bases))}
    def fp(target,suffix):
        candidates=[v for p,v in(target or{}).items()if p.endswith(suffix)]
        assert len(candidates)<=1
        if not candidates:return False,False
        assert candidates[0]['bytes']in [0,16]
        return True,candidates[0]['bytes']==16
    def state(s):
        entries=journal(s['journal']);success=[e['data']for e in entries if e['success']]
        exists,valid=fp(s['target'],'/run-build-script-build-script-build')
        if exists:assert success,'Fingerprint without a successful observed script basis'
        basis=basis_ids[key(signature(success[-1]))]if exists else 0
        _,rust_valid=fp(s['target'],'/bin-rules-freshness')
        selected=[v for p,v in(s['target']or{}).items()if p.endswith('/out/selected.txt')]
        if s['generated']is None:assert not selected
        else:
            assert len(selected)==1 and selected[0]['sha256']==hashlib.sha256(s['generated'].encode()).hexdigest()
        gen=0 if s['generated']is None else value_ids[key(data(s['generated']))]
        assert s['binary']==(s['target']or{}).get('debug/rules-freshness',{}).get('sha256')
        compiled=runtime.get(s['binary'])
        assert compiled is not None or s['binary']is None
        binary=0 if compiled is None else value_ids[key(compiled[0])]
        macro=0 if compiled is None else {'macro-first':1,'macro-second':2}[compiled[1]]
        return dict(scriptValid=valid,basis=basis,generated=gen,rustValid=rust_valid,binary=binary,macroValue=macro,runs=len(entries))
    projected=[]
    for c in rows:
        if c['kind']=='run':continue
        before,after=state(c['before']),state(c['after']);is_clean=c['kind']=='clean'
        wanted=requests.get(c['case']);inp=dict(action=1 if is_clean else 0,state=before,
            basis=0 if is_clean else basis_ids[key(signature(wanted))],dataValue=0 if is_clean else value_ids[key(wanted)],
            macroValue=0 if is_clean else {'macro-first':1,'macro-second':2}[c['environment']['RULES_MACRO']],fail=False if is_clean else wanted[3])
        messages=c['messages'];assert messages==[]or[json.loads(s)for s in(run/(c['case']+'.stdout')).read_text().splitlines()]==messages
        reported=sum(m['reason']=='build-script-executed'for m in messages);assert reported in [0,1]
        artifacts=[m for m in messages if m['reason']=='compiler-artifact'and m['target']['kind']==['bin']];assert len(artifacts)<=1
        fresh=2 if not artifacts else int(artifacts[0]['fresh'])
        ran=after['runs']-before['runs'];assert ran in [0,1]
        expected='/'.join(str(v)for v in [c['exitCode'],ran,reported,fresh,int(after['scriptValid']),after['basis'],after['generated'],int(after['rustValid']),after['binary'],after['macroValue'],after['runs']])
        projected.append(dict(case=c['case'],input=inp,expected=expected,binaryBytesEqual=c['before']['binary']==c['after']['binary']))
    assert len(projected)==16 and len(runtime)>0
    return dict(cases=projected,bases=[dict(id=basis_ids[k],tracked=v[0],file=v[1],fail=v[2])for k,v in sorted(bases.items())],
        values=[dict(id=value_ids[k],tracked=v[0],hidden=v[1],file=v[2],fail=v[3])for k,v in sorted(values.items())],runtimeIdentities=len(runtime))
