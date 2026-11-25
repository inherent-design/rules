"""Focused npm 12 getter comparison using the isolated official tool, never host npm."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

from probe import base_manifest, save_initial, image

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, value):
    p.write_text(json.dumps(value, indent=2) + '\n')


def main():
    assert sys.argv[1:] in [[], ['--paired-documents']]
    paired = sys.argv[1:] == ['--paired-documents']
    pin_path = ROOT / 'applications/sources/npm-manifest-npm12-tool.json'
    pin = json.loads(pin_path.read_text())
    local_pins = json.loads((ROOT / 'applications/sources/local-pins.json').read_text())['tools']
    node = local_pins['node']
    legacy = local_pins['npm']
    if paired:
        assert sha(Path(legacy['path'])) == legacy['sha256']
    assert sha(Path(node['path'])) == node['sha256']
    tool = ROOT / pin['toolCache']
    assert sha(tool / 'tool-acquisition.json') == pin['acquisitionReceiptSha256']
    assert sha(tool / 'npm.tgz') == pin['archiveSha256']
    entry = tool / pin['entryRelative']
    assert sha(entry) == pin['entrySha256']
    for p in pin['selectedSources']:
        assert sha(tool / 'package' / p['path']) == p['sha256']
    run = ROOT / 'applications/evidence' / (('npm-manifest-document-' if paired else 'npm-manifest-latest-') + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    (run / 'probe.py').write_bytes(Path(__file__).read_bytes())
    (run / 'fixture.py').write_bytes((ROOT / 'applications/npm-manifest/probe.py').read_bytes())
    (run / 'acquisition-producer.py').write_bytes((tool / 'acquisition-producer.py').read_bytes())
    # Keep only the acquisition summary publicly; the full vendor-file inventory stays with the tool.
    write(run / 'tool-pin.json', pin)
    work = Path(tempfile.mkdtemp(prefix='rules-npm-manifest-latest-', dir='/private/tmp'))
    for p in [work, *work.parents]:
        assert not any((p / n).exists() for n in ['.npmrc', 'package.json'])
    for name in ['home', 'config', 'cache', 'tmp', 'global', 'project']:
        (work / name).mkdir()
    (work / 'config/user.npmrc').write_text('registry=http://127.0.0.1:9\noffline=true\nfetch-retries=0\nupdate-notifier=false\n')
    (work / 'config/global.npmrc').write_text('')
    project = work / 'project'
    manifest = base_manifest()
    manifest['custom'].update(zero=0, text='', truth=True)
    save_initial(project / 'package.json', manifest)
    env = dict(PATH=str(Path(node['path']).parent) + ':/usr/bin:/bin', HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'),
               NPM_CONFIG_USERCONFIG=str(work / 'config/user.npmrc'), NPM_CONFIG_GLOBALCONFIG=str(work / 'config/global.npmrc'),
               NPM_CONFIG_CACHE=str(work / 'cache'), NPM_CONFIG_PREFIX=str(work / 'global'), NPM_CONFIG_OFFLINE='true',
               NPM_CONFIG_FETCH_RETRIES='0', NPM_CONFIG_UPDATE_NOTIFIER='false', NPM_CONFIG_COLOR='false',
               HTTP_PROXY='http://127.0.0.1:9', HTTPS_PROXY='http://127.0.0.1:9', ALL_PROXY='http://127.0.0.1:9',
               NO_PROXY='', LANG='en_US.UTF-8', DO_NOT_TRACK='1', MISE_SKIP_RESHIM='1')
    write(run / 'setup.json', dict(schema=1, mode='paired-documents' if paired else 'focused-latest', legacyNpm=legacy if paired else None, version=pin['version'], gitHead=pin['gitHead'], tool=str(tool),
          work=str(work), environment=env, node=node, entry=str(entry), entrySha256=sha(entry),
          producerSha256=sha(run / 'probe.py'), fixtureSha256=sha(run / 'fixture.py'),
          acquisitionProducerSha256=sha(run / 'acquisition-producer.py'), toolPinSha256=sha(pin_path),
          acquisitionReceiptSha256=pin['acquisitionReceiptSha256'], manifest=manifest,
          scope='Focused isolated npm12 version/query-mode check, no legacy-matrix rerun or host tool update.'))
    rows = []
    def command(label, args, expected=0, prefix=None):
        before = image(project)
        argv = (prefix or [node['path'], str(entry)]) + ['--prefix', str(project), *args]
        start = time.monotonic()
        child = subprocess.Popen(argv, cwd=project, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, start_new_session=True)
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
        after = image(project)
        row = dict(id=label, argv=argv, exitCode=child.returncode, processGroupAbsent=absent, timedOut=timed,
                   seconds=time.monotonic() - start, before=before, after=after,
                   streams={s: sha(run / (label + '.' + s)) for s in ['stdout', 'stderr']})
        rows.append(row)
        write(run / 'commands.json', rows)
        assert absent and not timed and child.returncode == expected and before == after, (label, child.returncode, err[-2000:])
    try:
        if paired:
            command('npm11-document', ['pkg', 'get', '--json'], prefix=[legacy['path']])
            command('npm12-document', ['pkg', 'get', '--json'])
        else:
            command('version', ['--version'])
            assert (run / 'version.stdout').read_text().strip() == pin['version']
            for label, path in [('false', 'custom.flag'), ('null', 'custom.nil'), ('zero', 'custom.zero'), ('empty-string', 'custom.text'),
                                ('empty-array', 'custom.empty'), ('single-array', 'custom.one'), ('many-array', 'custom.many'), ('missing', 'custom.missing')]:
                command('json-' + label, ['pkg', 'get', path, '--json'])
            command('json-null-child', ['pkg', 'get', 'custom.nil.child', '--json'], 1)
            for label, path in [('false', 'custom.flag'), ('single-array', 'custom.one'), ('null', 'custom.nil')]:
                command('raw-' + label, ['pkg', 'get', path])
        for p in pin['selectedSources']:
            assert sha(tool / 'package' / p['path']) == p['sha256']
        ps = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,command='], text=True)
        hits = [s for s in ps.splitlines() if str(work) in s and int(s.split()[0]) not in [os.getpid(), os.getppid()]]
        assert not hits
        write(run / 'receipt.json', dict(schema=1, complete=True, version=pin['version'], commands=len(rows),
              work=str(work), workPathProcessMatches=hits, allRecordedGroupsAbsent=True, authoredFilesUnchanged=True,
              privateAllocatedKiB=int(subprocess.check_output(['du', '-sk', str(work)], text=True).split()[0]),
              scope='Paired explicit-JSON full-document reads on pinned npm11 and isolated npm12;no host tool update or write.' if paired else 'Actual isolated npm12.2.3:9explicit-JSON and3default-text getter requests plus version. No install, hooks, workspace write/retry rerun, global tool update or whole-major conformance.'))
    except BaseException as error:
        write(run / 'incomplete.json', dict(schema=1, commands=len(rows), work=str(work), errorType=type(error).__name__, message=str(error)))
        raise
    print(json.dumps(dict(run=str(run.relative_to(ROOT)), version=pin['version'], commands=len(rows))))


if __name__ == '__main__':
    main()
