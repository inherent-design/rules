"""Disposable standalone Prism template builds; no launcher or game execution."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import tempfile
import zipfile

from archive_import_probe import snapshot

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    binary = Path('/Users/zer0cell/.local/bin/empack')
    assert sha(binary) == '99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
    run = ROOT / 'applications/evidence' / ('empack-templates-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    work = Path(tempfile.mkdtemp(prefix='rules-empack-templates-', dir='/private/tmp'))
    for name in ['project', 'state', 'cache', 'tmp']:
        (work / name).mkdir(mode=0o700)
    project = work / 'project'
    env = dict(PATH=os.environ['PATH'], LANG='en_US.UTF-8', TMPDIR=str(work / 'tmp'))
    shutil.copyfile(__file__, run / 'probe.py')
    shutil.copyfile(Path(__file__).with_name('archive_import_probe.py'), run / 'helpers.py')
    receipt = dict(schema=1, work=str(work), binary=str(binary), binarySha256=sha(binary),
        producerSha256=sha(run / 'probe.py'), helperSha256=sha(run / 'helpers.py'),
        environment=env, commands=[], cases=[], limits=[
            'Own dependency-free author project and small marker/template bytes only.',
            'Standalone bundled Prism snapshot ZIP; no bootstrap, launcher, Java, installer or game.',
            'An approved build publishes only its own dist artifact; failure checks do not claim no state/cache effects.',
            'A controlled generated shell printf is executed under /bin/sh in the private workspace; no arbitrary author scripts.'])
    write(run / 'receipt.json', receipt)

    def command(label, argv, expected=None):
        p = subprocess.Popen(argv, env=env, cwd=work, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timed = False
        try:
            out, err = p.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            timed = True
            os.killpg(p.pid, signal.SIGTERM)
            try:
                out, err = p.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                out, err = p.communicate(timeout=3)
        (run / (label + '.stdout')).write_bytes(out)
        (run / (label + '.stderr')).write_bytes(err)
        try:
            os.killpg(p.pid, 0)
            absent = False
        except ProcessLookupError:
            absent = True
        row = dict(label=label, argv=argv, pid=p.pid, exitCode=p.returncode, timedOut=timed,
            groupAbsent=absent, stdoutSha256=sha(run / (label + '.stdout')),
            stderrSha256=sha(run / (label + '.stderr')))
        receipt['commands'].append(row)
        write(run / 'receipt.json', receipt)
        assert absent and not timed, row
        if expected is not None:
            assert p.returncode == expected, (label, p.returncode, err.decode(errors='replace'))
        return p.returncode, out

    def empack(label, args, expected=None):
        return command(label, [str(binary), '--state-dir', str(work / 'state'),
            '--cache-dir', str(work / 'cache'), '--workdir', str(project),
            '--color', 'never', '--yes', *args], expected)

    name = "Study ' \" $RULES_UNSET $(printf injected) Ω"
    author = 'schema: 6\npack:\n  id: pack-8cdd3cf17c474ecba451a89bc3109c0f\n  name: ' + json.dumps(name) + '\n  version: fixture\n  authors: [Rules fixture]\nruntime:\n  minecraft: "1.21.1"\n  loader: vanilla\n  java:\n    preferred: 21\ndependencies: {}\n'
    (project / 'empack.yml').write_text(author)
    (run / 'empack.yml').write_text(author)
    empack('version', ['--version'], 0)
    empack('sync', ['sync'], 0)
    cases = [
        ('baseline', {'common/nested/settings.template': b'common {{NAME}}',
            'client/nested/settings.template': b'client {{NAME}}',
            'server/nested/settings.template': b'server {{NAME}}',
            'common/auto.txt': b'{{NAME}}', 'common/raw.bin': b'\x00\xffbinary',
            'common/run.sh.template': b'#!/bin/sh\nprintf %s {{shell_quote NAME}}\n'}),
        ('missing-value', {'common/value.txt.template': b'{{UNKNOWN_RULES_VALUE}}'}),
        ('explicit-binary', {'common/raw.bin.template': b'\x00\xffbinary'}),
        ('duplicate-output', {'common/same.txt.template': b'first', 'common/same.txt': b'second'}),
        ('file-ancestor', {'common/item.template': b'first', 'common/item/nested.txt': b'second'}),
        ('shadowed-invalid-body', {'common/shared.template': b'{{UNKNOWN_RULES_VALUE}}', 'client/shared.template': b'selected'}),
        ('opposite-side-invalid-body', {'server/ignored.template': b'\xff', 'common/value.txt': b'valid'}),
        ('unrecognized-layer', {'other/ignored.template': b'{{UNKNOWN_RULES_VALUE}}', 'common/value.txt': b'valid'}),
        ('implicit-render', {'common/literal.txt': b'{{UNKNOWN_RULES_VALUE}}'}),
        ('cross-layer-case-alias', {'common/Shared.txt': b'common', 'client/shared.txt': b'client'}),
        ('selected-game-collision', {'common/.minecraft/config/marker.txt': b'template'}),
    ]
    for identity, sources in cases:
        templates = project / 'templates'
        if templates.exists():
            shutil.rmtree(templates)
        for relative, body in sources.items():
            target = templates / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            if relative.endswith('run.sh.template'):
                target.chmod(0o555)
        pack = project / 'pack'
        if pack.exists():
            shutil.rmtree(pack)
        (pack / 'config').mkdir(parents=True)
        (pack / 'config/marker.txt').write_bytes(b'game bytes')
        source_snapshot = {k: v for k, v in snapshot(project).items() if k != 'dist' and not k.startswith('dist/')}
        before_dist = snapshot(project / 'dist')
        code, _ = empack(identity, ['build', '--ad-hoc', 'prism', '--delivery', 'bundled',
            '--environment', 'client', '--updates', 'snapshot', '--format', 'zip'])
        after_source = {k: v for k, v in snapshot(project).items() if k != 'dist' and not k.startswith('dist/')}
        archives = list((project / 'dist').glob('*.zip')) if (project / 'dist').exists() else []
        row = dict(id=identity, sourceBytes={k: v.hex() for k, v in sources.items()},
            beforeSource=source_snapshot, afterSource=after_source, beforeDist=before_dist,
            afterDist=snapshot(project / 'dist'), exitCode=code, outputs=[])
        if code == 0:
            assert len(archives) == 1
            path = archives[0]
            saved = run / (identity + '.zip')
            shutil.copyfile(path, saved)
            with zipfile.ZipFile(saved) as z:
                assert len(z.infolist()) < 64 and sum(i.file_size for i in z.infolist()) < 1024 * 1024
                for info in z.infolist():
                    row['outputs'].append(dict(path=info.filename, bytesHex=z.read(info).hex(),
                        mode=(info.external_attr >> 16), crc=info.CRC))
            row['archiveSha256'] = sha(saved)
        receipt['cases'].append(row)
        write(run / 'receipt.json', receipt)
        assert code in [0, 1, 2] and source_snapshot == after_source, identity
        if code:
            assert before_dist == row['afterDist'], identity
        if identity == 'baseline' and code == 0:
            script = next(o for o in row['outputs'] if o['path'] == 'run.sh')
            script_path = work / 'generated-printf.sh'
            script_path.write_bytes(bytes.fromhex(script['bytesHex']))
            _, output = command('generated-printf', ['/bin/sh', str(script_path)], 0)
            assert output.decode() == name
    receipt['complete'] = True
    receipt['privateKiB'] = int(subprocess.check_output(['du', '-sk', str(work)], text=True).split()[0])
    write(run / 'receipt.json', receipt)
    print(json.dumps(dict(run=str(run), work=str(work), outcomes=[(r['id'], r['exitCode']) for r in receipt['cases']])))


if __name__ == '__main__':
    main()
