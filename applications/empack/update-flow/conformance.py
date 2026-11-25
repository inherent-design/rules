"""Replay retained CLI observations against finite models; no native collection or network."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from observations import ROOT, RUNS, OPERATIONS, load, sha, packets, author

PRIMARY = RUNS[0]
HERE = Path(__file__).resolve().parent
write = lambda p, x: p.write_text(json.dumps(x, indent=2) + '\n')
FORMAL = ROOT / '.build/empack-update-flow-formal'


def evidence(owner_local=True):
    unavailable = []
    rows = [load(run / 'commands.json') for run in RUNS]
    setups = [load(run / 'setup.json') for run in RUNS]
    metadata = load(PRIMARY / 'independent-metadata.json')
    expected_binary = setups[0]['binarySha256']
    assert expected_binary == '99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
    for index, run in enumerate(RUNS):
        receipt = load(run / 'receipt.json'); setup = setups[index]
        assert receipt['complete'] and receipt['commands'] == [10,5,2,3][index]
        assert receipt['allRecordedGroupsAbsent'] and receipt['setupSha256'] == sha(run / 'setup.json')
        assert setup['binarySha256'] == expected_binary
        producer = ['probe.py','materialize_probe.py','build_probe.py','instance_probe.py'][index]
        assert sha(run / producer) == setup['producerSha256'] == receipt['producerSha256']
        assert sha(run / 'probe.py') == setups[0]['producerSha256']
        if index:
            assert setup['helperSha256'] == receipt['helperSha256'] == setups[0]['producerSha256']
            assert setup['basisCapture'] == str(RUNS[index-1].relative_to(ROOT))
            if index < 3:
                assert setup['basisCommandsSha256'] == sha(RUNS[index-1] / 'commands.json')
                assert setup['basisReceiptSha256'] == sha(RUNS[index-1] / 'receipt.json')
                assert rows[index][0]['before'] == rows[index-1][-1]['after']
            else:
                assert setup['basisArtifactsSha256'] == sha(RUNS[2] / 'artifacts.json')
                assert rows[index][0]['before'] == setup['initialImage']
        for left, right in zip(rows[index], rows[index][1:]): assert left['after'] == right['before']
        for row in rows[index]:
            assert row['exitCode'] == 0 and row['groupAbsent'] and not row['timedOut']
            assert row['argv'][0] == setups[0]['binary']
            assert row['argv'][row['argv'].index('--state-dir')+1] == str(Path(setup['work']) / ('recipient-state' if index == 3 else 'state'))
            assert row['argv'][row['argv'].index('--cache-dir')+1] == str(Path(setup['work']) / 'cache')
            for name in ['stdout','stderr']:
                assert sha(run / (row['id'] + '.' + name)) == row['streams'][name]
            parsed = run / (row['id'] + '.json')
            if parsed.exists(): assert load(parsed) == json.loads((run / (row['id'] + '.stdout')).read_text())
            for image in [row['before'],row['after']]:
                for value in image.values():
                    if 'bytesHex' in value:
                        raw=bytes.fromhex(value['bytesHex'])
                        assert len(raw) == value['bytes'] and hashlib.sha256(raw).hexdigest() == value['sha256']
        # These are captured fixture-entry effects, not global/cache side effects.
        readonly = {'inspect-old','held-old','inspect-unpinned','automatic-preview','exact-preview',
                    'inspect-new','held-new','check-reference','check-local-materialized',
                    'check-online-materialized','inspect-materialized','ensure-repeat','check-recipient'}
        for row in rows[index]:
            if row['id'] in readonly: assert row['before'] == row['after']
    assert setups[0]['metadataSha256'] == sha(PRIMARY / 'independent-metadata.json')
    assert rows[0][0]['before']['empack.yml']['bytesHex'] == setups[0]['author'].encode().hex()
    assert author(rows[0][0]['before'], metadata) == [1,0,0]
    # Compare actual successful apply effects with the earlier preview, not an
    # assertion that a saved approval or stale basis was reused by the process.
    preview = load(PRIMARY / 'exact-preview.json'); apply = rows[0][7]
    changed = {p for p in apply['before'].keys() | apply['after'].keys() if apply['before'].get(p) != apply['after'].get(p)}
    assert changed == {p['path'] for p in preview['file_changes']}
    for item in preview['file_changes']:
        for side in ['before','after']:
            actual = apply[side].get(item['path']); expected = item[side]
            assert (actual is None) == (expected is None)
            if actual: assert all(actual[k] == expected[k] for k in ['sha256','bytes'])
    mat = rows[1][1]
    assert {p for p in mat['before'].keys() | mat['after'].keys() if mat['before'].get(p) != mat['after'].get(p)} == {'pack/mods/' + metadata['target']['file']['filename']}
    artifacts = load(RUNS[2] / 'artifacts.json')
    assert load(RUNS[2] / 'receipt.json')['artifactsSha256'] == sha(RUNS[2] / 'artifacts.json')
    for artifact in artifacts:
        path = Path(artifact['retained'])
        assert len({e['path'] for e in artifact['entries']}) == len(artifact['entries'])
        if owner_local and path.exists():
            assert sha(path) == artifact['sha256'] and path.stat().st_size == artifact['bytes']
            with zipfile.ZipFile(path) as z:
                assert z.namelist() == [e['path'] for e in artifact['entries']]
                for entry in artifact['entries']:
                    raw=z.read(entry['path']); assert len(raw) == entry['bytes']
                    assert hashlib.sha256(raw).hexdigest() == entry['sha256'] and hashlib.sha512(raw).hexdigest() == entry['sha512']
                    if 'text' in entry: assert raw.decode() == entry['text']
        else: unavailable.append(str(path))
    ref=artifacts[1]; entries={e['path']:e for e in ref['entries']}; recipient=setups[3]
    assert recipient['sourceArchiveSha256'] == ref['sha256']
    release=entries['.minecraft/.empack-consumer/release.json']; digest=release['sha256']
    assert recipient['releaseSha256'] == digest
    prepare=json.loads(entries['.empack-tools/prepare.json']['text'])
    assert prepare == dict(schema='empack-bootstrap-invocation/1',engine_version='0.8.8-beta',append_arguments=False,arguments=recipient['approvedArguments'])
    assert recipient['approvedArguments'] == ['--workdir','.','--yes','instance','ensure','.minecraft/.empack-consumer/release.json','--sha256',digest,'--layout','prism','--side','client']
    assert rows[3][0]['after']['.empack/releases/' + digest + '.json']['sha256'] == digest
    assert all('/private/tmp/rules-' not in e.get('text','') and '/Users/zer0cell' not in e.get('text','') for a in artifacts for e in a['entries'])
    for name,h in setups[0]['privateApiBodySha256'].items():
        p=Path(setups[0]['work']) / ('api-' + name + '.json')
        if owner_local and p.exists(): assert sha(p) == h
        else: unavailable.append(str(p))
    binary=Path(setups[0]['binary'])
    if owner_local and binary.exists(): assert sha(binary) == expected_binary
    else: unavailable.append(str(binary))
    # Optional owner-local latest postimages. Earlier images remain historical.
    import importlib.util
    spec=importlib.util.spec_from_file_location('frozen_image',PRIMARY/'probe.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    for p,record in [(Path(setups[0]['work'])/'project',rows[2][-1]['after']),
                     (Path(setups[3]['recipient']),rows[3][-1]['after'])]:
        if owner_local and p.exists(): assert helper.image(p) == record
        else: unavailable.append(str(p))
    if owner_local:
        versions=Path(setups[0]['work'])/'api-versions.json'
        if versions.exists():
            records=load(versions)
            for key in ['old','target']:
                sampled=metadata[key]; record=next(r for r in records if r['id']==sampled['id'])
                assert record['project_id']==metadata['project'] and record['dependencies']==[]
                assert sampled['file'] in record['files']
    for source in load(ROOT/'applications/sources/empack-update-flow-selections.json'):
        p=ROOT/source['cache']
        if owner_local and p.exists():
            raw=p.read_bytes();assert sha(p)==source['sha256']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==source['gitBlob']
        else: unavailable.append(str(p))
    return unavailable


def bend_replay(inputs, expected, env, bend):
    # State expressions are computed from operation codes/prior model states,
    # never native observed after-values. Acyclic definitions keep terms small.
    ops={'syncOld':0,'inspect':1,'held':2,'unpin':3,'automaticPreview':4,'exactPreview':5,
         'applyExact':6,'checkRecorded':7,'materialize':8,'checkOnline':9,'bundled':10,
         'references':11,'ensure':12,'checkRecipient':13}
    definitions=['def p0() -> Nat: 1n','def s0() -> Nat: 0n','def f0() -> Nat: 0n','def r0() -> Bool: False{}']
    lines=[]
    for i,operation in enumerate(inputs['operations'],1):
        code=str(ops[operation])+'n'; prior=str(i-1)
        definitions += [f'def p{i}() -> Nat: P.pin({code},p{prior}())',
                        f'def s{i}() -> Nat: P.selected({code},p{prior}(),s{prior}())',
                        f'def f{i}() -> Nat: P.payload({code},p{prior}(),s{prior}(),f{prior}())',
                        f'def r{i}() -> Bool: P.recipient({code},r{prior}())']
        values=[] if ops[operation] >= 12 else [f'p{i}()',f's{i}()',f'f{i}()']
        if operation=='held': values += ['1n',f's{i}()']
        elif operation in ['automaticPreview','exactPreview']: values += ['2n','1n']
        elif operation in ['checkRecorded','checkOnline']: values += ['1n',f'P.verified(s{i}(),f{i}())',f'P.references(s{i}(),f{i}())']
        elif operation in ['bundled','references']: values += [f'P.embedded_mod({code})',f'P.embedded_bootstrap({code})','0n']
        elif operation=='ensure': values += [f'P.recipient_version(r{i}())','1n']
        elif operation=='checkRecipient': values += ['1n',f'Bool.pick(Nat,r{i}(),1n,0n)','0n','1n']
        lines.append('"[" ++ ' + ' ++ "," ++ '.join('Nat.show('+v+')' for v in values) + ' ++ "]"')
    path=FORMAL/'Replay.bend'
    path.write_text('import ../../applications/empack/update-flow/UpdateFlow.bend as P\nimport Base\n'+'\n'.join(definitions)+'\ndef main() -> IO(Unit):\n  IO.write("[" ++ '+' ++ "," ++ '.join(lines)+' ++ "]")\n')
    result=subprocess.run([bend,str(path)],cwd=ROOT,env=env,text=True,capture_output=True,check=True)
    assert json.loads(result.stdout) == expected


def main():
    assert sys.argv[1:] in [[],['--public-only']], 'Use no argument or --public-only'
    owner_local=not sys.argv[1:]
    unavailable=evidence(owner_local); inputs,expected=packets()
    write(PRIMARY/'model-input.json',inputs);write(PRIMARY/'observed-model-values.json',expected)
    proof=load(PRIMARY/'proof-gate.json');assert proof['observedExitCode']==0
    for p,h in proof['sourceSha256'].items(): assert sha(ROOT/p)==h
    env={**os.environ,'LEAN_PATH':str(FORMAL),'BEND_NO_TELEMETRY':'1'}
    lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend')
    command=[lean,'--run','applications/empack/update-flow/UpdateFlowCase.lean']
    actual=json.loads(subprocess.check_output(command+[str(PRIMARY/'model-input.json')],cwd=ROOT,env=env,text=True))
    assert actual==expected
    bend_replay(inputs,expected,env,bend)
    controls=[]
    # Change meaningful observed facts, not only display labels. Every change
    # must contradict the unchanged input-derived trace.
    for label,row,column,value in [('unpin-lost-selection',3,1,0),('unpin-deleted-payload',3,2,0),
        ('preview-applied-target',5,1,2),('apply-retained-old',7,1,1),('apply-materialized',7,2,2),
        ('reference-incomplete',10,3,0),('reference-claimed-verified',10,4,1),
        ('materialize-changed-pin',11,0,0),('bundled-omitted-mod',15,3,0),
        ('reference-enrolled',16,5,1),('recipient-lost-unowned',17,1,0),
        ('unowned-counted-as-seed',19,2,1)]:
        changed=copy.deepcopy(expected);changed[row][column]=value
        assert actual!=changed;controls.append(label)
    for label,change in [('schema',lambda x:x.update(schema=2)),
        ('profile',lambda x:x.update(profile='unqualified-general-graph')),
        ('identity',lambda x:x.update(target='unobserved')),
        ('order',lambda x:x['operations'].__setitem__(10,'materialize')),
        ('operation',lambda x:x['operations'].__setitem__(0,'launch')),
        ('missing-operation',lambda x:x['operations'].pop())]:
        changed=copy.deepcopy(inputs);change(changed);path=FORMAL/(label+'.json');write(path,changed)
        result=subprocess.run(command+[str(path)],cwd=ROOT,env=env,text=True,capture_output=True)
        assert result.returncode==2 and 'research' in result.stderr;controls.append(label)
    # Exercise the byte/JSON/archive observation adapters themselves. A decoded
    # contradiction or profile refusal must be caught, not merely a row edit.
    raw_rows=[load(r/'commands.json') for r in RUNS]
    raw_jsons=[{p.stem:load(p) for p in r.glob('*.json')} for r in RUNS]
    raw_artifacts=load(RUNS[2]/'artifacts.json')
    for label,kind in [('raw-check-count','count'),('raw-archive-mod','mod'),
                       ('raw-command-mode','args'),('raw-payload-assertion','hash')]:
        rows=copy.deepcopy(raw_rows);jsons=copy.deepcopy(raw_jsons);artifacts=copy.deepcopy(raw_artifacts)
        if kind=='count': jsons[1]['check-reference']['verified_files']=1
        elif kind=='mod': artifacts[0]['entries']=[e for e in artifacts[0]['entries'] if '/mods/' not in e['path']]
        elif kind=='args': rows[0][6]['argv'].append('--apply')
        else: rows[1][1]['after']['pack/mods/ferritecore-7.0.3-fabric.jar']['sha512']='0'*128
        try:
            _,changed=packets(rows,jsons,artifacts)
        except AssertionError: pass
        else:
            # Different decoded result is the expected rejection at comparison.
            assert changed!=actual
        controls.append(label)
    files=[p for run in RUNS for p in run.iterdir() if p.is_file() and p.name not in ['basis.json','conformance.json']]
    files += [p for p in HERE.iterdir() if p.is_file()]
    files += [ROOT/'applications/sources/empack-update-flow-selections.json']
    write(PRIMARY/'basis.json',{str(p.relative_to(ROOT)):sha(p) for p in files})
    result=dict(schema=1,replayProfile='owner-local' if owner_local else 'public-retained-only',nativeCommands=20,joinedWorkflows=1,traceRows=20,dualScalarComparisons=sum(map(len,expected)),
                leanLaws=18,bendLaws=19,controls=controls,basisFiles=len(files),unavailableArtifacts=unavailable,
                limits=['One successful provider root on Mac arm64; no multi-mod solving, failures, concurrency, other platforms, startup or game qualification.',
                        'Two snapshot exports and first native recipient preparation; no Java/bootstrap execution or existing recipient old-to-new update/channel.',
                        'Finite equality-label success profile, independently observed byte hashes; not a general YAML/graph/crypto model.',
                        'Retained replay never reacquires providers, rebuilds archives, or reruns application commands.'])
    write(PRIMARY/'conformance.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__': main()
