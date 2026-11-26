#!/usr/bin/env python3
"""Replay retained namespace decisions;never runs pnpm,Node,or package scripts."""
import argparse,copy,json,os,subprocess
from pathlib import Path
import observations as obs

ROOT=obs.ROOT;HERE=Path(__file__).resolve().parent
OUT=ROOT/'applications/evidence/pnpm-admission-comparison'
WORK=ROOT/'.build/pnpm-admission-replay'
KINDS={'tasks':0,'placeholder':1,'explicit-run':2,'declared-fallback':3}
B=lambda b:'True{}'if b else'False{}'
LIST=lambda xs:'['+','.join(json.dumps(s)for s in xs)+']'


def bend_request(r):
    values=[str(KINDS[r['kind']])+'n']+[B(r[k])for k in['forcedBuiltin','builtinHelp','inMember','localBody','rootBody']]+[json.dumps(r['scriptLabel']),LIST(r['args'])]
    return 'A.render(A.run(A.Request{'+','.join(values)+'}))'


def render(o):
    return '/'.join([o[0],str(o[1]),'~'if o[2]is None else o[2],''.join(a+','for a in o[3]),'~'if o[4]is None else o[4]])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--public-only',action='store_true');opts=parser.parse_args()
    request,measured,details,basis,excluded=obs.evidence(not opts.public_only)
    assert len(request['cases'])==len(measured)==15
    labels=[d['label']for d in details if d['role']=='namespace-case'];index={n:i for i,n in enumerate(labels)}
    OUT.mkdir(exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,LEAN_PATH=str(WORK),BEND_NO_TELEMETRY='1');lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend')
    def command(argv):return subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
    target=WORK/'applications/pnpm-admission/Admission.olean';target.parent.mkdir(parents=True,exist_ok=True)
    p=command([lean,'-DwarningAsError=true','-o',str(target),'applications/pnpm-admission/Admission.lean']);assert p.returncode==0,p.stdout+p.stderr
    path=WORK/'request.json'
    def replay(value):
        path.write_text(json.dumps(value)+'\n')
        return command([lean,'--run','applications/pnpm-admission/AdmissionCase.lean',str(path)])
    p=replay(request);assert p.returncode==0,p.stdout+p.stderr;assert json.loads(p.stdout)==measured,(p.stdout,measured)
    driver=WORK/'AdmissionReplay.bend';expressions=[bend_request(r)for r in request['cases']]
    # These are pure input-prefix comparisons, not 15 additional native cases.
    for r in request['cases']:
        expressions.append('Bool.pick(String,A.leading_pm('+LIST(r['rawArgs'])+'),"1","0")')
    driver.write_text('import Base\nimport '+str(HERE/'Admission.bend')+' as A\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join('('+e+' ++ "\\n")'for e in expressions)+')\n')
    p=command([bend,str(driver)]);assert p.returncode==0,p.stdout+p.stderr
    assert p.stdout.splitlines()==[render(o)for o in measured]+[str(int(r['forcedBuiltin']))for r in request['cases']],p.stdout
    refused=[]
    for name,edit in[
        ('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='all-pnpm-routing')),
        ('empty',lambda d:d.update(cases=[])),('bound',lambda d:d.update(cases=d['cases']*3)),
        ('namespace',lambda d:d['cases'][0].update(kind='external-program')),
        ('name',lambda d:d['cases'][0].update(name='unknown-program')),
        ('argument-bound',lambda d:d['cases'][0].update(args=['status']*4)),
        ('prefix-witness',lambda d:d['cases'][0].update(forcedBuiltin=True)),
        ('raw-request-witness',lambda d:d['cases'][0].update(rawArgs=['edit'])),
        ('root-local-witness',lambda d:d['cases'][0].update(rootBody=False)),
        ('member-fixture',lambda d:d['cases'][2].update(localBody=True,scriptLabel='tasks')),
        ('script-label',lambda d:d['cases'][0].update(scriptLabel='pm')),
        ('help-outside-parser',lambda d:d['cases'][4].update(builtinHelp=True)),
        ('tasks-operand',lambda d:d['cases'][0].update(args=['--literal'],rawArgs=['tasks','--literal'])),
        ('explicit-missing-body',lambda d:d['cases'][4].update(localBody=False,rootBody=False,scriptLabel='')),
        ('nonboolean',lambda d:d['cases'][0].update(forcedBuiltin=1))]:
        bad=copy.deepcopy(request);edit(bad);p=replay(bad)
        assert p.returncode==2 and not p.stdout,(name,p.returncode,p.stdout,p.stderr);refused.append(name)
    changed=[]
    for name,label,edit in[
        ('leading-force','root-tasks-script',lambda r:r.update(rawArgs=['pm','tasks','status'],forcedBuiltin=True)),
        ('root-shadow-basis','member-root-shadow',lambda r:r.update(rootBody=False)),
        ('empty-local-body','root-tasks-script',lambda r:r.update(localBody=False,rootBody=False,scriptLabel='')),
        ('explicit-versus-placeholder','explicit-edit',lambda r:r.update(kind='placeholder',rawArgs=['edit'])),
        ('help-dispatch','builtin-help-before-override',lambda r:r.update(builtinHelp=False,args=['status'],rawArgs=['tasks','status'])),
        ('literal-script-help','explicit-tasks',lambda r:r.update(args=['--help'],rawArgs=['run','tasks','--help'])),
        ('late-prefix-reselection','late-pm-is-script',lambda r:r.update(kind='tasks',name='tasks',rawArgs=['pm','tasks','status'],forcedBuiltin=True,scriptLabel='tasks',args=['status']))]:
        bad=copy.deepcopy(request);edit(bad['cases'][index[label]]);p=replay(bad)
        assert p.returncode==0,p.stderr;assert json.loads(p.stdout)!=measured,name;changed.append(name)
    rows=obs.read(obs.CAP/'commands.json');images=obs.read(obs.CAP/'manifest-images.json');edits=obs.read(obs.CAP/'interventions.json');setup=obs.read(obs.CAP/'setup.json')
    streams={r['label']:{n:(obs.CAP/v['path']).read_text()for n,v in r['streams'].items()}for r in rows};raw_index={r['label']:i for i,r in enumerate(rows)};raw=[]
    def changed_raw(name,edit):
        rs=copy.deepcopy(rows);ss=copy.deepcopy(streams);im=copy.deepcopy(images);edit(rs,ss,im)
        try:_,value,_,_=obs.observe(rs,im,edits,setup,ss)
        except (AssertionError,KeyError):raw.append(name);return
        assert value!=measured,name;raw.append(name)
    def replace_event(rs,ss,label,event):
        row=rs[raw_index[label]];row['events']=[event];ss[label]['stdout']=json.dumps(event)+'\n'
    def fake_script(rs,ss,label,event_label,args):
        replace_event(rs,ss,label,dict(label=event_label,args=args,cwd=rs[raw_index[label]]['cwd'],npmCommand='run-script'))
    changed_raw('hidden-child',lambda rs,ss,im:rs[raw_index['root-tasks-script']].update(events=[]))
    changed_raw('coherent-child-argv',lambda rs,ss,im:fake_script(rs,ss,'root-tasks-script','tasks',['--literal']))
    changed_raw('root-shadow-status',lambda rs,ss,im:rs[raw_index['member-root-shadow']].update(exitCode=0))
    changed_raw('placeholder-script',lambda rs,ss,im:(rs[raw_index['unsupported-edit']].update(exitCode=0),fake_script(rs,ss,'unsupported-edit','edit',[])))
    changed_raw('forced-script',lambda rs,ss,im:fake_script(rs,ss,'root-forced-tasks','tasks',['status']))
    changed_raw('late-prefix-child',lambda rs,ss,im:fake_script(rs,ss,'late-pm-is-script','tasks',['status']))
    changed_raw('help-notification',lambda rs,ss,im:ss['builtin-help-before-override'].update(stdout=''))
    changed_raw('input-preimage',lambda rs,ss,im:im['images'][0].update(text='{}\n'))
    p=replay(request);assert p.returncode==0,p.stderr
    controls=dict(schema=1,nativeCommands=21,comparedNamespaceCases=15,helpOnlyAdmissions=4,versionReads=2,purePrefixComparisons=15,leanLaws=10,bendLaws=10,decoderRefusals=refused,changedPremises=changed,changedRawObservations=raw,privateChecksExcluded=excluded,scope='Selected pnpm12.21 Mac CLI namespaces and controlled successful Node scripts. Prefix comparisons are not extra native runs. No pipeline/cache/runtime/global operations,arbitrary scripts,unknown executable fallback,or source-to-binary refinement.')
    for name,value in{'input.json':request,'measured.json':measured,'details.json':details,'basis.json':basis,'controls.json':controls}.items():
        if opts.public_only:
            old=obs.read(OUT/name)
            if name=='controls.json':old['privateChecksExcluded']=excluded
            assert old==value,name
        else:(OUT/name).write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(dict(namespaceCases=15,purePrefixComparisons=15,decoderRefusals=len(refused),changedPremises=len(changed),changedRawObservations=len(raw),publicOnly=opts.public_only,privateChecksExcluded=len(excluded))))


if __name__=='__main__':main()
