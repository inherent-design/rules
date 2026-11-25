"""Profile-bound interpretation of captured core calls; never execute empack."""
import json
import re

FAILURE_MESSAGES={
 'invalid-project':'Lock does not satisfy requested pin',
 'not-installed':'Cannot update an uninstalled identity: d',
 'occupied-key':'Dependency label already names another selection: a',
 'runtime-mismatch':'Addition was resolved for a different runtime or compatibility policy',
}


def version(value):
    match=re.fullmatch(r'Version([123])',value)
    assert match,'Outside fictional exact-ID profile'
    return int(match[1])


def preference(debug):
    values=re.findall(r'\breleases: (None|Some\((?:StableOnly|PreferStable|Any)\))',debug)
    assert len(values)==1,'Not the one-author-root fixture'
    return {'None':'none','Some(StableOnly)':'stable-only','Some(PreferStable)':'prefer-stable','Some(Any)':'any'}[values[0]]


def update_frame(r,matching_evidence):
    assert r['kind']=='update' and r['key'] in ['a','c','d'] and r['version'] in [1,2]
    assert r['beforePins']=={'a':'Version1' if r['held'] else None}
    assert preference(r['beforeIntentDebug'])==('none' if r['held'] else 'stable-only')
    requested=r['request']
    wire=dict(id=r['case'],key=r['key'],held=r['held'],version=r['version'],
              request=None if requested is None else dict(key=requested['key'],version=version(requested['pin'])),
              runtimeMismatch=r['runtimeMismatch'],foreignIdentity=r['foreignIdentity'],evidenceMatches=matching_evidence)
    # Complete-edge premise comes from the frozen fixture/driver construction,
    # not an observed provider graph. Version1 is an equality label, not chronology.
    failure=r['error']
    if failure=='other':
        assert r['case']=='same-held-pin'
        assert r['message']=='Required selection conflicts with retained content: a; resolve its update explicitly'
        failure='retained-evidence'
    elif failure in FAILURE_MESSAGES:assert r['message']==FAILURE_MESSAGES[failure]
    elif failure=='invalid-pin':assert r['message'].startswith('Exact update pin must match a requested provider author root and its resolved selection: ')
    else:assert failure is None
    ok=r['accepted']
    if ok:
        assert r['error'] is None and r['message'] is None
        pins=r['afterPins'];assert 'a' in pins
        selected=version(r['selected'])
        author='automatic' if pins['a'] is None else pins['a']
        pref=preference(r['afterIntentDebug'])
        roots=sorted(pins)
    else:
        assert failure is not None
        for key in ['afterPins','afterIntentDebug','selected','changed','existing','otherIntentPreserved']:assert r[key] is None
        selected=author=pref=roots=None
    expected=dict(id=r['case'],accepted=ok,failure=failure,afterAuthorPin=author,afterPreference=pref,
                  selected=selected,changed=r['changed'],existing=r['existing'],afterRoots=roots,
                  inputUnchanged=r['inputUnchanged'],otherIntentPreserved=r['otherIntentPreserved'])
    return wire,expected


def packets(primary,control):
    rows=[json.loads(line) for line in (primary/'observed.stdout').read_text().splitlines()]
    follow=[json.loads(line) for line in (control/'observed.stdout').read_text().splitlines()]
    assert len(rows)==19 and len(follow)==1
    wire=dict(schema=1,preferences=[],admissions=[],updates=[])
    expected=dict(preferences=[],admissions=[],updates=[])
    for r in rows:
        if r['kind']=='preference':
            assert r['key'] in ['a','missing','c',None]
            wire['preferences'].append(dict(id=r['case'],project=r['project'],root=r['root'],operation=r['operation'],rootApplies=r['key']=='a'))
            expected['preferences'].append(dict(id=r['case'],actual=r['actual']))
        elif r['kind']=='admission':
            assert r['case']=='pin-and-preference-invalid'
            assert r['message']=='Release preference requires an unpinned provider request'
            wire['admissions'].append(dict(id=r['case'],pinned=True,preferencePresent=True))
            expected['admissions'].append(dict(id=r['case'],accepted=r['accepted']))
        else:
            a,b=update_frame(r,False);wire['updates'].append(a);expected['updates'].append(b)
    assert follow[0]['case']=='same-held-pin-matching-evidence'
    a,b=update_frame(follow[0],True);wire['updates'].append(a);expected['updates'].append(b)
    assert [len(wire[k]) for k in ['preferences','admissions','updates']]==[6,1,13]
    return wire,expected
