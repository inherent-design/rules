#!/usr/bin/env python3
"""Pure Lean/Bend replay of retained original CodecUI one-field calls; no JVM launch."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAPTURE = 'evidence/schema-record-20261125T103534782983Z'
CONTRACT = 'codecui-1.21.1-1.4.10-dfu8-one-field'
FORMS = ['required','optional-wrapper','default-zero','default-null','map-required','map-default-two']
KINDS = ['missing','zero','seven','wrong-type','null']
INPUTS = [{},{'value':0},{'value':7},{'value':'bad'},{'value':None}]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def project(row):
    assert row['form'] in FORMS and row['inputKind'] in KINDS
    assert json.dumps(row['input'],sort_keys=True) == json.dumps(INPUTS[KINDS.index(row['inputKind'])],sort_keys=True)
    assert row['advertisedName']=='value' and row['advertisedInline'] is False
    assert all(type(row[k]) is bool for k in ['advertisedOptional','success'])
    default = row['advertisedDefault']
    assert default is None or type(default) is int and default==0
    present, value, encoded = False, 0, False
    if row['success']:
        assert type(row['valuePresent']) is bool and row['encodeSuccess'] is True
        present = row['valuePresent']
        assert (type(row['value']) is int and row['value'] in [0,2,7]) if present else row['value'] is None
        value = row['value'] if present else 0
        assert type(row['encoded']) is dict and set(row['encoded']) <= {'value'}
        encoded = 'value' in row['encoded']
        if encoded:assert present and type(row['encoded']['value']) is int and row['encoded']['value']==value
        assert 'error' not in row
    else:
        assert type(row['error']) is str and row['error']
        assert not {'valuePresent','value','encodeSuccess','encoded'} & set(row)
    request = dict(form=FORMS.index(row['form']),input=KINDS.index(row['inputKind']))
    answer = [int(row['advertisedOptional']),int(default is not None),default or 0,int(row['success']),int(present),value,int(encoded)]
    return request, answer


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',type=Path); args = parser.parse_args()
    capture = HERE/CAPTURE; receipt=json.loads((capture/'receipt.json').read_text())
    assert receipt['bundledSha256']=='389766940c13572819b4ba79cf9466c571256f01ecd0cb43dc3ac4b11ff3805a'
    assert receipt['profile']['JAVA_VERSION'].startswith('21.')
    contracts=json.loads((HERE/'polytone-contracts.json').read_text())
    breadth=json.loads((HERE/'polytone-managers.json').read_text())
    assert contracts['breadthSha256']==sha(HERE/'polytone-managers.json')
    assert contracts['artifactSha256']==breadth['artifactSha256']
    assert [(m['id'],m['reloadOrder']) for m in contracts['managers']]==sorted([(m['id'],m['reloadOrder']) for m in breadth['managers']],key=lambda p:p[1])
    library=next(l for l in contracts['libraries'] if l['declaration']['identifier']['artifact']=='codecui-neoforge')
    assert library['sha256']==receipt['bundledSha256']
    for name,source in contracts['librarySources'].items():
        if source['originalClassEntry'] in receipt['loadedBundledClassEntriesSha256']:
            assert source['originalClassSha256']==receipt['loadedBundledClassEntriesSha256'][source['originalClassEntry']]
    assert contracts['librarySources']['net/mehvahdjukaar/codecui/SchemaRecord.java']['originalClassEntry'] in receipt['loadedBundledClassEntriesSha256']
    for name,digest in receipt['sourcesSha256'].items():assert sha(capture/name)==digest
    for stem,command in zip(['compile','execute'],receipt['commands']):
        assert command['exitCode']==0 and command['ownedGroupAbsent'] and not command['timedOut']
        for stream in ['stdout','stderr']:assert sha(capture/(stem+'.'+stream))==command[stream+'Sha256']
    assert sha(capture/'observed.json')==receipt['observedSha256']==sha(capture/'execute.stdout')
    observed=json.loads((capture/'observed.json').read_text())
    native=observed['cases'];assert observed['schema']==1 and len(native)==30
    assert [(r['form'],r['inputKind']) for r in native]==[(f,k) for f in FORMS for k in KINDS]
    pairs=[project(r) for r in native]; rows=[r for r,a in pairs]; answers=[a for r,a in pairs]
    work=ROOT/'.build/minecraft/schema-record-replay';work.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=os.environ.get('LEAN_PATH',str(ROOT/'.build/formal')),BEND_NO_TELEMETRY='1')
    envelope=lambda rs:dict(schema=1,contract=CONTRACT,cases=rs)
    def lean_run(request,name):
        path=work/(name+'.json');path.write_text(json.dumps(request)+'\n')
        return subprocess.run([os.environ.get('LEAN','lean'),'--run',str(HERE/'SchemaRecordCase.lean'),str(path)],
            cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    def bend_run(rs,name):
        path=work/(name+'.bend')
        calls=['render(M.sc_evaluate('+str(r['form'])+'n,'+str(r['input'])+'n)) ++ "\\n"' for r in rs]
        path.write_text('''import Base
import ../../../host/minecraft/SchemaRecord.bend as M
def bit(b: Bool) -> String:
  Bool.pick(String,b,"1","0")
def render(r: M.RecordResult) -> String:
  match r:
    case M.RecordResult{o,d,n,s,p,v,e}: bit(o) ++ ":" ++ bit(d) ++ ":" ++ Nat.show(n) ++ ":" ++ bit(s) ++ ":" ++ bit(p) ++ ":" ++ Nat.show(v) ++ ":" ++ bit(e)
def main() -> IO(Unit):
  IO.write('''+' ++ '.join(calls)+')\n')
        result=subprocess.run([os.environ.get('BEND','bend'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
        assert result.returncode==0,result.stdout+result.stderr
        return [[int(v) for v in line.split(':')] for line in result.stdout.splitlines()]
    result=lean_run(envelope(rows),'cases');assert result.returncode==0,result.stdout+result.stderr
    assert json.loads(result.stdout)==answers and bend_run(rows,'Cases')==answers
    negatives=[dict(envelope(rows),schema=2),dict(envelope(rows),contract='other-version'),
        envelope([dict(form=6,input=0)]),envelope([dict(form=0,input=5)]),
        envelope([dict(form=True,input=0)]),envelope([dict(form=0,input=-1)]),
        envelope([dict(form=0,input=0.5)]),envelope([rows[0]]*65)]
    for i,request in enumerate(negatives):assert lean_run(request,'negative-'+str(i)).returncode==2
    variants=[]
    def variant(form,kind,changes):
        row=copy.deepcopy(next(r for r in native if r['form']==form and r['inputKind']==kind));row.update(changes)
        request,wrong=project(row);variants.append((request,wrong))
    variant('map-required','missing',dict(advertisedOptional=False))
    variant('optional-wrapper','missing',dict(valuePresent=True,value=0))
    variant('default-zero','seven',dict(encoded={}))
    variant('map-default-two','missing',dict(value=0))
    variant('map-default-two','missing',dict(advertisedDefault=0))
    variant('required','seven',dict(encoded={}))
    requests=[r for r,a in variants];wrong=[a for r,a in variants]
    result=lean_run(envelope(requests),'mutations');assert result.returncode==0
    assert all(a!=b for a,b in zip(json.loads(result.stdout),wrong))
    assert all(a!=b for a,b in zip(bend_run(requests,'Mutations'),wrong))
    refusals=0
    for key,value in [('advertisedOptional',1),('advertisedInline',True),('advertisedName','other')]:
        row=copy.deepcopy(native[0]);row[key]=value
        try:project(row)
        except AssertionError:refusals+=1
        else:raise AssertionError('Unselected observation admitted')
    row=copy.deepcopy(native[1]);row['value']=True
    try:project(row)
    except AssertionError:refusals+=1
    else:raise AssertionError('Boolean is not a measured integer')
    basis=[HERE/n for n in ['SchemaRecord.lean','SchemaRecord.bend','SchemaRecordCase.lean','schema_record_conformance.py','polytone-contracts.json','polytone-managers.json']]
    basis += [p for p in capture.iterdir() if p.is_file()]
    report=dict(schema=1,status='passed-original-bundled-builder-selected-one-field-callers',comparisons=len(rows),
        leanLaws=18,bendLaws=12,decoderRefusals=len(negatives),observationAdapterRefusals=refusals,
        changedObservationControls=len(variants),basisSha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(basis)},
        limits=receipt['limits']+['Only the displayed selected fields are compared; diagnostic wording is retained but not predicted.',
            'The replay performs no native application, JVM, browser, or library negotiation.'])
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','comparisons','decoderRefusals','observationAdapterRefusals','changedObservationControls']}))


if __name__=='__main__':main()
