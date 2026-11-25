#!/usr/bin/env python3
"""Export authored validator observations and identities, without tool/schema payloads."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    capture = args.capture.resolve()
    r = json.loads((capture / 'receipt.json').read_text())
    assert r['nativeClientOperations'] == r['subprocesses'] == 0 and r['allInstancesUnchanged']
    for name, key in [('observed.json', 'observedSha256'), ('sources.json', 'sourcesSha256'),
                      ('schema_probe.py', 'producerSha256'), ('schema-cases.json', 'requestsSha256'),
                      ('tool-inputs.json', 'wheelReceiptSha256')]:
        assert sha(capture / name) == r[key]
    destination = HERE / 'evidence' / capture.name
    destination.mkdir(parents=True, exist_ok=False)
    for name in ['receipt.json', 'observed.json', 'sources.json', 'schema_probe.py', 'schema-cases.json', 'tool-inputs.json']:
        shutil.copyfile(capture / name, destination / name)
    print(json.dumps(dict(capture=str(destination.relative_to(HERE)), validatorObservations=r['cases'], nativeClientOperations=0)))


if __name__ == '__main__':
    main()
