#!/usr/bin/env python3
"""Replay retained Cargo observations against two models; does not run Cargo."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    trace = json.loads((run / 'trace.json').read_text())
    rows = {r['operationId']: r for r in trace}
    for row in trace:
        assert row['outcome']['exitCode'] == 0
        for stream in ['stdout', 'stderr']:
            assert digest(run / (row['operationId'] + '.' + stream)) == row['observed'][stream + 'Sha256']
    metadata = json.loads((run / 'metadata.stdout').read_text())
    lib = next(p['id'] for p in metadata['packages'] if p['name'] == 'fixture-library')
    features = next(n['features'] for n in metadata['resolve']['nodes'] if n['id'] == lib)
    assert features == ['blue', 'red']
    assert rows['metadata']['observed']['before']['lockSha256'] is None
    lock = rows['metadata']['observed']['after']['lockSha256']
    assert lock and all(r['observed']['after']['lockSha256'] == lock for r in trace)
    clean = rows['clean']['observed']
    assert clean['before']['targetExists'] and not clean['after']['targetExists']
    outside = clean['before']['sideEffectSha256']
    assert outside and clean['after']['sideEffectSha256'] == outside
    env = dict(os.environ, LEAN_PATH=str(ROOT / '.build'), BEND_NO_TELEMETRY='1')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)

    def evaluate(case):
        path = run / 'model-input.json'
        path.write_text(json.dumps(case, indent=2) + '\n')
        a = json.loads(subprocess.check_output([lean, '--run', 'applications/cargo/Case.lean', str(path)], cwd=ROOT, env=env, text=True))
        # This code generator admits only fixture tokens/hashes, no arbitrary source text.
        for key in ['previousSignature', 'previousValue', 'signature', 'actual', 'outsideOutput']:
            assert re.fullmatch(r'[a-z0-9|]*', case[key]), (key, case[key])
        q = json.dumps
        source = 'import Base\nimport ../Build.bend as C\n\ndef bit(value: Bool) -> String:\n  match value:\n    case True{}: "true"\n    case False{}: "false"\n\ndef feature_lines(f: C.Features) -> String:\n  match f:\n    case C.Feat{red, blue}: bit(red) ++ "\\n" ++ bit(blue) ++ "\\n"\n\ndef main() -> IO(Unit):\n  IO.write(feature_lines(C.selected_features(' + ('True{}' if case['workspace'] else 'False{}') + ')) ++ C.captured(C.capture(C.Cache{' + q(case['previousSignature']) + ',' + q(case['previousValue']) + '},' + q(case['signature']) + ',' + q(case['actual']) + ')) ++ "\\n" ++ bit(C.target_present(C.clean(C.Effect{True{},""}))) ++ "\\n" ++ C.outside(C.clean(C.Effect{True{},' + q(case['outsideOutput']) + '})) ++ "\\n")\n'
        script = generated / 'NativeCase.bend'
        script.write_text(source)
        lines = subprocess.check_output([bend, str(script)], cwd=ROOT, env=env, text=True).splitlines()
        assert len(lines) == 5 and all(lines[i] in ['true', 'false'] for i in [0, 1, 3])
        b = {'red': lines[0] == 'true', 'blue': lines[1] == 'true', 'captured': lines[2],
             'targetAfterClean': lines[3] == 'true', 'outsideAfterClean': lines[4]}
        assert a == b, (a, b)
        return a

    cases, previous_signature, previous_value = [], 'absent', ''
    for label in ['red', 'workspace', 'red-again', 'undeclared-input', 'declared-input', 'declared-input-change']:
        before = rows[label + '-build']['observed']['before']
        signature = before['buildScriptSha256'] + ('|' + before['inputSha256'] if before['declaresInput'] else '')
        case = {'schema': 1, 'workspace': label == 'workspace', 'previousSignature': previous_signature,
                'previousValue': previous_value, 'signature': signature, 'actual': before['inputText'], 'outsideOutput': outside}
        model = evaluate(case)
        native = json.loads((run / (label + '-run.stdout')).read_text())
        assert {k: model[k] for k in ['red', 'blue']} == {k: native[k] for k in ['red', 'blue']}
        assert model['captured'] == native['input'], (label, model, native)
        cases.append({'label': label, 'input': case, 'native': native, 'model': model})
        previous_signature, previous_value = signature, native['input']
    artifact_events = [json.loads(s) for s in (run / 'undeclared-input-build.stdout').read_text().splitlines()]
    artifacts = [e for e in artifact_events if e['reason'] == 'compiler-artifact']
    assert artifacts and all(e['fresh'] for e in artifacts)
    # Two deliberately wrong interpretations are contradicted by direct output.
    assert cases[0]['native']['blue'] is False and 'blue' in features  # metadata union != app unit
    stale = next(c for c in cases if c['label'] == 'undeclared-input')
    assert stale['native']['input'] != stale['input']['actual']  # fresh != all real inputs unchanged
    (run / 'projected-cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    result = {'schema': 1, 'cases': len(cases), 'modelsAgreeWithNative': True,
              'metadataAsSelectedUnitCounterexampleRejected': True,
              'freshAsCompleteInputProofCounterexampleRejected': True,
              'coldMetadataCreatedLock': True, 'cleanPreservedOutsideEffect': True,
              'cleanAsUndoAllEffectsCounterexampleRejected': True,
              'traceSha256': digest(run / 'trace.json'), 'projectedCasesSha256': digest(run / 'projected-cases.json'),
              'models': {p.name: digest(p) for p in [HERE / 'Build.lean', HERE / 'Build.bend', HERE / 'Case.lean']},
              'limits': ['The watched signature projects fixture build.rs/input changes; does not implement Cargo timestamp/fingerprint detection.',
                         'Normal dependency unification for two workspace roots only; resolver versions, target splits and cross-compilation unqualified.',
                         'Complete-input implication is conditional; the incomplete fixture intentionally violates that premise.',
                         'Cleanup observation applies once at the end; the cleanup model is compared independently of the six build cases.']}
    (run / 'conformance.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
