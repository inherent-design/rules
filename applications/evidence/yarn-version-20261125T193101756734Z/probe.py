"""Owned offline workspace version decisions; no external packages, hooks or publication."""
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

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')


def image(project):
    result = {}
    for directory, names, files in os.walk(project, followlinks=False):
        names[:] = sorted(n for n in names if n != '.git')
        for name in sorted(names + files):
            p = Path(directory) / name
            if p.is_symlink():
                result[str(p.relative_to(project))] = dict(kind='link', target=os.readlink(p), mode=p.lstat().st_mode)
            elif p.is_file():
                raw = p.read_bytes()
                assert len(raw) < 1 << 20, 'Outside authored fixture capture bound'
                result[str(p.relative_to(project))] = dict(kind='file', sha256=sha(p), bytesHex=raw.hex(), mode=p.stat().st_mode,
                                                          mtimeNs=p.stat().st_mtime_ns)
    assert len(result) < 128
    return result


def main():
    assert sys.argv[1:] in [[], ['--initialized-check']]
    check_only = sys.argv[1:] == ['--initialized-check']
    pins = json.loads((ROOT / 'applications/sources/local-pins.json').read_text())['tools']
    for tool in ['node', 'yarn']:
        assert sha(Path(pins[tool]['path'])) == pins[tool]['sha256']
    ledger = ROOT / 'applications/sources/yarn-version-selections.json'
    for row in json.loads(ledger.read_text()):
        assert sha(ROOT / row['cache']) == row['sha256']
    run = ROOT / 'applications/evidence' / ('yarn-version-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    (run / 'probe.py').write_bytes(Path(__file__).read_bytes())
    work = Path(tempfile.mkdtemp(prefix='rules-yarn-version-', dir='/private/tmp'))
    for p in [work, *work.parents]:
        assert not any((p / n).exists() for n in ['.yarnrc.yml', 'package.json', 'yarn.lock'])
    for name in ['home', 'config', 'cache', 'state', 'data', 'tmp', 'projects', 'empty-hooks']:
        (work / name).mkdir()
    env = dict(PATH=str(Path(pins['node']['path']).parent) + ':/usr/bin:/bin', HOME=str(work / 'home'),
               TMPDIR=str(work / 'tmp'), XDG_CONFIG_HOME=str(work / 'config'), XDG_CACHE_HOME=str(work / 'cache'),
               XDG_STATE_HOME=str(work / 'state'), XDG_DATA_HOME=str(work / 'data'), LANG='en_US.UTF-8',
               YARN_ENABLE_TELEMETRY='0', YARN_ENABLE_NETWORK='0', YARN_ENABLE_COLORS='0',
               YARN_ENABLE_SCRIPTS='0', YARN_ENABLE_IMMUTABLE_INSTALLS='0', YARN_GLOBAL_FOLDER=str(work / 'data/yarn'),
               COREPACK_ENABLE_NETWORK='0', HTTP_PROXY='http://127.0.0.1:9', HTTPS_PROXY='http://127.0.0.1:9',
               ALL_PROXY='http://127.0.0.1:9', NO_PROXY='', DO_NOT_TRACK='1', MISE_SKIP_RESHIM='1',
               GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null', GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0',
               GIT_AUTHOR_NAME='Rules fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
               GIT_COMMITTER_NAME='Rules fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')
    write(run / 'setup.json', dict(schema=1, mode='initialized-check' if check_only else 'initial', work=str(work), tools={n:pins[n] for n in ['node', 'yarn']}, environment=env,
          producerSha256=sha(run / 'probe.py'), sourceLedgerSha256=sha(ledger),
          scope='Disposable local workspace-only release decisions and offline materialization; scripts/network disabled. No external registry packages, user Git/identity/hooks, publication, full-semver or crash/concurrent-writer qualification.'))
    rows, setup_git = [], []

    def git(project, args):
        cmd = ['/usr/bin/git', '-c', 'core.hooksPath=' + str(work / 'empty-hooks'), '-c', 'commit.gpgSign=false', *args]
        r = subprocess.run(cmd, cwd=project, env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=10)
        setup_git.append(dict(project=str(project), argv=cmd, exitCode=r.returncode, stdout=r.stdout.decode(), stderr=r.stderr.decode()))
        write(run / 'git-setup.json', setup_git)
        assert r.returncode == 0
        return r.stdout.decode()

    def project_for(name, vcs=False):
        p = work / 'projects' / name
        write(p / 'package.json', dict(name='rules-version-root', private=True, packageManager='yarn@4.19.0', workspaces=['packages/*']))
        for name, version in [('alpha', '1.2.3'), ('beta', '2.0.0'), ('gamma', '3.0.0')]:
            obj = dict(name='rules-version-' + name, version=version)
            if name != 'alpha':
                dep, rng = ('alpha', '^1.2.3') if name == 'beta' else ('beta', '~2.0.0')
                obj['dependencies'] = {'rules-version-' + dep:'workspace:' + rng}
            write(p / 'packages' / name / 'package.json', obj)
            (p / 'packages' / name / 'index.js').write_text('module.exports = "owned ' + name + '";\n')
        (p / '.yarnrc.yml').write_text('enableNetwork: false\nenableScripts: false\nenableTelemetry: false\nnodeLinker: node-modules\nenableGlobalCache: false\nchangesetBaseRefs: [main]\n')
        (p / 'yarn.lock').write_text('# Owned initial project marker; no external resolutions.\n')
        if vcs:
            git(p, ['init', '-b', 'main'])
            git(p, ['add', '--all'])
            git(p, ['commit', '-m', 'Owned fixture baseline'])
            git(p, ['checkout', '-b', 'study'])
            (p / 'packages/alpha/index.js').write_text('module.exports = "owned alpha changed";\n')
        return p

    def vcs_image(project):
        if not (project / '.git').exists():
            return None
        # Optional locks are disabled so the observer does not refresh the index.
        return dict(head=subprocess.check_output(['/usr/bin/git', 'rev-parse', 'HEAD'],cwd=project,env=env,text=True).strip(),
                    indexSha256=sha(project / '.git/index'),
                    status=subprocess.check_output(['/usr/bin/git', 'status', '--porcelain=v1', '--untracked-files=all'],cwd=project,env=env,text=True))

    def command(label, project, workspace, args, expected=0, required_text=None):
        cwd = project / 'packages' / workspace if workspace else project
        before, git_before = image(project), vcs_image(project)
        argv = [pins['node']['path'], pins['yarn']['path'], *args]
        start = time.monotonic()
        child = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timed = False
        try:
            out, err = child.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            timed = True; os.killpg(child.pid, signal.SIGTERM)
            try:
                out, err = child.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL); out, err = child.communicate()
        try:
            os.killpg(child.pid, 0); absent = False
        except ProcessLookupError:
            absent = True
        for stream, raw in [('stdout',out),('stderr',err)]:
            (run / (label + '.' + stream)).write_bytes(raw)
        row = dict(id=label, project=str(project), workspace=workspace, argv=argv, exitCode=child.returncode,
                   timedOut=timed, processGroupAbsent=absent, seconds=time.monotonic()-start,
                   before=before, after=image(project), gitBefore=git_before, gitAfter=vcs_image(project),
                   streams={s:sha(run / (label + '.' + s)) for s in ['stdout','stderr']})
        rows.append(row); write(run / 'commands.json',rows)
        print(label, child.returncode, flush=True)
        assert not timed and absent and child.returncode == expected, (label,err[-1500:],out[-1500:])
        if required_text is not None:
            assert required_text in (out + err).decode(), (label,required_text,out[-1500:])

    complete = False
    try:
        if check_only:
            p = project_for('initialized-vcs-check')
            command('initialize-local-workspaces',p,None,['install','--mode=skip-build'])
            git(p, ['init', '-b', 'main'])
            git(p, ['add', '--all'])
            git(p, ['commit', '-m', 'Owned initialized fixture baseline'])
            git(p, ['checkout', '-b', 'study'])
            (p / 'packages/alpha/index.js').write_text('module.exports = "owned alpha changed";\n')
            command('check-undecided',p,None,['version','check'],1,required_text='has been modified but doesn')
            command('record-changed',p,'alpha',['version','patch','--deferred'])
            command('check-dependent-undecided',p,None,['version','check'],1,required_text='which is planned for release')
            command('decline-dependent',p,'beta',['version','decline','--deferred'])
            command('check-complete',p,None,['version','check'])
        else:
            for name in ['alpha','beta','gamma']:
                p = project_for('scope-' + name)
                command('scope-' + name, p, name, ['version','patch','--recursive','--dry-run','--json'])
            p = project_for('deferred')
            command('record-alpha',p,'alpha',['version','minor','--deferred'])
            command('record-beta',p,'beta',['version','patch','--deferred'])
            command('preview-alpha',p,'alpha',['version','apply','--dry-run','--json'])
            command('apply-alpha',p,'alpha',['version','apply','--json'])
            command('apply-all',p,None,['version','apply','--all','--json'])
            command('apply-again',p,None,['version','apply','--all','--json'])
            p = project_for('downgrade')
            command('refuse-lower-record',p,'alpha',['version','1.1.0','--deferred'],1)
            command('force-lower-record',p,'alpha',['version','1.1.0','--deferred','--force'])
            command('refuse-lower-apply',p,'alpha',['version','apply','--json'],1)
            command('force-lower-apply',p,'alpha',['version','apply','--force','--json'])
            p = project_for('vcs-check',vcs=True)
            command('check-undecided',p,None,['version','check'],1)
            command('record-changed',p,'alpha',['version','patch','--deferred'])
            command('check-dependent-undecided',p,None,['version','check'],1)
            command('decline-dependent',p,'beta',['version','decline','--deferred'])
            command('check-complete',p,None,['version','check'])
        complete = True
    finally:
        processes=subprocess.check_output(['ps','-axo','pid=,args='],text=True).splitlines()
        matches=[line.strip() for line in processes if str(work) in line]
        allocation=subprocess.check_output(['/usr/bin/du','-sk',str(work)],text=True).split()[0]
        write(run / 'receipt.json',dict(schema=1,complete=complete,commands=len(rows),work=str(work),workPathProcessMatches=matches,
              allRecordedGroupsAbsent=all(r['processGroupAbsent'] for r in rows),privateAllocatedKiB=int(allocation),
              scope='Native workspace version decisions, selected records/application/check effects; no global install, registry publication, hook execution, broad graph/semver or crash safety claim.'))
        print(json.dumps(dict(capture=str(run.relative_to(ROOT)),complete=complete,commands=len(rows),work=str(work))))


if __name__ == '__main__':
    main()
