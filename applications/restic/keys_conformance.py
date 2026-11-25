#!/usr/bin/env python3
"""Pure comparison of successful key-wrapper operations and admission refusals."""
import copy,hashlib,json,os,subprocess
from pathlib import Path
import keys_observations as observations

ROOT=observations.ROOT
HERE=Path(__file__).resolve().parent
RUN=observations.RUN
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def build(receipt,commands,keyset):
    identities=receipt['identities'];tokens={identities[k]:i for i,k in enumerate(['initial','duplicate','changed'],1)}
    def state(image):
        keys=keyset(image);return dict(a=identities['initial']in keys,b=identities['duplicate']in keys,c=identities['changed']in keys,backing=1)
    rows=[]
    for c in commands[4:]:
        name=c['case'];before=state(c['before']);after=state(c['after'])
        kind=1 if name in ['add-same-password','add-wrong-password']else 2 if name=='change-one-password'else 4 if name=='add-empty-password'else 3 if name.startswith('remove-')else 0
        target=tokens.get(c['argv'][-1],4)if kind==3 else 0
        data=dict(**before,kind=kind,password={'a':1,'b':2,'wrong':3}[c['passwordLabel']],hint=tokens.get(c['keyHint'],0),target=target)
        current=None
        if name.startswith('list-'):
            listed=json.loads((RUN/(name+'.stdout')).read_text());current=tokens[next(k['id']for k in listed if k['current'])]
        values=[int(after[k])for k in ['a','b','c','backing']]+[c['outcome']['exitCode'],current]
        rows.append(dict(case=name,input=data,expected=values,measuredFields=list(range(6))if current is not None else list(range(5)),
            premise='Password labels follow the controlled add/change inputs and independent opens;no password derivation or decryption simulated. Current-key token measured only in list output. Non-key repository bytes separately checked unchanged.'))
    assert len(rows)==17;return rows


def compare(row,value):
    actual=list(map(int,value.split('/')));assert len(actual)==6
    for i in row['measuredFields']:assert actual[i]==row['expected'][i],(row['case'],i,actual,row['expected'])


def main():
    receipt,commands,keyset=observations.inspect();rows=build(receipt,commands,keyset);generated=HERE/'generated';generated.mkdir(exist_ok=True)
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend');env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1')
    target=ROOT/'.build/formal/applications/restic/Keys.olean';target.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.run([lean,'-DwarningAsError=true','-o',str(target),'applications/restic/Keys.lean'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    path=generated/'keys.json';data=dict(schema=1,profile='three-wrapper-local-repository',rows=[r['input']for r in rows])
    def replay(value):
        path.write_text(json.dumps(value)+'\n');return subprocess.run([lean,'--run','applications/restic/KeysCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    p=replay(data);assert p.returncode==0,p.stdout+p.stderr;actual=json.loads(p.stdout);assert len(actual)==len(rows)
    for r,v in zip(rows,actual):compare(r,v)
    calls=[]
    for row in rows:
        r=row['input'];b=lambda k:'True{}'if r[k]else'False{}'
        state='S.KState{'+','.join([b(k)for k in ['a','b','c']]+[str(r['backing'])+'n'])+'}'
        calls.append('S.render(S.run('+','.join([state]+[str(r[k])+'n'for k in ['kind','password','hint','target']])+')) ++ "\\n"')
    driver=generated/'KeysCase.bend';driver.write_text('import Base\nimport ../Keys.bend as S\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
    p=subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr;assert p.stdout.splitlines()==actual
    refusals=[]
    for name,edit in [('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='crypto-proof')),('count',lambda d:d.update(rows=d['rows']*8)),
        ('operation',lambda d:d['rows'][0].update(kind=5)),('password',lambda d:d['rows'][0].update(password=4)),('hint',lambda d:d['rows'][0].update(hint=4)),
        ('backing',lambda d:d['rows'][0].update(backing=0)),('target',lambda d:d['rows'][0].update(target=5)),('boolean',lambda d:d['rows'][0].update(a='true')),
        ('ambiguous-scan',lambda d:d['rows'][0].update(a=True,b=True,hint=0)),('duplicate-id',lambda d:d['rows'][0].update(kind=1,b=True))]:
        bad=copy.deepcopy(data);edit(bad);p=replay(bad);assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);refusals.append(name)
    mutations=[];n=next(i for i,r in enumerate(rows)if r['case']=='list-old-password')
    for i in range(6):
        bad=copy.deepcopy(rows[n]);bad['expected'][i]=999
        try:compare(bad,actual[n])
        except AssertionError:mutations.append('outcome-'+str(i))
        else:raise AssertionError('Changed key result escaped')
    files=[HERE/n for n in ['Keys.lean','Keys.bend','KeysCase.lean','keys_probe.py','keys_observations.py','keys_conformance.py']]
    files +=[ROOT/'applications/sources/restic-keys-selections.json']
    files +=[p for p in RUN.iterdir()if p.is_file()and p.name!='conformance.json']
    report=dict(schema=1,nativeCommands=21,postBackupComparisons=len(rows),currentKeyComparisons=sum(5 in r['measuredFields']for r in rows),
        researchRefusals=refusals,observationMutations=mutations,comparisons=[{**r,'model':v}for r,v in zip(rows,actual)],
        basisSha256={str(p.relative_to(ROOT)):sha(p)for p in sorted(set(files))},driverSha256=sha(driver),
        tools={n:dict(path=str(Path(p).resolve()),sha256=sha(Path(p)))for n,p in [('lean',lean),('bend',bend)]},
        limits=['No restic,crypto,backend or password-file mutation in replay. Credential labels are controlled witness relations,not cryptographic proofs. IDs are exact native wrappers mapped to three research tokens.',
            'Non-key backing token comes from independently equal repository file/hash images;not a master-key export. Three successful payload dumps independently verify readable fixture content.',
            'List current-key fields are native;other returned current tokens are model/source-only. No persistent active key setting is inferred.',
            'Only selected successful key writes/verifications/removals and explicit admission/current-key refusals;IO failure,crash,concurrency,scan limit and ambiguous unhinted ordering remain open.',
            'Password change replaces one wrapper and does not rotate the master or revoke another wrapper sharing its old password. Copied-key revocation is not tested.',
            'Password-change output describes a Key object while help promises its ID;reporting proposal remains separate from current behavior.'])
    (RUN/'conformance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in ['comparisons','basisSha256']},indent=2))


if __name__=='__main__':main()
