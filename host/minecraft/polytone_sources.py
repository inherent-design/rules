#!/usr/bin/env python3
"""Index exact private binary inspection views;not a semantic or runtime gate."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--views',type=Path,required=True);p.add_argument('--artifact',type=Path,required=True);args=p.parse_args()
    capture=args.views.resolve();views=capture/'source';r=json.loads((capture/'receipt.json').read_text())
    assert r['exitCode']==0 and r['ownedGroupAbsent'] and sha(args.artifact)==r['inputSha256']=='7c78b6f425d84a85dc1dcdc6d2d00073fbe16f9de0217325467d9d218a5cd96d'
    assert {str(p.relative_to(views)) for p in views.rglob('*.java')}==set(r['viewsSha256']),'Unfrozen inspection view'
    for name,digest in r['viewsSha256'].items():assert sha(views/name)==digest
    with zipfile.ZipFile(args.artifact) as binary:
        original_digests={n:hashlib.sha256(binary.read(n)).hexdigest() for n in binary.namelist() if n.endswith('.class')}
    root=views/'net/mehvahdjukaar/polytone/Polytone.java';text=root.read_text();imports={x.rsplit('.',1)[-1]:x for x in re.findall(r'^import ([\w.]+);',text,re.M)}
    fields=re.findall(r'public static final (\w+Manager) (\w+) = new \1\(\);',text);assert len(fields)==28
    order=re.search(r'COMPOUND_RELOADER = new PolytoneReloadManager\((.*?)\n      \);',text,re.S).group(1)
    order=re.findall(r'\b[A-Z_]+\b',order);assert len(order)==28 and set(order)=={f for c,f in fields}
    sources={};managers=[]
    def source(path):
        name=str(path.relative_to(views));entry=name.removesuffix('.java')+'.class'
        sources[name]=dict(viewSha256=sha(path),originalOuterClassEntry=entry,originalOuterClassEntrySha256=original_digests.get(entry),kind='decompiled-private-inspection-view;not-upstream-source');return name
    source(root)
    all_views=[(path,path.read_text()) for path in sorted(views.rglob('*.java'))]
    with zipfile.ZipFile(args.artifact) as jar:
        for cls,field in fields:
            name=imports[cls];entry=name.replace('.','/')+'.class';data=jar.read(entry);path=views/(name.replace('.','/')+'.java');s=path.read_text()
            constructor=re.search(r'public '+cls+r'\(\) \{(.*?)\n   }',s,re.S);assert constructor,cls
            body=constructor.group(1);folders=re.search(r'\.folders\(([^)]*)\)',body)
            if folders:
                folders=re.findall(r'"([^"]*)"',folders.group(1));resource=dict(style='default-polytone-directory',folders=folders,prefix='polytone/')
            elif cls=='ColorManager':
                folders=['polytone','colormatic','vanadium','optifine'];resource=dict(style='single-file-suffix-stack',folders=folders,suffixes=['color.properties','colors.json'])
            elif cls=='VoxelVolumeManager':folders=[];resource=dict(style='callback-derived;no-constructor-resource-directory',folders=[])
            else:raise ValueError('Unreviewed resource-root shape: '+cls)
            assert all(f.encode() in data for f in folders),'Original constant pool disagrees with view folder literals'
            consumers=[]
            for consumer,view in all_views:
                lines=[i for i,line in enumerate(view.splitlines(),1) if 'Polytone.'+field in line]
                if lines:consumers.append(dict(source=source(consumer),lines=lines,qualification='static-reference-candidate;not-active-injection-or-runtime-dispatch'))
            phases={phase:bool(re.search(r'(?:public|protected) (?:[\w<>.,? ]+) '+phase+r'\(',s)) for phase in ['earlyProcess','prepare','parseWithLevel','parseWithoutLevel','applyWithLevel','resetWithLevel']}
            declaration_candidates=re.findall(r'^   (?:public|protected) (?:static )?(?:final )?[^\n]+ (\w+)\([^;\n]*',s,re.M)
            managers.append(dict(id='polytone.'+field.lower(),field=field,className=name,classEntrySha256=hashlib.sha256(data).hexdigest(),source=source(path),constructorStartLine=s[:constructor.start()].count('\n')+1,reloadOrder=order.index(field),resources=resource,codecReferences=sorted(set(re.findall(r'([\w.$]+\.CODEC)',body))),declaredPhaseOverrides=phases,methodDeclarationCandidates=sorted(set(declaration_candidates)),staticConsumerReferences=consumers,assessment='source-discovery-only;schema,consumer-effects,UX,rules,proofs-and-native-qualification-pending'))
        descriptors=[]
        for entry in ['polytone-common.mixins.json','polytone.mixins.json']:
            raw=jar.read(entry);d=json.loads(raw);descriptors.append(dict(entry=entry,sha256=hashlib.sha256(raw).hexdigest(),package=d['package'],mixins=d.get('mixins',[]),client=d.get('client',[]),plugin=d.get('plugin'),qualification='descriptor-declaration;not-proof-of-applied-transform'))
    for name in ['common/Parsed.java','common/reloader/ContentManager.java','common/reloader/SingleFileContentManager.java','common/reloader/PolytoneReloadManager.java','platform/PolytoneForge.java','compat/CompatHandler.java']:
        source(views/'net/mehvahdjukaar/polytone'/name)
    result=dict(schema=1,status='provider breadth discovery;all semantic/runtime qualification incomplete',provider='polytone-Ty5Aowoi',artifactSha256=r['inputSha256'],generatorSha256=sha(Path(__file__)),privateInspectionReceiptSha256=sha(capture/'receipt.json'),registrationOrder=order,managers=managers,mixinDescriptors=descriptors,sources=sources,sharedQuestions=['Condition/priority decoding vs full/partial/disabled content decoding.','Directory aliases and pack stacks have distinct precedence;do not infer one universal priority.','Parallel preparation,barrier,ordered parse/apply and error aggregation differ from atomic publication.','Reset and log-off must preserve/retire each owned native/GPU resource under its actual consumer contract.','Configuration load/save,pack selection,late world/tag application and live controls need separate UX/effect traces.','Optional renderer integrations,model mixin overlap and later-version native data are not supplied by class presence.'],limits=['403 decompiled inspection files cover595 original class entries including nested classes;not matching upstream source or a verified compiler inverse.','Folder constants were independently found in corresponding original class entries;constructor/control-flow semantics remain inspection claims.','Method-name and consumer references are discovery locators,not completed semantic operations,reachable injection proofs or user commands.','Add-on manager registration remains an explicit extension boundary outside the28 built-in manager records.','This discovery collector executes no provider/game class;the separate priority band has its own explicit original-class adapter boundary.'])
    result['sharedPolicyEvidence']=[dict(component='per-ID priority and collection views',report='polytone-priority/README.md',conformance='evidence/polytone-priority-conformance.json',qualification='one-original-class-with-explicit-adapters;not-complete-manager-or-loader-qualification')]
    (HERE/'polytone-managers.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(managers=len(managers),sourceViews=len(sources),consumerReferences=sum(len(m['staticConsumerReferences']) for m in managers),allQualified=False)))


if __name__=='__main__':main()
