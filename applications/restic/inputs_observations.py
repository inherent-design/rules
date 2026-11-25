#!/usr/bin/env python3
"""Read retained input-policy streams/source images; never run restic."""
import hashlib,json
from pathlib import Path
from locks_probe import redact

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'applications/evidence/restic-inputs-20261125T025013712984Z'
FAILED=ROOT/'applications/evidence/restic-inputs-20261125T024920808343Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def inspect():
    receipt=json.loads((RUN/'receipt.json').read_text());rows=json.loads((RUN/'observations.json').read_text())
    commands=json.loads((RUN/'commands.json').read_text());by={r['case']:r for r in rows}
    assert receipt['cases']==len(rows)==len(by)==20 and receipt['commands']==len(commands)
    expected_commands=['init']
    for row in rows:
        expected_commands.append(row['case'])
        if row['newSnapshots']:expected_commands.append(row['case']+'-ls')
    assert [c['case']for c in commands]==expected_commands
    assert receipt['producerSha256']==sha(RUN/'probe.py')and receipt['helperSha256']==sha(RUN/'helper.py')
    assert receipt['allOwnedProcessesRetired']and receipt['finalLocks']==[]
    assert receipt['sourceBefore']==receipt['sourceAfter']
    assert all(c['retired']for c in json.loads((RUN/'owned-processes.json').read_text()))
    tool=Path(receipt['tool']['path']);assert sha(tool)==receipt['tool']['sha256']
    work=RUN/'work';source=work/'source'
    assert not list((work/'repository/locks').glob('*'))
    assert sorted(p.name for p in(work/'repository/snapshots').iterdir())==sorted(s for row in rows for s in row['newSnapshots'])
    actual={str(p.relative_to(source)):dict(sha256=sha(p),size=p.stat().st_size,mtimeNs=p.stat().st_mtime_ns,inode=p.stat().st_ino)
        for p in source.rglob('*')if p.is_file()}
    assert actual==receipt['sourceAfter']
    for name,h in receipt['listSha256'].items():assert sha(work/'lists'/name)==h
    for c in commands:
        assert not c['outcome']['timedOut']and c['outcome']['ownedGroupAbsent']
        for stream,s in c['streams'].items():
            raw=RUN/s['rawPrivatePath'];public=RUN/(c['case']+'.'+stream)
            assert sha(raw)==s['rawSha256']and sha(public)==s['publicSha256']
            assert redact(raw.read_bytes())==public.read_bytes()
    def lines(label):return [json.loads(s)for s in(work/'private'/(label+'.stdout')).read_text().splitlines()]
    for row in rows:
        c=next(c for c in commands if c['case']==row['case']);assert row['exitCode']==c['outcome']['exitCode']
        summaries=[r for r in lines(row['case'])if r.get('message_type')=='summary']
        if row['newSnapshots']:
            assert len(row['newSnapshots'])==len(summaries)==1
            assert summaries[0]['snapshot_id']==row['newSnapshots'][0]
            ls=next(c for c in commands if c['case']==row['case']+'-ls');assert ls['outcome']['exitCode']==0
            nodes=[]
            for n in lines(row['case']+'-ls'):
                if n.get('struct_type')!='node':continue
                p=Path(n['path']);assert p.is_absolute()and'..'not in p.parts
                nodes.append(dict(path=str(p.relative_to('/')),type=n['type']))
            nodes.sort(key=lambda n:n['path']);assert nodes==row['nodes']
            files=sorted(n['path']for n in nodes if n['type']=='file');assert files==row['files']
            assert set(files)<=set(actual)
            for n in lines(row['case']+'-ls'):
                if n.get('type')=='file':assert n['size']==actual[str(Path(n['path']).relative_to('/'))]['size']
        else:assert not summaries and row['files']==row['nodes']==[]
    allfiles=set(actual)
    # These independent expectations concern domain distinctions, not a second
    # copy of the model's eventual matching/list-decoding implementation.
    assert set(by['directory']['files'])==allfiles
    assert set(by['exclude-descendants']['files'])==allfiles-{'secret.tmp','nested/secret.tmp'}
    assert by['explicit-file']['files']==['secret.tmp']
    assert by['explicit-directory']['newSnapshots']and by['explicit-directory']['files']==[]
    assert dict(path='nested',type='dir')in by['explicit-directory']['nodes']
    assert by['ordered-reinclude']['files']==by['directory']['files']
    assert by['ordered-reexclude']['files']==by['exclude-descendants']['files']
    assert set(by['pruned-parent']['files'])==allfiles-{'pruned/keep.txt'}
    assert by['reopened-parent']['files']==by['directory']['files']
    assert by['insensitive']['files']==by['exclude-descendants']['files']
    assert by['sensitive']['files']==by['directory']['files']
    assert by['normal-list']['files']==['keep.txt','space name.txt']
    assert by['verbatim-list']['files']==['#literal.txt','keep.txt','space name.txt']
    assert by['glob-list']['files']==['secret.tmp']and by['verbatim-brackets']['files']==['[literal].txt']
    assert by['raw-newline']['files']==['#literal.txt','line\nbreak.txt']
    for name in ['verbatim-glob','normal-brackets','raw-unterminated','raw-empty']:
        assert by[name]['exitCode']==1 and not by[name]['newSnapshots']
    assert by['partial-list']['exitCode']==3 and by['partial-list']['files']==['keep.txt']and by['partial-list']['newSnapshots']
    tree={r['path']:r for r in json.loads((ROOT/'applications/tools/source-cache/restic-restore-tree.json').read_text())['tree']}
    ledger=json.loads((ROOT/'applications/sources/restic-inputs-selections.json').read_text())
    for row in ledger['sources']:
        p=ROOT/row['cache'];data=p.read_bytes();assert sha(p)==row['sha256']
        assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==row['gitBlobSha1']==tree[row['path']]['sha']
    # Preserve the initial collector failure without counting it as another
    # successful input-policy cohort or attributing its projection error to restic.
    failure=json.loads((FAILED/'collector-failure.json').read_text());assert failure['status'].startswith('Preserved collector failure')
    first=json.loads((FAILED/'commands.json').read_text());assert [c['case']for c in first]==['init','directory','directory-ls']
    assert all(c['outcome']['exitCode']==0 and c['outcome']['ownedGroupAbsent']for c in first)
    assert all(c['retired']for c in json.loads((FAILED/'owned-processes.json').read_text()))
    for c in first:
        for stream,s in c['streams'].items():
            raw=FAILED/s['rawPrivatePath'];public=FAILED/(c['case']+'.'+stream)
            assert sha(raw)==s['rawSha256']and sha(public)==s['publicSha256']and redact(raw.read_bytes())==public.read_bytes()
    return receipt,rows,commands


if __name__=='__main__':
    r,rows,c=inspect();print(json.dumps(dict(cases=len(rows),commands=len(c),preservedCollectorFailure=True,sourceFiles=len(r['sourceBefore']),modelComparison=False)))
