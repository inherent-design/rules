"""Read retained local package archives; execute only the two decision models."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import shutil

from observations import packets

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'applications/evidence/js-package-contents-20261125T181340790945Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())


def write(p, value):
    p.write_text(json.dumps(value, indent=2) + '\n')


def compare(actual, expected):
    assert actual == expected, 'Package contents differ from retained archive'


def main():
    receipt, setup = load(RUN / 'receipt.json'), load(RUN / 'setup.json')
    assert receipt['complete'] and receipt['commands'] == 21 and receipt['cases'] == 18
    assert receipt['allRecordedGroupsAbsent'] and not receipt['workPathProcessMatches']
    assert sha(RUN / 'probe.py') == setup['producerSha256']
    ledger = ROOT / 'applications/sources/js-package-contents-selections.json'
    context = ROOT / 'applications/sources/js-package-contents-link-context.json'
    assert sha(ledger) == setup['sourceLedgerSha256']
    assert sha(RUN / 'setup.json') == load(RUN / 'scope-qualification.json')['preservedOriginalSetupSha256']
    available, unavailable = [], []
    for item in load(ledger) + load(context):
        p = ROOT / item['cache']
        if not p.exists():
            unavailable.append(item['path'])
            continue
        raw = p.read_bytes()
        assert sha(p) == item['sha256']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == item['gitBlob']
        available.append(item['path'])
        if 'installedCorrespondence' in item:
            q = Path(item['installedCorrespondence']['path'])
            if q.exists():
                assert sha(q) == item['installedCorrespondence']['sha256'] == item['sha256']
    artifacts = {}
    for name, item in setup['tools'].items():
        p = Path(item['path'])
        artifacts[name] = 'unavailable'
        if p.exists():
            assert sha(p) == item['sha256']
            artifacts[name] = 'identity checked, not executed'
    rows = load(RUN / 'commands.json')
    assert len(rows) == 21 and len({r['id'] for r in rows}) == 21
    for row in rows:
        assert row['exitCode'] == 0 and row['processGroupAbsent'] and not row['timedOut']
        assert 'pack' in row['argv'] and not any(s in row['argv'] for s in ['publish', 'install'])
        for stream in ['stdout', 'stderr']:
            assert sha(RUN / (row['id'] + '.' + stream)) == row['streams'][stream]
    work = Path(receipt['work'])
    for case in load(RUN / 'observed.json')['cases']:
        request = load(RUN / (case['id'] + '-input.json'))
        assert not request['manifest'].get('scripts') and not request['manifest'].get('dependencies')
        project = work / case['manager'] / case['case'] / 'project'
        if project.exists():
            for path, old in request['before'].items():
                p = project / path
                if old['kind'] == 'symlink':
                    assert p.is_symlink() and os.readlink(p) == old['target'] and p.lstat().st_mode == old['mode']
                else:
                    assert not p.is_symlink() and sha(p) == old['sha256'] and p.stat().st_mode == old['mode']
            assert sha(project.parent / 'outside.txt') == request['outsideSha256']
    inputs, expected, archives = packets(RUN)
    assert len(inputs['cases']) == 177 and sum(a['selectedEntries'] for a in archives) == 134
    assert sum(a['symlinks'] for a in archives) == 5
    write(RUN / 'model-input.json', inputs)
    write(RUN / 'observed-model-values.json', expected)
    write(RUN / 'archive-checks.json', archives)
    proof = load(RUN / 'proof-gate.json')
    assert proof['observedExitCode'] == 0
    for p, digest in proof['sourceSha256'].items():
        assert sha(ROOT / p) == digest
    formal = ROOT / '.build/js-package-contents-formal'
    formal.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LEAN_PATH=str(formal), BEND_NO_TELEMETRY='1')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    command = [lean, '--run', 'applications/js-package-contents/ContentsCase.lean']
    actual = json.loads(subprocess.check_output(command + [str(RUN / 'model-input.json')], cwd=ROOT, env=env, text=True))
    compare(actual, expected)
    calls = []
    for row in inputs['cases']:
        args = [str(row['manager']) + 'n', str(row['kind']) + 'n']
        args += ['True{}' if row[k] else 'False{}' for k in ['globalExcluded', 'required', 'filesPresent', 'listed',
                 'npmPresent', 'npmMatch', 'gitMatch', 'nestedMatch']]
        calls.append('Bool.show(P.included(' + ','.join(args) + '))')
    target = formal / 'Replay.bend'
    target.write_text('import ../../applications/js-package-contents/Contents.bend as P\nimport Base\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ "\\n" ++ '.join(calls) + ' ++ "\\n")\n')
    result = subprocess.run([bend, str(target)], cwd=ROOT, env=env, text=True, capture_output=True, check=True)
    compare(result.stdout.splitlines(), [str(r['included']) for r in expected])
    controls = []
    for name, key in [('ignore-fallback-lost', 'npm-gitignore-fallback:ordinary-note.txt'),
                      ('empty-npmignore-does-not-replace', 'npm-npmignore-overrides:ordinary-note.txt'),
                      ('root-ignore-beats-files', 'pnpm-files-root:dist/public.js'),
                      ('nested-ignore-lost', 'yarn-files-nested:dist/private.txt'),
                      ('main-not-required', 'npm-files-root:src/main.js'),
                      ('npm-keeps-link', 'npm-symlinks:dist/internal-link.txt'),
                      ('pnpm-loses-dangling', 'pnpm-symlinks:dist/missing-link.txt'),
                      ('pnpm-keeps-external', 'pnpm-symlinks:dist/external-link.txt'),
                      ('yarn-drops-external', 'yarn-symlinks:dist/external-link.txt')]:
        changed = copy.deepcopy(expected)
        row = next(r for r in changed if r['id'] == key)
        row['included'] = not row['included']
        try:
            compare(actual, changed)
        except AssertionError:
            controls.append(name)
        else:
            raise AssertionError('Changed archive interpretation escaped')
    for label, change in [('schema', lambda d: d.update(schema=2)),
                          ('manager', lambda d: d['cases'][0].update(manager=3)),
                          ('link-class', lambda d: d['cases'][0].update(kind=4))]:
        changed = copy.deepcopy(inputs)
        change(changed)
        path = formal / (label + '.json')
        write(path, changed)
        result = subprocess.run(command + [str(path)], cwd=ROOT, env=env, text=True, capture_output=True)
        assert result.returncode == 2 and 'research' in result.stderr
        controls.append(label)
    first = load(RUN / 'observed.json')['cases'][0]
    with tempfile.TemporaryDirectory(prefix='archive-integrity-', dir=formal) as scratch:
        target_run = Path(scratch)
        write(target_run / 'observed.json', dict(cases=[first]))
        shutil.copy2(RUN / (first['id'] + '-input.json'), target_run / (first['id'] + '-input.json'))
        raw = bytearray((RUN / (first['id'] + '.tgz')).read_bytes())
        raw[0] ^= 1
        (target_run / (first['id'] + '.tgz')).write_bytes(raw)
        try:
            packets(target_run)
        except AssertionError as error:
            assert str(error) == 'Retained archive digest differs'
            controls.append('changed-archive-refused-before-decode')
        else:
            raise AssertionError('Changed archive escaped digest admission')
    files = [p for p in RUN.iterdir() if p.is_file() and p.name not in ['basis.json', 'conformance.json']]
    files += [ROOT / 'applications/js-package-contents' / n for n in
              ['probe.py', 'observations.py', 'conformance.py', 'Contents.lean', 'ContentsCase.lean', 'Contents.bend']]
    files += [ledger, context]
    write(RUN / 'basis.json', {str(p.relative_to(ROOT)): sha(p) for p in files})
    report = dict(schema=1, nativePacks=18, nativeCommands=21, filePredicates=177, archiveEntries=134, symlinks=5,
                  leanLaws=12, bendLaws=9, negativeControls=controls, availableSources=available,
                  unavailableSources=unavailable, artifacts=artifacts, basisFiles=len(files),
                  limits=['Literal fixture patterns and simple links are interpreted premises, not complete glob or filesystem traversal conformance.',
                          'Archive membership and link text do not establish safe extraction, consumer resolution, publication, or general host-read isolation.',
                          'No pack hooks, workspace ancestry/bundles, concurrent writer, upload, install, or other-platform qualification.'])
    write(RUN / 'conformance.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
