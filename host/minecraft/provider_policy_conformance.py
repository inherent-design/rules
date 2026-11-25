#!/usr/bin/env python3
"""Pure original-policy replay from the selected provider fixture;no Java or loader launch."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CAPTURE='provider-policy-20261125T174555987623Z'
KEYS=['modefite.model_rotations','modefite.item_definitions']
ROTATION=['client.MultiAxisModelMixin']
ITEMS=['client.definitions.Definition'+n+'Mixin'for n in ['Loading','Bakery','Binding','Registry','Resolver','Rendering']]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def row(**values):return dict.fromkeys(['selected','rotation','items','client','modefite','polytone'])|values


def facts(spec):
    version=spec['mods'].get('modefite');assert version in [None,'1.0.1+1.21.1','1.0.1+1.21.2']
    assert type(spec['client'])is bool and spec['model']in [-1,0,1]and spec['items']in [-1,0,1]
    return row(selected=spec.get('compatSelected',True),rotation=2 if spec['model']==-1 else spec['model'],items=2 if spec['items']==-1 else spec['items'],
        client=spec['client'],modefite=0 if version is None else 1 if version=='1.0.1+1.21.1'else 2,polytone='polytone'in spec['mods'])


def outcome(raw):
    if raw['status']=='not-invoked':
        assert set(raw)=={'id','status'};return [2,5,5,0,2]
    if raw['status']=='threw':
        assert raw['errorClass']=='IllegalStateException'
        assert '1.0.1+1.21.1'in raw['message']and'1.0.1+1.21.2'in raw['message']
        named=[i for i,k in enumerate(KEYS)if k in raw['message']];assert len(named)==1
        return [1,5,5,0,named[0]]
    assert raw['status']=='returned';states=[]
    for k in KEYS:
        f=raw['features'][k];assert type(f['enabled'])is bool
        if f['enabled']:assert set(f)=={'enabled'};states.append(3)
        else:
            assert f['reason']in ['DISABLED','WRONG_SIDE','MISSING']
            assert f['details']==(['modefite']if f['reason']=='MISSING'else[])
            states.append({'DISABLED':0,'WRONG_SIDE':1,'MISSING':2}[f['reason']])
    expected=(ROTATION if states[0]==3 else[])+(ITEMS if states[1]==3 else[])
    assert raw['mixins']==expected,'Candidate names/order differ.'
    return [0,*states,len(raw['mixins']),2]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private',action='store_true',help='Compare the original owner-local capture instead of its public export.')
    args=parser.parse_args()
    cap=(ROOT/'.build/minecraft'if args.private else HERE/'evidence')/CAPTURE
    r=json.loads((cap/'receipt.json').read_text());raw=json.loads((cap/'observed.json').read_text());request=json.loads((cap/'request.json').read_text())
    assert r['observerErrors']==raw['observerErrors']==0
    assert sha(cap/'request.json')==r['requestSha256']and sha(cap/'observed.json')==r['observed.jsonSha256']
    assert request==json.loads((HERE/'provider-cases.json').read_text())
    for n,h in r['sourcesSha256'].items():assert sha(cap/n)==h
    for stem,c in zip(['compile','execute'],r['commands'],strict=True):
        assert c['exitCode']==0 and c['ownedGroupAbsent']and not c['timedOut']
        for channel in ['stdout','stderr']:assert sha(cap/(stem+'.'+channel))==c[channel+'Sha256']
    assert raw['featureDefaults']==dict.fromkeys(KEYS,True)
    assert [s['id']for s in request['metadata']]==[s['id']for s in raw['metadata']]
    work=ROOT/'.build/minecraft/provider-policy-replay';work.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=os.environ.get('LEAN_PATH',str(ROOT/'.build/formal')),BEND_NO_TELEMETRY='1')
    def lean(data,label):
        p=work/(label+'.json');p.write_text(json.dumps(data)+'\n')
        return subprocess.run([os.environ.get('LEAN','lean'),'--run',str(HERE/'ProviderPolicyCase.lean'),str(p)],cwd=ROOT,env=env,text=True,capture_output=True,timeout=30)
    def bend(rows,label):
        calls=[]
        for d in rows:
            bo=lambda k:'True{}'if d[k]else'False{}'
            args=[bo('selected'),'True{}'if d['rotation']else'False{}','True{}'if d['items']else'False{}',bo('client'),str(d['modefite']or 0)+'n',bo('polytone')]
            calls.append('show(M.provider_evaluate('+','.join(args)+')) ++ "\\n"')
        p=work/(label+'.bend');p.write_text('import Base\nimport ../../../host/minecraft/ProviderPolicy.bend as M\ndef show(xs: List<&2, Nat>) -> String:\n  match xs:\n    case Nil{}: ""\n    case Con{h,t}: Nat.show(h) ++ "," ++ show(t)\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
        result=subprocess.run([os.environ.get('BEND','bend'),str(p)],cwd=ROOT,env=env,text=True,capture_output=True,timeout=30);assert result.returncode==0,result.stdout+result.stderr
        assert all(s.endswith(',')for s in result.stdout.splitlines())
        return [[int(n)for n in s[:-1].split(',')]for s in result.stdout.splitlines()]
    dto=dict(schema=1,contract='isolated-compat-model-policy-v1',rows=[facts(s)for s in request['metadata']])
    result=lean(dto,'plan');assert result.returncode==0,result.stdout+result.stderr;predicted=json.loads(result.stdout)
    assert predicted==bend(dto['rows'],'plan')
    assert [outcome(s)for s in raw['metadata']]==predicted
    valid=row(selected=True,rotation=1,items=1,client=True,modefite=1,polytone=False)
    invalid=[dict(dto,schema=2),dict(dto,contract='active-installed-provider'),dict(dto,rows=[valid]*129)]
    for change in [dict(selected=None),dict(rotation=None),dict(items=None),dict(client=None),dict(modefite=None),dict(rotation=3),dict(items=3),dict(modefite=3),dict(selected=1),dict(client=1)]:invalid.append(dict(dto,rows=[valid|change]))
    for i,data in enumerate(invalid):assert lean(data,'invalid-'+str(i)).returncode==2
    unused=[row(selected=False),row(selected=True,rotation=0,items=0),row(selected=True,rotation=1,items=1,client=False)]
    result=lean(dict(dto,rows=unused),'unused');assert result.returncode==0
    assert json.loads(result.stdout)==bend(unused,'unused')
    controls=[]
    tests=[('missing-activation','guard-1-1-1-missing-1','enable'),('disabled-reason','guard-0-0-0-other-0','reason'),
        ('side-reason','guard-0-1-1-other-1','reason'),('candidate-loss','guard-1-1-1-exact-0','candidate'),
        ('candidate-order','guard-1-1-1-exact-0','order'),('wrong-feature-refusal','guard-1-0-1-other-0','error')]
    for label,identity,kind in tests:
        changed=copy.deepcopy(raw['metadata']);target=next(s for s in changed if s['id']==identity)
        if kind=='enable':target['features'][KEYS[0]]={'enabled':True}
        elif kind=='reason':target['features'][KEYS[0]]['reason']='MISSING'
        elif kind=='candidate':target['mixins']=[]
        elif kind=='order':target['mixins'].reverse()
        else:target['message']=target['message'].replace(KEYS[1],KEYS[0])
        try:assert [outcome(s)for s in changed]==predicted
        except AssertionError:controls.append(label)
        else:raise AssertionError('Changed provider result admitted.')
    result=dict(schema=1,status='passed-retained-original-policy',privateCapture=args.private,nativeSelectComparisons=55,nonInvokedProcedureRecords=4,totalModelVectors=59,
        leanLaws=14,bendLaws=8,decoderRefusals=len(invalid),unneededUnknownExamples=3,changedObservationControls=controls,
        basisSha256={str(p.relative_to(ROOT)):sha(p)for p in [cap/'receipt.json',cap/'request.json',cap/'observed.json',*[HERE/n for n in ['ProviderPolicy.lean','ProviderPolicy.bend','ProviderPolicyCase.lean','provider_policy_conformance.py','provider-cases.json']]]},
        limits=['Supplied metadata/isolated feature settings;not actual installed providers/loader/plugin/Mixin application or full startup.',
            '55 actual select calls plus4 authored procedure-skipped rows;the skipped branch is not a native provider decision.',
            'Shared inspected projection;no JVM/translation/adapter proof.',
            'Configuration Reader5 observations remain unmodeled;the separate adaptation comparison owns27 JSON helper calls.'])
    (work/'conformance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ['basisSha256','limits']}))


if __name__=='__main__':main()
