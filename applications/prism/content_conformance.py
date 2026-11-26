#!/usr/bin/env python3
"""Replay retained regular-file effects; never launches Prism or a native fixture."""
import argparse,copy,json,os,subprocess
from pathlib import Path
import content_observations as obs

ROOT=obs.ROOT;HERE=Path(__file__).resolve().parent
OUT=ROOT/'applications/evidence/prism-content-comparison'
WORK=ROOT/'.build/prism-content-replay'
POLICIES={'current':0,'guarded':1,'staged':2}
SOURCES={'regular':0,'same-path':1,'destination-alias':2,'missing':3}


def bend_request(r):
    values=[str(POLICIES[r['policy']])+'n',str(SOURCES[r['source']])+'n',str(r['destination'])+'n',str(r['sourcePayload'])+'n']
    values+=['True{}'if r[k]else'False{}'for k in ['disabledSibling','drop','extraMissing','watching','refreshResult','cancelBeforeCommit']]
    return 'L.render(L.run(L.Request{'+','.join(values)+'}))'


def rendered(o):
    return '/'.join([str(int(o[0])),','.join(str(int(v))for v in o[1]),str(o[2]),str(int(o[3])),str(int(o[4])),str(o[5])])


def main():
    args=argparse.ArgumentParser();args.add_argument('--public-only',action='store_true');opts=args.parse_args()
    request,observed,details,basis,excluded=obs.evidence(not opts.public_only)
    assert len(request['cases'])==len(observed)==22
    OUT.mkdir(exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend')
    env=dict(os.environ,LEAN_PATH=str(WORK),BEND_NO_TELEMETRY='1')
    def command(argv):
        p=subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,text=True,timeout=90)
        return p
    target=WORK/'applications/prism/ContentInstall.olean';target.parent.mkdir(parents=True,exist_ok=True)
    p=command([lean,'-DwarningAsError=true','-o',str(target),'applications/prism/ContentInstall.lean']);assert p.returncode==0,p.stdout+p.stderr
    path=WORK/'request.json'
    def replay(value):
        path.write_text(json.dumps(value)+'\n')
        return command([lean,'--run','applications/prism/ContentInstallCase.lean',str(path)])
    p=replay(request);assert p.returncode==0,p.stdout+p.stderr
    assert json.loads(p.stdout)==observed,(json.loads(p.stdout),observed)
    driver=WORK/'ContentInstallCase.bend'
    driver.write_text('import Base\nimport '+str(HERE/'ContentInstall.bend')+' as L\n\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join('('+bend_request(r)+' ++ "\\n")'for r in request['cases'])+')\n')
    p=command([bend,str(driver)]);assert p.returncode==0,p.stdout+p.stderr
    assert p.stdout.splitlines()==[rendered(o)for o in observed],p.stdout
    refused=[]
    for name,edit in [
        ('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='full-prism')),
        ('empty',lambda d:d.update(cases=[])),('bound',lambda d:d.update(cases=d['cases']*2)),
        ('policy',lambda d:d['cases'][0].update(policy='atomic')),
        ('source',lambda d:d['cases'][0].update(source='arbitrary-alias')),
        ('payload',lambda d:d['cases'][0].update(sourcePayload=3)),
        ('missing-with-bytes',lambda d:d['cases'][0].update(source='missing')),
        ('alias-with-different-bytes',lambda d:d['cases'][3].update(sourcePayload=2)),
        ('extra-without-drop',lambda d:d['cases'][0].update(extraMissing=True)),
        ('cancel-current',lambda d:d['cases'][0].update(cancelBeforeCommit=True)),
        ('candidate-refresh',lambda d:d['cases'][8].update(watching=False)),
        ('candidate-disabled',lambda d:d['cases'][8].update(disabledSibling=True)),
        ('multichunk-policy',lambda d:d['cases'][-1].update(policy='current')),
        ('nonboolean',lambda d:d['cases'][0].update(drop='yes'))]:
        bad=copy.deepcopy(request);edit(bad);p=replay(bad)
        assert p.returncode==2 and not p.stdout,(name,p.returncode,p.stdout,p.stderr);refused.append(name)
    changed=[]
    for name,index,edit in [
        ('guard-alias',3,lambda r:r.update(policy='guarded')),
        ('stage-alias',3,lambda r:r.update(policy='staged')),
        ('refresh-result',7,lambda r:r.update(refreshResult=True)),
        ('drop-handled',6,lambda r:r.update(drop=False)),
        ('cancel-before-publication',20,lambda r:r.update(cancelBeforeCommit=False))]:
        bad=copy.deepcopy(request);edit(bad['cases'][index]);p=replay(bad)
        assert p.returncode==0,p.stderr;assert json.loads(p.stdout)!=observed,name;changed.append(name)
    native=[]
    raw=[json.loads(line)for line in(obs.CURRENT/'observe.stdout').read_text().splitlines()]
    raw_request=obs.load(obs.CURRENT/'input.json');before=obs.load(obs.CURRENT/'before.json');after=obs.load(obs.CURRENT/'after.json')
    # Change measured facts, not precomputed expected outputs. A changed packet
    # must fail independent filesystem consistency or disagree with the model.
    def changed_raw(name,edit):
        rows=copy.deepcopy(raw);post=copy.deepcopy(after);edit(rows,post)
        try:
            _,value,_=obs.observe(raw_request,rows,before,post,'current')
        except (AssertionError,KeyError):
            native.append(name);return
        assert value!=observed[:8],name
        native.append(name)
    changed_raw('drop-surface',lambda rows,post:rows[6].update(returned=False))
    changed_raw('drop-child',lambda rows,post:rows[5]['installCalls'][1].update(returned=True))
    changed_raw('refresh-count',lambda rows,post:rows[7].update(updateCalls=0))
    changed_raw('copy-status',lambda rows,post:rows[0]['installCalls'][0].update(returned=False))
    changed_raw('lost-target-view',lambda rows,post:rows[3]['after'][raw_request['cases'][3]['destination']+'/item.jar'].update(exists=True))
    changed_raw('disabled-neighbor',lambda rows,post:post.pop('disabled-sibling/installed/item.jar.disabled'))
    changed_raw('unrelated-source-write',lambda rows,post:post['fresh-copy/incoming/item.jar'].update(mtimeNs=0))
    changed_raw('staging-residue',lambda rows,post:post.update({'fresh-copy/installed/unexpected.tmp':copy.deepcopy(post['fresh-copy/installed/item.jar'])}))
    def hide_alias_loss(rows,post):
        case=raw_request['cases'][3];dst=case['destination']+'/item.jar';src=case['source']
        post[obs.relative(dst,raw_request['work'])]=copy.deepcopy(before[obs.relative(dst,raw_request['work'])])
        post[obs.relative(src,raw_request['work'])]['targetExists']=True
        rows[3]['after'][dst]=copy.deepcopy(rows[3]['before'][dst])
        rows[3]['after'][src]=copy.deepcopy(rows[3]['before'][src])
    changed_raw('coherent-hidden-alias-loss',hide_alias_loss)
    assert len(native)==9
    replay(request)
    artifacts={'input.json':request,'measured.json':observed,'details.json':details,'basis.json':basis}
    controls=dict(schema=1,nativeOriginalCases=8,nativeCandidateCases=13,nativeMultichunkContinuation=1,comparedOutcomes=22,
        leanLaws=14,bendLaws=13,decoderRefusals=refused,changedPremises=changed,changedRawObservations=native,
        privateChecksExcluded=excluded,scope='Selected regular-file methods and private candidates;not full launcher,GUI,game,crash,durability,arbitrary aliases,or concurrent writers.')
    artifacts['controls.json']=controls
    for name,value in artifacts.items():
        # Public mode reproduces the same four fact/basis artifacts. Its explicit
        # private-check exclusions are reported separately, not hidden in success.
        if opts.public_only:
            expected=obs.load(OUT/name)
            if name=='controls.json':expected['privateChecksExcluded']=excluded
            assert expected==value,name
        else:(OUT/name).write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(dict(compared=22,decoderRefusals=len(refused),changedPremises=len(changed),changedRawObservations=len(native),publicOnly=opts.public_only,privateChecksExcluded=len(excluded))))


if __name__=='__main__':main()
