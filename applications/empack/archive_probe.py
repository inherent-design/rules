"""Small owner-run archive source-fragment/core-API study; no Cargo or engine build."""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
REV = '0b4462e3032b4f09230b15329722eabefb7f574c'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, v): p.write_text(json.dumps(v, indent=2) + '\n')


def make_zip(names):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_STORED) as z:
        for name in names: z.writestr(name, b'payload')
    return out.getvalue()


def main():
    repo = ROOT.parent / 'empack'
    prior = ROOT / 'applications/evidence/empack-native-ownership-20261124T031930881554Z'
    core = json.loads((prior / 'core-receipt.json').read_text())
    library = prior / 'work/core/libempack_core.rlib'
    assert sha(library) == core['librarySha256']
    assert core['sourceRevision'] == REV
    for path, expected in core['sourceTree'].items(): assert sha(repo / path) == expected
    rustc = Path('/Users/zer0cell/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
    assert subprocess.check_output([str(rustc), '--version', '--verbose'], text=True) == core['compiler']
    run = ROOT / 'applications/evidence' / ('empack-archives-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir(); work = Path(tempfile.mkdtemp(prefix='rules-empack-archives-', dir='/private/tmp'))
    (run / 'inputs').mkdir(); (work / 'tmp').mkdir()
    shutil.copyfile(__file__, run / 'probe.py'); shutil.copyfile(HERE / 'archive_driver.rs', run / 'driver.rs')
    source_path = 'crates/empack-lib/src/engine/artifacts.rs'
    raw = subprocess.check_output(['git', '-C', str(repo), 'show', REV + ':' + source_path])
    assert raw == (repo / source_path).read_bytes(); text = raw.decode()
    selectors = [('limits-and-trait', '#[derive(Debug, Clone, Copy)]\npub struct ArchiveLimits', '/// Container bytes'),
                 ('raw-preflight', 'pub(super) fn preflight_zip(', '\n#[cfg(test)]')]
    fragments, parts = [], []
    for name, start, end in selectors:
        a = text.index(start); b = text.index(end, a); part = text[a:b]
        fragments.append(dict(name=name, path=source_path, start=a, end=b, sha256=hashlib.sha256(part.encode()).hexdigest()))
        parts.append(part)
    body = '// Selected empack source; Apache-2.0. See ../../sources/licenses/empack-Apache-2.0.txt.\n'
    body += 'use crate::{Cancellation, Context, Result};\nuse std::io::{Read, Seek, SeekFrom};\n' + '\n'.join(parts)
    (run / 'fragments.rs').write_text(body)
    strings = ['', '.', '..', '/', '/absolute', 'normal.txt', './normal.txt', 'a/../b', 'a//b', 'a\\b',
        'C:/drive', 'C:relative', 'a/C:resource', 'resource:name', 'CON', 'aux.txt', 'LPT9.ext', 'COM0.txt',
        'COM¹.txt', 'trailing.', 'trailing ', 'a?b', 'a*b', 'a|b', 'a<b', 'quote"name', 'a\x00b', 'a\x85b',
        '日本/resource.txt', 'é.txt', 'e\u0301.txt', 'META-INF/services/Test', 'A.class', 'a.class']
    paths = [dict(id='path-' + str(i), value=value) for i, value in enumerate(strings)]
    (run / 'pathcases.rs').write_text('pub fn cases() -> Vec<(&\'static str,Vec<u8>)> { vec![\n' +
        ',\n'.join('("'+r['id']+'",vec!['+','.join(str(v)for v in r['value'].encode())+'])'for r in paths) + '\n] }\n')
    write(run / 'paths.json', paths)
    cases = []
    def case(name, data, limit=20, cancel=-1, mutation=None):
        path = run / 'inputs' / (name + '.zip'); path.write_bytes(data)
        cases.append(dict(id=name, input=str(path.relative_to(ROOT)), sha256=sha(path), bytes=len(data),
                          entryLimit=limit, cancelAfter=cancel, mutation=mutation))
    empty, one, two = make_zip([]), make_zip(['safe.txt']), make_zip(['safe.txt', 'other.txt'])
    case('empty', empty); case('one', one); case('two', two)
    case('case-aliases', make_zip(['A.txt', 'a.txt']))
    case('traversal-name', make_zip(['../outside']))
    case('reserved-name', make_zip(['CON']))
    case('nonportable-punctuation', make_zip(['resource:name']))
    case('unicode-aliases', make_zip(['é.txt', 'e\u0301.txt']))
    # Constructing a duplicate is intentional; the stdlib warning remains visible.
    case('duplicate-raw-name', make_zip(['same.txt', 'same.txt']))
    case('entry-limit', two, limit=1)
    case('cancel-empty', empty, cancel=0); case('cancel-first', one, cancel=0); case('cancel-second', two, cancel=1)
    case('missing-end', b'not a zip')
    case('trailing-junk', one + b'junk')
    def patched(name, data, offset, value, fmt):
        out = bytearray(data); struct.pack_into(fmt, out, offset, value)
        case(name, bytes(out), mutation=dict(offset=offset, value=value, format=fmt))
    end = len(one)-22
    patched('multi-disk', one, end+4, 1, '<H')
    patched('metadata-cap-before-bounds', one, end+12, 16*1024*1024+1, '<I')
    patched('directory-beyond-end', one, end+16, len(one), '<I')
    patched('directory-count-too-small', two, len(two)-22+10, 1, '<H')
    patched('directory-count-too-large', one, end+10, 2, '<H')
    central = one.index(b'PK\x01\x02')
    patched('wrong-central-signature', one, central, 0x12345678, '<I')
    out = bytearray(one); struct.pack_into('<H', out, central+8, 1<<11); out[central+46] = 255
    case('invalid-declared-utf8', bytes(out), mutation='central UTF-8 flag with invalid first name byte; local name unchanged')
    out = bytearray(one); out[central+46] = 255
    case('undeclared-high-byte', bytes(out), mutation='same high central name byte without UTF-8 flag; decoding is outside preflight')
    def zip64(central_size=0, central_offset=0):
        record = struct.pack('<4sQHHIIQQQQ', b'PK\x06\x06', 44, 45, 45, 0, 0, 0, 0, central_size, central_offset)
        locator = struct.pack('<4sIQI', b'PK\x06\x07', 0, 0, 1)
        end = struct.pack('<4sHHHHIIH', b'PK\x05\x06', 0, 0, 0xffff, 0xffff, 0xffffffff, 0xffffffff, 0)
        return record + locator + end
    case('zip64-empty', zip64())
    case('zip64-directory-overflow', zip64(10, (1<<64)-3))
    case('zip64-metadata-cap', zip64(16*1024*1024+1))
    write(run / 'cases.json', cases)
    env = dict(PATH=str(rustc.parent)+':/usr/bin:/bin', TMPDIR=str(work / 'tmp'), LANG='en_US.UTF-8')
    receipt = dict(schema=1, revision=REV, work=str(work), producerSha256=sha(run/'probe.py'),
        source=dict(path=source_path, sha256=hashlib.sha256(raw).hexdigest()), fragments=fragments,
        compiler=dict(path=str(rustc), sha256=sha(rustc), version=core['compiler']),
        core=dict(receipt=str((prior/'core-receipt.json').relative_to(ROOT)), receiptSha256=sha(prior/'core-receipt.json'),
                  library=str(library), librarySha256=sha(library)), commands=[],
        adapters=['Standard-library error/context wrappers; not anyhow error-chain conformance.',
                  'Controlled cancellation callback; not native Cancellation or process retirement.',
                  'Traced std Cursor reads/seeks; actual unchanged raw preflight method.',
                  'Actual public core path APIs from the verified retained current-core library.',
                  'No ZIP payload decoder, extraction, engine or trust witness in this harness.'])
    def command(label, argv):
        result = subprocess.run(argv, cwd=run, env=env, capture_output=True, timeout=30)
        (run/(label+'.stdout')).write_bytes(result.stdout); (run/(label+'.stderr')).write_bytes(result.stderr)
        receipt['commands'].append(dict(label=label,argv=list(map(str,argv)),exitCode=result.returncode,
             stdoutSha256=sha(run/(label+'.stdout')),stderrSha256=sha(run/(label+'.stderr'))))
        write(run/'receipt.json',receipt)
        assert result.returncode==0,(label,result.stderr.decode(errors='replace'))
        return result.stdout.decode()
    binary=work/'archive-driver'
    command('compile',[str(rustc),'--edition=2024','-C','debuginfo=0','--extern','empack_core='+str(library),str(run/'driver.rs'),'-o',str(binary)])
    receipt['binary']=dict(path=str(binary),sha256=sha(binary),bytes=binary.stat().st_size)
    command('paths',[str(binary),'paths'])
    observed=[]
    for row in cases:
        out=command(row['id'],[str(binary),'preflight',str(ROOT/row['input']),str(row['entryLimit']),str(row['cancelAfter'])])
        ok,checks,reads,largest,seeks,error=out.rstrip('\n').split('\t',5)
        observed.append(dict(id=row['id'],accepted=ok=='true',checks=int(checks),readBytes=int(reads),largestBuffer=int(largest),seeks=int(seeks),error=error))
    write(run/'observed.json',observed)
    receipt.update(observedSha256=sha(run/'observed.json'),driverSha256=sha(run/'driver.rs'),fragmentSha256=sha(run/'fragments.rs'),paths=len(paths),preflightCases=len(cases),coreUnchanged=sha(library)==core['librarySha256'])
    write(run/'receipt.json',receipt);(ROOT/'.build/empack-archives-current').write_text(str(run)+'\n')
    print(json.dumps(dict(run=str(run),work=str(work),paths=len(paths),preflightCases=len(cases))))


if __name__=='__main__':main()
