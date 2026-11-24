#!/usr/bin/env python3
"""Compare the retained 45 CLI commands with two scoped recovery models."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import recovery_observations as observations

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
RUN=observations.RUN
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ansi=re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')


def load(ref):
    p=RUN/ref['image'];assert sha(p)==ref['sha256'];return{bytes.fromhex(k):v for k,v in json.loads(p.read_text()).items()}
def content(v):return bytes.fromhex(v['contentHex'])
def fingerprint(v):
    if v is None:return None
    assert v['kind']=='file';mode=v['mode']
    return dict(sha256=list(hashlib.sha256(content(v)).digest()),bytes=v['bytes'],readonly=not bool(mode&0o222),executable=bool(mode&0o111))
def journal(case,v):return json.loads(content(v[b'host/'+case['evidence']['key'].encode()+b'/journal.json']))
def position(case,v):
    f=fingerprint(v.get(b'project/pack/rules.txt'));j=case['journal']
    return 0 if f==j['changes'][0]['before']else 1 if f==j['changes'][0]['after']else 2

def view(case,v):
    j=journal(case,v);prior=case['evidence']['file'];at=v.get(b'project/pack/rules.txt')
    original=j['changes'][0]['before_object'];root=case['evidence']['root']
    # Within these quiescent private fixtures the original file is retained when
    # replaced. Device/inode distinguishes the actual retained versus new object;
    # no reboot, birth/token substitution, or general native capability is inferred.
    bound=at is not None and (at['device'],at['inode'])==(prior['volume'],prior['object']) and original==dict(persistent=prior['persistent'])
    state=b'host/'+case['evidence']['key'].encode()+b'/'+case['operation'].encode()+b'/'
    candidate=state+(b'restore-0'if j['restoring']else b'after-0')
    return dict(supported=j['schema']==5,rootMatches=j['root']==dict(persistent=root['persistent']),committed=j['committed'],restoring=j['restoring'],
        position=position(case,v),beforeObject=bound,candidateValid=fingerprint(v.get(candidate))==j['changes'][0]['after'],
        beforeValid=fingerprint(v.get(state+b'before-0'))==j['changes'][0]['before'])
def observed_same(a,b):
    x=a.get(b'project/pack/rules.txt');y=b.get(b'project/pack/rules.txt')
    def typed(v):
        return None if v is None else (fingerprint(v),v['mode'],v['device'],v['inode'])
    return typed(x)==typed(y)


def cases():
    r=json.loads((RUN/'receipt.json').read_text());commands={c['label']:c for c in r['commands']};rows=[]
    for c in r['cases']:
        for label in c['commands']:
            cmd=commands[label];argv=cmd['argv'];action=argv[argv.index('recover')+1]
            prepared=load(cmd['before']);observed=load(cmd.get('afterExplicitEdit',cmd['before']));after=load(cmd['after'])
            mode=0 if action=='inspect'else 1 if '--dry-run'in argv else 2
            data=dict(mode=mode,restore=action=='restore',accepted=cmd.get('answer','y')=='y',
                operationMatches=('--operation'not in argv or argv[argv.index('--operation')+1]==journal(c,prepared)['operation']),
                sameJournal=journal(c,prepared)==journal(c,observed),sameVisible=observed_same(prepared,observed),prepared=view(c,prepared),observed=view(c,observed))
            text=ansi.sub('',(RUN/(label+'.stdout')).read_text()+'\n'+(RUN/(label+'.stderr')).read_text())
            match=re.search(r'(?:Finish saved changes|Finish restoring previous files|Restore previous files): (\d+) file change',text)
            j=journal(c,after);scratch=b'host/'+c['evidence']['key'].encode()+b'/'+c['operation'].encode()+b'/restore-0'
            expected='/'.join(map(str,[cmd['exitCode'],0 if match is None else int(match[1])+1,position(c,after),int(j['committed']),int(j['restoring']),int(scratch not in observed and scratch in after)]))
            rows.append(dict(id=label,input=data,expected=expected,sourceCommand=cmd))
    assert len(rows)==45 and len({r['id']for r in rows})==45
    return rows


def boolean(b):return 'True{}'if b else 'False{}'
def bend_view(v):
    return 'S.RView{'+','.join(str(v[k])+'n'if k=='position'else boolean(v[k])for k in ['supported','rootMatches','committed','restoring','position','beforeObject','candidateValid','beforeValid'])+'}'
def bend_row(r):
    return 'S.RRequest{'+','.join([str(r['mode'])+'n',boolean(r['restore']),boolean(r['accepted']),boolean(r['operationMatches']),boolean(r['sameJournal']),boolean(r['sameVisible']),bend_view(r['prepared']),bend_view(r['observed'])])+'}'


def compare(row,actual):
    assert actual==row['expected'],(row['id'],actual,row['expected'],row['input'])


def main():
    checked=subprocess.run(['python3',str(HERE/'recovery_observations.py')],cwd=ROOT,capture_output=True,text=True,timeout=90)
    assert checked.returncode==0,checked.stdout+checked.stderr
    rows=cases();generated=HERE/'generated';formal=generated/'formal';artifact=formal/'applications/empack/Recovery.olean';artifact.parent.mkdir(parents=True,exist_ok=True)
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend');env=dict(os.environ,LEAN_PATH=str(formal),BEND_NO_TELEMETRY='1')
    p=subprocess.run([lean,'-DwarningAsError=true','-o',str(artifact),'applications/empack/Recovery.lean'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    assert p.returncode==0,p.stdout+p.stderr
    path=generated/'recovery.json'
    def replay(data):
        path.write_text(json.dumps(data)+'\n')
        return subprocess.run([lean,'--run','applications/empack/RecoveryCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    data=dict(schema=1,profile='one-file-authored-recovery',cases=[r['input']for r in rows]);p=replay(data);assert p.returncode==0,p.stdout+p.stderr
    actual=json.loads(p.stdout);assert len(actual)==len(rows)
    for row,(a,_)in zip(rows,actual):compare(row,a)
    driver=generated/'RecoveryCase.bend'
    calls=[]
    for row in rows:
        r=row['input'];calls.append('S.render(S.evaluate('+bend_row(r)+')) ++ "/" ++ Bool.pick(String,S.proposed('+bend_view(r['prepared'])+','+boolean(r['restore'])+'),"1","0") ++ "\\n"')
    driver.write_text('import Base\nimport ../Recovery.bend as S\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
    p=subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    assert p.stdout.splitlines()==[a+'/'+str(int(candidate))for a,candidate in actual]
    negatives=[]
    for name,edit in [('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='complete-recovery')),('count',lambda d:d.update(cases=d['cases']*6)),
        ('mode',lambda d:d['cases'][0].update(mode=3)),('position',lambda d:d['cases'][0]['prepared'].update(position=3)),('observed-position',lambda d:d['cases'][0]['observed'].update(position=3)),
        ('missing-field',lambda d:d['cases'][0].pop('accepted')),('wrong-bool',lambda d:d['cases'][0].update(accepted='yes'))]:
        d=copy.deepcopy(data);edit(d);p=replay(d);assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);negatives.append(name)
    differences=[row['id']for row,(a,candidate)in zip(rows,actual)if row['input']['mode']!=0 and candidate!=(a.split('/')[1]!='0')]
    # All six measured fields pass through the actual comparison boundary.
    mutations=[]
    for field in range(6):
        row=copy.deepcopy(rows[0]);m=row['expected'].split('/');m[field]='99';row['expected']='/'.join(m)
        try:compare(row,actual[0][0])
        except AssertionError:mutations.append(field)
        else:raise AssertionError('Observation mutation escaped: '+str(field))
    files=[HERE/n for n in ['Recovery.lean','Recovery.bend','RecoveryCase.lean','recovery_conformance.py','recovery_probe.py','recovery_fixture_oracle.rs','recovery_observations.py']]
    files +=[ROOT/'applications/sources/empack-recovery-selections.json']
    files +=[p for p in RUN.rglob('*')if p.is_file()and 'work'not in p.relative_to(RUN).parts and p.name!='conformance.json']
    receipt=dict(schema=1,sourceRevision='0b4462e3032b4f09230b15329722eabefb7f574c',installedCLIComparisons=45,researchRefusals=negatives,
        measuredFieldMutationControls=mutations,proposedEarlierRefusals=differences,basisSha256={str(p.relative_to(ROOT)):sha(p)for p in sorted(set(files))},
        tools={n:dict(path=str(Path(p).resolve()),sha256=sha(Path(p)))for n,p in [('lean',lean),('bend',bend)]},generatedDriverSha256=sha(driver),
        limits=['Pure replay of authored one-file journal fixtures,not another native/crash run.',
            'Native shape/crypto/capability,global unchanged inventory and directory/cancellation/creation/multi-file lifecycles are not supplied by these models.',
            'External raw-image decoder attributes object relations under private-root retention/quiescence;does not recreate durable tokens or general native authority.',
            'New early before-image verification remains proposed;actual execution must still validate its own inputs.'])
    (RUN/'conformance.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items()if k!='basisSha256'},indent=2))


if __name__=='__main__':main()
