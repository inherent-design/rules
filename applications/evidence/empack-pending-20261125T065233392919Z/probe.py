#!/usr/bin/env python3
"""Isolated installed-CLI pending flow with fictional, exact restricted inputs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
REVISION = '0b4462e3032b4f09230b15329722eabefb7f574c'
BINARY = Path('/Users/zer0cell/.local/bin/empack')
BINARY_SHA = '99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
PRODUCER = Path(__file__).read_bytes()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def fingerprint(value):
    """Independent authored-wire fixture adapter for the inspected codec hash.

    Native decoding/checking must admit the resulting documents before any
    workflow evidence is collected. This is not a production encoder port.
    """
    h = hashlib.sha256()

    def blob(b):
        h.update(len(b).to_bytes(8,'big'))
        h.update(b)

    def walk(v):
        if v is None:
            h.update(b'\0')
        elif isinstance(v,bool):
            h.update(bytes([1,int(v)]))
        elif isinstance(v,int):
            h.update(b'\2')
            blob(str(v).encode())
        elif isinstance(v,str):
            h.update(b'\3')
            blob(v.encode())
        elif isinstance(v,list):
            h.update(b'\4')
            h.update(len(v).to_bytes(8,'big'))
            for item in v:
                walk(item)
        elif isinstance(v,dict):
            h.update(b'\5')
            h.update(len(v).to_bytes(8,'big'))
            for key in sorted(v):
                blob(key.encode())
                walk(v[key])
        else:
            raise TypeError(type(v))
    blob(b'empack.intent.v2')
    walk(value)
    return h.hexdigest()


def fixture(project):
    env = dict(client='required',server='required')
    pack = dict(id='rules.pending.fixture',name='Rules pending fixture',version='one',authors=[])
    runtime = dict(minecraft='1.21.1',loader='vanilla',java=dict(preferred=21))
    author = dict(schema=6,pack=pack,runtime=runtime,dependencies={})
    canonical = {'schema':6,'dependency-policy':'prefer-stable','pack':dict(pack,description=None),
        'runtime':{'minecraft':'1.21.1','acceptable-versions':[],'loader':{'kind':'vanilla','version':None},'java':{'preferred':21}},
        'dependencies':{},'sources':{'exclude':[]},'layout':{},'installation-policies':{},
        'distribution':{'profiles':{},'defaults':[]},'extensions':{}}
    lock = {'schema':3,'intent-revision':'','resolver':'rules-fictional-pending-fixture',
        'java-policy':{'historical-minimum':21,'id':'empack-java-1','metadata-revision':'b8e2a3e1ba241414f8b861f13c9a6fd6bc5d922d',
                       'recommended':21,'required-minimum':21,'supported':[21]},
        'runtime':{'minecraft':'1.21.1','loader':'vanilla','loader-version':None},
        'acceptable-versions':[],'dependencies':{},'coverage':{},'required-edges':{}}
    assets = {}
    for index,name in enumerate(['first','second']):
        payload = ('payload-' + name).encode()
        assets[name] = payload
        digest = hashlib.sha256(payload).hexdigest()
        provider = dict(provider='curseforge',project=str(123+index))
        selection = dict(provider='curseforge',id=str(456+index))
        pin = dict(project=provider,selection=selection)
        placement = dict(destination='resourcepacks/' + name + '.zip',layer='common',environment=env)
        author['dependencies'][name] = dict(source=dict(kind='provider',identity=provider),pin=str(456+index),
                                            type='resource-pack',placement=[placement])
        canonical['dependencies'][name] = dict(releases=None,source=dict(kind='provider',identity=provider),
            content='resource-pack',selection={'mode':'provider-pin','pin':selection},placement=[placement],environment=env)
        digests = dict(sha256=digest)
        lock['dependencies'][name] = {'incompatibilities':[],'source-selector':None,'title':'Fictional '+name,
            'content':'resource-pack','identity':{'kind':'provider','project':provider},'selection':pin,
            'files':[{'slot':'primary','acquisition':{'kind':'manual','pin':pin,'instructions':'Supply exact fictional fixture bytes'},
                      'expected':{'digests':digests,'size':len(payload),'accepted-observation':None},
                      'provenance':{'source':'rules fictional fixture','location':None,'declared-digests':digests,'conversions':[]},
                      'placements':[placement]}]}
        lock['coverage'][name] = 'complete'
        lock['required-edges'][name] = []
    lock['intent-revision'] = fingerprint(canonical)
    for name,value in [('empack.yml',author),('empack.lock',lock)]:
        (project/name).write_text(json.dumps(value,indent=2)+'\n')
    return canonical,assets


def snapshot(root):
    result = {}
    if not root.exists():
        return result
    for p in sorted(root.rglob('*')):
        assert not p.is_symlink(),p
        if p.is_file():
            result[p.relative_to(root).as_posix()] = dict(bytes=p.stat().st_size,sha256=sha(p),mode=p.stat().st_mode&0o777)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','baseline'])
    parser.add_argument('run',nargs='?',type=Path)
    args = parser.parse_args()
    assert sha(BINARY) == BINARY_SHA
    if args.action == 'prepare':
        run = ROOT/'applications/evidence'/('empack-pending-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        work = run/'work'
        for name in ['project','home','tmp','downloads']:
            (work/name).mkdir(parents=True)
        canonical,assets = fixture(work/'project')
        (run/'probe.py').write_bytes(PRODUCER)
        for name in ['empack.yml','empack.lock']:
            (run/('initial-'+name)).write_bytes((work/'project'/name).read_bytes())
        (run/'canonical-intent.json').write_text(json.dumps(canonical,indent=2)+'\n')
        (run/'assets.json').write_text(json.dumps({name:dict(text=b.decode(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())for name,b in assets.items()},indent=2)+'\n')
        (run/'setup.json').write_text(json.dumps(dict(schema=1,binary=str(BINARY),binarySha256=BINARY_SHA,
            sourceRevision=REVISION,scope='Fictional component input, not provider resolution, real resource-pack payload, or source/runtime equivalence.'),indent=2)+'\n')
        print(json.dumps(dict(run=str(run.relative_to(ROOT)),intentRevision=fingerprint(canonical))))
        return
    assert args.run
    run = args.run.resolve()
    assert run.parent == ROOT/'applications/evidence' and run.name.startswith('empack-pending-')
    work,project = run/'work',run/'work/project'
    assert not (run/'baseline-started.json').exists(),'Inspect a previous baseline attempt; never silently restart it.'
    assert sha(run/'probe.py') == hashlib.sha256(PRODUCER).hexdigest()
    (run/'baseline-started.json').write_text(json.dumps(dict(schema=1,producerSha256=sha(run/'probe.py')))+'\n')
    env = dict(PATH='/usr/bin:/bin',HOME=str(work/'home'),TMPDIR=str(work/'tmp'),LANG='en_US.UTF-8',
        EMPACK_NET_TIMEOUT='1',HTTP_PROXY='http://127.0.0.1:9',HTTPS_PROXY='http://127.0.0.1:9',
        ALL_PROXY='http://127.0.0.1:9',NO_PROXY='',EMPACK_COLOR='never')
    commands,processes = [],[]
    before = {name:snapshot(work/name)for name in ['project','state','cache']}
    (run/'before.json').write_text(json.dumps(before,indent=2)+'\n')

    def command(label,args):
        argv = [str(BINARY),'--state-dir',str(work/'state'),'--cache-dir',str(work/'cache'),
                '--workdir',str(project),'--yes','--color','never',*args]
        with (run/(label+'.stdout')).open('xb') as out,(run/(label+'.stderr')).open('xb') as err:
            child = subprocess.Popen(argv,cwd=work,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
            processes.append(child)
            (run/'owned-processes.json').write_text(json.dumps([dict(pid=p.pid,retired=p.poll() is not None)for p in processes],indent=2)+'\n')
            timed = False
            start = time.monotonic()
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                timed = True
                os.killpg(child.pid,signal.SIGKILL)
                child.wait()
        try:
            os.killpg(child.pid,0)
        except ProcessLookupError:
            absent = True
        else:
            absent = False
        result = dict(case=label,argv=argv,exitCode=child.returncode,timedOut=timed,ownedGroupAbsent=absent,
            seconds=time.monotonic()-start,streams={s:sha(run/(label+'.'+s))for s in ['stdout','stderr']})
        commands.append(result)
        (run/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        (run/(label+'-after.json')).write_text(json.dumps({name:snapshot(work/name)for name in ['project','state','cache']},indent=2)+'\n')
        assert not timed and absent,(label,result)
        return result
    try:
        checked = command('check',['check','--json'])
        assert checked['exitCode'] == 0,'Authored-wire fixture must be admitted before exercising pending behavior.'
        preview = command('preview',['--dry-run','build','--ad-hoc','modrinth'])
        assert preview['exitCode'] == 0
        assert snapshot(project) == before['project'] and not (work/'state').exists()
        build = command('build',['build','--ad-hoc','modrinth'])
        assert build['exitCode'] != 0
        assert snapshot(project) == before['project']
        report = command('pending',['pending','list','--json'])
        assert report['exitCode'] == 0
        pending = json.loads((run/'pending.stdout').read_text())
        assert len(pending['operations']) == 1 and pending['operations'][0]['kind'] == 'build'
        assert len(pending['operations'][0]['inputs']) == 2
        (run/'baseline.json').write_text(json.dumps(dict(schema=1,status='complete',commands=len(commands),
            publicOperation=pending['operations'][0],limits=['Native documents/build preview/suspension/inspection only;continuation,content verification,scan,stale state and discard remain pending.']),indent=2)+'\n')
        print(json.dumps(dict(run=str(run.relative_to(ROOT)),baseline='complete',commands=len(commands))))
    finally:
        for child in processes:
            if child.poll() is None:
                os.killpg(child.pid,signal.SIGKILL)
                child.wait()
        (run/'owned-processes.json').write_text(json.dumps([dict(pid=p.pid,retired=p.poll() is not None)for p in processes],indent=2)+'\n')


if __name__ == '__main__':
    main()
