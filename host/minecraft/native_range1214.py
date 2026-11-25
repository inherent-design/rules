#!/usr/bin/env python3
"""Owner-run original range-index method on a closed, sorted integer-valued profile."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import zipfile
from mappings import read as read_mappings

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'java'))
from arena_probe import command
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['client', 'mappings', 'metadata', 'libraries', 'jdk', 'private']:
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    target = next(t for t in json.loads((HERE / 'targets.json').read_text())['javaReferences'] if t['release'] == '1.21.4')
    assert sha(args.client) == target['source']['clientSha256'] and sha(args.metadata) == target['source']['metadataSha256']
    metadata = json.loads(args.metadata.read_text())
    assert hashlib.sha1(args.mappings.read_bytes()).hexdigest() == metadata['downloads']['client_mappings']['sha1']
    libraries = json.loads(args.libraries.read_text())
    assert libraries['target'] == target['id'] and libraries['metadataSha256'] == sha(args.metadata)
    for r in libraries['libraries']:
        assert sha(Path(r['path'])) == r['sha256']
    jdk = args.jdk.resolve()
    fields = dict(re.findall(r'^([A-Z_]+)="([^"]*)"', (jdk / 'release').read_text(), re.M))
    assert fields['JAVA_VERSION'].startswith('21.')
    original_name = 'net.minecraft.client.renderer.item.RangeSelectItemModel'
    mapping = read_mappings(args.mappings)[original_name]
    bindings = dict(originalName=original_name, **{'class': mapping['name']},
                    method=mapping['methods']['lastIndexLessOrEqual(float[],float)'])
    requests_raw = (HERE / 'range1214_cases.json').read_bytes()
    requests = json.loads(requests_raw)
    assert requests['profile'] == target['id'] and len(requests['cases']) == 76
    for r in requests['cases']:
        a = r['thresholds']; q = r['query']
        assert type(a) is list and len(a) <= 32 and a == sorted(a)
        assert all(type(n) is int and 0 <= n <= 32 for n in a) and type(q) is int and -1 <= q <= 32
    capture = args.private.resolve() / ('range-1.21.4-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    capture.mkdir(parents=True, exist_ok=False)
    for n in ['classes', 'home', 'tmp']:
        (capture / n).mkdir()
    sources = [Path(__file__), HERE / 'Range1214Probe.java', HERE / 'range1214_cases.json', HERE / 'mappings.py', HERE.parent / 'java/arena_probe.py']
    for p in sources:
        shutil.copyfile(p, capture / p.name)
    (capture / 'bindings.json').write_text(json.dumps(bindings, indent=2) + '\n')
    shutil.copyfile(args.libraries, capture / 'library-input.json')
    with zipfile.ZipFile(args.client) as archive:
        member = mapping['name'].replace('.', '/') + '.class'
        original_sha = hashlib.sha256(archive.read(member)).hexdigest()
    record = dict(schema=1, target=target['id'], clientSha256=sha(args.client), metadataSha256=sha(args.metadata),
        mappingSha256=sha(args.mappings), originalClassMember=member, originalClassSha256=original_sha,
        sourcesSha256={p.name: sha(capture / p.name) for p in sources}, bindingsSha256=sha(capture / 'bindings.json'),
        libraryReceiptSha256=sha(capture / 'library-input.json'), libraries=libraries['libraries'],
        jdkReleaseSha256=sha(jdk / 'release'), profile={k: fields[k] for k in ['JAVA_VERSION', 'JAVA_RUNTIME_VERSION', 'IMPLEMENTOR', 'OS_NAME', 'OS_ARCH']},
        tools={n: dict(path=str(jdk / 'bin' / n), sha256=sha(jdk / 'bin' / n)) for n in ['java', 'javac']}, commands=[],
        scope='Original private static range-index method only; sorted integer-valued floats. No item property evaluation, baking, render update, model lookup, game entrypoint or provider fixture.')
    def save():
        (capture / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
    env = dict(os.environ, TMPDIR=str(capture / 'tmp'))
    classpath = os.pathsep.join(r['path'] for r in libraries['libraries'])
    save()
    argv = [str(jdk / 'bin/javac'), '-J-XX:ActiveProcessorCount=2', '-J-Xmx128m', '--release', '21', '-proc:none', '-Xlint:all,-classfile', '-Werror', '-encoding', 'UTF-8', '-cp', classpath, '-d', str(capture / 'classes'), str(capture / 'Range1214Probe.java')]
    result = command(argv, capture, 'compile', env, 30)
    record['commands'].append(result); save()
    assert result['exitCode'] == 0 and result['ownedGroupAbsent'] and not result['timedOut'], capture
    argv = [str(jdk / 'bin/java'), '-XX:ActiveProcessorCount=2', '-Xmx256m', '-Djava.awt.headless=true', '-Duser.home=' + str(capture / 'home'), '-Djava.io.tmpdir=' + str(capture / 'tmp'), '-Xlog:class+load=info:file=' + str(capture / 'class-load.log'), '-cp', os.pathsep.join([str(capture / 'classes'), str(args.client.resolve()), classpath]), 'study.minecraft.Range1214Probe', str(capture / 'bindings.json'), str(capture / 'range1214_cases.json'), str(capture / 'observed.json')]
    result = command(argv, capture, 'execute', env, 30)
    record['commands'].append(result)
    record['observerClassSha256'] = sha(capture / 'classes/study/minecraft/Range1214Probe.class')
    if (capture / 'observed.json').exists():
        observed = json.loads((capture / 'observed.json').read_text())
        record.update(cases=len(observed['cases']), observerErrors=observed['observerErrors'], observedSha256=sha(capture / 'observed.json'))
    if (capture / 'class-load.log').exists():
        record['classLoadLogSha256'] = sha(capture / 'class-load.log')
    save()
    assert sha(args.client) == record['clientSha256'] and all(sha(capture / n) == h for n, h in record['sourcesSha256'].items())
    assert all(sha(Path(r['path'])) == r['sha256'] for r in libraries['libraries'])
    (args.private / 'latest-range1214.json').write_text(json.dumps(dict(capture=str(capture))) + '\n')
    print(json.dumps(dict(capture=str(capture), exitCode=result['exitCode'], cases=record.get('cases'), observerErrors=record.get('observerErrors'), ownedGroupsAbsent=all(c['ownedGroupAbsent'] for c in record['commands']))))
    assert result['exitCode'] == 0 and result['ownedGroupAbsent'] and not result['timedOut'] and record.get('observerErrors') == 0, capture


if __name__ == '__main__':
    main()
