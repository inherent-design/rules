#!/usr/bin/env python3
"""Pure selected-channel replay. Compiles Lean, but runs no Rust, signer, engine, or network."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REVISION = '0b4462e3032b4f09230b15329722eabefb7f574c'
ADAPTER = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
SIGNATURE_MUTATIONS = {'wrong-envelope-kind', 'unsupported-algorithm', 'duplicate-signature', 'uppercase-payload',
    'bad-known-signature', 'unknown-envelope-field', 'bad-unknown-cosigner', 'bad-known-cosigner'}
ZERO_CONTROLS = {'bad-known-signature', 'bad-unknown-cosigner', 'bad-known-cosigner'}
ENGINE = {'>=0.8.5-beta': (True, True), '>=0.8.0': (True, False), '=0.8.8-beta': (True, True),
    '>=0.8.5-beta, <0.8.8-0': (False, True), '>=0.8.5-alpha': (True, False), '>=0.9.0-beta': (False, False)}
PACK = {'fixture-pack': 1, 'other-pack': 2}
CHANNEL = {'stable': 1, 'other': 2}
ORIGINS = {'https://publisher.invalid': 1, 'https://other.invalid': 2, 'https://publisher.invalid:444': 3}
URLS = set(ORIGINS) | {'https://publisher.invalid/path?fixture=1', 'http://publisher.invalid',
    'https://fixture@publisher.invalid', 'https://publisher.invalid/releases/fixture/release.json',
    'https://publisher.invalid:443/release.json', 'https://publisher.invalid:444/release.json',
    'https://other.invalid/release.json', 'https://publisher.invalid/channels/stable.json'}


def origin(value):
    if value not in URLS:
        raise ValueError('URL is outside the selected profile.')
    u = urlsplit(value)
    if u.scheme != 'https' or u.username is not None or u.password is not None or u.fragment:
        return False, 0
    text = 'https://' + u.hostname + (':' + str(u.port) if u.port not in [None, 443] else '')
    return True, ORIGINS[text]


def canonical(value, size):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{' + str(size) + '}', value) is not None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('original', type=Path)
    p.add_argument('corrected', type=Path)
    p.add_argument('saved', type=Path)
    a = p.parse_args()
    captures = [a.original.resolve(), a.corrected.resolve(), a.saved.resolve()]
    receipts, records = [], []
    models = [HERE / name for name in ['Channels.lean', 'ChannelsCase.lean', 'Channels.bend']]
    ledger = ROOT / 'applications/sources/empack-channel-selections.json'
    inputs = models + [ledger]
    for capture, count in zip(captures, [39, 39, 9]):
        assert capture.is_relative_to(ROOT / 'applications/evidence')
        receipt = json.loads((capture / 'receipt.json').read_text())
        assert receipt['revision'] == REVISION and receipt['records'] == count
        assert sha(capture / 'probe.py') == receipt['producerSha256']
        assert sha(capture / 'driver.rs') == receipt['driverSha256']
        assert sha(capture / 'observe.stdout') == receipt['observedSha256']
        for command in json.loads((capture / 'commands.json').read_text()):
            assert command['exitCode'] == 0 and not command['timedOut']
            for stream in ['stdout', 'stderr']:
                assert sha(capture / (command['case'] + '.' + stream)) == command[stream + 'Sha256']
        for name, expected_hash in receipt['generatedSha256'].items():
            assert name in ['selected_trust.rs', 'diagnostics.rs', 'main.rs']
            assert sha(capture / 'work' / name) == expected_hash
        assert sha(capture / 'work/channel-oracle') == receipt['binarySha256']
        observed = [json.loads(line) for line in (capture / 'observe.stdout').read_text().splitlines()]
        assert len(observed) == count and len({r['case'] for r in observed}) == count
        receipts.append(receipt)
        records.append(observed)
        inputs += [f for f in sorted(capture.iterdir()) if f.is_file() and f.name != 'conformance.json']
    basis = {str(path.relative_to(ROOT)): sha(path) for path in inputs}
    repo = ROOT.parent / 'empack'
    source_rows = json.loads(ledger.read_text())['sources']
    sources = {}
    for row in source_rows:
        data = subprocess.check_output(['git', '-C', str(repo), 'show', REVISION + ':' + row['path']])
        assert hashlib.sha256(data).hexdigest() == row['sha256']
        sources[row['path']] = data
    for receipt in receipts:
        for name, identity in receipt['sourceSha256'].items():
            assert name in sources and hashlib.sha256(sources[name]).hexdigest() == identity
        for part in receipt['sourceSelections']:
            text = sources[part['source']].decode()
            selected = text[text.index(part['startMarker']):text.index(part['stopMarker'])] if 'startMarker' in part else (
                ''.join(text.splitlines(keepends=True)[part['firstLine'] - 1:part['lastLine'] - 1]))
            assert hashlib.sha256(selected.encode()).hexdigest() == part['sha256']
    old, current, saved = records
    recovered = []
    for before, after in zip(old, current):
        x, y = copy.deepcopy(before), copy.deepcopy(after)
        first = x['observed'].get('result', {}).pop('diagnostic', None)
        second = y['observed'].get('result', {}).pop('diagnostic', None)
        assert x == y, 'Original result changed outside the diagnostic projection.'
        if first != second:
            assert first is None and second['code'] == 'publisher-authentication-failed'
            recovered.append(after['case'])
    assert len(recovered) == 8
    assert json.loads((captures[0] / 'disposition.json').read_text())['status'].startswith('partial observation')
    public = list(dict.fromkeys(k for row in current if 'publicKeys' in row['request'] for k in row['request']['publicKeys']))
    assert len(public) == 2 and all(canonical(k, 64) for k in public)
    key_ids = {hashlib.sha256(bytes.fromhex(k)).hexdigest(): n + 1 for n, k in enumerate(public)}
    public_ids = {k: n + 1 for n, k in enumerate(public)}
    payloads = set()
    for row in current:
        r = row['request']
        if 'payloadUtf8' in r:
            payloads.add(hashlib.sha256(r['payloadUtf8'].encode()).hexdigest())
        if r.get('floor'):
            payloads.add(r['floor']['payload'])
    for row in saved:
        record = row['request']['record']
        for floor in [record['floor'], row['request']['expected']]:
            if floor:
                assert canonical(floor['payload'], 64)
                payloads.add(floor['payload'])
        if record['observed'] is not None:
            payloads.add(hashlib.sha256(bytes.fromhex(json.loads(record['observed'])['payload'])).hexdigest())
    payload_ids = {value: n + 1 for n, value in enumerate(sorted(payloads))}
    valid_signatures = set()

    def add_generated(e):
        content = hashlib.sha256(bytes.fromhex(e['payload'])).hexdigest()
        for sig in e['signatures']:
            assert canonical(sig['key'], 64) and canonical(sig['signature'], 128)
            valid_signatures.add((sig['key'], content, sig['signature']))

    for row in current:
        if row['observed']['phase'] in ['channel', 'enrollment'] and row['case'] not in SIGNATURE_MUTATIONS:
            add_generated(row['request']['envelope'])
    for row in saved:
        if row['request']['record']['observed'] is not None:
            add_generated(json.loads(row['request']['record']['observed']))

    def signature(case, content, sig):
        if sig['key'] not in key_ids:
            raise ValueError('Unknown fixture signature key.')
        valid = (sig['key'], content, sig['signature']) in valid_signatures
        if not valid and not (case in ZERO_CONTROLS and sig['signature'] == '00' * 64):
            raise ValueError('Signature validity has no frozen producer/control witness.')
        return dict(key=key_ids[sig['key']], algorithmKnown=sig['algorithm'] == 'ed25519',
                    canonical=canonical(sig['key'], 64) and canonical(sig['signature'], 128), valid=valid)

    def floor(value):
        if value is None:
            return None
        if value['origin'] not in ORIGINS or not canonical(value['payload'], 64):
            raise ValueError('Unsupported floor identity.')
        return dict(binding=dict(pack=PACK[value['pack']], origin=ORIGINS[value['origin']], channel=CHANNEL[value['channel']]),
                    sequence=value['sequence'], payload=payload_ids[value['payload']])

    def document_valid(value, content):
        required = {'schema', 'pack', 'channel', 'sequence', 'release', 'minimum_engine'}
        if set(value) != required:
            return False
        release = value['release']
        return (len(content) <= 16 << 10 and value['schema'] == 2 and value['pack'] in PACK and value['channel'] in CHANNEL
            and type(value['sequence']) is int and 0 < value['sequence'] < 1 << 64
            and set(release) == {'id', 'url', 'maximum_bytes'} and canonical(release['id'], 64)
            and origin(release['url'])[0] and type(release['maximum_bytes']) is int
            and 0 < release['maximum_bytes'] <= 2 * 16 * 1024 * 1024 + 16 * 1024
            and value['minimum_engine'] in ENGINE)

    def request(case, r):
        assert r['engine'] == '0.8.8-beta'
        e = r['envelope']
        content = bytes.fromhex(e['payload'])
        identity = hashlib.sha256(content).hexdigest()
        assert content.decode() == r['payloadUtf8'] and identity == r['payloadSha256']
        d = json.loads(content)
        assert d == r['document']
        valid_origin, expected_origin = origin(r['origin'])
        bound, prerelease = ENGINE[d['minimum_engine']]
        return dict(operation='channel', keys=[public_ids[k] for k in r['publicKeys']],
            enrollmentShape=valid_origin, envelopeShape=(set(e) == {'schema', 'kind', 'payload', 'signatures'}
                and e['schema'] == 1 and e['kind'] == 'channel' and e['payload'] == content.hex()
                and len(json.dumps(e, separators=(',', ':')).encode()) <= 48 << 10),
            documentShape=document_valid(d, content), signatures=[signature(case, identity, s) for s in e['signatures']],
            expected=dict(pack=PACK[r['enrolledPack']], origin=expected_origin, channel=CHANNEL[r['expectedName']]),
            document=dict(pack=PACK[d['pack']], origin=origin(d['release']['url'])[1], channel=CHANNEL[d['channel']]),
            authoredBounds=bound, prereleaseAdmitted=prerelease, sequence=d['sequence'], payload=payload_ids[identity], floor=floor(r['floor']))

    cases, expected, references = [], [], []
    for row in current:
        o, r = row['observed'], row['request']
        if o['phase'] in ['decode', 'sign']:
            c = dict(operation=o['phase'], keys=[1, 1] if o['phase'] == 'sign' else [], enrollmentShape=False,
                envelopeShape=False, documentShape=True, signatures=[], expected=dict(pack=1, origin=1, channel=1),
                document=dict(pack=1, origin=1, channel=1), authoredBounds=True, prereleaseAdmitted=True,
                sequence=3, payload=payload_ids[current[0]['request']['payloadSha256']], floor=None)
            if o['phase'] == 'decode':
                content = r['payloadUtf8'].encode()
                c['documentShape'] = document_valid(json.loads(content), content)
            result = o
        else:
            c, result = request(row['case'], r), o['result']
        diagnostic = result.get('diagnostic')
        cause = diagnostic['code'] if diagnostic else 'absent'
        if diagnostic:
            assert diagnostic['phase'] == 'verification'
        values = [str(int(result['accepted'])), cause, o['phase']]
        if result['accepted'] and o['phase'] == 'channel':
            f = floor(result['floor'])
            assert f == dict(binding=c['expected'], sequence=c['sequence'], payload=c['payload'])
            values += [str(f['binding'][key]) for key in ['pack', 'origin', 'channel']] + [str(f['sequence']), str(f['payload'])]
        else:
            values += ['0'] * 5
        cases.append(c)
        expected.append('/'.join(values))
        references.append(dict(case=row['case'], native=expected[-1]))
    saved_cases, saved_expected = [], []
    for row in saved:
        r, o = row['request']['record'], row['observed']
        origin_valid, origin_id = origin(r['url'])
        encoded = json.dumps(r, separators=(',', ':')).encode()
        stored = floor(r['floor'])
        shape = (len(encoded) <= 128 << 10 and r['schema'] == 1 and 0 < len(r['root']) <= 256
            and r['pack'] in PACK and r['channel'] in CHANNEL and origin_valid
            and len(r['keys']) <= 16 and len(set(r['keys'])) == len(r['keys']) and all(k in public_ids for k in r['keys'])
            and (r['floor'] is None) == (r['observed'] is None))
        if stored:
            shape = shape and stored['binding'] == dict(pack=PACK[r['pack']], origin=origin_id, channel=CHANNEL[r['channel']])
        observed = None
        if r['observed'] is not None:
            e = json.loads(r['observed'])
            content = bytes.fromhex(e['payload'])
            observed = request(row['case'], dict(engine='0.8.8-beta', origin=r['url'], enrolledPack=r['pack'],
                expectedName=r['channel'], publicKeys=r['keys'], envelope=e, document=json.loads(content),
                payloadUtf8=content.decode(), payloadSha256=hashlib.sha256(content).hexdigest(), floor=r['floor']))
        saved_cases.append(dict(recordShape=shape, observed=observed, stored=stored, selected=floor(row['request']['expected'])))
        assert bool(shape) == o['decoded']
        if not o['decoded']:
            saved_expected.append('0/not-run/not-run/not-run/not-run')
        else:
            assert o['recordBytesUnchanged']
            saved_expected.append('/'.join(str(int(v)) for v in [True, o['selectedGuard'], o['authenticated']['accepted'],
                o['returnedFloorEqualsSaved'], o['currentSelectionChecksPass']]))
    # The role counterexample is compared as current behavior; exact revalidation
    # remains a proposed result, never substituted for its native observation.
    mismatch = next(r for r in saved if r['case'] == 'newer-observation')
    assert mismatch['observed']['currentSelectionChecksPass'] and not mismatch['observed']['returnedFloorEqualsSaved']
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)
    data = dict(schema=1, cases=cases, saved=saved_cases)
    path = generated / 'channels.json'
    path.write_text(json.dumps(data, indent=2) + '\n')
    formal = generated / 'channels-formal'
    artifact = formal / 'applications/empack/Channels.olean'
    artifact.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LEAN_PATH=str(formal), BEND_NO_TELEMETRY='1')
    lean = os.environ.get('LEAN', 'lean')
    # Always build this exact source before importing it. A failed compile must
    # stop replay rather than leave a previous .olean eligible as evidence.
    compile_command = [lean, '-DwarningAsError=true', '-o', str(artifact), str(models[0])]
    compiled = subprocess.run(compile_command, cwd=ROOT, env=env, capture_output=True, text=True)
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    lean_version = subprocess.check_output([lean, '--version'], text=True).strip()
    formal_build = dict(sourceSha256=sha(models[0]), artifactSha256=sha(artifact),
                        command=compile_command, toolVersion=lean_version)

    def lean_run(value):
        return subprocess.run([lean, '--run', 'applications/empack/ChannelsCase.lean', str(value)],
                              cwd=ROOT, env=env, capture_output=True, text=True)

    result = lean_run(path)
    assert result.returncode == 0, result.stdout + result.stderr
    actual = json.loads(result.stdout)
    assert actual['cases'] == expected
    assert ['/'.join(s.split('/')[:5]) for s in actual['saved']] == saved_expected
    assert actual['saved'][1].endswith('/0'), 'Proposed exactness must refuse the demonstrated mismatch.'
    bit = lambda value: 'True{}' if value else 'False{}'

    def list_text(values):
        result = 'Nil{}'
        for item in reversed(values):
            result = 'Con{' + item + ',' + result + '}'
        return result

    def binding_text(value):
        return 'C.Binding{' + ','.join(str(value[k]) + 'n' for k in ['pack', 'origin', 'channel']) + '}'

    def floor_text(value, optional=True):
        if value is None:
            assert optional
            return 'None{}'
        body = 'C.Floor{' + binding_text(value['binding']) + ',' + str(value['sequence']) + 'n,' + str(value['payload']) + 'n}'
        return 'Some{' + body + '}' if optional else body

    def request_text(c):
        keys = list_text([str(k) + 'n' for k in c['keys']])
        sigs = list_text(['C.Signature{' + ','.join([str(s['key']) + 'n', bit(s['algorithmKnown']), bit(s['canonical']), bit(s['valid'])]) + '}'
                          for s in c['signatures']])
        return 'C.Request{' + ','.join([keys, bit(c['enrollmentShape']), bit(c['envelopeShape']), bit(c['documentShape']), sigs,
            binding_text(c['expected']), binding_text(c['document']), bit(c['authoredBounds']), bit(c['prereleaseAdmitted']),
            str(c['sequence']) + 'n', str(c['payload']) + 'n', floor_text(c['floor'])]) + '}'

    calls = []
    for c in cases:
        if c['operation'] == 'decode':
            call = 'direct(' + bit(c['documentShape']) + ',"decode")'
        elif c['operation'] == 'sign':
            call = 'direct(C.signing_admits(' + bit(c['documentShape']) + ',' + list_text([str(k) + 'n' for k in c['keys']]) + '),"sign")'
        else:
            call = 'channel(' + request_text(c) + ')'
        calls.append(call + ' ++ "\\n"')
    for c in saved_cases:
        observed = 'None{}' if c['observed'] is None else 'Some{' + request_text(c['observed']) + '}'
        calls.append('saved(C.saved_outcome(' + ','.join([bit(c['recordShape']), observed, floor_text(c['stored']),
            floor_text(c['selected'], optional=False)]) + ')) ++ "\\n"')
    runner = generated / 'ChannelsCase.bend'
    runner.write_text('''import Base
import ../Channels.bend as C

def bit(b: Bool) -> String:
  match b:
    case True{}: "1"
    case False{}: "0"

def cause(c: C.TypedCause) -> String:
  match c:
    case C.NoTypedCause{}: "absent"
    case C.PublisherAuthentication{}: "publisher-authentication-failed"
    case C.IncompatibleEngine{}: "incompatible-engine"

def phase(r: C.Request) -> String:
  match r:
    case C.Request{keys,enrollment_shape,envelope_shape,document_shape,signatures,expected,document,bounds,prerelease,sequence,payload,floor}:
      Bool.pick(String,C.enrollment_admits(keys,enrollment_shape),"channel","enrollment")

def returned(accepted: Bool, f: C.Floor) -> String:
  match accepted:
    case False{}: "0/0/0/0/0"
    case True{}:
      match f:
        case C.Floor{binding,sequence,payload}:
          match binding:
            case C.Binding{pack,origin,channel}: Nat.show(pack) ++ "/" ++ Nat.show(origin) ++ "/" ++ Nat.show(channel) ++ "/" ++ Nat.show(sequence) ++ "/" ++ Nat.show(payload)

def fields(+accepted: Bool, c: C.TypedCause, phase: String, f: C.Floor) -> String:
  bit(accepted) ++ "/" ++ cause(c) ++ "/" ++ phase ++ "/" ++ returned(accepted,f)

def channel(+r: C.Request) -> String:
  fields(C.admitted(r),C.typed_cause(r),phase(r),C.candidate(r))

def direct(accepted: Bool, phase: String) -> String:
  bit(accepted) ++ "/absent/" ++ phase ++ "/0/0/0/0/0"

def saved(o: C.SavedOutcome) -> String:
  match o:
    case C.NotDecoded{}: "0/not-run/not-run/not-run/not-run/0"
    case C.Checked{guard,authenticated,exact,current_checks,proposed_checks}: "1/" ++ bit(guard) ++ "/" ++ bit(authenticated) ++ "/" ++ bit(exact) ++ "/" ++ bit(current_checks) ++ "/" ++ bit(proposed_checks)

def main() -> IO(Unit):
  IO.write(''' + ' ++ '.join(calls) + ')\n')
    result = subprocess.run([os.environ.get('BEND', 'bend'), str(runner)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == actual['cases'] + actual['saved']
    negatives = [dict(data, schema=2), *[dict(data, cases=[dict(cases[0], **change)]) for change in
        [dict(operation='install'), dict(keys=[3]), dict(sequence=0), dict(sequence=1 << 64), dict(payload=0),
         dict(expected=dict(pack=1, origin=4, channel=1))]]]
    bad_saved = copy.deepcopy(data)
    bad_saved['saved'][0]['observed']['floor'] = None
    negatives.append(bad_saved)
    for n, negative in enumerate(negatives):
        file = generated / f'channels-negative-{n}.json'
        file.write_text(json.dumps(negative))
        result = lean_run(file)
        assert result.returncode == 2 and result.stderr
    rejected_crypto = copy.deepcopy(current[0]['request']['envelope']['signatures'][0])
    rejected_crypto['signature'] = '11' * 64
    try:
        signature('baseline', current[0]['request']['payloadSha256'], rejected_crypto)
    except ValueError:
        pass
    else:
        raise AssertionError('Arbitrary nonzero signature was accepted as a validity witness.')
    assert all(sha(ROOT / name) == identity for name, identity in basis.items())
    report = dict(schema=1, uniqueSourceObservations=48, originalDiagnosticRepeat=39, channelRecords=39, savedRecords=9,
        leanMatchesCurrentObservations=True, bendMatchesCurrentObservations=True, researchInputsRefused=len(negatives),
        unsupportedCryptoWitnessRefused=True, recoveredTypedContexts=recovered, adapterSha256=ADAPTER,
        basisSha256=basis, formalBuild=formal_build, mainComparison=references,
        savedCurrent=saved_expected, savedModels=actual['saved'],
        limits=['Selected source compilation, not pure-core/installed CLI/full-engine execution.',
            'Signature validity is a closed producer/control witness catalog; this replay is not an Ed25519 verifier.',
            'Fixed URL and six engine requirement profiles; no general JSON/URL/SemVer implementation.',
            'Saved-record checks ran independently in-memory; currentSelectionChecksPass is composition, not a full acquisition/update trace.',
            'Exact saved-observation validation is proposed; current acceptance of the mismatched record stays in the comparison.',
            'Original wrong diagnostic projection is excluded; its other39 observations agree with the corrected capture.'])
    (captures[1] / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['basisSha256', 'mainComparison', 'savedModels']}, indent=2))


if __name__ == '__main__':
    main()
