#!/usr/bin/env python3
"""Replay retained local copy observations; no restic or repository mutation."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from locks_probe import redact

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
RUN=ROOT/'applications/evidence/restic-copy-20261124T231054816138Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


class Labels:
    def __init__(self):self.values={}
    def get(self,value):
        if value is None:return None
        key=json.dumps(value,sort_keys=True,separators=(',',':'))
        if key not in self.values:self.values[key]=len(self.values)+1
        return self.values[key]


def inspect():
    receipt=json.loads((RUN/'receipt.json').read_text())
    assert receipt['producerSha256']==sha(RUN/'probe.py')and receipt['completionSha256']==sha(RUN/'finish.py')
    assert receipt['helperSha256']==sha(RUN/'helper.py')==sha(HERE/'locks_probe.py')
    assert sha(ROOT/'applications/tools/restic-0.20.0/restic')==receipt['tool']['binarySha256']
    assert receipt['allOwnedGroupsAbsent']and receipt['sourceRepositoryFilesUnchangedByCompletion']
    commands=json.loads((RUN/'commands.json').read_text())+json.loads((RUN/'finish-commands.json').read_text())
    assert len(commands)==receipt['initialCommands']+receipt['completionCommands']==54
    for c in commands:
        assert c['outcome']['ownedGroupAbsent']and not c['outcome'].get('timedOut',False)
        if 'sourceBefore'in c:assert c['sourceBefore']==c['sourceAfter']
        for name,stream in c['streams'].items():
            public=RUN/(c['case']+'.'+name);raw=RUN/stream['rawPrivatePath']
            assert sha(public)==stream['publicSha256']and sha(raw)==stream['rawSha256']and public.read_bytes()==redact(raw.read_bytes())
    assert {c['case']:c['outcome']['exitCode']for c in commands if c['outcome']['exitCode']!= 0}=={'wrong-source-password':12,'dump-c-0':1}
    obs=json.loads((RUN/'finished-observations.json').read_text());raw_path=RUN/'work/private/finished-observations.json'
    assert sha(raw_path)==receipt['rawFinishedObservationsSha256']and sha(RUN/'finished-observations.json')==receipt['finishedObservationsSha256']
    assert redact(raw_path.read_bytes())==(RUN/'finished-observations.json').read_bytes()
    raw=json.loads(raw_path.read_text());cases=[o for o in raw if 'sourceSnapshots'in o]
    assert len(cases)==8 and len([o for o in raw if 'payloadHex'in o])==3
    assert all(o['sourceRepositoryUnchanged']for o in cases)
    by={o['case']:o for o in cases};assert [len(o['newIds'])for o in cases]==[1,1,0,2,1,1,0,0]
    command_by={c['case']:c for c in commands}
    for c in cases:
        for field,label in [('before','-before'),('after','-after'),('sourceSnapshots','-source')]:
            assert c[field]==json.loads((RUN/command_by[c['case']+label]['streams']['stdout']['rawPrivatePath']).read_text())
        observed=command_by[c['case']]
        assert c['exitCode']==observed['outcome']['exitCode']
        assert c['newIds']==sorted({s['id']for s in c['after']}-{s['id']for s in c['before']})
        assert c['sourceRepositoryUnchanged']==(observed['before'][c['source']]==observed['after'][c['source']])
        assert c['destinationUnchanged']==(observed['before'][c['destination']]==observed['after'][c['destination']])
    for name in ['repeat-source','empty-tag-selection','wrong-source-password']:assert by[name]['destinationUnchanged']
    transitive=by['transitive']
    assert {s['id']for s in transitive['sourceSnapshots']}.isdisjoint({s['id']for s in transitive['after']})
    cfg=receipt['configs'];assert len({c['id']for c in cfg.values()})==3
    for n in cfg:assert cfg[n]==json.loads((RUN/command_by['finish-config-'+n]['streams']['stdout']['rawPrivatePath']).read_text())
    assert cfg['a']['chunker_polynomial']==cfg['b']['chunker_polynomial']!=cfg['c']['chunker_polynomial']
    first=by['explicit-first']['sourceSnapshots'][0]['id']
    second=next(s['id']for s in by['all-source']['sourceSnapshots']if s['id']!=first)
    source_second=next(s for s in by['all-source']['sourceSnapshots']if s['id']==second);assert source_second['parent']==first
    expected={first:command_by['backup-first']['sourceBefore']['mutable.txt']['sha256'],second:command_by['backup-second']['sourceBefore']['mutable.txt']['sha256']}
    for o in raw:
        if 'payloadHex'in o:
            assert o['payloadHex']==(RUN/command_by[o['case']]['streams']['stdout']['rawPrivatePath']).read_bytes().hex()
            assert hashlib.sha256(bytes.fromhex(o['payloadHex'])).hexdigest()==expected[o['snapshot']['original']]
    assert all(s.get('parent')is None for s in by['transitive-variant']['after'])
    return receipt,commands,cases


def rows(cases):
    identities,fixed,strings,ignored=Labels(),Labels(),Labels(),Labels()
    def project(s):return dict(id=identities.get(s['id']),original=identities.get(s.get('original')),parent=identities.get(s.get('parent')),
        fixed=fixed.get([s.get(k)for k in ['time','tree','hostname','username','uid','gid']]),
        paths=[strings.get(v)for v in s.get('paths',[])],tags=[strings.get(v)for v in s.get('tags',[])],excludes=[strings.get(v)for v in s.get('excludes',[])],
        ignored=ignored.get([s.get('program_version'),s.get('summary')]))
    def comparable(s):return {k:v for k,v in s.items()if k not in ['id','short_id','original','parent','program_version','summary']}
    result=[]
    for c in cases:
        selected=c['sourceSnapshots']
        if c['case']=='explicit-first':selected=[s for s in selected if s['id']in c['selection']]
        if c['case']=='empty-tag-selection':selected=[]
        if c['exitCode']==12:selected=selected[:1]
        for s in selected:
            # Expected copy effects come from a fresh destination listing. Match
            # preserved metadata exactly,not the model's membership comparator.
            found=[d for d in c['after']if d.get('original')==(s.get('original')or s['id'])and comparable(d)==comparable(s)]
            added=[d for d in found if d['id']in c['newIds']]
            assert len(added)<=1
            if c['exitCode']==12:status=12
            else:assert found;status=1 if added else 0
            target=project(added[0]if added else s);source=project(s)
            expectation='/'.join(map(str,[status,target['original']if added else source['original']or source['id'],'-'if target['parent']is None else 'parent',target['fixed']]))
            result.append(dict(case=c['case'],sourceId=s['id'],input=dict(source=source,destination=[project(d)for d in c['before']],sourceKeyAccepted=c['exitCode']!=12,copiedId=target['id']),
                measuredFields=[0,1,2,3]if added else[0],expected=expectation))
    return result


def bend_snap(s):
    option=lambda v:'None{}'if v is None else'Some{'+str(v)+'n}'
    values=lambda xs:'['+','.join(str(v)+'n'for v in xs)+']'
    return 'S.CSnap{'+','.join([str(s['id'])+'n',option(s['original']),option(s['parent']),str(s['fixed'])+'n',values(s['paths']),values(s['tags']),values(s['excludes']),str(s['ignored'])+'n'])+'}'
def compare(row,value):
    actual,expected=value.split('/'),row['expected'].split('/');assert len(actual)==len(expected)==4
    for i in row['measuredFields']:assert actual[i]==expected[i],(row['case'],i,actual,expected)


def main():
    receipt,commands,cases=inspect();observed=rows(cases);generated=HERE/'generated';generated.mkdir(exist_ok=True)
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend');env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1')
    target=ROOT/'.build/formal/applications/restic/Copy.olean';target.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.run([lean,'-DwarningAsError=true','-o',str(target),'applications/restic/Copy.lean'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    path=generated/'copy.json';data=dict(schema=1,profile='restic-local-copy',rows=[r['input']for r in observed])
    def replay(value):
        path.write_text(json.dumps(value)+'\n');return subprocess.run([lean,'--run','applications/restic/CopyCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    p=replay(data);assert p.returncode==0,p.stdout+p.stderr;actual=json.loads(p.stdout);assert len(actual)==len(observed)
    for row,value in zip(observed,actual):compare(row,value)
    calls=[]
    for r in observed:
        v=r['input'];calls.append('S.render('+bend_snap(v['source'])+',['+','.join(bend_snap(d)for d in v['destination'])+'],'+('True{}'if v['sourceKeyAccepted']else'False{}')+','+str(v['copiedId'])+'n) ++ "\\n"')
    driver=generated/'CopyCase.bend';driver.write_text('import Base\nimport ../Copy.bend as S\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(calls)+')\n')
    p=subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr;assert p.stdout.splitlines()==actual
    refusals=[]
    for name,edit in [('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='production-copy')),('count',lambda d:d.update(rows=d['rows']*30)),
        ('identity',lambda d:d['rows'][0]['source'].update(id=0)),('label',lambda d:d['rows'][0]['source'].update(fixed=4097)),('list',lambda d:d['rows'][0]['source'].update(tags=[1]*33)),('boolean',lambda d:d['rows'][0].update(sourceKeyAccepted='true'))]:
        bad=copy.deepcopy(data);edit(bad);p=replay(bad);assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);refusals.append(name)
    mutations=[]
    first=next(i for i,r in enumerate(observed)if len(r['measuredFields'])==4)
    for i in range(4):
        row=copy.deepcopy(observed[first]);parts=row['expected'].split('/');parts[i]='999';row['expected']='/'.join(parts)
        try:compare(row,actual[first])
        except AssertionError:mutations.append('field-'+str(i))
        else:raise AssertionError('Observation mutation escaped')
    ledger=json.loads((ROOT/'applications/sources/restic-copy-selections.json').read_text())
    for s in ledger['sources']:assert sha(ROOT/s['cache'])==s['sha256']
    files=[HERE/n for n in ['Copy.lean','Copy.bend','CopyCase.lean','copy_conformance.py','copy_probe.py','locks_probe.py']]
    files +=[ROOT/'applications/sources/restic-copy-selections.json']
    files +=[p for p in RUN.rglob('*')if p.is_file()and'work'not in p.relative_to(RUN).parts and p.name!='conformance.json']
    report=dict(schema=1,scope='Native local copy decisions and destination normalization;source-only duplicate/ignored-field laws remain separate.',
        nativeCopyCases=8,nativeCommands=54,modeledSourceDecisions=len(observed),decoderRefusals=refusals,expectedFieldMutations=mutations,
        comparisons=[{**r,'modelResult':a}for r,a in zip(observed,actual)],basisSha256={str(p.relative_to(ROOT)):sha(p)for p in sorted(set(files))},driverSha256=sha(driver),
        tools={n:dict(path=str(Path(p).resolve()),sha256=sha(Path(p)))for n,p in [('lean',lean),('bend',bend)]},
        limits=['No new restic/backup/copy/restore execution. Source fixed-field labels are built from owner-local raw observations;public user fields were redacted and alone cannot reconstruct those witnesses.',
                'Scalar labels and destination snapshot IDs are externally observed identities;no crypto,packing,hash collision,concurrency,remote or interruption proof.',
                'Copy-needed is a selection decision,not publication. Normalized metadata compares only actual added snapshots;skips/refusals compare only decisions. Filter selection is an observed input,not a modeled filter API.',
                'Initial failed dump is a harness path error. Its original records remain;seven read-only commands complete verification without repeating copy. Whole feature/parent scenario remains pending.'])
    (RUN/'conformance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in['comparisons','basisSha256']},indent=2))


if __name__=='__main__':main()
