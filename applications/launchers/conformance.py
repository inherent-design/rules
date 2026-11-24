#!/usr/bin/env python3
"""Replay launcher source-fragment results; no GUI, compiler C++, or download."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    receipt = json.loads((run / 'receipt.json').read_text())
    assert sha((run / 'input.json').read_bytes()) == receipt['inputSha256']
    assert sha((run / 'observed.stdout').read_bytes()) == receipt['stdoutSha256']
    assert sha((run / 'observed.stderr').read_bytes()) == receipt['stderrSha256']
    assert sha((run / 'probe.py').read_bytes()) == receipt['entrypointSha256']
    inputs = json.loads((run / 'input.json').read_text())
    observed = json.loads((run / 'observed.stdout').read_text())
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    env = dict(os.environ, LEAN_PATH=str(ROOT / '.build'), BEND_NO_TELEMETRY='1')
    result = subprocess.run([lean, '--run', 'applications/launchers/Case.lean', str(run / 'input.json')], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    model = json.loads(result.stdout)
    (run / 'lean-model.json').write_text(json.dumps(model, indent=2) + '\n')
    assert model['mo2'] == observed['mo2']
    assert len(model['mo2']) == 56 and len(model['prism']) == 6
    for expected, actual in zip(model['prism'], observed['prism']):
        assert {k: expected[k] for k in actual} == actual

    # Bend compares the complete MO2 winner projection and the Prism reuse
    # decision matrix. The generic Prism list plan is implemented only in Lean.
    q = lambda s: json.dumps(s, ensure_ascii=False)
    mo2_lines, prism_lines, pair_expected = [], [], []
    for c in inputs['mo2']:
        assert re.fullmatch(r'pair-[0-9]+', c['id'])
        origins = []
        for o in c['candidates']:
            value = o['priority'] if o['loose'] else o['archiveOrder']
            assert value in [-1, 0, 1, 2] and o['id'] in [1, 2]
            maybe = 'None{}' if value < 0 else 'Some{' + str(value) + 'n}'
            origins.append('M.Orig{' + str(o['id']) + 'n,' + ('True{}' if o['loose'] else 'False{}') + ',' + maybe + '}')
        mo2_lines.append(q(c['id'] + '=') + ' ++ M.winner_id(M.winner([' + ','.join(origins) + '])) ++ "\\n"')
    for c in inputs['prism']:
        for new in c['new']:
            for old in c['old']:
                for f in [new, old]:
                    assert re.fullmatch(r'config/[A-Za-z._α日本/-]+\.json', f['path'])
                    assert re.fullmatch(r'[0-9a-f]{128}', f['hash'])
                a = 'P.Entry{' + q(new['path']) + ',' + q(new['hash']) + '}'
                b = 'P.Entry{' + q(old['path']) + ',' + q(old['hash']) + '}'
                for aware in [False, True]:
                    prism_lines.append('Bool.pick(String, P.can_reuse(' + ('True{}' if aware else 'False{}') + ',' + a + ',' + b + '), "1", "0") ++ "\\n"')
                    pair_expected.append('1' if new['hash'] == old['hash'] and (not aware or new['path'] == old['path']) else '0')
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)
    source = 'import Base\nimport ../../mo2/Overlay.bend as M\nimport ../../prism/Update.bend as P\n\ndef main() -> IO(Unit):\n  IO.write("mo2\\n" ++ ' + ' ++ '.join(mo2_lines) + ' ++ "prism\\n" ++ ' + ' ++ '.join(prism_lines) + ')\n'
    (generated / 'Cases.bend').write_text(source)
    result = subprocess.run([bend, str(generated / 'Cases.bend')], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    lines = result.stdout.splitlines()
    cut = lines.index('prism')
    assert lines[0] == 'mo2'
    assert lines[1:cut] == [str(c['id']) + '=' + str(c['winner']) for c in observed['mo2']]
    assert lines[cut + 1:] == pair_expected
    (run / 'bend-model.stdout').write_text(result.stdout)
    # Stronger expectations are checked independently of the source filter.
    impacts = []
    for c, m in zip(inputs['prism'], model['prism']):
        expected = {f['path']: f['hash'] for f in c['new']}
        current = {f['path']: f['hash'] for f in m['simulatedFinal']}
        proposed = {f['path']: f['hash'] for f in m['proposedFinal']}
        assert proposed == expected
        impacts.append({'id': c['id'], 'missing': sorted(set(expected) - set(current)),
                        'extra': sorted(set(current) - set(expected)),
                        'wrong': sorted(k for k in expected.keys() & current.keys() if expected[k] != current[k]),
                        'pathAwareProposalMatchesTarget': True})
    indexed = {c['id']: c for c in impacts}
    assert indexed['moved-path-plus-change']['missing'] == ['config/new.json']
    assert indexed['single-moved-path']['extra'] == ['config/old.json']
    assert indexed['swapped-content-plus-change']['wrong'] == ['config/extra.json', 'config/old.json']
    assert indexed['same-path-plus-change']['missing'] == indexed['same-path-plus-change']['wrong'] == []
    assert any(max(c['candidates'], key=lambda o: o['priority'])['id'] != out['winner']
               for c, out in zip(inputs['mo2'], observed['mo2']))
    (run / 'simulated-impact.json').write_text(json.dumps(impacts, indent=2) + '\n')
    models = [HERE / 'Case.lean', HERE.parent / 'mo2/Overlay.lean', HERE.parent / 'mo2/Overlay.bend',
              HERE.parent / 'prism/Update.lean', HERE.parent / 'prism/Update.bend']
    report = {'schema': 1, 'status': 'Source-fragment/model comparison; full product native qualification pending',
              'mo2WinnerCases': 56, 'prismPlanCases': 6, 'prismPairDecisions': len(pair_expected),
              'leanPlansMatchExecutedFragments': True, 'bendMo2WinnersAndPrismDecisionsAgree': True,
              'priorityOnlyWinnerAssumptionRejected': True, 'hashOnlyReuseTargetCounterexamples': True,
              'emptyPendingReparseGuardRetained': True, 'pathAwareProposalMatchesSixTargets': True,
              'models': {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in models},
              'limits': ['MO2 fragment field adapters are fixture implementations, not Windows VFS.',
                         'Prism source filter uses Qt6; staging reparse and final overlay are explicit projections, not full importer execution.',
                         'Bend covers Prism reuse decisions; generic filtering/staging simulation is Lean-only.',
                         'The path-aware proposal is unimplemented in Prism and does not prove all update cases or local-edit policy.']}
    (run / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
