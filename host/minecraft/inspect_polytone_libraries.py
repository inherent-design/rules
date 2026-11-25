#!/usr/bin/env python3
"""Owner-run inspection of exact bundled libraries; no provider or library execution."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import sys
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'java'))
from arena_probe import command

PARENT_SHA256 = '7c78b6f425d84a85dc1dcdc6d2d00073fbe16f9de0217325467d9d218a5cd96d'
TOOL_SHA256 = '1dfcfe974395734fa467ce620661c7623d05ba83670de0529b1fbd63ff548b9d'
MEMBERS = {
    'META-INF/jarjar/codecui-neoforge-1.21.1-1.4.10.jar',
    'META-INF/jarjar/exp4j-0.4.8.jar',
    'META-INF/jarjar/nexp-1.2.1.jar',
}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def inventory(raw):
    """Read class headers as data, without resolving, linking, or initializing classes."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)), 'Duplicate ZIP names'
        assert sum(i.file_size for i in archive.infolist()) < 8 * 1024 * 1024
        classes = {}
        for name in names:
            path = PurePosixPath(name)
            assert not path.is_absolute() and '..' not in path.parts
            if not name.endswith('.class'):
                continue
            data = archive.read(name)
            assert len(data) >= 8 and data[:4] == b'\xca\xfe\xba\xbe'
            minor, major = struct.unpack('>HH', data[4:8])
            classes[name] = dict(sha256=hashlib.sha256(data).hexdigest(), minor=minor, major=major)
        return dict(classes=classes,
            nestedArchives=[n for n in names if n.endswith(('.jar', '.zip'))],
            nativePayloadCandidates=[n for n in names if n.lower().endswith(('.dll', '.dylib', '.so', '.exe'))],
            licenseEntries=[n for n in names if any(word in n.lower() for word in ['license', 'notice', 'copying'])])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['artifact', 'jdk', 'decompiler', 'private']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    assert sha(args.artifact) == PARENT_SHA256 and sha(args.decompiler) == TOOL_SHA256
    jdk = args.jdk.resolve()
    fields = dict(re.findall(r'^([A-Z_]+)="([^"]*)"', (jdk / 'release').read_text(), re.M))
    assert fields['JAVA_VERSION'].startswith('21.'), 'Select explicit JDK21 inspection host'
    with zipfile.ZipFile(args.artifact) as archive:
        metadata = archive.read('META-INF/jarjar/metadata.json')
        declarations = json.loads(metadata)['jars']
        assert {row['path'] for row in declarations} == MEMBERS and len(declarations) == 3
        inputs = {row['path']: archive.read(row['path']) for row in declarations}
    assert sum(map(len, inputs.values())) < 512 * 1024
    capture = args.private.resolve() / ('polytone-libraries-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    capture.mkdir(parents=True)
    for name in ['inputs', 'source', 'home', 'tmp']:
        (capture / name).mkdir()
    for source in [Path(__file__), HERE.parent / 'java/arena_probe.py']:
        shutil.copyfile(source, capture / source.name)
    (capture / 'metadata.json').write_bytes(metadata)
    record = dict(schema=1, scope='Bundled library byte/header and decompiled-view inspection; no provider/library linking or execution, no resolved runtime library selection.',
        parentSha256=PARENT_SHA256, metadataSha256=sha(capture / 'metadata.json'),
        decompilerSha256=TOOL_SHA256, javaSha256=sha(jdk / 'bin/java'), jdkReleaseSha256=sha(jdk / 'release'),
        profile={key: fields[key] for key in ['JAVA_VERSION', 'JAVA_RUNTIME_VERSION', 'IMPLEMENTOR', 'OS_NAME', 'OS_ARCH']},
        producersSha256={name: sha(capture / name) for name in ['inspect_polytone_libraries.py', 'arena_probe.py']},
        libraries=[], limits=['Bundled artifact version and accepted range do not identify the runtime-selected dependency.',
            'Class headers and suffix-based native payload searches do not prove runtime requirements or effect closure.',
            'Decompiled views are not upstream source or proved semantic inverses.',
            'JVM heap/processor settings do not bound physical memory or host-wide concurrency.'])
    def save():
        (capture / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
    save()
    env = dict(os.environ, TMPDIR=str(capture / 'tmp'))
    for declaration in declarations:
        raw = inputs[declaration['path']]
        name = PurePosixPath(declaration['path']).name
        artifact = capture / 'inputs' / name
        artifact.write_bytes(raw)
        views = capture / 'source' / declaration['identifier']['artifact']
        views.mkdir()
        entry = dict(declaration=declaration, sha256=sha(artifact), bytes=len(raw), **inventory(raw))
        record['libraries'].append(entry)
        save()
        argv = [str(jdk / 'bin/java'), '-XX:ActiveProcessorCount=2', '-Xmx256m', '-Djava.awt.headless=true',
            '-Duser.home=' + str(capture / 'home'), '-Djava.io.tmpdir=' + str(capture / 'tmp'),
            '-jar', str(args.decompiler.resolve()), '--folder', '--log-level=WARN', str(artifact), str(views)]
        entry['command'] = command(argv, capture, declaration['identifier']['artifact'], env, 60)
        entry['viewsSha256'] = {str(p.relative_to(views)): sha(p) for p in sorted(views.rglob('*.java'))}
        save()
        assert entry['command']['exitCode'] == 0 and entry['command']['ownedGroupAbsent'] and not entry['command']['timedOut'], capture
    assert sha(args.artifact) == PARENT_SHA256 and sha(args.decompiler) == TOOL_SHA256
    assert sha(jdk / 'bin/java') == record['javaSha256'] and sha(jdk / 'release') == record['jdkReleaseSha256']
    assert all(sha(capture / name) == value for name, value in record['producersSha256'].items())
    print(json.dumps(dict(capture=str(capture), libraries=len(record['libraries']),
        classes=sum(len(e['classes']) for e in record['libraries']), views=sum(len(e['viewsSha256']) for e in record['libraries']),
        inputBytes=sum(e['bytes'] for e in record['libraries']), ownedGroupsAbsent=all(e['command']['ownedGroupAbsent'] for e in record['libraries']))))


if __name__ == '__main__':
    main()
