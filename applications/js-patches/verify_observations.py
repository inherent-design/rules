#!/usr/bin/env python3
"""Verify retained fixture identities and selected facts; not formal conformance."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
NAMES=['js-patches-help-20261124T173628320229Z','js-patches-20261124T173819947477Z',
    'js-patches-20261124T173857262805Z','js-patches-followup-20261124T174112934092Z',
    'js-patches-control-20261124T174304431021Z']


def main():
    captures={name:ROOT/'applications/evidence'/name for name in NAMES}
    ledger=ROOT/'applications/sources/js-patches-selections.json'
    for source in json.loads(ledger.read_text()):assert sha(ROOT/source['cache'])==source['sha256']
    basis={str(ledger.relative_to(ROOT)):sha(ledger)};traces={}
    for name,capture in captures.items():
        ast.parse((capture/'probe.py').read_text())
        for p in capture.rglob('*'):
            if p.is_file() and 'work' not in p.relative_to(capture).parts:
                basis[str(p.relative_to(ROOT))]=sha(p)
        if 'help' in name:
            rows=json.loads((capture/'commands.json').read_text());receipt=json.loads((capture/'receipt.json').read_text())
            assert len(rows)==receipt['commands']==6 and receipt['producerSha256']==sha(capture/'probe.py')
            for row in rows:
                assert row['exitCode']==0 and not row['timedOut']
                for stream in ['stdout','stderr']:assert sha(capture/(row['app']+'-'+row['command']+'.'+stream))==row[stream+'Sha256']
            continue
        rows=json.loads((capture/'trace.json').read_text());traces[name]=rows
        receipt_path=capture/'receipt.json'
        if receipt_path.exists():
            receipt=json.loads(receipt_path.read_text());assert receipt['commands']==len(rows) and receipt['producerSha256']==sha(capture/'probe.py')
            for tool in receipt['tools'].values():assert sha(Path(tool['path']))==tool['sha256']
        else:
            failure=json.loads((capture/'failure.json').read_text());review=json.loads((capture/'capture-review.json').read_text())
            assert failure['commands']==len(rows) and review['traceSha256']==sha(capture/'trace.json') and review['originalProducerSha256']==sha(capture/'probe.py')
        for row in rows:
            assert not row['outcome']['timedOut']
            for stream in ['stdout','stderr']:assert sha(capture/(row['app']+'-'+row['case']+'.'+stream))==row['observed'][stream+'Sha256']
            for frame in [row['observed']['before'],row['observed']['after']]:
                for value in [*frame['files'].values(),*([frame['installed']] if frame['installed'] else [])]:
                    p=capture/value['captured'];assert sha(p)==value['sha256'] and p.stat().st_size==value['bytes']
                if frame['installed']:assert (capture/frame['installed']['captured']).read_text()==frame['installed']['content']
            if row['case'].endswith('-runtime'):
                data=json.loads((capture/(row['app']+'-'+row['case']+'.stdout')).read_text());payload=row['observed']['after']['installed'];assert payload is not None
                expected='patched' if payload['content']=='module.exports = "patched";\n' else 'base'
                assert payload['content'] in ['module.exports = "patched";\n','module.exports = "base";\n']
                assert data==dict(value=expected,path=payload['path'])
    primary_name=NAMES[2];primary=captures[primary_name];rows=traces[primary_name]
    control_name=NAMES[4];control=captures[control_name];controls=traces[control_name]
    assert [len(traces[n]) for n in NAMES[1:]]==[16,36,10,15]
    def select(rows,app,case):return next(r for r in rows if r['app']==app and r['case']==case)
    for observations in [rows,controls]:
        good=select(observations,'pnpm','install-patch');bad=select(observations,'pnpm','invalid-apply');restored=select(observations,'pnpm','restore-valid')
        assert good['outcome']['exitCode']==0 and good['observed']['after']['installed']['content']=='module.exports = "patched";\n'
        assert bad['outcome']['exitCode']==1 and bad['observed']['after']['installed']['content']=='module.exports = "base";\n'
        assert restored['outcome']['exitCode']==0 and restored['observed']['after']['installed']['content']=='module.exports = "base";\n'
        assert bad['observed']['after']['installed']['path']==restored['observed']['after']['installed']['path']
        assert good['observed']['after']['files']['pnpm-lock.yaml']==restored['observed']['after']['files']['pnpm-lock.yaml']
        def patch_hash(frame):return next(v['sha256'] for k,v in frame['files'].items() if k.endswith('.patch'))
        assert patch_hash(good['observed']['after'])==patch_hash(restored['observed']['after'])!=patch_hash(bad['observed']['after'])
    forced=select(controls,'pnpm','force-valid-repair');assert forced['outcome']['exitCode']==0 and forced['observed']['after']['installed']['content']=='module.exports = "patched";\n'
    assert forced['observed']['after']['installed']['path']==select(controls,'pnpm','install-patch')['observed']['after']['installed']['path']
    assert select(rows,'yarn','commit')['observed']['after']['installed']['content']=='module.exports = "base";\n'
    assert select(rows,'yarn','frozen-after-commit')['outcome']['exitCode']==1
    assert select(rows,'yarn','invalid-apply')['observed']['after']['installed']['content']=='module.exports = "patched";\n'
    unplug=select(rows,'yarn','unplug');assert unplug['outcome']['exitCode']==1 and unplug['observed']['before']==unplug['observed']['after']
    missing=select(rows,'pnpm','remove-missing-version-key');assert missing['outcome']['exitCode']==1 and missing['observed']['before']==missing['observed']['after']
    follow=traces[NAMES[3]];assert select(follow,'pnpm','retry-same-bad-install')['outcome']['exitCode']==1
    assert select(follow,'yarn','install-unpatched')['observed']['after']['installed']['content']=='module.exports = "base";\n'
    assert all(sha(ROOT/path)==digest for path,digest in basis.items())
    print(json.dumps(dict(schema=1,helpCommands=6,packageAndRuntimeCommands=77,freshPnpmControlReproducesSuccessWithUnpatchedPayload=True,
        forcedRepairObserved=True,retryOfSameInvalidPatchStillRefused=True,sourcePins=len(json.loads(ledger.read_text())),
        limits='Observation checks only;Lean/Bend models,formal replay,full source mechanism and joined lifecycle qualification pending.'),indent=2))


if __name__=='__main__':main()
