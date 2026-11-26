"""Compare retained real adoption calls; no engine/application/native collection."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import shutil
import importlib.util
from observations import ROOT,BASE,EXTRA,read,packets

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,indent=2)+'\n')


def evidence(private=True):
    setup=read(BASE/'setup.json');available=[];excluded=[]
    for capture in [BASE,EXTRA]:
        receipt=read(capture/'receipt.json');assert receipt['complete']and receipt['allGroupsAbsent']
        assert sha(capture/'probe.py')==receipt['producerSha256']
        if capture==EXTRA:assert sha(capture/'setup.json')==receipt['setupSha256']
    for p,h in [(Path(setup['binary']),setup['binarySha256']),(ROOT/setup['snapshotHelper'],setup['snapshotHelperSha256'])]:
        if private and p.exists():assert sha(p)==h;available.append(str(p))
        else:excluded.append(str(p))
    ledger=read(ROOT/'applications/sources/empack-adoption-flow-selections.json')
    assert all(any(r['path']==v['path']and r['sha256']==v['sha256']and r['gitBlob']==v['gitBlob']for r in ledger['sources'])for v in setup['sourceIdentities'])
    for row in ledger['sources']:
        if private and(ROOT.parent/'empack/.git').exists():
            raw=subprocess.check_output(['git','-C',str(ROOT.parent/'empack'),'show',row['revision']+':'+row['path']]);assert hashlib.sha256(raw).hexdigest()==row['sha256']and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['gitBlob'];available.append(row['path'])
        else:excluded.append(row['path'])
    if private:
        helper=ROOT/setup['snapshotHelper'];spec=importlib.util.spec_from_file_location('retained_snapshot_only',helper)
        prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
        final={c['project']:c['after']for c in read(BASE/'commands.json')}
        final['local']=read(EXTRA/'commands.json')[-1]['after']
        for project,scopes in final.items():
            for name,expected in scopes.items():
                path=Path(setup['work'])/('projects'if name=='project'else name)/project
                if path.exists():
                    actual=prior.image(path)
                    for rel,value in actual.items():
                        if value['kind']=='file'and rel.startswith(('pack/','vendor/')):
                            s=(path/rel).stat();value.update(inode=s.st_ino,device=s.st_dev,ctimeNs=s.st_ctime_ns)
                    assert actual==expected;available.append(str(path))
                else:excluded.append(str(path))
    else:excluded.append('Current private project/state/cache images for all three fixtures')
    return dict(available=available,excluded=excluded)


def main():
    proof=read(BASE/'proof-gate.json');assert proof['exitCode']==0
    for name,digest in proof['sourceSha256'].items():assert sha(ROOT/name)==digest
    identities=evidence(os.environ.get('ADOPTION_PRIVATE','1')!='0');inputs,expected,effects=packets()
    write(BASE/'model-input.json',inputs);write(BASE/'observed-model-values.json',expected);write(BASE/'scope-effects.json',effects)
    formal=ROOT/'.build/adoption-flow-replay';formal.mkdir(parents=True,exist_ok=True)
    env={**os.environ,'LEAN_PATH':os.environ.get('ADOPTION_FORMAL',str(ROOT/'.build/formal')),'BEND_NO_TELEMETRY':'1'}
    lean,bend=os.environ['LEAN'],os.environ['BEND'];command=[lean,'--run','applications/empack/adoption-flow/AdoptionCase.lean']
    r=subprocess.run(command+[str(BASE/'model-input.json')],cwd=ROOT,env=env,text=True,capture_output=True,check=True);actual=json.loads(r.stdout)
    comparable=copy.deepcopy(actual)
    for v,native in zip(comparable,expected,strict=True):
        if native['candidate']is None:v['candidate']=None
    assert comparable==expected,'Adoption model differs from retained native calls.'
    bo=lambda b:'True{}'if b else'False{}';calls=[];wanted=[]
    for row,v in zip(inputs['cases'],expected,strict=True):
        reason='P.reason('+','.join([bo(row[n])for n in ['firstLock','allRoots','repeated','localSource']]+[str(row[n])+'n'for n in ['sourceBytes','installedBytes']])+')'
        args=','.join([bo(row['preview']),reason,str(row['acceptedBefore'])+'n',str(row['installedBytes'])+'n'])
        calls+=['Nat.show('+reason+')','Nat.show(P.accepted('+args+'))','Bool.show(P.changed('+args+'))']
        wanted += [str(v['reason']),str(v['acceptedAfter']),str(v['documentsChanged'])]
        if v['candidate']is not None:
            calls.append('Nat.show(P.candidate('+reason+','+str(row['installedBytes'])+'n))');wanted.append(str(v['candidate']))
    p=formal/'Replay.bend';p.write_text('import ../../applications/empack/adoption-flow/Adoption.bend as P\nimport Base\ndef main() -> IO(Unit):\n  IO.write('+' ++ "\\n" ++ '.join(calls)+' ++ "\\n")\n')
    r=subprocess.run([bend,str(p)],cwd=ROOT,env=env,text=True,capture_output=True,check=True);assert r.stdout.splitlines()==wanted
    controls=[]
    for label,case,field,value in [('preview-as-save','url-first-preview','documentsChanged',True),('failed-local-admitted','local-mismatch-refusal','reason',0),('old-observation-retained','url-changed-apply','acceptedAfter',1),('changed-local-blocked','matching-new-local-apply','reason',4)]:
        changed=copy.deepcopy(expected);next(r for r in changed if r['id']==case)[field]=value;assert changed!=comparable;controls.append(label)
    for label,change in [('schema',lambda d:d.update(schema=2)),('payload',lambda d:d['cases'][0].update(installedBytes=3)),('first-lock-observation',lambda d:d['cases'][0].update(acceptedBefore=1)),('local-without-source',lambda d:d['cases'][7].update(sourceBytes=0)),('url-with-local-source',lambda d:d['cases'][2].update(sourceBytes=1))]:
        changed=copy.deepcopy(inputs);change(changed);p=formal/(label+'.json');write(p,changed)
        r=subprocess.run(command+[str(p)],cwd=ROOT,env=env,text=True,capture_output=True);assert r.returncode==2 and 'observed-file adoption'in r.stderr;controls.append(label)
    for label,case,field,value in [('preview-to-apply','url-first-preview','preview',False),('changed-source-to-mismatch','matching-new-local-apply','sourceBytes',1),('missing-installed-to-present','local-missing-refusal','installedBytes',1)]:
        changed=copy.deepcopy(inputs);next(r for r in changed['cases']if r['id']==case)[field]=value;p=formal/(label+'.json');write(p,changed)
        r=subprocess.run(command+[str(p)],cwd=ROOT,env=env,text=True,capture_output=True,check=True);assert json.loads(r.stdout)!=actual;controls.append(label)
    for label in ['published-hash','payload-rewritten','broken-continuation','wrong-stream']:
        with tempfile.TemporaryDirectory(prefix='raw-',dir=formal)as d:
            base,extra=Path(d)/'base',Path(d)/'extra';shutil.copytree(BASE,base);shutil.copytree(EXTRA,extra)
            if label=='broken-continuation':
                p=extra/'setup.json';j=read(p);j['baseReceiptSha256']='0'*64;write(p,j)
            elif label=='wrong-stream':
                p=base/'url-first-apply.stdout';p.write_bytes(p.read_bytes()+b'changed')
            else:
                p=base/'commands.json';j=read(p);c=next(c for c in j if c['id']=='url-first-apply')
                if label=='payload-rewritten':c['after']['project']['pack/resourcepacks/observed.zip']['inode']+=1
                else:
                    x=c['after']['project']['empack.lock'];raw=bytes.fromhex(x['bytesHex']).replace(read(BASE/'setup.json')['payloads']['A'].encode(),read(BASE/'setup.json')['payloads']['B'].encode());x.update(bytesHex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest(),sha512=hashlib.sha512(raw).hexdigest(),bytes=len(raw))
                write(p,j)
            try:packets(base,extra)
            except AssertionError:controls.append(label)
            else:raise AssertionError('Changed raw adoption observation escaped: '+label)
    report=dict(schema=1,nativeCommands=13,leanLaws=12,bendLaws=9,bendScalarComparisons=len(calls),controls=controls,scopeEffects=effects,evidence=identities,
                unreportedCandidates=[v['id']for v in expected if v['candidate']is None],limits=['Two no-change previews print no candidate digest; candidate model values are explicitly excluded for those observations, not inferred from silence.','Three owned projects,ordinary URL/local resource-pack files,explicit placements,no independent digest/provider selections.','URL origins reserved example.invalid;no general network-interception/absence proof.','Preview/refusal unchanged across project/state/cache;successful calls publish lock only and create own durable records. No whole-host read-only claim.','No no-op apply,provider/file-role identification,concurrent edits,stale approval,symlinks,crash recovery,consumer export,or game tested.','Formal transition models this admitted profile; payload non-write laws do not prove the production implementation. Native inode/time/hash snapshots supply bounded non-write observations.'])
    write(BASE/'conformance.json',report)
    files=[p for d in [BASE,EXTRA]for p in d.rglob('*')if p.is_file()and p.name not in ['basis.json','conformance.json']]
    files += [p for p in HERE.iterdir()if p.is_file()and p.suffix in ['.py','.lean','.bend']]
    files.append(ROOT/'applications/sources/empack-adoption-flow-selections.json')
    write(BASE/'basis.json',{str(p.relative_to(ROOT)):sha(p)for p in files})
    print(json.dumps({k:v for k,v in report.items()if k not in ['evidence','scopeEffects']},indent=2))


if __name__=='__main__':main()
