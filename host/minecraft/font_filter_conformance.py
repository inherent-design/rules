#!/usr/bin/env python3
"""Pure retained two-option font-filter comparisons; no JVM, fonts or renderer."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
CAPTURES = ['font-filter-1.21.1-20261125T142332481315Z','font-filter-1.21.4-20261125T142448795641Z',
            'font-filter-1.21.5-20261125T142450189243Z','font-filter-1.21.11-20261125T142451619717Z','font-filter-26.3-20261125T142452505278Z']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def project(obs):
    assert obs['schema'] == 1 and obs['observerErrors'] == 0 and obs['options'] == 2
    expected = []
    for left in range(9):
        expected += [('direct',left,0,mask) for mask in range(4)]
        expected += [('merged',left,right,mask) for right in range(9) for mask in range(4)]
    expected += [(label,left,0,1) for label,left in [('before-borrowed',2),('before-snapshot',2),('after-borrowed',1),('after-snapshot',2)]]
    raw = obs['rows'] + obs['controls']; assert len(obs['rows']) == 360 and len(obs['controls']) == 4
    assert len(raw) == len(expected); rows = []; results = []
    for row,(kind,left,right,mask) in zip(raw,expected):
        assert (row['kind'],row['left'],row['right'],row['mask']) == (kind,left,right,mask)
        assert type(row['result']) is bool
        rows.append(dict(left=left,right=right,mask=mask,merged=kind == 'merged')); results.append(int(row['result']))
    return dict(schema=1,contract='original-font-filter-two-options',rows=rows),results


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output',type=Path); a = p.parse_args()
    work = ROOT/'.build/minecraft/font-filter-replay'; work.mkdir(parents=True,exist_ok=True)
    env = dict(os.environ,LEAN_PATH=os.environ.get('LEAN_PATH',str(ROOT/'.build/formal')),BEND_NO_TELEMETRY='1')
    def lean(data,label):
        path = work/(label+'.json'); path.write_text(json.dumps(data)+'\n')
        return subprocess.run([os.environ.get('LEAN','lean'),'--run',str(HERE/'FontFilterCase.lean'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    def bend(rows,label):
        calls = ['Nat.show(M.font_filter_evaluate('+str(r['left'])+'n,'+str(r['right'])+'n,'+str(r['mask'])+'n,'+('True{}' if r['merged'] else 'False{}')+')) ++ "\\n"' for r in rows]
        path = work/(label+'.bend'); path.write_text('import Base\nimport ../../../host/minecraft/FontFilter.bend as M\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
        r = subprocess.run([os.environ.get('BEND','bend'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
        assert r.returncode == 0,r.stdout+r.stderr
        return [int(v) for v in r.stdout.splitlines()]
    basis = [HERE/n for n in ['FontFilter.lean','FontFilter.bend','FontFilterCase.lean','font_filter_conformance.py']]
    observations = []; predictions = []; requests = []; profiles = []
    for i,name in enumerate(CAPTURES):
        c = HERE/'evidence'/name; receipt = json.loads((c/'receipt.json').read_text()); observed = json.loads((c/'observed.json').read_text())
        assert receipt['rows'] == 360 and receipt['controls'] == 4 and receipt['observerErrors'] == 0
        assert sha(c/'bindings.json') == receipt['bindingsSha256'] and sha(c/'observed.json') == receipt['observed.jsonSha256']
        for f,h in receipt['sourcesSha256'].items(): assert sha(c/f) == h
        for stem,cmd in zip(['compile','execute'],receipt['commands']):
            assert cmd['exitCode'] == 0 and cmd['ownedGroupAbsent'] and not cmd['timedOut']
            for channel in ['stdout','stderr']: assert sha(c/(stem+'.'+channel)) == cmd[channel+'Sha256']
        data,expected = project(observed); r = lean(data,str(i)); assert r.returncode == 0,r.stdout+r.stderr
        predicted = json.loads(r.stdout); assert predicted == expected == bend(data['rows'],str(i))
        observations.append(observed); predictions.append(predicted); requests.append(data)
        profiles.append(dict(target=receipt['target'],profile=receipt['profile'],predicateComparisons=360,mapCustodyComparisons=4)); basis += [f for f in c.iterdir() if f.is_file()]
    base = requests[0]; negatives = [dict(base,schema=2),dict(base,contract='font-rasterizer'),dict(base,rows=base['rows']*2)]
    row = dict(left=0,right=0,mask=0,merged=False)
    for change in [dict(left=9),dict(right=9),dict(mask=4),dict(left=-1),dict(left=True),dict(merged=1),dict(right=1)]: negatives.append(dict(base,rows=[row|change]))
    for i,bad in enumerate(negatives): assert lean(bad,'negative-'+str(i)).returncode == 2
    rejected = []
    for kind,index in [('direct',0),('merged',5),('merged',42),('control',2),('control',3)]:
        changed = copy.deepcopy(observations[0])
        rows = changed['controls'] if kind == 'control' else [r for r in changed['rows'] if r['kind'] == kind]
        rows[index]['result'] = not rows[index]['result']
        try: assert project(changed)[1] == predictions[0]
        except AssertionError: rejected.append(kind+':'+str(index))
        else: raise AssertionError('Changed predicate admitted')
    # Exhaustive contradiction witness under the selected finite predicates.
    false_true = next(r for r in observations[0]['rows'] if r['kind']=='merged' and (r['left'],r['right'],r['mask'])==(1,2,0))
    assert false_true['result'] is True
    direct = {(r['left'],r['mask']):r['result'] for r in observations[0]['rows'] if r['kind']=='direct'}
    assert (direct[(1,0)] and direct[(2,0)]) is False
    report = dict(schema=1,status='passed-original-font-filter-two-options',profiles=profiles,comparisons=1820,
        predicateComparisons=1800,mapCustodyComparisons=20,leanLaws=12,bendLaws=8,decoderRefusals=len(negatives),changedObservationControls=rejected,
        basisSha256={str(f.relative_to(ROOT)):sha(f) for f in sorted(basis)},
        limits=['Original filter APIs on authored two-option HashMaps/HashSets;no glyph/provider/rasterizer/renderer or full font-reference execution.',
                'Four temporal controls per profile compare borrowed-map changes and a merged captured map through predetermined source-plan predicate inputs;not a JVM heap/concurrency proof.',
                'Merge precedence is modeled,not replaced with conjunction. Whole font loader/filter/display integration remains source-only.',
                'Native macOS/JDK21/25 only;arbitrary custom maps/sets,unknown options,nulls,subclass effects,other platforms and native resources remain unqualified.'])
    if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','comparisons','predicateComparisons','mapCustodyComparisons','decoderRefusals','changedObservationControls']}))


if __name__ == '__main__': main()
