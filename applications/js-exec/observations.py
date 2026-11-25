#!/usr/bin/env python3
"""Read generated execution evidence; no package-manager or fixture execution."""
import hashlib,json,tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'applications/evidence/js-exec-20261125T011635281573Z'
NAME='rules-exec-probe'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def inspect():
    receipt=json.loads((RUN/'receipt.json').read_text());commands=json.loads((RUN/'commands.json').read_text())
    assert receipt['producerSha256']==sha(RUN/'probe.py')and len(commands)==receipt['commands']==27
    assert receipt['allOwnedGroupsAbsent']and all(p['retired']for p in json.loads((RUN/'owned-processes.json').read_text()))
    for pin in receipt['tools'].values():assert sha(Path(pin['path']))==pin['sha256']
    ledger=json.loads((ROOT/'applications/sources/js-exec-selections.json').read_text())
    for pin in ledger['sources']:
        p=ROOT/pin['cache'];assert sha(p)==pin['sha256']and p.stat().st_size==pin['bytes']
        if 'installedPath'in pin:assert sha(Path(pin['installedPath']))==pin['sha256']
    archive=RUN/'fixture-executable-1.0.0.tgz';assert sha(archive)==receipt['archiveSha256']and archive.stat().st_size<65536
    with tarfile.open(archive,'r:gz')as tar:
        members=tar.getmembers();assert [m.name for m in members]==['package/package.json','package/bin.cjs']
        assert all(m.isfile()and m.size<16384 for m in members)and members[1].mode==0o755
        package=json.loads(tar.extractfile(members[0]).read());body=tar.extractfile(members[1]).read()
    assert package==dict(name='fixture-executable',version='1.0.0',bin={NAME:'bin.cjs'})
    assert body.startswith(b'#!/usr/bin/env node\n')and b'FIXTURE_EFFECT_FILE'in body and b'"dependency"'in body
    readback=json.loads((RUN/'project-inputs.json').read_text());inputs={(p['app'],p['profile']):p for p in readback['projects']}
    assert len(inputs)==9 and set(inputs)=={(a,p)for a in ['npm','pnpm','yarn']for p in ['dependency-and-path','path-only','missing']}
    events=[];prior={};warnings=[]
    for c in commands:
        key=c['app'],c['profile'];p=inputs[key];before,after=c['before'],c['after']
        assert c['outcome']['ownedGroupAbsent']and not c['outcome']['timedOut']
        for s in c['streams'].values():assert sha(RUN/s['file'])==s['sha256']
        expected_auth={n:f['sha256']for n,f in p['files'].items()}
        assert before['authored']==after['authored']==expected_auth
        for f in p['files'].values():assert hashlib.sha256(f['text'].encode()).hexdigest()==f['sha256']
        manifest=json.loads(p['files']['package.json']['text']);assert manifest['scripts']=={NAME:'node script.cjs'}
        assert bool(manifest.get('dependencies'))==(c['profile']=='dependency-and-path')
        if key in prior:assert before==prior[key]
        else:assert c['operation']=='install'and before['lock']is None and before['effects']==[]
        prior[key]=after
        assert after['lock']is not None
        if c['operation']=='install':assert c['outcome']['exitCode']==0
        else:assert before['lock']==after['lock']
        assert after['effects'][:len(before['effects'])]==before['effects']
        new=after['effects'][len(before['effects']):]
        assert len(new)<=1
        for event in new:
            assert set(event)=={'kind','args','cwd'}and event['args']==receipt['arguments']and event['cwd']==c['cwd']
            assert event['kind']in ['dependency','inherited-path','root-script']
            # Independent executable stdout agrees with the separately written
            # effect record; banners are permitted around that one JSON line.
            text=(RUN/c['streams']['stdout']['file']).read_text()
            printed=[json.loads(line)for line in text.splitlines()if line.startswith('{')]
            assert printed==[event];events.append(event)
        if new:assert c['outcome']['exitCode']==0
        if c['operation']=='nested-exec':assert Path(c['cwd']).name=='nested'
        else:assert Path(c['cwd']).name=='project'
        err=(RUN/c['streams']['stderr']['file']).read_text()
        if 'managePackageManagerVersions'in err:warnings.append('/'.join([*key,c['operation']]))
        if c['app']=='npm'and c['operation']=='exec'and c['outcome']['exitCode']!=0:assert 'ENOTCACHED'in err and '/'+NAME in err
        if c['app']=='npm'and c['operation']=='explicit-shell-call'and c['outcome']['exitCode']!=0:assert NAME in err and 'not found'in err
        if c['app']=='pnpm'and c['profile']=='missing'and c['operation']=='exec':assert 'Command "'+NAME+'" not found'in err
        if c['app']=='yarn'and c['profile']=='missing'and c['operation']=='exec':assert 'command not found: '+NAME in err
    assert len(events)==13 and warnings
    for (app,profile),p in inputs.items():
        if profile=='dependency-and-path':assert p['installedProgramSha256']==hashlib.sha256(body).hexdigest()
        assert 'managePackageManagerVersions: false'in p['files']['pnpm-workspace.yaml']['text']
    return receipt,commands,warnings


if __name__=='__main__':
    receipt,commands,warnings=inspect();print(json.dumps(dict(commands=len(commands),exactArgvCwdEvents=13,ignoredSettingWarnings=len(warnings))))
