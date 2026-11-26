#!/usr/bin/env python3
"""Owner-run 1.21.1 CPU-image fixture, one zero-initialized 2x2 allocation."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
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


def steps():
    rows = [dict(id="allocate-zeroed", operation="construct"), dict(id="get-zero", operation="get", x=0, y=0)]
    rows += [dict(id="set-" + str(i), operation="set", x=i % 2, y=i // 2, word=w)
             for i, w in enumerate(["12345678", "89abcdef", "ffffffff", "00000000"])]
    rows += [dict(id="get-last", operation="get", x=1, y=1),
             dict(id="get-negative-live", operation="get", x=-1, y=0),
             dict(id="set-outside-live", operation="set", x=2, y=0, word="aabbccdd"),
             dict(id="close", operation="close"),
             dict(id="get-closed", operation="get", x=0, y=0),
             dict(id="set-closed", operation="set", x=0, y=0, word="aabbccdd"),
             dict(id="get-outside-closed", operation="get", x=2, y=0),
             dict(id="set-negative-closed", operation="set", x=0, y=-1, word="aabbccdd"),
             dict(id="metadata-closed", operation="metadata"), dict(id="close-again", operation="close")]
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--java-inputs", type=Path, required=True)
    parser.add_argument("--native-receipt", type=Path, required=True)
    parser.add_argument("--private", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.inputs.read_text())["profiles"]["1.21.1"]
    target = next(t for t in json.loads((HERE / "targets.json").read_text())["javaReferences"] if t["release"] == "1.21.1")
    client, metadata, mappings = (Path(plan[k]) for k in ["client", "metadata", "mappings"])
    assert sha(client) == target["source"]["clientSha256"] and sha(metadata) == target["source"]["metadataSha256"]
    library_basis = json.loads(args.java_inputs.read_text())
    libraries = library_basis["libraries"]
    official = {x["name"]: x["downloads"]["artifact"] for x in json.loads(metadata.read_text())["libraries"]}
    for lib in libraries:
        path = Path(lib["path"])
        assert sha(path) == lib["sha256"] and path.stat().st_size == lib["bytes"] == official[lib["name"]]["size"]
        assert hashlib.sha1(path.read_bytes()).hexdigest() == lib["sha1"] == official[lib["name"]]["sha1"]
    native = json.loads(args.native_receipt.read_text())
    native_path = Path(native["nativePath"])
    assert sha(native_path) == native["nativeSha256"] and sha(Path(native["archivePath"])) == native["archiveSha256"]
    expected = official.get("org.lwjgl:lwjgl:3.3.3:natives-macos-arm64")
    assert expected and expected["sha1"] == native["source"]["sha1"] and expected["size"] == native["source"]["bytes"]
    jdk = Path("/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home")
    assert 'JAVA_VERSION="21.' in (jdk / "release").read_text()
    locators = read(mappings)
    image, fmt = (locators["com.mojang.blaze3d.platform.NativeImage" + suffix] for suffix in ["", "$Format"])
    methods = image["methods"]
    bindings = dict(imageClass=image["name"], formatClass=fmt["name"], width=methods["getWidth()"],
                    height=methods["getHeight()"], format=methods["format()"],
                    get=methods["getPixelRGBA(int,int)"], set=methods["setPixelRGBA(int,int,int)"])
    capture = args.private.resolve() / ("native-image-1.21.1-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    capture.mkdir(parents=True)
    for name in ["classes", "home", "tmp"]: (capture / name).mkdir()
    inputs = {"inputs.json": args.inputs, "java-inputs.json": args.java_inputs, "native-input.json": args.native_receipt,
              "native_image_probe.py": Path(__file__), "NativeImageProbe.java": HERE / "NativeImageProbe.java",
              "mappings.py": HERE / "mappings.py", "arena_probe.py": HERE.parent / "java/arena_probe.py"}
    for name, path in inputs.items(): shutil.copyfile(path, capture / name)
    request = dict(schema=1, bindings=bindings, steps=steps())
    (capture / "request.json").write_text(json.dumps(request, indent=2) + "\n")
    with zipfile.ZipFile(client) as archive:
        classes = {name: hashlib.sha256(archive.read(name.replace(".", "/") + ".class")).hexdigest()
                   for name in [image["name"], fmt["name"]]}
    record = dict(schema=1, release="1.21.1", target=target["id"], clientSha256=sha(client), metadataSha256=sha(metadata),
                  mappingSha256=sha(mappings), originalClasses=classes, libraries=libraries,
                  native=dict(path=str(native_path), sha256=sha(native_path), acquisitionSha256=sha(args.native_receipt)),
                  jdkReleaseSha256=sha(jdk / "release"),
                  tools={n: dict(path=str(jdk / "bin" / n), sha256=sha(jdk / "bin" / n)) for n in ["java", "javac"]},
                  producerSha256={name: sha(capture / name) for name in inputs}, requestSha256=sha(capture / "request.json"),
                  scope="One original zeroed2x2 RGBA CPU image;opaque32bit pixel API words,bounds,close and metadata. No decoder/STB/free-type/GPU/game/raw-pointer/physical-memory claim.",
                  commands=[])
    def save(): (capture / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
    env = dict(os.environ, TMPDIR=str(capture / "tmp"))
    startup_keys = ["JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH", "DYLD_FALLBACK_LIBRARY_PATH", "CLASSPATH"]
    record["removedChildEnvironmentKeys"] = [key for key in startup_keys if key in env]
    for key in startup_keys: env.pop(key, None)
    cp = os.pathsep.join([str(client)] + [lib["path"] for lib in libraries])
    save()
    compile_args = [str(jdk / "bin/javac"), "-J-XX:ActiveProcessorCount=2", "-J-Xmx96m", "--release", "21", "-proc:none", "-Xlint:all,-classfile", "-Werror", "-encoding", "UTF-8", "-cp", cp, "-d", str(capture / "classes"), str(capture / "NativeImageProbe.java")]
    record["commands"].append(command(compile_args, capture, "compile", env, 30)); save()
    assert record["commands"][-1]["exitCode"] == 0, capture
    execute = [str(jdk / "bin/java"), "-XX:ActiveProcessorCount=2", "-Xmx96m", "-Djava.awt.headless=true",
               "-Duser.home=" + str(capture / "home"), "-Djava.io.tmpdir=" + str(capture / "tmp"),
               "-Dorg.lwjgl.librarypath=" + str(native_path.parent), "-Dorg.lwjgl.system.allocator=system",
               "-Xlog:library=debug,class+load=info,class+init=info:file=" + str(capture / "vm.log"),
               "-cp", os.pathsep.join([str(capture / "classes"), cp]), "study.minecraft.NativeImageProbe",
               str(capture / "request.json"), str(capture / "observed.json")]
    record["commands"].append(command(execute, capture, "execute", env, 30))
    record["outputs"] = {name: sha(capture / name) for name in ["observed.json", "vm.log"] if (capture / name).is_file()}
    record["observerClasses"] = {str(p.relative_to(capture / "classes")): sha(p) for p in (capture / "classes").rglob("*.class")}
    record["processReadback"] = subprocess.check_output(["ps", "-axo", "pid=,ppid=,pgid=,command="], text=True)
    # Only matching rows enter the retained receipt, not unrelated personal process data.
    record["processReadback"] = [line for line in record["processReadback"].splitlines() if str(capture) in line]
    save()
    assert all(c["exitCode"] == 0 and c["ownedGroupAbsent"] and not c["timedOut"] for c in record["commands"]), capture
    assert not record["processReadback"], capture
    assert all(sha(capture / name) == digest for name, digest in record["producerSha256"].items())
    assert sha(client) == record["clientSha256"] and sha(native_path) == record["native"]["sha256"]
    assert all(sha(Path(lib["path"])) == lib["sha256"] for lib in libraries)
    observed = json.loads((capture / "observed.json").read_text())
    assert [s["id"] for s in request["steps"]] == [r["id"] for r in observed["events"]]
    assert observed["finallyCloseReturned"] is True
    (args.private / "latest-native-image-1.21.1.json").write_text(json.dumps(dict(capture=str(capture))) + "\n")
    print(json.dumps(dict(capture=str(capture), steps=len(observed["events"]), groupsAbsent=True)))


if __name__ == "__main__":
    main()
