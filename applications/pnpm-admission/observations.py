"""Independent retained command/script observer;no package manager execution."""
import hashlib,json,shlex
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CAP=ROOT/'applications/evidence/pnpm-admission-20261126T031327788019Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())


def observe(rows,images,edits,setup,streams):
    by_hash={r['sha256']:r for r in images['images']}
    for r in by_hash.values():assert len(r['text'].encode())==r['bytes']and hashlib.sha256(r['text'].encode()).hexdigest()==r['sha256']
    expected_events=[];packets=[];observed=[];details=[];previous=None;used_edit=False
    for row in rows:
        before,after=row['before'],row['after']
        if previous is not None and before!=previous:
            assert not used_edit and len(edits)==1 and previous==edits[0]['before']and before==edits[0]['after'];used_edit=True
        previous=after
        for name in['package.json','packages/member/package.json','pnpm-workspace.yaml']:
            info=before[name];assert info['sha256']in by_hash and by_hash[info['sha256']]['bytes']==info['bytes']
            assert before[name]==after[name]
        assert row['cwd']in[setup['project'],setup['member']]
        expected_events+=row['events']
        if row['label'].endswith('-version')or row['label'].startswith('help-'):
            assert not row['events'];details.append(dict(label=row['label'],role='version-or-help-only',exitCode=row['exitCode']));continue
        args=row['argv'][1:];forced=bool(args and args[0]=='pm')
        if forced:args=args[1:]
        if args[:2]==['--dir','.']:args=args[2:]
        command=args[0]
        if command=='run':kind='explicit-run';name=args[1];forward=args[2:]
        elif command=='tasks':kind='tasks';name=command;forward=args[1:]
        elif command in['edit','xmas']:kind='placeholder';name=command;forward=args[1:]
        else:kind='declared-fallback';name=command;forward=args[1:]
        member=row['cwd']==setup['member'];root=json.loads(by_hash[before['package.json']['sha256']]['text'])
        local=json.loads(by_hash[before['packages/member/package.json'if member else'package.json']['sha256']]['text'])
        root_body=root.get('scripts',{}).get(name,'');local_body=local.get('scripts',{}).get(name,'')
        assert isinstance(root_body,str)and isinstance(local_body,str)
        script_label=''
        if local_body:
            parts=shlex.split(local_body);assert len(parts)==3 and parts[:2]==[setup['tools']['node']['path'],str(Path(setup['work'])/'marker.cjs')];script_label=parts[2]
        help_flag=kind=='tasks'and forward==['--help']
        packets.append(dict(kind=kind,name=name,rawArgs=row['argv'][1:],forcedBuiltin=forced,builtinHelp=help_flag,inMember=member,localBody=bool(local_body),rootBody=bool(root_body),scriptLabel=script_label,args=forward))
        text=streams[row['label']];events=row['events'];assert len(events)<=1
        stdout_events=[]
        for line in text['stdout'].splitlines():
            try:value=json.loads(line)
            except json.JSONDecodeError:continue
            if isinstance(value,dict)and set(value)=={'label','args','cwd','npmCommand'}:stdout_events.append(value)
        assert stdout_events==events
        if events:
            event=events[0];assert event['cwd']==row['cwd'];action='script'
            measured=[action,row['exitCode'],event['label'],event['args'],event['npmCommand']]
        else:
            if'ERR_PNPM_NOT_IMPLEMENTED'in text['stderr']:action='unsupported'
            elif'ERR_PNPM_SCRIPT_OVERRIDE_IN_WORKSPACE_ROOT'in text['stderr']:action='root-shadow'
            elif'Usage: pnpm tasks 'in text['stdout']:action='builtin-help'
            elif'No concurrency groups are in use.'in text['stdout']:action='builtin-status'
            else:raise AssertionError(('Unadmitted observed outcome',row['label']))
            # Null means no script child was observed, not an empty script or
            # an assertion about the built-in process's own environment.
            measured=[action,row['exitCode'],None,[],None]
        observed.append(measured)
        details.append(dict(label=row['label'],role='namespace-case',observedAction=measured[0],leadingPmToken=forced,authorFilesPreserved=True,projectFilesChanged=before!=after,scope='Marker events,real CLI diagnostics/help/status,and authored inputs;not general script semantics or group scheduling.'))
    assert len(rows)==21 and len(packets)==len(observed)==15 and used_edit
    return dict(schema=1,profile='pnpm-command-script-namespace',cases=packets),observed,details,expected_events


def evidence(owner_local=True):
    for name,digest in read(CAP/'collection-basis.json').items():assert sha(CAP/name)==digest
    setup=read(CAP/'setup.json');receipt=read(CAP/'receipt.json');rows=read(CAP/'commands.json');images=read(CAP/'manifest-images.json');edits=read(CAP/'interventions.json')
    assert sha(CAP/'probe.py')==setup['producerSha256']==sha(ROOT/'applications/pnpm_admission_probe.py')
    assert images['producerSha256']==setup['producerSha256']and images['markerSha256']==setup['markerSha256']==sha(CAP/'marker.cjs')
    assert receipt['commands']==21 and receipt['allGroupsAbsent']and read(CAP/'current-process.json')['status']=='terminal'
    streams={}
    for row in rows:
        assert row['groupAbsent']and not row['timedOut']
        streams[row['label']]={}
        for name,info in row['streams'].items():
            p=CAP/info['path'];assert sha(p)==info['sha256'];streams[row['label']][name]=p.read_text()
    request,observed,details,events=observe(rows,images,edits,setup,streams)
    assert [json.loads(s)for s in(CAP/'events.jsonl').read_text().splitlines()]==events
    assert sha(CAP/'events.jsonl')==receipt['eventsSha256']
    excluded=[]
    if owner_local:
        work=Path(setup['work']);project=Path(setup['project'])
        for pin in setup['tools'].values():assert sha(Path(pin['path']))==pin['sha256']
        current={str(p.relative_to(project)):dict(bytes=p.stat().st_size,sha256=sha(p))for p in project.rglob('*')if p.is_file()}
        assert current==receipt['finalProject']and sha(work/'events.jsonl')==receipt['eventsSha256']and sha(work/'marker.cjs')==setup['markerSha256']
    else:excluded=['Current native tool bytes','Current owned project,event file,and marker bytes']
    basis={str(p.relative_to(ROOT)):sha(p)for p in CAP.iterdir()if p.is_file()}
    selections=ROOT/'applications/sources/pnpm-admission-selections.json'
    for source in read(selections)['sources']:
        if owner_local:
            data=(ROOT/source['cache']).read_bytes()
            assert len(data)==source['bytes']and hashlib.sha256(data).hexdigest()==source['sha256']
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==source['gitBlob']
        else:excluded.append('Private selected source: '+source['path'])
    gate=read(CAP/'proof-gate.json');assert gate['exitCode']==0 and'Checked 2 Lean modules and 1 Bend files.'in gate['stdout']
    for name,digest in gate['sourceSha256'].items():assert sha(ROOT/name)==digest
    # The captured setup binds the selected Node/pnpm profiles. Unrelated
    # edits to the shared tool catalog are not this comparison's read basis.
    for p in[Path(__file__).resolve(),Path(__file__).with_name('conformance.py'),Path(__file__).with_name('Admission.lean'),Path(__file__).with_name('Admission.bend'),Path(__file__).with_name('AdmissionCase.lean'),selections,ROOT/'applications/pnpm_admission_probe.py']:basis[str(p.relative_to(ROOT))]=sha(p)
    return request,observed,details,basis,excluded


if __name__=='__main__':
    request,observed,details,basis,excluded=evidence();out=ROOT/'.build/pnpm-admission-preread/observations.json';out.write_text(json.dumps(dict(input=request,measured=observed,details=details,basis=basis,privateChecksExcluded=excluded),indent=2)+'\n');print(json.dumps(dict(namespaceCases=len(observed),basisFiles=len(basis),actions=sorted(set(r[0]for r in observed)),privateChecksExcluded=excluded)))
