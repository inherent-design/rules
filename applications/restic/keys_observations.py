#!/usr/bin/env python3
"""Read frozen key access/ownership observations; no restic/crypto execution."""
import hashlib,json
from pathlib import Path
from locks_probe import redact

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'applications/evidence/restic-keys-20261125T005527819839Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def inspect():
    receipt=json.loads((RUN/'receipt.json').read_text());commands=json.loads((RUN/'commands.json').read_text());identities=receipt['identities']
    assert len(commands)==receipt['commands']==21 and len(set(identities.values()))==3
    assert sha(RUN/'probe.py')==receipt['producerSha256']and sha(RUN/'helper.py')==receipt['helperSha256']
    assert sha(Path(__file__).with_name('locks_probe.py'))==receipt['helperSha256']
    assert receipt['allOwnedGroupsAbsent']and all(p['retired']for p in json.loads((RUN/'owned-processes.json').read_text()))
    tool=ROOT/'applications/tools/restic-0.20.0/restic';assert sha(tool)==receipt['tool']['sha256']
    by={c['case']:c for c in commands}
    baseline={k:v for k,v in by['backup']['after'].items()if not k.startswith('keys/')}
    assert baseline and any(k.startswith('snapshots/')for k in baseline)
    def keyset(image):
        result={p.removeprefix('keys/')for p in image if p.startswith('keys/')}
        assert result<=set(identities.values())
        for key in result:assert image['keys/'+key]['sha256']==key
        return result
    for c in commands:
        assert c['outcome']['ownedGroupAbsent']and not c['outcome']['timedOut']
        for name,s in c['streams'].items():
            public=RUN/(c['case']+'.'+name);assert sha(public)==s['publicSha256']
            raw=RUN/s['rawPrivatePath']
            if raw.exists():assert sha(raw)==s['rawSha256']and redact(raw.read_bytes())==public.read_bytes()
        if c['case']not in ['version','help-passwd','init','backup']:
            assert {k:v for k,v in c['before'].items()if not k.startswith('keys/')}==baseline
            assert {k:v for k,v in c['after'].items()if not k.startswith('keys/')}==baseline
            keyset(c['before']);keyset(c['after'])
        if c['case'].startswith('list-'):
            assert c['before']==c['after']and c['outcome']['exitCode']==0
            listed=json.loads((RUN/(c['case']+'.stdout')).read_text())
            assert {k['id']for k in listed}==keyset(c['after'])and sum(k['current']for k in listed)==1
        if c['case'].startswith('dump-'):
            assert c['before']==c['after']and sha(RUN/(c['case']+'.stdout'))==receipt['payloadSha256']
        if c['outcome']['exitCode']!=0:assert c['before']==c['after']
    for previous,current in zip(commands,commands[1:]):assert previous['after']==current['before']
    a,b,c=[identities[k]for k in ['initial','duplicate','changed']]
    assert keyset(by['add-same-password']['before'])=={a}and keyset(by['add-same-password']['after'])=={a,b}
    assert keyset(by['change-one-password']['before'])=={a,b}and keyset(by['change-one-password']['after'])=={b,c}
    assert keyset(by['remove-other-wrapper']['before'])=={b,c}and keyset(by['remove-other-wrapper']['after'])=={b}
    # Preserve actual password-change presentation; it describes the Key object
    # rather than printing the full returned ID promised by the selected help.
    change=(RUN/'change-one-password.stdout').read_text();assert 'saved new key as <Key of'in change and c not in change
    assert 'Returns the new key ID.'in(RUN/'help-passwd.stdout').read_text()
    assert 'refusing to remove key currently used'in(RUN/'remove-current-with-other.stderr').read_text()
    assert json.loads((RUN/'removed-password.stderr').read_text())['code']==12
    ledger=json.loads((ROOT/'applications/sources/restic-keys-selections.json').read_text())
    for source in ledger['sources']:assert sha(ROOT/source['cache'])==source['sha256']
    # Private fixture credentials must never appear in published command data.
    public=b'\n'.join(p.read_bytes()for p in RUN.iterdir()if p.is_file())
    for p in(RUN/'work').glob('password-*'):
        password=p.read_bytes().strip()
        if password:assert password not in public
    private=RUN/'work'
    if all((private/('password-'+n)).exists()for n in ['a','b','wrong','empty']):
        values=[(private/('password-'+n)).read_bytes()for n in ['a','b','wrong']]
        assert len(set(values))==3 and all(values)and(private/'password-empty').read_bytes()==b''
    return receipt,commands,keyset


if __name__=='__main__':
    receipt,commands,_=inspect();print(json.dumps(dict(commands=len(commands),allOwnedGroupsAbsent=True,backingUnchangedAfterBackup=True)))
