"""Exact std-only encoders and addressing with retained real core path types."""
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
SOURCE = Path('/Users/zer0cell/production/empack')
REV = '0b4462e3032b4f09230b15329722eabefb7f574c'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    run = ROOT / 'applications/evidence' / ('empack-template-encoding-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir()
    work = Path(tempfile.mkdtemp(prefix='rules-template-encoding-', dir='/private/tmp'))
    (work / 'tmp').mkdir()
    shutil.copyfile(__file__, run / 'probe.py')
    driver = Path(__file__).with_name('template_encoding_driver.rs')
    shutil.copyfile(driver, run / 'driver.rs')
    rust = Path('/Users/zer0cell/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
    library = ROOT / 'applications/evidence/empack-native-ownership-20261124T031930881554Z/work/core/libempack_core.rlib'
    assert sha(library) == '2631cbfd994f5cb0971ca645313e0fdca67b777617ca8277bfeafd1518f0037f'
    sources = {}
    for suffix in ['templates.rs', 'templates/encoding.rs']:
        path = 'crates/empack-lib/src/engine/' + suffix
        data = subprocess.check_output(['git', 'show', REV + ':' + path], cwd=SOURCE)
        assert (SOURCE / path).read_bytes() == data
        sources[path] = data
    template = sources['crates/empack-lib/src/engine/templates.rs'].decode()
    start = template.index('pub(super) fn template_address(')
    end = template.index('\n/// Render a standalone target', start)
    address = template[start:end]
    # Visibility is the only body edit: the standalone driver has no enclosing
    # engine module. Result's error box is a study adapter, not native anyhow.
    address = address.replace('pub(super) fn ', 'fn ', 1)
    enum_start = template.index('#[derive(Debug, Clone, Copy, PartialEq, Eq)]')
    enum_end = template.index('#[derive(Debug, Clone, Copy)]', enum_start)
    generated = driver.read_text().replace('/*ADDRESS*/', template[enum_start:enum_end] + address)
    generated = generated.replace('/*ENCODING*/', sources['crates/empack-lib/src/engine/templates/encoding.rs'].decode())
    (work / 'driver.rs').write_text(generated)
    values = ['', 'plain', ' a,;=\\"é🦀 ', '@Variant(test)', '@@literal', '\x01aF\n[General]',
        'x\0a', '\nnewline\r\tend', '日本 Ω', 'a\\u0041', '#!=:value', '\u202eabc',
        'é', 'e\u0301', '\x7fA0', 'supplementary 🐈']
    addresses = ['common/file.template', 'client/nested/file', 'server/game/server.properties.template',
        'other/file.template', 'file.template', 'common/file.TEMPLATE', 'common/.template',
        'common/a.template.template', 'common/a//b', 'common/../file', 'common/CON',
        'common/a\\b', 'client/file:bad', 'server/日本.template', 'common/.hidden',
        'Common/file.template', 'common/dir.template/file', 'common/file.']
    rows = [dict(kind='address', value=value) for value in addresses] + [dict(kind='value', value=value) for value in values]
    write(run / 'input.json', dict(schema=1, rows=rows))
    (work / 'input.tsv').write_text(''.join(row['kind'] + '\t' + row['value'].encode().hex() + '\n' for row in rows))
    env = dict(PATH='/usr/bin:/bin', LANG='en_US.UTF-8', TMPDIR=str(work / 'tmp'))
    receipt = dict(schema=1, work=str(work), revision=REV, producerSha256=sha(run / 'probe.py'),
        driverSha256=sha(run / 'driver.rs'), generatedSha256=sha(work / 'driver.rs'),
        inputSha256=sha(run / 'input.json'), inputTsvSha256=sha(work / 'input.tsv'),
        compiler=str(rust), compilerSha256=sha(rust), library=str(library.relative_to(ROOT)),
        librarySha256=sha(library), environment=env, sources=[dict(path=p, sha256=hashlib.sha256(v).hexdigest()) for p, v in sources.items()],
        addressTextRange=[start, end], commands=[], limits=[
            'Selected unchanged address body and full encoding module; only address visibility and error Result host alias differ.',
            'Real retained core path types; this is not WorkspaceSnapshot, Handlebars registration/rendering or complete template preparation.',
            'Scalar encoder outputs are bytes, not consumer interpretation or correct use in arbitrary template syntax.',
            'Small curated UTF-8 inputs only; no malformed Rust string or source acquisition.'])
    write(run / 'receipt.json', receipt)
    def command(label, argv):
        p = subprocess.Popen(argv, cwd=work, env=env, stdin=subprocess.DEVNULL,
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
        row = dict(label=label, argv=argv, pid=p.pid, exitCode=p.returncode, timedOut=timed, groupAbsent=absent,
            stdoutSha256=sha(run / (label + '.stdout')), stderrSha256=sha(run / (label + '.stderr')))
        receipt['commands'].append(row)
        write(run / 'receipt.json', receipt)
        assert p.returncode == 0 and absent and not timed, row
    command('compiler-version', [str(rust), '--version', '--verbose'])
    command('compile', [str(rust), '--edition=2024', str(work / 'driver.rs'), '--extern',
        'empack_core=' + str(library), '-o', str(work / 'probe')])
    receipt['binarySha256'] = sha(work / 'probe')
    write(run / 'receipt.json', receipt)
    command('observed', [str(work / 'probe'), str(work / 'input.tsv')])
    receipt['complete'] = True
    receipt['privateKiB'] = int(subprocess.check_output(['du', '-sk', str(work)], text=True).split()[0])
    write(run / 'receipt.json', receipt)
    print(json.dumps(dict(run=str(run), work=str(work), rows=len(rows))))


if __name__ == '__main__':
    main()
