"""Owner-run override policy study over generated packages and a loopback registry."""
from datetime import datetime, timezone
import argparse
import base64
import gzip
import hashlib
import http.server
import io
import json
import os
from pathlib import Path
import platform
import signal
import stat
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.parse

ROOT = Path(__file__).resolve().parents[2]
LEAF, LEFT, RIGHT = 'rules-override-leaf', 'rules-override-left', 'rules-override-right'
sha = lambda b: hashlib.sha256(b).hexdigest()
write = lambda p, v: p.write_text(json.dumps(v, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manager', choices=['all', 'npm', 'pnpm', 'yarn'], default='all')
    manager_option = parser.parse_args().manager
    pins = json.loads((ROOT / 'applications/sources/local-pins.json').read_text())['tools']
    for name in ['node', 'npm', 'pnpm', 'yarn']:
        assert sha(Path(pins[name]['path']).read_bytes()) == pins[name]['sha256'], name
    npm_package = Path(pins['node']['path']).parent.parent / 'lib/node_modules/npm/package.json'
    assert json.loads(npm_package.read_text())['version'] == pins['npm']['version']
    run = ROOT / 'applications/evidence' / ('js-overrides-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir(); (run / 'probe.py').write_bytes(Path(__file__).read_bytes())
    for name in ['archives', 'responses', 'states']: (run / name).mkdir()
    work = Path(tempfile.mkdtemp(prefix='rules-js-overrides-', dir='/private/tmp'))
    for ancestor in [work, *work.parents]:
        assert not any((ancestor / name).exists() for name in ['package.json', '.npmrc', '.yarnrc.yml', 'pnpm-workspace.yaml']), ancestor
    rc_name = '.' + work.name + '.yml'
    assert not (Path.home() / rc_name).exists()
    packages, archive_info, commands, mutations, events = {}, {}, [], [], []
    current = {'case': 'setup'}; mutex = threading.Lock()
    for name, versions in [(LEAF, ['1.0.0', '1.1.0', '2.0.0']), (LEFT, ['1.0.0']), (RIGHT, ['1.0.0'])]:
        for version in versions:
            dependencies = {} if name == LEAF else {LEAF: '^1.0.0'}
            package = dict(name=name, version=version, main='index.js', license='UNLICENSED', dependencies=dependencies)
            code = 'module.exports={name:' + json.dumps(name) + ',version:' + json.dumps(version) + ',file:__filename'
            if name != LEAF: code += ',leaf:require(' + json.dumps(LEAF) + ')'
            bodies = {'package.json': (json.dumps(package, separators=(',', ':')) + '\n').encode(), 'index.js': (code + '};\n').encode()}
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode='w', format=tarfile.USTAR_FORMAT) as archive:
                for path, body in bodies.items():
                    info = tarfile.TarInfo('package/' + path); info.mode = 0o644; info.mtime = 0; info.size = len(body)
                    archive.addfile(info, io.BytesIO(body))
            raw = gzip.compress(buffer.getvalue(), mtime=0); filename = name + '-' + version + '.tgz'
            (run / 'archives' / filename).write_bytes(raw)
            item = dict(name=name, version=version, manifest=package, filename=filename, bytes=len(raw), sha256=sha(raw),
                        integrity='sha512-' + base64.b64encode(hashlib.sha512(raw).digest()).decode(),
                        shasum=hashlib.sha1(raw).hexdigest(), files={p:dict(bytes=len(b),sha256=sha(b)) for p,b in bodies.items()})
            packages[name, version] = raw; archive_info[name, version] = item

    class Registry(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            self.connection.settimeout(5)
            parts = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path).lstrip('/').split('/')
            status, kind, body = 200, 'application/json', b''
            if len(parts) == 1 and parts[0] in [LEAF, LEFT, RIGHT]:
                name = parts[0]; versions = sorted(v for n,v in packages if n == name)
                values = {}
                for version in versions:
                    item = archive_info[name, version]
                    values[version] = {**item['manifest'], 'dist':dict(tarball=origin + '/' + name + '/-/' + item['filename'], integrity=item['integrity'], shasum=item['shasum'])}
                body = (json.dumps(dict(name=name, _id=name, **{'dist-tags':dict(latest=versions[-1])}, versions=values,
                    time=dict(created='2024-01-01T00:00:00.000Z', modified='2024-01-05T00:00:00.000Z',
                              **{v:'2024-01-02T00:00:00.000Z' for v in versions})), separators=(',', ':')) + '\n').encode()
            elif len(parts) == 3 and parts[1] == '-':
                item = next((x for x in archive_info.values() if x['name'] == parts[0] and x['filename'] == parts[2]), None)
                if item: body = packages[item['name'], item['version']]; kind = 'application/octet-stream'
                else: status = 404
            else: status = 404
            if status == 404: body = b'{"error":"generated_fixture_not_found"}\n'
            digest = sha(body); target = run / 'responses' / (digest + ('.tgz' if kind == 'application/octet-stream' else '.json'))
            with mutex:
                if not target.exists(): target.write_bytes(body)
                events.append(dict(**current, path=self.path, status=status, response=str(target.relative_to(run)), sha256=digest,
                                   authorizationPresent=bool(self.headers.get('Authorization'))))
            self.send_response(status); self.send_header('Content-Type', kind); self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store'); self.end_headers()
            try: self.wfile.write(body)
            except BrokenPipeError: pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Registry); server.daemon_threads = False
    origin = 'http://127.0.0.1:' + str(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, name='owned-override-registry'); thread.start()
    error = None

    def image(project):
        result = {}
        for directory, dirs, names in os.walk(project, followlinks=False):
            for name in sorted(dirs + names):
                p = Path(directory) / name; st = p.lstat(); rel = p.relative_to(project).as_posix()
                if stat.S_ISLNK(st.st_mode): result[rel] = dict(kind='link', target=os.readlink(p), mode=st.st_mode)
                elif stat.S_ISREG(st.st_mode):
                    raw = p.read_bytes(); digest = sha(raw); saved = run / 'states' / (digest + '.bin')
                    if not saved.exists(): saved.write_bytes(raw)
                    result[rel] = dict(kind='file', bytes=len(raw), sha256=digest, mode=st.st_mode, captured=str(saved.relative_to(run)))
                elif stat.S_ISDIR(st.st_mode): result[rel] = dict(kind='directory', mode=st.st_mode)
                else: raise AssertionError('Unexpected fixture object')
        return result

    try:
        for manager in (['npm', 'pnpm', 'yarn'] if manager_option == 'all' else [manager_option]):
            profiles = ['graph', 'direct'] + (['manual'] if manager == 'yarn' else [])
            for profile in profiles:
                base = work / (manager + '-' + profile); project = base / 'project'; project.mkdir(parents=True)
                for name in ['cache', 'config', 'state', 'tmp', 'global']: (base / name).mkdir()
                for name in ['user.npmrc', 'global.npmrc']: (base / 'config' / name).write_text('')
                manifest = dict(name='rules-override-study', version='1.0.0', private=True,
                                dependencies={LEFT:'1.0.0', RIGHT:'1.0.0'} if profile == 'graph' else {LEAF:'^1.0.0'})
                write(project / 'package.json', manifest)
                (project / '.npmrc').write_text('registry=' + origin + '\nignore-scripts=true\naudit=false\nfund=false\nfetch-retries=0\nupdate-notifier=false\n')
                env = dict(PATH=str(Path(pins['node']['path']).parent) + ':/usr/bin:/bin', TMPDIR=str(base / 'tmp'), LANG='en_US.UTF-8', TERM='dumb', NO_COLOR='1',
                    XDG_CONFIG_HOME=str(base / 'config'), XDG_CACHE_HOME=str(base / 'cache'), XDG_STATE_HOME=str(base / 'state'),
                    NPM_CONFIG_USERCONFIG=str(base / 'config/user.npmrc'), NPM_CONFIG_GLOBALCONFIG=str(base / 'config/global.npmrc'),
                    NPM_CONFIG_CACHE=str(base / 'cache/npm'), NPM_CONFIG_PREFIX=str(base / 'global'), NPM_CONFIG_REGISTRY=origin,
                    NPM_CONFIG_FETCH_RETRIES='0', NPM_CONFIG_IGNORE_SCRIPTS='true', NPM_CONFIG_AUDIT='false', NPM_CONFIG_FUND='false', NPM_CONFIG_UPDATE_NOTIFIER='false',
                    PNPM_HOME=str(base / 'global'), PNPM_CONFIG_STATE_DIR=str(base / 'state'), COREPACK_ENABLE_NETWORK='0',
                    YARN_RC_FILENAME=rc_name, YARN_GLOBAL_FOLDER=str(base / 'global'), YARN_CACHE_FOLDER=str(base / 'cache/yarn'),
                    YARN_ENABLE_TELEMETRY='0', YARN_ENABLE_IMMUTABLE_INSTALLS='false', YARN_IGNORE_PATH='1', DO_NOT_TRACK='1')
                yaml_base = 'packages: []\nstoreDir: ' + str(base / 'cache/store') + '\ncacheDir: ' + str(base / 'cache/metadata') + '\nautoDedupe: false\n'
                if manager == 'pnpm':
                    (project / 'pnpm-workspace.yaml').write_text(yaml_base)
                    prefix, install = [pins['pnpm']['path']], ['install', '--no-frozen-lockfile', '--ignore-scripts']
                elif manager == 'yarn':
                    (project / 'yarn.lock').write_text('')
                    (project / rc_name).write_text('nodeLinker: node-modules\nenableGlobalCache: false\nenableTelemetry: false\nenableScripts: false\nhttpRetry: 0\nnpmRegistryServer: ' + origin + '\nunsafeHttpWhitelist: [127.0.0.1]\n')
                    prefix, install = [pins['node']['path'], pins['yarn']['path']], ['install']
                else: prefix, install = [pins['npm']['path']], ['install', '--ignore-scripts']
                def command(label, arguments, expected_failure=False, query=False):
                    case = manager + '-' + profile + '-' + label
                    with mutex: current['case'] = case
                    before = image(project); began = time.monotonic()
                    argv = ([pins['node']['path']] if query else prefix) + arguments
                    child = subprocess.Popen(argv, cwd=project, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
                    print(json.dumps(dict(start=case, pid=child.pid)), flush=True)
                    timed = False
                    try: stdout, stderr = child.communicate(timeout=90)
                    except subprocess.TimeoutExpired:
                        timed = True; os.killpg(child.pid, signal.SIGKILL); stdout, stderr = child.communicate()
                    (run / (case + '.stdout')).write_bytes(stdout); (run / (case + '.stderr')).write_bytes(stderr)
                    try: os.killpg(child.pid, 0); absent = False
                    except ProcessLookupError: absent = True
                    after = image(project)
                    commands.append(dict(id=case, manager=manager, profile=profile, query=query, argv=argv, pid=child.pid,
                        exitCode=child.returncode, timedOut=timed, groupAbsent=absent, seconds=time.monotonic()-began,
                        before=before, after=after, stdoutSha256=sha(stdout), stderrSha256=sha(stderr)))
                    write(run / 'commands.json', commands)
                    print(json.dumps(dict(finish=case, exitCode=child.returncode)), flush=True)
                    assert not timed and absent and ((child.returncode != 0) if expected_failure else child.returncode == 0), 'Retain unexpected result before any retry.'
                    if query: assert before == after
                query_script = "const fs=require('fs'),r=require('module').createRequire(process.cwd()+'/package.json');const p=JSON.parse(fs.readFileSync('package.json','utf8'));const v={};for(const n of Object.keys(p.dependencies)){v[n]={resolved:r.resolve(n),value:r(n)}};console.log(JSON.stringify(v))"
                def inspect(label): command(label + '-runtime', ['-e', query_script], query=True)
                def policy(label, entries):
                    before = image(project)
                    if manager == 'pnpm':
                        text = yaml_base + ('overrides:\n' + ''.join('  ' + json.dumps(k) + ': ' + json.dumps(v) + '\n' for k,v in entries) if entries else '')
                        (project / 'pnpm-workspace.yaml').write_text(text)
                    else:
                        key = 'overrides' if manager == 'npm' else 'resolutions'
                        manifest[key] = dict(entries); write(project / 'package.json', manifest)
                    mutations.append(dict(id=manager + '-' + profile + '-' + label, manager=manager, profile=profile,
                                          action='authored-policy-edit', entries=entries, before=before, after=image(project)))
                    write(run / 'mutations.json', mutations)
                command('baseline', install); inspect('baseline')
                if profile == 'graph':
                    scoped = (LEFT, {LEAF:'2.0.0'}) if manager == 'npm' else ((LEFT + '>' + LEAF) if manager == 'pnpm' else (LEFT + '/' + LEAF), '2.0.0')
                    generic = (LEAF, '1.0.0')
                    for label, entries in [('parent-only', [scoped]), ('global-first', [generic, scoped]), ('parent-first', [scoped, generic])]:
                        policy(label, entries); command(label, install); inspect(label)
                    if manager == 'pnpm':
                        for label, value in [('converge-outside', '2.0.0'), ('converge-inside', '1.0.0')]:
                            policy(label, [(LEAF + '@', value)]); command(label, install); inspect(label)
                elif profile == 'direct':
                    policy('force-direct', [(LEAF, '2.0.0')]); command('force-direct', install, expected_failure=manager == 'npm'); inspect('force-direct')
                else:
                    command('set-resolution', ['set', 'resolution', LEAF + '@npm:^1.0.0', 'npm:2.0.0']); inspect('set-resolution')
                    before = image(project); (project / 'yarn.lock').unlink()
                    mutations.append(dict(id='yarn-manual-remove-lock', manager=manager, profile=profile, action='owned-lock-removal', before=before, after=image(project)))
                    write(run / 'mutations.json', mutations)
                    command('recreate-lock', install); inspect('recreate-lock')
        for name in ['node','npm','pnpm','yarn']: assert sha(Path(pins[name]['path']).read_bytes()) == pins[name]['sha256']
    except BaseException as failure:
        error = str(failure)
        raise
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
        write(run / 'events.json', events); write(run / 'archives.json', list(archive_info.values()))
        write(run / 'receipt.json', dict(schema=1, complete=error is None, error=error, work=str(work), origin=origin,
            tools={k:pins[k] for k in ['node','npm','pnpm','yarn']}, npmPackageSha256=sha(npm_package.read_bytes()),
            producerSha256=sha((run / 'probe.py').read_bytes()), commands=len(commands), authoredMutations=len(mutations),
            allRecordedGroupsAbsent=all(c['groupAbsent'] for c in commands), registryThreadRetired=not thread.is_alive(),
            authorizationSeen=any(r['authorizationPresent'] for r in events), platform=platform.platform(),
            allocatedKiB=int(subprocess.check_output(['du','-sk',str(work)],text=True).split()[0]),
            scope='Sequential native package-manager and fresh Node queries in generated fixtures, own loopback registry and explicit config/cache paths. No personal project, real registry publication, engine build, GUI or global install. No HOME override. Installed results and scope need independent retained-data review; no full resolver/linker/platform qualification.'))
        print(json.dumps(dict(run=str(run), complete=error is None, commands=len(commands), registryThreadRetired=not thread.is_alive())), flush=True)


if __name__ == '__main__': main()
