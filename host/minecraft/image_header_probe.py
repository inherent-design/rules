#!/usr/bin/env python3
"""Owner-run original PNG-header methods on <=33-byte buffers, never decoding images."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import zipfile
import zlib

from mappings import read

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "java"))
from arena_probe import command


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def cases():
    rows = []
    def add(name, *, width=2, height=3, depth=8, color=6, compression=0, filter=0, interlace=0,
            limit=33, position=0, order="LITTLE_ENDIAN", read_only=False, offset=None, value=None):
        body = struct.pack(">IiiBBBBB", 1229472850, width, height, depth, color, compression, filter, interlace)
        data = bytearray(bytes.fromhex("89504e470d0a1a0a") + struct.pack(">I", 13) + body + struct.pack(">I", zlib.crc32(body)))
        if offset is not None: data[offset] = value
        assert len(data) == 33 and 0 <= position <= limit <= 33
        rows.append(dict(id=name, hex=data.hex(), limit=limit, position=position, order=order, readOnly=read_only))
    add("valid-prefix")
    for limit in [0, 7, 8, 11, 12, 15, 16, 25, 26, 32]: add("limit-" + str(limit), limit=limit)
    add("bad-magic", offset=0, value=0)
    add("bad-length", offset=11, value=12)
    add("bad-type", offset=12, value=0)
    add("zero-width", width=0)
    add("negative-height", height=-1)
    add("invalid-depth", depth=3)
    add("invalid-color", color=1)
    add("incompatible-depth-color", depth=1, color=6)
    add("depth16-small", depth=16)
    add("depth16-int-overflow", depth=16, width=16384, height=16384)
    add("depth16-long-wrap-negative", depth=16, width=1073741825, height=2147483646)
    add("depth16-long-wrap-positive", depth=16, width=1073763824, height=2147439649)
    add("bad-crc", offset=32, value=0)
    add("nonzero-compression", compression=99)
    add("nonzero-filter", filter=99)
    add("nonzero-interlace", interlace=99)
    add("readonly-valid", read_only=True)
    add("readonly-bad-magic", read_only=True, offset=0, value=0)
    add("big-endian-valid", order="BIG_ENDIAN")
    add("big-endian-bad-magic", order="BIG_ENDIAN", offset=0, value=0)
    add("position-32", position=32)
    add("limit16-position15", limit=16, position=15)
    return rows


def arithmetic():
    return [dict(id=name, width=w, height=h) for name, w, h in [
        ("small", 2, 3), ("int-overflow", 16384, 16384),
        ("long-wrap-negative", 1073741825, 2147483646),
        ("long-wrap-positive", 1073763824, 2147439649)]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=["1.21.1", "1.21.4", "1.21.5", "1.21.11", "26.3", "java17"], required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--private", type=Path, required=True)
    args = parser.parse_args()
    primitive = args.version == "java17"
    plan = {} if primitive else json.loads(args.inputs.read_text())["profiles"][args.version]
    major = "17" if primitive else "25" if args.version == "26.3" else "21"
    jdk = Path("/Library/Java/JavaVirtualMachines/temurin-" + major + ".jdk/Contents/Home") if major != "25" else Path(plan["jdk"])
    assert f'JAVA_VERSION="{major}.' in (jdk / "release").read_text()
    client = Path(plan["client"]) if not primitive else None
    target = None if primitive else next(t for t in json.loads((HERE / "targets.json").read_text())["javaReferences"] if t["release"] == args.version)
    if target:
        assert sha(client) == target["source"]["clientSha256"]
        assert sha(Path(plan["metadata"])) == target["source"]["metadataSha256"]
    mapping_path = Path(plan["mappings"]) if "mappings" in plan else None
    owner = "net.minecraft.util.PngInfo"
    mapping = read(mapping_path)[owner] if mapping_path else None
    original = mapping["name"] if mapping else owner
    method = mapping["methods"]["validateHeader(java.nio.ByteBuffer)"] if mapping else "validateHeader"
    gson_basis = ROOT / ".build/minecraft/resource-cache-20261125T195402530738Z/receipt.json"
    gson = json.loads(gson_basis.read_text())["libraries"][0]
    assert gson["name"] == "com.google.code.gson:gson:2.10.1" and sha(Path(gson["path"])) == gson["sha256"]
    capture = args.private.resolve() / ("image-header-" + args.version + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    capture.mkdir(parents=True)
    for name in ["classes", "home", "tmp"]: (capture / name).mkdir()
    for path in [Path(__file__), HERE / "ImageHeaderProbe.java", HERE / "mappings.py", HERE.parent / "java/arena_probe.py"]: shutil.copyfile(path, capture / path.name)
    shutil.copyfile(args.inputs, capture / "inputs.json")
    request = dict(schema=1, cases=[] if primitive else cases(), arithmetic=arithmetic() if args.version in ["java17", "1.21.1", "26.3"] else [])
    if not primitive: request.update(className=original, methodName=method)
    (capture / "request.json").write_text(json.dumps(request, indent=2) + "\n")
    class_digest = None
    if client:
        with zipfile.ZipFile(client) as archive: class_digest = hashlib.sha256(archive.read(original.replace(".", "/") + ".class")).hexdigest()
    record = dict(schema=1, release=args.version, target=target["id"] if target else "java17-primitives", clientSha256=sha(client) if client else None,
        metadataSha256=sha(Path(plan["metadata"])) if client else None, mappingSha256=sha(mapping_path) if mapping_path else None,
        originalClass=original if client else None, originalClassSha256=class_digest, gson=gson, gsonBasisSha256=sha(gson_basis),
        tools={name: dict(path=str(jdk / "bin" / name), sha256=sha(jdk / "bin" / name)) for name in ["java", "javac"]}, jdkReleaseSha256=sha(jdk / "release"),
        producerSha256={name: sha(capture / name) for name in ["image_header_probe.py", "ImageHeaderProbe.java", "mappings.py", "arena_probe.py", "inputs.json"]},
        requestSha256=sha(capture / "request.json"), commands=[],
        scope="Original header method on authored <=33-byte heap buffers and JDK arithmetic; no PNG decode/STB/NativeImage/native allocation/upload/game/bootstrap.")
    def save(): (capture / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
    save()
    env = dict(os.environ, TMPDIR=str(capture / "tmp"))
    classpath = os.pathsep.join(([str(client.resolve())] if client else []) + [gson["path"]])
    compile_args = [str(jdk / "bin/javac"), "-J-XX:ActiveProcessorCount=2", "-J-Xmx96m", "--release", major, "-proc:none", "-Xlint:all,-classfile", "-Werror", "-cp", classpath, "-d", str(capture / "classes"), str(capture / "ImageHeaderProbe.java")]
    record["commands"].append(command(compile_args, capture, "compile", env, 30)); save()
    assert record["commands"][-1]["exitCode"] == 0, capture
    execute = [str(jdk / "bin/java"), "-XX:ActiveProcessorCount=2", "-Xmx96m", "-Djava.awt.headless=true", "-Duser.home=" + str(capture / "home"), "-Djava.io.tmpdir=" + str(capture / "tmp"), "-Xlog:class+load=info:file=" + str(capture / "class-load.log"), "-cp", os.pathsep.join([str(capture / "classes"), classpath]), "study.minecraft.ImageHeaderProbe", str(capture / "request.json"), str(capture / "observed.json")]
    record["commands"].append(command(execute, capture, "execute", env, 30))
    for name in ["observed.json", "class-load.log"]:
        if (capture / name).is_file(): record[name + "Sha256"] = sha(capture / name)
    record["observerClassSha256"] = {str(p.relative_to(capture / "classes")): sha(p) for p in (capture / "classes").rglob("*.class")}
    save()
    assert all(c["exitCode"] == 0 and c["ownedGroupAbsent"] and not c["timedOut"] for c in record["commands"]), capture
    assert all(sha(capture / name) == value for name, value in record["producerSha256"].items())
    assert sha(capture / "request.json") == record["requestSha256"] and (not client or sha(client) == record["clientSha256"])
    observed = json.loads((capture / "observed.json").read_text())
    assert [r["id"] for r in request["cases"]] == [r["id"] for r in observed["cases"]]
    assert [r["id"] for r in request["arithmetic"]] == [r["id"] for r in observed["arithmetic"]]
    (args.private / ("latest-image-header-" + args.version + ".json")).write_text(json.dumps(dict(capture=str(capture))) + "\n")
    print(json.dumps(dict(capture=str(capture), calls=len(observed["cases"]), arithmetic=len(observed["arithmetic"]), groupsAbsent=True)))


if __name__ == "__main__":
    main()
