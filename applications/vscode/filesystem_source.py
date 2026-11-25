"""Run pinned capability method fragments, not a VS Code instance or its RPC layer."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
COMMIT = '8a14f0cc1b08d531eb83255ea3764ae22aa932b5'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def body(text, marker):
    start = text.index(marker)
    opening = text.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[opening + 1:end - 1]


def main():
    run = ROOT / 'applications/evidence/vscode-filesystem-source'
    run.mkdir(exist_ok=True)
    acquired = json.loads((ROOT / 'applications/sources/vscode-filesystem-selections.json').read_text())['sources']
    excerpts = {}
    for entry in acquired:
        path = ROOT / entry['cache']
        assert sha(path) == entry['sha256'] and entry['commit'] == COMMIT
        excerpts[Path(entry['path']).name] = path.read_text()
    bridge = excerpts['mainThreadFileSystem.ts']
    line = next(x.strip() for x in bridge.splitlines() if 'onDidChangeFileSystemProviderRegistrations(e =>' in x)
    current = line.split('Registrations(', 1)[1].removesuffix('));')
    assert current.endswith('null)')
    candidate = current.replace('e.provider?.capabilities ?? null', 'e.added ? (e.provider?.capabilities ?? null) : null')
    assert candidate != current
    accept = body(excerpts['extHostFileSystemInfo.ts'], '$acceptProviderInfos(')
    get = body(excerpts['extHostFileSystemInfo.ts'], 'getCapabilities(')
    writable = body(excerpts['extHostFileSystemConsumer.ts'], 'isWritableFileSystem(')
    masks = {}
    for name in ['FileReadWrite', 'PathCaseSensitive', 'Readonly']:
        shift = int(re.search(r'\b' + name + r' = 1 << (\d+)', excerpts['files.ts'])[1])
        masks[name] = 1 << shift
    assert masks == dict(FileReadWrite=2, PathCaseSensitive=1024, Readonly=2048)
    notice = ('/* Selected Microsoft VS Code method bodies. Copyright (c) Microsoft Corporation.\n'
              ' * MIT license: ../../sources/licenses/vscode-MIT.txt.\n'
              ' * Study scaffolding and the explicitly labeled candidate are new. */\n')
    js = notice + "const files = {FileSystemProviderCapabilities:" + json.dumps(masks) + "};\n"
    js += 'const URI={from:x=>x};\n'
    js += 'function run(candidate){\nconst store={_providerInfo:new Map(),\n'
    js += '$acceptProviderInfos(uri,capabilities){' + accept + '},\ngetCapabilities(scheme){' + get + '}};\n'
    js += 'const fileSystemInfo=store,infoProxy=store;\n'
    js += 'const writable=function(scheme){' + writable + '};\n'
    js += 'const current=' + current + ';\nconst proposed=' + candidate + ';\n'
    js += '''const callback=candidate?proposed:current;
const trace=[];
for(const event of [
 {id:'add-writable',added:true,scheme:'fixture',provider:{capabilities:1026}},
 {id:'remove-writable',added:false,scheme:'fixture',provider:{capabilities:1026}},
 {id:'add-readonly',added:true,scheme:'fixture',provider:{capabilities:3074}},
 {id:'other-scheme',added:true,scheme:'other',provider:{capabilities:1026}},
 {id:'remove-readonly',added:false,scheme:'fixture',provider:{capabilities:3074}},
 {id:'absent-provider-removal',added:false,scheme:'fixture'}
]){callback(event);trace.push({event,known:store.getCapabilities(event.scheme)!==undefined,
 writable:writable(event.scheme)??null,fixtureWritable:writable('fixture')??null});}
return trace;
}
console.log(JSON.stringify({schema:1,current:run(false),proposed:run(true)},null,2));
'''
    path = run / 'fragment.cjs'
    path.write_text(js)
    result = subprocess.run(['node', str(path)], check=True, capture_output=True)
    (run / 'observed.json').write_bytes(result.stdout)
    (run / 'stderr.txt').write_bytes(result.stderr)
    ranges = {
        'mainThreadFileSystem.ts': [(28, 46)],
        'extHostFileSystemInfo.ts': [(37, 51)],
        'extHostFileSystemConsumer.ts': [(90, 123), (151, 159), (249, 255)],
        'fileService.ts': [(52, 87), (1521, 1537)],
        'extHostFileSystem.ts': [(132, 240)],
        'files.ts': [(599, 635)],
    }
    for entry in acquired:
        name = Path(entry['path']).name
        lines = excerpts[name].splitlines(keepends=True)
        entry['inspection'] = 'Selected registration/capability/write contract ranges only; see excerpts.'
        entry['ranges'] = ranges[name]
        selected = ''.join(f'\n// Original lines {a}-{b}\n' + ''.join(lines[a-1:b]) for a, b in ranges[name])
        target = run / (name + '.txt')
        target.write_text(notice + selected)
        entry['excerpt'] = str(target.relative_to(ROOT))
        entry['excerptSha256'] = sha(target)
    (run / 'sources.json').write_text(json.dumps(acquired, indent=2) + '\n')
    receipt = {'schema': 1, 'kind': 'selected-source-methods-with-adapters',
               'producerSha256': sha(Path(__file__)), 'fragmentSha256': sha(path),
               'observedSha256': sha(run / 'observed.json'), 'masks': masks,
               'node': subprocess.check_output(['node', '--version'], text=True).strip(),
               'nodeExecutableSha256': sha(Path(shutil.which('node')).resolve()),
               'adapters': ['URI.from identity', 'real JavaScript Map', 'ordinary serialized event list; removal includes historical provider',
                            'candidate changes one expression; not a patched VS Code product'],
               'exitCode': result.returncode}
    (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
