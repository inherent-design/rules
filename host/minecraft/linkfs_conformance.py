#!/usr/bin/env python3
"""Pure retained linked-filesystem comparisons;no JVM,game,filesystem-provider collection."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CAPTURES=['linkfs-native-1.21.1-20261125T163537038277Z','linkfs-native-1.21.4-20261125T163538338427Z',
          'linkfs-native-1.21.5-20261125T163539600229Z','linkfs-native-1.21.11-20261125T163540951708Z','linkfs-native-26.3-20261125T163340102803Z']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
FIELDS=['sameFilesystem','sameNode','absolute','registered','mapped','backing']


def row(kind,**facts):
    return dict(kind=kind,**dict.fromkeys(FIELDS))|facts


def plan():
    # These premises come from the frozen Java producer's explicit registrations,
    # canonical path pairs and owned A/B/delete/restore schedule,not native results.
    return [
        ('initial-open','virtual',row(0)),('initial-readonly','virtual',row(0)),
        ('same-logical-path','provider',row(1,sameFilesystem=True,sameNode=True)),
        ('different-logical-shared-backing','provider',row(1,sameFilesystem=True,sameNode=False)),
        ('files-api-shared-backing','library',row(1,sameFilesystem=True,sameNode=False)),
        ('different-filesystem-same-label','provider',row(1,sameFilesystem=False)),
        ('same-missing-logical-path','provider',row(1,sameFilesystem=True,sameNode=True)),
        ('mapped-existing','virtual',row(2,absolute=True,registered=True)),
        ('mapped-missing-backing-existing','virtual',row(2,absolute=True,registered=True)),
        ('unmapped-existing','virtual',row(2,absolute=True,registered=False)),
        ('relative-existing','virtual',row(2,absolute=False)),
        ('relative-read','read',row(3,mapped=True,backing=1)),
        ('initial-read','read',row(3,mapped=True,backing=1)),
        ('ghost-read','read',row(3,mapped=True,backing=0)),
        ('metadata-size','attributes',row(4,registered=True)),
        ('read-after-backing-write','read',row(3,mapped=True,backing=2)),
        ('mapped-existing-after-delete','virtual',row(2,absolute=True,registered=True)),
        ('read-after-backing-delete','read',row(3,mapped=True,backing=0)),
        ('write-open','provider',row(5)),('open-after-close','virtual',row(0)),
        ('read-after-close-and-restore','read',row(3,mapped=True,backing=1)),
    ]


def observe(raw):
    assert raw['schema']==1 and raw['observerErrors']==0 and raw['ownedOriginalBytesRestored']is True
    selected=plan();ids=[p[0]for p in selected];ids.insert(15,'root-list');ids.insert(16,'backing-write-key-stability')
    assert [r['id']for r in raw['rows']]==ids
    indexed={r['id']:r for r in raw['rows']};result=[]
    for identity,domain,request in selected:
        r=indexed[identity];assert r['domain']==domain and ('value'in r)!=('error'in r)
        if'error'in r:
            assert r['error']in ['NoSuchFileException','UnsupportedOperationException']
            value=0 if r['error']=='NoSuchFileException'else 6
        elif request['kind']in [0,1,2,5]:
            assert type(r['value'])is bool;value=2 if r['value']else 1
        elif request['kind']==3:
            assert r['value']in ['A','B'];value=3 if r['value']=='A'else 4
        else:
            assert type(r['value'])is int and r['value']>=0;value=5 if r['value']==0 else 7
        result.append(value)
    roots=indexed['root-list'];assert roots['domain']=='virtual'and roots['value']==sorted({p[0]for p in [('assets','a'),('alias',),('ghost',)]})
    stability=indexed['backing-write-key-stability'];assert stability['domain']=='owned-control'and(stability['value']is None or type(stability['value'])is bool)
    return result,stability['value']


def main():
    work=ROOT/'.build/minecraft/linkfs-replay';work.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=os.environ.get('LEAN_PATH',str(ROOT/'.build/formal')),BEND_NO_TELEMETRY='1')
    def lean(data,label):
        p=work/(label+'.json');p.write_text(json.dumps(data)+'\n')
        return subprocess.run([os.environ.get('LEAN','lean'),'--run',str(HERE/'LinkedFilesystemCase.lean'),str(p)],env=env,cwd=ROOT,text=True,capture_output=True,timeout=30)
    def bend(rows,label):
        calls=[]
        for r in rows:
            args=[str(r['kind'])+'n']+['True{}'if r[k]else'False{}'for k in FIELDS[:-1]]+[str(r['backing']or 0)+'n']
            calls.append('Nat.show(M.linkfs_evaluate('+','.join(args)+')) ++ "\\n"')
        p=work/(label+'.bend');p.write_text('import Base\nimport ../../../host/minecraft/LinkedFilesystem.bend as M\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
        r=subprocess.run([os.environ.get('BEND','bend'),str(p)],env=env,cwd=ROOT,text=True,capture_output=True,timeout=30);assert r.returncode==0,r.stdout+r.stderr
        return [int(x)for x in r.stdout.splitlines()]
    request=dict(schema=1,contract='canonical-linkfs-owned-bytes-v1',rows=[r for _,_,r in plan()])
    r=lean(request,'plan');assert r.returncode==0,r.stdout+r.stderr;predicted=json.loads(r.stdout);assert predicted==bend(request['rows'],'plan')
    profiles=[];native=[];basis=[HERE/n for n in ['LinkedFilesystem.lean','LinkedFilesystem.bend','LinkedFilesystemCase.lean','linkfs_conformance.py','LinkFSProbe.java','targets.json','linkfs-sources.json']]+[ROOT/'common/FilesystemGuard.lean']
    targets=json.loads((HERE/'targets.json').read_text())['javaReferences']
    for name,version in zip(CAPTURES,['1.21.1','1.21.4','1.21.5','1.21.11','26.3']):
        cap=HERE/'evidence'/name;r=json.loads((cap/'receipt.json').read_text());raw=json.loads((cap/'observed.json').read_text());target=next(t for t in targets if t['release']==version)
        assert r['target']==target['id']and r['clientSha256']==target['source']['clientSha256']and r['metadataSha256']==target['source']['metadataSha256']
        assert r['rows']==23 and r['observerErrors']==0 and r['ownedOriginalBytesRestored']is True
        assert sha(cap/'bindings.json')==r['bindingsSha256']and sha(cap/'observed.json')==r['observed.jsonSha256']
        for n,h in r['sourcesSha256'].items():assert sha(cap/n)==h
        assert sha(cap/'LinkFSProbe.java')==sha(HERE/'LinkFSProbe.java')
        for stem,c in zip(['compile','execute'],r['commands']):
            assert c['exitCode']==0 and c['ownedGroupAbsent']and not c['timedOut']
            for channel in ['stdout','stderr']:assert sha(cap/(stem+'.'+channel))==c[channel+'Sha256']
        actual,stable=observe(raw);assert actual==predicted
        profiles.append(dict(target=r['target'],snapshots=23,modelComparisons=21,rootListingChecked=True,backingFileKeyAfterWrite=stable));native.append(raw);basis.extend(p for p in cap.iterdir()if p.is_file())
    negatives=[dict(request,schema=2),dict(request,contract='physical-file-identity'),dict(request,rows=request['rows']*7)]
    for bad in [row(6),row(1,sameFilesystem=True),row(1),row(2,absolute=True),row(2),row(3,mapped=True),row(3),row(3,mapped=True,backing=3),row(4),row(1,sameFilesystem=1,sameNode=True)]:negatives.append(dict(request,rows=[bad]))
    for i,bad in enumerate(negatives):assert lean(bad,'negative-'+str(i)).returncode==2
    positive=[row(0),row(1,sameFilesystem=False),row(2,absolute=False),row(3,mapped=False)]
    p=lean(dict(request,rows=positive),'unneeded-unknown');assert p.returncode==0 and json.loads(p.stdout)==[2,1,1,0]
    changed=[]
    for identity,field,value in [('different-logical-shared-backing','value',True),('mapped-missing-backing-existing','value',False),
                                  ('relative-existing','value',True),('read-after-backing-write','value','A'),('open-after-close','value',False),
                                  ('metadata-size','value',1),('ghost-read','error','AccessDeniedException'),('root-list','value',['alias','assets'])]:
        raw=copy.deepcopy(native[0]);next(r for r in raw['rows']if r['id']==identity)[field]=value
        try:assert observe(raw)[0]==predicted
        except AssertionError:changed.append(identity)
        else:raise AssertionError('Changed linked-filesystem observation admitted.')
    report=dict(schema=1,status='passed-original-linkfs-owned-bytes',profiles=profiles,nativeSnapshots=115,modelComparisons=105,supplementalListings=5,
        supplementalFileKeyObservations=5,leanLaws=17,bendLaws=9,decoderRefusals=len(negatives),unneededUnknownExamples=4,changedObservationControls=changed,
        basisSha256={str(p.relative_to(ROOT)):sha(p)for p in sorted(basis)},
        limits=['Fixed canonical file-node layout and owned A/B/absent backing schedule;not complete path grammar,arbitrary trees,permissions,concurrency or provider equivalence.',
                'Both models receive the same manually inspected Python projection of the frozen Java producer plan;adapter fidelity is not formally proven.',
                'Listing and optional file-key facts are independently checked/retained,not general Lean/Bend proofs of directory iteration or inode lifetime.',
                'Original class/link/library identities are attributable;not a full JVM/Minecraft translation or implementation proof.',
                'Native Darwin/JDK21/25 only;no game,index parser,real assets,provider coexistence,reload,renderer or other-host execution.'])
    (HERE/'evidence/linkfs-conformance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','nativeSnapshots','modelComparisons','decoderRefusals','unneededUnknownExamples','changedObservationControls']}))


if __name__=='__main__':main()
