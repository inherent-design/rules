"""Owner-run local npm document edits; no scripts, install, or registry operation."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def base_manifest():
    return dict(name='rules-manifest-fixture', version='1.0.0', private=True,
                custom=dict(flag=False, nil=None, empty=[], one=['one'], many=['a', 'b'],
                            scalar='fixed', first='original'),
                contributors=[dict(name='First'), dict(name='Second'), dict(name='Third')],
                exports={'.': dict(default='./index.js')}, scripts=dict(test='echo owned declarative marker'))


def save_initial(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent='\t') + '\n').replace('\n', '\r\n').encode())


def image(project):
    result = {}
    for p in sorted(project.rglob('package.json')):
        raw = p.read_bytes()
        result[str(p.relative_to(project))] = dict(sha256=hashlib.sha256(raw).hexdigest(),
                 bytesHex=raw.hex(), semantic=json.loads(raw), mode=p.stat().st_mode,
                 mtimeNs=p.stat().st_mtime_ns)
    return result


def main():
    pins = json.loads((ROOT / 'applications/sources/local-pins.json').read_text())['tools']
    for name in ['node', 'npm']:
        assert sha(Path(pins[name]['path'])) == pins[name]['sha256']
    ledger = ROOT / 'applications/sources/npm-manifest-selections.json'
    for row in json.loads(ledger.read_text()):
        assert sha(ROOT / row['cache']) == row['sha256']
        if 'installedCorrespondence' in row:
            assert sha(Path(row['installedCorrespondence']['path'])) == row['sha256']
    run = ROOT / 'applications/evidence' / ('npm-manifest-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    (run / 'probe.py').write_bytes(Path(__file__).read_bytes())
    work = Path(tempfile.mkdtemp(prefix='rules-npm-manifest-', dir='/private/tmp'))
    for p in [work, *work.parents]:
        assert not any((p / name).exists() for name in ['.npmrc', 'package.json'])
    for name in ['home', 'config', 'cache', 'tmp', 'projects', 'global']:
        (work / name).mkdir()
    (work / 'config/user.npmrc').write_text('registry=http://127.0.0.1:9\noffline=true\nfetch-retries=0\nupdate-notifier=false\n')
    (work / 'config/global.npmrc').write_text('')
    env = dict(PATH=str(Path(pins['node']['path']).parent) + ':/usr/bin:/bin', HOME=str(work / 'home'),
               TMPDIR=str(work / 'tmp'), LANG='en_US.UTF-8', NPM_CONFIG_USERCONFIG=str(work / 'config/user.npmrc'),
               NPM_CONFIG_GLOBALCONFIG=str(work / 'config/global.npmrc'), NPM_CONFIG_CACHE=str(work / 'cache'),
               NPM_CONFIG_PREFIX=str(work / 'global'), NPM_CONFIG_OFFLINE='true', NPM_CONFIG_FETCH_RETRIES='0',
               NPM_CONFIG_UPDATE_NOTIFIER='false', HTTP_PROXY='http://127.0.0.1:9', HTTPS_PROXY='http://127.0.0.1:9',
               ALL_PROXY='http://127.0.0.1:9', NO_PROXY='', DO_NOT_TRACK='1', MISE_SKIP_RESHIM='1')
    write(run / 'setup.json', dict(schema=1, work=str(work), environment=env,
          tools={n: pins[n] for n in ['node', 'npm']}, sourceLedgerSha256=sha(ledger), producerSha256=sha(run / 'probe.py'),
          limits='Owned JSON documents, direct argv, isolated configuration; no install, publish, script execution, general host-I/O tracing or write-failure/crash qualification.'))
    rows = []
    def project_for(label):
        project = work / 'projects' / label
        save_initial(project / 'package.json', base_manifest())
        return project
    def command(label, project, args, allowed=(0,)):
        before = image(project)
        argv = [pins['npm']['path'], '--prefix', str(project), 'pkg', *args]
        started = time.monotonic()
        child = subprocess.Popen(argv, cwd=project, env=env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timed = False
        try:
            out, err = child.communicate(timeout=25)
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
        row = dict(id=label, project=str(project), argv=argv, allowedExitCodes=list(allowed),
                   exitCode=child.returncode, processGroupAbsent=absent, timedOut=timed,
                   seconds=time.monotonic() - started, before=before, after=image(project),
                   streams={s: sha(run / (label + '.' + s)) for s in ['stdout', 'stderr']})
        rows.append(row)
        write(run / 'commands.json', rows)
        assert not timed and absent and child.returncode in allowed, (label, child.returncode, err[-2000:])
    try:
        for label, path, allowed in [
            ('get-missing', 'custom.missing', (0,)), ('get-null', 'custom.nil', (0,)),
            ('get-null-child', 'custom.nil.child', (1,)), ('get-empty', 'custom.empty', (0,1)),
            ('get-single', 'custom.one', (0,)), ('get-many', 'custom.many', (0,)),
            ('get-parent', 'custom', (0,)), ('get-array-projection', 'contributors.name', (0,)),
            ('get-literal-dot', 'exports[.].default', (0,)),
        ]:
            command(label, project_for(label), ['get', path], allowed)
        for label, args, allowed in [
            ('set-string', ['set', 'custom.flag=true'], (0,)),
            ('set-json', ['set', 'custom.flag=true', '--json'], (0,)),
            ('noop', ['set', 'custom.flag=false', '--json'], (0,)),
            ('invalid-identity', ['set', 'name=not a package name!', 'version=not-semver'], (0,)),
            ('late-override-refusal', ['set', 'custom.first=changed', 'custom.scalar.child=blocked'], (1,)),
            ('late-json-refusal', ['set', 'custom.first="changed"', 'custom.next={', '--json'], (1,)),
            ('late-script-type-refusal', ['set', 'custom.first="changed"', 'scripts.test=true', '--json'], (1,)),
            ('forbidden-key', ['set', 'custom.__proto__.owned=true'], (1,)),
            ('delete-array-index', ['delete', 'contributors[0]'], (0,)),
            ('force-conversion', ['set', 'custom.scalar.child=changed', '--force'], (0,)),
        ]:
            command(label, project_for(label), args, allowed)
        project = project_for('append-repeated')
        command('append-first', project, ['set', 'contributors[].name=Appended'])
        command('append-repeated', project, ['set', 'contributors[].name=Appended'])
        project = work / 'projects/workspaces'
        save_initial(project / 'package.json', dict(name='rules-manifest-root', private=True, workspaces=['alpha','omega']))
        save_initial(project / 'alpha/package.json', dict(name='rules-manifest-alpha', version='1.0.0', private=True, custom={}))
        save_initial(project / 'omega/package.json', dict(name='rules-manifest-omega', version='1.0.0', private=True, custom='fixed'))
        command('workspace-partial', project, ['set', 'custom.mode=changed', '--workspaces'], (1,))
        command('workspace-readback', project, ['get', 'custom', '--workspaces'])
        command('global-refusal', project_for('global-refusal'), ['get', 'name', '--global'], (1,))
        ps = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,command='], text=True)
        hits = [s for s in ps.splitlines() if str(work) in s and int(s.split()[0]) not in [os.getpid(), os.getppid()]]
        assert not hits
        write(run / 'receipt.json', dict(schema=1, complete=True, commands=len(rows), work=str(work),
              workPathProcessMatches=hits, allRecordedGroupsAbsent=True,
              privateAllocatedKiB=int(subprocess.check_output(['du', '-sk', str(work)], text=True).split()[0]),
              scope='Native local manifest query/edit/validation and sequential workspace partial effects on pinned npm;no install, scripts, publication, crash, save I/O failure or global transaction guarantee.'))
    except BaseException as error:
        write(run / 'incomplete.json', dict(schema=1, commands=len(rows), work=str(work), errorType=type(error).__name__, message=str(error)))
        raise
    print(json.dumps(dict(run=str(run.relative_to(ROOT)), commands=len(rows))))


if __name__ == '__main__':
    main()
