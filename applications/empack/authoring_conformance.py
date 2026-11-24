#!/usr/bin/env python3
"""Compare proposed authoring models with design examples, not native empack."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    inputs = HERE / 'fixtures/authoring.json'
    expected_path = HERE / 'fixtures/expected.json'
    data, expected = json.loads(inputs.read_text()), json.loads(expected_path.read_text())
    run = ROOT / 'applications/evidence' / ('empack-authoring-candidate-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'
    work.mkdir(parents=True)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    env = dict(os.environ, LEAN_PATH=os.pathsep.join(str(ROOT / p) for p in ['.build', '.build/formal']), BEND_NO_TELEMETRY='1')
    result = subprocess.run([lean, '--run', 'applications/empack/AuthoringCase.lean', str(inputs)],
                            cwd=ROOT, env=env, capture_output=True, text=True)
    (run / 'lean.stdout').write_text(result.stdout)
    (run / 'lean.stderr').write_text(result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == expected
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)
    initial = data['initial']
    saved = 'None{}' if initial['saved'] is None else 'Some{' + str(initial['saved']) + 'n}'
    lines = [f'  +s0 : E.DraftEditor = E.Editor{{{initial["epoch"]}n,{initial["current"]}n,{saved},{initial["savedRevision"]}n}}']
    outputs = []
    boolean = lambda b: 'True{}' if b else 'False{}'
    for i, a in enumerate(data['actions'], 1):
        old, new = f's{i-1}', f's{i}'
        if a['kind'] == 'edit':
            expression = f'E.edit_to({old},{a["image"]}n)'
        elif a['kind'] == 'save':
            expression = f'E.accept_save({data["project"]}n,{data["incarnation"]}n,{a["project"]}n,{a["incarnation"]}n,{boolean(a["confirmed"])},{old},{a["revision"]}n,{a["image"]}n)'
        else:
            assert a['kind'] in ['observe', 'background']
            expression = old
        lines.append(f'  +{new} : E.DraftEditor = {expression}')
        background = f'Bool.show(E.accepts_background({new},{a["epoch"]}n,{a["image"]}n))' if a['kind'] == 'background' else '"none"'
        outputs.append(f'row({new},{background})')
    for c in data['readiness']:
        as_list = lambda values: '[' + ','.join(str(v) + 'n' for v in values) + ']'
        args = ','.join([boolean(c['valid']), boolean(c['complete']), boolean(c['capable']), as_list(c['required']), as_list(c['held'])])
        outputs.extend([f'Bool.show(E.can_save({as_list(c["available"])},{as_list(c["held"])})) ++ "\\n"',
                        f'Bool.show(E.can_export({args})) ++ "\\n"'])
    source = '''import Base
import ../Authoring.bend as E

def saved_text(value: Maybe<&2, Nat>) -> String:
  match value:
    case None{}: "none"
    case Some{value}: Nat.show(value)

def row(+editor: E.DraftEditor, background: String) -> String:
  Nat.show(E.epoch(editor)) ++ "\\n" ++ Nat.show(E.current_image(editor)) ++ "\\n" ++ saved_text(E.saved_image(editor)) ++ "\\n" ++ Nat.show(E.saved_revision(editor)) ++ "\\n" ++ Bool.show(E.dirty(editor)) ++ "\\n" ++ background ++ "\\n"

def main() -> IO(Unit):
''' + '\n'.join(lines) + '\n  IO.write(' + ' ++ '.join(outputs) + ')\n'
    case = generated / 'AuthoringCase.bend'
    case.write_text(source)
    result = subprocess.run([bend, str(case)], cwd=ROOT, env=env, capture_output=True, text=True)
    (run / 'bend.stdout').write_text(result.stdout)
    (run / 'bend.stderr').write_text(result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    expected_text = ''.join('\n'.join([r['epoch'], r['current'], r['saved'] or 'none', r['savedRevision'], str(r['unsaved']),
        'none' if r['backgroundAccepted'] is None else str(r['backgroundAccepted'])]) + '\n' for r in expected['editor'])
    expected_text += ''.join(str(r[k]) + '\n' for r in expected['readiness'] for k in ['canSave', 'canExport'])
    assert result.stdout == expected_text
    assert expected['editor'][7]['unsaved'] is False and int(expected['editor'][7]['epoch']) > int(expected['editor'][3]['epoch'])
    assert expected['editor'][8]['backgroundAccepted'] is False
    assert expected['editor'][6]['current'] != expected['editor'][6]['saved']
    current_only = [x for x in data['retention']['stored'] if x in data['retention']['current']]
    assert current_only != expected['collected'] and 9 not in expected['collected']
    # Unsupported actions must be refused, not silently treated as observation.
    invalid = json.loads(inputs.read_text())
    invalid['actions'][0]['kind'] = 'publish-unverified-image'
    bad = work / 'invalid.json'
    bad.write_text(json.dumps(invalid))
    result = subprocess.run([lean, '--run', 'applications/empack/AuthoringCase.lean', str(bad)],
                            cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 2 and 'Unsupported proposed authoring action' in result.stderr
    report = {'schema': 1, 'kind': 'Proposed protocol examples;not native implementation conformance',
        'editorStatesMatchBothModels': len(expected['editor']), 'readinessCasesMatchBothModels': len(expected['readiness']),
        'leanRetentionExampleMatches': True, 'unknownActionRefused': True,
        'rejectedInterpretations': ['edit epoch alone establishes unsaved changes', 'same image alone admits stale background work',
            'a late save replaces the current editor image', 'current draft alone covers retention roots',
            'invalid authoring must be discarded before saving', 'missing unselected content blocks every export'],
        'inputSha256': sha(inputs), 'expectedSha256': sha(expected_path), 'adapterSha256': sha(Path(__file__)),
        'models': {p.name: sha(p) for p in [HERE / 'Authoring.lean', HERE / 'Authoring.bend', HERE / 'AuthoringCase.lean', ROOT / 'common/Lifecycle.lean']},
        'limits': ['Design examples are manually specified policy expectations,not observations from empack0.9.',
            'Image and asset IDs are admitted symbolic identities;no raw-document codec,hashing,lease implementation,or actual export is modeled.',
            'Host save revisions and finalization are premises;no browser storage,multi-tab transaction,native publication,or crash test.',
            'Retention example uses the shared pure classifier under complete coordinated roots;Bend replay covers editor/readiness only.']}
    (run / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'run': str(run), **report}, indent=2))


if __name__ == '__main__':
    main()
