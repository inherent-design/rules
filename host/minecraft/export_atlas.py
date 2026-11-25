#!/usr/bin/env python3
"""Export authored serial atlas traces and identities; original game bytes stay private."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--client',type=Path,required=True);p.add_argument('--check',action='store_true');a=p.parse_args()
    cap=a.capture.resolve();r=json.loads((cap/'receipt.json').read_text())
    assert r['observerErrors']==0 and r['cases']==16 and sha(a.client)==r['clientSha256']
    for name,digest in r['sourcesSha256'].items():assert sha(cap/name)==digest
    assert sha(cap/'bindings.json')==r['bindingsSha256']
    for name in ['observed.json','class-load.log']:assert sha(cap/name)==r[name+'Sha256']
    for name,digest in r['observerClassesSha256'].items():assert sha(cap/'classes'/name)==digest
    for t in r['tools'].values():assert sha(Path(t['path']))==t['sha256']
    for lib in r['libraries']:assert sha(Path(lib['path']))==lib['sha256']
    loaded={}
    with zipfile.ZipFile(a.client) as archive:
        for name,digest in r['selectedClassSha256'].items():assert hashlib.sha256(archive.read(name)).hexdigest()==digest
        for line in (cap/'class-load.log').read_text().splitlines():
            if a.client.name not in line:continue
            match=re.search(r'\] ([^ ]+) source: ',line);assert match
            member=match[1].replace('.','/')+'.class';loaded[member]=hashlib.sha256(archive.read(member)).hexdigest()
    assert set(r['selectedClassSha256'])<=set(loaded)
    dest=HERE/'evidence'/cap.name
    if a.check:assert dest.is_dir()
    else:dest.mkdir(exist_ok=False)
    def copy(name):
        if a.check:assert (cap/name).read_bytes()==(dest/name).read_bytes()
        else:shutil.copyfile(cap/name,dest/name)
    for name in [*r['sourcesSha256'],'bindings.json','observed.json']:copy(name)
    for stem,c in zip(['compile','execute'],r['commands']):
        assert c['exitCode']==0 and c['ownedGroupAbsent'] and not c['timedOut']
        for stream in ['stdout','stderr']:
            name=stem+'.'+stream;assert sha(cap/name)==c[stream+'Sha256'];copy(name)
    public={k:v for k,v in r.items() if k not in ['commands','tools','libraries']}
    public['commands']=[{k:v for k,v in c.items() if k!='argv'}|dict(argvDisclosure='Exact local argv stays private; frozen producer constructs it.') for c in r['commands']]
    public['tools']={n:dict(executable=Path(t['path']).name,sha256=t['sha256']) for n,t in r['tools'].items()}
    public['libraries']=[{k:v for k,v in x.items() if k!='path'}|dict(file=Path(x['path']).name) for x in r['libraries']]
    public['privateReceiptSha256']=sha(cap/'receipt.json');public['loadedOriginalClassSha256']=loaded
    public['limits']=['Original list assembly only with authored source/loader proxies;no image loader called or resource manager used.',
        'Supplier aliases and throwing callbacks are deliberate adapter controls,not established production/provider reachability.',
        'Returned loader order comes from an actual HashMap;models compare bags,not a stable sprite ordering guarantee.',
        'Discard is an observed callback,not proof of pixel release,unreachability,ownership validity or GPU retirement.',
        'Null resource manager is deliberately ignored by authored sources;actual source codecs/resource-stack parsing remain separate.',
        'Class-load identities are not initialization,method-execution or effect-closure proofs. Native macOS/JDK21 or25 only.']

    if a.check:assert json.loads((dest/'receipt.json').read_text())==public
    else:(dest/'receipt.json').write_text(json.dumps(public,indent=2)+'\n')
    print(json.dumps(dict(capture=dest.name,cases=r['cases'],loadedOriginalClasses=len(loaded),checked=a.check)))


if __name__=='__main__':main()
