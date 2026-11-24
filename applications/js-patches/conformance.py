#!/usr/bin/env python3
"""Pure model comparison with frozen patch traces; does not rerun package managers."""
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import verify_observations as retained

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
BASE='module.exports = "base";\n';PATCHED='module.exports = "patched";\n'


def main():
    with contextlib.redirect_stdout(io.StringIO()) as checked:retained.main()
    observations=json.loads(checked.getvalue())
    captures=[ROOT/'applications/evidence'/name for name in retained.NAMES[1:]]
    models=[HERE/name for name in ['Patches.lean','PatchesCase.lean','Patches.bend']]
    basis_inputs=models+[ROOT/'applications/sources/js-patches-selections.json',HERE/'verify_observations.py']
    for capture in [ROOT/'applications/evidence'/retained.NAMES[0],*captures]:
        basis_inputs.extend(p for p in capture.rglob('*') if p.is_file() and 'work' not in p.relative_to(capture).parts)
    basis={str(p.relative_to(ROOT)):sha(p) for p in basis_inputs}
    sources=json.loads((ROOT/'applications/sources/js-patches-selections.json').read_text())
    source_basis={row['cache']:sha(ROOT/row['cache']) for row in sources}
    cases=[];expected=[];labels=[]
    # Exact authored patch identities are derived from captured input files,
    # not from the observed exit status or payload.
    patch_tags={}
    for capture in captures:
        for p in (capture/'files').glob('*.txt'):
            raw=p.read_bytes()
            if raw.startswith(b'diff --git a/index.js b/index.js\n'):
                assert raw.count(b'@@')==2 and b'+module.exports = "patched";' in raw
                tag=1 if b'-module.exports = "base";' in raw else 2
                assert tag==1 or b'-module.exports = "absent-context";' in raw
                patch_tags[hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()]=tag
    assert sorted(patch_tags.values())==[1,2]

    def decode_image(capture,app,frame):
        files=frame['files'];manifest=json.loads((capture/files['package.json']['captured']).read_text())
        assert set(manifest['dependencies'])=={'fixture-patch'}
        spec=manifest['dependencies']['fixture-patch'];patches=[v for name,v in files.items() if name.endswith('.patch')]
        assert len(patches)<=1
        if app=='pnpm':
            assert spec.startswith('file:') and spec.endswith('/fixture-patch-1.0.0.tgz')
            workspace=(capture/files['pnpm-workspace.yaml']['captured']).read_text() if 'pnpm-workspace.yaml' in files else ''
            bindings=re.findall(r'(?m)^  fixture-patch: (patches/fixture-patch\.patch)$',workspace)
            assert len(bindings)<=1
            active=bool(bindings)
        else:
            active=spec.startswith('patch:')
            assert active or spec.startswith('file:')
        recipe=0
        if active:
            assert len(patches)==1
            raw=(capture/patches[0]['captured']).read_bytes();recipe=patch_tags[hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()]
        lockname='pnpm-lock.yaml' if app=='pnpm' else 'yarn.lock';lock=0
        if lockname in files:
            text=(capture/files[lockname]['captured']).read_text()
            if app=='pnpm':
                hashes=re.findall(r'(?m)^  fixture-patch: ([a-f0-9]{64})$',text)
                assert len(hashes)<=1
                if hashes:
                    assert 'patchedDependencies:\n  fixture-patch: '+hashes[0] in text
                    assert '(patch_hash='+hashes[0]+')' in text
                    lock=patch_tags[hashes[0]]+1
                else:
                    assert '(patch_hash=' not in text;lock=1
            else:
                locators=re.findall(r'(?m)^  resolution: "(fixture-patch@patch:[^\n]+)"$',text)
                assert len(locators)<=1
                if locators:
                    assert re.search(r'&hash=[a-f0-9]{6}(?:&|$)',locators[0])
                    # Only the known valid derived locator was published in
                    # these traces. This is not an implementation of its hash.
                    lock=2
                else:lock=1
        payload=0;live=0
        if frame['installed']:
            installed=frame['installed'];assert installed['content'] in [BASE,PATCHED]
            payload=1 if installed['content']==BASE else 2
            if app=='yarn':
                assert installed['path'].endswith('/yarn/project/node_modules/fixture-patch/index.js');live=1
            elif 'patch_hash=' in installed['path']:
                encoded=re.search(r'patch_hash=([a-f0-9]+)_',installed['path']);assert encoded and len(encoded[1])>=20
                matching=[tag for identity,tag in patch_tags.items() if identity.startswith(encoded[1])]
                assert len(matching)==1;live=matching[0]+1
            else:live=1
        return dict(recipe=recipe,lock=lock,live=live,payload=payload,patchFile=bool(patches))

    for capture in captures:
        rows=json.loads((capture/'trace.json').read_text());prepared={(r['app'],r['case']):r for r in json.loads((capture/'prepared.json').read_text())} if (capture/'prepared.json').exists() else {}
        for row in rows:
            app=row['app'];argv=row['argv'];label=row['case'];before=decode_image(capture,app,row['observed']['before']);after=decode_image(capture,app,row['observed']['after'])
            c=dict(profile=app,image=before,action='observe',importExisting=False,frozen=False,force=False,keyMatches=False,draft=0)
            if not label.endswith('-runtime'):
                prefix=1 if app=='pnpm' else 2;verb=argv[prefix]
                if verb=='install':c.update(action='install',frozen=('--frozen-lockfile' in argv or '--immutable' in argv),force='--force' in argv)
                elif verb=='patch':c.update(action='prepare',importExisting=('--ignore-existing' not in argv if app=='pnpm' else '--update' in argv))
                elif verb=='patch-commit':c.update(action='commit',draft=2)
                elif verb=='patch-remove':
                    assert argv[prefix+1] in ['fixture-patch','fixture-patch@1.0.0'];c.update(action='remove',keyMatches=argv[prefix+1]=='fixture-patch')
                elif verb=='unplug':c['action']='unplug'
                else:raise AssertionError((label,argv))
            extraction=0
            if c['action']=='prepare':
                p=prepared[(app,label)];assert p['content'] in [BASE,PATCHED]
                extraction=1 if p['content']==BASE else 2
            cases.append(c);expected.append(dict(status=row['outcome']['exitCode'],image=after,prepared=extraction));labels.append(capture.name+'/'+app+'/'+label)
    assert len(cases)==77 and sum(c['action']=='prepare' for c in cases)==10
    generated=HERE/'generated';generated.mkdir(exist_ok=True);formal=generated/'formal';artifact=formal/'applications/js-patches/Patches.olean';artifact.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=str(formal),BEND_NO_TELEMETRY='1');lean=os.environ.get('LEAN','lean')
    compiled=subprocess.run([lean,'-DwarningAsError=true','-o',str(artifact),str(models[0])],cwd=ROOT,env=env,capture_output=True,text=True);assert compiled.returncode==0,compiled.stdout+compiled.stderr
    data=dict(schema=1,cases=cases);path=generated/'cases.json';path.write_text(json.dumps(data,indent=2)+'\n')
    def run(q):return subprocess.run([lean,'--run','applications/js-patches/PatchesCase.lean',str(q)],cwd=ROOT,env=env,capture_output=True,text=True)
    result=run(path);assert result.returncode==0,result.stdout+result.stderr
    actual=json.loads(result.stdout)
    mismatches=[(labels[i],x,y) for i,(x,y) in enumerate(zip(actual['current'],expected)) if x!=y]
    assert len(actual['current'])==77 and not mismatches,mismatches
    def render(r):
        s=r['image'];return '/'.join(str(v) for v in [r['status'],s['recipe'],s['lock'],s['live'],s['payload'],int(s['patchFile']),r['prepared']])
    def bit(b):return 'True{}' if b else 'False{}'
    calls=[]
    for c in cases:
        s=c['image'];image='C.PatchImage{'+','.join([*(str(s[k])+'n' for k in ['recipe','lock','live','payload']),bit(s['patchFile'])])+'}'
        action={'observe':'C.Observe{}','prepare':'C.Prepare{'+bit(c['importExisting'])+'}','commit':'C.Commit{}','install':'C.Install{'+bit(c['frozen'])+','+bit(c['force'])+'}','remove':'C.Remove{'+bit(c['keyMatches'])+'}','unplug':'C.Unplug{}'}[c['action']]
        p='C.Pnpm{}' if c['profile']=='pnpm' else 'C.Yarn{}';calls.append('pair('+p+','+image+','+action+') ++ "\\n"')
    runner=generated/'Cases.bend';runner.write_text('''import Base
import ../Patches.bend as C
def flag(b: Bool) -> String:
  match b:
    case True{}: "1"
    case False{}: "0"
def show_image(s: C.PatchImage) -> String:
  match s:
    case C.PatchImage{r,k,l,b,f}: Nat.show(r) ++ "/" ++ Nat.show(k) ++ "/" ++ Nat.show(l) ++ "/" ++ Nat.show(b) ++ "/" ++ flag(f)
def render(r: C.PatchOutcome) -> String:
  match r:
    case C.PatchOutcome{status,image,prepared}: Nat.show(status) ++ "/" ++ show_image(image) ++ "/" ++ Nat.show(prepared)
def pair(+p: C.PatchProfile,+s: C.PatchImage,+a: C.PatchAction) -> String:
  render(C.run(p,s,a,False{})) ++ "|" ++ render(C.run(p,s,a,True{}))
def main() -> IO(Unit):
  IO.write('''+' ++ '.join(calls)+')\n')
    result=subprocess.run([os.environ.get('BEND','bend'),str(runner)],cwd=ROOT,env=env,capture_output=True,text=True);assert result.returncode==0,result.stdout+result.stderr
    pairs=[line.split('|') for line in result.stdout.splitlines()]
    assert [v[0] for v in pairs]==list(map(render,actual['current'])) and [v[1] for v in pairs]==list(map(render,actual['proposed']))
    negatives=[dict(data,schema=2)]
    for change in [dict(profile='classic'),dict(action='patch-all'),dict(frozen=True,force=True),dict(action='commit',draft=0),dict(action='remove',profile='yarn')]:negatives.append(dict(data,cases=[dict(cases[0],**change)]))
    for change in [dict(recipe=3),dict(live=4),dict(payload=2),dict(recipe=1,patchFile=False)]:
        bad=copy.deepcopy(cases[0]);bad['image'].update(change);negatives.append(dict(data,cases=[bad]))
    for i,value in enumerate(negatives):
        q=generated/f'negative-{i}.json';q.write_text(json.dumps(value));result=run(q);assert result.returncode==2 and result.stderr
    assert all(sha(ROOT/p)==digest for p,digest in basis.items()) and all(sha(ROOT/p)==digest for p,digest in source_basis.items())
    changes=[labels[i] for i,(x,y) in enumerate(zip(actual['current'],actual['proposed'])) if x!=y]
    report=dict(schema=1,commands=77,preparedOutputs=10,leanCurrentMatches=True,bendCurrentMatches=True,proposedModelsAgree=True,
        researchInputsRefused=len(negatives),adapterSha256=sha(Path(__file__)),basisSha256=basis,sourceSha256=source_basis,
        verifiedObservations=observations,proposedDifferences=changes,
        limits=['Closed one-tarball/direct-root/text-hunk/node-modules profile;decoder identities are equality labels,not general codecs or integrity proofs.',
            'Current pnpm reuse condition is a projection of observed cases,not the complete source admission algorithm. Additional source/host premises remain unqualified.',
            'Yarn flat path does not identify patch content. Its published valid locator is classified opaquely;its effects-based hash algorithm is not reimplemented.',
            'Conservative proposed candidate policy is model-only;native staging,efficient admitted-backing reuse and publication need separate implementation/verification.'])
    (HERE/'comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['basisSha256','sourceSha256']},indent=2))


if __name__=='__main__':main()
