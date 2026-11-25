#!/usr/bin/env python3
"""Export authored range observations and class identities; keep game bytes private."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--client', type=Path, required=True)
    args = parser.parse_args()
    capture = args.capture.resolve()
    receipt = json.loads((capture / 'receipt.json').read_text())
    assert receipt['target'] == 'java-1.21.4-vanilla' and receipt['observerErrors'] == 0 and receipt['cases'] == 76
    assert sha(args.client) == receipt['clientSha256']
    assert all(c['exitCode'] == 0 and c['ownedGroupAbsent'] and not c['timedOut'] for c in receipt['commands'])
    for name, digest in receipt['sourcesSha256'].items():
        assert sha(capture / name) == digest
    assert sha(capture / 'bindings.json') == receipt['bindingsSha256']
    assert sha(capture / 'observed.json') == receipt['observedSha256']
    assert sha(capture / 'library-input.json') == receipt['libraryReceiptSha256']
    assert sha(capture / 'class-load.log') == receipt['classLoadLogSha256']
    # Record classes loaded from this exact original JAR, without confusing load
    # with initialization, execution, or a complete method/host-effect closure.
    loaded = {}
    with zipfile.ZipFile(args.client) as archive:
        assert hashlib.sha256(archive.read(receipt['originalClassMember'])).hexdigest() == receipt['originalClassSha256']
        for line in (capture / 'class-load.log').read_text().splitlines():
            if args.client.name not in line:
                continue
            match = re.search(r'\] ([^ ]+) source: ', line)
            assert match, line
            member = match[1].replace('.', '/') + '.class'
            loaded[member] = hashlib.sha256(archive.read(member)).hexdigest()
    assert receipt['originalClassMember'] in loaded
    destination = HERE / 'evidence' / capture.name
    destination.mkdir(parents=True, exist_ok=False)
    for name in [*receipt['sourcesSha256'], 'bindings.json', 'observed.json']:
        shutil.copyfile(capture / name, destination / name)
    for stem, c in zip(['compile', 'execute'], receipt['commands']):
        for stream in ['stdout', 'stderr']:
            name = stem + '.' + stream
            assert sha(capture / name) == c[stream + 'Sha256']
            shutil.copyfile(capture / name, destination / name)
    public = {k: v for k, v in receipt.items() if k not in ['commands', 'tools', 'libraries']}
    public['tools'] = {n: dict(executable=Path(t['path']).name, sha256=t['sha256']) for n, t in receipt['tools'].items()}
    public['libraries'] = [{k: v for k, v in r.items() if k != 'path'} | dict(file=Path(r['path']).name) for r in receipt['libraries']]
    public['commands'] = [{k: v for k, v in c.items() if k != 'argv'} | dict(argvDisclosure='Exact argv stays in the private receipt; frozen collector constructs it.') for c in receipt['commands']]
    public['privateReceiptSha256'] = sha(capture / 'receipt.json')
    public['loadedOriginalClassMembersSha256'] = loaded
    public['limits'] = ['Original private static method under authored reflection, not full item property/bake/render execution.',
                        'Class loading is not initialization, method execution, or a complete dependency/effect closure.',
                        'Sorted integer-valued float inputs only; NaN, infinities, signed-zero and arbitrary fractional cases are unqualified.',
                        'Array readback equality is not a host-wide no-effects claim; tooling, JVM logs and capture files are written.',
                        'Observed duplicate indices belong to the recorded Java21 build. The Java17/21/25 API permits other matching duplicate indices.']
    (destination / 'receipt.json').write_text(json.dumps(public, indent=2) + '\n')
    print(json.dumps(dict(capture='evidence/' + capture.name, cases=76, loadedOriginalClasses=len(loaded))))


if __name__ == '__main__':
    main()
