#!/usr/bin/env python3
"""Replay retained sync observations with Lean/Bend; no Qt/native launch."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unicodedata

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'applications/restic'))
from locks_probe import redact
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('excluded',type=Path)
    a=p.parse_args();capture=a.capture.resolve();excluded=a.excluded.resolve()
    assert capture.is_relative_to(ROOT/'applications/evidence') and excluded.is_relative_to(ROOT/'applications/evidence')
    receipt=json.loads((capture/'receipt.json').read_text());assert receipt['cases']==15 and receipt['commands']==16 and receipt['allOwnedProcessesRetired']
    for name,key in [('probe.py','producerSha256'),('driver.cpp','driverSha256'),('helper.py','helperSha256')]:assert sha(capture/name)==receipt[key]
    assert sha(ROOT/'applications/restic/locks_probe.py')==receipt['helperSha256']
    assert sha(capture/'work/sync-oracle')==receipt['binarySha256']
    source=ROOT/receipt['sourcePath'];text=source.read_text();assert sha(source)==receipt['sourceSha256']
    selected=text[text.index(receipt['sourceSelection']['start']):]
    assert hashlib.sha256(selected.encode()).hexdigest()==receipt['sourceSelection']['sha256']==sha(capture/'work/selected_sync.cpp')
    assert sha(Path(receipt['compiler']['path']))==receipt['compiler']['sha256']
    sdk=Path(receipt['sdk']['path']);assert sha(sdk/'SDKSettings.json')==receipt['sdk']['settingsSha256'];assert sha(sdk/'usr/include/c++/v1/type_traits')==receipt['sdk']['typeTraitsSha256']
    environment=json.loads((capture/'environment.json').read_text())
    for identity in environment['frameworks'].values():assert sha(Path(identity['path']))==identity['sha256']
    assert 'Excluded compile failure' in json.loads((excluded/'disposition.json').read_text())['status']
    failed=json.loads((excluded/'commands.json').read_text());assert len(failed)==1 and failed[0]['outcome']==dict(exitCode=1,timedOut=False)
    assert not (excluded/'observations.json').exists()
    raw=capture/'work/private/observations.json'
    assert sha(raw)==receipt['rawObservationSha256'] and sha(capture/'observations.json')==receipt['publicObservationSha256']
    assert redact(raw.read_bytes())==(capture/'observations.json').read_bytes()
    models=[HERE/n for n in ['Overwrite.lean','OverwriteCase.lean','Overwrite.bend']]
    ledger=ROOT/'applications/sources/mo2-overwrite-selections.json'
    inputs=models+[ledger]+[p for p in capture.iterdir() if p.is_file() and p.name!='conformance.json']+[p for p in excluded.iterdir() if p.is_file()]
    basis={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    for row in json.loads(ledger.read_text())['sources']:assert sha(ROOT/row['cache'])==row['sha256']
    commands=json.loads((capture/'commands.json').read_text())
    for r in commands+failed:
        directory=capture if r in commands else excluded
        for stream in ['stdout','stderr']:
            x=r['streams'][stream];private=directory/x['rawPrivatePath'];public=directory/(r['case']+'.'+stream)
            assert sha(private)==x['rawSha256'] and sha(public)==x['publicSha256']
            assert redact(private.read_bytes())==public.read_bytes()
    assert all(r['outcome']==dict(exitCode=0,timedOut=False) for r in commands)
    observations=json.loads((capture/'observations.json').read_text())
    assert len(observations)==15
    payloads={hashlib.sha256(b'incoming\n').hexdigest():1,hashlib.sha256(b'old A\n').hexdigest():2,
              hashlib.sha256(b'old B\n').hexdigest():4,hashlib.sha256(b'incoming B\n').hexdigest():5}
    def normalized(image):
        out={}
        for key,value in image.items():
            key=unicodedata.normalize('NFC',key);assert key not in out;out[key]=value
        return out
    def backing(entry):
        if entry is None:return None
        if entry['kind']=='symlink':return 3
        assert entry['kind']=='file';return payloads[entry['sha256']]
    cases,expected=[],[]
    directory_facts=[]
    for row in observations:
        result=row['result'];assert result['qt']==receipt['qt']['pkgConfigVersion']=='6.12.0' and result['platformPlugin']=='offscreen'
        request=row['request'];before=normalized(row['before']);after=normalized(row['after'])
        assert json.loads((capture/(row['case']+'.stdout')).read_text())==result
        assert all(event['removed'] for event in result['interventions'])
        assert [e['relative'] for e in result['interventions']]==request['removeBeforeApply']
        before_apply=copy.deepcopy(before)
        for event in result['interventions']:
            key=unicodedata.normalize('NFC',event['relative']);assert key in before_apply;before_apply.pop(key)
        if 'canary.txt' in before:assert before['canary.txt']==after['canary.txt']
        for file in request['files']:
            rel=file['relative'];choice=next(c for c in result['choices'] if c['relative']==rel)
            for role in ['source','mods/A','mods/B']:
                assert result['beforeApply'][rel][role]==(role+'/'+rel in before_apply)
                assert result['afterApply'][rel][role]==(role+'/'+rel in after)
            metadata=rel.split('/')[-1]=='meta.ini'
            values=None if metadata else [-1]+([v for v in [file['primary'],*file['alternatives']] if v!=0] if file['entryPresent'] else [])
            assert choice['widgetPresent']==(values is not None)
            if values is not None:assert choice['options']==values and choice['default']==values[-1]
            selected=choice.get('selected')
            if selected is not None:assert selected==(file['choice'] if file['choice'] is not None else values[-1])
            origin={1:'A',2:'B'}.get(selected,'A')
            destination='mods/'+origin+'/'+rel
            relevant=[m for m in result['errors'] if m.endswith('/'+rel)]
            assert len(relevant)<=1
            failure='remove' if relevant and relevant[0].startswith('failed to remove ') else 'move' if relevant and relevant[0].startswith('failed to move ') else 'none'
            assert not relevant or failure!='none'
            active=selected not in [None,-1]
            remove_ok=active and failure!='remove'
            move_ok=remove_ok and failure!='move'
            src=backing(before_apply.get('source/'+rel));dst=backing(before_apply.get(destination))
            if move_ok:
                original=before_apply['source/'+rel]
                moved=after[destination]
                assert original['kind']==moved['kind'] and original['mode']==moved['mode']
                if original['kind']=='symlink':assert original['target']==moved['target']
                else:assert original['sha256']==moved['sha256'] and original['bytes']==moved['bytes']
            cases.append(dict(metadata=metadata,known=file['entryPresent'],primary=file['primary'],alternatives=file['alternatives'],
                choice=file['choice'],source=src,destination=dst,removeOk=remove_ok,moveOk=move_ok))
            expected.append(dict(case=row['case'],relative=rel,default=choice.get('default'),selected=selected,
                source=backing(after.get('source/'+rel)),destination=backing(after.get(destination)),failure=failure))
            # Unselected other mod backings are unchanged; symlink objects are
            # compared separately from the independently unchanged canary.
            other='mods/'+('B' if origin=='A' else 'A')+'/'+rel
            assert before_apply.get(other)==after.get(other)
        directory_facts.append(dict(case=row['case'],sourceDirectoryAfter='source' in after))
    assert len(cases)==16
    generated=HERE/'generated';generated.mkdir(exist_ok=True)
    data=dict(schema=1,cases=cases);path=generated/'overwrite.json';path.write_text(json.dumps(data,indent=2)+'\n')
    formal=generated/'overwrite-formal';artifact=formal/'applications/mo2/Overwrite.olean';artifact.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=str(formal),BEND_NO_TELEMETRY='1');lean=os.environ.get('LEAN','lean')
    compiled=subprocess.run([lean,'-DwarningAsError=true','-o',str(artifact),str(models[0])],cwd=ROOT,env=env,capture_output=True,text=True)
    assert compiled.returncode==0,compiled.stdout+compiled.stderr
    def lean_run(q):return subprocess.run([lean,'--run','applications/mo2/OverwriteCase.lean',str(q)],cwd=ROOT,env=env,capture_output=True,text=True)
    result=lean_run(path);assert result.returncode==0,result.stdout+result.stderr
    actual=json.loads(result.stdout);assert len(actual)==16
    proposed=[]
    for value,native in zip(actual,expected):
        default,selected,src,dst,failure,retained=value.split('/')
        assert default==('absent' if native['default'] is None else str(native['default']))
        assert selected==('absent' if native['selected'] is None else str(native['selected']))
        assert int(src)==(native['source'] or 0) and int(dst)==(native['destination'] or 0) and failure==native['failure']
        proposed.append(dict(case=native['case'],retainedPriorModel=int(retained),scope='Proposed verified prior-backing retention, not native data.'))
    def list_text(values):
        out='Nil{}'
        for v in reversed(values):out='Con{'+str(v)+'n,'+out+'}'
        return out
    bit=lambda x:'True{}' if x else 'False{}'
    nat=lambda n:str(n or 0)+'n'
    calls=[]
    for c in cases:
        requested=0 if c['choice'] is None else 3 if c['choice']==-1 else c['choice']
        calls.append('row('+','.join([bit(c['metadata']),bit(c['known']),str(c['primary'])+'n',list_text(c['alternatives']),
            str(requested)+'n',nat(c['source']),nat(c['destination']),bit(c['removeOk']),bit(c['moveOk'])])+') ++ "\\n"')
    runner=generated/'OverwriteCase.bend'
    runner.write_text('''import Base
import ../Overwrite.bend as C

def choice_name(+n: Nat) -> String:
  Bool.pick(String,Nat.is_eq(n,0n),"absent",Bool.pick(String,Nat.is_eq(n,3n),"-1",Nat.show(n)))

def files_text(f: C.Backings) -> String:
  match f:
    case C.Backings{source,destination}: Nat.show(source) ++ "/" ++ Nat.show(destination)

def row(metadata: Bool, known: Bool, primary: Nat, alternatives: List<&2, Nat>, requested: Nat, source: Nat, +destination: Nat, remove_ok: Bool, move_ok: Bool) -> String:
  +values = C.options(metadata,known,primary,alternatives)
  +choice = C.choose(values,requested)
  +out = C.apply(C.Backings{source,destination},choice,remove_ok,move_ok)
  choice_name(C.last_or_zero(values)) ++ "/" ++ choice_name(choice) ++ "/" ++ files_text(C.files(out)) ++ "/" ++ C.failure_name(out) ++ "/" ++ Nat.show(C.kept_prior(C.retain_if_move_error(out,destination)))

def main() -> IO(Unit):
  IO.write('''+' ++ '.join(calls)+')\n')
    result=subprocess.run([os.environ.get('BEND','bend'),str(runner)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.splitlines()==actual
    negatives=[dict(data,schema=2)]+[dict(data,cases=[dict(cases[0],**edit)]) for edit in [dict(primary=3),dict(choice=2),dict(source=0),dict(destination=None,removeOk=True),dict(source=None,moveOk=True),dict(removeOk=False,moveOk=True)]]
    for i,value in enumerate(negatives):
        q=generated/f'overwrite-negative-{i}.json';q.write_text(json.dumps(value));result=lean_run(q);assert result.returncode==2 and result.stderr
    assert all(sha(ROOT/name)==digest for name,digest in basis.items())
    report=dict(schema=1,nativeCases=15,fileTransitions=16,leanMatches=True,bendMatches=True,researchInputsRefused=len(negatives),
        adapterSha256=sha(Path(__file__)),basisSha256=basis,modelRows=actual,nativeTransitions=expected,proposedRetention=proposed,directoryFacts=directory_facts,
        limits=['Unchanged selected MO2 methods with real offscreen Qt6.12/macOS QFile. Not native MO2/Windows/USVFS or full origin-tree/UI behavior.',
            'Primitive remove/move witnesses are scoped source-branch interpretations cross-checked against filesystem effects, not a generic permission/rename simulator.',
            'Two pre-apply deletions are explicitly controlled harness events; original before images are not falsely attributed to the method alone.',
            'NFC matching is only a unique fixture path projection for macOS names; no general path equivalence or symlink security proof.',
            'Prior-backing retention is proposed and model-only; the current failure with absent destination stays in the native comparison.',
            'Current Qt dependency hashes are post-run readback; no whole supported-consumer dependency or reproducible-build qualification.'])
    (capture/'conformance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['basisSha256','modelRows','nativeTransitions','proposedRetention','directoryFacts']},indent=2))


if __name__=='__main__':main()
