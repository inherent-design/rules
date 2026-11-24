#!/usr/bin/env python3
"""Check initializer source/artifacts, effects, and retained interruption results."""
import hashlib
import json
import inspect
from pathlib import Path
import subprocess

from root_state_observations import image

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'applications/evidence/empack-initializer-20261124T205241728563Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    r = json.loads((RUN / 'receipt.json').read_text()); commands = json.loads((RUN / 'commands.json').read_text())
    assert r['commands'] == commands and len(commands) == 25 and len(r['cases']) == 23
    assert r['sourceRevision'] == '0b4462e3032b4f09230b15329722eabefb7f574c'
    assert sha(RUN / 'probe.py') == r['producerSha256'] and sha(RUN / 'driver.rs') == r['driverSha256']
    assert sha(ROOT / r['scaffold']) == r['scaffoldSha256'] and sha(ROOT / r['scaffoldReceipt']) == r['scaffoldReceiptSha256']
    previous = json.loads((ROOT / r['scaffoldReceipt']).read_text()); prior_work = (ROOT / r['scaffold']).parent
    for name, digest in previous['generatedSha256'].items(): assert sha(prior_work / name) == digest
    assert sha(Path(r['compiler']['path'])) == r['compiler']['sha256']
    for a in r['libraries'].values():
        assert sha(Path(a['path'])) == a['sha256']
        if 'fingerprint' in a: assert sha(Path(a['fingerprint'])) == a['fingerprintSha256']
    for name, digest in r['generatedSha256'].items(): assert sha(RUN / 'work' / name) == digest
    for info in r['binaries'].values(): assert sha(ROOT / info['path']) == info['sha256']
    repo = ROOT.parent / 'empack'
    for path, digest in r['sourceSha256'].items():
        raw = subprocess.check_output(['git', '-C', str(repo), 'show', r['sourceRevision'] + ':' + path])
        assert hashlib.sha256(raw).hexdigest() == digest == sha(repo / path)
    current = (RUN / 'work/current.rs').read_text(); candidate = (RUN / 'work/candidate.rs').read_text()
    patch = r['candidatePatch']; assert patch['count'] == current.count(patch['old']) == 1
    assert candidate == current.replace(patch['old'], patch['new'])
    root_source = (repo / patch['path']).read_text(); assert root_source in current and root_source.replace(patch['old'], patch['new']) in candidate
    for s in r['sourceSelections']:
        raw = (repo / s['path']).read_text(); chunk = raw[raw.index(s['start']):raw.index(s['stop'])]
        assert hashlib.sha256(chunk.encode()).hexdigest() == s['sha256'] and chunk in current and chunk in candidate
    assert 'actual_instance_runtime::ensure_stopped(state)?;fixture_phase("locked")' in current
    assert 'file.try_lock().context("Native root association initialization is busy")?' in candidate
    by_command = {c['label']: c for c in commands}; assert len(by_command) == 25
    for c in commands:
        assert not c['timedOut'] and c['ownedGroupAbsent']
        assert c['exitCode'] == (-9 if c['intentionalKill'] else 0)
        for stream in ['stdout', 'stderr']: assert sha(RUN / (c['label'] + '.' + stream)) == c[stream + 'Sha256']
    cases = {c['label']: c for c in r['cases']}; latest = {}; all_images = set()
    for c in r['cases']:
        for part in ['before', 'during', 'after']:
            if part not in c: continue
            ref = c[part]; p = RUN / ref['image']; assert sha(p) == ref['sha256']; all_images.add(ref['image'])
        last = c['after']; latest[c['fixture']] = json.loads((RUN / last['image']).read_text())
        rows = [json.loads(l) for l in (RUN / (c['label'] + '.stdout')).read_text().splitlines()]
        if c['action'].startswith('terminated-'):
            assert len(rows) == 1 and rows[0] == c['phase'] and rows[0]['pid'] == by_command[c['label']]['pid']
        else:
            assert len(rows) == 1 and rows[0]['outcome'] == c['outcome'] and rows[0]['pid'] == by_command[c['label']]['pid']
    for fixture, expected in latest.items(): assert image(RUN / 'work' / fixture) == expected
    def at(label, part='after'):
        return json.loads((RUN / cases[label][part]['image']).read_text())
    def files(state):
        return {bytes.fromhex(p).decode(): bytes.fromhex(v['contentHex']) for p,v in state.items() if v['kind'] == 'file'}
    def roots(state): return sorted(p for p in state if bytes.fromhex(p).startswith(b'host/project-') and bytes.fromhex(p).count(b'/') == 1)
    def unchanged(label): assert cases[label]['before']['sha256'] == cases[label]['after']['sha256'], label
    for variant in ['current', 'candidate']:
        assert cases[variant + '-normal']['outcome']['ok']; unchanged(variant + '-idempotent')
        normal = at(variant + '-normal'); selected = roots(normal); assert len(selected) == 1
        directory = normal[selected[0]]; assert directory['mode'] & 0o777 == 0o700
        marker = bytes.fromhex(selected[0]).decode() + '/root-identity.json'; record = json.loads(files(normal)[marker])
        assert record['schema'] == 1 and record['persistent'] == cases[variant + '-normal']['outcome']['root']['persistent']
        assert normal[marker.encode().hex()]['mode'] & 0o777 == 0o600
        assert not any('.empack-candidate-' in p for p in files(normal))
        paused = cases[variant + '-paused']; assert paused['kernelLockHeldBeforeKill'] and paused['kernelLockAvailableAfterKill']
        assert paused['during']['sha256'] == paused['after']['sha256']
        held = files(at(variant + '-paused'))
        lock = 'operation.lock' if variant == 'current' else 'state.lock'
        assert len(roots(at(variant + '-paused'))) == 1
        assert sorted(p.rsplit('/',1)[1] for p in held if p.startswith('host/')) == [lock]
        assert all(raw == b'' for p,raw in held.items() if p.startswith('host/'))
        for suffix in ['-concurrent', '-after-kill-lookup']:
            unchanged(variant + suffix)
        assert not cases[variant + '-concurrent']['outcome']['ok']
        if variant == 'current':
            for suffix in ['-concurrent', '-after-kill-lookup', '-retry']:
                o = cases[variant + suffix]['outcome']; assert not o['ok'] and o['unassociated']; unchanged(variant + suffix)
        else:
            assert 'initialization is busy' in cases[variant + '-concurrent']['outcome']['error']
            assert cases[variant + '-after-kill-lookup']['outcome']['selected'] is None
            assert cases[variant + '-retry']['outcome']['ok']
        assert cases[variant + '-completed-lookup']['outcome']['ok'] and cases[variant + '-completed-lookup']['outcome']['selected']
        assert cases[variant + '-completed-retry']['outcome']['ok']; unchanged(variant + '-completed-retry')
        assert not cases[variant + '-unknown-refusal']['outcome']['ok']; unchanged(variant + '-unknown-refusal')
        assert any(p.endswith('/journal.json') and b'unknown retained fixture' == raw for p,raw in files(at(variant + '-unknown-refusal')).items())
    assert cases['candidate-current-interop']['outcome']['ok']; unchanged('candidate-current-interop')
    from initializer_probe import retire_owned
    cleanup=json.loads((RUN/'harness-cleanup-recheck.json').read_text())
    assert cleanup['helperSha256']==hashlib.sha256(inspect.getsource(retire_owned).encode()).hexdigest()
    assert cleanup['testSourceSha256']==sha(RUN/'harness_cleanup_probe.py')
    assert len(cleanup['cases'])==2 and cleanup['cases'][0]['ownedGroupAbsent'] and cleanup['cases'][1]['groupKillRefused']
    report = dict(schema=1, sourcePins=len(r['sourceSha256']), commands=25, cases=23, intentionalTerminations=4,
        normalResultRows=19, successfulOrdinaryAPIResultRows=sum(c.get('outcome',{}).get('ok',False) for c in r['cases']),
        terminatedAfterSuccessfulInitializerReturnCases=sum(c['action']=='terminated-after-initializer-return' for c in r['cases']),
        sourceNativeFixturePostimagesVerified=len(latest), capturedImageFilesVerified=len(all_images),
        cleanupHelperControls=2, cleanupScope='Separate helper test;does not enlarge initializer coverage. Current producer adds failure cleanup after the frozen native collection.',
        currentFinding='Complete selected initializer leaves operation.lock without association after owned-child termination;fresh lookup and retry refuse the slot without changing it.',
        candidateFinding='One private call substitution uses state.lock for association initialization;concurrent attempt is busy,released metadata-only slot is discoverable as absent,and retry publishes an association.',
        protections=['Current and candidate preserve existing unknown journal/operation-lock fixture state on refusal.',
            'Candidate reads a current-profile published association without a new file or rewrite.',
            'Source initialization completes through temporary file,fsync,rename anddirectory sync;normal record mode600/directory700 observed onmacOS.',
            'All25 owned command groups observed absent onretirement;four deliberateSIGKILL outcomes are not successful command exits. Kernel lock held before andavailable after post-lock termination.'],
        limits=['Formal initializer trace comparison pending;retained source/effects checker only.',
            'Supplied host capability and complete selected initializer chain,not full Engine/CLI request,Publisher::open,project publication or recovery.',
            'Actual post-lock pause delegates real runtime predicate;controlled instrumentation andSIGKILL,not OSreboot,power-loss proof or arbitrarycrash-point coverage.',
            'Candidate is privatecopied source plus onechangedcall;no production implementation/adoption. Windows/Linux,post-rename pre-fsync failure,malicious metadata lock types andgeneral concurrent lifecycle remainunqualified.',
            'Images retain bytes,paths,mode,inode/device andmtime;atime/ctime excluded. Historical PID/group results are not fresh liveness or PID-reuse authority.'])
    (ROOT / 'applications/empack/initializer-observations.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':main()
