"""Bounded owner-run local workspace deployments, with no registry or user project."""
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def snapshot(root):
    result = {}
    if not root.exists() and not root.is_symlink():
        return result
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(directory) / name
            key = path.relative_to(root).as_posix()
            st = path.lstat()
            if path.is_symlink():
                result[key] = dict(kind='symlink', target=os.readlink(path))
            elif path.is_file():
                result[key] = dict(kind='file', sha256=sha(path), bytes=st.st_size,
                    mode=st.st_mode & 0o777, mtimeNs=str(st.st_mtime_ns))
            else:
                assert path.is_dir()
                result[key] = dict(kind='directory')
    return result


def archive(path):
    files = {'package/package.json': json.dumps(dict(name='rules-deploy-ext', version='1.0.0', main='index.cjs')).encode(),
        'package/index.cjs': b'module.exports="external-v1";\n'}
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode='wb', mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as tar:
            for name, data in files.items():
                info = tarfile.TarInfo(name)
                info.mode = 0o644
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    path.write_bytes(output.getvalue())


def main():
    pins = json.loads((ROOT / 'applications/sources/local-pins.json').read_text())['tools']
    for key in ['pnpm', 'node']:
        assert sha(Path(pins[key]['path'])) == pins[key]['sha256']
    run = ROOT / 'applications/evidence' / ('pnpm-deploy-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    shutil.copyfile(__file__, run / 'probe.py')
    work = Path(tempfile.mkdtemp(prefix='rules-pnpm-deploy-', dir='/private/tmp'))
    project = work / 'project'
    for name in ['project', 'config', 'cache', 'state', 'tmp', 'global', 'archives', 'portable', 'empty-store']:
        (work / name).mkdir(mode=0o700)
    for parent in [work, *work.parents]:
        assert not any((parent / f).exists() for f in ['.npmrc', 'pnpm-workspace.yaml']), parent
    for name in ['user.npmrc', 'global.npmrc']:
        (work / 'config' / name).write_text('')
    env = dict(PATH=str(Path(pins['node']['path']).parent) + ':/usr/bin:/bin', LANG='en_US.UTF-8',
        TMPDIR=str(work / 'tmp'), XDG_CONFIG_HOME=str(work / 'config'), XDG_CACHE_HOME=str(work / 'cache'),
        XDG_STATE_HOME=str(work / 'state'), PNPM_HOME=str(work / 'global'), PNPM_CONFIG_STATE_DIR=str(work / 'state'),
        NPM_CONFIG_USERCONFIG=str(work / 'config/user.npmrc'), NPM_CONFIG_GLOBALCONFIG=str(work / 'config/global.npmrc'),
        NPM_CONFIG_CACHE=str(work / 'cache/npm'), NPM_CONFIG_PREFIX=str(work / 'global'),
        NPM_CONFIG_REGISTRY='http://127.0.0.1:9', NPM_CONFIG_FETCH_RETRIES='0', NPM_CONFIG_IGNORE_SCRIPTS='true',
        NPM_CONFIG_AUDIT='false', NPM_CONFIG_FUND='false', NPM_CONFIG_UPDATE_NOTIFIER='false',
        COREPACK_ENABLE_NETWORK='0', DO_NOT_TRACK='1', NO_COLOR='1', TERM='dumb')
    external = work / 'archives/external.tgz'
    archive(external)
    shutil.copyfile(external, run / 'external.tgz')
    write(project / 'package.json', dict(name='rules-deploy-root', private=True, version='1.0.0'))
    (project / 'pnpm-workspace.yaml').write_text('packages:\n  - packages/*\nnodeLinker: isolated\nstoreDir: ' + str(work / 'cache/store') + '\ncacheDir: ' + str(work / 'cache/metadata') + '\n')
    (project / '.npmrc').write_text('registry=http://127.0.0.1:9\nignore-scripts=true\nfetch-retries=0\nupdate-notifier=false\n')
    bodies = {
        'app': 'module.exports={app:"app",lib:require("rules-deploy-lib"),ext:require("rules-deploy-ext")};\n',
        'lib': 'module.exports={lib:"lib",leaf:require("rules-deploy-leaf")};\n',
        'leaf': 'module.exports="leaf";\n', 'opt': 'module.exports="optional";\n',
        'dev': 'module.exports="development";\n',
    }
    for name, body in bodies.items():
        directory = project / 'packages' / name
        directory.mkdir(parents=True)
        manifest = dict(name='rules-deploy-' + name, version='1.0.0', main='index.cjs', files=['index.cjs'])
        if name == 'app':
            manifest.update(dependencies={'rules-deploy-lib': 'workspace:*', 'rules-deploy-ext': 'file:' + str(external)},
                optionalDependencies={'rules-deploy-opt': 'workspace:*'}, devDependencies={'rules-deploy-dev': 'workspace:*'})
        if name == 'lib':
            manifest['dependencies'] = {'rules-deploy-leaf': 'workspace:*'}
        write(directory / 'package.json', manifest)
        (directory / 'index.cjs').write_text(body)
        (directory / 'private.txt').write_text('not selected by files list\n')
    receipt = dict(schema=1, work=str(work), producerSha256=sha(run / 'probe.py'), tools={key: pins[key] for key in ['node', 'pnpm']},
        environment=env, externalSha256=sha(external), commands=[], cases=[], limits=[
            'Private workspace and deterministic local tarball;offline/ignored scripts/unreachable registry configured. No external service.',
            'Source/manifests/lock and target file effects recorded independently of command exit.',
            'Copied deployed output is tested with the owned source/cache/archive roots renamed temporarily, then restored in finally.',
            'No peer/platform/native-addon/lifecycle-script/crash/concurrent-publication claim.'])
    write(run / 'receipt.json', receipt)

    def command(label, argv, cwd=project, expected=None):
        child = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timed = False
        try:
            out, err = child.communicate(timeout=60)
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
        row = dict(label=label, argv=argv, cwd=str(cwd), pid=child.pid, exitCode=child.returncode,
            timedOut=timed, groupAbsent=absent, stdoutSha256=sha(run / (label + '.stdout')),
            stderrSha256=sha(run / (label + '.stderr')))
        receipt['commands'].append(row)
        write(run / 'receipt.json', receipt)
        assert not timed and absent, row
        if expected is not None:
            assert child.returncode == expected, (label, child.returncode, out.decode(errors='replace'), err.decode(errors='replace'))
        return child.returncode, out

    command('pnpm-version', [pins['pnpm']['path'], '--version'], expected=0)
    command('node-version', [pins['node']['path'], '--version'], expected=0)
    command('install', [pins['pnpm']['path'], 'install', '--offline', '--ignore-scripts', '--no-frozen-lockfile'], expected=0)
    for name in ['package.json', 'pnpm-workspace.yaml', 'pnpm-lock.yaml', '.npmrc']:
        shutil.copyfile(project / name, run / name)
    write(run / 'source-inputs.json', snapshot(project / 'packages'))
    runtime = work / 'read-runtime.cjs'
    runtime.write_text('''const fs=require('node:fs');const {createRequire}=require('node:module');
const path=require('node:path');const root=process.argv[2];const req=createRequire(path.join(root,'package.json'));
const output={};for(const name of ['rules-deploy-lib','rules-deploy-ext','rules-deploy-leaf','rules-deploy-opt','rules-deploy-dev']){
try{const found=req.resolve(name);output[name]={value:req(name),realpath:fs.realpathSync(found)};}catch(error){output[name]={error:error.code};}}
output.app=req('./index.cjs');console.log(JSON.stringify(output));\n''')
    shutil.copyfile(runtime, run / 'runtime.cjs')

    def sources():
        return {k: v for k, v in snapshot(project).items() if k != 'deployed' and not k.startswith('deployed/') and k != 'through-link'}

    def deploy(label, target, flags=(), filters=('rules-deploy-app',)):
        before, before_target = sources(), snapshot(target)
        args = [pins['pnpm']['path']]
        for value in filters:
            args += ['--filter', value]
        args += ['deploy', str(target), '--offline', '--ignore-scripts', *flags]
        code, _ = command(label, args)
        row = dict(id=label, filters=list(filters), flags=list(flags), target=str(target), beforeSource=before,
            afterSource=sources(), beforeTarget=before_target, afterTarget=snapshot(target), exitCode=code)
        receipt['cases'].append(row)
        write(run / 'receipt.json', receipt)
        assert row['beforeSource'] == row['afterSource'], label
        if code == 0:
            command(label + '-runtime', [pins['node']['path'], str(runtime), str(target)], cwd=work, expected=0)
            portable = work / 'portable' / label
            shutil.copytree(target, portable, symlinks=True)
            moved = []
            try:
                for original in [project, work / 'cache', work / 'archives']:
                    hidden = original.with_name(original.name + '-hidden')
                    original.rename(hidden)
                    moved.append((original, hidden))
                command(label + '-portable', [pins['node']['path'], str(runtime), str(portable)], cwd=work, expected=0)
            finally:
                for original, hidden in reversed(moved):
                    hidden.rename(original)
            row['portableSnapshot'] = snapshot(portable)
            row['sourceRestored'] = sources() == before
            assert row['sourceRestored'], label
            write(run / 'receipt.json', receipt)
        return row

    (project / 'deployed').mkdir()
    deploy('no-selection', project / 'deployed/none', filters=('not-a-workspace',))
    deploy('many-selected', project / 'deployed/many', filters=('rules-deploy-*',))
    deploy('unsafe-root', project, flags=('--force',))
    blocked = project / 'deployed/nonempty'
    blocked.mkdir()
    (blocked / 'marker.txt').write_text('retained\n')
    deploy('nonempty', blocked)
    baseline = deploy('production', project / 'deployed/production', flags=('--prod',))
    assert baseline['exitCode'] == 0, 'Baseline failed;inspect before collecting more deployments'
    deploy('production-no-optional', project / 'deployed/no-optional', flags=('--prod', '--no-optional'))
    deploy('all-groups', project / 'deployed/all')
    deploy('outside-new', work / 'outside-new', flags=('--prod',))
    forced = project / 'deployed/forced'
    forced.mkdir()
    (forced / 'marker.txt').write_text('owned disposable old deployment\n')
    deploy('forced-child', forced, flags=('--prod', '--force'))
    outside = work / 'outside-occupied'
    outside.mkdir()
    (outside / 'marker.txt').write_text('outside marker retained\n')
    deploy('forced-outside', outside, flags=('--prod', '--force'))
    (project / 'through-link').symlink_to(outside, target_is_directory=True)
    deploy('symlink-component', project / 'through-link/new', flags=('--prod', '--force'))
    late = project / 'deployed/late-failure'
    late.mkdir()
    (late / 'marker.txt').write_text('owned disposable old deployment\n')
    hidden = external.with_suffix('.held')
    external.rename(hidden)
    try:
        deploy('missing-archive', late, flags=('--prod', '--force', '--store-dir', str(work / 'empty-store')))
    finally:
        hidden.rename(external)
    receipt['complete'] = True
    receipt['externalRestored'] = sha(external) == receipt['externalSha256']
    receipt['privateKiB'] = int(subprocess.check_output(['du', '-sk', str(work)], text=True).split()[0])
    write(run / 'receipt.json', receipt)
    assert receipt['externalRestored']
    print(json.dumps(dict(run=str(run), work=str(work), outcomes=[(c['id'], c['exitCode']) for c in receipt['cases']])))


if __name__ == '__main__':
    main()
