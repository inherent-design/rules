"""Replay retained template facts against models. Never rerun native collectors."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

from template_facts import address_facts, fixture_body, project_facts, properties_bytes, ini_bytes

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
NATIVE = ROOT / 'applications/evidence/empack-templates-20261125T145924167329Z'
ENCODING = ROOT / 'applications/evidence/empack-template-encoding-20261125T150106975825Z'
PROPERTIES = ROOT / 'applications/evidence/empack-template-properties-20261125T150217339816Z'
EXCLUDED = ROOT / 'applications/evidence/empack-templates-20261125T145859236192Z'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def compare(actual, expected):
    assert actual == expected, 'Template measured outcome differs from modeled facts'


def observed_address(status):
    if status == 'ignore':
        return 0
    if status.startswith('error:'):
        return 1
    layer, path, mode = status.split(':')
    assert layer in ['Common', 'Client', 'Server'] and path
    assert mode in ['Handlebars', 'TextOrBinary']
    return 2 if mode == 'Handlebars' else 3


def observed_stage(row, message):
    if row['exitCode'] == 0:
        return 0
    assert row['exitCode'] == 1
    for text, value in [('Two templates produce', 2), ('collides with selected game content', 5),
            ('File destination collides', 3), ('Template rendering failed:', 4), ('Explicit template is not UTF-8:', 4)]:
        if text in message:
            return 2 if row['id'] == 'file-ancestor' else value
    raise AssertionError('Refusal does not match this closed stage projection')


def verify_capture(folder):
    receipt = load(folder / 'receipt.json')
    assert receipt['complete']
    assert sha(folder / 'probe.py') == receipt['producerSha256']
    for command in receipt['commands']:
        assert command['groupAbsent'] and not command['timedOut']
        for stream in ['stdout', 'stderr']:
            assert sha(folder / (command['label'] + '.' + stream)) == command[stream + 'Sha256']
    return receipt


def main():
    native = verify_capture(NATIVE)
    encoding = verify_capture(ENCODING)
    consumer = verify_capture(PROPERTIES)
    assert sha(NATIVE / 'helpers.py') == native['helperSha256']
    assert sha(ENCODING / 'driver.rs') == encoding['driverSha256']
    assert sha(PROPERTIES / 'TemplatePropertiesProbe.java') == consumer['driverSha256']
    assert sha(PROPERTIES / 'input.tsv') == consumer['inputSha256']
    assert (PROPERTIES / 'input.tsv').read_bytes() == (ENCODING / 'observed.stdout').read_bytes()
    assert sha(ENCODING / 'receipt.json') == consumer['encodingReceiptSha256']
    # Validate attributed Git objects, not another writer's current checkout.
    source_bytes = {}
    for source in encoding['sources']:
        raw = subprocess.check_output(['git', 'show', encoding['revision'] + ':' + source['path']], cwd=ROOT.parent / 'empack')
        assert hashlib.sha256(raw).hexdigest() == source['sha256']
        source_bytes[source['path']] = raw
    template = source_bytes['crates/empack-lib/src/engine/templates.rs'].decode()
    start, end = encoding['addressTextRange']
    address = template[start:end]
    assert address.startswith('pub(super) fn template_address(') and address.endswith('}\n')
    enum_start = template.index('#[derive(Debug, Clone, Copy, PartialEq, Eq)]')
    enum_end = template.index('#[derive(Debug, Clone, Copy)]', enum_start)
    generated = (ENCODING / 'driver.rs').read_text().replace('/*ADDRESS*/', template[enum_start:enum_end] + address.replace('pub(super) fn ', 'fn ', 1))
    generated = generated.replace('/*ENCODING*/', source_bytes['crates/empack-lib/src/engine/templates/encoding.rs'].decode())
    assert hashlib.sha256(generated.encode()).hexdigest() == encoding['generatedSha256']
    private_checks = []
    for path, digest in [(Path(encoding['compiler']), encoding['compilerSha256']),
            (ROOT / encoding['library'], encoding['librarySha256']),
            (Path(encoding['work']) / 'driver.rs', encoding['generatedSha256']),
            (Path(encoding['work']) / 'probe', encoding['binarySha256']),
            (Path(consumer['work']) / 'TemplatePropertiesProbe.class', consumer['classSha256'])]:
        if path.exists():
            assert sha(path) == digest
            private_checks.append(str(path))
    for tool in consumer['tools'].values():
        path = Path(tool['path'])
        if path.exists():
            assert sha(path) == tool['sha256']
            private_checks.append(str(path))
            if 'releaseSha256' in tool:
                assert sha(path.parent.parent / 'release') == tool['releaseSha256']
    source_rows = load(ENCODING / 'input.json')['rows']
    assert sha(ENCODING / 'input.json') == encoding['inputSha256']
    input_tsv = ''.join(row['kind'] + '\t' + row['value'].encode().hex() + '\n' for row in source_rows)
    assert hashlib.sha256(input_tsv.encode()).hexdigest() == encoding['inputTsvSha256']
    proof = load(ENCODING / 'proof-gate.json')
    assert proof['observedExitCode'] == 0 and proof['observedSummary'] == 'Checked 2 Lean modules and 1 Bend files.'
    for path, digest in proof['sourceSha256'].items():
        assert sha(ROOT / path) == digest
    rows = [line.split('\t') for line in (ENCODING / 'observed.stdout').read_text().splitlines()]
    assert len(rows) == len(source_rows) == 34
    addresses, observed_addresses = [], []
    value_expected = {}
    for index, (item, output) in enumerate(zip(source_rows, rows, strict=True)):
        assert output[:2] == [str(index), item['kind']]
        if item['kind'] == 'address':
            facts, layer, destination = address_facts(item['value'])
            addresses.append(facts)
            status = output[2]
            observed_addresses.append(observed_address(status))
            if not (status == 'ignore' or status.startswith('error:')):
                actual_layer, actual_destination, mode = status.split(':')
                assert actual_layer.lower() == layer and bytes.fromhex(actual_destination).decode() == destination
        else:
            assert bytes.fromhex(output[2]) == ini_bytes(item['value'])
            assert bytes.fromhex(output[3]) == properties_bytes(item['value'])
            value_expected[str(index)] = item['value'].encode().hex()
    for major in ['17', '21', '25']:
        lines = (PROPERTIES / ('java-' + major + '.stdout')).read_text().splitlines()
        assert lines[0].startswith('runtime\t' + major + '.')
        parsed = [line.split('\t') for line in lines[1:]]
        assert len(parsed) == 2 * len(value_expected)
        assert {(r[0], r[1]) for r in parsed} == {(key, route) for key in value_expected for route in ['stream', 'reader']}
        for index, route, count, value in parsed:
            assert count == '1' and value == value_expected[index], (major, index, route)
    bodies, body_codes, prepares, prepare_codes, details = [], [], [], [], []
    # The authored metadata is known and parsed independently of output status.
    name = "Study ' Ω"
    assert json.loads((NATIVE / 'empack.yml').read_text().split('  name: ', 1)[1].split('\n', 1)[0]) == name
    for row in native['cases']:
        assert row['beforeSource'] == row['afterSource']
        facts, outputs, selected_bodies = project_facts(row['sourceBytes'], name)
        prepares.append(facts)
        if row['exitCode'] == 0:
            saved = NATIVE / (row['id'] + '.zip')
            assert sha(saved) == row['archiveSha256']
            with zipfile.ZipFile(saved) as archive:
                actual = [dict(path=i.filename, bytesHex=archive.read(i).hex(), mode=i.external_attr >> 16, crc=i.CRC) for i in archive.infolist()]
            assert actual == row['outputs']
            members = {p['path']: p for p in actual}
            for destination, data in outputs.items():
                assert data is not None and bytes.fromhex(members[destination]['bytesHex']) == data
            if row['id'] == 'baseline':
                assert members['run.sh']['mode'] & 0o777 == 0o555
                assert (NATIVE / 'generated-printf.stdout').read_bytes() == name.encode()
                assert bytes.fromhex(members['raw.bin']['bytesHex']) == b'\0\xffbinary'
            assert bytes.fromhex(members['.minecraft/config/marker.txt']['bytesHex']) == b'game bytes'
        else:
            assert row['exitCode'] == 1 and row['beforeDist'] == row['afterDist']
            message = (NATIVE / (row['id'] + '.stderr')).read_text()
        code = observed_stage(row, (NATIVE / (row['id'] + '.stderr')).read_text())
        prepare_codes.append(code)
        # Real publication is checked against the fixture byte interpreter. The
        # formal body projection has source-fact inputs, not an API result stream.
        for source, body_facts, body_code in selected_bodies:
            bodies.append(body_facts)
            body_codes.append(body_code)
        details.append(dict(id=row['id'], facts=facts, outputs={k: None if v is None else v.hex() for k, v in outputs.items()},
            selectedBodyFacts=[dict(source=src, facts=facts, expectedCode=code) for src, facts, code in selected_bodies]))
    inputs = dict(schema=1, addresses=addresses, bodies=bodies, prepares=prepares)
    expected = dict(addresses=observed_addresses, bodies=body_codes, prepares=prepare_codes)
    write(ENCODING / 'model-input.json', inputs)
    write(ENCODING / 'projection-facts.json', details)
    formal = ROOT / '.build/empack-templates-formal'
    env = {**os.environ, 'LEAN_PATH': str(formal), 'BEND_NO_TELEMETRY': '1'}
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')
    command = [lean, '--run', 'applications/empack/TemplatesCase.lean', str(ENCODING / 'model-input.json')]
    result = subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True, text=True)
    actual = json.loads(result.stdout)
    compare(actual, expected)
    bo = lambda b: 'True{}' if b else 'False{}'
    opt = lambda b: 'None{}' if b is None else 'Some{' + bo(b) + '}'
    calls, wanted = [], []
    for facts, code in zip(addresses, observed_addresses, strict=True):
        calls.append('T.show_decision(T.address(' + bo(facts['recognized']) + ',' + opt(facts['valid']) + ',' + bo(facts['explicit']) + '))')
        wanted.append(str(code))
    for facts, code in zip(bodies, body_codes, strict=True):
        calls.append('Nat.show(T.body(' + str(facts['mode']) + 'n,' + bo(facts['utf8']) + ',' + bo(facts['known']) + '))')
        wanted.append(str(code))
    for facts, code in zip(prepares, prepare_codes, strict=True):
        calls.append('T.show_decision(T.prepare(' + ','.join(opt(facts[k]) for k in ['addresses', 'sameLayer', 'namespaceValid', 'bodies', 'game']) + '))')
        wanted.append(str(code))
    main_bend = formal / 'compare.bend'
    main_bend.write_text('import ../../applications/empack/Templates.bend as T\nimport Base\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ "\\n" ++ '.join(calls) + ')\n')
    result = subprocess.run([bend, str(main_bend)], cwd=ROOT, env=env, check=True, capture_output=True, text=True)
    compare(result.stdout.splitlines(), wanted)
    controls = []
    changed_observations = []
    changed = copy.deepcopy(expected)
    changed['addresses'][0] = observed_address('ignore')
    changed_observations.append(('changed-address-stream', changed))
    changed = copy.deepcopy(expected)
    changed['prepares'][0] = observed_stage(dict(native['cases'][0], exitCode=1), 'Template rendering failed: controlled changed observation')
    changed_observations.append(('changed-native-outcome', changed))
    for label, changed in changed_observations:
        try:
            compare(actual, changed)
        except AssertionError:
            controls.append(label)
        else:
            raise AssertionError('Changed outcome escaped')
    for label, alter in [('schema', lambda d: d.update(schema=2)),
            ('needed-address', lambda d: d['addresses'][0].update(valid=None)),
            ('needed-prepare', lambda d: d['prepares'][0].update(bodies=None)),
            ('mode', lambda d: d['bodies'][0].update(mode=3))]:
        changed = copy.deepcopy(inputs)
        alter(changed)
        path = formal / (label + '.json')
        write(path, changed)
        rejected = subprocess.run(command[:-1] + [str(path)], cwd=ROOT, env=env, capture_output=True, text=True)
        assert rejected.returncode == 2 and ('Unsupported' in rejected.stderr or 'unknown' in rejected.stderr)
        controls.append(label)
    mutated_properties = copy.deepcopy(value_expected)
    mutated_properties['19'] = b'changed scalar'.hex()
    first_java = (PROPERTIES / 'java-17.stdout').read_text().splitlines()[1:]
    assert any(value != mutated_properties[index] for index, route, count, value in (line.split('\t') for line in first_java))
    controls.append('changed-properties-scalar')
    excluded = verify_capture(EXCLUDED)
    assert load(EXCLUDED / 'disposition.json')['templateObservations'] == 0
    assert all(c['exitCode'] == 2 for c in excluded['cases'])
    # Basis excludes this replay's own derived report and hash manifest.
    files = [p for folder in [NATIVE, ENCODING, PROPERTIES, EXCLUDED] for p in folder.rglob('*')
        if p.is_file() and p.name not in ['conformance.json', 'basis.json']]
    files += [HERE / p for p in ['template_probe.py', 'template_encoding_probe.py', 'template_encoding_driver.rs',
        'template_properties_probe.py', 'TemplatePropertiesProbe.java', 'template_facts.py', 'template_conformance.py',
        'Templates.lean', 'TemplatesCase.lean', 'Templates.bend']]
    ledger = ROOT / 'applications/sources/empack-template-selections.json'
    for source in load(ledger)['sources']:
        data = subprocess.check_output(['git', 'show', source['commit'] + ':' + source['path']], cwd=ROOT.parent / 'empack')
        assert hashlib.sha256(data).hexdigest() == source['sha256']
    files.append(ledger)
    write(ENCODING / 'basis.json', {str(p.relative_to(ROOT)): sha(p) for p in files})
    report = dict(schema=1, nativeBuilds=11, acceptedBuilds=4, refusedBuilds=7,
        addressSourceCalls=18, encodedScalars=16, consumerPropertiesReads=96,
        modelAddressComparisons=18, modelPrepareComparisons=11, sourceFactBodyProjections=len(bodies),
        leanLaws=15, bendLaws=6, controls=controls, basisFiles=len(files), privateArtifactsChecked=len(private_checks),
        nativeCodeSourceCorrespondence='Installed binary and pinned current-source excerpts are distinct, not a reproducible-build proof.',
        limits=['Closed literal/NAME/shell_quote fixture grammar, not a Handlebars implementation or encoder proof.',
            'Model body codes are source-fact projections; actual published bytes have independent native comparison.',
            'INI encoding checked as bytes only; no Prism/Qt consumer execution here.',
            'Properties consumer reads exact encoder output, not a server artifact.',
            'Native standalone Prism ZIP builds only; no explicit Copy override, input/output limit, cancellation, snapshot race or managed hook qualification.',
            'Original invalid-artifact-name run is excluded from template comparisons; all original evidence retained.'])
    write(ENCODING / 'conformance.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
