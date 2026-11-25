#!/usr/bin/env python3
"""Read-only observer for two retained VS Code task collections; never launches."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ORIGINAL=ROOT/'applications/evidence/vscode-tasks-20261125T083319891600Z'
CONTINUATION=ROOT/'applications/evidence/vscode-tasks-continuation-20261125T084118001187Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def inspect(original=None,continuation=None,children=None):
    original=read(ORIGINAL/'observed.json') if original is None else original
    continuation=read(CONTINUATION/'observed.json') if continuation is None else continuation
    children=[json.loads(s)for s in(CONTINUATION/'child-events.jsonl').read_text().splitlines()] if children is None else children
    assert original['status']=='failed' and len(original['rows'])==12
    assert original['rows'][-1]['kind']=='fixture-error' and "undefined" in original['error']
    assert continuation['status']=='complete' and len(continuation['rows'])==46
    assert read(CONTINUATION/'meta.json')['continuationOf']==str(ORIGINAL.relative_to(ROOT))
    for run,native in [(ORIGINAL,original),(CONTINUATION,continuation)]:
        meta,exit,disposition=read(run/'meta.json'),read(run/'exit.json'),read(run/'disposition.json')
        assert meta['revision']==exit['revision']=='8a14f0cc1b08d531eb83255ea3764ae22aa932b5'
        assert exit['exitCode']==0 and disposition['ownedGroupAbsent'] and disposition['desktopReleased']
        assert not disposition['privateWorkspaceProcessHits']
        assert sha(run/'observed.json')==exit['observedSha256']
        assert sha(run/'probe.py')==meta['producerSha256']==exit['launchProducerSha256']
        assert sha(run/'extension.cjs')==meta['extensionSha256']
        assert sha(run/'task_worker.py')==meta['workerSha256']
        assert read(run/'package.json')['contributes']['taskDefinitions'][0]['type']=='rules-task-study'
        assert read(run/'tasks.json')['tasks'][0]['isBackground']
        rows=native['rows'];assert [r['sequence']for r in rows]==list(range(len(rows)))
        assert rows[0]['version']=='1.147.0' and rows[0]['uiKind']==1 and rows[0]['remoteName']is None
        identities={}
        for row in rows:
            if 'id'in row:
                prior=identities.setdefault(row['id'],row['name']);assert prior==row['name']
            for v in row['active']:
                prior=identities.setdefault(v['id'],v['name']);assert prior==v['name']
            assert len({v['id']for v in row['active']})==len(row['active'])
            for v in row['active']:assert v['name'].startswith('rules-') and 1<=v['id']<=5
            if row['kind']=='process-start' and row['name']in['rules-custom-seven','rules-provider-hold']:assert row['pid']==-1
    o=original['rows'];c=continuation['rows']
    assert o[1]['names']==[] and o[2]['kind']=='invalid-refused'
    assert o[9]['kind']=='process-end' and o[9]['exitCode']==7
    assert not o[10]['active']
    assert c[1]['kind']=='fetched' and c[1]['names']==[]
    assert c[2]['kind']=='auto-detect-enabled' and c[5]['names']==['rules-provider-hold']
    assert c[13]['kind']=='provider-disposed' and c[14]['names']==[]
    assert c[13]['active']==c[14]['active']==c[15]['active']==[{'id':1,'name':'rules-provider-hold'}]
    assert c[18]['kind']=='task-end' and not c[18]['active'] and c[18]['workerAlive']
    assert c[19]['workerAlive'] and c[20]['kind']=='worker-retired' and not c[20]['workerAlive']
    assert c[24]['kind']=='process-end' and c[24]['exitCode']==7
    assert all(c[i]['kind']=='process-end' and c[i]['exitCode']is None for i in[17,30,43])
    assert c[41]['kind']=='dependency-finished' and c[41]['backgroundStillActive']
    assert c[-1]['kind']=='complete' and not c[-1]['active']
    assert [e['kind']for e in children]==['start','exit','start','signal','exit','start','ready','start','exit','signal','exit']
    for row in children:
        assert row['pid']>0 and row['pgid']==row['pid']
    starts={e['name']:e for e in children if e['kind']=='start'}
    for name in ['process-seven','process-stop']:
        assert starts[name]['argv']==['a b','Ω 日本','$RULES_LITERAL']
    meta=read(CONTINUATION/'meta.json')
    assert all(e['cwd']==meta['project']for e in starts.values())
    for row in c:
        if row['kind']=='process-start' and row['pid']>0:
            assert starts[row['name'].removeprefix('rules-') if row['name'].startswith('rules-process-')else row['name']]['pid']==row['pid']
    assert [e['name']for e in children if e['kind']=='signal']==['process-stop','rules-background']
    assert all(e['signal']==1 for e in children if e['kind']=='signal')
    assert [e['code']for e in children if e['kind']=='exit']==[7,11,0,11]
    assert [e['name']for e in children if e['kind']=='ready']==['rules-background']
    assert c[36]['kind']=='readiness-gate-released' and c[37]['kind']=='task-start' and c[37]['name']=='rules-dependent'
    assert read(CONTINUATION/'disposition.json')['childPidsAbsent']
    sources=read(ROOT/'applications/sources/vscode-task-selections.json')
    for s in sources['sources']:
        assert sha(ROOT/s['cache'])==s['sha256']
    return original,continuation,children

EVENTS={'execute-returned':1,'task-start':2,'process-start':3,'terminate-returned':4,'process-end':5,'task-end':6}
def trace_input(native):return dict(kind='trace',events=[dict(kind=EVENTS.get(r['kind'],0),task=r.get('id',0) if r['kind']in EVENTS else 0)for r in native['rows']])
def trace_observed(native):return ';'.join('['+','.join(str(v['id'])for v in r['active'])+']'for r in native['rows'])
