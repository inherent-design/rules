"""Owner-run local package contents comparison; no upload or archive extraction."""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def image(root):
    files = {}
    for p in sorted(root.rglob('*')):
        name = str(p.relative_to(root))
        if p.is_symlink():
            files[name] = dict(kind='symlink', target=os.readlink(p), mode=p.lstat().st_mode)
        elif p.is_file():
            files[name] = dict(kind='file', sha256=sha(p), mode=p.stat().st_mode)
    return files


def main():
    pins = json.loads((ROOT / 'applications/sources/local-pins.json').read_text())['tools']
    for name in ['node', 'npm', 'pnpm', 'yarn']:
        assert sha(Path(pins[name]['path'])) == pins[name]['sha256']
    ledger = ROOT / 'applications/sources/js-package-contents-selections.json'
    for row in json.loads(ledger.read_text()):
        assert sha(ROOT / row['cache']) == row['sha256']
    run = ROOT / 'applications/evidence' / ('js-package-contents-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    (run / 'probe.py').write_bytes(Path(__file__).read_bytes())
    work = Path(tempfile.mkdtemp(prefix='rules-js-package-contents-', dir='/private/tmp'))
    for p in [work, *work.parents]:
        assert not any((p / name).exists() for name in ['.npmrc', '.yarnrc.yml', 'pnpm-workspace.yaml'])
    write(run / 'setup.json', dict(schema=1, work=str(work), tools={n: pins[n] for n in ['node', 'npm', 'pnpm', 'yarn']},
          producerSha256=sha(run / 'probe.py'), sourceLedgerSha256=sha(ledger),
          limits='Generated source-only packages and owned link targets; no hooks/dependencies, upload, archive extraction, install or outside fixture reads.'))
    rows, cases = [], []
    def command(label, argv, cwd, env):
        started = time.monotonic()
        child = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timed = False
        try:
            out, err = child.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            timed = True
            os.killpg(child.pid, signal.SIGTERM)
            try:
                out, err = child.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                out, err = child.communicate()
        try:
            os.killpg(child.pid, 0)
            absent = False
        except ProcessLookupError:
            absent = True
        for stream, raw in [('stdout', out), ('stderr', err)]:
            (run / (label + '.' + stream)).write_bytes(raw)
        row = dict(id=label, argv=argv, cwd=str(cwd), exitCode=child.returncode,
                   processGroupAbsent=absent, timedOut=timed, seconds=time.monotonic() - started,
                   streams={s: sha(run / (label + '.' + s)) for s in ['stdout', 'stderr']})
        rows.append(row)
        write(run / 'commands.json', rows)
        assert not timed and absent and child.returncode == 0, (label, child.returncode, err[-2400:])
    try:
        for manager in ['npm', 'pnpm', 'yarn']:
            base = work / manager
            for name in ['home', 'config', 'cache', 'state', 'data', 'tmp']:
                (base / name).mkdir(parents=True)
            (base / 'config/user.npmrc').write_text('registry=http://127.0.0.1:9\nfetch-retries=0\noffline=true\nupdate-notifier=false\n')
            (base / 'config/global.npmrc').write_text('')
            env = dict(PATH=str(Path(pins['node']['path']).parent) + ':/usr/bin:/bin', HOME=str(base / 'home'),
                       TMPDIR=str(base / 'tmp'), XDG_CONFIG_HOME=str(base / 'config'), XDG_CACHE_HOME=str(base / 'cache'),
                       XDG_DATA_HOME=str(base / 'data'), LANG='en_US.UTF-8', COREPACK_ENABLE_NETWORK='0',
                       NPM_CONFIG_USERCONFIG=str(base / 'config/user.npmrc'), NPM_CONFIG_GLOBALCONFIG=str(base / 'config/global.npmrc'),
                       NPM_CONFIG_CACHE=str(base / 'cache/npm'), NPM_CONFIG_REGISTRY='http://127.0.0.1:9',
                       NPM_CONFIG_OFFLINE='true', NPM_CONFIG_UPDATE_NOTIFIER='false', NPM_CONFIG_FETCH_RETRIES='0',
                       PNPM_CONFIG_STATE_DIR=str(base / 'state'), PNPM_CONFIG_FETCH_RETRIES='0',
                       YARN_ENABLE_NETWORK='false', YARN_ENABLE_TELEMETRY='0', YARN_ENABLE_IMMUTABLE_INSTALLS='false',
                       HTTP_PROXY='http://127.0.0.1:9', HTTPS_PROXY='http://127.0.0.1:9', ALL_PROXY='http://127.0.0.1:9',
                       NO_PROXY='', DO_NOT_TRACK='1', MISE_SKIP_RESHIM='1')
            prefix = [pins['node']['path'], pins['yarn']['path']] if manager == 'yarn' else [pins[manager]['path']]
            command(manager + '-help', prefix + ['pack', '--help'], base, env)
            for case in ['baseline', 'gitignore-fallback', 'npmignore-overrides', 'files-root', 'files-nested', 'symlinks']:
                label = manager + '-' + case
                case_root = base / case
                project, output = case_root / 'project', case_root / 'output'
                for directory in [project / 'src', project / 'bin', project / 'dist', output]:
                    directory.mkdir(parents=True)
                manifest = dict(name='rules-pack-contents-fixture', version='1.0.0', private=True,
                                main='src/main.js', bin={'fixture': 'bin/run.js'}, license='UNLICENSED')
                if case.startswith('files-') or case == 'symlinks':
                    manifest['files'] = ['dist']
                authored = {'package.json': json.dumps(manifest, indent=2) + '\n',
                            'src/main.js': 'module.exports = "owned main fixture";\n',
                            'bin/run.js': '#!/usr/bin/env node\nconsole.log("owned executable fixture");\n',
                            'dist/public.js': 'module.exports = "owned selected fixture";\n',
                            'dist/private.txt': 'owned nested exclusion marker; not a secret\n',
                            'ordinary-note.txt': 'owned root exclusion marker; not a secret\n',
                            'README.md': 'Owned package contents fixture.\n', 'LICENSE': 'UNLICENSED fixture material.\n'}
                if case in ['gitignore-fallback', 'npmignore-overrides']:
                    authored['.gitignore'] = 'ordinary-note.txt\n'
                if case == 'npmignore-overrides':
                    authored['.npmignore'] = ''
                if case.startswith('files-'):
                    authored['.npmignore'] = 'dist/**\nsrc/**\nbin/**\nREADME.md\nLICENSE\n'
                if case == 'files-nested':
                    authored['dist/.npmignore'] = 'private.txt\n'
                if manager == 'yarn':
                    authored['.yarnrc.yml'] = 'nodeLinker: node-modules\nenableNetwork: false\nenableTelemetry: false\nenableGlobalCache: false\n'
                for name, text in authored.items():
                    (project / name).write_text(text)
                (project / 'bin/run.js').chmod(0o755)
                outside = case_root / 'outside.txt'
                outside.write_text('owned outside-project link target; not a secret\n')
                if case == 'symlinks':
                    (project / 'dist/internal-link.txt').symlink_to('public.js')
                    (project / 'dist/external-link.txt').symlink_to('../../outside.txt')
                    (project / 'dist/missing-link.txt').symlink_to('missing-target.txt')
                before = image(project)
                outside_before = sha(outside)
                write(run / (label + '-input.json'), dict(manifest=manifest, authored=authored, before=before,
                      outsideSha256=outside_before, environment=env))
                args = ['pack', '--json', '--pack-destination', str(output), '--ignore-scripts'] if manager != 'yarn' else ['pack', '--json', '--out', str(output / 'package.tgz')]
                command(label, prefix + args, project, env)
                after = image(project)
                assert before == after and sha(outside) == outside_before
                archives = list(output.glob('*.tgz'))
                assert len(archives) == 1
                raw = archives[0].read_bytes()
                assert len(raw) <= 1 << 20
                (run / (label + '.tgz')).write_bytes(raw)
                members = []
                with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tar:
                    entries = tar.getmembers()
                    assert len(entries) < 64 and sum(m.size for m in entries) < 1 << 20
                    for entry in entries:
                        assert entry.isfile() or entry.isdir() or entry.issym(), entry.name
                        assert entry.name.startswith('package/') and '..' not in Path(entry.name).parts
                        body = tar.extractfile(entry).read() if entry.isfile() else b''
                        members.append(dict(path=entry.name, kind='file' if entry.isfile() else 'symlink' if entry.issym() else 'directory',
                                            link=entry.linkname, mode=entry.mode, bytes=entry.size,
                                            sha256=hashlib.sha256(body).hexdigest() if entry.isfile() else None))
                cases.append(dict(id=label, manager=manager, case=case, authoredBefore=before, authoredAfter=after,
                                  outsideUnchanged=True, archiveSha256=hashlib.sha256(raw).hexdigest(), archiveBytes=len(raw), members=members))
                write(run / 'observed.json', dict(schema=1, cases=cases))
        ps = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,command='], text=True)
        hits = [s for s in ps.splitlines() if str(work) in s and int(s.split()[0]) not in [os.getpid(), os.getppid()]]
        assert not hits
        write(run / 'receipt.json', dict(schema=1, complete=True, commands=len(rows), cases=len(cases), work=str(work),
              workPathProcessMatches=hits, allRecordedGroupsAbsent=True,
              privateAllocatedKiB=int(subprocess.check_output(['du', '-sk', str(work)], text=True).split()[0]),
              scope='Native local packs with authored selection rules and owned internal/external/missing symlinks; no registry, hooks, install, extraction or general glob/consumer policy qualification.'))
    except BaseException as error:
        write(run / 'incomplete.json', dict(schema=1, work=str(work), commands=len(rows), cases=len(cases),
              errorType=type(error).__name__, message=str(error)))
        raise
    print(json.dumps(dict(run=str(run.relative_to(ROOT)), commands=len(rows), cases=len(cases))))


if __name__ == '__main__':
    main()
