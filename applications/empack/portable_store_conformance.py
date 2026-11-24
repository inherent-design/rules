#!/usr/bin/env python3
"""Pure model replay of the executed research adapter;not production empack."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

import portable_study_observations as observations
from portable_study_native import decode

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
RUN=observations.RUN
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def semantic(draft):
    raw=draft['rawAuthor'].encode();content=lambda r:{k:r[k]for k in ['sha256','bytes']}
    value=dict(label=draft['label'],author=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)),
        entries=[{**e,'asset':content(e['asset'])}for e in draft['entries']],missing=draft['missing'])
    return hashlib.sha256(canonical(value)).hexdigest()

def record_image(record):
    content=lambda r:{k:r[k]for k in ['sha256','bytes']};d=record['draft']
    value={**d,'author':content(d['author']),'entries':[{**e,'asset':content(e['asset'])}for e in d['entries']]}
    actual=hashlib.sha256(canonical(value)).hexdigest();assert actual==record['image'];return actual


class Labels:
    def __init__(self):self.values={}
    def label(self,key):
        if key is None:return None
        if key not in self.values:self.values[key]=len(self.values)+1
        return self.values[key]


def build():
    browser=json.loads((RUN/'receipt.json').read_text());backend=json.loads((RUN/'backend-inspection.json').read_text());by_engine={r['engine']:r for r in backend['rows']}
    images,roles=Labels(),Labels();rows=[]
    def root(record):return dict(revision=0 if record is None else int(record['revision']),image=None if record is None else images.label(record_image(record)))
    def current_editor(state,saved=None):
        actual=dict(epoch=state['epoch'],current=images.label(semantic(state['draft'])),saved=images.label(state['savedImage']),savedRevision=int(state['savedRevision']))
        if saved is not None:actual.update(saved=saved['saved'],savedRevision=saved['savedRevision'])
        return actual
    def role_sets(draft,corrupt=None):
        author='author:'+hashlib.sha256(draft['rawAuthor'].encode()).hexdigest();available=[roles.label(author)]
        for e in draft['entries']:available.append(roles.label('available:'+e['asset']['id']))
        held=[n for n in available if corrupt is None or n!=roles.label('available:'+corrupt)]
        return sorted(available),sorted(roles.label('missing:'+p)for p in draft['missing']),sorted(held)
    def emit(profile,event,data,expected,metadata):rows.append(dict(id=profile+'/'+event,input=data,expected=expected,source=metadata))
    def text(s,e,status):return '/'.join(str(v)if v is not None else '-'for v in [s['revision'],s['image'],e['epoch'],e['current'],e['saved'],e['savedRevision'],status])
    for p in browser['profiles']:
        name=p['engine'];events=p['events'];store=None;main=None;main_draft=None
        complete_bundle,complete_files=decode((RUN/next(d['file']for d in p['downloads']if d['label']=='complete-backup')).read_bytes())
        native_author=complete_files['empack.yml'].decode()
        for index,event in enumerate(events):
            kind=event['kind'];state=event.get('state');data=None;measured=list(range(7))
            if kind=='import-edit':
                main=current_editor(state);main_draft=copy.deepcopy(state['draft'])
                assert main['saved']is None and main['savedRevision']==0
                assert main_draft['label']=='<img src=x onerror="window.injected=true"> Ω 日本'
                assert main_draft['rawAuthor']=='schema: [\n' and main_draft['missing']==['pack/config/not-supplied.cfg']
                out_store=root(None);expected_editor=current_editor(state);op=0;status=0;draft=main_draft
            elif kind in ['save-invalid-missing','same-image-new-backing','retry-after-unpublished-file','save-complete']:
                previous=root(store);draft=copy.deepcopy(main_draft);before=copy.deepcopy(main)
                if kind=='save-complete':
                    # These edits are selected by the frozen producer. The new
                    # file's handle is observed,while its byte identity,path and
                    # original filename are independently checked inputs.
                    third=copy.deepcopy(next(e for e in state['draft']['entries']if e['path']=='pack/config/not-supplied.cfg'))
                    assert third['originalName']=='arbitrary-name.cfg' and third['asset']['sha256']==browser['inputSha256']['supplied']
                    draft.update(label='Complete study Ω 日本',rawAuthor=native_author,missing=[],entries=sorted([*draft['entries'],third],key=lambda e:e['path']))
                    before.update(epoch=main['epoch']+3,current=images.label(semantic(draft)))
                    # The producer issued three edits,but fill() generated more
                    # DOM input events. No pre-save snapshot counts those
                    # events. Compare the image/basis/result,not that epoch.
                    measured.remove(2)
                op=1;status=1;out_store=root(event['record']);expected_editor=current_editor(state)
                data=dict(stored=previous,editor=before,expected=before['savedRevision'],image=before['current'],boundary=3)
                store=event['record'];main=expected_editor;main_draft=draft
            elif kind=='stale-tab':
                draft=copy.deepcopy(events[1]['state']['draft']);draft['label']='Stale tab'
                other=dict(epoch=2,current=images.label(semantic(draft)),saved=images.label(events[1]['record']['image']),savedRevision=1)
                op=1;status=3;out_store=root(event['current']);expected_editor=current_editor(state)
                data=dict(stored=root(store),editor=other,expected=1,image=other['current'],boundary=3)
                assert event['code']=='STALE_REVISION'
            elif kind=='invalid-backup':
                op=3;status=6;out_store=root(store);expected_editor=main;draft=main_draft;measured=[0,1,6]
                downloaded=next(d for d in p['downloads']if d['label']=='invalid-backup');bundle,_=decode((RUN/downloaded['file']).read_bytes())
                assert root(bundle['record'])==out_store and downloaded['completed']
            elif kind=='worker-loss':
                draft=copy.deepcopy(main_draft);draft['label']='Loss boundary '+event['hold']
                before={**main,'epoch':main['epoch']+1,'current':images.label(semantic(draft))}
                assert before==current_editor(event['before'])
                op=1;status=2;data=dict(stored=root(store),editor=before,expected=before['savedRevision'],image=before['current'],
                    boundary={'asset-created':0,'assets-retained':1,'metadata-committed':2}[event['hold']])
                assert event['completion']['code']=='OUTCOME_UNKNOWN';out_store=root(event['current']);expected_editor=current_editor(event['state'])
                store=event['current'];main=expected_editor;main_draft=draft
            elif kind=='reconcile-after-loss':
                op=2;status=5;out_store=root(event['record']);expected_editor=current_editor(state);draft=state['draft']
                data=dict(stored=root(store),editor=main,expected=main['savedRevision'],image=images.label(record_image(event['record'])),boundary=3)
                store=event['record'];main=expected_editor;main_draft=copy.deepcopy(draft)
            elif kind=='browser-relaunch-reopen':
                op=2;status=5;out_store=root(event['record']);expected_editor=current_editor(state);draft=state['draft']
                data=dict(stored=root(store),editor=dict(epoch=0,current=0,saved=None,savedRevision=0),expected=0,image=images.label(record_image(event['record'])),boundary=3)
                main=expected_editor;main_draft=copy.deepcopy(draft)
            else:
                assert kind=='retained-corruption';op=4;status=4;out_store=root(event['current']);expected_editor=current_editor(state);draft=main_draft
                assert event['openError']==event['saveError']=='Retained digest mismatch' and by_engine[name]['record']==event['current']
            available,missing,held=role_sets(draft,event['entry']['asset']['id']if kind=='retained-corruption'else None)
            if data is None:data=dict(stored=out_store,editor=main,expected=main['savedRevision'],image=images.label(semantic(draft)),boundary=3)
            raw_hash=hashlib.sha256(draft['rawAuthor'].encode()).hexdigest();valid=raw_hash==browser['inputSha256']['nativeAuthor']
            if not valid:assert draft['rawAuthor']=='schema: [\n'
            data.update(kind=op,validAuthoring=valid,available=available,missing=missing,verified=held,backing=kind!='retained-corruption',finalized=True)
            emit(name,str(index)+'-'+kind,data,text(out_store,expected_editor,status),dict(profile=name,eventIndex=index,kind=kind,measuredFields=measured))
            if kind=='browser-relaunch-reopen':
                # The completed download after this event has its own receipt;
                # no after-download editor snapshot was recorded.
                download=next(d for d in p['downloads']if d['label']=='complete-backup');assert download['completed']
                backup_data={**data,'kind':3};emit(name,'complete-download',backup_data,text(root(complete_bundle['record']),main,6),dict(profile=name,eventIndex=index,kind='complete-download',measuredFields=[0,1,6]))
    assert len(rows)==30
    return rows,images,roles


def bend_option(n):return 'None{}'if n is None else 'Some{'+str(n)+'n}'
def bend_list(xs):return '['+','.join(str(n)+'n'for n in xs)+']'
def bend_result(r):
    s=r['stored'];e=r['editor'];state='S.PStored{'+str(s['revision'])+'n,'+bend_option(s['image'])+'}'
    editor='A.Editor{'+','.join([str(e['epoch'])+'n',str(e['current'])+'n',bend_option(e['saved']),str(e['savedRevision'])+'n'])+'}'
    b=lambda v:'True{}'if v else 'False{}'
    if r['kind']==0:return 'S.observe('+state+','+editor+')'
    if r['kind']==1:return 'S.save('+','.join([state,editor,str(r['expected'])+'n',str(r['image'])+'n',bend_list(r['available']),bend_list(r['verified']),str(r['boundary'])+'n'])+')'
    if r['kind']==2:return 'S.reopen('+','.join([state,editor,b(r['backing'])])+')'
    if r['kind']==3:return 'S.backup('+','.join([state,editor,b(r['backing']),b(r['finalized'])])+')'
    return 'S.reopen_then_save('+','.join([state,editor,b(r['backing']),bend_list(r['available']),bend_list(r['verified']),str(r['boundary'])+'n'])+')'


def compare(row,actual):
    a,e=actual.split('/'),row['expected'].split('/');assert len(a)==len(e)==7
    for i in row['source']['measuredFields']:assert a[i]==e[i],(row['id'],i,actual,row['expected'])
def main():
    p=subprocess.run(['python3',str(HERE/'portable_study_observations.py')],cwd=ROOT,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    rows,images,roles=build();generated=HERE/'generated';generated.mkdir(exist_ok=True)
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend');env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1')
    # Dependencies are the source-bound artifacts from the normal formal check.
    artifact=ROOT/'.build/formal/applications/empack/PortableStore.olean';artifact.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.run([lean,'-DwarningAsError=true','-o',str(artifact),'applications/empack/PortableStore.lean'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    path=generated/'portable-store.json'
    def replay(data):
        path.write_text(json.dumps(data)+'\n')
        return subprocess.run([lean,'--run','applications/empack/PortableStoreCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    data=dict(schema=1,profile='captured-browser-study-save',rows=[r['input']for r in rows]);p=replay(data);assert p.returncode==0,p.stdout+p.stderr
    actual=json.loads(p.stdout);assert len(actual)==len(rows)
    for row,result in zip(rows,actual):compare(row,result)
    calls=['S.render('+bend_result(r['input'])+') ++ "\\n"'for r in rows]
    driver=generated/'PortableStoreCase.bend';driver.write_text('import Base\nimport ../PortableStore.bend as S\nimport ../Authoring.bend as A\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
    p=subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    assert p.stdout.splitlines()==actual
    refusals=[]
    for name,edit in [('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='empack-production')),('count',lambda d:d.update(rows=d['rows']*10)),
        ('operation',lambda d:d['rows'][0].update(kind=5)),('boundary',lambda d:d['rows'][0].update(boundary=4)),('revision',lambda d:d['rows'][0]['stored'].update(revision=4097)),
        ('missing-saved-basis',lambda d:d['rows'][0]['stored'].update(revision=1)),('role-label',lambda d:d['rows'][0].update(available=[0])),
        ('duplicate-role',lambda d:d['rows'][0].update(available=[1,1])),('unsorted-role',lambda d:d['rows'][0].update(available=[2,1])),
        ('wrong-bool',lambda d:d['rows'][0].update(backing='true'))]:
        bad=copy.deepcopy(data);edit(bad);p=replay(bad);assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);refusals.append(name)
    mutations=[]
    for n in range(7):
        row=copy.deepcopy(rows[0]);parts=row['expected'].split('/');parts[n]='999';row['expected']='/'.join(parts)
        try:compare(row,actual[0])
        except AssertionError:mutations.append('field-'+str(n))
        else:raise AssertionError('Measured-field mutation escaped')
    files=[HERE/n for n in ['PortableStore.lean','PortableStore.bend','PortableStoreCase.lean','Authoring.lean','Authoring.bend','portable_store_conformance.py','portable_study_observations.py','portable_study_native.py']]
    files +=[ROOT/'common/Lifecycle.lean',ROOT/'applications/sources/empack-portable-storage-selections.json']
    files +=[p for p in RUN.rglob('*')if p.is_file()and 'work'not in p.relative_to(RUN).parts and p.name!='conformance.json']
    receipt=dict(schema=1,scope='Executed proposed storage adapter versus conditional models,not production empack',browserObservationComparisons=30,browserSourceEvents=28,
        researchRefusals=refusals,measuredMutations=mutations,imageLabels=images.values,roleLabels=roles.values,
        comparisons=[{**row,'modelResult':result}for row,result in zip(rows,actual)],
        basisSha256={str(p.relative_to(ROOT)):sha(p)for p in sorted(set(files))},generatedDriverSha256=sha(driver),
        tools={n:dict(path=str(Path(p).resolve()),sha256=sha(Path(p)))for n,p in [('lean',lean),('bend',bend)]},
        limits=['No new browser/native execution. Do not promote the complete portable-authoring scenario.',
            'Hashing/JSON,verified byte roles and semantic image labels are external decoded witnesses. This model neither mints capability nor supplies source authentication.',
            'Edits follow the frozen producer and known prior saved basis. Final fill() DOM event count was not captured before save,so that row excludes editor epoch. Backup rows compare only measured storage/delivery fields.',
            'Backing validity follows the closed fixture:verified downloads/raw inspection and source-controlled mutation timing. No hidden/noncooperating writes assumed.',
            'Corruption is one composed reopen-then-save observation,not fabricated intermediate snapshots. Logical revision arithmetic is unbounded here. Prototype UInt64 guard,arbitrary contention/history/GC/streaming/permissions and native consumer engine parity remain separate obligations.'])
    (RUN/'conformance.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items()if k not in ['basisSha256','imageLabels','roleLabels','comparisons']},indent=2))


if __name__=='__main__':main()
