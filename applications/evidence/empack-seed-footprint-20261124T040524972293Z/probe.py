#!/usr/bin/env python3
"""Owner-run sparse seed observation study; private instances, no game launch."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[2]
    original = root / 'applications/evidence/empack-native-ownership-20261124T031930881554Z/work/releases/b'
    binary = Path('/Users/zer0cell/.local/bin/empack')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    if sha(binary) != '99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f':
        raise RuntimeError('Installed binary differs from the selected 0.8.8 fixture.')
    source = json.loads((original / 'release.json').read_text())
    if {f['destination']: f['policy'] for f in source['files']} != {'config/rules.txt': 'seed', 'payload.txt': 'managed'}:
        raise RuntimeError('Prepared release does not have the expected two-file inventory.')
    run = root / 'applications/evidence' / ('empack-seed-footprint-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'
    work.mkdir(parents=True, mode=0o700)
    for name in ['state', 'cache', 'config', 'home', 'instance', 'input']:
        (work / name).mkdir(mode=0o700)
    for p in original.rglob('*'):
        if p.is_symlink():
            raise RuntimeError('Source fixture contains a link.')
        target = work / 'input' / p.relative_to(original)
        if p.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif p.is_file():
            if p.stat().st_size > 1024 * 1024:
                raise RuntimeError('Unexpectedly large prepared input.')
            shutil.copyfile(p, target)
    manifest = work / 'input/release.json'
    release_id = sha(manifest)
    entrypoint = Path(__file__).read_bytes()
    (run / 'probe.py').write_bytes(entrypoint)
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(work / 'home'), 'XDG_CONFIG_HOME': str(work / 'config'),
           'XDG_DATA_HOME': str(work / 'home/data'), 'XDG_CACHE_HOME': str(work / 'cache'), 'LANG': 'en_US.UTF-8', 'NO_COLOR': '1'}
    commands = []

    def command(label, args):
        argv = [str(binary), '--state-dir', str(work / 'state'), '--cache-dir', str(work / 'cache'),
                '--workdir', str(work / 'instance'), '--color', 'never', '--yes', *args]
        result = subprocess.run(argv, cwd=work, env=env, input=b'', capture_output=True, timeout=30)
        (run / (label + '.stdout')).write_bytes(result.stdout)
        (run / (label + '.stderr')).write_bytes(result.stderr)
        commands.append({'label': label, 'argv': argv, 'exitCode': result.returncode,
                         'stdoutSha256': sha(run / (label + '.stdout')), 'stderrSha256': sha(run / (label + '.stderr'))})
        (run / 'progress.json').write_text(json.dumps(commands, indent=2) + '\n')
        return result

    result = command('install', ['instance', 'install', str(manifest), '--sha256', release_id])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors='replace'))
    seed = work / 'instance/game/config/rules.txt'
    logical_size = 8 * 1024 * 1024 * 1024 + 1
    with seed.open('r+b') as f:
        f.truncate(logical_size)
    before = seed.stat()
    allocated = before.st_blocks * 512
    # Never continue into a test with an unexpectedly allocated large payload.
    if allocated > 1024 * 1024:
        with seed.open('r+b') as f:
            f.truncate(0)
        raise RuntimeError('Fixture was not sparse; truncated owned test payload and stopped.')
    result = command('check-sparse-seed', ['instance', 'check', '--json'])
    checked = json.loads(result.stdout) if result.returncode == 0 else None
    preview = command('preview-sparse-seed', ['instance', 'install', str(manifest), '--sha256', release_id, '--dry-run'])
    after = seed.stat()
    observations = {'seedLogicalBytes': logical_size, 'seedAllocatedBytesBefore': allocated,
        'seedAllocatedBytesAfter': after.st_blocks * 512,
        'seedSizeUnchanged': before.st_size == after.st_size,
        'seedMtimeUnchanged': before.st_mtime_ns == after.st_mtime_ns,
        'checkExit': result.returncode, 'checkComplete': checked.get('complete') if checked else None,
        'previewExit': preview.returncode, 'previewDiagnostic': preview.stderr.decode(errors='replace')}
    # Restore only this fixture's own seed after observing it. Keep native state,
    # descriptors, commands, and raw outputs; no recovery records are removed.
    with seed.open('wb') as f:
        f.write(b'owned seed fixture restored\n')
    repaired_check = command('check-after-restoring-small-seed', ['instance', 'check', '--json'])
    observations['restoredSeedCheckExit'] = repaired_check.returncode
    report = {'schema': 1, 'kind': 'Native seed observation footprint, not a preservation implementation fix',
        'binarySha256': sha(binary), 'releaseId': release_id, 'probeSha256': hashlib.sha256(entrypoint).hexdigest(),
        'observations': observations, 'commands': commands,
        'limits': ['One 0.8.8 macOS binary and one selected ordinary seed;no claim about every consumer or world group.',
            'Sparse metadata stress input;not a representative game configuration or a performance benchmark.',
            'No network or process tracing was collected;the selected workflow uses local snapshots and launches no game.']}
    (run / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'run': str(run), **observations}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
