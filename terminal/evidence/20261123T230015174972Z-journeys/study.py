#!/usr/bin/env python3
"""Bounded disposable four-tool observations through the shared host fixture."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def snapshot(root):
    result = {}
    for path in sorted(root.rglob('*')):
        info = path.lstat()
        name = path.relative_to(root).as_posix()
        if stat.S_ISLNK(info.st_mode):
            result[name] = {'kind': 'link', 'target': os.readlink(path)}
        elif stat.S_ISREG(info.st_mode):
            result[name] = {'kind': 'file', 'bytes': info.st_size,
                            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                            'mode': stat.S_IMODE(info.st_mode)}
        elif not stat.S_ISDIR(info.st_mode):
            result[name] = {'kind': 'other', 'mode': info.st_mode}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stdin', choices=['pipe', 'tty'], default='pipe')
    args = parser.parse_args()
    pins = json.loads((ROOT / 'terminal/tools/pins.json').read_text())
    tools = pins['tools']
    for item in tools.values():
        assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256']
    run = ROOT / 'terminal/evidence' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run.mkdir(parents=True)
    cases = []
    for tool in ('npm', 'pnpm', 'yarn', 'empack'):
        work = run / 'work' / tool
        project = work / 'project'
        tiny = work / 'tiny'
        for p in (project, tiny, work / 'home', work / 'cache', work / 'tmp'):
            p.mkdir(parents=True, exist_ok=True)
        (tiny / 'package.json').write_text(json.dumps({'name': 'terminal-tiny', 'version': '1.0.0'}))
        (tiny / 'index.js').write_text('module.exports = 1;\n')
        manifest = {'name': 'terminal-study', 'private': True, 'version': '1.0.0',
                    'packageManager': tool + '@' + tools[tool]['version'],
                    'dependencies': {'terminal-tiny': 'file:../tiny'}}
        if tool != 'empack':
            (project / 'package.json').write_text(json.dumps(manifest, indent=2) + '\n')
        else:
            (project / 'empack.yml').write_text('schema: 6\npack:\n  id: terminal.fixture\n  name: Terminal Fixture\n  version: "1.0.0"\n  authors: [Fixture]\nruntime:\n  minecraft: "1.21.1"\n  loader: vanilla\n  java: {preferred: 21}\ndependencies: {}\n')
        if tool == 'yarn':
            (project / '.yarnrc.yml').write_text('enableGlobalCache: false\nenableNetwork: false\nnodeLinker: node-modules\n')
        env = {k: os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL', 'LC_CTYPE') if k in os.environ}
        env.update(PATH=str(Path(tools['node']['path']).parent) + os.pathsep + env['PATH'],
                   HOME=str(work / 'home'), USERPROFILE=str(work / 'home'),
                   XDG_CONFIG_HOME=str(work / 'home/config'), XDG_CACHE_HOME=str(work / 'cache'),
                   XDG_DATA_HOME=str(work / 'home/data'), TMPDIR=str(work / 'tmp'), TERM='xterm-256color',
                   npm_config_cache=str(work / 'cache/npm'), npm_config_update_notifier='false',
                   npm_config_audit='false', npm_config_fund='false',
                   EMPACK_STATE_DIR=str(work / 'state'), EMPACK_CACHE_DIR=str(work / 'cache/empack'))
        prefix = [tools[tool]['path']]
        if tool == 'yarn':
            prefix = [tools['node']['path'], tools[tool]['path']]
        commands = {
            'npm': [('help', ['--help']), ('refusal', ['terminal-unknown-command']),
                    ('inspect', ['pkg', 'get', '--json']),
                    ('preview', ['install', '--dry-run', '--ignore-scripts', '--no-audit', '--no-fund'])],
            'pnpm': [('help', ['--help']), ('refusal', ['terminal-unknown-command']),
                     ('inspect', ['list', '--json']),
                     ('preview', ['install', '--dry-run', '--ignore-scripts', '--offline'])],
            'yarn': [('help', ['--help']), ('refusal', ['terminal-unknown-command']),
                     ('inspect', ['info', '--json']),
                     ('resolve-write', ['install', '--mode=update-lockfile', '--json'])],
            'empack': [('help', ['--help']), ('refusal', ['terminal-unknown-command']),
                       ('inspect', ['check', '--documents', '--json']),
                       ('preview', ['--net-timeout', '3', '--dry-run', '--yes', 'sync'])],
        }[tool]
        for name, arguments in commands:
            before = snapshot(work)
            command = prefix + arguments
            captured = subprocess.run([sys.executable, str(ROOT / 'scripts/host-streams'),
                                       '--stdin', args.stdin, '--timeout', '15', '--', *command],
                                      cwd=project, env=env, capture_output=True, text=True, timeout=20)
            if captured.returncode:
                raise RuntimeError(captured.stderr)
            trace = json.loads(captured.stdout)
            after = snapshot(work)
            changed = {p: {'before': before.get(p), 'after': after.get(p)}
                       for p in sorted(before.keys() | after.keys()) if before.get(p) != after.get(p)}
            record = {'v': 1, 'surface': 'terminal-application', 'case': tool + '/' + name,
                      'observed': {'request': {'argv': command, 'cwd': str(project)},
                                   'host': trace['observed'], 'before': before, 'after': after,
                                   'changes': changed, 'expectationBasis': 'journeys.md; validation pending'},
                      'outcome': {**trace['outcome'],
                                  'safeNext': 'Inspect actual effects and diagnostic before retry; no automatic replay.'}}
            (run / (tool + '-' + name + '.json')).write_text(json.dumps(record, indent=2) + '\n')
            for channel in ('stdout', 'stderr'):
                (run / (tool + '-' + name + '.' + channel)).write_bytes(base64.b64decode(trace['observed'][channel + '_b64']))
            cases.append({'tool': tool, 'case': name, **trace['outcome'], 'changedPaths': len(changed)})
            print(json.dumps(cases[-1]), flush=True)
    receipt = {'v': 1, 'profile': 'local-macos-arm64-stdout-pipe-stderr-private-pty',
               'stdin': args.stdin, 'pins': pins, 'fixtureSha256': hashlib.sha256((ROOT / 'scripts/host-streams').read_bytes()).hexdigest(),
               'harnessSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'cases': cases,
               'limits': 'No cross-stream total order; private PTY is not a human or a controlling terminal; no hooks requested.'}
    (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(str(run), flush=True)


if __name__ == '__main__':
    main()
