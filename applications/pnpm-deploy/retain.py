"""Freeze still-retained owned manifests only after matching native snapshots."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'applications/evidence/pnpm-deploy-20261125T152000035565Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    receipt = json.loads((RUN / 'receipt.json').read_text())
    assert receipt['complete'] and receipt['externalRestored']
    work = Path(receipt['work'])
    assert work.parent == Path('/private/tmp') and work.name.startswith('rules-pnpm-deploy-')
    source_snapshot = json.loads((RUN / 'source-inputs.json').read_text())
    source = {}
    for path, item in source_snapshot.items():
        if item['kind'] == 'file':
            original = work / 'project/packages' / path
            assert sha(original) == item['sha256']
            source[path] = original.read_text()
    output = {}
    for case in receipt['cases']:
        target = Path(case['target'])
        assert target.is_relative_to(work)
        if case['id'] == 'unsafe-root':
            continue  # Its root changed later through subsequent owned target creation.
        entries = {}
        for path, item in case['afterTarget'].items():
            original = target / path
            if item['kind'] == 'file':
                assert sha(original) == item['sha256'], (case['id'], path)
                if path.endswith(('package.json', 'pnpm-lock.yaml', 'pnpm-workspace.yaml')):
                    entries[path] = original.read_text()
            if item['kind'] == 'symlink':
                assert original.is_symlink() and str(original.readlink()) == item['target']
        output[case['id']] = entries
    link = work / 'project/through-link'
    assert link.is_symlink() and link.readlink() == work / 'outside-occupied'
    result = dict(schema=1, sourcePackageText=source, targetMetadataText=output,
        retainedLink=dict(path=str(link), target=str(link.readlink())),
        attribution='Supplemental readback after collection;all selected bytes matched the prior recorded SHA256s. Does not repeat a deploy or overwrite original observations.')
    destination = RUN / 'retained-metadata.json'
    assert not destination.exists()
    destination.write_text(json.dumps(result, indent=2) + '\n')
    alias_run = ROOT / 'applications/evidence/pnpm-deploy-alias-20261125T152635252659Z'
    alias = json.loads((alias_run / 'receipt.json').read_text())
    final = alias['cases'][-1]
    original = Path(alias['work']) / 'project/packages/app/package.json'
    assert sha(original) == final['sourceSnapshot']['package.json']['sha256']
    saved = alias_run / 'postimage-package.json'
    assert not saved.exists()
    saved.write_bytes(original.read_bytes())
    print('Verified and retained', len(source), 'source files and', sum(len(x) for x in output.values()), 'target metadata files')


if __name__ == '__main__':
    main()
