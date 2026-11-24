#!/usr/bin/env python3
"""Disposable lifecycle observations; no user project or global installation writes."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile

from study import ROOT, snapshot
from streams import capture


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Lab:
    def __init__(self, profile):
        self.pins = json.loads((ROOT / 'terminal/tools/pins.json').read_text())
        self.profile = profile
        for pin in self.pins['tools'].values():
            assert digest(Path(pin['path'])) == pin['sha256']
        self.run = ROOT / 'terminal/evidence' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-journeys')
        self.run.mkdir(parents=True)
        self.cases = []
        for name in ('journeys.py', 'streams.py', 'study.py'):
            shutil.copyfile(ROOT / 'terminal' / name, self.run / name)

    def setup(self, tool):
        self.tool = tool
        self.work = self.run / 'work' / tool
        self.project = self.work / 'project'
        for part in ('project', 'tiny', 'extra', 'home', 'cache', 'tmp'):
            (self.work / part).mkdir(parents=True)
        for directory, name in [('tiny', 'terminal-tiny'), ('extra', 'terminal-extra')]:
            (self.work / directory / 'package.json').write_text(json.dumps({'name': name, 'version': '1.0.0'}))
            (self.work / directory / 'index.js').write_text('module.exports = 1;\n')
        manifest = {'name': 'terminal-study', 'private': True, 'version': '1.0.0',
                    'packageManager': tool + '@' + self.pins['tools'][tool]['version'],
                    'dependencies': {'terminal-tiny': 'file:../tiny'},
                    'scripts': {'fixture-fail': 'node fixture-fail.cjs',
                                'fixture-wait': 'node fixture-wait.cjs',
                                'fixture-input': 'node fixture-input.cjs'}}
        if tool == 'empack':
            (self.project / 'empack.yml').write_text('schema: 6\npack:\n  id: terminal.fixture\n  name: Terminal Fixture\n  version: "1.0.0"\n  authors:\n    - Fixture\nruntime:\n  minecraft: "1.21.1"\n  loader: vanilla\n  java:\n    preferred: 21\ndependencies: {}\n')
        else:
            (self.project / 'package.json').write_text(json.dumps(manifest, indent=2) + '\n')
        if tool == 'yarn':
            (self.project / '.yarnrc.yml').write_text('enableGlobalCache: false\nenableNetwork: false\nnodeLinker: node-modules\n')
        (self.project / 'fixture-fail.cjs').write_text("require('fs').writeFileSync('hook-effect.txt', 'completed before failure\\n'); console.error('FIXTURE_FAILURE_AFTER_WRITE'); process.exit(7);\n")
        (self.project / 'fixture-wait.cjs').write_text("require('fs').writeFileSync('interrupt-effect.txt', 'completed before interruption\\n'); console.error('FIXTURE_WAIT_READY'); setInterval(() => {}, 1000);\n")
        (self.project / 'fixture-input.cjs').write_text("console.error('FIXTURE_INPUT_READY'); process.stdin.setEncoding('utf8'); process.stdin.once('data', d => {console.log(JSON.stringify({answer:d.trim(),tty:!!process.stdin.isTTY}));process.exit(0)}); process.stdin.on('end',()=>{console.error('FIXTURE_INPUT_EOF');process.exitCode=3});\n")
        env = {k: os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL', 'LC_CTYPE') if k in os.environ}
        env.update(PATH=str(Path(self.pins['tools']['node']['path']).parent) + os.pathsep + env['PATH'],
                   HOME=str(self.work / 'home'), USERPROFILE=str(self.work / 'home'),
                   XDG_CONFIG_HOME=str(self.work / 'home/config'), XDG_CACHE_HOME=str(self.work / 'cache'),
                   XDG_DATA_HOME=str(self.work / 'home/data'), TMPDIR=str(self.work / 'tmp'), TERM='xterm-256color',
                   npm_config_cache=str(self.work / 'cache/npm'), npm_config_update_notifier='false',
                   npm_config_audit='false', npm_config_fund='false', NODE_DISABLE_COMPILE_CACHE='1',
                   EMPACK_STATE_DIR=str(self.work / 'state'), EMPACK_CACHE_DIR=str(self.work / 'cache/empack'))
        if tool == 'pnpm':
            env['pnpm_config_pm_on_fail'] = 'ignore'  # Use the pinned native executable, not downloaded self-management.
        self.env = env
        self.prefix = [self.pins['tools'][tool]['path']]
        if tool == 'yarn':
            self.prefix.insert(0, self.pins['tools']['node']['path'])

    def case(self, name, argv, expectation, safe_next, *, marker=None, action=None, timeout=12, overrides=None):
        before = snapshot(self.work)
        previous = os.getcwd()
        old_env = os.environ.copy()
        try:
            os.chdir(self.project)
            os.environ.clear()
            os.environ.update(self.env)
            if overrides:
                os.environ.update(overrides)
            trace = capture(self.prefix + argv, **self.profile, marker=marker, action=action, timeout=timeout)
        finally:
            os.chdir(previous)
            os.environ.clear()
            os.environ.update(old_env)
        after = snapshot(self.work)
        changes = {p: {'before': before.get(p), 'after': after.get(p)} for p in sorted(before.keys() | after.keys()) if before.get(p) != after.get(p)}
        categories = {k: [p for p in changes if p.startswith(prefix)] for k, prefix in
                      [('project', 'project/'), ('durable', 'state/'), ('cache', 'cache/'), ('home', 'home/'), ('temporary', 'tmp/')]}
        record = {'v': 1, 'surface': self.tool, 'case': name,
                  'observed': {'request': {'argv': self.prefix + argv, 'cwd': str(self.project)},
                               'expectation': expectation, 'expectationKind': 'reviewer hypothesis, compare native result',
                               'profile': self.profile, 'envOverrides': overrides or {},
                               'configuration': {k: v for k, v in self.env.items() if k.startswith(('pnpm_', 'npm_', 'NODE_', 'EMPACK_'))},
                               'host': trace['observed'], 'before': before, 'after': after,
                               'changes': changes, 'effectsByScope': categories},
                  'outcome': {**trace['outcome'], 'safeNext': safe_next, 'safeNextKind': 'reviewer recommendation'}}
        stem = self.tool + '-' + name
        (self.run / (stem + '.json')).write_text(json.dumps(record, indent=2) + '\n')
        for channel in ('stdout', 'stderr', 'combined'):
            if channel + '_b64' in trace['observed']:
                (self.run / (stem + '.' + channel)).write_bytes(base64.b64decode(trace['observed'][channel + '_b64']))
        summary = {'tool': self.tool, 'case': name, **trace['outcome'], 'effects': {k: len(v) for k, v in categories.items()}}
        self.cases.append(summary)
        print(json.dumps(summary), flush=True)

    def finish(self):
        receipt = {'v': 1, 'pins': self.pins, 'profile': self.profile, 'cases': self.cases,
                   'harness': {n: digest(self.run / n) for n in ('journeys.py', 'streams.py', 'study.py')},
                   'limits': ['macOS arm64 only; non-controlling PTY', 'No claim of universal hook isolation; private environment is not an OS sandbox',
                              'SIGINT is group-directed, not a physical Ctrl-C keypress', 'Network was not blocked by OS; package fixtures are local and Yarn network disabled',
                              'Before/after snapshots do not observe transient writes or external paths; no human/screen-reader acceptance']}
        (self.run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(self.run, flush=True)


def packages(lab, tool):
    lab.setup(tool)
    installs = {'npm': ['install', '--ignore-scripts', '--offline'],
                'pnpm': ['install', '--ignore-scripts', '--offline'],
                'yarn': ['install', '--json']}
    install = installs[tool]
    lab.case('apply', install, 'Resolve and install the local dependency; lock and install-tree effects expected.', 'Inspect lock and installed package before repeating.')
    lab.case('repeat', install, 'An unchanged install should preserve dependency selection; incidental metadata may change.', 'Use the observed lock/install tree, not only the success label.')
    manifest_path = lab.project / 'package.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['dependencies']['terminal-extra'] = 'file:../extra'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    frozen = {'npm': ['ci', '--ignore-scripts', '--offline'], 'pnpm': ['install', '--frozen-lockfile', '--ignore-scripts', '--offline'],
              'yarn': ['install', '--immutable', '--json']}[tool]
    lab.case('lock-refusal', frozen, 'Manifest was deliberately changed after install. Locked/immutable operation should refuse; measure all scopes.', 'Reconcile the intended manifest with a normal install; do not erase the manifest change.')
    lab.case('recover-lock', install, 'Normal install should reconcile the retained intended extra dependency.', 'Confirm both intended dependencies are present.')
    remove = {'npm': ['uninstall', 'terminal-extra', '--ignore-scripts', '--offline'],
              'pnpm': ['remove', 'terminal-extra', '--ignore-scripts', '--offline'],
              'yarn': ['remove', 'terminal-extra']}[tool]
    lab.case('remove', remove, 'Explicitly remove terminal-extra from manifest, lock, and install tree; retain terminal-tiny.', 'Inspect declaration and lock together; removal is a write operation.')
    add = {'npm': ['install', '../extra', '--ignore-scripts', '--offline'],
           'pnpm': ['add', '../extra', '--ignore-scripts', '--offline'],
           'yarn': ['add', 'terminal-extra@file:../extra', '--json']}[tool]
    lab.case('add', add, 'Explicitly add a local dependency back; project writes expected.', 'Confirm authored identity and lock agree.')
    lab.case('hook-failure', ['run', 'fixture-fail'], 'Explicit requested script writes marker then exits7; failure must not imply rollback.', 'Keep hook-effect.txt as evidence; inspect effects before retrying the script.')
    lab.case('input', ['run', 'fixture-input'], 'EOF is observable refusal; tty input can be supplied by the controlled fixture only.', 'Distinguish missing input from dependency failure.',
             marker='FIXTURE_INPUT_READY', action='yes\n' if lab.profile['stdin'] == 'tty' else None)
    lab.case('interrupt', ['run', 'fixture-wait'], 'Marker establishes a write before group SIGINT; original project effect should remain.', 'Inspect interrupt-effect.txt and lock/install tree before a deliberate retry.',
             marker='FIXTURE_WAIT_READY', action='interrupt')
    lab.case('recover-after-interrupt', install, 'Reconcile installation after interruption; this does not undo arbitrary script effects.', 'Inspect the retained marker separately from package installation success.')


def empack(lab):
    lab.setup('empack')
    lab.case('apply', ['--yes', 'sync'], 'Publish the empty local authoring lock and durable ownership using the real engine.', 'Inspect manifest/check and recovery status before subsequent operations.')
    lab.case('repeat', ['--yes', 'sync'], 'Repeat current intent; dependency selection should stay unchanged.', 'Use check to inspect current documents and lock.')
    lab.case('inspect-json', ['check', '--json'], 'Structured stdout should parse as a single JSON value, with progress on stderr.', 'Read findings, not only exit status.')
    lock = lab.project / 'empack.lock'
    saved = lock.read_bytes() if lock.exists() else None
    lock.write_text('not valid lock JSON\n')
    lab.case('lock-refusal', ['check', '--json'], 'Malformed saved lock should produce an explicit failure finding without silently erasing it.', 'Preserve malformed input; inspect diagnostic before restoring or regenerating.')
    if saved is not None:
        lock.write_bytes(saved)
    lab.case('recover-lock', ['check', '--json'], 'Restore exact prior lock bytes explicitly, then check the resulting state.', 'A check result is not a native repair claim.')
    # Local resource pack: no external payload, no third-party hooks.
    (lab.project / 'supplied').mkdir()
    with zipfile.ZipFile(lab.project / 'supplied/resource.zip', 'w') as archive:
        archive.writestr('pack.mcmeta', json.dumps({'pack': {'pack_format': 34, 'description': 'Terminal Ω fixture'}}))
    lab.case('add-preview', ['--net-timeout', '2', '--yes', '--dry-run', 'add', 'supplied/resource.zip', '--type', 'resourcepack'],
             'Preview a local supplied resource pack; no project or durable publication authorized.', 'If identification needs a decision, inspect that request rather than accepting guessed policy.')
    lab.case('add', ['--net-timeout', '2', '--yes', 'add', 'supplied/resource.zip', '--type', 'resourcepack'],
             'Explicit local addition may require identification or role decisions; only observed outcome is established.', 'Inspect manifest and diagnostics before removal or retry.')
    lab.case('remove-preview', ['--yes', '--dry-run', 'remove', 'resource'],
             'Preview removal of the sole local resource dependency; no publication authorized.', 'Read the proposed target and any evidence limitation before applying.')
    lab.case('remove', ['--yes', 'remove', 'resource'],
             'Request removal of the sole local resource dependency; preserve refusal if relationship evidence is insufficient.', 'Inspect actual manifest, lock, and payload; do not equate refusal with absence.')
    shutil.copyfile(lab.project / 'supplied/resource.zip', lab.project / 'supplied/resource2.zip')
    lab.case('interrupt', ['--yes', 'add', 'supplied/resource2.zip', '--type', 'resourcepack'],
             'Request cancellation when publication progress is observed; completion may already have happened.', 'Inspect status, pending inputs, recovery, and actual files before retrying.',
             marker='Saving verified changes', action='interrupt')
    lab.case('status-after-interrupt', ['status', '--json'],
             'Inspect actual authoring and recovery state after cancellation without automatic replay.', 'Match any recovery action to the exact recorded operation.')
    lab.case('recovery-inspect', ['recover'],
             'Inspect whether publication recovery is actually necessary; no finish/restore authorized by inspection.', 'If recovery is reported, preserve its evidence and choose an explicit target-bound action.')
    lab.case('pending-list', ['pending', 'list'],
             'Inspect saved continuation inputs, distinct from an interrupted publication.', 'Resume only after fresh review of the retained target.')
    lab.case('pending', ['pending', '--help'], 'Discover continuation commands without creating or discarding an operation.', 'Inspect saved inputs rather than deleting recovery state.')
    lab.case('recover-help', ['recover', '--help'], 'Discover recovery commands; this is not an exercised interrupted engine recovery.', 'Recover only identified owned operations after inspecting their state.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stdin', choices=['pipe', 'tty'], default='pipe')
    p.add_argument('--stdout', choices=['pipe', 'tty'], default='pipe')
    p.add_argument('--stderr', choices=['pipe', 'tty'], default='tty')
    p.add_argument('--width', type=int, default=80)
    p.add_argument('--tools', nargs='+', choices=['npm', 'pnpm', 'yarn', 'empack'], default=['npm', 'pnpm', 'yarn', 'empack'])
    args = p.parse_args()
    profile = vars(args).copy()
    selected = profile.pop('tools')
    lab = Lab(profile)
    try:
        for tool in selected:
            if tool == 'empack':
                empack(lab)
            else:
                packages(lab, tool)
    finally:
        lab.finish()


if __name__ == '__main__':
    main()
