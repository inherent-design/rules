"""Pure owner-run SBOM comparison over retained sources and observations."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import observations as obs

ROOT,HERE=obs.ROOT,Path(__file__).resolve().parent
write=lambda p,v:p.write_text(json.dumps(v,indent=2)+'\n')
sha=obs.sha


def request(operation,format='cyclonedx',lockOnly=False,runtimeOnly=False):
    return dict(operation=operation,format=format,lockOnly=lockOnly,runtimeOnly=runtimeOnly)


def report_text(doc,manager):
    if doc.get('bomFormat')=='CycloneDX':
        root=doc['metadata']['component'];identity=root['purl'];assert identity.startswith('pkg:npm/')and identity.endswith('@1.0.0')
        name=identity.removeprefix('pkg:npm/').removesuffix('@1.0.0');version=doc['specVersion'];phase=doc['metadata']['lifecycles'][0]['phase'];components=doc['components']
        def row(c):
            hashes=c.get('hashes')if manager=='npm'else next(r['hashes']for r in c['externalReferences']if r['type']=='distribution')
            assert len(hashes)==1 and hashes[0]['alg']=='SHA-512'
            dev=any(p==dict(name='cdx:npm:package:development',value='true')for p in c.get('properties',[]))
            license=c.get('licenses',[]);assert license in [[],[dict(license=dict(id='MIT'))]]
            return[c['name'],hashes[0]['content'],c.get('scope','-'),'dev'if dev else'-','MIT'if license else'-']
    else:
        name=doc['name'].removesuffix('@1.0.0');root=next(c for c in doc['packages']if c['name']==name);version=doc['spdxVersion'];phase='-'
        components=[c for c in doc['packages']if c is not root]
        def row(c):
            assert c['filesAnalyzed']is False;checksums=c['checksums'];assert len(checksums)==1 and checksums[0]['algorithm']=='SHA512'
            rels=[r for r in doc['relationships']if (r['spdxElementId'],r['relatedSpdxElement'])==((c['SPDXID'],root['SPDXID'])if manager=='npm'else(root['SPDXID'],c['SPDXID']))]
            assert len(rels)==1;license=c['licenseDeclared'];assert license in ['MIT','NOASSERTION']
            return[c['name'],checksums[0]['checksumValue'],rels[0]['relationshipType'],'-','MIT'if license=='MIT'else'-']
    rows=sorted([row(c)for c in components]);assert len({r[0]for r in rows})==len(rows)
    return'|'.join([root['name'],name,version,phase,';'.join(','.join(r)for r in rows)])


def build(observed):
    commands=obs.read(obs.RUN/'commands.json');mutations=obs.read(obs.RUN/'mutations.json')
    archives={r['name']:r for r in obs.read(obs.RUN/'archives.json')};rows,bindings=[],[]
    for manager in ['npm','pnpm']:
        cs=[c for c in commands if c['manager']==manager];ms=[m for m in mutations if m['manager']==manager]
        requests,facts=[],[];previous=None;cursor=0
        for c in cs:
            if previous is not None:
                while previous!=c['before']:
                    m=ms[cursor];cursor+=1;assert m['before']==previous
                    action={'replace-prod-code':'replace-code','hold-prod-entry':'hold-entry','restore-prod-entry':'restore-entry','hold-lock':'hold-lock'}[m['action']]
                    requests.append(request(action));facts.append(dict(id=m['id'],kind='authored',expected='0/-/-'));previous=m['after']
            args=c['argv'][1:]
            if c['query']:
                r=request('query');value=next(v['observed'][obs.PROD]for v in observed['runtime']if v['id']==c['id'])
                query='missing'if'error'in value else value['value']['value'];expected='0/'+query+'/-';kind='runtime'
            elif args==['install','--offline','--ignore-scripts']:
                r=request('install');expected='0/-/-';kind='qualified-seed'
            else:
                assert args[0]=='sbom';kind='report'
                options=args[1:];fmt=[x.split('=',1)[1]for x in options if x.startswith('--sbom-format=')];assert len(fmt)<=1
                flags=[x for x in options if not x.startswith('--sbom-format=')]
                assert flags in [[],['--package-lock-only']if manager=='npm'else['--lockfile-only'],['--omit=dev','--omit=optional']if manager=='npm'else['--prod','--no-optional']]
                r=request('report',fmt[0]if fmt else'missing',lockOnly=any('lock' in f for f in flags),runtimeOnly=any(f in ['--prod','--omit=dev']for f in flags))
                document=report_text(obs.read(obs.RUN/(c['id']+'.stdout')),manager)if c['exitCode']==0 else'-'
                expected=str(c['exitCode'])+'/-/'+document
            requests.append(r);facts.append(dict(id=c['id'],kind=kind,expected=expected));previous=c['after']
        assert cursor==len(ms)
        declaration=json.loads(obs.body(cs[0]['before'],'package.json'))
        rows.append(dict(profile=manager,declaredName=declaration['name'],directoryName='project',
                         prodDigest=archives[obs.PROD]['sha512'],devDigest=archives[obs.DEV]['sha512'],optionalDigest=archives[obs.OPTIONAL]['sha512'],requests=requests))
        bindings.append(dict(manager=manager,facts=facts))
    return dict(schema=1,profile='three-direct-local-archives',rows=rows),bindings


def blist(values,encode):
    result='Nil{}'
    for item in reversed(values):result='Con{'+encode(item)+','+result+'}'
    return result
def bend_call(r):
    q=json.dumps;b=lambda v:'True{}'if v else'False{}'
    actions={'install':'Install','query':'Query','report':'Report','replace-code':'ReplaceCode','hold-entry':'HoldEntry','restore-entry':'RestoreEntry','hold-lock':'HoldLock'}
    formats={'cyclonedx':'CycloneDx','spdx':'Spdx','missing':'Missing'}
    request=lambda s:'S.Request{'+','.join(['S.'+actions[s['operation']]+'{}','S.'+formats[s['format']]+'{}',b(s['lockOnly']),b(s['runtimeOnly'])])+'}'
    context='S.ModelContext{'+','.join(['S.'+{'npm':'Npm','pnpm':'Pnpm'}[r['profile']]+'{}',*[q(r[k])for k in ['declaredName','directoryName','prodDigest','devDigest','optionalDigest']]])+'}'
    return'S.lines(S.trace('+blist(r['requests'],request)+','+context+',S.Snapshot{False{},False{},False{},False{}}))'


def raw_controls():
    original=obs.read;rejected=[]
    for name,file,change in [
        ('stream-hash','commands.json',lambda v:v[0].update(stdoutSha256='0'*64)),
        ('captured-length','commands.json',lambda v:next(e for e in v[0]['after'].values()if e['kind']=='file').update(bytes=-1)),
        ('runtime-backing','npm-changed-runtime.stdout',lambda v:v[obs.PROD]['value'].update(value='original')),
        ('archive-assertion','npm-changed-cyclonedx.stdout',lambda v:next(c for c in v['components']if c['name']==obs.PROD)['hashes'][0].update(content='0'*128)),
        ('dangling-reference','npm-baseline-cyclonedx.stdout',lambda v:v['dependencies'][0]['dependsOn'].append('missing-component')),
        ('files-analyzed','npm-baseline-spdx.stdout',lambda v:v['packages'][0].update(filesAnalyzed=True)),
        ('ordered-author-actions','mutations.json',lambda v:v.reverse())]:
        def patched(path):
            value=original(path)
            if path==obs.RUN/file:change(value)
            return value
        obs.read=patched
        try:
            try:obs.inspect()
            except (AssertionError,KeyError,ValueError,IndexError,StopIteration):rejected.append(name)
            else:raise RuntimeError(('Raw control escaped',name))
        finally:obs.read=original
    return rejected


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--private',action='store_true');args=parser.parse_args()
    observed=obs.inspect();data,bindings=build(observed);expected=[[f['expected']for f in b['facts']]for b in bindings]
    out=ROOT/'.build/js-sbom-review';out.mkdir(exist_ok=True);formal=ROOT/'.build/js-sbom-formal';target=formal/'applications/js-sbom/Sbom.olean';target.parent.mkdir(exist_ok=True,parents=True)
    lean=os.environ.get('LEAN','lean');bend=os.environ.get('BEND','bend');env=dict(os.environ,LEAN_PATH=str(formal),BEND_NO_TELEMETRY='1')
    def run(argv):return subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,text=True,timeout=120)
    result=run([lean,'-DwarningAsError=true','-o',str(target),'applications/js-sbom/Sbom.lean']);assert result.returncode==0,result.stdout+result.stderr
    path=out/'input.json'
    def replay(value):write(path,value);return run([lean,'--run','applications/js-sbom/SbomCase.lean',str(path)])
    result=replay(data);assert result.returncode==0,result.stdout+result.stderr
    actual=json.loads(result.stdout);assert actual==expected,[(b['facts'][i]['id'],a,e)for row,wanted,b in zip(actual,expected,bindings)for i,(a,e)in enumerate(zip(row,wanted))if a!=e]
    driver=out/'SbomNative.bend';driver.write_text('import Base\nimport ../../applications/js-sbom/Sbom.bend as S\ndef main() -> IO(Unit):\n  IO.write('+' ++ '.join(bend_call(r)for r in data['rows'])+')\n')
    result=run([bend,str(driver)]);assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.splitlines()==[s for row in expected for s in row]
    refusals=[]
    for name,change in [
        ('schema',lambda d:d.update(schema=2)),('profile',lambda d:d.update(profile='all-SBOMs')),
        ('application',lambda d:d['rows'][0].update(profile='yarn')),('package-name',lambda d:d['rows'][0].update(declaredName='../x')),
        ('digest',lambda d:d['rows'][0].update(prodDigest='not-a-hash')),('count',lambda d:d['rows'][0].update(requests=[])),
        ('operation',lambda d:d['rows'][0]['requests'][0].update(operation='verify')),
        ('format',lambda d:d['rows'][0]['requests'][2].update(format='csv')),
        ('report-only-options',lambda d:d['rows'][0]['requests'][1].update(lockOnly=True)),
        ('seed-first',lambda d:d['rows'][0]['requests'][0].update(operation='query')),
        ('authored-precondition',lambda d:next(r for r in d['rows'][0]['requests']if r['operation']=='replace-code').update(operation='restore-entry')),
        ('unsupported-lock-format',lambda d:d['rows'][0]['requests'][3].update(lockOnly=True))]:
        bad=copy.deepcopy(data);change(bad);result=replay(bad);assert result.returncode==2 and not result.stdout,(name,result.stdout,result.stderr);refusals.append(name)
    premises=[]
    for name,target_id,change in [
        ('application-policy','npm-baseline-cyclonedx',lambda d:d['rows'][0].update(profile='pnpm')),
        ('runtime-scope','npm-runtime-filter',lambda d:next(r for r in d['rows'][0]['requests']if r['runtimeOnly']).update(runtimeOnly=False)),
        ('lock-only-basis','npm-missing-lock-only',lambda d:next(r for r in d['rows'][0]['requests']if r['lockOnly']).update(lockOnly=False)),
        ('actual-code-change','npm-changed-runtime',lambda d:next(r for r in d['rows'][0]['requests']if r['operation']=='replace-code').update(operation='query')),
        ('source-location','npm-no-lock-cyclonedx',lambda d:next(r for r in d['rows'][0]['requests']if r['operation']=='hold-lock').update(operation='query')),
        ('physical-name','npm-baseline-cyclonedx',lambda d:d['rows'][0].update(directoryName='another-place')),
        ('artifact-identity','npm-baseline-cyclonedx',lambda d:d['rows'][0].update(prodDigest='0'*128))]:
        bad=copy.deepcopy(data);change(bad);result=replay(bad);assert result.returncode==0,result.stdout+result.stderr
        changed_result=json.loads(result.stdout)
        j,i=next((j,i)for j,b in enumerate(bindings)for i,f in enumerate(b['facts'])if f['id']==target_id)
        assert changed_result[j][i]!=actual[j][i],name;premises.append(dict(name=name,observedAt=target_id))
    changed=[]
    for name,id,value in [('missing-entry','npm-missing-cyclonedx','0/-/-'),('runtime-code','npm-changed-runtime','0/original/-'),('root-identity','npm-baseline-cyclonedx','0/-/wrong-root'),('lock-requirement','pnpm-no-lock-cyclonedx','0/-/-')]:
        bad=copy.deepcopy(expected)
        for j,b in enumerate(bindings):
            for i,f in enumerate(b['facts']):
                if f['id']==id:bad[j][i]=value
        assert bad!=actual,name;changed.append(name)
    raw=raw_controls();checked,excluded=[],[]
    for row in obs.read(ROOT/'applications/sources/js-sbom-selections.json')['sources']:
        if not args.private:excluded.append(row['cache']);continue
        p=ROOT/row['cache'];body=p.read_bytes();assert hashlib.sha256(body).hexdigest()==row['sha256']
        assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==row['gitBlob'];checked.append(row['cache'])
    paths=[HERE/n for n in ['Sbom.lean','Sbom.bend','SbomCase.lean','conformance.py','observations.py','probe.py']]+[ROOT/'applications/sources/js-sbom-selections.json']
    basis={**observed['basisSha256'],**{str(p.relative_to(ROOT)):sha(p)for p in paths}};assert all(sha(ROOT/p)==s for p,s in basis.items())
    record=dict(schema=1,sourceScope='Three direct local archives,no scripts/peers/workspaces;successful installation seed is admitted,not an installer proof.',nativeCommands=26,qualifiedSeedEvents=2,runtimeComparisons=6,sbomRequests=18,documents=11,authoredEvents=8,bothModelsMatch=True,input=data,bindings=bindings,results=actual,researchRefusals=refusals,premiseControls=premises,changedObservationControls=changed,rawObservationControls=raw,sourceAvailability=dict(checked=checked,excluded=excluded),basisSha256=basis,driverSha256=sha(driver),tools={k:dict(path=str(Path(p).resolve()),sha256=sha(Path(p)))for k,p in [('lean',lean),('bend',bend)]},limits=['No application/Node/installer or fixture rerun.','Current artifact fields and observed code are distinct. Verification-scope law is model-defined,no native verification receipt asserted.','Graph/metadata basis rules are source-derived;not extra native JSON provenance fields.','No complete SBOM schema/graph verifier,other sources/hosts,concurrency or production correction.'])
    write(out/'comparison.json',record)
    print(json.dumps({k:record[k]for k in ['qualifiedSeedEvents','runtimeComparisons','sbomRequests','documents','authoredEvents','researchRefusals','premiseControls','changedObservationControls','rawObservationControls']}))


if __name__=='__main__':main()
