#!/usr/bin/env python3
"""One-shot continuations of the frozen isolated pending baseline."""
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
BINARY = Path('/Users/zer0cell/.local/bin/empack')
BINARY_SHA = '99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
PRODUCER = Path(__file__).read_bytes()

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def snapshot(root):
    if not root.exists():
        return None
    result = {}
    for p in sorted(root.rglob('*')):
        assert not p.is_symlink(), p
        s = p.stat()
        result[p.relative_to(root).as_posix()] = dict(kind='file' if p.is_file() else 'directory',
            mode=s.st_mode & 0o777, **(dict(bytes=s.st_size, sha256=digest(p)) if p.is_file() else {}))
    return result

class Runner:
    def __init__(self,run,phase):
        self.run, self.work, self.phase = run,run/'work',phase
        self.commands, self.processes = [],[]
        assert digest(BINARY) == BINARY_SHA
        assert json.loads((run/'baseline.json').read_text())['status'] == 'complete'
        frozen = run/'continuation-probe.py'
        if frozen.exists():
            assert frozen.read_bytes() == PRODUCER
        else:
            frozen.write_bytes(PRODUCER)
        with (run/(phase+'-started.json')).open('x') as f:
            json.dump(dict(schema=1,producerSha256=digest(frozen),startedAt=datetime.now(timezone.utc).isoformat()),f)
        self.env = dict(PATH='/usr/bin:/bin',HOME=str(self.work/'home'),TMPDIR=str(self.work/'tmp'),
            LANG='en_US.UTF-8',EMPACK_NET_TIMEOUT='1',HTTP_PROXY='http://127.0.0.1:9',
            HTTPS_PROXY='http://127.0.0.1:9',ALL_PROXY='http://127.0.0.1:9',NO_PROXY='',EMPACK_COLOR='never')
        self.write(phase+'-before.json',self.capture())

    def write(self,name,value):
        (self.run/name).write_text(json.dumps(value,indent=2)+'\n')

    def capture(self):
        return {name:snapshot(self.work/name)for name in ['project','state','cache','downloads']}

    def command(self,label,args):
        label = self.phase+'-'+label
        before = self.capture()
        argv = [str(BINARY),'--state-dir',str(self.work/'state'),'--cache-dir',str(self.work/'cache'),
            '--workdir',str(self.work/'project'),'--yes','--color','never',*args]
        start = time.monotonic()
        with (self.run/(label+'.stdout')).open('xb') as out,(self.run/(label+'.stderr')).open('xb') as err:
            child = subprocess.Popen(argv,cwd=self.work,env=self.env,stdin=subprocess.DEVNULL,
                stdout=out,stderr=err,start_new_session=True)
            self.processes.append(child)
            self.process_receipt()
            timed = False
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
        after = self.capture()
        result = dict(case=label,argv=argv,exitCode=child.returncode,timedOut=timed,ownedGroupAbsent=absent,
            seconds=time.monotonic()-start,streams={s:digest(self.run/(label+'.'+s))for s in ['stdout','stderr']},
            changedScopes=[name for name in before if before[name] != after[name]])
        self.commands.append(result)
        self.write(self.phase+'-commands.json',self.commands)
        self.write(label+'-before.json',before)
        self.write(label+'-after.json',after)
        self.process_receipt()
        assert not timed and absent,result
        return result

    def process_receipt(self):
        self.write(self.phase+'-processes.json',[dict(pid=p.pid,retired=p.poll() is not None)for p in self.processes])

    def operation(self,label):
        result = self.command(label,['pending','list','--json'])
        assert result['exitCode'] == 0,result
        assert not result['changedScopes'],result
        ops = json.loads((self.run/(result['case']+'.stdout')).read_text())['operations']
        return ops

    def close(self):
        for child in self.processes:
            if child.poll() is None:
                os.killpg(child.pid,signal.SIGKILL)
                child.wait()
        self.process_receipt()

def partial(r):
    initial = json.loads((r.run/'baseline.json').read_text())['publicOperation']
    opid = initial['id']
    keys = {i['name'].removeprefix('Fictional '):i['key']for i in initial['inputs']}
    assets = json.loads((r.run/'assets.json').read_text())
    downloads = r.work/'downloads'
    wrong = downloads/'first.zip'
    correct = downloads/'renamed-first.bin'
    wrong.write_bytes(b'X'*assets['first']['bytes'])
    correct.write_bytes(assets['first']['text'].encode())
    observed = r.operation('list')
    assert observed == [initial]
    shown = r.command('show',['pending','show',opid])
    assert shown['exitCode'] == 0 and not shown['changedScopes'],shown
    preview = r.command('preview',['--dry-run','pending','resume',opid,'--downloads-dir',str(r.work/'never-created')])
    assert preview['exitCode'] == 0 and not preview['changedScopes'],preview
    assoc = keys['first']+'='+str(correct)
    cases = [('wrong-bytes',['--file',keys['first']+'='+str(wrong)]),
             ('unknown-key',['--file','unknown='+str(correct)]),
             ('duplicate-key',['--file',assoc,'--file',assoc])]
    for label,args in cases:
        result = r.command(label,['pending','resume',opid,*args])
        assert result['exitCode'] != 0 and not result['changedScopes'],result
    result = r.command('first',['pending','resume',opid,'--file',assoc])
    assert result['exitCode'] != 0 and 'project' not in result['changedScopes'],result
    current = r.operation('retained-list')
    assert len(current) == 1
    current = current[0]
    assert current['id'] != opid
    assert any(i['supplied_candidate'] is not None for i in current['inputs'])
    old = r.command('old-id',['pending','show',opid])
    assert old['exitCode'] != 0 and not old['changedScopes'],old
    r.write('partial-result.json',dict(schema=1,status='complete',initial=initial,current=current,
        sourceFiles={p.name:dict(bytes=p.stat().st_size,sha256=digest(p))for p in [wrong,correct]},
        limits=['Regular-file/directory content/mode snapshots exclude mtime/inode and OS-shared effects.','No real provider, game, crash, concurrent writer or private content fault yet.']))

def finish(r):
    current = json.loads((r.run/'partial-result.json').read_text())['current']
    assert r.operation('initial-list') == [current]
    assets = json.loads((r.run/'assets.json').read_text())
    downloads = r.work/'downloads'
    for name in ['renamed-second-A.bin','renamed-second-B.bin']:
        (downloads/name).write_bytes(assets['second']['text'].encode())
    # The same bytes under two names are one content candidate, not ambiguity.
    result = r.command('discover',['pending','resume',current['id'],'--downloads-dir',str(downloads)])
    assert result['exitCode'] == 0,result
    assert r.operation('completed-list') == []
    import zipfile
    products = list((r.work/'project/dist').glob('*.mrpack'))
    assert len(products) == 1,products
    with zipfile.ZipFile(products[0]) as archive:
        inventory = {n:dict(bytes=len(archive.read(n)),sha256=hashlib.sha256(archive.read(n)).hexdigest())
            for n in archive.namelist()}
        for name in ['first','second']:
            assert archive.read('overrides/resourcepacks/'+name+'.zip') == assets[name]['text'].encode()
    r.write('finish-result.json',dict(schema=1,status='complete',artifact=dict(path=str(products[0].relative_to(r.work)),
        bytes=products[0].stat().st_size,sha256=digest(products[0]),members=inventory),
        limits=['Artifact byte inspection only; fictional payloads are not usable resource packs.','No browser/download-page opening, real provider, Minecraft, cache eviction or power-loss qualification.']))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=['partial','finish'])
    p.add_argument('run',type=Path)
    a = p.parse_args()
    run = a.run.resolve()
    assert run.parent == ROOT/'applications/evidence' and run.name.startswith('empack-pending-')
    r = Runner(run,a.phase)
    try:
        globals()[a.phase](r)
        print(json.dumps(dict(run=str(run.relative_to(ROOT)),phase=a.phase,status='complete',commands=len(r.commands))))
    finally:
        r.close()

if __name__ == '__main__':
    main()
