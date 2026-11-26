#!/usr/bin/env python3
"""Audit/export constructed sprite observations; no Java, image, or game run."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
from urllib.parse import unquote, urlparse
import zipfile

from mappings import read
from sprite_inputs_probe import cases

HERE = Path(__file__).resolve().parent


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def observe(spec, raw, index):
    assert raw["id"] == spec["id"] and raw["status"] == "returned" and raw["imageFinalCloseReturned"] is True
    assert type(raw["width"]) is int and type(raw["height"]) is int
    assert all(type(n) is int for n in raw["uniqueFrames"]) and len(raw["uniqueFrames"]) in [1, 2]
    matrices = raw["matrices"]
    assert [m["frame"] for m in matrices] == raw["uniqueFrames"]
    assert all(type(m["frame"]) is int and len(m["transparent"]) == raw["width"] * raw["height"]
               and all(type(cell) is bool for cell in m["transparent"]) for m in matrices)
    alias = None
    if spec["aliasLifecycle"]:
        assert raw["spriteExplicitCloseReturned"] is True and type(raw["beforeMutation"]) is type(raw["afterMutation"]) is bool
        assert type(raw["widthAfterClose"]) is int and type(raw["heightAfterClose"]) is int
        assert all(type(n) is int for n in raw["framesAfterClose"])
        errors = {"returned": 0, "java.lang.IllegalStateException": 2}
        alias = {k: raw[k] for k in ["beforeMutation", "afterMutation", "widthAfterClose", "heightAfterClose", "framesAfterClose"]}
        alias.update(inputError=errors[raw["inputImageAfterSpriteClose"]], spriteError=errors[raw["spriteAfterClose"]])
    else:
        assert raw["spriteCleanupReturned"] is True and "beforeMutation" not in raw and "spriteExplicitCloseReturned" not in raw
    return dict(id=index, width=raw["width"], height=raw["height"], uniqueFrames=raw["uniqueFrames"], matrices=matrices, aliasState=alias)


def audit(private, export=False):
    capture = Path(json.loads((private / "latest-sprite-inputs-1.21.1.json").read_text())["capture"])
    r, request, output = [json.loads((capture / name).read_text()) for name in ["receipt.json", "request.json", "observed.json"]]
    assert r["schema"] == request["schema"] == output["schema"] == 1 and r["release"] == "1.21.1"
    assert request["cases"] == cases() and len(output["cases"]) == 26
    for i, (spec, raw) in enumerate(zip(request["cases"], output["cases"], strict=True)): observe(spec, raw, i)
    assert output["nameContext"] == "null adapter;no identifier construction" and output["metadataContext"] == "original ResourceMetadata.EMPTY;no metadata parsing"
    assert output["javaVersion"] == "21.0.13.1" and output["os"] == "Mac OS X" and output["architecture"] == "aarch64" and output["originalSigners"] == 4
    for name, digest in r["producerSha256"].items(): assert sha(capture / name) == digest
    for name, path in [("sprite_inputs_probe.py", HERE / "sprite_inputs_probe.py"), ("SpriteInputsProbe.java", HERE / "SpriteInputsProbe.java"),
                       ("mappings.py", HERE / "mappings.py"), ("arena_probe.py", HERE.parent / "java/arena_probe.py")]:
        assert sha(path) == r["producerSha256"][name]
    assert sha(capture / "request.json") == r["requestSha256"]
    for name, digest in r["outputs"].items(): assert sha(capture / name) == digest
    for name, digest in r["helperClassesSha256"].items(): assert sha(capture / "classes" / name) == digest
    for tool in r["tools"].values(): assert sha(Path(tool["path"])) == tool["sha256"]
    jdk = Path(r["tools"]["java"]["path"]).parents[1]
    assert sha(jdk / "release") == r["jdkReleaseSha256"]
    plan = json.loads((capture / "inputs.json").read_text())["profiles"]["1.21.1"]
    client, metadata, mapping_path = (Path(plan[k]) for k in ["client", "metadata", "mappings"])
    target = next(t for t in json.loads((HERE / "targets.json").read_text())["javaReferences"] if t["release"] == "1.21.1")
    assert sha(client) == r["clientSha256"] == target["source"]["clientSha256"]
    assert sha(metadata) == r["metadataSha256"] == target["source"]["metadataSha256"] and sha(mapping_path) == r["mappingSha256"]
    mapping = read(mapping_path)
    official = {row["name"]: row["downloads"]["artifact"] for row in json.loads(metadata.read_text())["libraries"]}
    for lib in r["libraries"]:
        path = Path(lib["path"])
        assert sha(path) == lib["sha256"] and path.stat().st_size == lib["bytes"] == official[lib["name"]]["size"]
        assert hashlib.sha1(path.read_bytes()).hexdigest() == lib["sha1"] == official[lib["name"]]["sha1"]
    native = json.loads((capture / "native-input.json").read_text())
    assert sha(capture / "native-input.json") == r["native"]["acquisitionSha256"]
    assert sha(Path(native["nativePath"])) == native["nativeSha256"] == r["native"]["sha256"]
    assert sha(Path(native["archivePath"])) == native["archiveSha256"] and hashlib.sha1(Path(native["archivePath"]).read_bytes()).hexdigest() == official[native["library"]]["sha1"]
    with zipfile.ZipFile(native["archivePath"]) as archive: assert hashlib.sha256(archive.read(native["nativeMember"])).hexdigest() == native["nativeSha256"]
    log = (capture / "vm.log").read_text(); loaded, libraries = [], []
    for line in log.splitlines():
        if " source: file:" in line:
            before, uri = line.split(" source: ", 1)
            if Path(unquote(urlparse(uri).path)).resolve() == client.resolve(): loaded.append(before.split("[class,load]")[-1].strip())
        if "Loaded library " in line: libraries.append(line.split("Loaded library ", 1)[1].split(", handle ")[0])
    with zipfile.ZipFile(client) as archive:
        loaded_hashes = {name: hashlib.sha256(archive.read(name.replace(".", "/") + ".class")).hexdigest() for name in loaded}
        for name, digest in r["originalClassSha256"].items():
            assert hashlib.sha256(archive.read(mapping[name]["name"].replace(".", "/") + ".class")).hexdigest() == digest
    assert output["spriteClass"] == request["bindings"]["spriteClass"] in loaded
    initialized = re.findall(r"Initializing '([^']+)'", log)
    bad = [name for name in initialized if any(name == prefix or name.startswith(prefix + "$") for prefix in r["forbiddenInitializers"])]
    excluded = [name for name in initialized if any(name.startswith(prefix) for prefix in ["org/lwjgl/stb/", "org/lwjgl/util/freetype/", "org/lwjgl/glfw/", "com/mojang/jtracy/"])]
    assert bad == r["forbiddenInitializersObserved"] == [] and excluded == r["excludedLibraryInitializersObserved"] == []
    assert "org/lwjgl/system/MemoryManage$StdlibAllocator" in initialized
    assert native["nativePath"] in libraries and all(Path(path).is_relative_to(jdk) or path == native["nativePath"] for path in libraries)
    for label, command in zip(["compile", "execute"], r["commands"], strict=True):
        assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
        for stream in ["stdout", "stderr"]: assert sha(capture / (label + "." + stream)) == command[stream + "Sha256"]
    assert r["exactCaptureProcessReadback"] == []
    public = HERE / "evidence" / capture.name
    if export:
        public.mkdir(exist_ok=True)
        for name in ["request.json", "observed.json", "compile.stdout", "compile.stderr", "execute.stdout", "execute.stderr"]:
            shutil.copyfile(capture / name, public / name)
        normalized = {k: v for k, v in r.items() if k not in ["tools", "commands", "libraries", "native"]}
        normalized["tools"] = {k: dict(sha256=v["sha256"]) for k, v in r["tools"].items()}
        normalized["commands"] = [{k: v for k, v in c.items() if k != "argv"} for c in r["commands"]]
        normalized["libraries"] = [{k: v for k, v in lib.items() if k != "path"} for lib in r["libraries"]]
        normalized["native"] = {k: v for k, v in r["native"].items() if k != "path"} | dict(name=Path(native["nativePath"]).name)
        normalized["loadedOriginalClassSha256"] = loaded_hashes
        normalized["loggedNativeLoads"] = [Path(path).name for path in libraries]
        normalized["stdlibAllocatorInitialized"] = True
        normalized["normalization"] = "Authored requests,observations,streams unchanged;receipt omits local tool/library/command locations. Frozen producers,compiled helper,original inputs and VM logs stay private. Logged library loads do not enumerate all transitive OS dependencies."
        (public / "receipt.json").write_text(json.dumps(normalized, indent=2) + "\n")
        manifest = dict(schema=1, capture=capture.name, privateReceiptSha256=sha(capture / "receipt.json"), exporterSha256=sha(Path(__file__)),
                        profile={k: output[k] for k in ["javaVersion", "os", "osVersion", "architecture"]},
                        publicPayloadSha256={p.name: sha(p) for p in sorted(public.iterdir()) if p.is_file()})
        (HERE / "sprite-inputs-capture.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return dict(schema=1, scenarios=26, loadedOriginalClassEntries=len(loaded), matrixQueries=130, aliasQueries=2,
                guardedClosedAccesses=2, maxRequestedPixelBytes=32, allRecordedGroupsAbsent=True,
                limits="Constructed baseline sprite inputs/context adapters only;no full resource/metadata decode,ticker,generator,bake,GPU/game,other profile or physical-reclamation qualification.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()
    print(json.dumps(audit(args.private.resolve(), args.export)))
