#!/usr/bin/env python3
"""Compare discovery models with retained private views; no native execution."""
import copy
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess

import root_state_observations as observations

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
quote = lambda s: json.dumps(s, ensure_ascii=False)
boolean = lambda v: 'True{}' if v else 'False{}'


class Pairs(list):
    """Distinguish a JSON object and retain duplicate fields."""


def fields(value, required, optional=()):
    if not isinstance(value, Pairs): raise ValueError('not an object')
    names = [k for k, _ in value]
    if len(names) != len(set(names)) or not set(required) <= set(names) or not set(names) <= set(required) | set(optional):
        raise ValueError('missing,duplicate,or unknown field')
    return dict(value)


def integer(n, bits):
    if type(n) is not int or not 0 <= n < 2**bits: raise ValueError('integer range/type')
    return n


def bytes_array(xs, size):
    if type(xs) is not list or len(xs) != size: raise ValueError('byte array shape')
    return bytes(integer(x, 8) for x in xs)


def key(volume, number, created):
    if created is None: return None
    return f'project-{volume:016x}-{number:032x}-{created[0]:x}-{created[1]:x}'


def parsed_record(raw, label):
    """External strict typed projection,not a Lean/Bend JSON text parser."""
    try:
        obj = fields(json.loads(raw.decode('utf-8'), object_pairs_hook=Pairs), ['schema', 'persistent', 'original'])
        original = fields(obj['original'], ['volume', 'object'], ['created'])
        created = original.get('created')
        if created is not None:
            if type(created) is not list or len(created) != 2: raise ValueError('creation shape')
            created = [integer(created[0], 64), integer(created[1], 32)]
        volume = integer(original['volume'], 64)
        number = int.from_bytes(bytes_array(original['object'], 16), 'little')
        return dict(schema=integer(obj['schema'], 32), original=key(volume, number, created),
                    token=label(bytes_array(obj['persistent'], 32)))
    except (ValueError, TypeError, UnicodeDecodeError):
        return None


class Tokens:
    def __init__(self): self.values = {}
    def label(self, raw):
        assert len(raw) == 32
        if raw not in self.values: self.values[raw] = len(self.values) + 1
        assert len(set(self.values.values())) == len(self.values) <= 4096
        return self.values[raw]


def view(row, state, tokens):
    saved = row['root']; created = saved['created']
    current = key(int(saved['volume']), int(saved['object']), created)
    assert current == row['currentKey'] and current is not None
    suffix = '-' + current.split('-', 2)[2]
    raw = {bytes.fromhex(p): v for p, v in state.items()}
    at = raw.get(bytes.fromhex(row['rootLocationHex']))
    root = 1 if at is None else 0 if at['kind'] == 'directory' and (at['device'], at['inode']) == (saved['volume'], saved['object']) else 2
    # For these quiescent private fixtures a retained root prevents inode reuse;
    # birth/UUID/durable-token changes with the same object are not injected.
    # This relation is not a general replacement for native check_binding().
    entries = []
    for path, metadata in raw.items():
        if not path.startswith(b'host/') or path.count(b'/') != 1: continue
        name = path.split(b'/')[1].decode('utf-8')
        directory = metadata['kind'] == 'directory'
        children = sorted(p.rsplit(b'/', 1)[1].decode('utf-8') for p in raw if p.startswith(path + b'/') and p.count(b'/') == 2) if directory else []
        marker = raw.get(path + b'/root-identity.json') if directory else None
        kind, count, record = 0, 0, None
        if marker is not None:
            if marker['kind'] != 'file': kind = 1
            else:
                kind = 2; payload = bytes.fromhex(marker['contentHex']); count = len(payload)
                assert count == marker['bytes']
                # The real reader refuses oversize before serde sees the bytes.
                if count <= 1024: record = parsed_record(payload, tokens.label)
        entries.append(dict(name=name, directory=directory, markerKind=kind, bytes=count, record=record, children=children))
    entries.sort(key=lambda e: e['name'])
    return dict(root=root, current=current, suffix=suffix,
        token=None if saved['persistent'] is None else tokens.label(bytes(saved['persistent'])), entries=entries)


def bend_opt(value): return 'S.RNoToken{}' if value is None else f'S.RToken{{{value}n}}'
def bend_list(xs): return '[' + ','.join(xs) + ']'
def bend_entry(r):
    if r['markerKind'] == 0: marker = 'S.RAbsent{}'
    elif r['markerKind'] == 1: marker = 'S.RUnreadable{}'
    else:
        v = r['record']
        if v is None: record = 'S.RMalformed{}'
        else:
            original = 'S.RNoKey{}' if v['original'] is None else 'S.RKey{' + quote(v['original']) + '}'
            record = 'S.RRecord{' + str(v['schema']) + 'n,' + original + ',' + str(v['token']) + 'n}'
        marker = 'S.RWire{' + str(r['bytes']) + 'n,' + record + '}'
    return 'S.REntry{' + ','.join([quote(r['name']), boolean(r['directory']), marker, bend_list(map(quote, r['children']))]) + '}'

def bend_call(row):
    return 'S.evaluate(' + ','.join([quote(row['current']), quote(row['suffix']), bend_opt(row['token']), str(row['root']) + 'n', bend_list(map(bend_entry, row['entries']))]) + ')'

def text_out(value):
    return '/'.join(['1' if value['ok'] else '0', value['selected'] or '-',
        '-' if value['found'] is None else '1' if value['found'] else '0', value['bound'] or '-'])


def main():
    checked = subprocess.run(['python3', str(HERE / 'root_state_observations.py')], cwd=ROOT, capture_output=True, text=True, timeout=90)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    original, inputs, expected, basis_files = [], [], [], []
    tokens = Tokens()
    for run in [observations.RUN, observations.PREFIX]:
        rows = [json.loads(l) for l in (run / 'observed.stdout').read_text().splitlines()]
        for row in rows:
            image = run / 'images' / row['image']; basis_files.append(image)
            if row.get('setupUnavailable'): continue
            value = view(row, json.loads(image.read_text()), tokens)
            inputs.append(value); original.append(row)
            expected.append(dict(ok=row['resolved']['ok'], selected=row['resolved']['selected'], found=row['found']['found'], bound=row['bound']['key']))
        basis_files += [run / n for n in ['receipt.json', 'commands.json', 'probe.py', 'driver.rs', 'observed.stdout', 'observed.stderr']]
    assert len(inputs) == 35 and len({r['id'] for r in original}) == 35
    # Same immutable files witness a before-prefix view;this is a MODEL input
    # derived from the recorded image,not a fresh native observation/authority.
    prefix = original[-1]['prefixBefore']; path = observations.PREFIX / 'images' / prefix['image']; basis_files.append(path)
    assert sha(path) == prefix['sha256']
    before_prefix = view(original[-1], json.loads(path.read_text()), tokens)
    # The alternative changes only initializer coordination in the retained view.
    # No proposed writer is implemented/executed by this comparison.
    candidate = copy.deepcopy(inputs[-1]); current_slot = next(e for e in candidate['entries'] if e['name'] == candidate['current'])
    assert current_slot['markerKind'] == 0 and current_slot['children'] == ['operation.lock']
    current_slot['children'] = ['state.lock']
    proposed = [before_prefix, candidate]
    proposed_expected = [dict(ok=True, selected=None, found=False, bound=r['current']) for r in proposed]
    basis_files += [HERE / n for n in ['RootState.lean', 'RootStateCase.lean', 'RootState.bend', 'root_state_conformance.py',
        'root_state_observations.py', 'root-state-observations.json', 'root_state_probe.py', 'root_state_oracle.rs']]
    basis_files += [ROOT / 'applications/sources/empack-root-state-selections.json']
    basis_files += [observations.RUN / n for n in ['model-runtime.json','model-interpreter.stderr','model-typecheck.stdout']]
    basis = {str(p.relative_to(ROOT)): sha(p) for p in basis_files}
    generated = HERE / 'generated'; formal = generated / 'formal'
    artifact = formal / 'applications/empack/RootState.olean'; artifact.parent.mkdir(parents=True, exist_ok=True)
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    env = dict(os.environ, LEAN_PATH=str(formal), BEND_NO_TELEMETRY='1')
    result = subprocess.run([lean, '-DwarningAsError=true', '-o', str(artifact), 'applications/empack/RootState.lean'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    path = generated / 'root-state.json'
    def replay(value):
        path.write_text(json.dumps(value) + '\n')
        return subprocess.run([lean, '--run', 'applications/empack/RootStateCase.lean', str(path)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
    data = dict(schema=1, profile='quiescent-mac-discovery', cases=inputs + proposed)
    result = replay(data); assert result.returncode == 0, result.stdout + result.stderr
    actual = json.loads(result.stdout)
    assert actual == expected + proposed_expected, [(o['id'], a, b) for o, a, b in zip(original, actual, expected) if a != b]
    driver = generated / 'RootStateCase.bend'
    driver.write_text('import Base\nimport ../RootState.bend as S\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(bend_call(r) + ' ++ "\\n"' for r in inputs + proposed) + ')\n')
    # Bend's checked interpreter overflows its machine stack on the large
    # Peano/list boundary fixture. Keep every input and use its native builder;
    # this is a model replay,not fresh empack/OS evidence collection.
    executable = generated / 'root-state-model'
    built = subprocess.run([bend, str(driver), '-o', str(executable)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
    assert built.returncode == 0, built.stdout + built.stderr
    result = subprocess.run([str(executable)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == list(map(text_out, expected + proposed_expected))
    backend = dict(kind='Bend native model builder',toolPath=str(Path(shutil.which(bend) or bend).resolve()),
        toolSha256=sha(Path(shutil.which(bend) or bend)), generatedSourceSha256=sha(driver), binarySha256=sha(executable),
        binaryBytes=executable.stat().st_size, stdoutSha256=hashlib.sha256(result.stdout.encode()).hexdigest(),
        note='Generated fixture typechecking and model kernel-verdict pass;interpreted execution of this large fixture exceeds its stack. Subordinate native compiler invocation is not independently recorded.')
    invalids = [('schema', dict(data, schema=2), 'schema/profile'), ('profile', dict(data, profile='arbitrary-host'), 'schema/profile')]
    def bad(name, index, mutate, message):
        row = copy.deepcopy(inputs[index]); mutate(row)
        invalids.append((name, dict(data, cases=[row]), message))
    current = next(i for i, r in enumerate(original) if r['id'] == 'valid-current')
    empty = next(i for i, r in enumerate(original) if r['id'] == 'current-empty')
    bad('unknown-root', current, lambda r: r.update(root=3), 'Unknown root evidence')
    bad('invalid-current', current, lambda r: r.update(current='other'), 'Invalid current key')
    bad('mismatched-suffix', current, lambda r: r.update(suffix='-other'), 'Invalid current suffix')
    bad('duplicate-entry', current, lambda r: r['entries'].append(copy.deepcopy(r['entries'][0])), 'entry order,count,or duplicate')
    bad('traversal-entry', current, lambda r: r['entries'][0].update(name='../other'), 'Invalid immediate entry name')
    bad('unknown-marker', current, lambda r: r['entries'][0].update(markerKind=3), 'Unknown marker kind')
    bad('token-zero', current, lambda r: r.update(token=0), 'current token witness')
    bad('record-token-zero', current, lambda r: r['entries'][0]['record'].update(token=0), 'decoded association witness')
    bad('absent-with-record', current, lambda r: r['entries'][0].update(markerKind=0, bytes=0), 'absent marker witness')
    bad('absent-with-byte-count', empty, lambda r: r['entries'][0].update(bytes=1), 'absent marker witness')
    bad('non-directory-with-children', current, lambda r: r['entries'][0].update(directory=False), 'nondirectory payload')
    bad('duplicate-child', current, lambda r: r['entries'][0]['children'].append('root-identity.json'), 'child order or duplicate')
    for name, value, message in invalids:
        result = replay(value); assert result.returncode == 2 and message in result.stderr, (name, result.stdout, result.stderr)
    path.write_text(json.dumps(data, indent=2) + '\n')
    assert all(sha(ROOT / p) == h for p, h in basis.items()), 'Basis changed during comparison.'
    report = dict(schema=1, basisSha256=basis, nativeCases=35, entrypointsPerCase=3, leanNativeComparisons=35, bendNativeComparisons=35,
        additionalModelOnlyViews=['recorded-before-lock-prefix', 'proposed-state-lock-only-coordination'],
        unavailableNativeCells=['nonutf8 filename rejected during setup,errno92;no discovery call'],
        bendBackend=backend, tokenEqualityLabels=len(tokens.values), largestCompleteHostViews=[len(inputs[i]['entries']) for i, r in enumerate(original) if r['id'] in ['limit4096', 'limit4097']],
        invalidResearchInputsRefused=[v[0] for v in invalids],
        limits=['Admission/physical selection/found/key fallback only;native error chains retained but first-error ordering/IO failure priority is not modeled.',
            'Complete quiescent private views,real root held against inode reuse;root relation derives device/inode/presence and assumes unchanged birth/UUID/token for the same object. Native check_binding retains its complete comparison.',
            'External duplicate-preserving typed JSON projection;models consume decoded witnesses,no JSON text/parser/OS capability proof.',
            'No reboot,new native acquisition,complete state initialization,forced termination,power-loss recovery,real operations or native/browser authority qualification.',
            'Before-prefix and candidate views are model-only;current prefix refusal remains intact,proposed writer requires separate implementation/verification.'])
    (observations.RUN / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'basisSha256'}, indent=2))


if __name__ == '__main__': main()
