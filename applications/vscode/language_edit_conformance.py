"""Pure language-edit replay; no editor, provider, GUI, or native-child launch."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import language_edit_observations as observations

ROOT,HERE,CAP = observations.ROOT,observations.HERE,observations.CAP
FORMAL = ROOT/'.build/vscode-language-formal'
write = lambda p,v: p.write_text(json.dumps(v,indent=2)+'\n')


def main():
    assert sys.argv[1:] in [[],['--public-only']]
    inputs,measured,details,basis,excluded = observations.evidence(not sys.argv[1:])
    FORMAL.mkdir(parents=True,exist_ok=True)
    write(CAP/'model-input.json',inputs);write(CAP/'measured.json',measured);write(CAP/'details.json',details)
    lean,bend = os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    env = dict(os.environ,LEAN_PATH=str(FORMAL),BEND_NO_TELEMETRY='1')
    for name in ['WorkspaceSearch','LanguageEdit']:
        target = FORMAL/f'applications/vscode/{name}.olean';target.parent.mkdir(parents=True,exist_ok=True)
        q = subprocess.run([lean,'-DwarningAsError=true','-o',str(target),str(HERE/f'{name}.lean')],cwd=ROOT,env=env,capture_output=True,text=True)
        assert q.returncode == 0,q.stdout+q.stderr
    command = [lean,'--run',str(HERE/'LanguageEditCase.lean')]
    path = FORMAL/'input.json'
    def replay(value):
        write(path,value)
        return subprocess.run(command+[str(path)],cwd=ROOT,env=env,capture_output=True,text=True)
    q = replay(inputs);assert q.returncode == 0,q.stdout+q.stderr
    # Lean encodes the nested product as [response,[text,[changes,canceled]]].
    def flatten(v):return [v[0],v[1][0],v[1][1][0],v[1][1][1]]
    actual = [flatten(v) for v in json.loads(q.stdout)]
    assert actual == measured,(actual,measured)
    modes = ['workspace','guarded','editor-pair','format-compute','format-apply','format-command','rename-compute','rename-apply']
    boolean = lambda v:'True{}' if v else 'False{}'
    def request(r):
        return 'L.Request{' + ','.join([str(modes.index(r['mode']))+'n',str(r['basis'])+'n',str(r['secondBasis'])+'n',boolean(r['intervened']),boolean(r['secondEmpty'])]) + '}'
    calls = ['L.render(L.run('+request(r)+'))' for r in inputs['cases']]
    driver = HERE/'_language_edit_replay.bend'
    driver.write_text('import Base\nimport LanguageEdit.bend as L\ndef main() -> IO(Unit):\n  IO.write('+' ++ "\\n--CASE--\\n" ++ '.join(calls)+')\n')
    try:q = subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True)
    finally:driver.unlink()
    assert q.returncode == 0,q.stdout+q.stderr
    expected = '\n--CASE--\n'.join(f'{v[0]}|{v[2]}|{str(v[3]).lower()}|{v[1]}' for v in measured)
    assert q.stdout == expected,(q.stdout,expected)
    controls = []
    for name,mutate in [
        ('schema',lambda x:x.update(schema=2)),('profile',lambda x:x.update(profile='full-vscode')),
        ('empty',lambda x:x.update(cases=[])),('count',lambda x:x.update(cases=x['cases']*2)),
        ('mode',lambda x:x['cases'][0].update(mode='completion')),
        ('unknown-version',lambda x:x['cases'][0].update(basis=0)),
        ('second-outside-editor',lambda x:x['cases'][0].update(secondEmpty=True)),
        ('unobserved-editor-schedule',lambda x:x['cases'][3].update(secondBasis=60)),
        ('wrong-type',lambda x:x['cases'][0].update(intervened='true'))]:
        bad = copy.deepcopy(inputs);mutate(bad);p = replay(bad)
        assert p.returncode == 2 and not p.stdout,(name,p.stdout,p.stderr)
        controls.append(dict(kind='DTO',name=name,refused=True))
    # Independent raw outputs are projected again; these do not compare a
    # mutated expectation with itself or rerun the native program.
    raw,meta = observations.load(CAP/'observed.json'),observations.load(CAP/'meta.json')
    for name,mutate in [
        ('api-acceptance',lambda x:x['rows'][0]['result'].update(applied=False)),
        ('parallel-second',lambda x:x['rows'][3]['result']['results'].__setitem__(1,True)),
        ('buffer-result',lambda x:x['rows'][-1]['after'].update(text='REN beta\n')),
        ('version-effect',lambda x:x['rows'][-1]['after'].update(version=21)),
        ('computed-payload',lambda x:x['rows'][6]['result']['returned']['edits'][0].update(newText='BAD')),
        ('provider-cancellation',lambda x:next(e for e in x['events'] if e.get('action')=='interactive-format-late' and e['kind']=='format').update(canceledAtReturn=False))]:
        bad = copy.deepcopy(raw);mutate(bad)
        try:_,changed,_ = observations.observe(bad,meta);refused = changed != actual
        except AssertionError:refused = True
        assert refused,name
        controls.append(dict(kind='changed-raw-observation',name=name,refused=True))
    for name,index,mutate in [
        ('make-parallel-sequential',3,lambda r:r.update(secondBasis=r['basis']+1)),
        ('remove-late-workspace-change',1,lambda r:r.update(intervened=False)),
        ('remove-format-cancellation',8,lambda r:r.update(intervened=False))]:
        bad = copy.deepcopy(inputs);mutate(bad['cases'][index]);p = replay(bad)
        assert p.returncode == 0 and [flatten(v) for v in json.loads(p.stdout)] != actual,(name,p.stderr)
        controls.append(dict(kind='changed-premise',name=name,refused=True))
    write(CAP/'basis.json',basis);write(CAP/'controls.json',controls)
    write(CAP/'conformance.json',dict(schema=1,apiRows=11,generatedCallerPolicyRows=1,
        comparedFieldsPerRow=['API response','buffer text','version change','provider cancellation'],matched=True,
        controls=len(controls),basisFiles=len(basis),privateExcluded=excluded,
        tools={n:dict(path=str(Path(p).resolve()),sha256=observations.sha(Path(p))) for n,p in [('lean',lean),('bend',bend)]},
        limits=['One ASCII file/custom providers on desktop1.148;no general language engine or interactive rename widget.',
                'Bridge submission version comes from inspected source and immediate API snapshot,not captured RPC.',
                'Minimal edit shape observed independently;model checks equivalent effect,not diff algorithm.',
                'Only normal-format content/position change case observed;no isolated cause or general timing proof.',
                'Caller guard is authored policy;no atomic compare-and-apply extension API is introduced.',
                'Edit success/no-op/provider result is not save,semantic correctness,or durability.',
                'Closure is original-group/exact-work-argv scope,not arbitrary detached-process census.',
                'Historical1.147 pins/evidence unchanged;shared host stores not fully measured.']))
    print(json.dumps(dict(apiRows=11,matched=True,controls=len(controls),basisFiles=len(basis),privateExcluded=len(excluded))))


if __name__ == '__main__':main()
