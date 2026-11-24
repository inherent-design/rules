#!/usr/bin/env python3
"""Owner-run publication fixture. Generated packages and loopback HTTP only."""
from datetime import datetime, timezone
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
PRODUCER = Path(__file__).read_bytes()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    assert sys.argv[1:] in [[], ['--loss-boundaries']]
    boundaries = sys.argv[1:] == ['--loss-boundaries']
    pins = json.loads((HERE / 'sources/local-pins.json').read_text())['tools']
    for key in ['node', 'npm', 'pnpm', 'yarn']:
        assert digest(Path(pins[key]['path']).read_bytes()) == pins[key]['sha256'], key
    run = HERE / 'evidence' / ('js-publication-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    (run / 'probe.py').write_bytes(PRODUCER)
    work = Path(tempfile.mkdtemp(prefix='rules-js-publication-', dir='/private/tmp'))
    for p in [work, *work.parents]:
        assert not any((p / f).exists() for f in ['.npmrc', '.yarnrc.yml', 'pnpm-workspace.yaml']), p
    records, events, rows = {}, [], []
    control = dict(mode='accept', case='setup')
    mutex = threading.Lock()

    class Registry(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *args):
            pass

        def reply(self, status, body):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(data)
            self.close_connection = True

        def do_GET(self):
            name = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path.lstrip('/'))
            with mutex:
                versions = records.get(name, {})
                body = dict(name=name, _id=name, _rev='fixture-1', versions=versions,
                            **{'dist-tags': {'latest': list(versions)[-1]} if versions else {}})
                events.append(dict(case=control['case'], method='GET', path=self.path,
                                   status=200 if versions else 404))
            self.reply(200 if versions else 404, body if versions else {'error': 'not_found'})

        def do_PUT(self):
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length < 1024 * 1024:
                return self.reply(413, {'error': 'fixture_body_limit'})
            data = self.rfile.read(length)
            body = json.loads(data)
            name = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path.lstrip('/'))
            assert name.startswith('rules-publication-fixture-') and body['name'] == name
            versions = body['versions']
            assert len(versions) == 1
            version, manifest = next(iter(versions.items()))
            attachments = body['_attachments']
            assert len(attachments) == 1
            attachment = next(iter(attachments.values()))
            archive = base64.b64decode(attachment['data'], validate=True)
            assert len(archive) == attachment['length']
            with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tar:
                files = {m.name: digest(tar.extractfile(m).read()) for m in tar if m.isfile()}
                packaged = json.loads(tar.extractfile('package/package.json').read())
                assert packaged['name'] == name and packaged['version'] == version
                assert 'package/index.js' in files and 'package/secret.txt' not in files
            assert manifest['dist']['shasum'] == hashlib.sha1(archive).hexdigest()
            assert manifest['dist']['integrity'] == 'sha512-' + base64.b64encode(hashlib.sha512(archive).digest()).decode()
            with mutex:
                index = len(events)
                mode, case = control['mode'], control['case']
                exists = version in records.get(name, {})
                accepted = mode not in ['reject', 'drop-before-accept'] and not exists
                status = 403 if mode == 'reject' else 409 if exists else 201
                event = dict(case=case, method='PUT', path=self.path, version=version,
                    mode=mode, accepted=accepted, status=None if mode == 'drop-before-accept' or mode == 'drop' and accepted else status,
                    responseDropped=mode == 'drop-before-accept' or mode == 'drop' and accepted,
                    archiveSha256=digest(archive), archiveBytes=len(archive), files=files,
                    requestSha256=digest(data), authorizationPresent=bool(self.headers.get('Authorization')))
                events.append(event)
                if accepted:
                    records.setdefault(name, {})[version] = manifest
                    (run / f'received-{index}.json').write_bytes(data)
                    (run / f'received-{index}.tgz').write_bytes(archive)
                (run / 'server-events.json').write_text(json.dumps(events, indent=2) + '\n')
            if event['responseDropped']:
                self.close_connection = True
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
            else:
                self.reply(status, {'ok': True} if accepted else {'error': 'forbidden' if status == 403 else 'version_exists'})

    server = ThreadingHTTPServer(('127.0.0.1', 0), Registry)
    server.daemon_threads = False
    thread = threading.Thread(target=server.serve_forever, name='rules-fixture-registry')
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}/'
    try:
        for manager in ['npm', 'pnpm', 'yarn']:
            base, project = work / manager, work / manager / 'project'
            for p in [project, base / 'home', base / 'config', base / 'cache', base / 'tmp']:
                p.mkdir(parents=True)
            # Not a credential: only this loopback fixture accepts the literal marker.
            (base / 'config/user.npmrc').write_text(f'registry={url}\n//127.0.0.1:{server.server_port}/:_authToken=rules-local-fixture-only\nfetch-retries=0\n')
            (base / 'config/global.npmrc').write_text('')
            (project / 'index.js').write_text('module.exports = "generated publication fixture";\n')
            (project / 'secret.txt').write_text('generated exclusion marker, not a secret\n')
            (project / 'hook.cjs').write_text('require("fs").appendFileSync("hooks.log", process.argv[2] + "\\n");\n'
                'if (process.argv[2] === process.env.FIXTURE_FAIL_HOOK) process.exit(7);\n')
            env = dict(PATH=str(Path(pins['node']['path']).parent) + ':/usr/bin:/bin', HOME=str(base / 'home'),
                XDG_CONFIG_HOME=str(base / 'config'), XDG_CACHE_HOME=str(base / 'cache'), TMPDIR=str(base / 'tmp'),
                NPM_CONFIG_USERCONFIG=str(base / 'config/user.npmrc'), NPM_CONFIG_GLOBALCONFIG=str(base / 'config/global.npmrc'),
                NPM_CONFIG_CACHE=str(base / 'cache/npm'), NPM_CONFIG_REGISTRY=url, NPM_CONFIG_FETCH_RETRIES='0',
                PNPM_CONFIG_FETCH_RETRIES='0', PNPM_CONFIG_STATE_DIR=str(base / 'state'),
                LANG='en_US.UTF-8', COREPACK_ENABLE_NETWORK='0', YARN_ENABLE_TELEMETRY='0',
                YARN_ENABLE_IMMUTABLE_INSTALLS='false', DO_NOT_TRACK='1', MISE_SKIP_RESHIM='1')
            name = 'rules-publication-fixture-' + manager
            if manager == 'yarn':
                (project / '.yarnrc.yml').write_text('nodeLinker: node-modules\nenableGlobalCache: false\nenableTelemetry: false\n'
                    f'npmRegistryServer: {url}\nnpmPublishRegistry: {url}\nunsafeHttpWhitelist: [127.0.0.1]\n'
                    'npmAuthToken: rules-local-fixture-only\nnpmAlwaysAuth: true\nhttpRetry: 0\n')
                prefix, publish = [pins['node']['path'], pins['yarn']['path']], ['npm', 'publish', '--json']
            elif manager == 'pnpm':
                prefix, publish = [pins['pnpm']['path']], ['publish', '--no-git-checks', '--json', '--registry', url,
                    '--npmrc-auth-file', str(base / 'config/user.npmrc')]
            else:
                prefix, publish = [pins['npm']['path']], ['publish', '--json', '--fetch-retries=0', '--no-audit', '--no-fund']

            def manifest(version, hooks=False):
                value = dict(name=name, version=version, files=['index.js'], main='index.js', license='UNLICENSED',
                             publishConfig=dict(registry=url))
                if hooks:
                    value['scripts'] = {event: 'node hook.cjs ' + event for event in
                        ['prepublish', 'prepublishOnly', 'prepack', 'postpack', 'publish', 'postpublish']}
                (project / 'package.json').write_text(json.dumps(value, indent=2) + '\n')

            def command(case, args, mode='accept', fail_hook=''):
                with mutex:
                    control.update(case=manager + '-' + case, mode=mode)
                    before_events = len(events)
                    before_versions = sorted(records.get(name, {}))
                hooks = project / 'hooks.log'
                before_hooks = hooks.read_text().splitlines() if hooks.exists() else []
                stem = manager + '-' + case
                (run / (stem + '-package.json')).write_bytes((project / 'package.json').read_bytes())
                started = time.monotonic()
                r = subprocess.run(prefix + args, cwd=project, env={**env, 'FIXTURE_FAIL_HOOK': fail_hook},
                                   input=b'', capture_output=True, timeout=40)
                for stream, data in [('stdout', r.stdout), ('stderr', r.stderr)]:
                    (run / (stem + '.' + stream)).write_bytes(data)
                with mutex:
                    selected_events = json.loads(json.dumps(events[before_events:]))
                    after_versions = sorted(records.get(name, {}))
                row = dict(v=1, app=manager, case=case, argv=prefix + args,
                    request=dict(version=json.loads((project / 'package.json').read_text())['version'],
                                 fixtureMode=mode, failingHook=fail_hook),
                    observed=dict(serverEvents=selected_events, beforeVersions=before_versions, afterVersions=after_versions,
                        hooksBefore=before_hooks, hooksAfter=hooks.read_text().splitlines() if hooks.exists() else [],
                        seconds=time.monotonic() - started, stdoutSha256=digest(r.stdout), stderrSha256=digest(r.stderr)),
                    outcome=dict(exitCode=r.returncode))
                rows.append(row)
                (run / 'trace.json').write_text(json.dumps(rows, indent=2) + '\n')
                print(manager, case, r.returncode, [(e['method'], e.get('status')) for e in selected_events], flush=True)
                return r

            manifest('1.0.0')
            command('help', ['npm', 'publish', '--help'] if manager == 'yarn' else ['publish', '--help'])
            if manager == 'yarn':
                assert command('initialize', ['install']).returncode == 0
            if boundaries:
                command('loss-before-accept', publish, mode='drop-before-accept')
                manifest('2.0.0', hooks=True)
                command('before-upload-hook-failure', publish, fail_hook='prepack')
                continue
            assert command('dry-run', publish + ['--dry-run']).returncode == 0
            assert command('accepted', publish).returncode == 0
            command('duplicate', publish)
            manifest('2.0.0')
            command('rejected', publish, mode='reject')
            manifest('3.0.0')
            command('lost-response', publish, mode='drop')
            # Independent read after the command, not substituted for its own knowledge.
            with mutex:
                control.update(case=manager + '-owner-read-after-loss', mode='accept')
            body = urllib.request.urlopen(url + name, timeout=5).read()
            (run / (manager + '-owner-read-after-loss.json')).write_bytes(body)
            assert '3.0.0' in json.loads(body)['versions']
            command('retry-after-loss', publish)
            manifest('4.0.0', hooks=True)
            command('dry-run-hooks', publish + ['--dry-run'])
            manifest('5.0.0', hooks=True)
            command('after-upload-hook-failure', publish, fail_hook='postpack' if manager == 'yarn' else 'postpublish')
        (run / 'receipt.json').write_text(json.dumps(dict(schema=1, producerSha256=digest(PRODUCER),
            tools={k: pins[k] for k in ['node', 'npm', 'pnpm', 'yarn']}, platform=platform.platform(), architecture=platform.machine(),
            registry=url, originalWork=str(work), commands=len(rows), boundaryFollowup=boundaries,
            scope='Generated single package per tool; immutable in-memory fixture versions and retained received bytes; no real registry/auth/TLS/replication/durability proof. Private config/home/cache; only loopback target, literal fixture-only auth marker. Server-side admission and client status are separate observations. Hooks are generated owned code.'), indent=2) + '\n')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()
        (run / 'server-events.json').write_text(json.dumps(events, indent=2) + '\n')
        (run / 'server-retired.json').write_text(json.dumps(dict(threadJoined=True, listeningSocketClosed=server.socket.fileno() == -1)) + '\n')
        shutil.move(str(work), str(run / 'work'))
        print('capture', run, flush=True)


if __name__ == '__main__':
    main()
