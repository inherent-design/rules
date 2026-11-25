#!/usr/bin/env python3
"""Pure selected library-rule comparisons; no Qt/compiler/launcher execution."""
import copy,json,os,subprocess
from pathlib import Path
import library_observations as obs
ROOT=obs.ROOT;HERE=Path(__file__).resolve().parent
B=lambda v:'True{}'if v else'False{}'
N=lambda v:str(v)+'n'
def bend(r):
    k=r['kind']
    if k=='rename':return 'L.rename_text('+','.join([json.dumps(r['current']),json.dumps(r['requested']),B(r['role'])])+')'
    if k=='group':return 'L.group_text('+','.join(B(r[v])for v in['present','alias','candidate'])+')'
    if k=='lookup':return 'Nat.show(L.first([L.I{1n,0n,2n},L.I{2n,2n,3n}],'+N(r['mode'])+',2n))'
    if k=='unique':return 'Nat.show(L.unique_acc([L.I{1n,0n,2n},L.I{2n,2n,3n}],'+N(r['mode'])+',2n,0n))'
    if k=='remove':return 'L.remove_text('+B(r['trashMode'])+','+B(r['writeSucceeded'])+')'
    if k=='undo':return 'L.undo_text('+','.join(B(r[v])for v in['hasHistory','mainMoved','shortcutsMoved'])+')'
    if k=='retry':return 'L.retry_text(L.advance(L.R{'+B(r['mainPending'])+','+N(r['shortcutsPending'])+'},'+B(r['mainMoved'])+','+B(r['shortcutsMoved'])+'))'
    if k=='save':return 'L.save_text('+B(r['probed'])+','+B(r['writeSucceeded'])+')'
    if k=='counts':return 'L.counts_text(['+','.join(N(n)for n in r['members'])+'],[1n,2n])'
    if k=='collapse':return 'Bool.pick(String,Bool.or('+B(r['prior'])+','+B(r['incoming'])+'),"1","0")'
    return ' ++ "," ++ '.join('Bool.pick(String,L.discovered('+B(c)+','+B(a)+'),"1","0")'for c,a in zip(r['configs'],r['aliases']))
def main():
    d=obs.inspect();rows=[];expected=[];bit=lambda b:str(int(b))
    def add(r,result):rows.append(r);expected.append(result)
    for id in['rename-label','rename-wrong-role','duplicate-label']:
        r=d[id];add(dict(kind='rename',current='a',requested='b'if id=='duplicate-label'else'Renamed',role=id!='rename-wrong-role'),bit(r['ok'])+'|'+r['after']['names']['a'])
    for id in['group-directory','group-uuid-first','group-uuid-existing','group-uuid-candidate']:
        r=d[id];after=r['after'];saved=after['saved']['groups'];savedA='a'in saved.get('New',{}).get('instances',[])
        add(dict(kind='group',present='a'in r['before']['index'],alias=id!='group-directory',candidate=id=='group-uuid-candidate'),bit('1'*32 in after['index'])+'|'+bit(after['live']['a']=='New')+'|'+bit(savedA))
    add(dict(kind='lookup',mode=0),'1'if d['lookup-collision']['resolvedId']=='a'else'2')
    for id,trash,success,stage in[('trash-failure',True,False,'after'),('delete-failure',False,False,'after'),('undo-success',True,True,'trashed')]:
        r=d[id][stage];add(dict(kind='remove',trashMode=trash,writeSucceeded=success),bit('a'in r['index'])+'|'+str(r['history']))
    review=obs.read(obs.RUN/'postimage-review.json')
    for id in['undo-success','undo-directory-collision','undo-file-collision','undo-shortcut-collision']:
        row=d[id];images=review['postimages'][id];moved=any(x['payload']=='a'for x in images.values())
        add(dict(kind='undo',hasHistory=True,mainMoved=moved,shortcutsMoved=id!='undo-shortcut-collision'),bit(row['ok'])+'|'+bit(moved)+'|'+str(row['after']['history']))
    r=d['undo-file-collision'];add(dict(kind='undo',hasHistory=False,mainMoved=False,shortcutsMoved=False),bit(r['secondOk'])+'|0|'+str(r['second']['history']))
    # Cause labels are fixture/source classifications; Prism's methods return
    # void here. The disk/live disagreement is independently captured.
    for id,probed,good,label in[('save-refused',True,False,'failed'),('save-unprobed',False,True,'skipped')]:
        saved=d[id]['after']['saved']['groups'];add(dict(kind='save',probed=probed,writeSucceeded=good),label+'|'+bit('a'in saved.get('New',{}).get('instances',[])))
    for id in['reload-collapse','load-duplicate','load-missing']:
        r=d[id];members=[{'a':1,'b':2,'ghost':3}[x]for x in r['input']['groups']['New']['instances']]
        rawCount=sum(r['after']['counts'].values());savedCount=sum(len(g['instances'])for g in r['resaved']['saved']['groups'].values())
        add(dict(kind='counts',members=members),str(rawCount)+'|'+str(len(r['after']['index']))+'|'+str(savedCount))
    add(dict(kind='collapse',prior=True,incoming=False),bit('New'in d['reload-collapse']['after']['collapsed']))
    nodes=['.hidden','a','b','internal','external','no-config'];add(dict(kind='discover',configs=[True]*5+[False],aliases=[False,False,False,True,False,False]),','.join(bit(x in d['discover']['found'])for x in nodes))
    assert len(rows)==23
    for mode,value in[(0,'3'),(1,'2'),(2,'1')]:add(dict(kind='unique',mode=mode),value)
    for mainPending,mainMoved,shortMoved,text in[(True,False,True,'1|1|0'),(True,True,False,'0|1|0'),(False,False,True,'0|0|1'),(True,True,True,'0|0|1')]:add(dict(kind='retry',mainPending=mainPending,mainMoved=mainMoved,shortcutsMoved=shortMoved,shortcutsPending=1),text)
    defaults=dict(current='a',requested='a',role=True,present=False,alias=False,candidate=False,trashMode=False,mode=0,hasHistory=False,mainPending=False,mainMoved=False,shortcutsMoved=False,shortcutsPending=0,probed=True,writeSucceeded=False,members=[],prior=False,incoming=False,configs=[],aliases=[])
    for row in rows:
        for k,v in defaults.items():row.setdefault(k,copy.deepcopy(v))
    lean,bendTool=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend');env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1');gen=HERE/'generated';gen.mkdir(exist_ok=True)
    target=ROOT/'.build/formal/applications/prism/Library.olean';target.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.run([lean,'-DwarningAsError=true','-o',str(target),'applications/prism/Library.lean'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    value=dict(schema=1,profile='prism-library-methods',rows=rows);path=gen/'library.json'
    def replay(v):
        path.write_text(json.dumps(v)+'\n');return subprocess.run([lean,'--run','applications/prism/LibraryCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    p=replay(value);assert p.returncode==0,p.stdout+p.stderr;assert json.loads(p.stdout)==expected,(p.stdout,expected)
    driver=gen/'LibraryCase.bend';driver.write_text('import Base\nimport ../Library.bend as L\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join('('+bend(r)+' ++ "\\n")'for r in rows)+')\n')
    p=subprocess.run([bendTool,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr;assert p.stdout.splitlines()==expected,(p.stdout,expected)
    refused=[]
    for name,edit in[('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='full-prism')),('empty',lambda d:d.update(rows=[])),('selector',lambda d:d['rows'][0].update(mode=3)),('shortcut-bound',lambda d:d['rows'][0].update(shortcutsPending=2)),('member',lambda d:d['rows'][0].update(members=[4])),('alias-shape',lambda d:d['rows'][0].update(configs=[True],aliases=[])),('name',lambda d:d['rows'][0].update(current='private-user'))]:
        bad=copy.deepcopy(value);edit(bad);p=replay(bad);assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);refused.append(name)
    changed=[]
    for name,i,edit in[('rename-role',0,lambda r:r.update(role=False)),('canonical-insertion',4,lambda r:r.update(candidate=True)),('raw-lookup-mode',7,lambda r:r.update(mode=1)),('remaining-history',15,lambda r:r.update(hasHistory=True)),('save-gate',17,lambda r:r.update(probed=True)),('duplicate-members',19,lambda r:r.update(members=[1])),('internal-alias',22,lambda r:r['aliases'].__setitem__(3,False))]:
        bad=copy.deepcopy(value);edit(bad['rows'][i]);p=replay(bad);assert p.returncode==0,p.stderr;assert json.loads(p.stdout)!=expected,name;changed.append(name)
    native=obs.read(obs.RUN/'observed.json')['rows'];changedNative=[]
    for name,edit in[('uuid-binding',lambda d:d[4]['after']['index'].clear()),('lost-payload',lambda d:d[10].update(bytes='')),('undo-retry',lambda d:d[14]['after'].update(history=1)),('shortcut-effect',lambda d:d[15].update(shortcutBytes='shortcut')),('collapsed-view',lambda d:d[16]['after'].update(collapsed=[])),('duplicate-count',lambda d:d[17]['after'].update(counts={'New':1})),('unknown-discovery',lambda d:d[22]['found'].append('internal'))]:
        bad=copy.deepcopy(native);edit(bad)
        try:obs.inspect(bad)
        except AssertionError:changedNative.append(name)
        else:raise AssertionError('Changed observation accepted '+name)
    bad=copy.deepcopy(native);bad[13]['restoredPath']='not-authoritative';obs.inspect(bad)
    replay(value)
    report=dict(schema=1,nativeScenarios=24,currentSourceScenarios=23,nativePrivateCandidateScenarios=1,comparedCurrentProjections=22,comparedNativeCandidateProjections=1,proposedModelOnlyCases=7,totalComparisons=30,leanLaws=21,bendLaws=12,decoderRefusals=refused,changedPremises=changed,changedObservations=changedNative,excludedProjectionControl='restoredPath changes do not override independently inspected payload bytes;original collector error retained',limits=['Selected original bodies plus declared fixture adapters;not full launcher/GUI/backend.','Directory restoration/collision host facts are admitted observations,not a formal QFile/filesystem model.','Proposed retry-reference state is not exclusive OS trash retention or write authority.'])
    (HERE/'library-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
