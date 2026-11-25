#!/usr/bin/env python3
"""Pure replay of retained Prism setting/check components; no Qt/JVM launch."""
import copy
import json
import os
from pathlib import Path
import subprocess
import java_observations as observations

ROOT, RUN = observations.ROOT, observations.RUN
HERE = Path(__file__).resolve().parent
sha = observations.sha


def bend_call(row):
    s = json.dumps
    b = lambda v: 'True{}' if v else 'False{}'
    n = lambda v: str(v) + 'n'
    ls = lambda values: '[' + ','.join(values) + ']'
    if row['kind'] == 'setting':
        r = row['setting']
        optional = 'None{}' if r['localValue'] is None else 'Some{' + s(r['localValue']) + '}'
        state = 'S.S{' + ','.join([b(r['passthrough']), b(r['gate']), s(r['globalDefault']), s(r['globalValue']), optional]) + '}'
        actions = []
        for a in r['actions']:
            actions.append(dict(set=lambda: 'S.Set{' + s(a['text']) + '}',
                                global_=lambda: 'S.Global{' + s(a['text']) + '}',
                                gate=lambda: 'S.Gate{' + b(a['flag']) + '}', reset=lambda: 'S.Reset{}')[a['op'].replace('global', 'global_')]())
        return 'S.trace(' + ls(actions) + ',' + state + ')'
    r = row['pipeline']

    def metadata(m):
        major = {'21.0.1': 21, '25.0.1': 25, '1.8.0_452': 8, 'unknown': 0, '': 0}[m['version']]
        return 'S.M{' + ','.join([s(m['version']), n(major), s(m['architecture']), s(m['realArchitecture']), s(m['vendor'])]) + '}'

    return 'S.run(S.I{' + ','.join([b(r['executable']), b(r['checkerAvailable']), b(r['override']), b(r['signatureMatches']),
           metadata(r['stored']), n(r['probe']), metadata(r['result']), n(r['memory']), b(r['ignore']), ls([n(v) for v in r['majors']])]) + '})'


def compare(a, b):
    assert a == b, (a, b)


def main():
    receipt, inputs, outputs = observations.inspect()
    rows = [observations.normalized(c) for c in inputs]
    expected = [observations.measured(o) for o in outputs]
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    env = dict(os.environ, LEAN_PATH=str(ROOT / '.build/formal'), BEND_NO_TELEMETRY='1')
    target = ROOT / '.build/formal/applications/prism/Java.olean'
    target.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run([lean, '-DwarningAsError=true', '-o', str(target), 'applications/prism/Java.lean'],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
    assert p.returncode == 0, p.stdout + p.stderr
    path = generated / 'java.json'
    data = dict(schema=1, profile='prism-settings-injected-probe', rows=rows)

    def replay(value):
        path.write_text(json.dumps(value) + '\n')
        return subprocess.run([lean, '--run', 'applications/prism/JavaCase.lean', str(path)], cwd=ROOT,
                              env=env, capture_output=True, text=True, timeout=90)

    p = replay(data)
    assert p.returncode == 0, p.stdout + p.stderr
    actual = json.loads(p.stdout)
    compare(expected, actual)
    driver = generated / 'JavaCase.bend'
    driver.write_text('import Base\nimport ../Java.bend as S\n\ndef main() -> IO(Unit):\n  IO.write(' +
                      ' ++ '.join('(' + bend_call(r) + ' ++ "\\n")' for r in rows) + ')\n')
    p = subprocess.run([bend, str(driver)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
    assert p.returncode == 0, p.stdout + p.stderr
    compare(expected, p.stdout.splitlines())
    refusals = []
    edits = [
        ('schema', lambda d: d.update(schema=2)), ('profile', lambda d: d.update(profile='full-prism')),
        ('empty', lambda d: d.update(rows=[])), ('count', lambda d: d.update(rows=d['rows'] * 4)),
        ('kind', lambda d: d['rows'][0].update(kind='widget')),
        ('contradictory-kind', lambda d: d['rows'][0].update(pipeline=d['rows'][10]['pipeline'])),
        ('action', lambda d: d['rows'][0]['setting']['actions'][0].update(op='save')),
        ('action-payload', lambda d: d['rows'][0]['setting']['actions'][0].update(flag=True)),
        ('line-codec', lambda d: d['rows'][0]['setting'].update(globalValue='a|b')),
        ('sentinel', lambda d: d['rows'][0]['setting'].update(localValue='-')),
        ('action-bound', lambda d: d['rows'][0]['setting'].update(actions=d['rows'][0]['setting']['actions'] * 3)),
        ('probe-result', lambda d: d['rows'][10]['pipeline'].update(probe=3)),
        ('version-profile', lambda d: d['rows'][10]['pipeline']['stored'].update(version='26.0.1')),
        ('architecture', lambda d: d['rows'][10]['pipeline']['stored'].update(architecture='128')),
        ('memory', lambda d: d['rows'][10]['pipeline'].update(memory=16385)),
        ('major-zero', lambda d: d['rows'][10]['pipeline'].update(majors=[0])),
        ('major-bound', lambda d: d['rows'][10]['pipeline'].update(majors=[33])),
        ('boolean', lambda d: d['rows'][10]['pipeline'].update(ignore='true')),
        ('missing-field', lambda d: d['rows'][10]['pipeline'].pop('stored'))]
    for name, edit in edits:
        bad = copy.deepcopy(data)
        edit(bad)
        p = replay(bad)
        assert p.returncode == 2 and not p.stdout, (name, p.stdout, p.stderr)
        refusals.append(name)
    premise_controls = []
    for name, index, edit in [
            ('gate-basis', 0, lambda r: r['setting'].update(gate=True)),
            ('passthrough-write', 0, lambda r: r['setting'].update(passthrough=True)),
            ('cache-basis', 10, lambda r: r['pipeline'].update(signatureMatches=False)),
            ('required-major', 10, lambda r: r['pipeline'].update(majors=[25]))]:
        bad = copy.deepcopy(data)
        edit(bad['rows'][index])
        p = replay(bad)
        assert p.returncode == 0, p.stderr
        assert json.loads(p.stdout) != expected
        premise_controls.append(name)
    output_controls = []
    for name, index, edit in [
            ('effective-setting', 0, lambda r: r['trace'][0].update(effective='wrong')),
            ('probe-status', 10, lambda r: r.update(probed=True)),
            ('memory-diagnostic', 14, lambda r: r.update(verifyLogs=[])),
            ('metadata-placement', 24, lambda r: r['localStored'].update(JavaVersion='wrong'))]:
        changed = copy.deepcopy(outputs)
        edit(changed[index])
        try:
            compare([observations.measured(r) for r in changed], actual)
        except AssertionError:
            output_controls.append(name)
        else:
            raise AssertionError('Changed observation escaped: ' + name)
    replay(data)
    files = [HERE / n for n in ['Java.lean', 'Java.bend', 'JavaCase.lean', 'java_probe.py', 'java_observations.py', 'java_conformance.py']]
    files += [ROOT / 'applications/sources/prism-java-selections.json']
    files += [p for p in RUN.rglob('*') if p.is_file() and p.name != 'conformance.json']
    report = dict(schema=1, cases=37, settingsTraces=10, runtimeComponents=27,
                  comparisons=[dict(id=c['id'], input=r, observed=e, model=m) for c, r, e, m in zip(inputs, rows, expected, actual)],
                  researchRefusals=refusals, changedPremiseControls=premise_controls, changedObservationControls=output_controls,
                  basisSha256={str(p.relative_to(ROOT)): sha(p) for p in sorted(set(files))},
                  driverSha256=sha(driver), tools={n: dict(path=str(Path(p).resolve()), sha256=sha(Path(p))) for n, p in [('lean', lean), ('bend', bend)]},
                  limits=receipt['limits'] + ['Pure replay only; no Qt/JVM/compiler/Prism executed.',
                      'Decoder admits a bounded string/probe fixture profile; it is not the real Prism input decoder.',
                      'mtime/path signature is an observed cache heuristic, not executable integrity or process identity.',
                      'Major parsing is compared for five fixture strings; general JavaVersion ordering/parsing is unqualified.',
                      'The proposed evidence classification is not a production policy or full automatic-selection model.'])
    (RUN / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['comparisons', 'basisSha256']}, indent=2))


if __name__ == '__main__':
    main()
