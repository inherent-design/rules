#!/usr/bin/env python3
"""Pure comparison of retained synthetic account components; no app/auth IO."""
import copy,hashlib,json,os,re,subprocess
from pathlib import Path
import accounts_observations as observations

ROOT,HERE,RUN=observations.ROOT,Path(__file__).resolve().parent,observations.RUN
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bit=lambda b:'1'if b else'0'


def actor(a):
    return dict(id=a['id'],name=a['name'],profileId=a['profileId'],kind=a['type'],owns=a['owns'],hasToken=a['tokenPresent'],
        validity=a['validity'],hasExpiry=a['hasExpiry'],expiresIn=a['expiresIn'],hasIssue=a['hasIssue'],issuedAgo=a['issuedAgo'])


def normalized(c):
    a=c.get('account',c.get('accounts',[{}])[0]);p=c.get('profileResponse',dict(id='',name=''))
    # The private candidate's shape check does not authenticate its response or
    # bind it to the selected actor. Those remain external fixture premises.
    shape=bool(re.fullmatch('[0-9a-f]{32}',p['id'])and re.fullmatch('[A-Za-z0-9_]{3,16}',p['name']))
    return dict(kind=['identity','refresh','claim','login'].index(c['kind']),actor=actor(a),actors=[actor(a)for a in c.get('accounts',[])],
        selected=c.get('selected',''),mode=c.get('mode',0),mutation=['none','offline','demo'].index(c.get('mutation','none')),
        fill=c.get('fill',False),inUse=c.get('inUse',False),accepted=c.get('accept',False),
        profileId=p['id'],profileName=p['name'],shapeValid=shape,
        missingUuid=observations.offline_uuid(a['name']or'No Minecraft profile'),
        demoUuid='3'*32 if c['kind']=='identity'else observations.offline_uuid('Demo_Player'))


def session(s):
    return [s['session'],s['access_token'],str(s['mode']),s['name'],s['uuid'],s['user_type']]


def account(a):
    return [a['id'],a['rawName'],a['profileName'],a['profileId'],bit(a['owns']),bit(a['hasProfile']),str(a['uses'])]


def measured(row):
    if row['kind']=='identity':
        return [bit(row['account']['owns']),bit(row['account']['hasProfile']),row['account']['profileName']]+session(row['before'])+session(row['after'])
    if row['kind']=='refresh':return ['?'if row['remaining']is None else str(row['remaining']),str(row['uses']),bit(row['refresh'])]
    if row['kind']=='claim':
        fields=[row['claimed'],row['candidateClaimed']]
        for name in ['before','held','oneFinalized','finalized','candidateHeld','candidateFinalized']:
            for a in row[name]:fields +=[a['id'],str(a['uses']),bit(a['refresh'])]
        return fields
    fields=[]
    for name in ['current','refillOnly','admittedThenRefill']:
        r=row[name];fields += account(r['before'])+account(r['account'])+session(r['session'])
        fields +=[str(r['dialogs']),str(r['launches']),bit(r['aborted']),r['error']]
    return fields


def bend_actor(a):
    b=lambda v:'True{}'if v else'False{}'
    n=lambda v:str(abs(v))+'n'
    time='S.remaining('+','.join([b(a['hasExpiry']),b(a['expiresIn']<0),str(abs(a['expiresIn'])),b(a['hasIssue']),b(a['issuedAgo']<0),str(abs(a['issuedAgo']))])+')'
    values=[json.dumps(a['id']),json.dumps(a['name']),json.dumps(a['profileId']),n(a['kind']),b(a['owns']),b(a['hasToken']),n(a['validity']),time]
    return 'S.AAccount{'+','.join(values)+'}'


def bend_call(r):
    b=lambda v:'True{}'if v else'False{}'
    s=json.dumps;a=bend_actor(r['actor']);mode=str(r['mode'])+'n'
    if r['kind']==0:call='S.identity_fields('+','.join([a,mode,b(r['fill']),str(r['mutation'])+'n',s(r['missingUuid']),s(r['demoUuid'])])+')'
    elif r['kind']==1:call='S.refresh_fields('+a+','+b(r['inUse'])+')'
    elif r['kind']==2:
        actors='Nil{}'
        for a in reversed(r['actors']):actors='Con{'+bend_actor(a)+','+actors+'}'
        call='S.claim_fields('+','.join([actors,s(r['selected']),mode])+')'
    else:
        profile='S.AProfile{'+s(r['profileId'])+','+s(r['profileName'])+'}'
        call='S.login_fields('+','.join([a,mode,b(r['accepted']),b(r['shapeValid']),profile,s(r['missingUuid']),s(r['demoUuid'])])+')'
    return 'S.joined('+call+') ++ "\\n"'


def compare(expected,actual):
    assert actual==expected,(actual,expected)


def main():
    receipt,inputs,observed=observations.inspect();rows=[normalized(c)for c in inputs];expected=[measured(r)for r in observed]
    generated=HERE/'generated';generated.mkdir(exist_ok=True)
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1')
    target=ROOT/'.build/formal/applications/prism/Accounts.olean';target.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.run([lean,'-DwarningAsError=true','-o',str(target),'applications/prism/Accounts.lean'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    assert p.returncode==0,p.stdout+p.stderr
    path=generated/'accounts.json';data=dict(schema=1,profile='prism-account-method-components',rows=rows)
    def replay(value):
        path.write_text(json.dumps(value)+'\n')
        return subprocess.run([lean,'--run','applications/prism/AccountsCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    p=replay(data);assert p.returncode==0,p.stdout+p.stderr;actual=json.loads(p.stdout);compare(expected,actual)
    driver=generated/'AccountsCase.bend'
    driver.write_text('import Base\nimport ../Accounts.bend as S\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(bend_call(r)for r in rows)+')\n')
    p=subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    lines=p.stdout.splitlines();assert len(lines)==len(rows)and all(s.endswith('|')for s in lines)
    compare(expected,[s[:-1].split('|')for s in lines])
    refusals=[]
    for name,edit in [('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='full-prism-app')),
        ('count',lambda d:d.update(rows=d['rows']*5)),('operation',lambda d:d['rows'][0].update(kind=4)),
        ('mode',lambda d:d['rows'][0].update(mode=3)),('mutation',lambda d:d['rows'][0].update(mutation=3)),
        ('kind',lambda d:d['rows'][0]['actor'].update(kind=2)),('validity',lambda d:d['rows'][0]['actor'].update(validity=3)),
        ('time-bound',lambda d:d['rows'][0]['actor'].update(expiresIn=200001)),
        ('duplicate-actors',lambda d:d['rows'][19].update(actors=[d['rows'][19]['actors'][0]]*2)),
        ('missing-selected',lambda d:d['rows'][19].update(selected='unknown')),
        ('shape-witness',lambda d:d['rows'][24].update(shapeValid=False)),('uuid-witness',lambda d:d['rows'][0].update(missingUuid='?')),
        ('line-codec',lambda d:d['rows'][0]['actor'].update(name='A|B')),('boolean',lambda d:d['rows'][0].update(fill='true')),
        ('missing-field',lambda d:d['rows'][0].pop('inUse'))]:
        bad=copy.deepcopy(data);edit(bad);p=replay(bad)
        assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);refusals.append(name)
    # Distinguish wrong output fields from wrong fixture/model inputs. These
    # controls keep the actual observed rows immutable and test comparison.
    mutations=[]
    for name,index,field,value in [('session-uuid',0,7,'wrong'),('unknown-time',16,0,'0'),('refresh-cutoff',11,2,'1'),
        ('source-holder',19,0,'B'),('candidate-holder',19,1,'A'),('source-use-count',19,9,'9'),
        ('login-profile',24,10,'wrong'),('login-launch-request',24,21,'0'),('candidate-profile',24,58,'wrong'),
        ('candidate-refusal',26,69,'1')]:
        bad=copy.deepcopy(expected);assert bad[index][field]!=value,(name,index,field)
        bad[index][field]=value
        try:compare(bad,actual)
        except AssertionError:mutations.append(name)
        else:raise AssertionError('Changed native projection escaped: '+name)
    files=[HERE/n for n in ['Accounts.lean','Accounts.bend','AccountsCase.lean','accounts_probe.py','accounts_observations.py','accounts_conformance.py']]
    files +=[ROOT/'applications/sources/prism-accounts-selections.json']
    files +=[p for p in RUN.iterdir()if p.is_file()and p.name!='conformance.json']
    report=dict(schema=1,cases=30,units=dict(identity=7,refresh=12),components=dict(claim=5,loginPrefix=6),loginVariants=3,
        comparisons=[dict(id=c['id'],kind=c['kind'],input=r,observed=e,model=v)for c,r,e,v in zip(inputs,rows,expected,actual)],
        researchRefusals=refusals,observationMutations=mutations,basisSha256={str(p.relative_to(ROOT)):sha(p)for p in sorted(set(files))},
        driverSha256=sha(driver),tools={n:dict(path=str(Path(p).resolve()),sha256=sha(Path(p)))for n,p in [('lean',lean),('bend',bend)]},
        limits=['Pure replay only;no Qt,compiler,Prism,auth,GUI,network or game executed.',
            'Native selected source methods plus declared adapters,not full account/session APIs. Fixed clock replaces one current-time call;Qt6.12 differs from unqualified app-bundled Qt.',
            'All actors retained. shared_ptr fixture aliases and omitted QObject use notifications do not qualify destruction,reentrancy or shared_qobject_ptr ownership.',
            'Login prefix starts after mode admission;launch requests are stub counters,not game starts. Dialog NoError accepts without updating the source account.',
            'Profile candidate uses admitted same-actor fixture data plus a shape check. Format is not authentication;actual parser/network/result ambiguity and durable persistence remain unqualified.',
            'UUID witnesses are independently computed name-MD5 identities,not cryptographic proofs. Unknown expiry is preserved separately from source Qt invalid-secsTo fallback.',
            'Three later caller-source selections support reachability only and were not compiled in the native cohort. Toolchain/bundle metadata readbacks were post-run,not frozen SDK or running-app attestations.',
            'Restricted line codec bounds only this research comparison,not real Prism inputs;no cross-platform,full OAuth,account file,entitlement or cancellation-lifetime claim.'])
    (RUN/'conformance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k not in ['comparisons','basisSha256']},indent=2))


if __name__=='__main__':main()
