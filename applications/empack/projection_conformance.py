#!/usr/bin/env python3
"""Compare retained actual core projection results; never compile or run empack."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ADAPTER = sha(Path(__file__))


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    receipt = json.loads((run / 'receipt.json').read_text()); commands = json.loads((run / 'commands.json').read_text())
    assert sha(run / 'probe.py') == receipt['producerSha256']
    assert sha(run / 'driver.rs') == receipt['driverSha256']
    assert sha(run / 'observed.stdout') == receipt['observedSha256']
    assert len(commands) == 3 and all(c['exitCode'] == 0 and not c['timedOut'] for c in commands)
    sources = ROOT / 'applications/sources/empack-projection-selections.json'
    inputs = [HERE / p for p in ['Projection.lean', 'Projection.bend', 'ProjectionCase.lean']]
    inputs += [Path(__file__), sources, *[run / p for p in ['receipt.json','commands.json','probe.py','driver.rs']]]
    for c in commands:
        for stream in ['stdout','stderr']:
            path = run / (c['label'] + '.' + stream);inputs.append(path);assert sha(path) == c[stream + 'Sha256']
    basis = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    assert basis[str(Path(__file__).relative_to(ROOT))] == ADAPTER
    repo = ROOT.parent / 'empack'; revision = receipt['revision']
    for path, digest in receipt['sourceSha256'].items():
        content = subprocess.check_output(['git','-C',str(repo),'show',revision + ':' + path])
        assert hashlib.sha256(content).hexdigest() == digest, path
    for source in json.loads(sources.read_text())['sources']:
        content = subprocess.check_output(['git','-C',str(repo),'show',revision + ':' + source['path']])
        assert hashlib.sha256(content).hexdigest() == source['sha256'], source['path']
    rows, expected, names = [], [], []
    choice_calls, choice_expected, complete_calls, complete_expected = [], [], [], []
    excluded = []
    policy_names = ['Preserve','Unresolved','Enable','Disable','Defaults','Unknown']
    bit = lambda b: 'True{}' if b else 'False{}'
    global_errors = {'select/duplicate','select/invalid-environment','select/conflicting-choice','select/unknown-choice','select/preserve-required'}
    for line in (run / 'observed.stdout').read_text().splitlines():
        name,target,policy,encoded,status,entries,precedence,choices = line.split('\t')
        target,policy = int(target),int(policy)
        specs = [dict(zip(['owner','layer','destination','client','server','representation','asset'],map(int,s.split(',')),strict=True)) for s in encoded.split(';') if s]
        assert len({(s['owner'],s['destination'])for s in specs}) == len(specs), 'Source lookup would be ambiguous in this fixture.'
        row = dict(target=target,policy=policy,inputs=specs);rows.append(row);names.append(name)
        result = dict(status=status,entries=sorted(entries.split(';')) if entries else [],precedence=sorted(precedence.split(';')) if precedence else [],choices=choices.split(';') if choices else [])
        expected.append(result)
        selected = []
        for entry in result['entries']:
            owner,layer,path,client,server,representation,asset = entry.split(':')
            assert path in ['config/p0.cfg','config/p1.cfg']
            selected.append(dict(owner=int(owner[1:]),destination=int(path[8]),client=int(client),server=int(server),representation=int(representation),asset=int(asset)))
        full = target in [0,1,5]
        for entry in selected:
            source = next(s for s in specs if s['owner']==entry['owner'] and s['destination']==entry['destination'])
            kind = source['representation']
            representation = 'P.Embedded{}' if kind==0 else 'P.Unacquired{}' if kind==1 else 'P.Download{' + bit(kind!=3) + ',' + bit(kind!=4) + '}'
            complete_calls.append('P.complete(' + representation + ',' + bit(full) + ') ++ "\\n"')
            if status.startswith('finish/'):
                assert len(selected)==1, 'Multiple independent failure gates need additional observed ordering.'
                complete_expected.append(status.removeprefix('finish/'))
            else:
                assert status=='ok';complete_expected.append('ok')
        if target in [3,4,5,6]:
            excluded.append({'case':name,'scope':'Preserved-layer/global recipe behavior is compared by Lean, not this Bend choice projection.'})
            continue
        if status in global_errors:
            assert not selected
            excluded.append({'case':name,'scope':'Native result is a global admission failure; Bend does not reimplement that validator.'})
            continue
        side = 'server' if target==1 else 'client'; side_layer=3 if side=='server' else 2
        for destination in sorted({s['destination'] for s in specs}):
            candidates = sorted([s for s in specs if s['destination']==destination and s['layer'] in [0,1,side_layer]],key=lambda s:s['layer'],reverse=True)
            nodes=[]
            for s in candidates:
                req=s[side]; requirement='P.Unsupported{}' if req==0 else 'P.Required{}' if req==1 else 'P.Optional{' + bit(req==3) + '}'
                nodes.append('P.Candidate{' + str(s['owner']) + 'n,' + requirement + '}')
            choice_calls.append('P.label(P.choose([' + ','.join(nodes) + '],P.' + policy_names[policy] + '{},' + bit(full) + ')) ++ "\\n"')
            if status.startswith('select/'):
                assert len({s['destination']for s in specs})==1
                assert status in ['select/overlay-needs-choice','select/choice-required']
                choice_expected.append('error/' + status.removeprefix('select/'))
            else:
                chosen=[e for e in selected if e['destination']==destination]
                assert len(chosen)<=1
                choice_expected.append('none' if not chosen else 's'+str(chosen[0]['owner'])+':'+str(chosen[0][side]))
    assert len(rows)==len(set(names))==receipt['cases']==32
    generated=HERE/'generated';generated.mkdir(exist_ok=True);path=generated/'projection.json'
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    env=dict(os.environ,LEAN_PATH=os.pathsep.join(str(ROOT/p)for p in ['.build/formal','.build']),BEND_NO_TELEMETRY='1')
    def replay(value):
        path.write_text(json.dumps(value)+'\n')
        return subprocess.run([lean,'--run','applications/empack/ProjectionCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True)
    result=replay({'schema':1,'cases':rows});assert result.returncode==0,result.stdout+result.stderr
    actual=json.loads(result.stdout)
    assert actual==expected, [(name,a,e)for name,a,e in zip(names,actual,expected,strict=True)if a!=e]
    runner=generated/'ProjectionCase.bend'
    runner.write_text('import Base\nimport ../Projection.bend as P\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(choice_calls+complete_calls)+')\n')
    result=subprocess.run([bend,str(runner)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.splitlines()==choice_expected+complete_expected
    invalids=[('schema',{'schema':2,'cases':rows},'Unsupported projection schema'),
        ('recipe',{'schema':1,'cases':[dict(rows[0],target=99)]},'Unknown recipe profile'),
        ('policy',{'schema':1,'cases':[dict(rows[0],policy=99)]},'Unknown choice policy')]
    for field,value,message in [('layer',9,'Unknown layer code'),('client',9,'Unknown requirement code'),('representation',9,'Unknown representation code'),('destination',2,'outside the captured profile')]:
        invalids.append((field,{'schema':1,'cases':[dict(rows[0],inputs=[dict(rows[0]['inputs'][0],**{field:value})])]},message))
    refused=[]
    for label,value,diagnostic in invalids:
        result=replay(value);assert result.returncode==2 and diagnostic in result.stderr;refused.append(label)
    path.write_text(json.dumps({'schema':1,'cases':rows},indent=2)+'\n')
    assert all(sha(ROOT/p)==h for p,h in basis.items()), 'Inputs changed while replay was active.'
    by_name=dict(zip(names,expected,strict=True))
    assert by_name['four-layers-client']==by_name['reversed-client']
    assert len(by_name['same-bytes-distinct-placements']['entries'])==2
    report={'schema':1,'adapterSha256':ADAPTER,'basisSha256':basis,'actualCoreCases':32,'leanCasesMatch':True,
        'bendFlatDestinationChoices':len(choice_calls),'bendRepresentationGates':len(complete_calls),'bendProjectionMatches':True,'bendExcludedScopes':excluded,
        'refusedResearchInputs':refused,'rejectedInterpretations':['Map insertion order determines the selected layer.','Disabled optional override deletes its lower fallback.',
            'A shadowed unresolved optional always needs an answer.','Every consumer flattens to one layer.','Identical bytes mean one placement.',
            'Successful selection means every selected representation is complete.','Synthetic core values authenticate actual file bytes or authorize publication.'],
        'limits':['One fixed choice key/description and synthetic content labels. Download cases have no independent digest assertions; not general key maps,digest-bearing references,actual byte verification,path parsing or provider/codec evidence.',
            'Lean compares complete controlled selection/finish outcomes,selected entry membership,precedence and choice provenance. Bend compares local layer choice/representation gates after native admission,not global validation or retained-layer recipes.',
            'Entry and precedence membership is normalized for comparison; output presentation order is not qualified.',
            'Actual standalone core source/build is separate from installed0.8.8 CLI,full engine,native filesystem,browser,WASM or real consumer execution.',
            'Initial063406 driver compile failure is preserved separately and contributes no API cases.']}
    (run/'conformance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items()if k not in ['basisSha256','bendExcludedScopes']},indent=2))


if __name__=='__main__':main()
