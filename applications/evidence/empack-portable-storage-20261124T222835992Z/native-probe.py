#!/usr/bin/env python3
"""Independent study-backup decoder and installed native export comparison."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import signal
import stat
import subprocess
import unicodedata
import zipfile

ROOT=Path(__file__).resolve().parents[2]
FORMAT='rules.empack.draft-study'
UUID=re.compile(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}')
HEX=re.compile(r'[a-f0-9]{64}')
sha=lambda b:hashlib.sha256(b).hexdigest()


def pairs(values):
    r={}
    for k,v in values:
        if k in r:raise ValueError('Duplicate field: '+k)
        r[k]=v
    return r

def exact(value,keys):
    if not isinstance(value,dict)or set(value)!=set(keys):raise ValueError('Study object fields')
    return value

def ref(value,extra=()):
    exact(value,['id','sha256','bytes',*extra])
    if not isinstance(value['id'],str)or not UUID.fullmatch(value['id'])or not isinstance(value['sha256'],str)or not HEX.fullmatch(value['sha256']):raise ValueError('Study asset ID/digest')
    if type(value['bytes'])is not int or not 0<=value['bytes']<=1024*1024:raise ValueError('Study asset size')
    return value

def path(value):
    if not isinstance(value,str)or not value or len(value)>512 or value!=unicodedata.normalize('NFC',value)or re.search(r'[\\\x00-\x1f<>:"|?*]',value):raise ValueError('Study path')
    if any(p in ['', '.', '..']or p.endswith(('.', ' '))for p in value.split('/')):raise ValueError('Study path segments')
    return value

def decode(payload):
    if len(payload)>8*1024*1024:raise ValueError('Study container bound')
    r=json.loads(payload.decode('utf-8'),object_pairs_hook=pairs);exact(r,['format','schema','record','assets'])
    if r['format']!=FORMAT or type(r['schema'])is not int or r['schema']!=1:raise ValueError('Study format/version')
    record=exact(r['record'],['format','schema','project','revision','attempt','image','draft'])
    if record['format']!=FORMAT or record['schema']!=1 or record['project']!='fixture-project':raise ValueError('Study record header')
    if not isinstance(record['revision'],str)or not re.fullmatch(r'[1-9][0-9]*',record['revision'])or int(record['revision'])>2**64-1:raise ValueError('Study revision')
    if not isinstance(record['attempt'],str)or not re.fullmatch(r'[a-z0-9-]{1,80}',record['attempt']):raise ValueError('Study attempt')
    draft=exact(record['draft'],['label','author','entries','missing']);ref(draft['author'])
    if not isinstance(draft['label'],str)or len(draft['label'])>256 or not isinstance(draft['entries'],list)or not isinstance(draft['missing'],list)or len(draft['entries'])+len(draft['missing'])>32:raise ValueError('Study draft bound')
    names=set()
    for entry in draft['entries']:
        exact(entry,['path','asset','originalName','evidence']);p=path(entry['path']);key=p.lower()
        if key in names:raise ValueError('Study path collision')
        names.add(key);ref(entry['asset'])
        if not isinstance(entry['originalName'],str)or len(entry['originalName'])>256 or entry['evidence']!='observed-only':raise ValueError('Study source evidence')
    if [e['path']for e in draft['entries']]!=sorted(e['path']for e in draft['entries']):raise ValueError('Study entry order')
    for p in draft['missing']:
        p=path(p);key=p.lower()
        if key in names:raise ValueError('Study missing/available collision')
        names.add(key)
    if draft['missing']!=sorted(draft['missing']):raise ValueError('Study missing order')
    if not isinstance(r['assets'],list)or len(r['assets'])>33:raise ValueError('Study asset count')
    assets={};metadata={};total=0
    for a in r['assets']:
        ref(a,extra=['base64'])
        if a['id']in assets or not isinstance(a['base64'],str):raise ValueError('Study duplicate asset')
        value=base64.b64decode(a['base64'],validate=True);total+=len(value)
        if len(value)!=a['bytes']or sha(value)!=a['sha256']or total>4*1024*1024:raise ValueError('Study asset bytes/digest/total')
        assets[a['id']]=value;metadata[a['id']]={k:a[k]for k in ['id','sha256','bytes']}
    refs=[draft['author'],*[e['asset']for e in draft['entries']]]
    if set(assets)!={a['id']for a in refs}or any(metadata[a['id']]!=a for a in refs):raise ValueError('Study retained closure')
    content=lambda a:{k:a[k]for k in ['sha256','bytes']}
    semantic={**draft,'author':content(draft['author']),'entries':[{**e,'asset':content(e['asset'])}for e in draft['entries']]}
    encoded=json.dumps(semantic,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    if not isinstance(record['image'],str)or sha(encoded)!=record['image']:raise ValueError('Study semantic image')
    files={'empack.yml':assets[draft['author']['id']],**{e['path']:assets[e['asset']['id']]for e in draft['entries']}}
    return r,files


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path);args=parser.parse_args();run=args.run.resolve()
    assert run.parent==ROOT/'applications/evidence'and run.name.startswith('empack-portable-storage-')
    target=run/'work/native';assert not target.exists(),'Inspect prior partial native work instead of restarting.'
    target.mkdir(mode=0o700)
    browser=json.loads((run/'receipt.json').read_text());assert not browser.get('error')and browser['serverClosed']
    program=Path('/Users/zer0cell/.local/bin/empack');assert sha(program.read_bytes())=='99dabfeac357d25c9ec68f05c4d09b3154dbdcd905baf516c28a866e847d447f'
    (run/'native-probe.py').write_bytes(Path(__file__).read_bytes());commands=[];profiles=[]
    report=dict(schema=1,binary=str(program),binarySha256=sha(program.read_bytes()),producerSha256=sha((run/'native-probe.py').read_bytes()),browserReceiptSha256=sha((run/'receipt.json').read_bytes()),commands=commands,profiles=profiles,
        limits=['Study decoder is not an empack project schema or recovery/adoption path.',
            'Native export consumes restored source bytes with generated native lock;no browser consumer codec/shared engine or lossless full native-project backup is qualified.',
            'Opaque JAR fixture tests byte transport,not executable mod behavior,loader compatibility or actual Prism/game launch.'])
    def save():(run/'native.json').write_text(json.dumps(report,indent=2)+'\n')
    def command(label,base,tail):
        env=dict(PATH='/usr/bin:/bin',HOME=str(base/'home'),TMPDIR=str(base/'tmp'),LANG='en_US.UTF-8',NO_COLOR='1')
        argv=[str(program),'--state-dir',str(base/'state'),'--cache-dir',str(base/'cache'),'--workdir',str(base/'project'),'--color','never','--yes',*tail]
        proc=subprocess.Popen(argv,cwd=base,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        try:out,err=proc.communicate(timeout=45)
        except BaseException:
            if proc.poll()is None:os.killpg(proc.pid,signal.SIGKILL);proc.communicate(timeout=10)
            raise
        try:os.killpg(proc.pid,0)
        except ProcessLookupError:absent=True
        else:absent=False
        assert absent
        for stream,data in [('stdout',out),('stderr',err)]:(run/(label+'.'+stream)).write_bytes(data)
        c=dict(label=label,argv=argv,exitCode=proc.returncode,ownedGroupAbsent=absent,stdoutSha256=sha(out),stderrSha256=sha(err));commands.append(c);save();print(label,proc.returncode,flush=True);return c
    input_hashes=browser['inputSha256'];all_inventories=[]
    for profile in browser['profiles']:
        assert profile['contextClosed']and profile['firstContextClosed'];name=profile['engine'];summary=dict(engine=name,backups=[]);profiles.append(summary)
        decoded={}
        for d in profile['downloads']:
            payload=(run/d['file']).read_bytes();assert sha(payload)==d['sha256']and len(payload)==d['bytes']and d['completed']
            bundle,files=decode(payload);decoded[d['label']]=(bundle,files)
            observed={p:dict(bytes=len(value),sha256=sha(value))for p,value in files.items()}
            summary['backups'].append(dict(label=d['label'],image=bundle['record']['image'],revision=bundle['record']['revision'],files=observed,missing=bundle['record']['draft']['missing']))
            assert observed['pack/mods/Sample Ω 日本.jar']['sha256']==input_hashes['jar']
            assert observed['pack/config/renamed-rules.json']['sha256']==input_hashes['config']
            if d['label']=='complete-backup':assert observed['pack/config/not-supplied.cfg']['sha256']==input_hashes['supplied']and observed['empack.yml']['sha256']==input_hashes['nativeAuthor']
        for label in ['invalid-backup','complete-backup']:
            bundle,files=decoded[label];base=target/name/label
            for folder in ['project','state','cache','home','tmp']:(base/folder).mkdir(parents=True,mode=0o700)
            for p,data in files.items():
                destination=base/'project'/p;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
            if label=='invalid-backup':
                c=command(name+'-invalid-author',base,['--dry-run','sync']);assert c['exitCode']!=0
            else:
                c=command(name+'-sync',base,['sync']);assert c['exitCode']==0,'Retain failed native sync.'
                c=command(name+'-prism',base,['build','--ad-hoc','prism','--delivery','bundled','--environment','client','--updates','snapshot','--format','zip']);assert c['exitCode']==0,'Retain failed native export.'
                paths=list((base/'project/dist').iterdir());assert len(paths)==1 and zipfile.is_zipfile(paths[0]);archive=paths[0]
                inventory={}
                with zipfile.ZipFile(archive)as z:
                    assert len(z.infolist())<=64;total=0
                    for member in z.infolist():
                        p=PurePosixPath(member.filename);assert not p.is_absolute()and '..'not in p.parts and '\\'not in member.filename
                        if member.is_dir():continue
                        assert member.filename not in inventory;value=z.read(member);total+=len(value);assert total<=4*1024*1024
                        inventory[member.filename]=dict(bytes=len(value),sha256=sha(value),mode=(member.external_attr>>16)&0o777)
                for p,data in files.items():
                    if p.startswith('pack/'):
                        matches=[v for n,v in inventory.items()if n.endswith('/.minecraft/'+p[5:])or n=='.minecraft/'+p[5:]]
                        assert len(matches)==1 and matches[0]['sha256']==sha(data),(p,list(inventory))
                summary['archive']=dict(path=str(archive.relative_to(run)),sha256=sha(archive.read_bytes()),inventory=inventory)
                all_inventories.append(inventory)
            assert all((base/'project'/p).read_bytes()==value for p,value in files.items())
        save()
    assert all_inventories[0]==all_inventories[1],'Different browser inputs produced different consumer inventories;inspect before normalizing.'
    # The decoder must reject altered transport/schema/paths/closure,not just
    # successfully read this producer's output.
    import copy
    original=json.loads((run/browser['profiles'][0]['downloads'][1]['file']).read_text());negative=[]
    for label,edit in [('version',lambda b:b.update(schema=2)),('path',lambda b:b['record']['draft']['entries'][0].update(path='../escape')),
        ('missing-asset',lambda b:b['assets'].pop()),('wrong-digest',lambda b:b['assets'][0].update(sha256='0'*64)),
        ('extra-asset',lambda b:b['assets'].append(b['assets'][0])),('changed-image',lambda b:b['record'].update(image='0'*64))]:
        value=copy.deepcopy(original);edit(value)
        try:decode(json.dumps(value,ensure_ascii=False).encode())
        except (ValueError,TypeError):negative.append(label)
        else:raise AssertionError('Study decoder accepted altered '+label)
    report.update(equalNativeInventories=True,decoderRefusals=negative,allocatedKiB=int(subprocess.check_output(['du','-sk',str(run/'work')],text=True).split()[0]));save();print(json.dumps(dict(run=str(run),commands=len(commands),profiles=len(profiles),equalNativeInventories=True,negative=negative),indent=2))


if __name__=='__main__':main()
