#!/usr/bin/env python3
"""Owner-run original reload orchestration with authored listeners and direct executors;no game or renderer."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import zipfile
from mappings import read

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'java'))
from arena_probe import command
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ROLES={role:'net.minecraft.server.packs.resources.'+name for role,name in {
    'simple':'SimpleReloadInstance','instance':'ReloadInstance','listener':'PreparableReloadListener',
    'barrier':'PreparableReloadListener$PreparationBarrier','manager':'ResourceManager'}.items()}

def methods(version):
    barrier=ROLES['barrier'];manager=ROLES['manager'];executor='java.util.concurrent.Executor'
    if version in ['1.21.11','26.3']:
        args=ROLES['listener']+'$SharedState,'+executor+','+barrier+','+executor
    elif version=='1.21.1':
        args=barrier+','+manager+',net.minecraft.util.profiling.ProfilerFiller,net.minecraft.util.profiling.ProfilerFiller,'+executor+','+executor
    else:args=barrier+','+manager+','+executor+','+executor
    result={'simple':{'create':'create('+manager+',java.util.List,'+executor+','+executor+',java.util.concurrent.CompletableFuture,boolean)'},
        'instance':{'done':'done()'},'listener':{'reload':'reload('+args+')'},'barrier':{'wait':'wait(java.lang.Object)'},'manager':{}}
    if version in ['1.21.11','26.3']:result['listener']['prepareSharedState']='prepareSharedState('+ROLES['listener']+'$SharedState)'
    return result



def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version',choices=['1.21.1','1.21.4','1.21.5','1.21.11','26.3'],required=True)
    p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--basis',type=Path,required=True,help='Existing successful pinned library/tool/classpath receipt;read-only.')
    p.add_argument('--private',type=Path,required=True)
    a=p.parse_args(); paths={k:Path(v)for k,v in json.loads(a.inputs.read_text())['profiles'][a.version].items()}
    target=next(t for t in json.loads((HERE/'targets.json').read_text())['javaReferences']if t['release']==a.version)
    basis=json.loads((a.basis/'receipt.json').read_text());assert basis['target']==target['id']
    assert sha(paths['client'])==basis['clientSha256']==target['source']['clientSha256']
    assert sha(paths['metadata'])==target['source']['metadataSha256']
    for lib in basis['libraries']:assert sha(Path(lib['path']))==lib['sha256']
    jdk=Path(basis['tools']['java']['path']).parent.parent
    for name,t in basis['tools'].items():assert sha(Path(t['path']))==t['sha256']
    release=dict(re.findall(r'^([A-Z_]+)="([^"]*)"',(jdk/'release').read_text(),re.M))
    assert release['JAVA_VERSION'].startswith('25.'if a.version=='26.3'else'21.')
    METHODS=methods(a.version)
    if a.version=='26.3':
        mappings={role:dict(name=name,methods={k:v.split('(')[0]for k,v in METHODS[role].items()})for role,name in ROLES.items()}
    else:
        metadata=json.loads(paths['metadata'].read_text())
        assert hashlib.sha1(paths['mappings'].read_bytes()).hexdigest()==metadata['downloads']['client_mappings']['sha1']
        all_mappings=read(paths['mappings']);mappings={role:all_mappings[name]for role,name in ROLES.items()}
    bindings={role:dict(originalName=ROLES[role],**{'class':item['name']},methods={k:item['methods'][signature]if a.version!='26.3'else item['methods'][k]for k,signature in METHODS[role].items()})for role,item in mappings.items()}
    cap=a.private.resolve()/('reload-native-'+a.version+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));cap.mkdir(parents=True)
    for n in ['classes','home','tmp']:(cap/n).mkdir()
    for src in [Path(__file__),HERE/'ReloadProbe.java',HERE/'reload-cases.json',HERE/'mappings.py',HERE.parent/'java/arena_probe.py']:shutil.copyfile(src,cap/src.name)
    (cap/'bindings.json').write_text(json.dumps(bindings,indent=2)+'\n');shutil.copyfile(a.inputs,cap/'inputs.json')
    request=json.loads((cap/'reload-cases.json').read_text());request['hasSharedState']=a.version in ['1.21.11','26.3']
    (cap/'request.json').write_text(json.dumps(request,indent=2)+'\n')
    with zipfile.ZipFile(paths['client'])as z:
        original={v['name'].replace('.','/')+'.class':hashlib.sha256(z.read(v['name'].replace('.','/')+'.class')).hexdigest()for v in mappings.values()}
    r=dict(schema=1,target=target['id'],clientSha256=sha(paths['client']),metadataSha256=sha(paths['metadata']),
        mappingSha256=sha(paths['mappings'])if a.version!='26.3'else None,basisReceiptSha256=sha(a.basis/'receipt.json'),requestSha256=sha(cap/'request.json'),
        bindingsSha256=sha(cap/'bindings.json'),inputsSha256=sha(cap/'inputs.json'),selectedClassSha256=original,
        sourcesSha256={n:sha(cap/n)for n in ['native_reload.py','ReloadProbe.java','reload-cases.json','mappings.py','arena_probe.py']},
        libraries=basis['libraries'],tools=basis['tools'],jdkReleaseSha256=sha(jdk/'release'),
        profile={k:release[k]for k in ['JAVA_VERSION','JAVA_RUNTIME_VERSION','IMPLEMENTOR','OS_NAME','OS_ARCH']},commands=[],
        scope='Original SimpleReloadInstance.create/ReloadInstance.done and preparation barriers with authored dynamic-proxy listeners,manual completion gates and direct executors. No ResourceManager method effects,game,GUI,real pack,IO worker or renderer qualification;incidental JVM/library effects unmeasured.')
    save=lambda:(cap/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
    save();cp=os.pathsep.join(lib['path']for lib in r['libraries']);env=dict(os.environ,TMPDIR=str(cap/'tmp'))
    argv=[str(jdk/'bin/javac'),'-J-XX:ActiveProcessorCount=2','-J-Xmx128m','--release','21','-proc:none','-Xlint:all,-classfile','-Werror','-encoding','UTF-8','-cp',cp,'-d',str(cap/'classes'),str(cap/'ReloadProbe.java')]
    result=command(argv,cap,'compile',env,30);r['commands'].append(result);save();assert result['exitCode']==0 and result['ownedGroupAbsent']and not result['timedOut']
    argv=[str(jdk/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx256m','-Djava.awt.headless=true','-Duser.home='+str(cap/'home'),'-Djava.io.tmpdir='+str(cap/'tmp'),'-Xlog:class+load=info:file='+str(cap/'class-load.log'),'-cp',os.pathsep.join([str(cap/'classes'),str(paths['client']),cp]),'study.minecraft.ReloadProbe',str(cap/'bindings.json'),str(cap/'request.json'),str(cap/'observed.json')]
    result=command(argv,cap,'execute',env,30);r['commands'].append(result)
    r['observerClassesSha256']={str(f.relative_to(cap/'classes')):sha(f)for f in (cap/'classes').rglob('*.class')}
    for n in ['observed.json','class-load.log']:
        if(cap/n).exists():r[n+'Sha256']=sha(cap/n)
    if(cap/'observed.json').exists():
        rows=json.loads((cap/'observed.json').read_text());r['cases']=len(rows['cases']);r['snapshots']=sum(len(c.get('snapshots',[]))for c in rows['cases']);r['observerErrors']=rows['observerErrors'];r['skippedCases']=[c['id']for c in rows['cases']if'skipped'in c]
    save();assert result['exitCode']==0 and result['ownedGroupAbsent']and not result['timedOut']and r.get('observerErrors')==0 and r.get('cases')==8
    assert sha(cap/'bindings.json')==r['bindingsSha256'] and sha(a.inputs)==r['inputsSha256']
    assert sha(paths['client'])==r['clientSha256'] and all(sha(cap/n)==h for n,h in r['sourcesSha256'].items())
    assert all(sha(Path(lib['path']))==lib['sha256']for lib in r['libraries'])
    (a.private/('latest-reload-native-'+a.version+'.json')).write_text(json.dumps(dict(capture=str(cap)))+'\n')
    print(json.dumps(dict(capture=str(cap),cases=r['cases'],snapshots=r['snapshots'],skippedCases=r['skippedCases'],observerErrors=r['observerErrors'],ownedGroupsAbsent=True)))


if __name__=='__main__':main()
