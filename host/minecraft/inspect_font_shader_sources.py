#!/usr/bin/env python3
"""Bounded private font/language/shader source inspection from existing selected inputs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile
from mappings import read

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'java'))
from arena_probe import command
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
PREFIXES = ['net.minecraft.client.gui.font.', 'com.mojang.blaze3d.font.', 'net.minecraft.client.resources.language.',
            'net.minecraft.client.resources.metadata.language.', 'com.mojang.blaze3d.shaders.', 'com.mojang.blaze3d.preprocessor.']
ROOTS = ['net.minecraft.locale.Language', 'net.minecraft.client.StringSplitter', 'net.minecraft.client.gui.Font',
         'net.minecraft.client.renderer.ShaderManager', 'net.minecraft.client.renderer.ShaderInstance',
         'net.minecraft.client.renderer.EffectInstance', 'net.minecraft.client.renderer.PostChain',
         'net.minecraft.client.renderer.PostChainConfig', 'net.minecraft.client.renderer.PostPass',
         'net.minecraft.client.renderer.ShaderDefines', 'net.minecraft.client.renderer.RenderPipelines']
DEPENDENCIES = ['net.minecraft.client.renderer.'+n for n in
                ['ShaderProgramConfig','ShaderProgram','CompiledShader','CompiledShaderProgram','CoreShaders','UniformValue']]
LIFETIMES = ['com.mojang.blaze3d.pipeline.PipelineCache','com.mojang.renderpearl.api.device.GpuDevice',
             'com.mojang.renderpearl.api.pipeline.CompiledRenderPipeline','com.mojang.renderpearl.frontend.shaders.GlslCompiler']
TEXT_DESCRIPTIONS = ['net.minecraft.network.chat.Style','net.minecraft.network.chat.FontDescription','net.minecraft.client.gui.GlyphSource']


def selected(name):
    return (any(name.startswith(p) for p in PREFIXES) or any(name == r or name.startswith(r+'$') for r in ROOTS)
            or ('Shader' in name and name.startswith('com.mojang.renderpearl.'))) and not name.endswith('package-info')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', choices=['1.21.1','1.21.4','1.21.5','1.21.11','26.3'], required=True)
    p.add_argument('--surface', choices=['font-shader','shader-dependencies','shader-lifetimes','text-descriptions'], default='font-shader')
    for name in ['client','metadata','jdk','decompiler','private']:
        p.add_argument('--'+name, type=Path, required=True)
    for name in ['named','mappings']:
        p.add_argument('--'+name, type=Path)
    a = p.parse_args(); target = next(t for t in json.loads((HERE/'targets.json').read_text())['javaReferences'] if t['release'] == a.version)
    assert sha(a.client) == target['source']['clientSha256'] and sha(a.metadata) == target['source']['metadataSha256']
    metadata = json.loads(a.metadata.read_text())
    assert sha(a.decompiler) == '1dfcfe974395734fa467ce620661c7623d05ba83670de0529b1fbd63ff548b9d'
    jdk = a.jdk.resolve(); assert 'JAVA_VERSION="25.' in (jdk/'release').read_text()
    if a.version == '26.3':
        assert a.named is None and a.mappings is None; named = a.client; mapping = None
    else:
        assert a.named and a.mappings
        assert hashlib.sha1(a.mappings.read_bytes()).hexdigest() == metadata['downloads']['client_mappings']['sha1']
        named = a.named; mapping = read(a.mappings)
    prefix = {'font-shader':'font-shader-views','shader-dependencies':'font-shader-dependencies','shader-lifetimes':'font-shader-lifetimes','text-descriptions':'text-description-views'}[a.surface]
    cap = a.private.resolve()/(prefix+'-'+a.version+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')); cap.mkdir(parents=True)
    for n in ['classes','source','tmp','home']: (cap/n).mkdir()
    for src in [Path(__file__), HERE/'mappings.py', HERE.parent/'java/arena_probe.py']: shutil.copyfile(src, cap/src.name)
    original = {}; inspection = {}
    with zipfile.ZipFile(a.client) as source, zipfile.ZipFile(named) as archive:
        for member in archive.namelist():
            if not member.endswith('.class'): continue
            name = member[:-6].replace('/','.')
            if a.surface == 'font-shader':
                if not selected(name): continue
            elif not any(name == root or name.startswith(root+'$') for root in {'shader-dependencies':DEPENDENCIES,'shader-lifetimes':LIFETIMES,'text-descriptions':TEXT_DESCRIPTIONS}[a.surface]): continue
            binary = mapping[name]['name'].replace('.','/')+'.class' if mapping else member
            original[name] = dict(member=binary, sha256=hashlib.sha256(source.read(binary)).hexdigest())
            path = cap/'classes'/member; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(archive.read(member)); inspection[member] = sha(path)
    assert (50 <= len(original) <= 260) if a.surface == 'font-shader' else (1 <= len(original) <= 50)
    receipt = dict(schema=1, target=target['id'], selectedRelease=a.version, surface=a.surface, clientSha256=sha(a.client), metadataSha256=sha(a.metadata),
        mappingSha256=sha(a.mappings) if mapping else None, namedJarSha256=sha(named), toolSha256=sha(a.decompiler),
        javaSha256=sha(jdk/'bin/java'), jdkReleaseSha256=sha(jdk/'release'),
        producersSha256={n:sha(cap/n) for n in ['inspect_font_shader_sources.py','mappings.py','arena_probe.py']},
        originalClassMembers=original, inspectionClassSha256=inspection,
        scope='Private static source inspection only; no original class linking,initialization,font rasterization,shader compilation,game or backend execution.')
    (cap/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    argv = [str(jdk/'bin/java'),'-XX:ActiveProcessorCount=2','-Xmx384m','-Djava.awt.headless=true',
            '-Duser.home='+str(cap/'home'),'-Djava.io.tmpdir='+str(cap/'tmp'),'-jar',str(a.decompiler.resolve()),
            '--folder','--log-level=WARN','--add-external='+str(named.resolve()),str(cap/'classes'),str(cap/'source')]
    result = command(argv,cap,'inspect',dict(os.environ,TMPDIR=str(cap/'tmp')),90)
    receipt.update(command=result,viewsSha256={str(p.relative_to(cap/'source')):sha(p) for p in (cap/'source').rglob('*.java')},
        limits=['Original/named class pairing and source hashes attribute inspection; renaming/decompilation are not verified translations.',
                'Selected roots are an inspection slice,not exhaustive consumer/native-effect closure.',
                'Tool heap384MiB/processors2 are settings,not physical memory or host-wide bounds. Private inputs/views remain retained.'])
    (cap/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    assert result['exitCode'] == 0 and result['ownedGroupAbsent'] and not result['timedOut']
    assert sha(a.client) == target['source']['clientSha256'] and sha(named) == receipt['namedJarSha256']
    assert all(sha(cap/n) == h for n,h in receipt['producersSha256'].items())
    (a.private/('latest-'+prefix+'-'+a.version+'.json')).write_text(json.dumps(dict(capture=str(cap)))+'\n')
    print(json.dumps(dict(capture=str(cap),classes=len(original),views=len(receipt['viewsSha256']),groupAbsent=True)))


if __name__ == '__main__': main()
