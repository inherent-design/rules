#!/usr/bin/env python3
"""Replay retained identity function results; no engine/native execution."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = ROOT / 'applications/evidence/empack-identity-20261124T193525996513Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
bit = lambda x: '1' if x else '0'
optional_bit = lambda x: '-' if x is None else bit(x)
quote = lambda x: json.dumps(x, ensure_ascii=False)
boolean = lambda x: 'True{}' if x else 'False{}'


class Pairs(list):
    """Keep duplicate JSON members separate from JSON arrays."""


class Labels:
    def __init__(self): self.roles = {}
    def value(self, role, value):
        key = json.dumps(value, sort_keys=True, separators=(',', ':'))
        values = self.roles.setdefault(role, {})
        if key not in values: values[key] = len(values) + 1
        assert len(values) <= 4096 and len(set(values.values())) == len(values)
        return values[key]
    def optional(self, role, value):
        return None if value is None else self.value(role, value)
    def object(self, obj):
        assert set(obj) == {'volume', 'object', 'created', 'persistent'}
        assert obj['volume'].isdigit() and 0 <= int(obj['volume']) < 2**64
        assert obj['object'].isdigit() and 0 <= int(obj['object']) < 2**128
        created = obj['created']; token = obj['persistent']
        assert created is None or len(created) == 2 and all(type(n) is int and 0 <= n < 2**64 for n in created)
        assert token is None or len(token) == 32 and all(type(n) is int and 0 <= n < 256 for n in token)
        return dict(volume=self.value('volume', obj['volume']), number=self.value('number', obj['object']),
                    created=self.optional('created', created), token=self.optional('token', token))
    def snapshot(self, image):
        entries = []
        paths = [e['path'] for e in image['entries']]
        assert paths == sorted(set(paths))
        for e in image['entries']:
            o = e['observation']; tag = o['tag']
            row = dict(path=e['path'], kind=['absent', 'ancestor', 'file', 'directory'].index(tag),
                object=None, content=None, bytes=None, readonly=None, mode=None, members=[])
            if tag != 'absent': row['object'] = self.object(o['object'])
            if tag == 'file':
                assert len(o['content']) == 32 and all(type(n) is int and 0 <= n < 256 for n in o['content'])
                assert type(o['bytes']) is int and 0 <= o['bytes'] < 2**64
                assert type(o['mode']) is int and 0 <= o['mode'] < 2**32 and type(o['readonly']) is bool
                row.update(content=self.value('content', o['content']), bytes=self.value('bytes', o['bytes']),
                    readonly=o['readonly'], mode=self.value('mode', o['mode']))
            if tag == 'directory':
                assert o['members'] == sorted(set(o['members']))
                row['members'] = o['members']
            entries.append(row)
        return dict(root=self.object(image['root']), entries=entries)


def wire_shape(raw):
    parsed = json.loads(bytes(raw).decode('utf-8'), object_pairs_hook=Pairs)
    members = []
    if isinstance(parsed, Pairs):
        for name, value in parsed:
            array = type(value) is list
            # Exact byte values stay exact; all larger magnitudes share the
            # out-of-byte-range class. Sign remains independently represented.
            atoms = [dict(number=type(n) is int, negative=type(n) is int and n < 0,
                magnitude=min(abs(n), 256) if type(n) is int else 0) for n in value] if array else []
            members.append(dict(name=name, array=array, atoms=atoms))
    return dict(kind='wire', object=isinstance(parsed, Pairs), members=members), parsed


def binding_key(obj):
    if obj['created'] is None: return None
    seconds, nanos = obj['created']
    return f"project-{int(obj['volume']):016x}-{int(obj['object']):032x}-{seconds:x}-{nanos:x}"


def journal_text(out):
    assert type(out['captureOk']) is bool
    if not out['captureOk']:
        assert out['matches'] is None and out['error']; return '0/-'
    assert type(out['matches']) is bool and out['error'] is None
    return '1/' + bit(out['matches'])


def bend_opt(n): return 'I.IdNone{}' if n is None else f'I.IdSome{{{n}n}}'
def bend_obj(o):
    return 'I.IdObject{' + ','.join([str(o['volume']) + 'n', str(o['number']) + 'n', bend_opt(o['created']), bend_opt(o['token'])]) + '}'
def bend_optional(o): return 'I.IdAbsent{}' if o is None else 'I.IdPresent{' + bend_obj(o) + '}'
def bend_list(values): return '[' + ','.join(values) + ']'
def bend_snapshot(s):
    def node(r):
        if r['kind'] == 0: return 'I.IdMissing{}'
        obj = bend_obj(r['object'])
        if r['kind'] == 1: return 'I.IdAncestor{' + obj + '}'
        if r['kind'] == 2:
            return 'I.IdFile{' + ','.join([obj, str(r['content']) + 'n', str(r['bytes']) + 'n', boolean(r['readonly']), str(r['mode']) + 'n']) + '}'
        return 'I.IdDirectory{' + obj + ',' + bend_list(map(quote, r['members'])) + '}'
    entries = bend_list('I.IdEntry{' + quote(r['path']) + ',' + node(r) + '}' for r in s['entries'])
    return 'I.IdSnapshot{' + bend_obj(s['root']) + ',' + entries + '}'
def bend_call(r):
    kind = r['kind']
    if kind == 'identity': return 'I.identity(' + bend_obj(r['left']) + ',' + bend_obj(r['right']) + ')'
    if kind == 'journal': return 'I.journal(' + bend_optional(r['saved']) + ',' + bend_optional(r['observed']) + ')'
    if kind == 'snapshot': return 'I.snapshot(' + bend_snapshot(r['left']) + ',' + bend_snapshot(r['right']) + ')'
    if kind == 'wire':
        members = []
        for m in r['members']:
            atoms = bend_list('I.IdNumber{' + boolean(a['negative']) + ',' + str(a['magnitude']) + 'n}' if a['number'] else 'I.IdOther{}' for a in m['atoms'])
            members.append('I.IdMember{' + quote(m['name']) + ',' + boolean(m['array']) + ',' + atoms + '}')
        return 'I.wire(' + boolean(r['object']) + ',' + bend_list(members) + ')'
    if kind == 'association': return 'I.association(' + ','.join([quote(r['original']), quote(r['selected']), str(r['saved']) + 'n', bend_opt(r['observed'])]) + ')'
    assert kind == 'availability'; return 'I.availability(' + quote(r['reason']) + ')'


def main():
    observed = subprocess.run(['python3', str(HERE / 'identity_observations.py')], cwd=ROOT, capture_output=True, text=True)
    assert observed.returncode == 0, observed.stdout + observed.stderr
    original = [json.loads(line) for line in (RUN / 'observed.stdout').read_text().splitlines()]
    labels = Labels(); inputs, expected = [], []
    for row in original:
        i, o, kind = row['input'], row['outcome'], row['kind']
        if kind == 'identity':
            r = dict(kind='identity', left=labels.object(i['left']), right=labels.object(i['right']))
            e = bit(o['liveEqual']) + '/' + bit(o['durableEqual']) + '/' + journal_text(o['journal'])
        elif kind == 'journal-optional':
            r = dict(kind='journal', saved=None if i['saved'] is None else labels.object(i['saved']),
                observed=None if i['observed'] is None else labels.object(i['observed']))
            e = journal_text(o)
        elif kind == 'journal-codec':
            r, parsed = wire_shape(i['wire']); e = bit(o['accepted'])
            if o['accepted']:
                assert parsed == Pairs([('persistent', o['value']['persistent'])])
            else: assert o['error']
        elif kind == 'fingerprint':
            r = dict(kind='snapshot', left=labels.snapshot(i['left']), right=labels.snapshot(i['right']))
            e = '/'.join([bit(o['leftOk']), bit(o['rightOk']), optional_bit(o['equal']), bit(o['rootIdentityEqual']), bit(o['entriesEqual'])])
        elif kind == 'association-predicate':
            saved = labels.object(i['saved']); current = labels.object(i['observed'])
            key = binding_key(i['saved']); assert key is not None and saved['token'] is not None
            selected = key + '-wrong' if i['wrongName'] else key
            # The native fixture emits these PRE-CALL arguments in its outcome
            # object. Derive them from raw inputs here; never consume its verdict.
            record = o['record']; assert record['schema'] == 1 and record['persistent'] == i['saved']['persistent']
            assert record['original'] == dict(volume=int(i['saved']['volume']), object=list(int(i['saved']['object']).to_bytes(16, 'little')), created=i['saved']['created'])
            assert o['name'] == selected and o['currentKey'] == binding_key(i['observed'])
            r = dict(kind='association', original=key, selected=selected, saved=saved['token'], observed=current['token'])
            if o['matched'] is None:
                assert o['error']; e = 'name-error' if i['wrongName'] else 'unavailable-error'
            else:
                assert o['error'] is None; e = bit(o['matched'])
        else:
            assert kind == 'availability'
            r = dict(kind=kind, reason=i['name']); e = 'unavailable' if o['ok'] else 'error'
            assert (o['available'] is False and o['error'] is None) if o['ok'] else (o['available'] is None and o['error'])
        inputs.append(r); expected.append(e)
    assert len(inputs) == 58
    files = [HERE / n for n in ['Identity.lean', 'IdentityCase.lean', 'Identity.bend', 'identity_conformance.py',
        'identity_probe.py', 'identity_oracle.rs', 'identity_observations.py', 'identity-observations.json']]
    files += [RUN / n for n in ['receipt.json', 'commands.json', 'probe.py', 'driver.rs', 'observed.stdout', 'observed.stderr']]
    files += [ROOT / 'applications/sources/empack-identity-selections.json']
    basis = {str(p.relative_to(ROOT)): sha(p) for p in files}
    generated = HERE / 'generated'; formal = generated / 'formal'
    artifact = formal / 'applications/empack/Identity.olean'; artifact.parent.mkdir(parents=True, exist_ok=True)
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    env = dict(os.environ, LEAN_PATH=str(formal), BEND_NO_TELEMETRY='1')
    result = subprocess.run([lean, '-DwarningAsError=true', '-o', str(artifact), 'applications/empack/Identity.lean'], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    path = generated / 'identity.json'
    def replay(data):
        path.write_text(json.dumps(data) + '\n')
        return subprocess.run([lean, '--run', 'applications/empack/IdentityCase.lean', str(path)], cwd=ROOT, env=env, capture_output=True, text=True)
    data = dict(schema=1, profile='mac-native-identity-labels', cases=inputs)
    result = replay(data); assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == expected, [(o['id'], a, b) for o, a, b in zip(original, json.loads(result.stdout), expected) if a != b]
    driver = generated / 'IdentityCase.bend'
    driver.write_text('import Base\nimport ../Identity.bend as I\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(bend_call(r) + ' ++ "\\n"' for r in inputs) + ')\n')
    result = subprocess.run([bend, str(driver)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == expected, [(o['id'], a, b) for o, a, b in zip(original, result.stdout.splitlines(), expected) if a != b]
    invalids = [('schema', dict(data, schema=2), 'schema/profile'), ('profile', dict(data, profile='all-platforms'), 'schema/profile')]
    def invalid(label, index, mutate, message):
        row = copy.deepcopy(inputs[index]); mutate(row)
        invalids.append((label, dict(data, cases=[row]), message))
    invalid('unknown-kind', 0, lambda r: r.update(kind='recovery'), 'Unknown identity case')
    invalid('zero-label', 0, lambda r: r['left'].update(volume=0), 'Invalid equality label')
    invalid('large-label', 0, lambda r: r['left'].update(number=4097), 'Invalid equality label')
    invalid('negative-label', 0, lambda r: r['left'].update(number=-1), 'Natural number expected')
    snap = next(i for i, r in enumerate(inputs) if r['kind'] == 'snapshot')
    invalid('repeated-path', snap, lambda r: r['left']['entries'].append(copy.deepcopy(r['left']['entries'][0])), 'entry order or repeated path')
    invalid('unordered-paths', snap, lambda r: r['left']['entries'].reverse(), 'entry order or repeated path')
    invalid('unknown-node', snap, lambda r: r['left']['entries'][0].update(kind=4), 'Unknown node kind')
    def absent_payload(r):
        a = next(e for e in r['left']['entries'] if e['kind'] == 0); a['object'] = r['left']['root']
    invalid('absence-with-object', snap, absent_payload, 'Invalid absent payload')
    def wrong_members(r):
        a = next(e for e in r['left']['entries'] if e['kind'] == 3); a['members'] = ['a', 'a']
    invalid('duplicate-member', snap, wrong_members, 'directory payload/order')
    codec = next(i for i, r in enumerate(inputs) if r['kind'] == 'wire')
    invalid('inconsistent-atom', codec, lambda r: r['members'][0]['atoms'][0].update(number=False), 'Invalid nonnumber atom')
    invalid('scalar-with-array-payload', codec, lambda r: r['members'][0].update(array=False), 'scalar member payload')
    invalid('unknown-errno', 57, lambda r: r.update(reason='UNKNOWN'), 'Unknown errno profile')
    for label, bad, message in invalids:
        result = replay(bad); assert result.returncode == 2 and message in result.stderr, (label, result.stdout, result.stderr)
    path.write_text(json.dumps(data, indent=2) + '\n')
    assert all(sha(ROOT / p) == digest for p, digest in basis.items()), 'Frozen basis changed during replay.'
    report = dict(schema=1, basisSha256=basis, sourceCases=58, leanComparisons=58, bendComparisons=58,
        perRoleLabelCounts={k: len(v) for k, v in labels.roles.items()}, duplicatePreservingWireCases=12,
        invalidResearchInputsRefused=[v[0] for v in invalids],
        limits=['Comparison of selected source methods on macOS;not whole-engine/root capture,revalidation,state lookup,recovery or reboot qualification.',
            'Structural fingerprint projection,not a cryptographic implementation/injectivity proof;Python independently checks22valid byte encodings and2unavailable sides.',
            'JSON text parsing is external and duplicate-preserving;Lean/Bend model inner binding shape,not full journal admission or schema migration.',
            'Equality labels preserve per-role equality only;token generation is native opaque output,not independently proven provider identity.',
            'Association names are independently derived from raw original identity and supplied wrong-name flag;no directory reader/lock authority.',
            'Decoder refusals qualify the research boundary,not additional production validation or cross-platform errno semantics.'])
    (RUN / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'basisSha256'}, indent=2))


if __name__ == '__main__': main()
