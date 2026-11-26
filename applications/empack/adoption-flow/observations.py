"""Independent retained CLI/document/effect reader; never runs empack."""
import copy
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'applications/evidence/empack-adoption-flow-20261126T081334217208Z'
EXTRA=ROOT/'applications/evidence/empack-adoption-matching-local-20261126T081545037258Z'
read=lambda p:json.loads(p.read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()


def text(image,name):
    r=image[name];raw=bytes.fromhex(r['bytesHex'])
    assert len(raw)==r['bytes'] and sha(raw)==r['sha256'] and hashlib.sha512(raw).hexdigest()==r['sha512']
    return raw.decode()


def changed(before,after):return sorted(k for k in before.keys()|after.keys()if before.get(k)!=after.get(k))


def packets(base=BASE,extra=EXTRA):
    setup=read(base/'setup.json');versions={v:i for i,v in enumerate([None,setup['payloads']['A'],setup['payloads']['B']])}
    for v in ['A','B']:
        p=base/('payload-'+v+'.zip');assert sha(p.read_bytes())==setup['payloads'][v]
        with zipfile.ZipFile(p)as z:
            assert z.testzip()is None and z.namelist()==['pack.mcmeta','assets/rules/textures/marker.txt']
            assert z.read('assets/rules/textures/marker.txt')==v.encode()
    def accepted(image):
        if 'empack.lock'not in image:return 0
        lock=text(image,'empack.lock')
        values=re.findall(r'^        accepted-observation: ([a-f0-9]{64})$',lock,re.M)
        assert len(values)==1 and values[0]in versions and 'schema: 3\n'in lock
        assert '        digests: null\n'in lock and '  observed: unknown\n'in lock and '    selection: null\n'in lock
        return versions[values[0]]
    mutations=read(base/'mutations.json');previous={};used=0;inputs=[];views=[];effects=[]
    def inspect(run,command):
        doc=json.loads(text(command['before']['project'],'empack.yml'));roots=doc['dependencies'];assert set(roots)<= {'observed','second'}
        assert roots['observed']['type']=='resource-pack'
        root=roots['observed'];local='path'in root
        assert root['placement']==[dict(destination='resourcepacks/observed.zip',layer='common',environment=dict(client='required',server='unsupported'))]
        if local:assert root['path']=='vendor/observed.zip'
        else:assert root['url']=='https://example.invalid/observed.zip' and root['accept-observed']is True
        argv=command['argv'];args=argv[argv.index('--yes')+1:];assert args[0]=='adopt';keys=[k for k in args[1:]if k!='--dry-run']
        assert keys and set(keys)<=set(roots)
        before,after=command['before']['project'],command['after']['project'];old=accepted(before);new=accepted(after)
        def content(image,name):return versions[image.get(name,{}).get('sha256')]
        payload=content(before,'pack/resourcepacks/observed.zip');source=content(before,'vendor/observed.zip')if local else 0
        assert content(after,'pack/resourcepacks/observed.zip')==payload and text(before,'empack.yml')==text(after,'empack.yml')
        assert {k:v for k,v in before.items()if k.startswith(('pack/','vendor/'))}=={k:v for k,v in after.items()if k.startswith(('pack/','vendor/'))},'Payload identity,mode,time,or bytes changed.'
        error=(run/(command['id']+'.stderr')).read_text();stdout=(run/(command['id']+'.stdout')).read_text()
        for stream in ['stdout','stderr']:assert sha((run/(command['id']+'.'+stream)).read_bytes())==command['streams'][stream]
        assert command['groupAbsent']and not command['timedOut']
        reasons={'First-lock adoption must select every declared dependency root':1,'Repeated adoption key':2,'Input is not a captured regular file: pack/resourcepacks/observed.zip':3,'Source differs from accepted lock observation':4}
        if command['exitCode']==0:
            reason=0;vals=re.findall(r'^i After file primary: accepted SHA-256 ([a-f0-9]{64})$',stdout,re.M)
            if vals:
                assert len(vals)==1 and vals[0]in versions;candidate=versions[vals[0]]
                assert candidate==payload and 'After dependency information: not recorded'in stdout
                assert ('download hosts https://example.invalid'in stdout) == (not local)
            else:
                assert '--dry-run'in args and old==payload==new and '+ Dry run complete - no changes applied'in stdout
                candidate=None  # No candidate detail was printed; do not infer it from silence.
        else:
            assert command['exitCode']==1;found=[v for k,v in reasons.items()if k in error];assert len(found)==1;reason=found[0];candidate=0
        changes={k:changed(command['before'][k],command['after'][k])for k in ['project','state','cache']};assert not changes['cache']
        if reason or '--dry-run'in args:assert not any(changes.values()),'Preview/refusal changed a measured scope.'
        else:
            assert changes['project']==['empack.lock']and changes['state']
            assert '+ Recorded 1 existing dependency (1 file change)'in stdout
        inputs.append(dict(id=command['id'],firstLock=old==0,allRoots=set(keys)==set(roots),repeated=len(keys)!=len(set(keys)),localSource=local,sourceBytes=source,installedBytes=payload,acceptedBefore=old,preview='--dry-run'in args))
        views.append(dict(id=command['id'],reason=reason,candidate=candidate,acceptedAfter=new,documentsChanged=bool(changes['project']),installedAfter=payload))
        effects.append(dict(id=command['id'],projectChanges=changes['project'],stateChanged=bool(changes['state']),cacheChanged=False,payloadUnchanged=True))
    commands=read(base/'commands.json');assert len(commands)==11
    for c in commands:
        name=c['project']
        if name in previous and c['before']!=previous[name]:
            assert used<len(mutations);m=mutations[used];assert m['project']==name and m['before']==previous[name]['project']
            assert set(changed(m['before'],m['after']))=={m['path']}
            expected=copy.deepcopy(previous[name]);expected['project']=m['after'];assert expected==c['before'];used+=1
        previous[name]=c['after'];inspect(base,c)
    assert used==len(mutations)==4
    continuation=read(extra/'setup.json');assert sha((base/'receipt.json').read_bytes())==continuation['baseReceiptSha256']and sha((base/'commands.json').read_bytes())==continuation['baseCommandsSha256']
    assert continuation['initial']==previous['local'];mutation=read(extra/'mutation.json');assert mutation['before']==previous['local']
    assert set(changed(mutation['before']['project'],mutation['after']['project']))==set(mutation['paths'])=={'vendor/observed.zip','pack/resourcepacks/observed.zip'}
    assert mutation['before']['state']==mutation['after']['state']and mutation['before']['cache']==mutation['after']['cache']
    for n in mutation['paths']:assert mutation['after']['project'][n]['sha256']==setup['payloads']['B']
    previous['local']=mutation['after'];commands=read(extra/'commands.json');assert len(commands)==2
    for c in commands:assert c['before']==previous['local'];previous['local']=c['after'];inspect(extra,c)
    return dict(schema=1,cases=inputs),views,effects
