#!/usr/bin/env python3
"""Explicit export of authored/generated folder fixtures, without game payloads."""
import argparse
import json
from pathlib import Path
import shutil
from native_codecs import sha

HERE=Path(__file__).resolve().parent


def errors(x):
    if isinstance(x,dict):
        if x.get('observerError',False):raise ValueError('Observer error is not qualified native evidence')
        for v in x.values():errors(v)
    elif isinstance(x,list):
        for v in x:errors(v)


def export(capture):
    r=json.loads((capture/'receipt.json').read_text());request=json.loads((capture/'request.json').read_text())
    assert r['fixturesUnchanged'] and r['fixturesBefore']==r['fixturesAfter']
    assert sha(capture/'request.json')==r['requestSha256'] and sha(capture/'observed.json')==r['observedSha256']
    assert all(x['exitCode']==0 and x['ownedGroupAbsent'] and not x['timedOut'] for x in r['commands'])
    observations=json.loads((capture/'observed.json').read_text());errors(observations)
    destination=HERE/'evidence'/capture.name;destination.mkdir(parents=True,exist_ok=False)
    for name,digest in r['sourceSha256'].items():
        assert sha(capture/name)==digest;shutil.copyfile(capture/name,destination/name)
    shutil.copyfile(capture/'observed.json',destination/'observed.json')
    for name,command in zip(['compile','execute'],r['commands']):
        for stream in ['stdout','stderr']:
            assert sha(capture/(name+'.'+stream))==command[stream+'Sha256']
            shutil.copyfile(capture/(name+'.'+stream),destination/(name+'.'+stream))
    (destination/'cases.json').write_text(json.dumps(request['cases'],indent=2)+'\n')
    # Every exported byte comes from the explicitly generated fixture image.
    files={}
    for name,digest in r['fixturesBefore'].items():
        p=capture/'fixtures'/name;assert sha(p)==digest
        files[name]=p.read_text()
    (destination/'files.json').write_text(json.dumps(files,indent=2)+'\n')
    public={k:v for k,v in r.items() if k not in ['libraries','commands','tools']}
    public['libraries']=[{k:v for k,v in x.items() if k!='path'}|dict(file=Path(x['path']).name) for x in r['libraries']]
    public['tools']={k:dict(executable=Path(v['path']).name,sha256=v['sha256']) for k,v in r['tools'].items()}
    public['commands']=[{k:v for k,v in x.items() if k!='argv'}|dict(argvDisclosure='Exact owner-local argv retained privately; authored collector constructs arguments.') for x in r['commands']]
    public['publicCasesSha256']=sha(destination/'cases.json');public['publicFilesSha256']=sha(destination/'files.json')
    public['limits']=['Generated folders with manual pack order;not ZIP/discovery/UI/overlays/reload/baking/rendering.','No original game, mapping, library, decompiled source, account, world, or installation payload exported.','Metadata decoding can fail after bytes were opened;retain both facts.']
    (destination/'receipt.json').write_text(json.dumps(public,indent=2)+'\n')
    print(destination)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('capture',type=Path);export(parser.parse_args().capture.resolve())
