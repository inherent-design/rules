#!/usr/bin/env python3
"""Verify frozen feature/compiled-unit observations without rerunning Cargo."""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
CAPTURE=ROOT/'applications/evidence/cargo-features-20261124T181357949100Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=CAPTURE;receipt=json.loads((p/'receipt.json').read_text());rows=json.loads((p/'trace.json').read_text());configs=json.loads((p/'configuration.json').read_text());binaries=json.loads((p/'binaries.json').read_text())
    assert len(rows)==receipt['commands']==51 and len(binaries)==20 and receipt['targetCleaned']
    assert sha(p/'probe.py')==receipt['producerSha256']
    assert not (p/'work/target').exists()
    for tool in receipt['tools'].values():assert sha(Path(tool['path']))==tool['sha256']
    source_pins=json.loads((ROOT/'applications/sources/cargo-features-selections.json').read_text())
    for source in source_pins:assert sha(ROOT/source['localCache'])==source['sha256']
    flags=receipt['flags'];assert flags==['normal','build','dev','platform','extra','explicit','defaulted','sibling','default']
    def mask(names):
        assert len(names)==len(set(names)) and set(names)<=set(flags)
        return sum(1<<flags.index(n) for n in names)
    def names(bits):return [n for i,n in enumerate(flags) if bits&(1<<i)]
    metadata={};runtime=[];refused=[]
    for row in rows:
        resolver=row['resolver'];case=row['case'];stem='r'+str(resolver)+'-'+case
        assert not row['outcome']['timedOut']
        for stream in ['stdout','stderr']:assert sha(p/(stem+'.'+stream))==row['observed'][stream+'Sha256']
        expected={name:hashlib.sha256(text.encode()).hexdigest() for name,text in configs[str(resolver)].items()}
        assert row['observed']['before']['sourceSha256']==row['observed']['after']['sourceSha256']==expected
        raw=(p/(stem+'.stdout')).read_text()
        if case.startswith('metadata'):
            data=json.loads(raw);ids={q['id']:q['name'] for q in data['packages']};assert set(ids.values())=={'fixture-app','fixture-flags','fixture-defaults'}
            node=next(n for n in data['resolve']['nodes'] if ids[n['id']]=='fixture-flags')
            if resolver in metadata:assert ids==metadata[resolver]['ids']
            else:metadata[resolver]=dict(ids=ids,mask=mask(node['features']))
            assert mask(node['features'])==479
        elif case=='qualified-self-feature-refusal':
            assert resolver==1 and row['outcome']['exitCode']==101
            assert 'does not have a dependency named `fixture-app`' in (p/(stem+'.stderr')).read_text()
            assert not any(json.loads(line).get('reason')=='compiler-artifact' for line in raw.splitlines())
            refused.append(stem)
        else:assert row['outcome']['exitCode']==0
        if case.endswith('-runtime'):
            records=re.findall(r'FIXTURE_(APP|TEST):(\{[^\n]+\})',raw);assert len(records)==1
            kind,payload=records[0];value=json.loads(payload);assert set(value)=={'normal','build'}
            assert all(type(v)is int and 0<=v<512 for v in value.values())
            compile_case=case.removesuffix('-runtime');binary=next(b for b in binaries if b['resolver']==resolver and b['case']==compile_case)
            assert re.fullmatch('[a-f0-9]{64}',binary['sha256']) and binary['bytes']>0
            assert row['argv'][0]==binary['path']
            assert bool(binary['artifact']['profile']['test'])==(kind=='TEST')
            messages=[json.loads(line) for line in (p/('r'+str(resolver)+'-'+compile_case+'.stdout')).read_text().splitlines()]
            sets={mask(m['features']) for m in messages if m.get('reason')=='compiler-artifact' and metadata[resolver]['ids'][m['package_id']]=='fixture-flags'}
            # Role names come from this fixture's unique declaration tags,
            # not an invented compiler-emitted host/target field.
            normal=[s for s in sets if s&1];build=[s for s in sets if s&2]
            assert normal==[value['normal']] and build==[value['build']],(stem,sets,value)
            runtime.append(dict(resolver=resolver,case=compile_case,normal=value['normal'],build=value['build'],normalFeatures=names(value['normal']),buildFeatures=names(value['build']),reportedLibraryFeatureSets=sorted(sets),kind=kind))
    assert len(runtime)==20 and len(refused)==1
    assert rows[-1]['case']=='clean' and not rows[-1]['observed']['after']['targetPresent']
    for name,text in configs['3'].items():assert sha(p/'work/project'/name)==hashlib.sha256(text.encode()).hexdigest()
    # The omitted feature is enabled by another selected declaration; a false
    # default flag on one request is not a global negative constraint.
    for resolver in [2,3]:
        row=next(r for r in runtime if r['resolver']==resolver and r['case']=='workspace-no-default')
        assert 'default' in row['normalFeatures'] and 'defaulted'in row['normalFeatures'] and 'sibling'not in row['normalFeatures']
    report=dict(schema=1,commands=51,metadataCommands=9,compiledAndExecutedCases=20,qualifiedSelfRefusals=refused,
        sourcePins=len(source_pins),peakTargetAllocatedKiB=receipt['peakTargetAllocatedKiB'],targetCleaned=True,scopedRuntime=runtime,
        limits=['Observed profile consistency only;the separate features_conformance.py checks the Lean/Bend policy projection.',
          'Metadata queries retain one package reached by several kinds;this is not a discriminating test of conditional-only package removal by filter-platform.',
          'Build/test outputs are directly executed on the same Mac. Windows metadata is not Windows compilation;resolver3 MSRV selection is not exercised.',
          'Compiler-reported feature sets are observed;role labels use controlled source tags and runtime/build-script witnesses. They are not raw UnitKind fields or counts of newly compiled units.',
          'Executable SHA256/size were measured before owned target cleanup;cleaned executables are not currently available at historical output paths.'])
    (ROOT/'applications/cargo/features-observations.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='scopedRuntime'},indent=2))


if __name__=='__main__':main()
