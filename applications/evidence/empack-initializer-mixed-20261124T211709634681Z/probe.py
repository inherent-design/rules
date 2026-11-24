#!/usr/bin/env python3
"""Owner-run mixed initializer schedules using the two retained private binaries."""
import hashlib
import json
import os
from pathlib import Path
import platform
import selectors
import signal
import subprocess
from datetime import datetime, timezone

from initializer_probe import retire_owned
from root_state_observations import image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = Path(__file__).read_bytes()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert platform.system() == 'Darwin'
    prior = ROOT / 'applications/evidence/empack-initializer-20261124T205241728563Z'
    basis = json.loads((prior / 'receipt.json').read_text())
    binaries = {v: ROOT / info['path'] for v, info in basis['binaries'].items()}
    for v, p in binaries.items(): assert sha(p) == basis['binaries'][v]['sha256']
    run = ROOT / 'applications/evidence' / ('empack-initializer-mixed-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    work = run / 'work'
    for name in ['home', 'tmp', 'fixtures']: (work / name).mkdir(parents=True)
    (run / 'images').mkdir(); (run / 'probe.py').write_bytes(PRODUCER)
    env = dict(PATH='/usr/bin:/bin', HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'), LANG='en_US.UTF-8')
    receipt = dict(schema=1, sourceRevision=basis['sourceRevision'], priorReceipt=str((prior / 'receipt.json').relative_to(ROOT)),
        priorReceiptSha256=sha(prior / 'receipt.json'), binaries=basis['binaries'], producerSha256=sha(run / 'probe.py'),
        retireHelperSha256=hashlib.sha256(__import__('inspect').getsource(retire_owned).encode()).hexdigest(), platform=platform.platform(),
        limits=['Existing private copied current/candidate initializer binaries;no source compilation or production edits.',
            'Controlled post-lock schedules on fresh owned roots using private stdin readiness;not complete Engine/CLI or project publication.',
            'Same physical root and association schema;does not qualify all protocol-version,platform,rename/fsync or power-loss behavior.'])
    commands, scenarios, active, prefixes = [], [], {}, {}
    def save():
        receipt.update(commands=commands, scenarios=scenarios)
        (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    def abort():
        captured = []
        for label, p in list(active.items()):
            try: streams = retire_owned(p)
            except Exception as e: captured.append((label,None,str(e).encode())); continue
            if streams is not None: captured.append((label,prefixes.get(label,b'') + streams[0],streams[1]))
        # All possible retirements precede writes,including a full-storage error.
        for label, out, err in captured:
            if out is not None: (run / (label + '-aborted.stdout')).write_bytes(out)
            (run / (label + '-aborted.stderr')).write_bytes(err)
    def snap(s, label, base):
        p = run / 'images' / (label + '.json'); p.write_text(json.dumps(image(base), sort_keys=True, separators=(',', ':')))
        ref = dict(label=label,image=str(p.relative_to(run)),sha256=sha(p));s['views'].append(ref);save();return ref
    def fixture(name):
        p = work / 'fixtures' / name; (p / 'project').mkdir(parents=True, mode=0o700); (p / 'host').mkdir(mode=0o700)
        (p / 'project/document.txt').write_bytes(b'unchanged author input')
        s = dict(id=name,fixture=str(p.relative_to(work)),events=[],views=[]);scenarios.append(s);snap(s,name+'-initial',p);return s,p
    def launch(s,label,variant,base,point='',action='initialize'):
        argv = [str(binaries[variant]),str(base),action,point]
        p = subprocess.Popen(argv,cwd=work,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        active[label] = p;prefixes[label] = b''
        s['events'].append(dict(event='started',label=label,variant=variant,pid=p.pid,action=action,point=point));save()
        if point:
            sel = selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ)
            ready = sel.select(timeout=10);sel.close()
            assert ready,'No owned readiness event: '+label
            line=p.stdout.readline();prefixes[label]=line;event=json.loads(line)
            assert event==dict(event='phase',phase=point,pid=p.pid) and p.poll() is None,(label,event)
            s['events'].append(dict(event='phase',label=label,phase=point,pid=p.pid));save()
        return p
    def finish(s,label,kill=False,resume=False):
        p=active[label]
        if kill: os.killpg(p.pid,signal.SIGKILL)
        elif resume: p.stdin.write(b'C');p.stdin.flush()
        try: out,err=p.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            retire_owned(p);raise
        active.pop(label);out=prefixes[label]+out
        for stream,raw in [('stdout',out),('stderr',err)]: (run/(label+'.'+stream)).write_bytes(raw)
        try:os.killpg(p.pid,0)
        except ProcessLookupError:absent=True
        else:absent=False
        row=dict(label=label,pid=p.pid,argv=p.args,exitCode=p.returncode,intentionalKill=kill,ownedGroupAbsent=absent,
            stdoutSha256=sha(run/(label+'.stdout')),stderrSha256=sha(run/(label+'.stderr')))
        commands.append(row);save();assert absent and p.returncode==(-9 if kill else 0),label
        rows=[json.loads(l) for l in out.splitlines()]
        result=next((r['outcome'] for r in rows if r['event']=='result'),None)
        s['events'].append(dict(event='finished',label=label,pid=p.pid,exitCode=p.returncode,outcome=result));save();return result
    def call(s,label,variant,base,action='initialize'):
        launch(s,label,variant,base,action=action);return finish(s,label)
    def held_pair(s,base,label):
        state=next((base/'host').glob('project-*'));import fcntl
        held=[]
        for name in ['state.lock','operation.lock']:
            with (state/name).open('r+b') as f:
                try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:held.append(name)
                else:fcntl.flock(f,fcntl.LOCK_UN)
        assert held==['state.lock','operation.lock']
        s['events'].append(dict(event='kernel-locks-held',label=label,names=held));save()
    save()
    try:
        s,p=fixture('candidate-first-current-completes')
        launch(s,'one-candidate','candidate',p,'locked');snap(s,'one-candidate-paused',p)
        old=call(s,'one-current','current',p);snap(s,'one-current-returned',p)
        new=finish(s,'one-candidate',resume=True);snap(s,'one-candidate-returned',p)
        s['results']=dict(current=old,candidate=new);save()

        s,p=fixture('current-dies-candidate-completes')
        launch(s,'two-candidate','candidate',p,'locked');launch(s,'two-current','current',p,'locked');held_pair(s,p,'two-both-held');snap(s,'two-both-paused',p)
        finish(s,'two-current',kill=True);snap(s,'two-current-terminated',p)
        new=finish(s,'two-candidate',resume=True);snap(s,'two-candidate-returned',p)
        lookup=call(s,'two-lookup','candidate',p,'lookup');snap(s,'two-reopened',p);s['results']=dict(candidate=new,lookup=lookup);save()

        s,p=fixture('both-die-old-footprint-remains')
        launch(s,'three-candidate','candidate',p,'locked');launch(s,'three-current','current',p,'locked');held_pair(s,p,'three-both-held');snap(s,'three-both-paused',p)
        finish(s,'three-current',kill=True);finish(s,'three-candidate',kill=True);snap(s,'three-terminated',p)
        lookup=call(s,'three-lookup','candidate',p,'lookup');snap(s,'three-lookup-result',p)
        retry=call(s,'three-retry','candidate',p);snap(s,'three-retry-result',p);s['results']=dict(lookup=lookup,retry=retry);save()

        s,p=fixture('current-first-candidate-retries')
        launch(s,'four-current','current',p,'locked');snap(s,'four-current-paused',p)
        first=call(s,'four-candidate-refused','candidate',p);snap(s,'four-candidate-refused',p)
        old=finish(s,'four-current',resume=True);snap(s,'four-current-returned',p)
        retry=call(s,'four-candidate-retry','candidate',p);snap(s,'four-candidate-retried',p)
        s['results']=dict(first=first,current=old,retry=retry);save()
    finally:
        abort()
    save();print(json.dumps(dict(run=str(run),scenarios=len(scenarios),commands=len(commands),allOwnedGroupsRetired=all(c['ownedGroupAbsent']for c in commands)),indent=2))


if __name__=='__main__':main()
