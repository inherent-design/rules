#!/usr/bin/env python3
"""Replay frozen publication facts. No package manager or server is started."""
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ADAPTER = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('boundaries', type=Path)
    args = parser.parse_args()
    captures = [args.run.resolve(), args.boundaries.resolve()]
    sources_path = ROOT / 'applications/sources/js-publication-selections.json'
    sources = json.loads(sources_path.read_text())
    for source in sources:
        assert sha(ROOT / source['cache']) == source['sha256']
    inputs = [HERE / name for name in ['Publication.lean', 'PublicationCase.lean', 'Publication.bend']]
    inputs.append(sources_path)
    for capture in captures:
        inputs += [p for p in sorted(capture.rglob('*')) if p.is_file() and 'work' not in p.relative_to(capture).parts
                   and p.name != 'conformance.json']
    basis = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    cases, expected, comparisons, archives, hook_sequences = [], [], [], [], []
    count = 0
    for capture in captures:
        receipt = json.loads((capture / 'receipt.json').read_text())
        rows = json.loads((capture / 'trace.json').read_text())
        assert receipt['commands'] == len(rows)
        count += len(rows)
        assert sha(capture / 'probe.py') == receipt['producerSha256']
        assert json.loads((capture / 'server-retired.json').read_text()) == dict(threadJoined=True, listeningSocketClosed=True)
        events = json.loads((capture / 'server-events.json').read_text())
        received = {}
        for index, event in enumerate(events):
            if event['method'] != 'PUT':
                continue
            if event['accepted']:
                body_path, tgz_path = capture / f'received-{index}.json', capture / f'received-{index}.tgz'
                body = json.loads(body_path.read_text())
                assert sha(body_path) == event['requestSha256']
                assert sha(tgz_path) == event['archiveSha256']
                attachment, = body['_attachments'].values()
                data = base64.b64decode(attachment['data'], validate=True)
                assert data == tgz_path.read_bytes() and len(data) == attachment['length'] == event['archiveBytes']
                manifest, = body['versions'].values()
                assert manifest['dist']['shasum'] == hashlib.sha1(data).hexdigest()
                assert manifest['dist']['integrity'] == 'sha512-' + base64.b64encode(hashlib.sha512(data).digest()).decode()
                with tarfile.open(fileobj=io.BytesIO(data)) as tar:
                    files = {m.name: hashlib.sha256(tar.extractfile(m).read()).hexdigest() for m in tar if m.isfile()}
                    packed = json.loads(tar.extractfile('package/package.json').read())
                assert files == event['files'] and set(files) == {'package/package.json', 'package/index.js'}
                assert packed['name'] == body['name'] and packed['version'] == event['version']
                received[event['case']] = event
                archives.append(dict(capture=str(capture.relative_to(ROOT)), case=event['case'],
                                     sha256=sha(tgz_path), files=files, publishedScripts=list(packed.get('scripts', {}))))
        for row in rows:
            app, name = row['app'], row['case']
            stem = app + '-' + name
            for stream in ['stdout', 'stderr']:
                assert sha(capture / (stem + '.' + stream)) == row['observed'][stream + 'Sha256']
            if name in ['help', 'initialize']:
                assert row['outcome']['exitCode'] == 0
                continue
            assert app in ['npm', 'pnpm', 'yarn']
            assert name in ['dry-run', 'accepted', 'duplicate', 'rejected', 'lost-response', 'retry-after-loss',
                            'dry-run-hooks', 'after-upload-hook-failure', 'loss-before-accept', 'before-upload-hook-failure']
            request, observed = row['request'], row['observed']
            manifest = json.loads((capture / (stem + '-package.json')).read_text())
            assert manifest['version'] == request['version'] and manifest['name'] == 'rules-publication-fixture-' + app
            assert manifest['files'] == ['index.js']
            assert observed['serverEvents'] == [e for e in events if e['case'] == stem]
            puts = [e for e in observed['serverEvents'] if e['method'] == 'PUT']
            assert len(puts) <= 1, 'Selected no-retry fixture has changed.'
            before, after = observed['beforeVersions'], observed['afterVersions']
            assert set(before) <= set(after)
            exists = request['version'] in before
            present = request['version'] in after
            accepted = any(e['accepted'] for e in puts)
            acknowledged = any(e['accepted'] and e['status'] == 201 and not e['responseDropped'] for e in puts)
            assert present == (exists or accepted)
            hooks_before, hooks_after = observed['hooksBefore'], observed['hooksAfter']
            assert hooks_after[:len(hooks_before)] == hooks_before
            new_hooks = hooks_after[len(hooks_before):]
            if manifest.get('scripts'):
                sequence = ['prepublishOnly', 'prepack', 'postpack', 'publish', 'postpublish'] if app == 'npm' else (
                    ['prepublishOnly', 'prepublish', 'prepack', 'postpack', 'publish', 'postpublish'] if app == 'pnpm' else
                    ['prepublish', 'prepack', 'postpack'])
                if request['failingHook']:
                    sequence = sequence[:sequence.index(request['failingHook']) + 1]
                assert new_hooks == sequence
                hook_sequences.append(dict(app=app, case=name, observed=new_hooks))
            else:
                assert not new_hooks
            case = dict(profile=app, dry=name.startswith('dry-run'), recordPresent=exists,
                rejected=request['fixtureMode'] == 'reject',
                loss={'accept': 'none', 'reject': 'none', 'drop': 'after', 'drop-before-accept': 'before'}[request['fixtureMode']],
                hooks=bool(manifest.get('scripts')), hookFailure='none' if not request['failingHook'] else
                    'before' if request['failingHook'] == 'prepack' else 'after')
            cases.append(case)
            facts = [bool(puts), accepted, present, acknowledged, bool(new_hooks), row['outcome']['exitCode']]
            expected.append('/'.join(str(int(f)) for f in facts))
            comparisons.append(dict(app=app, case=name, nativeFacts=expected[-1]))
        # The original producer predates the optional boundary-only mode.
        if not receipt.get('boundaryFollowup', False):
            for app in ['npm', 'pnpm', 'yarn']:
                remote = json.loads((capture / (app + '-owner-read-after-loss.json')).read_text())
                assert '3.0.0' in remote['versions']
                accepted = received[app + '-lost-response']
                retry, = [r for r in rows if r['app'] == app and r['case'] == 'retry-after-loss']
                for put in [e for e in retry['observed']['serverEvents'] if e['method'] == 'PUT']:
                    assert put['archiveSha256'] == accepted['archiveSha256'] and not put['accepted']
                lost, = [r for r in rows if r['app'] == app and r['case'] == 'lost-response']
                assert remote['versions']['3.0.0']['dist']['integrity'] == json.loads(
                    (capture / f"received-{events.index(accepted)}.json").read_text())['versions']['3.0.0']['dist']['integrity']
                assert lost['outcome']['exitCode'] == 1
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)
    input_path = generated / 'publication.json'
    input_path.write_text(json.dumps(dict(schema=1, cases=cases), indent=2) + '\n')
    env = dict(os.environ, LEAN_PATH=str(ROOT / '.build/formal'), BEND_NO_TELEMETRY='1')
    lean, bend = os.environ.get('LEAN', 'lean'), os.environ.get('BEND', 'bend')

    def lean_run(path):
        return subprocess.run([lean, '--run', 'applications/js-peers/PublicationCase.lean', str(path)],
                              cwd=ROOT, env=env, capture_output=True, text=True)

    result = lean_run(input_path)
    assert result.returncode == 0, result.stdout + result.stderr
    actual = json.loads(result.stdout)
    assert actual == expected, [(a, e, c) for a, e, c in zip(actual, expected, cases) if a != e]
    bit = lambda b: 'True{}' if b else 'False{}'
    calls = []
    for c in cases:
        p = {'npm': 'Npm', 'pnpm': 'Pnpm', 'yarn': 'Yarn'}[c['profile']]
        loss = {'none': 'NoLoss', 'before': 'BeforeAcceptance', 'after': 'AfterAcceptance'}[c['loss']]
        hook = {'none': 'NoHook', 'before': 'BeforeUpload', 'after': 'AfterUpload'}[c['hookFailure']]
        r = ','.join([bit(c['dry']), bit(c['recordPresent']), bit(c['rejected']), f'M.{loss}{{}}', bit(c['hooks']), f'M.{hook}{{}}'])
        calls.append(f'render(M.publish(M.{p}{{}},M.Request{{{r}}})) ++ "\\n"')
    runner = generated / 'PublicationCase.bend'
    runner.write_text('import Base\nimport ../Publication.bend as M\n\ndef bit(b: Bool) -> String:\n  match b:\n    case True{}: "1"\n    case False{}: "0"\n\ndef render(f: M.Facts) -> String:\n  match f:\n    case M.Facts{sent,accepted,present,acknowledged,effects,status}: bit(sent) ++ "/" ++ bit(accepted) ++ "/" ++ bit(present) ++ "/" ++ bit(acknowledged) ++ "/" ++ bit(effects) ++ "/" ++ Nat.show(status)\n\ndef main() -> IO(Unit):\n  IO.write(' + ' ++ '.join(calls) + ')\n')
    result = subprocess.run([bend, str(runner)], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == expected
    invalid = [dict(schema=2, cases=cases), *[dict(schema=1, cases=[dict(cases[0], **change)]) for change in
        [dict(profile='yarn-classic'), dict(loss='maybe'), dict(hookFailure='during'),
         dict(hooks=False, hookFailure='after'), dict(dry=True, loss='after'), dict(recordPresent=True, loss='after')]]]
    for n, value in enumerate(invalid):
        path = generated / f'publication-invalid-{n}.json'
        path.write_text(json.dumps(value))
        result = lean_run(path)
        assert result.returncode == 2 and result.stderr
    assert all(sha(ROOT / p) == value for p, value in basis.items())
    report = dict(schema=1, nativeCommands=count, publicationOutcomes=len(cases), matchedModels=['Lean', 'Bend'],
        unsupportedResearchInputsRefused=len(invalid), archiveInventories=len(archives), archives=archives,
        comparisons=comparisons, hooks=hook_sequences, adapterSha256=ADAPTER, basisSha256=basis,
        rejectedInterpretations=['command failure proves version absent', 'dry run means no network or local effects',
            'an upload acknowledgement proves every post-upload step succeeded', 'retry conflict alone proves identical release bytes'],
        limits=['Loopback generated fixture, not a real registry or credential/TLS/replication/durability test.',
            'Models project admitted source ordering; no general packlist, HTTP, script, resolver or server implementation.',
            'Claim is proposed reporting derived from admitted evidence, not a decoded current CLI field.',
            'No public upload/unpublish, stage/provenance, workspace batches, auth challenges, automatic retries or interrupted-process qualification.'])
    (captures[0] / 'conformance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['basisSha256', 'archives', 'comparisons', 'hooks']}, indent=2))


if __name__ == '__main__':
    main()
