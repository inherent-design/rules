"""One owned case-alias target control; preserve source preimages and terminal effects."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile

from probe import snapshot

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    pins = json.loads((ROOT / 'applications/sources/local-pins.json').read_text())['tools']
    for key in ['pnpm', 'node']:
        assert sha(Path(pins[key]['path'])) == pins[key]['sha256']
    run = ROOT / 'applications/evidence' / ('pnpm-deploy-alias-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    work = Path(tempfile.mkdtemp(prefix='rules-pnpm-deploy-alias-', dir='/private/tmp'))
    project = work / 'project'
    app = project / 'packages/app'
    app.mkdir(parents=True)
    for directory in ['config', 'cache', 'state', 'tmp', 'global']:
        (work / directory).mkdir()
    for name in ['user.npmrc', 'global.npmrc']:
        (work / 'config' / name).write_text('')
    shutil.copyfile(__file__, run / 'probe.py')
    shutil.copyfile(Path(__file__).with_name('probe.py'), run / 'helpers.py')
    write(project / 'package.json', dict(name='rules-deploy-custody-root', private=True))
    (project / 'pnpm-workspace.yaml').write_text('packages:\n  - packages/*\nstoreDir: ' + str(work / 'cache/store') + '\n')
    write(app / 'package.json', dict(name='rules-deploy-custody-app', version='1.0.0', main='index.cjs', files=['index.cjs']))
    (app / 'index.cjs').write_text('module.exports="owned source preimage";\n')
    (app / 'private.txt').write_text('owned author source;not a deployment artifact\n')
    env = dict(PATH=str(Path(pins['node']['path']).parent) + ':/usr/bin:/bin', LANG='en_US.UTF-8', TMPDIR=str(work / 'tmp'),
        XDG_CONFIG_HOME=str(work / 'config'), XDG_CACHE_HOME=str(work / 'cache'), XDG_STATE_HOME=str(work / 'state'),
        PNPM_HOME=str(work / 'global'), PNPM_CONFIG_STATE_DIR=str(work / 'state'),
        NPM_CONFIG_USERCONFIG=str(work / 'config/user.npmrc'), NPM_CONFIG_GLOBALCONFIG=str(work / 'config/global.npmrc'),
        NPM_CONFIG_CACHE=str(work / 'cache/npm'), NPM_CONFIG_REGISTRY='http://127.0.0.1:9', NPM_CONFIG_FETCH_RETRIES='0',
        NPM_CONFIG_IGNORE_SCRIPTS='true', NPM_CONFIG_UPDATE_NOTIFIER='false', COREPACK_ENABLE_NETWORK='0',
        DO_NOT_TRACK='1', NO_COLOR='1', TERM='dumb')
    receipt = dict(schema=1, work=str(work), producerSha256=sha(run / 'probe.py'), helperSha256=sha(run / 'helpers.py'),
        tools={key: pins[key] for key in ['pnpm', 'node']}, environment=env, commands=[], cases=[],
        limits=['Only a fresh owned dependency-free workspace;source preimages retained before force control.',
            'One exact-spelling refusal and one case-only alias;if the host has distinct objects the alias control is unavailable.',
            'No user checkout,old fixture,global store,world,or product source is modified. No restoration is claimed from this probe.'])
    write(run / 'receipt.json', receipt)

    def command(label, args):
        child = subprocess.Popen([pins['pnpm']['path'], *args], cwd=project, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timed = False
        try:
            out, err = child.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            timed = True
            os.killpg(child.pid, signal.SIGTERM)
            try:
                out, err = child.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                out, err = child.communicate(timeout=3)
        (run / (label + '.stdout')).write_bytes(out)
        (run / (label + '.stderr')).write_bytes(err)
        try:
            os.killpg(child.pid, 0)
            absent = False
        except ProcessLookupError:
            absent = True
        receipt['commands'].append(dict(label=label, args=args, pid=child.pid, exitCode=child.returncode,
            timedOut=timed, groupAbsent=absent, stdoutSha256=sha(run / (label + '.stdout')),
            stderrSha256=sha(run / (label + '.stderr'))))
        write(run / 'receipt.json', receipt)
        assert absent and not timed
        return child.returncode

    assert command('install', ['install', '--offline', '--ignore-scripts', '--no-frozen-lockfile']) == 0
    for path in ['package.json', 'pnpm-workspace.yaml', 'pnpm-lock.yaml', 'packages/app/package.json', 'packages/app/index.cjs', 'packages/app/private.txt']:
        saved = run / 'preimage' / path
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(project / path, saved)
    for label, target in [('exact-source', app), ('case-alias-source', app.with_name('APP'))]:
        before = snapshot(project)
        same = target.exists() and os.path.samefile(target, app)
        identity = None
        if same:
            original, alias = app.stat(), target.stat()
            identity = dict(original=dict(device=str(original.st_dev), inode=str(original.st_ino)),
                alias=dict(device=str(alias.st_dev), inode=str(alias.st_ino)))
        if label == 'case-alias-source' and not same:
            receipt['cases'].append(dict(id=label, available=False, reason='Host has distinct case paths'))
            break
        code = command(label, ['--filter', 'rules-deploy-custody-app', 'deploy', str(target), '--force', '--offline', '--ignore-scripts'])
        row = dict(id=label, available=True, target=str(target), sameSourceObjectBefore=same, identityBefore=identity,
            before=before, after=snapshot(project), exitCode=code, sourceExists=app.exists(), sourceSnapshot=snapshot(app))
        receipt['cases'].append(row)
        write(run / 'receipt.json', receipt)
        if label == 'exact-source':
            assert code != 0 and before == row['after'], 'Exact control must preserve the owned source before alias testing'
    receipt['complete'] = True
    receipt['privateKiB'] = int(subprocess.check_output(['du', '-sk', str(work)], text=True).split()[0])
    write(run / 'receipt.json', receipt)
    print(json.dumps(dict(run=str(run), work=str(work), outcomes=[(r['id'], r.get('exitCode'), r.get('sourceExists')) for r in receipt['cases']])))


if __name__ == '__main__':
    main()
