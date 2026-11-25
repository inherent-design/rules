#!/usr/bin/env python3
"""Verify private original-codec evidence and publish only authored data and receipts."""
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
    cap=a.capture.resolve();r=json.loads((cap/'receipt.json').read_text());assert sha(a.client)==r['clientSha256']and r['rows']==14 and r['observerErrors']==0
    assert sha(cap/'request.json')==r['requestSha256']and sha(cap/'inputs.json')==r['inputsSha256']
    for n,h in r['sourcesSha256'].items():assert sha(cap/n)==h
    for n,h in r['observerClassesSha256'].items():assert sha(cap/'classes'/n)==h
    for t in r['tools'].values():assert sha(Path(t['path']))==t['sha256']
    for t in r['libraries']:assert sha(Path(t['path']))==t['sha256']
    for n in ['observed.json','class-load.log']:assert sha(cap/n)==r[n+'Sha256']
    loaded={}
    with zipfile.ZipFile(a.client)as z:
        for n,h in r['selectedClassSha256'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h
        for line in (cap/'class-load.log').read_text().splitlines():
            if a.client.name not in line:continue
            m=re.search(r'\] ([^ ]+) source: ',line);assert m
            name=m[1].replace('.','/')+'.class';loaded[name]=hashlib.sha256(z.read(name)).hexdigest()
    assert set(r['selectedClassSha256'])<=set(loaded)
    dest=HERE/'evidence'/cap.name
    if a.check:assert dest.is_dir()
    else:dest.mkdir(exist_ok=False)
    def copy(name):
        if a.check:assert(cap/name).read_bytes()==(dest/name).read_bytes()
        else:shutil.copyfile(cap/name,dest/name)
    for n in [*r['sourcesSha256'],'observed.json']:copy(n)
    for stem,c in zip(['compile','execute'],r['commands']):
        assert c['exitCode']==0 and c['ownedGroupAbsent']and not c['timedOut']
        for channel in ['stdout','stderr']:
            n=stem+'.'+channel;assert sha(cap/n)==c[channel+'Sha256'];copy(n)
    request=json.loads((cap/'request.json').read_text());cases=dict(schema=1,target=r['target'],cases=request['cases'])
    cases_bytes=(json.dumps(cases,indent=2)+'\n').encode()
    if a.check:assert(dest/'cases.json').read_bytes()==cases_bytes
    else:(dest/'cases.json').write_bytes(cases_bytes)
    public={k:v for k,v in r.items()if k not in ['commands','libraries','tools']}
    public['commands']=[{k:v for k,v in c.items()if k!='argv'}|dict(argvDisclosure='Exact local argv retained privately;frozen producer defines it.')for c in r['commands']]
    public['tools']={k:dict(executable=Path(v['path']).name,sha256=v['sha256'])for k,v in r['tools'].items()}
    public['libraries']=[{k:v for k,v in t.items()if k!='path'}|dict(file=Path(t['path']).name)for t in r['libraries']]
    public.update(privateReceiptSha256=sha(cap/'receipt.json'),casesSha256=hashlib.sha256(cases_bytes).hexdigest(),loadedOriginalClassSha256=loaded,
        limits=['Fourteen bounded integer/Boolean requests per profile to original GuiSpriteScaling.CODEC;not whole JSON or delegated-number grammar.',
                'Dimension fields and later stretchInner are observed;native diagnostics are retained,not predicted stable public error codes.',
                'No actual GUI,image,atlas,game,provider or renderer call;destination-border clamping and submitted uses remain source-only.',
                'Native macOS/JDK21/25 only;incidental JVM/class/library effects and other hosts remain unqualified.'])
    if a.check:assert json.loads((dest/'receipt.json').read_text())==public
    else:(dest/'receipt.json').write_text(json.dumps(public,indent=2)+'\n')
    print(json.dumps(dict(capture=dest.name,rows=14,loadedOriginalClasses=len(loaded),checked=a.check)))


if __name__=='__main__':main()
