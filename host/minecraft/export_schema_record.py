#!/usr/bin/env python3
"""Export authored one-field observations; all bundled/library bytecode stays private."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
from urllib.parse import unquote, urlsplit
import zipfile

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture',type=Path)
    parser.add_argument('--bundled',type=Path,required=True)
    parser.add_argument('--check',action='store_true',help='Verify the existing export without writing it.')
    args = parser.parse_args(); capture = args.capture.resolve()
    receipt = json.loads((capture/'receipt.json').read_text())
    assert sha(args.bundled) == receipt['bundledSha256'] == '389766940c13572819b4ba79cf9466c571256f01ecd0cb43dc3ac4b11ff3805a'
    assert receipt['profile']['JAVA_VERSION'].startswith('21.')
    for name,value in receipt['sourcesSha256'].items():assert sha(capture/name)==value
    for name,key in [('observed.json','observedSha256'),('metadata.json','metadataSha256'),
                     ('reused-input.json','reusedReceiptSha256'),('class-load.log','classLoadLogSha256')]:
        assert sha(capture/name)==receipt[key]
    for name,value in receipt['observerClassesSha256'].items():assert sha(capture/'classes'/name)==value
    for tool in receipt['tools'].values():assert sha(Path(tool['path']))==tool['sha256']
    assert sha(Path(receipt['tools']['java']['path']).parent.parent/'release')==receipt['jdkReleaseSha256']
    for lib in receipt['libraries']:assert sha(Path(lib['path']))==lib['sha256']
    loaded = {}
    with zipfile.ZipFile(args.bundled) as archive:
        for line in (capture/'class-load.log').read_text().splitlines():
            match = re.search(r'\[class,load\] ([\w.$]+) source: (.*)',line)
            if not match:continue
            name,origin = match.groups()
            assert not name.startswith(('net.minecraft.','net.mehvahdjukaar.polytone.'))
            if name.startswith('net.mehvahdjukaar.codecui.'):
                uri = urlsplit(origin)
                assert uri.scheme == 'file' and not uri.netloc and Path(unquote(uri.path)).resolve() == args.bundled.resolve(), 'Different original class origin'
                member = name.replace('.','/')+'.class'
                loaded[member] = hashlib.sha256(archive.read(member)).hexdigest()
    assert loaded == receipt['loadedBundledClassEntriesSha256']
    destination = HERE/'evidence'/capture.name
    if args.check:assert destination.is_dir()
    else:destination.mkdir(exist_ok=False)
    def copy_or_check(name):
        if args.check:assert (capture/name).read_bytes()==(destination/name).read_bytes(),name
        else:shutil.copyfile(capture/name,destination/name)
    for name in [*receipt['sourcesSha256'],'observed.json']:
        copy_or_check(name)
    for stem,command in zip(['compile','execute'],receipt['commands']):
        assert command['exitCode']==0 and command['ownedGroupAbsent'] and not command['timedOut']
        for stream in ['stdout','stderr']:
            name=stem+'.'+stream;assert sha(capture/name)==command[stream+'Sha256']
            copy_or_check(name)
    public = {k:v for k,v in receipt.items() if k not in ['tools','libraries','commands']}
    public['tools'] = {n:dict(executable=Path(t['path']).name,sha256=t['sha256']) for n,t in receipt['tools'].items()}
    public['libraries'] = [{k:v for k,v in l.items() if k!='path'}|dict(file=Path(l['path']).name) for l in receipt['libraries']]
    public['commands'] = [{k:v for k,v in c.items() if k!='argv'}|dict(argvDisclosure='Exact argv retained privately; frozen authored collector constructs it.') for c in receipt['commands']]
    public['privateReceiptSha256'] = sha(capture/'receipt.json')
    public['limits'] = receipt['limits']+['No original class, JAR, decompiled third-party source or class-load log exported.',
        'Loaded classes are not a complete initialization, execution, dependency, or host-effect graph.',
        'JVM heap/CPU settings and retired process groups do not establish physical-memory bounds or global reclamation.']
    if args.check:assert json.loads((destination/'receipt.json').read_text())==public
    else:(destination/'receipt.json').write_text(json.dumps(public,indent=2)+'\n')
    print(json.dumps(dict(destination=str(destination.relative_to(HERE)),cases=30,loadedBundledClasses=len(loaded))))


if __name__=='__main__':main()
