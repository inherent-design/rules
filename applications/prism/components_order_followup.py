#!/usr/bin/env python3
"""Additional version-spelling cases through the already attributed Qt binary."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = Path(__file__).read_bytes()
sha = lambda data: hashlib.sha256(data).hexdigest()


def main():
    original = ROOT / 'applications/evidence/prism-components-20261124T111134328480Z'
    receipt = json.loads((original / 'receipt.json').read_text())
    binary = original / 'work/probe'
    assert sha(binary.read_bytes()) == receipt['binarySha256']
    for name, digest in receipt['generatedSha256'].items():
        assert sha((original / 'work' / name).read_bytes()) == digest
    selections = json.loads((ROOT / 'applications/sources/prism-components-selections.json').read_text())
    current = {r['path']: r['sha256'] for r in selections}
    assert all(current.get(path) == digest for path, digest in receipt['sources'].items())
    for row in selections:
        assert sha((ROOT / row['cache']).read_bytes()) == row['sha256']

    def component(uid, exact='', suggested=''):
        return dict(uid=uid, version='1.0', requires=[dict(uid='net.minecraft', equals=exact, suggests=suggested)])

    cases = [
        dict(id='equal-rank-suggestions-left-right', components=[component('fixture.left', suggested='1.2+left'), component('fixture.right', suggested='1.2+right')]),
        dict(id='equal-rank-suggestions-right-left', components=[component('fixture.right', suggested='1.2+right'), component('fixture.left', suggested='1.2+left')]),
        dict(id='distinct-exact-spelling', components=[component('fixture.left', exact='1.02'), component('fixture.right', exact='1.2')]),
    ]
    run = ROOT / 'applications/evidence' / ('prism-component-order-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    work = run / 'work'
    (work / 'home').mkdir(parents=True)
    (work / 'tmp').mkdir()
    (run / 'probe.py').write_bytes(PRODUCER)
    (run / 'input.json').write_text(json.dumps(dict(schema=1, cases=cases), indent=2) + '\n')
    env = dict(PATH='/usr/bin:/bin', HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'), LANG='en_US.UTF-8')
    argv = [str(binary), str(run / 'input.json')]
    result = subprocess.run(argv, env=env, capture_output=True, timeout=20)
    (run / 'observed.stdout').write_bytes(result.stdout)
    (run / 'observed.stderr').write_bytes(result.stderr)
    assert result.returncode == 0
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(rows) == 3 and {r['qtRuntime'] for r in rows} == {receipt['qtVersion']}
    assert sha(binary.read_bytes()) == receipt['binarySha256']
    rec = dict(schema=1, producerSha256=sha(PRODUCER), reusedCapture=str(original.relative_to(ROOT)),
        reusedReceiptSha256=sha((original / 'receipt.json').read_bytes()), reusedBinarySha256=receipt['binarySha256'],
        sourceRevision=receipt['sourceRevision'], argv=argv, executeExit=result.returncode,
        inputSha256=sha((run / 'input.json').read_bytes()), stdoutSha256=sha(result.stdout), stderrSha256=sha(result.stderr),
        qtVersion=receipt['qtVersion'], cases=len(rows),
        limits=['No new compilation. Reuses the prior exactly attributed unmodified-source Qt fragment binary and its fixture Component adapters.',
            'Selected equivalent-ranking suggestion spellings and distinct exact strings only; not full FlexVer, metadata parsing, or resolver/publication qualification.'])
    (run / 'receipt.json').write_text(json.dumps(rec, indent=2) + '\n')
    print(json.dumps(dict(run=str(run), observations=rows), indent=2))


if __name__ == '__main__':
    main()
