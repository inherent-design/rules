#!/usr/bin/env python3
"""Replay one retained untitled reload observation; never launch a browser."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def admit(receipt, review):
    assert receipt['schema'] == review['schema'] == 1
    assert receipt['mode'] == 'untitled-reload' and not receipt.get('error')
    observed = receipt['observation']
    assert observed['versionInfo'] == 'stable;1.147.0;8a14f0cc1b08d531eb83255ea3764ae22aa932b5'
    assert observed['browserVersion'] == '156.0.8078.4'
    assert observed['sdkVersion'] == '1.64.1'
    assert observed['secure'] and observed['workbenchPresent'] and not observed['errors']
    editing = observed['editing']
    assert editing['paletteChoice'].split('\n')[0] == 'File: New Untitled Text File'
    assert editing['markerObservedAfterReload'] and not editing['dialogs']
    marker = editing['marker']
    assert editing['before']['renderedText'] == editing['afterRenderedText'] == [marker]
    tabs = editing['before']['tabs']
    assert len([t for t in tabs if 'Untitled-1' in t['label'] and 'dirty' in t['className'].split()]) == 1
    # Post-reload dirty state comes from an explicitly retained image review,
    # not a nonexistent DOM capture or an inference from marker restoration.
    assert review['afterDirtyObservation'].startswith('Visual inspection')
    return marker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    load = lambda name: json.loads((run / name).read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    receipt, review = load('receipt.json'), load('review.json')
    assert sha(run / 'receipt.json') == review['receiptSha256']
    assert sha(run / 'probe.mjs') == review['probeSha256'] == receipt['entrypointSha256']
    for name, image in review['screenshots'].items():
        assert sha(run / name) == image['sha256']
    marker = admit(receipt, review)
    key = review['logicalResourceKey']
    inputs = {'schema': 1, 'logicalResourceKey': key, 'renderedMarker': marker}
    (run / 'model-input.json').write_text(json.dumps(inputs, indent=2) + '\n')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    env = dict(os.environ, LEAN_PATH=str(ROOT / '.build'), BEND_NO_TELEMETRY='1')
    result = subprocess.run([lean, '--run', 'applications/vscode/WebCase.lean', str(run / 'model-input.json')],
                            cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    lean_projection = json.loads(result.stdout)
    assert lean_projection == dict(logicalResourceKey=key, renderedMarker=marker, dirty=True, fileWriteReceipt=None)
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)
    source = '''import Base
import ../WebDraft.bend as W

def receipt_text(value: Maybe<&2, String>) -> String:
  match value:
    case None{}: "no-file-receipt"
    case Some{value}: value

def report(+observation: W.UntitledObservation) -> String:
  W.rendered_text(observation) ++ "\\n" ++ receipt_text(W.receipt(observation))

def main() -> IO(Unit):
  IO.write(report(W.restored_untitled(''' + json.dumps(key) + ',' + json.dumps(marker, ensure_ascii=False) + ')))\n'
    case = generated / 'WebCase.bend'
    case.write_text(source)
    result = subprocess.run([bend, str(case)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == marker + '\nno-file-receipt'
    wrong = json.loads(json.dumps(receipt))
    wrong['observation']['editing']['paletteChoice'] = 'File: Compare New Untitled Text Files'
    try:
        admit(wrong, review)
    except AssertionError:
        pass
    else:
        raise AssertionError('Different command incorrectly admitted as the ordinary editor flow.')
    # The actual earlier diff-editor run is excluded, not rewritten as a pass.
    diff = json.loads((run.parent / 'vscode-web-untitled-reload-20261124T022038104Z/receipt.json').read_text())
    try:
        admit(diff, review)
    except AssertionError:
        pass
    else:
        raise AssertionError('Actual comparison-editor run was accepted as the ordinary editor flow.')
    report = {
        'schema': 1, 'ordinaryReloadCases': 1,
        'leanRestorationProjectionMatches': True, 'bendMarkerAndNoFileReceiptMatch': True,
        'differentCommandRejected': True, 'actualComparisonEditorRunExcluded': True,
        'fileSaveInferredFromReload': False,
        'models': {p.name: sha(p) for p in [HERE / 'WebDraft.lean', HERE / 'WebDraft.bend', HERE / 'WebCase.lean']},
        'adapterSha256': sha(Path(__file__)), 'receiptSha256': sha(run / 'receipt.json'),
        'reviewSha256': sha(run / 'review.json'),
        'limits': [
            'Projection conditions on successful restoration; it does not implement or prove the backup protocol.',
            'One same-profile Chromium page reload; no process relaunch,eviction,local-file save,or project durability.',
            'Marker and dirty indication only; no complete document snapshot or native resource URI was exported.',
            'After-reload dirty indication is retained screenshot review,not captured DOM state.',
            'Bend comparison covers marker/no-file-receipt; its resource/dirty fields are not independently replayed.'
        ]}
    (run / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
