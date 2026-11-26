"""Compare finite models with retained archive observations; no native app execution."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil
import tempfile
from observations import ROOT, RUN, load, packets

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
write = lambda p, v: p.write_text(json.dumps(v, indent=2) + '\n')


def evidence(include_private=True):
    receipt, setup = load(RUN / 'receipt.json'), load(RUN / 'setup.json')
    assert receipt['cases'] == 8 and receipt['sourceComponentOnly'] and receipt['allGroupsAbsent']
    assert sha(RUN / 'probe.py') == setup['producerSha256'] and sha(RUN / 'driver.cpp') == setup['templateSha256']
    commands = load(RUN / 'commands.json')
    assert len(commands) == 2 and [c['label'] for c in commands] == ['compile', 'observe']
    for c in commands:
        assert c['exitCode'] == 0 and not c['timedOut'] and c['groupAbsent']
        for stream in ['stdout', 'stderr']:
            assert sha(RUN / (c['label'] + '.' + stream)) == c[stream + 'Sha256']
    checks, excluded = [], []
    artifacts = [(setup['compiler']['path'], setup['compiler']['sha256']),
                 (str(Path(setup['sdk']['path']) / 'SDKSettings.json'), setup['sdk']['settingsSha256']),
                 (str(Path(receipt['work']) / 'main.cpp'), receipt['generatedSourceSha256']),
                 (str(Path(receipt['work']) / 'probe'), receipt['binarySha256'])]
    artifacts += [(v['path'], v['sha256']) for v in setup['archive'].values()]
    # Qt path is part of the compile link flags; no new pkg-config/compiler run.
    qt = Path('/opt/homebrew/opt/qtbase/lib/QtCore.framework/Versions/A/QtCore')
    artifacts.append((str(qt), setup['qtCoreSha256']))
    for path, digest in artifacts:
        p = Path(path)
        if include_private and p.exists():
            assert sha(p) == digest
            checks.append(path)
        else:
            excluded.append(path)
    sources = {}
    ledger = load(ROOT / 'applications/sources/prism-export-selections.json')
    for row in ledger['sources']:
        p = ROOT / row['cache']
        if include_private and p.exists():
            raw = p.read_bytes()
            assert sha(p) == row['sha256'] and hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['gitBlob']
            sources[row['path']] = raw.decode()
        else:
            excluded.append(row['cache'])
    if all(r['path'] in sources for r in setup['excerpts']):
        sys.path.insert(0, str(ROOT / 'applications/prism'))
        from accounts_probe import function
        bodies = []
        for r in setup['excerpts']:
            body = function(sources[r['path']], r['signature'])
            assert hashlib.sha256(body.encode()).hexdigest() == r['originalSha256']
            compiled = body.replace('ExportToZipTask::exportZip', 'ExportHarness::exportZip', 1) if r['transformation'] != 'none' else body
            assert hashlib.sha256(compiled.encode()).hexdigest() == r['compiledSha256']
            bodies.append(compiled)
        generated = (RUN / 'driver.cpp').read_text()
        for name, body in [('WRITER', '\n'.join(bodies[:6])), ('COLLECTOR', bodies[6]), ('EXPORT', bodies[7])]:
            generated = generated.replace('// @' + name + '@', body)
        assert hashlib.sha256(generated.encode()).hexdigest() == setup['generatedSourceSha256']
    for suffix in ['20261126T074735022094Z', '20261126T074924322822Z']:
        failed = ROOT / 'applications/evidence' / ('prism-export-headless-' + suffix)
        c = load(failed / 'commands.json')
        assert len(c) == 1 and c[0]['label'] == 'compile' and c[0]['exitCode'] == 1 and c[0]['groupAbsent']
        assert not (failed / 'observe.stdout').exists()
        assert sha(failed / 'compile.stderr') == c[0]['stderrSha256']
    return dict(availableSourcePins=len(sources), retainedArtifacts=checks, unavailablePrivateInputs=excluded)


def main():
    identities = evidence(os.environ.get('PRISM_EXPORT_PRIVATE', '1') != '0')
    inputs, expected, content = packets()
    write(RUN / 'model-input.json', inputs);write(RUN / 'observed-model-values.json', expected);write(RUN / 'content-observations.json', content)
    formal = ROOT / '.build/prism-export-replay'
    formal.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'LEAN_PATH': os.environ.get('PRISM_EXPORT_FORMAL', str(ROOT / '.build/formal')), 'BEND_NO_TELEMETRY': '1'}
    lean, bend = os.environ['LEAN'], os.environ['BEND']
    cmd = [lean, '--run', 'applications/prism/ExportCase.lean']
    result = subprocess.run(cmd + [str(RUN / 'model-input.json')], cwd=ROOT, env=env, text=True, capture_output=True, check=True)
    actual = json.loads(result.stdout)
    assert actual == expected, 'Export model differs from retained archive observations'
    bo = lambda b: 'True{}' if b else 'False{}'
    calls, wanted = [], []
    for r, v in zip(inputs['cases'], expected, strict=True):
        entries = '[' + ','.join('[' + ','.join(str(int(e[n])) + 'n' for n in ['id','leafHidden','excluded','missingAtWrite','link']) + ']' for e in r['entries']) + ']'
        s = 'P.state(' + ','.join([bo(r['rootExists']), bo(r['outputDirectory']), bo(r['canceled']), bo(any(not e['leafHidden'] and not e['excluded'] for e in r['entries'])), bo(bool(r['extras'])), entries]) + ')'
        calls += ['P.selected(' + entries + ')' if r['rootExists'] else '""', 'Nat.show(' + s + ')', 'Bool.show(P.error_present(' + s + '))',
                  'Bool.show(P.output_replaced(' + bo(r['rootExists']) + ',' + bo(r['outputDirectory']) + '))', 'Bool.show(P.completed(' + s + ',' + bo(r['canceled']) + '))']
        wanted += [''.join(str(x) + ',' for x in v['selected']), str(v['state']), str(v['errorPresent']), str(v['outputReplaced']), str(v['completed'])]
        for m in v['members']:
            if m['id'] in r['extras']:
                continue
            e = next(e for e in r['entries'] if e['id'] == m['id'])
            calls.append('Bool.show(P.retained_link(' + bo(e['link']) + ',' + bo(r['follow']) + '))');wanted.append(str(m['link']))
    target = formal / 'Replay.bend'
    target.write_text('import ../../applications/prism/Export.bend as P\nimport Base\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ "\\n" ++ '.join(calls) + ' ++ "\\n")\n')
    result = subprocess.run([bend, str(target)], cwd=ROOT, env=env, text=True, capture_output=True, check=True)
    assert result.stdout.splitlines() == wanted
    controls = []
    for label, case, field, change in [('cancellation-as-completion','canceled-witness','completed',True),('partial-as-complete','vanished-input','state',2),
            ('failed-write-preserves-prior','vanished-input','outputReplaced',False),('empty-selection-as-no-output','empty-selection','outputReplaced',False),
            ('missing-root-invokes-writer','missing-root','state',2)]:
        altered = copy.deepcopy(expected);next(r for r in altered if r['id'] == case)[field] = change
        assert altered != actual;controls.append(label)
    for label, change in [('schema',lambda d:d.update(schema=2)),('placement',lambda d:d['cases'][0].update(placement=2)),
            ('duplicate-entry',lambda d:d['cases'][0]['entries'].append(d['cases'][0]['entries'][0])),
            ('entry-id',lambda d:d['cases'][0]['entries'][0].update(id=32)),('extra-id',lambda d:d['cases'][0].update(extras=[32]))]:
        altered = copy.deepcopy(inputs);change(altered);p = formal / (label + '.json');write(p,altered)
        r = subprocess.run(cmd + [str(p)],cwd=ROOT,env=env,text=True,capture_output=True)
        assert r.returncode == 2 and 'research' in r.stderr;controls.append(label)
    # Downstream premises: changing the inputs must change the independently observed result.
    for label, case, change in [('include-hidden-leaf','instance-follow',lambda r: next(e for e in r['entries'] if e['leafHidden']).update(leafHidden=False)),
            ('retain-symlink','instance-follow',lambda r: r.update(follow=False)),('remove-prefix','game-filter-prefix',lambda r:r.update(placement=0))]:
        altered = copy.deepcopy(inputs);change(next(r for r in altered['cases'] if r['id']==case));p = formal/(label+'.json');write(p,altered)
        r = subprocess.run(cmd+[str(p)],cwd=ROOT,env=env,text=True,capture_output=True,check=True)
        assert json.loads(r.stdout) != actual;controls.append(label)
    # Corrupt copied observations, never the retained originals or native fixtures.
    for label in ['archive-bytes', 'source-bytes', 'link-target', 'false-collector-refusal']:
        with tempfile.TemporaryDirectory(prefix='raw-control-', dir=formal) as directory:
            copied = Path(directory) / 'capture'
            shutil.copytree(RUN, copied)
            if label == 'archive-bytes':
                p = copied / 'outputs/instance-follow.zip';p.write_bytes(p.read_bytes() + b'changed')
            elif label in ['source-bytes', 'link-target']:
                p = copied / 'before.json';data = load(p)
                name = 'instance-follow/instance/.minecraft/config/' + ('visible.txt' if label == 'source-bytes' else 'linked.txt')
                data[name]['sha256' if label == 'source-bytes' else 'target'] = 'changed';write(p,data)
            else:
                p = copied / 'observe.stdout';data = [json.loads(s) for s in p.read_text().splitlines()]
                data[1]['collected'] = False;p.write_text(''.join(json.dumps(r) + '\n' for r in data))
            try:
                packets(copied)
            except (AssertionError, ValueError):
                controls.append(label)
            else:
                raise AssertionError('Changed raw evidence escaped: ' + label)
    report = dict(schema=1,nativeSourceCases=8,leanLaws=16,bendLaws=10,bendScalarComparisons=len(calls),archiveContentObservations=len(content['contents']),
                  controls=controls,evidence=identities,limits=['Source-component execution; no normal Prism GUI export or bundled dependency qualification.',
                  'Directory traversal order admitted for owned ASCII fixture names; no symlink-directory cycles, filesystem races, or portable ordering proof.',
                  'Constant cancellation and exact exclusion callbacks are adapters; no QFuture, FileIgnoreProxy, Task cleanup, or atomic publication executed.',
                  'Lean predicts selected entries, writer state and member identity/link role; Bend compares selection/state/effect/completion and written link roles, not ZIP encoding.',
                  'Installed Mac launcher GUI run interrupted and produced zero exports; possible overlapping human focus, not an attributed product/automation defect.'])
    write(RUN/'conformance.json',report)
    files=[p for p in RUN.rglob('*') if p.is_file() and p.name not in ['basis.json','conformance.json']]
    files += [HERE/n for n in ['headless_probe.py','headless_driver.cpp','observations.py','conformance.py']]
    files += [ROOT/'applications/prism'/n for n in ['Export.lean','ExportCase.lean','Export.bend']]
    files.append(ROOT/'applications/sources/prism-export-selections.json')
    write(RUN/'basis.json',{str(p.relative_to(ROOT)):sha(p)for p in files})
    print(json.dumps({k:v for k,v in report.items()if k!='evidence'},indent=2))


if __name__ == '__main__':main()
