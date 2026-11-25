"""Run two selected MO2 policies with inert Windows/Qt/lifecycle adapters."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, value):
    p.write_text(json.dumps(value, indent=2) + '\n')


def main():
    ledger_path = ROOT / 'applications/sources/mo2-process-selections.json'
    ledger = json.loads(ledger_path.read_text())
    source = next(r for r in ledger['sources'] if r['path'] == 'src/processrunner.cpp')
    source_path = ROOT / source['cache']
    assert sha(source_path) == source['sha256']
    raw = source_path.read_bytes()
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == source['gitBlob']
    text = raw.decode('utf-8')
    cuts = []
    for start, end in [
        ('bool ProcessRunner::shouldRefresh(', '\nProcessRunner::Results ProcessRunner::postRun('),
        ('ProcessRunner::Results ProcessRunner::postRun(', '\nProcessRunner::Results ProcessRunner::attachToProcess('),
    ]:
        assert text.count(start) == 1 and text.count(end) == 1
        a, b = text.index(start), text.index(end)
        body = text[a:b]
        cuts.append(dict(start=start, end=end, textOffset=a, textLength=b-a,
                         sha256=hashlib.sha256(body.encode()).hexdigest(), body=body))
    template = HERE / 'process_driver.cpp'
    generated = template.read_text().replace('// @@SELECTED_METHODS@@', '\n'.join(c['body'] for c in cuts))
    # Authored branch and outcome cases, not an exhaustive product/Windows profile.
    cases = [
        ('unhooked', 0, 1, 1, 1, 2),
        ('unhooked-force', 0, 7, 0, 1, 2),
        ('no-reason', 1, 1, 0, 1, 2),
        ('disabled-gui', 1, 1, 1, 0, 2),
        ('forced-default-reason', 1, 7, 0, 0, 2),
        ('forced-background', 1, 7, 3, 0, 2),
        ('forced-background-unlock', 1, 7, 3, 0, 5),
        ('forced-output', 1, 7, 2, 0, 2),
        ('ordinary-completed', 1, 1, 1, 1, 2),
        ('ordinary-force-unlocked', 1, 1, 1, 1, 5),
        ('ordinary-cancelled', 1, 1, 1, 1, 4),
        ('ordinary-error', 1, 1, 1, 1, 3),
        ('ordinary-running', 1, 1, 1, 1, 1),
        ('wait-refresh-completed', 1, 5, 1, 1, 2),
        ('wait-refresh-unlocked', 1, 5, 1, 1, 5),
        ('wait-refresh-cancelled', 1, 5, 1, 1, 4),
        ('wait-bit-without-trigger', 1, 4, 1, 1, 2),
        ('force-without-refresh', 1, 2, 0, 0, 2),
        ('disabled-no-reason', 1, 5, 0, 0, 5),
        ('unhooked-disabled', 0, 7, 1, 0, 4),
    ]
    fields = ['id', 'hooked', 'flags', 'reason', 'lockEnabled', 'waitResult']
    run = ROOT / 'applications/evidence' / ('mo2-process-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    work = Path(tempfile.mkdtemp(prefix='rules-mo2-process-', dir='/private/tmp'))
    for name in ['tmp', 'cache', 'config']:
        (work / name).mkdir()
    (work / 'main.cpp').write_text(generated)
    (run / 'probe.py').write_bytes(Path(__file__).read_bytes())
    (run / 'driver.cpp').write_bytes(template.read_bytes())
    write(run / 'input.json', dict(schema=1, cases=[dict(zip(fields, row)) for row in cases]))
    payload = ''.join(' '.join(str(x) for x in row) + '\n' for row in cases)
    env = {**os.environ, 'TMPDIR': str(work / 'tmp'), 'XDG_CACHE_HOME': str(work / 'cache'),
           'XDG_CONFIG_HOME': str(work / 'config')}
    commands = []
    def execute(name, argv, data=None):
        p = subprocess.Popen(argv, cwd=work, env=env, stdin=subprocess.PIPE if data else subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            out, err = p.communicate(data, timeout=40)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGTERM)
            try:
                out, err = p.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                out, err = p.communicate()
            raise RuntimeError('Owned research command exceeded bound; retain partial capture')
        (run / (name + '.stdout')).write_text(out)
        (run / (name + '.stderr')).write_text(err)
        try:
            os.killpg(p.pid, 0)
            absent = False
        except ProcessLookupError:
            absent = True
        commands.append(dict(name=name, argv=argv, pid=p.pid, processGroup=p.pid,
                             processGroupAbsent=absent, exitCode=p.returncode,
                             stdoutSha256=sha(run / (name + '.stdout')),
                             stderrSha256=sha(run / (name + '.stderr'))))
        assert p.returncode == 0 and absent, name
        return out
    compiler = Path('/usr/bin/clang++')
    execute('compiler', [str(compiler), '--version'])
    execute('compile', [str(compiler), '-std=c++17', '-Wall', '-Wextra', '-Werror', 'main.cpp', '-o', 'probe'])
    observed = execute('observed', [str(work / 'probe')], payload)
    assert len(observed.splitlines()) == len(cases)
    write(run / 'receipt.json', dict(schema=1, complete=True, work=str(work), cases=len(cases),
        producerSha256=sha(Path(__file__)), driverSha256=sha(template), inputSha256=sha(run / 'input.json'),
        source=source, cuts=[{k: v for k, v in c.items() if k != 'body'} for c in cuts],
        generatedSha256=sha(work / 'main.cpp'), binarySha256=sha(work / 'probe'),
        compilerSha256=sha(compiler), commands=commands,
        limits=['Unchanged selected methods; all Qt, lock, wait, refresh and process APIs are inert adapters.',
                'No Windows child, MO2/Qt UI, live profile, event acknowledgement or persistence qualification.']))
    print(json.dumps(dict(capture=str(run.relative_to(ROOT)), work=str(work), cases=len(cases),
                          allGroupsAbsent=all(r['processGroupAbsent'] for r in commands))))


if __name__ == '__main__':
    main()
