#!/usr/bin/env python3
"""Owner-run tiny constructed SpriteContents inputs; no generator/bake/game."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

from mappings import read

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "java"))
from arena_probe import command


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def cases():
    rows = [dict(id="static-2x2-" + str(mask), width=2, height=2, masks=[mask], aliasLifecycle=False) for mask in range(16)]
    rows += [dict(id="static-3x2-" + str(mask), width=3, height=2, masks=[mask], aliasLifecycle=False) for mask in [0, 5, 40, 45, 63]]
    rows += [dict(id="animated-2x2-" + str(i), width=2, height=2, masks=masks, aliasLifecycle=False)
             for i, masks in enumerate([[1, 8], [9, 6], [5, 10], [15, 0]])]
    rows += [dict(id="alias-mutation-close", width=2, height=2, masks=[0], aliasLifecycle=True)]
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["inputs", "java-inputs", "native-receipt", "private"]: parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.inputs.read_text())["profiles"]["1.21.1"]
    target = next(t for t in json.loads((HERE / "targets.json").read_text())["javaReferences"] if t["release"] == "1.21.1")
    client, metadata, mapping_path = (Path(plan[k]) for k in ["client", "metadata", "mappings"])
    assert sha(client) == target["source"]["clientSha256"] and sha(metadata) == target["source"]["metadataSha256"]
    libraries = json.loads(args.java_inputs.read_text())["libraries"]
    official = {r["name"]: r["downloads"]["artifact"] for r in json.loads(metadata.read_text())["libraries"]}
    assert len(libraries) == 11 and len({r["name"] for r in libraries}) == 11
    for lib in libraries:
        path = Path(lib["path"])
        assert sha(path) == lib["sha256"] and path.stat().st_size == lib["bytes"] == official[lib["name"]]["size"]
        assert hashlib.sha1(path.read_bytes()).hexdigest() == lib["sha1"] == official[lib["name"]]["sha1"]
    native = json.loads(args.native_receipt.read_text()); native_path = Path(native["nativePath"])
    assert sha(native_path) == native["nativeSha256"] and sha(Path(native["archivePath"])) == native["archiveSha256"]
    assert hashlib.sha1(Path(native["archivePath"]).read_bytes()).hexdigest() == official[native["library"]]["sha1"]
    with zipfile.ZipFile(native["archivePath"]) as archive: assert hashlib.sha256(archive.read(native["nativeMember"])).hexdigest() == native["nativeSha256"]
    mapping = read(mapping_path)
    names = dict(imageClass="com.mojang.blaze3d.platform.NativeImage", spriteClass="net.minecraft.client.renderer.texture.SpriteContents",
                 sizeClass="net.minecraft.client.resources.metadata.animation.FrameSize", metadataClass="net.minecraft.server.packs.resources.ResourceMetadata",
                 nameClass="net.minecraft.resources.ResourceLocation")
    b = {key: mapping[name]["name"] for key, name in names.items()}
    im, sp = mapping[names["imageClass"]]["methods"], mapping[names["spriteClass"]]["methods"]
    b.update(get=im["getPixelRGBA(int,int)"], set=im["setPixelRGBA(int,int,int)"], width=sp["width()"], height=sp["height()"],
             frames=sp["getUniqueFrames()"], transparent=sp["isTransparent(int,int,int)"], emptyMetadata=mapping[names["metadataClass"]]["fields"]["EMPTY"])
    forbidden = ["net.minecraft.client.Minecraft", "com.mojang.blaze3d.systems.RenderSystem", "net.minecraft.core.Direction",
                 "net.minecraft.network.codec.ByteBufCodecs", names["nameClass"]]
    forbidden = [mapping[name]["name"].replace(".", "/") for name in forbidden]
    jdk = Path("/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home")
    assert 'JAVA_VERSION="21.' in (jdk / "release").read_text()
    capture = args.private.resolve() / ("sprite-inputs-1.21.1-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")); capture.mkdir(parents=True)
    for name in ["classes", "home", "tmp"]: (capture / name).mkdir()
    sources = {"sprite_inputs_probe.py": Path(__file__), "SpriteInputsProbe.java": HERE / "SpriteInputsProbe.java", "mappings.py": HERE / "mappings.py",
               "arena_probe.py": HERE.parent / "java/arena_probe.py", "inputs.json": args.inputs, "java-inputs.json": args.java_inputs, "native-input.json": args.native_receipt}
    for name, path in sources.items(): shutil.copyfile(path, capture / name)
    (capture / "request.json").write_text(json.dumps(dict(schema=1, bindings=b, cases=cases()), indent=2) + "\n")
    with zipfile.ZipFile(client) as archive:
        entries = {name: hashlib.sha256(archive.read(original.replace(".", "/") + ".class")).hexdigest()
                   for name, original in ((name, mapping[name]["name"]) for name in names.values())}
    record = dict(schema=1, target=target["id"], release="1.21.1", clientSha256=sha(client), metadataSha256=sha(metadata), mappingSha256=sha(mapping_path),
                  originalClassSha256=entries, libraries=libraries, native=dict(path=str(native_path), sha256=sha(native_path), acquisitionSha256=sha(args.native_receipt)),
                  jdkReleaseSha256=sha(jdk / "release"), tools={n: dict(path=str(jdk / "bin" / n), sha256=sha(jdk / "bin" / n)) for n in ["java", "javac"]},
                  producerSha256={n: sha(capture / n) for n in sources}, requestSha256=sha(capture / "request.json"), commands=[],
                  forbiddenInitializers=forbidden, scope="Original constructed SpriteContents over <=8zeroedpixelwords;null name context adapter,explicit FrameSize,originalResourceMetadata.EMPTY. No identifier construction,metadata decode,ticker,generatedmodel,bake,GPU/game or whole sprite-loading qualification.")
    def save(): (capture / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
    env = dict(os.environ, TMPDIR=str(capture / "tmp"))
    startup = ["JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS", "CLASSPATH", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH", "DYLD_FALLBACK_LIBRARY_PATH"]
    record["removedChildEnvironmentKeys"] = [k for k in startup if k in env]
    for key in startup: env.pop(key, None)
    cp = os.pathsep.join([str(client)] + [lib["path"] for lib in libraries])
    save()
    compile_args = [str(jdk / "bin/javac"), "-J-XX:ActiveProcessorCount=2", "-J-Xmx96m", "--release", "21", "-proc:none", "-encoding", "UTF-8", "-Xlint:all,-classfile", "-Werror", "-cp", cp, "-d", str(capture / "classes"), str(capture / "SpriteInputsProbe.java")]
    record["commands"].append(command(compile_args, capture, "compile", env, 30)); save(); assert record["commands"][-1]["exitCode"] == 0, capture
    execute = [str(jdk / "bin/java"), "-XX:ActiveProcessorCount=2", "-Xmx96m", "-XX:MaxDirectMemorySize=16m", "-Djava.awt.headless=true",
               "-Duser.home=" + str(capture / "home"), "-Djava.io.tmpdir=" + str(capture / "tmp"),
               "-Dorg.lwjgl.librarypath=" + str(native_path.parent), "-Dorg.lwjgl.system.allocator=system",
               "-Xlog:library=debug,class+load=info,class+init=info:file=" + str(capture / "vm.log"),
               "-cp", os.pathsep.join([str(capture / "classes"), cp]), "study.minecraft.SpriteInputsProbe", str(capture / "request.json"), str(capture / "observed.json")]
    record["commands"].append(command(execute, capture, "execute", env, 30))
    record["outputs"] = {n: sha(capture / n) for n in ["observed.json", "vm.log"] if (capture / n).is_file()}
    record["helperClassesSha256"] = {str(p.relative_to(capture / "classes")): sha(p) for p in (capture / "classes").rglob("*.class")}
    record["exactCaptureProcessReadback"] = [line for line in subprocess.check_output(["ps", "-axo", "pid=,ppid=,pgid=,command="], text=True).splitlines() if str(capture) in line]
    initialized = re.findall(r"Initializing '([^']+)'", (capture / "vm.log").read_text()) if (capture / "vm.log").exists() else []
    record["forbiddenInitializersObserved"] = [name for name in initialized if any(name == bad or name.startswith(bad + "$") for bad in forbidden)]
    record["excludedLibraryInitializersObserved"] = [name for name in initialized if any(name.startswith(prefix) for prefix in ["org/lwjgl/stb/", "org/lwjgl/util/freetype/", "org/lwjgl/glfw/", "com/mojang/jtracy/"])]
    save()
    assert all(c["exitCode"] == 0 and c["ownedGroupAbsent"] and not c["timedOut"] for c in record["commands"]), capture
    assert not record["exactCaptureProcessReadback"] and not record["forbiddenInitializersObserved"] and not record["excludedLibraryInitializersObserved"], capture
    assert all(sha(capture / name) == digest for name, digest in record["producerSha256"].items()) and sha(client) == record["clientSha256"]
    assert sha(native_path) == record["native"]["sha256"] and all(sha(Path(lib["path"])) == lib["sha256"] for lib in libraries)
    output = json.loads((capture / "observed.json").read_text()); assert len(output["cases"]) == 26 and all(r["status"] == "returned" and r["imageFinalCloseReturned"] for r in output["cases"])
    (args.private / "latest-sprite-inputs-1.21.1.json").write_text(json.dumps(dict(capture=str(capture))) + "\n")
    print(json.dumps(dict(capture=str(capture), scenarios=26, groupsAbsent=True, forbiddenInitializersObserved=[])))


if __name__ == "__main__":
    main()
