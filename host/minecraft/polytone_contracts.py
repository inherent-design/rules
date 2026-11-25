#!/usr/bin/env python3
"""Attribute manager inheritance and codec declaration locators, not complete schemas."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import zipfile

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
PHASES = ['earlyProcess', 'prepare', 'parseWithLevel', 'parseWithoutLevel', 'applyWithLevel', 'resetWithLevel']


def mask(text):
    """Preserve offsets while ignoring quoted/comment delimiters in these private views."""
    return re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/',
                  lambda m: re.sub(r'[^\n]', ' ', m[0]), text, flags=re.S)


def closing(clean, start):
    pairs = {'(': ')', '[': ']', '{': '}'}
    stack = [pairs[clean[start]]]
    for pos in range(start + 1, len(clean)):
        char = clean[pos]
        if char in pairs:
            stack.append(pairs[char])
        elif char in ')]}':
            assert char == stack.pop(), 'Unbalanced private view'
            if not stack:
                return pos
    raise ValueError('Unterminated private view delimiter')


def arguments(text, clean, start, end):
    positions = [start + 1]
    pos = start + 1
    while pos < end:
        if clean[pos] in '([{':
            pos = closing(clean, pos)
        elif clean[pos] == ',':
            positions.append(pos + 1)
        pos += 1
    return [text[a:b-1].strip() for a, b in zip(positions, positions[1:] + [end+1])]


def field_candidates(text):
    clean = mask(text)
    types = []
    for match in re.finditer(r'\b(?:class|interface|enum|record)\s+(\w+)', clean):
        start = clean.find('{', match.end())
        types.append((start, closing(clean, start), match[1]))
    rows = []
    for match in re.finditer(r'\.(fieldOf|optionalFieldOf|lenientOptionalFieldOf|field|optional)\s*\(', clean):
        kind = match[1]
        if kind in ['field', 'optional'] and 'import net.mehvahdjukaar.codecui.SchemaRecord;' not in text:
            continue
        start = clean.index('(', match.start())
        args = arguments(text, clean, start, closing(clean, start))
        literal = re.fullmatch(r'"([\w.-]+)"', args[0])
        scope = [name for a, b, name in sorted(types) if a < match.start() < b]
        row = dict(fieldName=literal[1] if literal else None, dynamicName=not bool(literal),
            callKind=kind, argumentCount=len(args), line=text[:match.start()].count('\n')+1,
            containingTypes=scope, qualification='lexical declaration locator; not a full codec path, overload resolution or runtime admission')
        default_index = 2 if kind == 'optional' and len(args) == 4 else 1 if kind in ['optionalFieldOf','lenientOptionalFieldOf'] and len(args) >= 2 else None
        if default_index is not None:
            default = args[default_index]
            row['defaultCandidate'] = default if re.fullmatch(r'(?:null|true|false|-?\d+(?:\.\d+)?[FfLlDd]?|(?:List|Set|Map)\.of\(\)|[\w.]+\.EMPTY)', default) else 'expression; inspect source/overload'
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['artifact', 'views', 'libraries']:
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--check',action='store_true',help='Compare the current public map instead of rewriting it.')
    args = parser.parse_args()
    breadth = json.loads((HERE/'polytone-managers.json').read_text())
    original = json.loads((args.views/'receipt.json').read_text())
    library_receipt = json.loads((args.libraries/'receipt.json').read_text())
    assert sha(args.artifact) == breadth['artifactSha256'] == original['inputSha256'] == library_receipt['parentSha256']
    assert original['exitCode'] == 0 and original['ownedGroupAbsent']
    assert sha(args.views/'receipt.json') == breadth['privateInspectionReceiptSha256']
    with zipfile.ZipFile(args.artifact) as archive:
        metadata = archive.read('META-INF/jarjar/metadata.json')
        assert hashlib.sha256(metadata).hexdigest() == library_receipt['metadataSha256'] == sha(args.libraries/'metadata.json')
        assert json.loads(metadata)['jars'] == [e['declaration'] for e in library_receipt['libraries']]
        for entry in library_receipt['libraries']:
            assert hashlib.sha256(archive.read(entry['declaration']['path'])).hexdigest() == entry['sha256']
    for name,value in library_receipt['producersSha256'].items():assert sha(args.libraries/name)==value
    library_sources = {}
    root = args.views/'source'
    sources = {}
    with zipfile.ZipFile(args.artifact) as archive:
        def remember(relative):
            path = root/relative
            assert sha(path) == original['viewsSha256'][relative]
            entry = relative.removesuffix('.java')+'.class'
            sources[relative] = dict(viewSha256=sha(path), originalClassEntry=entry,
                originalClassSha256=hashlib.sha256(archive.read(entry)).hexdigest(),
                qualification='private decompiled view; not upstream source or transformation proof')
            return relative
        def resolve(relative, symbol):
            text = (root/relative).read_text()
            imports = {x.rsplit('.',1)[-1]:x for x in re.findall(r'^import ([\w.]+);',text,re.M)}
            package = re.search(r'^package ([\w.]+);',text,re.M)[1]
            first, *tail = symbol.split('.')
            name = imports.get(first,package+'.'+first)
            candidate = name.replace('.','/')+'.java'
            if (root/candidate).exists():
                return dict(owner=name+''.join('.'+t for t in tail), source=remember(candidate), status='inspection view available')
            return dict(owner=name+''.join('.'+t for t in tail), source=None, status='external or unresolved; no unsupported inference')
        managers = []
        for m in sorted(breadth['managers'],key=lambda m:m['reloadOrder']):
            relative = remember(m['source']); text = (root/relative).read_text()
            base = re.search(r'public class \w+ extends (\w+)',text)[1]
            assert base in ['ContentManager','SingleFileContentManager']
            chain = [relative]
            if base == 'SingleFileContentManager':
                chain.append(remember('net/mehvahdjukaar/polytone/common/reloader/SingleFileContentManager.java'))
            chain.append(remember('net/mehvahdjukaar/polytone/common/reloader/ContentManager.java'))
            phases = {}
            for phase in PHASES:
                for owner in chain:
                    body = (root/owner).read_text(); clean = mask(body)
                    match = re.search(r'^   (?:public|protected) [^\n]+\b'+phase+r'\(',clean,re.M)
                    if match:
                        start = clean.index('{',match.end()); end = closing(clean,start)
                        phases[phase] = dict(source=owner,line=body[:match.start()].count('\n')+1,
                            inherited=owner!=relative,emptyBody=not clean[start+1:end].strip(),
                            bodySha256=hashlib.sha256(body[start:end+1].encode()).hexdigest(),
                            qualification='declared nearest implementation; not runtime dispatch, reachability, super-call or effect closure')
                        break
                assert phase in phases
                assert m['declaredPhaseOverrides'][phase] == (not phases[phase]['inherited'])
            references = sorted(set(re.findall(r'\b((?:[A-Za-z_]\w*\.)+[A-Za-z_]*CODEC\w*)\b',text)))
            bindings = [dict(reference=ref, **resolve(relative,ref.rsplit('.',1)[0])) for ref in references]
            managers.append(dict(id=m['id'],reloadOrder=m['reloadOrder'],source=relative,effectivePhases=phases,
                constructorCodecReferences=m['codecReferences'],managerFileCodecReferences=bindings,
                localCodecSymbolCandidates=sorted(set(re.findall(r'\b([A-Z_]*CODEC[A-Z_]*)\b',text))),
                limits=['References cover the manager file, including helpers; not every reference is its content codec.',
                        'Absent constructor codec does not imply absent grammar; bespoke paths and later decoder calls remain.']))
        definitions = {}
        for relative in list(sources):
            text = (root/relative).read_text()
            definitions[relative] = dict(fieldDeclarationCandidates=field_candidates(text),
                codecFamilyCalls=sorted(set(re.findall(r'\b(?:SchemaCodecs|Codec)\.(\w+)\(',text))),
                schemaRecordDeclared='SchemaRecord.create(' in text,
                limits=['Whole-file declarations include nested/helper codecs; containing type is a locator, not a merged object schema.',
                        'Indirect, recursive, dynamic-name, custom decoder, validation and dispatch semantics remain incomplete.'])
    libraries = []
    for entry in library_receipt['libraries']:
        artifact = args.libraries/'inputs'/Path(entry['declaration']['path']).name
        assert sha(artifact) == entry['sha256']
        command = entry['command']; assert command['exitCode'] == 0 and command['ownedGroupAbsent'] and not command['timedOut']
        java = Path(command['argv'][0]); tool = Path(command['argv'][command['argv'].index('-jar')+1])
        assert sha(java) == library_receipt['javaSha256'] and sha(java.parent.parent/'release') == library_receipt['jdkReleaseSha256']
        assert sha(tool) == library_receipt['decompilerSha256']
        for stream in ['stdout','stderr']:
            assert sha(args.libraries/(entry['declaration']['identifier']['artifact']+'.'+stream)) == command[stream+'Sha256']
        views = args.libraries/'source'/entry['declaration']['identifier']['artifact']
        assert {str(p.relative_to(views)) for p in views.rglob('*.java')} == set(entry['viewsSha256'])
        for name,value in entry['viewsSha256'].items(): assert sha(views/name) == value
        with zipfile.ZipFile(artifact) as archive:
            assert {name for name in archive.namelist() if name.endswith('.class')} == set(entry['classes'])
            for name,row in entry['classes'].items():
                data=archive.read(name); assert hashlib.sha256(data).hexdigest() == row['sha256']
                minor,major=struct.unpack('>HH',data[4:8]);assert minor==row['minor'] and major==row['major']
            if entry['declaration']['identifier']['artifact']=='codecui-neoforge':
                for name in ['SchemaRecord','SchemaCodec','Schema','SchemaCodecs','internal/SchemaResolver']:
                    relative='net/mehvahdjukaar/codecui/'+name+'.java';member=relative.removesuffix('.java')+'.class'
                    library_sources[relative]=dict(librarySha256=entry['sha256'],viewSha256=sha(views/relative),
                        originalClassEntry=member,originalClassSha256=hashlib.sha256(archive.read(member)).hexdigest(),
                        qualification='private original bundled-library decompilation; not source equivalence')
        libraries.append(dict(declaration=entry['declaration'],sha256=entry['sha256'],bytes=entry['bytes'],
            classEntries=len(entry['classes']),privateViews=len(entry['viewsSha256']),
            classVersions=sorted({str(c['major'])+'.'+str(c['minor']) for c in entry['classes'].values()}),
            nativePayloadCandidates=entry['nativePayloadCandidates'],nestedArchives=entry['nestedArchives'],
            runtimeSelectedVersion=None,status='bundled bytes inspected; effective runtime selection unobserved'))
    result = dict(schema=1,provider=breadth['provider'],artifactSha256=breadth['artifactSha256'],
        generatorSha256=sha(Path(__file__)),breadthSha256=sha(HERE/'polytone-managers.json'),
        originalReceiptSha256=sha(args.views/'receipt.json'),libraryReceiptSha256=sha(args.libraries/'receipt.json'),
        libraries=libraries,managers=managers,definitionLocators=definitions,sources=sources,librarySources=library_sources,
        codecUiPolicies=[
            dict(id='record-overloads',source='net/mehvahdjukaar/codecui/SchemaRecord.java',
                interpretation='Three-argument optional stores an Optional-returning MapCodec override. Four-argument optional stores a default. mapCodecFor uses the override first; otherwise a non-null optional default selects optionalFieldOf, and the remaining path selects fieldOf.'),
            dict(id='schema-metadata',source='net/mehvahdjukaar/codecui/SchemaRecord.java',
                interpretation='toSchemaField copies optional/default metadata independently of the actual MapCodec. The explicit MapCodec field overload also sets optional=true and default=null.'),
            dict(id='decode-and-schema',source='net/mehvahdjukaar/codecui/SchemaCodec.java',
                interpretation='Both wrappers delegate encode/decode to their underlying Codec. Lazy schema access invokes its schema supplier; schema access and value decoding are distinct operations.'),
            dict(id='inference-modes',source='net/mehvahdjukaar/codecui/SchemaCodecs.java',
                interpretation='inferenceMode reports construction-interception MIXIN or REFLECTION. The selected fixture supplies an explicit primitive schema and does not qualify either inference path.'),
            dict(id='inference-fallback',source='net/mehvahdjukaar/codecui/internal/SchemaResolver.java',
                interpretation='resolve bootstraps curated schemas, uses per-thread identity caching, and considers tags, custom handlers, structural and reflective paths. Field locators do not establish the active runtime inference result.')],
        limits=['All 28 managers remain incomplete; no provider/game installation or runtime capability qualification.',
                'Source-byte attribution does not establish decompilation equivalence or a complete schema/consumer graph.',
                'Bundled library negotiation is not a native resolved-graph observation.'])
    output=HERE/'polytone-contracts.json'
    if args.check:assert json.loads(output.read_text())==result,'Public manager/codec map differs from its inspected inputs'
    else:output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(managers=len(managers),phaseBindings=sum(len(m['effectivePhases']) for m in managers),
        inheritedBindings=sum(p['inherited'] for m in managers for p in m['effectivePhases'].values()),
        sourceFiles=len(sources),fieldLocators=sum(len(d['fieldDeclarationCandidates']) for d in definitions.values()),
        bundledLibraries=len(libraries),allQualified=False)))


if __name__ == '__main__':
    main()
