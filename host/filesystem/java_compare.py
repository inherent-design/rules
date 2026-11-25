#!/usr/bin/env python3
"""Pure retained Java library/attribute observations and scoped guard decisions."""
import hashlib
import json
from pathlib import Path
from protocol import facts,key
from verify import vectors

HERE=Path(__file__).resolve().parent
CAPTURES=['java-same-file-17-20261125T155733434126Z','java-same-file-21-20261125T155733742817Z','java-same-file-25-20261125T155734068359Z']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def decode(text):
    rows=[line.split('\t')for line in text.splitlines()]
    assert len(rows)==5 and [r[0]for r in rows]==['existing-equal','existing-different','case-spelling','missing-equal','missing-different']
    assert all(len(r)==4 for r in rows)
    assert rows[0][1:]==['true','directory','directory']
    assert rows[1][1:]==['false','directory','directory']
    assert rows[2][1:]in [['true','directory','directory'],['NoSuchFileException','directory','NoSuchFileException']]
    assert rows[3][1:]==['true','NoSuchFileException','NoSuchFileException']
    assert rows[4][1:]==['NoSuchFileException','NoSuchFileException','NoSuchFileException']
    return rows


def main():
    table=vectors();profiles=[];basis=[HERE/n for n in ['java_compare.py','protocol.py','verify.py','vectors.json']];controls=[]
    for feature,name in zip([17,21,25],CAPTURES):
        cap=HERE/'evidence'/name;r=json.loads((cap/'receipt.json').read_text());assert r['feature']==feature and r['classMajor']==61
        assert r['profile']['JAVA_VERSION'].startswith(str(feature)+'.')
        for n,h in r['sourcesSha256'].items():assert sha(cap/n)==h
        for stem,c in zip(['compile','execute'],r['commands']):
            assert c['exitCode']==0 and c['ownedGroupAbsent']and not c['timedOut']
            for channel in ['stdout','stderr']:assert sha(cap/(stem+'.'+channel))==c[channel+'Sha256']
        raw=(cap/'execute.stdout').read_text();rows=decode(raw);out=[]
        for label,same,a,b in rows:
            # No Java ancestry/complete-coverage or mutation-boundary protocol
            # was exercised. A false library result does not supply those facts.
            relation=1 if same=='true'and a==b=='directory'else 0
            row=facts(relation,False);decision=table[key(row)];assert decision[1]==0
            if label=='missing-equal':assert same=='true'and decision[0]==1
            out.append(dict(case=label,libraryResult=same,attributes=[a,b],preflight=decision[0]))
        for label,wrong in [('missing-equal-claims-object',raw.replace('missing-equal\ttrue\tNoSuchFileException\tNoSuchFileException','missing-equal\ttrue\tdirectory\tdirectory')),
                            ('changed-api-result',raw.replace('existing-equal\ttrue','existing-equal\tfalse'))]:
            try:decode(wrong)
            except AssertionError:controls.append(str(feature)+':'+label)
            else:raise AssertionError('Changed Java observation admitted.')
        profiles.append(dict(feature=feature,profile=r['profile'],calls=5,guardProjections=out));basis.extend(p for p in cap.iterdir()if p.is_file())
    report=dict(schema=1,status='passed-retained-java-samefile',calls=15,guardProjections=15,changedObservationControls=controls,profiles=profiles,
        basisSha256={str(p.relative_to(HERE.parents[1])):sha(p)for p in sorted(basis)},
        limits=['Selected default-provider calls on three Darwin JDKs;not all providers,permissions,hosts or races.',
                'Equal missing paths returning true is library behavior,not an existence witness or a demonstrated product bug.',
                'Guard projections use explicit attributes and withhold complete separation/boundary authority;shared Python adapter not formally proven.',
                'Private class/tool/execution artifact verification occurred at export;ordinary replay never starts Java or re-proves a JVM.'])
    (HERE/'evidence/java-conformance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],calls=15,guardProjections=15,changedObservationControls=len(controls))))


if __name__=='__main__':main()
