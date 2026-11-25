#!/usr/bin/env python3
"""Read-only original-source and retained Qt observation checks; no app/JVM."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'applications/evidence/prism-java-20261125T054951238691Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def original(text, signature, expected):
    assert text.count(signature) == 1
    start = text.index(signature)
    for end in range(start, min(start + 16000, len(text))):
        if text[end] == '}' and hashlib.sha256(text[start:end + 1].encode()).hexdigest() == expected:
            return text[start:end + 1]
    raise AssertionError(signature)


def normalized(c):
    if c['kind'] == 'setting':
        actions = []
        for a in c['actions']:
            item = dict(op=a['op'])
            if a['op'] in ['set', 'global']:
                item['text'] = a['value']
            if a['op'] == 'gate':
                item['flag'] = a['value']
            actions.append(item)
        return dict(kind='setting', setting=dict(passthrough=c['passthrough'], gate=c['gate'],
                    globalDefault=c['globalDefault'], globalValue=c['global'], localValue=c['local'], actions=actions))
    s = c['stored']
    return dict(kind='pipeline', pipeline=dict(executable=c['executable'], checkerAvailable=c['checkerAvailable'],
                override=c['override'], signatureMatches=c['signatureMatches'], memory=c['memory'],
                ignore=c['ignore'], majors=c['majors'], probe=c['probe'],
                stored=dict(version=s['JavaVersion'], architecture=s['JavaArchitecture'],
                            realArchitecture=s['JavaRealArchitecture'], vendor=s['JavaVendor']),
                result=dict(version=c['resultVersion'], architecture=c['resultArch'],
                            realArchitecture='aarch64', vendor='fixture-vendor')))


def measured(row):
    if row['kind'] == 'setting':
        return ';'.join('|'.join([s['global'], '-' if s['local'] is None else s['local'], s['effective'], s['default']]) for s in row['trace'])
    b = lambda v: '1' if v else '0'
    mem = any(s['text'].startswith('Max memory allocation exceeds') for s in row['verifyLogs'])
    ignored = any(s['text'].startswith('Java major version is incompatible.') for s in row['verifyLogs'])
    invalid = any(s['text'].startswith('Java checker returned some invalid data') for s in row['checkLogs'])
    fields = [b(row['probed']), b(row['checkSucceeded']), b(row['checkFailed']), b(row['verifyCalled']),
              b(row['verifySucceeded']), b(row['verifyFailed']), b(mem), b(ignored), b(invalid),
              b(row['signatureMatchesAfter']), str(row['selectedMajor'])]
    keys = ['JavaVersion', 'JavaArchitecture', 'JavaRealArchitecture', 'JavaVendor']
    fields += [row['effective'][k] for k in keys]
    fields += [row['localStored'].get(k, '-') for k in keys]
    return '|'.join(fields)


def inspect():
    receipt = json.loads((RUN / 'receipt.json').read_text())
    inputs = json.loads((RUN / 'input.json').read_text())['cases']
    outputs = [json.loads(s) for s in (RUN / 'observe.stdout').read_text().splitlines()]
    assert len(inputs) == len(outputs) == receipt['cases'] == 37
    assert [c['id'] for c in inputs] == [o['id'] for o in outputs]
    assert len({o['id'] for o in outputs}) == 37
    assert sha(RUN / 'probe.py') == receipt['producerSha256'] == sha(ROOT / 'applications/prism/java_probe.py')
    assert receipt['allOwnedGroupsAbsent'] and all(p['retired'] for p in json.loads((RUN / 'owned-processes.json').read_text()))
    commands = json.loads((RUN / 'commands.json').read_text())
    assert [c['case'] for c in commands] == ['moc-Setting', 'moc-OverrideSetting', 'moc-PassthroughSetting', 'compile', 'observe']
    for c in commands:
        assert c['exitCode'] == 0 and not c['timedOut'] and c['ownedGroupAbsent']
        for stream, expected in c['streams'].items():
            assert sha(RUN / (c['case'] + '.' + stream)) == expected
    work = RUN / 'work'
    for path, expected in [('main.cpp', receipt['generatedSourceSha256']), ('probe', receipt['binarySha256']),
                           ('settings/SettingsObject.h', receipt['storageAdapterSha256']),
                           ('java-fixture', receipt['executableWitnessSha256'])]:
        assert sha(work / path) == expected
    ledger = json.loads((ROOT / 'applications/sources/prism-java-selections.json').read_text())
    tree = {s['path']: s for s in json.loads((ROOT / 'applications/tools/source-cache/prism-tree.json').read_text())['tree']}
    selected = {s['path']: s for s in ledger['sources']}
    for path, s in selected.items():
        data = (ROOT / s['cache']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == s['sha256']
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert blob == s['gitBlobSha1'] == tree[path]['sha']
    for path, h in receipt['copiedSources'].items():
        assert sha(work / Path(path).name) == h == selected[path]['sha256']
    generated = (work / 'main.cpp').read_text()
    for s in receipt['excerpts']:
        body = original((ROOT / selected[s['path']]['cache']).read_text(), s['signature'], s['sha256'])
        assert s['transformation'] == 'none' and generated.count(body) == 1
    assert len(receipt['excerpts']) == 7
    assert receipt['qtVersion'] == '6.12.0' and all(o['qtRuntime'] == '6.12.0' for o in outputs)
    assert sha(Path(receipt['moc']['path'])) == receipt['moc']['sha256']
    compile_argv = next(c['argv'] for c in commands if c['case'] == 'compile')
    qt_paths = [a.removeprefix('-Wl,-rpath,') for a in compile_argv if a.startswith('-Wl,-rpath,')]
    assert len(qt_paths) == 1
    qt = Path(qt_paths[0]) / 'QtCore.framework/Versions/A/QtCore'
    assert sha(qt) == receipt['frameworkSha256']
    readback = json.loads((RUN / 'toolchain-readback.json').read_text())
    for name in ['compilerShim', 'compilerResolved', 'installedPrismBinary']:
        assert sha(Path(readback[name]['path'])) == readback[name]['sha256']
    assert readback['installedPrismBinary']['sha256'] == '590fad2e7feaed261ff5f772addd0670ce2a653218023e3fb4dca5bb3b10e489'
    assert not readback['installedPrismBinary']['executed']
    signature = hashlib.sha1((str((work / 'java-fixture').stat().st_mtime_ns // 1000000) + str(work / 'java-fixture')).encode()).hexdigest()
    for c, row in zip(inputs, outputs):
        assert c['kind'] == row['kind']
        if c['kind'] == 'setting':
            assert len(row['trace']) == len(c['actions']) + 1
            assert row['trace'][0]['global'] == c['global'] and row['trace'][0]['local'] == c['local']
            continue
        assert row['contextUpdates'] == (1 if row['checkSucceeded'] else 0)
        assert row['signatureMatchesAfter'] == row['globalSignatureMatchesAfter']
        for key in row['effective']:
            assert row['effective'][key] == row['globalStored'][key]
        if c['executable']:
            assert row['signatureMatchesAfter'] == (row['effective']['JavaSignature'] == signature)
        if row['verifyFailed']:
            assert row['verifyReason'] == 'Incompatible Java major version'
        if not row['verifyCalled']:
            assert not row['verifySucceeded'] and not row['verifyFailed'] and not row['verifyLogs']
    by = {r['id']: r for r in outputs}
    assert by['equal-write-1']['trace'][1]['local'] is None
    assert by['equal-write-1']['trace'][2]['effective'] == 'changed'
    assert by['settings-1-1-1']['trace'][-1]['local'] == 'written'
    assert by['settings-1-1-1']['trace'][-1]['global'] == 'default'
    assert by['probe-1-1']['verifySucceeded'] and by['probe-1-1']['selectedMajor'] == 21
    assert not by['probe-1-1']['signatureMatchesAfter']
    assert by['probe-1-2']['globalStored']['JavaVersion'] == '25.0.1'
    assert by['probe-1-2']['localStored']['JavaVersion'] == '25.0.1'
    assert 'JavaArchitecture' not in by['probe-1-2']['localStored']
    assert by['invalid-probe-empty-version']['selectedMajor'] == 0 and by['invalid-probe-empty-version']['verifyFailed']
    assert by['invalid-probe-empty-no-requirement']['verifySucceeded']
    assert 'instance' in by['missing-instance-executable']['checkLogs'][0]['text']
    assert 'instance' not in by['missing-global-executable']['checkLogs'][0]['text']
    return receipt, inputs, outputs


if __name__ == '__main__':
    r, i, o = inspect()
    print(json.dumps(dict(cases=len(o), sourceFiles=26, copiedFiles=len(r['copiedSources']), unchangedMethods=7,
                          fullApplicationQualification=False, javaProcesses=0)))
