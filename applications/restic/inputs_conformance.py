#!/usr/bin/env python3
"""Pure finite pattern/traversal/outcome comparison; list admission is an adapter."""
import copy,fnmatch,hashlib,json,os,subprocess
from pathlib import Path
import inputs_observations as observations

ROOT,HERE,RUN=observations.ROOT,Path(__file__).resolve().parent,observations.RUN
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def build(receipt,rows):
    files=sorted(receipt['sourceBefore']);directories=['nested','pruned'];names=['.',*directories,*files]
    top=[f for f in files if'/'not in f]+directories
    def hit(pattern,path,insensitive):
        # This finite adapter admits only the literal/suffix spellings exercised
        # here. It is not a general Go filepath.Match or Unicode-case model.
        if insensitive:pattern,path=pattern.lower(),path.lower()
        assert pattern in ['*.tmp','*.TMP','secret.tmp','pruned','pruned/keep.txt','nested']
        if pattern.startswith('*.'):return any(c.endswith(pattern[1:])for c in path.split('/'))
        parts,path_parts=pattern.split('/'),path.split('/')
        return any(path_parts[i:i+len(parts)]==parts for i in range(len(path_parts)-len(parts)+1))
    results=[]
    for row in rows:
        args=iter(row['request']);targets=[];ordinary=[];insensitive=[];framing=True
        for value in args:
            if value in ['--exclude','--iexclude']:
                (ordinary if value=='--exclude'else insensitive).append(next(args));continue
            if value in ['--files-from','--files-from-verbatim','--files-from-raw']:
                p=Path(next(args));assert p.parent==RUN/'work/lists';raw=p.read_bytes()
                if value=='--files-from-raw':
                    framing=raw.endswith(b'\0')and all(raw[:-1].split(b'\0'))
                    if framing:targets +=[s.decode('utf8')for s in raw[:-1].split(b'\0')]
                elif value=='--files-from-verbatim':targets +=[s for s in raw.decode('utf8').split('\n')if s]
                else:
                    for line in raw.decode('utf8').split('\n'):
                        line=line.strip()
                        if not line or line.startswith('#'):continue
                        assert line in ['keep.txt','space name.txt','*.tmp','[literal].txt']
                        targets +=sorted(n for n in top if fnmatch.fnmatchcase(n,line))
                continue
            assert value in ['.','nested','secret.tmp'];targets.append(value)
        groups=[]
        for patterns,fold in [(insensitive,True),(ordinary,False)]:
            if patterns:
                groups.append([dict(negated=p.startswith('!'),hits=[n for n in names if hit(p.removeprefix('!'),n,fold)])for p in patterns])
        roots=[t for t in targets if t in names]
        data=dict(groups=groups,roots=roots,skippedMissing=len(roots)!=len(targets),framingValid=bool(framing))
        expected=dict(exitCode=row['exitCode'],snapshot=bool(row['newSnapshots']),selected=[f in row['files']for f in files])
        results.append(dict(case=row['case'],input=data,expected=expected))
    return files,results


def compare(expected,actual):assert expected==actual,(expected,actual)
def bend_list(values,encode):
    result='Nil{}'
    for v in reversed(values):result='Con{'+encode(v)+','+result+'}'
    return result
def bend_call(row,files):
    r=row['input'];b=lambda v:'True{}'if v else'False{}';s=lambda v:json.dumps(v,ensure_ascii=False)
    rule=lambda v:'S.IRule{'+b(v['negated'])+','+bend_list(v['hits'],s)+'}'
    groups=bend_list(r['groups'],lambda g:bend_list(g,rule))
    calls=['Nat.show(S.exit_code('+b(r['framingValid'])+','+b(bool(r['roots']))+','+b(r['skippedMissing'])+'))',
        'S.bit(S.snapshot('+b(r['framingValid'])+','+b(bool(r['roots']))+'))']
    for f in files:
        chains=[]
        for root in r['roots']:
            if root=='.'or f.startswith(root+'/'):
                parts=f.split('/');prefixes=['/'.join(parts[:i])for i in range(1,len(parts)+1)]
                chains.append([p for p in prefixes if root=='.'or p!=root])
        encoded=bend_list(chains,lambda chain:bend_list(chain,s))
        admitted='S.snapshot('+b(r['framingValid'])+','+b(bool(r['roots']))+')'
        calls.append('S.bit(Bool.and('+admitted+',S.selected('+groups+','+b(f in r['roots'])+','+encoded+')))')
    return ' ++ "|" ++ '.join(calls)+' ++ "\\n"'


def main():
    receipt,native,commands=observations.inspect();files,rows=build(receipt,native)
    generated=HERE/'generated';generated.mkdir(exist_ok=True)
    lean,bend=os.environ.get('LEAN','lean'),os.environ.get('BEND','bend');env=dict(os.environ,LEAN_PATH=str(ROOT/'.build/formal'),BEND_NO_TELEMETRY='1')
    target=ROOT/'.build/formal/applications/restic/Inputs.olean';target.parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.run([lean,'-DwarningAsError=true','-o',str(target),'applications/restic/Inputs.lean'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    assert p.returncode==0,p.stdout+p.stderr
    path=generated/'inputs.json';data=dict(schema=1,profile='local-relative-regular-inputs',rows=[r['input']for r in rows])
    def replay(value):
        path.write_text(json.dumps(value)+'\n');return subprocess.run([lean,'--run','applications/restic/InputsCase.lean',str(path)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    p=replay(data);assert p.returncode==0,p.stdout+p.stderr;actual=json.loads(p.stdout);expected=[r['expected']for r in rows];compare(expected,actual)
    driver=generated/'InputsCase.bend';driver.write_text('import Base\nimport ../Inputs.bend as S\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(bend_call(r,files)for r in rows)+')\n')
    p=subprocess.run([bend,str(driver)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=90);assert p.returncode==0,p.stdout+p.stderr
    results=[]
    for line in p.stdout.splitlines():
        fields=line.split('|');assert len(fields)==2+len(files)and all(v in ['0','1']for v in fields[1:])
        results.append(dict(exitCode=int(fields[0]),snapshot=fields[1]=='1',selected=[v=='1'for v in fields[2:]]))
    compare(expected,results)
    refusals=[]
    for name,edit in [('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='general-glob')),
        ('count',lambda d:d.update(rows=d['rows']*7)),('root',lambda d:d['rows'][0].update(roots=['../outside'])),
        ('root-bound',lambda d:d['rows'][0].update(roots=['.']*17)),('group-bound',lambda d:d['rows'][0].update(groups=[[]]*5)),
        ('path-witness',lambda d:d['rows'][1]['groups'][0][0].update(hits=['../outside'])),
        ('duplicate-witness',lambda d:d['rows'][1]['groups'][0][0].update(hits=['secret.tmp']*2)),
        ('boolean',lambda d:d['rows'][0].update(framingValid='true')),('missing-field',lambda d:d['rows'][0].pop('skippedMissing'))]:
        bad=copy.deepcopy(data);edit(bad);p=replay(bad);assert p.returncode==2 and not p.stdout,(name,p.stdout,p.stderr);refusals.append(name)
    premise_mutations=[]
    for name,edit in [('framing-witness',lambda d:d['rows'][0].update(framingValid=False)),
        ('comment-witness',lambda d:d['rows'][10]['roots'].append('#literal.txt')),
        ('ordered-rule-witness',lambda d:d['rows'][5]['groups'][0].reverse()),
        ('pruned-parent-witness',lambda d:d['rows'][6]['groups'][0][0]['hits'].remove('pruned'))]:
        bad=copy.deepcopy(data);edit(bad);p=replay(bad);assert p.returncode==0,p.stdout+p.stderr
        changed=json.loads(p.stdout)
        try:compare(expected,changed)
        except AssertionError:premise_mutations.append(name)
        else:raise AssertionError('Changed adapter premise escaped native comparison: '+name)
    mutations=[]
    for name,index,field in [('explicit-file',2,'selected'),('pruned-parent',6,'selected'),('verbatim-comment',11,'selected'),
        ('raw-newline',16,'selected'),('invalid-framing',17,'snapshot'),('partial-status',19,'exitCode'),('empty-tree',3,'snapshot')]:
        bad=copy.deepcopy(expected)
        if field=='selected':bad[index][field]=[not v for v in bad[index][field]]
        elif field=='snapshot':bad[index][field]=not bad[index][field]
        else:bad[index][field]=0
        try:compare(bad,actual)
        except AssertionError:mutations.append(name)
        else:raise AssertionError('Changed native observation escaped: '+name)
    sources=[HERE/n for n in ['Inputs.lean','Inputs.bend','InputsCase.lean','inputs_probe.py','inputs_observations.py','inputs_conformance.py']]
    sources +=[ROOT/'applications/sources/restic-inputs-selections.json']
    sources +=[p for p in RUN.iterdir()if p.is_file()and p.name!='conformance.json']
    sources +=[p for p in observations.FAILED.iterdir()if p.is_file()]
    result=dict(schema=1,cases=20,nativeCommands=len(commands),files=files,comparisons=[dict(**r,model=a)for r,a in zip(rows,actual)],
        researchRefusals=refusals,normalizedPremiseMutations=premise_mutations,observationMutations=mutations,driverSha256=sha(driver),basisSha256={str(p.relative_to(ROOT)):sha(p)for p in sorted(set(sources))},
        tools={n:dict(path=str(Path(p).resolve()),sha256=sha(Path(p)))for n,p in [('lean',lean),('bend',bend)]},
        limits=['Pure replay;no restic,repository mutation,backup/restore or native fixture execution.',
            'Both models compare finite ordered exclusion/traversal/outcome projections after target admission. Python supplies checked finite match/list witnesses;no formal general Go glob,raw/line parser,Unicode-case or filesystem admission proof.',
            'Native saved paths/types/sizes are checked,not per-file restored bytes,repository encryption/chunking,durability or crash consistency.',
            'One local macOS regular-file fixture with relative targets. No absolute-root,special/symlink,permission/cloud/device or remote/race scope.',
            'Cross-group negation law is model/source-only;native cases exercise one ordinary or one insensitive group at a time.',
            'Initial successful backup/ls followed by a collector host-path projection assertion remains retained separately;corrected fresh run is not reattributed to it.',
            'Restic restore include options are separate;this backup cohort tests ordered negative excludes,not native restore include.'])
    (RUN/'conformance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ['comparisons','basisSha256']},indent=2))


if __name__=='__main__':main()
