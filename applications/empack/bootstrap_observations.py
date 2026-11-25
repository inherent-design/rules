#!/usr/bin/env python3
"""Project frozen invocation bytes, authored cache state, child events and scopes."""
import hashlib
import json
from pathlib import Path
import re

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def unique_object(pairs):
    result={}
    for k,v in pairs:
        if k in result:raise ValueError('duplicate')
        result[k]=v
    return result

def project(run,overrides=None):
    overrides=overrides or {}
    rows=overrides.get('commands.json',json.loads((run/'commands.json').read_text()))
    actual_version=(run/'native-identity-version.stdout').read_text().strip().removeprefix('empack ')
    actual_protocol=(run/'native-identity-protocol.stdout').read_text().strip()
    result=[]
    for r in rows:
        name=r['case'];argv=r['argv'];before=r['before'];after=r['after'];req=r['request'];events=r['events']
        assert not r['timedOut']and r['ownedGroupAbsent']
        for stream in ['stdout','stderr']:assert sha(run/(name+'.'+stream))==r['streams'][stream]
        base=run/'work/cases'/name/'Pack Ω 日本'
        record_ok=True;record=None;append_ok=True
        if '--invocation-file'in argv:
            relative=argv[argv.index('--invocation-file')+1]
            entry=before['Pack Ω 日本'][relative]
            record_ok=entry['kind']=='file'and bool(re.fullmatch(r'\.empack-tools/[A-Za-z0-9_-]+\.json',relative))
            if record_ok:
                p=base/relative;assert sha(p)==entry['sha256']
                try:
                    record=json.loads(p.read_bytes().decode('utf-8'),object_pairs_hook=unique_object)
                    record_ok=(set(record)=={'schema','engine_version','arguments','append_arguments'}and
                        record['schema']=='empack-bootstrap-invocation/1'and isinstance(record['engine_version'],str)and
                        isinstance(record['arguments'],list)and len(record['arguments'])>0 and
                        all(isinstance(a,str)for a in record['arguments'])and type(record['append_arguments'])is bool)
                except (ValueError,UnicodeError,TypeError):record_ok=False
            if record_ok:
                append_ok=record['append_arguments']or '--'not in argv
        version=record['engine_version']if record_ok and record is not None else req['version']
        # Closed exact-version fixtures,not another general SemVer parser.
        assert version in {'0.8.8-beta','v0.8.8-beta','^0.8.8','0.8.8+one','0.8.8-01'}
        explicit='--engine'in argv
        development='--development-engine'in argv
        options_ok=append_ok and version=='0.8.8-beta'and(not development or explicit)
        local_state=0 if req['local']is None else 2 if req['local']=='wrong-version'else 1
        cache_state=0
        cached_records=[(k,v)for k,v in (before['cache']or{}).items()if k.endswith('/ready.properties')]
        assert len(cached_records)<=1
        if cached_records:
            k,image=cached_records[0];p=run/'work/cases'/name/'cache'/k;assert sha(p)==image['sha256']
            props=dict(line.split('=',1)for line in p.read_text().splitlines())
            executable=p.parent/'objects'/props['archive']/'empack'
            assert executable.is_file()
            good=(props['kind']=='empack-engine/1'and props['version']==version and props['target']=='aarch64-apple-darwin'and
                  props['executable']==sha(executable)and props['bytes']==str(executable.stat().st_size))
            cache_state=1 if good else 2
        effective_version=actual_version if req['nativeEngine']else req['engineVersion']
        version_ok=effective_version==version or(development and effective_version=='0.0.0-dev')
        protocol_ok=(actual_protocol if req['nativeEngine']else req['protocol'])=='empack-bootstrap/1'
        term=0 if r['signalSent']is None else 1 if r['signalSent']==15 else 2
        inp=dict(recordOk=record_ok,optionsOk=options_ok,explicit=explicit,localState=local_state,cache=cache_state,
                 versionOk=version_ok,protocolOk=protocol_ok,termination=term,childResult=7 if term==1 else 0)
        started=[e for e in events if e['kind']=='started'];completed=[e for e in events if e['kind']=='completed']
        assert len(started)<=1 and len(completed)<=1
        if req['nativeEngine']:
            output=json.loads((run/(name+'.stdout')).read_text())
            assert output['complete']is True and output['pack']=='Rules pending fixture'
            delegated=True;selected=1;child=0;cancel=0
        else:
            delegated=bool(started);child=completed[0]['result']if completed else None
            candidates=[e for e in events if e['kind']in ['version','protocol','started']]
            selected={'explicit':1,'distribution':2,'cached':3}[candidates[-1]['engine']]if candidates else 0
            cancellation=[e for e in events if e['kind']=='cancellation']
            cancel=1 if cancellation and cancellation[0]['explicit']else 2 if cancellation and cancellation[0]['parentLoss']else 0
            assert all(not e['controlPresent']for e in events if e['kind']in ['version','protocol'])
            if delegated:
                assert started[0]['authenticated']and completed
                output=json.loads((run/(name+'.stdout')).read_text())
                assert output['argv']==started[0]['argv']and output['cwd']==started[0]['cwd']==str(base)
                assert output['result']==child
                expected_args=record['arguments']if record is not None else ['--fixture-echo','Ω 日本','value with spaces']
                assert output['argv']==expected_args+(req['dynamic']or[])
        cache_open=any(k.endswith('/writer.lock')for k in (after['cache']or{}))
        expected='/'.join([str(r['exitCode']),str(selected),str(int(cache_open)),str(int(delegated)),'-'if child is None else str(child),str(cancel)])
        result.append(dict(case=name,input=inp,expected=expected,changedScopes=[k for k in before if before[k]!=after[k]]))
    assert len(result)==29
    return result
