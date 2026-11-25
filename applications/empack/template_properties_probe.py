"""Read the exact retained encoder bytes with installed JDK 17, 21 and 25."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ENCODING = ROOT / 'applications/evidence/empack-template-encoding-20261125T150106975825Z'


def write(p, value):
    p.write_text(json.dumps(value, indent=2) + '\n')


def main():
    previous = json.loads((ENCODING / 'receipt.json').read_text())
    assert previous['complete'] and sha(ENCODING / 'observed.stdout') == previous['commands'][-1]['stdoutSha256']
    run = ROOT / 'applications/evidence' / ('empack-template-properties-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    work = Path(tempfile.mkdtemp(prefix='rules-template-properties-', dir='/private/tmp'))
    (work / 'tmp').mkdir()
    shutil.copyfile(__file__, run / 'probe.py')
    shutil.copyfile(Path(__file__).with_name('TemplatePropertiesProbe.java'), run / 'TemplatePropertiesProbe.java')
    shutil.copyfile(ENCODING / 'observed.stdout', run / 'input.tsv')
    homes = {
        '17': Path('/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home'),
        '21': Path('/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home'),
        '25': Path('/Library/Java/JavaVirtualMachines/25.0.4+101.0.LTS.jdk/Contents/Home'),
    }
    env = dict(PATH='/usr/bin:/bin', LANG='en_US.UTF-8', TMPDIR=str(work / 'tmp'))
    receipt = dict(schema=1, work=str(work), encodingCapture=str(ENCODING.relative_to(ROOT)),
        encodingReceiptSha256=sha(ENCODING / 'receipt.json'), inputSha256=sha(run / 'input.tsv'),
        producerSha256=sha(run / 'probe.py'), driverSha256=sha(run / 'TemplatePropertiesProbe.java'),
        environment=env, commands=[], tools={}, limits=[
            'Properties.load(InputStream) and load(Reader) only; no Minecraft, launcher, VM registry edit, process daemon or game.',
            'Read exact captured Rust properties encoder output, not files from a server build.',
            'Not QSettings/Prism interpretation, cross-platform or Java8 coverage.'])
    write(run / 'receipt.json', receipt)
    def command(label, argv):
        p = subprocess.Popen(argv, env=env, cwd=work, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timed = False
        try:
            out, err = p.communicate(timeout=40)
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
        receipt['commands'].append(dict(label=label, argv=argv, pid=p.pid, exitCode=p.returncode,
            groupAbsent=absent, timedOut=timed, stdoutSha256=sha(run / (label + '.stdout')),
            stderrSha256=sha(run / (label + '.stderr'))))
        write(run / 'receipt.json', receipt)
        assert p.returncode == 0 and absent and not timed, receipt['commands'][-1]
    javac = homes['17'] / 'bin/javac'
    receipt['tools']['javac'] = dict(path=str(javac), sha256=sha(javac))
    command('compiler-version', [str(javac), '-version'])
    command('compile', [str(javac), '--release', '17', '-d', str(work), str(run / 'TemplatePropertiesProbe.java')])
    receipt['classSha256'] = sha(work / 'TemplatePropertiesProbe.class')
    for major, home in homes.items():
        program = home / 'bin/java'
        receipt['tools'][major] = dict(path=str(program), sha256=sha(program), releaseSha256=sha(home / 'release'))
        command('java-' + major, [str(program), '-cp', str(work), 'TemplatePropertiesProbe', str(run / 'input.tsv')])
    receipt['complete'] = True
    receipt['privateKiB'] = int(subprocess.check_output(['du', '-sk', str(work)], text=True).split()[0])
    write(run / 'receipt.json', receipt)
    print(json.dumps(dict(run=str(run), work=str(work), commands=len(receipt['commands']))))


if __name__ == '__main__':
    main()
