#!/usr/bin/env python3
"""Pure retained workspace/search/edit replay; no VS Code or desktop actions."""
import copy
import json
import os
from pathlib import Path
import subprocess
import search_observations as observations

ROOT, RUN = observations.ROOT, observations.RUN
HERE = Path(__file__).resolve().parent
sha = observations.sha


def bend_call(row):
    b = lambda v: 'True{}' if v else 'False{}'
    n = lambda v: str(v) + 'n'
    s = json.dumps
    ls = lambda values: '[' + ','.join(values) + ']'
    roots = ls([s(v) for v in row.get('roots',[])])
    kind = row['kind']
    if kind in ['file','text']:
        resources = ls(['S.R{' + ','.join([s(r['identity']),s(r['root']),b(r['present']),b(r['excluded']),
                        b(r['providerMatch']),b(r['openEligible']),b(r['openMatch'])]) + '}' for r in row['resources']])
        if kind == 'file':
            return 'S.file_query_text(' + ','.join([resources,roots,b(row['respect']),b(row['cancelled'])]) + ')'
        return s('F|' if kind=='file' else 'T|') + ' ++ S.comma(S.' + ('file_results' if kind=='file' else 'text_results') + '(' + ','.join([resources,roots,b(row['respect'])]) + '))'
    if kind == 'workspace':
        return 'S.workspace_text(S.W{' + roots + ',None{}},' + ','.join([n(row['start']),n(row['count']),ls([s(v) for v in row['adds']])]) + ')'
    if kind == 'version':
        return '"E|" ++ Bool.pick(String,S.current_guard(' + n(row['submitted']) + ',' + n(row['actual']) + '),"1","0")'
    return 'S.groups_text(' + ls(['S.G{' + b(g['admitted']) + ',' + ls([s(v) for v in g['effects']]) + '}' for g in row['groups']]) + ')'


def main():
    native,host,sources = observations.inspect()
    rows, expected, ids = [], [], []
    for index,row in enumerate(native):
        value = observations.normalized(row)
        if value is not None:
            for key,default in dict(roots=[],respect=False,resources=[],cancelled=False,start=0,count=0,adds=[],
                                    planned=0,submitted=0,actual=0,groups=[]).items():
                value.setdefault(key,copy.deepcopy(default))
            rows.append(value)
            expected.append(observations.measured(row,native[index-1]))
            ids.append(row['id'])
    assert len(rows) == 18
    generated = HERE / 'generated'
    generated.mkdir(exist_ok=True)
    lean,bend = os.environ.get('LEAN','lean'),os.environ.get('BEND','bend')
    env = dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1')
    target = ROOT/'.build/formal/applications/vscode/WorkspaceSearch.olean'
    target.parent.mkdir(parents=True,exist_ok=True)
    p = subprocess.run([lean,'-DwarningAsError=true','-o',str(target),'applications/vscode/WorkspaceSearch.lean'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    assert p.returncode == 0,p.stdout+p.stderr
    input = dict(schema=1,profile='vscode-workspace-search-edits',rows=rows)
    path = generated/'workspace-search.json'

    def replay(value):
        path.write_text(json.dumps(value)+'\n')
        return subprocess.run([lean,'--run','applications/vscode/WorkspaceSearchCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)

    p = replay(input)
    assert p.returncode == 0,p.stdout+p.stderr
    actual = json.loads(p.stdout)
    assert actual == expected,(actual,expected)
    driver = generated/'WorkspaceSearchCase.bend'
    driver.write_text('import Base\nimport ../WorkspaceSearch.bend as S\n\ndef main() -> IO(Unit):\n  IO.write(' +
                     ' ++ '.join('(' + bend_call(r) + ' ++ "\\n")' for r in rows) + ')\n')
    p = subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    assert p.returncode == 0,p.stdout+p.stderr
    assert p.stdout.splitlines() == expected,(p.stdout,expected)
    refusals = []
    for name,edit in [
            ('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='full-vscode')),
            ('empty',lambda d:d.update(rows=[])),('count',lambda d:d.update(rows=d['rows']*4)),
            ('kind',lambda d:d['rows'][0].update(kind='rename')),
            ('root-identity',lambda d:d['rows'][0].update(roots=['personal'])),
            ('duplicate-root',lambda d:d['rows'][0].update(roots=['a','a'])),
            ('resource-identity',lambda d:d['rows'][0]['resources'][0].update(identity='/private/file')),
            ('wrong-owner',lambda d:d['rows'][0]['resources'][0].update(root='c')),
            ('unobserved-open-editor',lambda d:d['rows'][0]['resources'][0].update(openEligible=True)),
            ('duplicate-resource',lambda d:d['rows'][0].update(resources=[d['rows'][0]['resources'][0]]*2)),
            ('text-cancellation',lambda d:d['rows'][4].update(cancelled=True)),
            ('workspace-range',lambda d:d['rows'][9].update(start=4)),
            ('duplicate-addition',lambda d:d['rows'][9].update(adds=['c','c'])),
            ('unknown-version',lambda d:d['rows'][14].update(actual=0)),
            ('effects-bound',lambda d:d['rows'][-1]['groups'][0].update(effects=['delete:personal'])),
            ('boolean',lambda d:d['rows'][0].update(respect='true'))]:
        bad = copy.deepcopy(input)
        edit(bad)
        p = replay(bad)
        assert p.returncode == 2 and not p.stdout,(name,p.stdout,p.stderr)
        refusals.append(name)
    changed_inputs = []
    for name,index,edit in [
            ('file-exclusion',0,lambda r:r.update(respect=False)),
            ('open-no-match',6,lambda r:next(f for f in r['resources'] if f['identity']=='a/visible.txt').update(openEligible=False)),
            ('outside-open-scope',8,lambda r:next(f for f in r['resources'] if f['identity']=='outside.txt').update(openEligible=False)),
            ('submission-version',14,lambda r:r.update(actual=5)),
            ('earlier-group-effects',17,lambda r:r['groups'][0].update(admitted=False))]:
        bad = copy.deepcopy(input)
        edit(bad['rows'][index])
        p = replay(bad)
        assert p.returncode == 0,p.stderr
        assert json.loads(p.stdout) != expected,name
        changed_inputs.append(name)
    changed_outputs = []
    for name,index,edit in [
            ('file-result',1,lambda r:r['result']['paths'].remove('a/visible.txt')),
            ('buffer-result',9,lambda r:r['result'].update(matches=[])),
            ('workspace-membership',11,lambda r:r['result']['immediate'].pop()),
            ('range-outcome',16,lambda r:r['result'].update(accepted=False)),
            ('partial-effects',19,lambda r:r['files'].update({'a/interleaved.txt':{'present':False}}))]:
        bad = copy.deepcopy(native)
        edit(bad[index])
        projected = [observations.measured(r,bad[i-1]) for i,r in enumerate(bad) if observations.normalized(r) is not None]
        assert projected != actual,name
        changed_outputs.append(name)
    p = replay(input)
    assert p.returncode == 0 and json.loads(p.stdout) == expected
    files = [HERE/n for n in ['WorkspaceSearch.lean','WorkspaceSearch.bend','WorkspaceSearchCase.lean',
                             'search-extension.cjs','search_probe.py','search_observations.py','search_conformance.py']]
    files += [ROOT/'applications/sources/vscode-search-selections.json']
    files += [p for p in RUN.iterdir() if p.is_file() and p.name != 'conformance.json']
    report = dict(schema=1,nativeRows=21,modeledActions=18,contextRows=3,
                  comparisons=[dict(id=id,input=row,observed=e,model=m) for id,row,e,m in zip(ids,rows,expected,actual)],
                  researchRefusals=refusals,changedPremiseControls=changed_inputs,changedObservationControls=changed_outputs,
                  basisSha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(files))},driverSha256=sha(driver),
                  tools={n:dict(path=str(Path(p).resolve()),sha256=sha(Path(p))) for n,p in [('lean',lean),('bend',bend)]},
                  limits=['Pure retained-data replay; no VS Code, browser, desktop or native source acquisition.',
                          'Whole installed native APIs in an isolated multi-root profile; proposed findTextInFiles explicitly enabled. No Search UI, remote provider or supported-platform qualification.',
                          'Match/glob/URI admission and prepared-group facts are bounded adapters. No generic search/regex or file-group validator implemented.',
                          'Submission version is inferred from inspected source and immediate native API version, not a captured internal RPC.',
                          'Caller-range freshness is a separately proposed guard. Existing WorkspaceEdit does not promise to rebase ranges prepared earlier.',
                          'Three context rows include explicit cleanup-save; applyEdit success is not save/publication/durability.',
                          'Ordinary HOME with isolated profiles/in-memory secrets leaves OS-shared startup effects unmeasured.',
                          'All parent operation statuses remain pending; partial source/native coverage is recorded separately.'])
    (RUN/'conformance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['comparisons','basisSha256']},indent=2))


if __name__ == '__main__':
    main()
