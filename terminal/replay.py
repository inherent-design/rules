#!/usr/bin/env python3
"""Compare checked executable model decisions with retained native evidence.

Offline: does not invoke a package manager or modify any tool installation.
"""
import base64
import copy
import json
import os
from pathlib import Path
import subprocess

from study import ROOT

BREADTH = ['20261123T224740171810Z', '20261123T224805512573Z']
PIPE = '20261123T225211680511Z-journeys'
TTY = '20261123T225322018614Z-journeys'
EARLY = '20261123T230015174972Z-journeys'
COLOR = '20261123T230434898129Z-journeys'


def read(run, stem):
    return json.loads((ROOT / 'terminal/evidence' / run / (stem + '.json')).read_text())


def raw(record, channel):
    return base64.b64decode(record['observed']['host'][channel + '_b64'])


def changed(record, scope='project'):
    changes = record['observed']['changes']
    return [p for p in changes if p.startswith(scope + '/')]


def check_projection(record, status, project_changed):
    outcome = record['outcome']
    actual = outcome['exit_code'] if outcome['signal'] is None else 256 + outcome['signal']
    assert actual == status, (record['case'], 'status', actual, status)
    assert bool(changed(record)) == bool(project_changed), (record['case'], 'project effect')
    assert outcome['capture_complete'] and not outcome['timed_out']


def check_json(record):
    stdout = raw(record, 'stdout')
    assert b'\x1b' not in stdout
    return json.loads(stdout)


def main():
    bend = os.environ.get('BEND', 'bend')
    lean = os.environ.get('LEAN', 'lean')
    env = dict(os.environ, BEND_NO_TELEMETRY='1', LEAN_PATH=str(ROOT / '.build'))
    native = subprocess.check_output([bend, 'terminal/Native.bend'], cwd=ROOT, env=env, text=True)
    projections = [[int(v) for v in line.split(',')] for line in native.splitlines() if line]
    assert len(projections) == 16
    checks = 0
    for tool_id, case_id, status, effects, channel in projections:
        tool = ('npm', 'pnpm', 'yarn', 'empack')[tool_id]
        if case_id < 3:
            case = ('help', 'refusal', 'resolve-write' if tool == 'yarn' else 'preview')[case_id]
            for run in BREADTH:
                record = read(run, tool + '-' + case)
                check_projection(record, status, effects)
                if case_id == 1:
                    payload = raw(record, 'stdout' if channel == 0 else 'stderr')
                    assert payload.strip(), (tool, 'missing expected diagnostic channel')
                checks += 1
        else:
            record = read(TTY, tool + '-interrupt')
            check_projection(record, status, effects)
            assert record['observed']['host']['actionTriggered']
            checks += 1

    # Native facts used by the separately identified Lean tool models.
    lean_output = subprocess.check_output([lean, '-DwarningAsError=true', '--run', 'terminal/Replay.lean'], cwd=ROOT, env=env, text=True)
    lean_facts, lean_candidate = {}, []
    for line in lean_output.splitlines():
        pieces = line.split(',')
        if pieces[0] == 'candidate':
            lean_candidate.append([int(x) for x in pieces[1:]])
        else:
            lean_facts[pieces[0]] = int(pieces[1])
    expected = {
        'npm-help': read(BREADTH[0], 'npm-help')['outcome']['exit_code'],
        'npm-dry-project': int(bool(changed(read(BREADTH[0], 'npm-preview')))),
        'npm-dry-cache': int(bool(changed(read(BREADTH[0], 'npm-preview'), 'cache'))),
        'pnpm-refusal-project': int(bool(changed(read(BREADTH[0], 'pnpm-refusal')))),
        'yarn-lock-write': int('project/yarn.lock' in changed(read(BREADTH[0], 'yarn-resolve-write'))),
        'yarn-lock-link': int(any(p.startswith('project/node_modules/') for p in read(BREADTH[0], 'yarn-resolve-write')['observed']['after'])),
        'yarn-signal': read(TTY, 'yarn-interrupt')['outcome']['exit_code'],
        'empack-parser': read(BREADTH[0], 'empack-refusal')['outcome']['exit_code'],
    }
    assert lean_facts == expected
    checks += len(expected)
    candidate = subprocess.check_output([bend, 'terminal/Candidate.bend'], cwd=ROOT, env=env, text=True)
    bend_candidate = [[int(x) for x in line.split(',')] for line in candidate.splitlines() if line]
    assert bend_candidate == lean_candidate and len(lean_candidate) == 24
    for mode, current, evidence, approved, decision in lean_candidate:
        if mode == 2 and decision == 2:
            assert current and evidence and approved
        if mode < 2:
            assert decision == mode
    checks += 24

    # Machine result and failure must both remain parseable where actually promised.
    for run in (PIPE, TTY):
        valid = read(run, 'empack-inspect-json')
        invalid = read(run, 'empack-lock-refusal')
        assert check_json(valid)['complete'] is True
        report = check_json(invalid)
        assert report['complete'] is False and report['lock'] == 'invalid'
        assert invalid['outcome']['exit_code'] != 0 and raw(invalid, 'stderr').strip()
        assert not changed(invalid) and not changed(invalid, 'state')
        checks += 2
        for tool in ('npm', 'pnpm', 'yarn'):
            failure = read(run, tool + '-hook-failure')
            assert failure['outcome']['exit_code'] == 7
            assert 'project/hook-effect.txt' in changed(failure)
            interrupt = read(run, tool + '-interrupt')
            assert 'project/interrupt-effect.txt' in changed(interrupt)
            replay = read(run, tool + '-recover-after-interrupt')
            for marker in ('project/hook-effect.txt', 'project/interrupt-effect.txt'):
                assert replay['observed']['before'][marker] == replay['observed']['after'][marker]
            checks += 2
    early = read(EARLY, 'empack-cancel-at-approval')
    assert early['outcome']['exit_code'] == 130
    assert not changed(early) and not changed(early, 'state')
    assert read(TTY, 'empack-interrupt')['outcome']['exit_code'] == 0
    checks += 2

    for tool in ('npm', 'pnpm', 'yarn', 'empack'):
        for color in ('never', 'always'):
            record = read(COLOR, tool + '-color-' + color)
            data = raw(record, 'stdout')
            assert record['outcome']['exit_code'] == 0 and b'\x1b' not in data
            if tool == 'yarn':
                assert data.splitlines()
                [json.loads(line) for line in data.splitlines()]
            else:
                json.loads(data)
            checks += 1

    # These deliberate broken observations must fail the same checker.
    mutations = []
    bad = copy.deepcopy(read(BREADTH[0], 'pnpm-refusal'))
    bad['observed']['changes'] = {}
    mutations.append(('refusal-assumed-rollback', lambda: check_projection(bad, 1, True)))
    bad_status = copy.deepcopy(read(TTY, 'empack-interrupt'))
    bad_status['outcome']['exit_code'] = 130
    mutations.append(('cancellation-erases-success', lambda: check_projection(bad_status, 0, True)))
    bad_json = copy.deepcopy(read(TTY, 'empack-inspect-json'))
    bad_json['observed']['host']['stdout_b64'] = base64.b64encode(b'Working...\n' + raw(bad_json, 'stdout')).decode()
    mutations.append(('progress-contaminates-json', lambda: check_json(bad_json)))
    rejected = []
    for name, check in mutations:
        try:
            check()
        except (AssertionError, ValueError):
            rejected.append(name)
        else:
            raise AssertionError('Broken observation was accepted: ' + name)
    output = {'v': 1, 'nativeAndModelChecks': checks, 'negativeControlsRejected': rejected,
              'candidateCombinations': len(lean_candidate),
              'limits': 'Finite retained-trace conformance and abstract proofs; not a proof of complete application/source correspondence.'}
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
