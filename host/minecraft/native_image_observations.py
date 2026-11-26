#!/usr/bin/env python3
"""Read-only audit/export of the retained tiny CPU image fixture; no JVM run."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from urllib.parse import unquote, urlparse
import zipfile

from native_image_probe import steps

HERE = Path(__file__).resolve().parent


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit(private, export=False):
    capture = Path(json.loads((private / "latest-native-image-1.21.1.json").read_text())["capture"])
    r, request, output = [json.loads((capture / name).read_text()) for name in ["receipt.json", "request.json", "observed.json"]]
    assert r["schema"] == request["schema"] == output["schema"] == 1 and r["release"] == "1.21.1"
    assert request["steps"] == steps() and [s["id"] for s in steps()] == [o["id"] for o in output["events"]]
    for name, digest in r["producerSha256"].items(): assert sha(capture / name) == digest
    for name, path in [("native_image_probe.py", HERE / "native_image_probe.py"), ("NativeImageProbe.java", HERE / "NativeImageProbe.java"),
                       ("mappings.py", HERE / "mappings.py"), ("arena_probe.py", HERE.parent / "java/arena_probe.py")]:
        assert sha(path) == r["producerSha256"][name]
    assert sha(capture / "request.json") == r["requestSha256"]
    for name, digest in r["outputs"].items(): assert sha(capture / name) == digest
    for name, digest in r["observerClasses"].items(): assert sha(capture / "classes" / name) == digest
    for name, tool in r["tools"].items(): assert sha(Path(tool["path"])) == tool["sha256"]
    assert sha(Path(r["tools"]["java"]["path"]).parents[1] / "release") == r["jdkReleaseSha256"]
    plan = json.loads((capture / "inputs.json").read_text())["profiles"]["1.21.1"]
    target = next(t for t in json.loads((HERE / "targets.json").read_text())["javaReferences"] if t["release"] == "1.21.1")
    client = Path(plan["client"]).resolve()
    assert sha(client) == r["clientSha256"] == target["source"]["clientSha256"]
    assert sha(Path(plan["metadata"])) == r["metadataSha256"] == target["source"]["metadataSha256"]
    assert sha(Path(plan["mappings"])) == r["mappingSha256"]
    with zipfile.ZipFile(client) as archive:
        for name, digest in r["originalClasses"].items():
            assert hashlib.sha256(archive.read(name.replace(".", "/") + ".class")).hexdigest() == digest
    official = {x["name"]: x["downloads"]["artifact"] for x in json.loads(Path(plan["metadata"]).read_text())["libraries"]}
    for lib in r["libraries"]:
        path = Path(lib["path"])
        assert sha(path) == lib["sha256"] and path.stat().st_size == lib["bytes"] == official[lib["name"]]["size"]
        assert hashlib.sha1(path.read_bytes()).hexdigest() == lib["sha1"] == official[lib["name"]]["sha1"]
    native = json.loads((capture / "native-input.json").read_text())
    assert sha(capture / "native-input.json") == r["native"]["acquisitionSha256"]
    assert sha(Path(native["nativePath"])) == native["nativeSha256"] == r["native"]["sha256"]
    assert sha(Path(native["archivePath"])) == native["archiveSha256"]
    assert hashlib.sha1(Path(native["archivePath"]).read_bytes()).hexdigest() == official[native["library"]]["sha1"]
    with zipfile.ZipFile(native["archivePath"]) as archive:
        assert hashlib.sha256(archive.read(native["nativeMember"])).hexdigest() == native["nativeSha256"]
    loaded, native_loads = [], []
    log = (capture / "vm.log").read_text()
    for line in log.splitlines():
        if " source: file:" in line:
            before, uri = line.split(" source: ", 1)
            if Path(unquote(urlparse(uri).path)).resolve() == client:
                loaded.append(before.split("[class,load]")[-1].strip())
        if "Loaded library " in line:
            native_loads.append(line.split("Loaded library ", 1)[1].split(", handle ")[0])
    assert loaded == list(r["originalClasses"]) == [request["bindings"]["imageClass"], request["bindings"]["formatClass"]]
    assert str(Path(native["nativePath"]).resolve()) in native_loads
    assert all(Path(path).is_relative_to(Path(r["tools"]["java"]["path"]).parents[1]) or path == native["nativePath"] for path in native_loads)
    assert "Initializing 'org/lwjgl/system/MemoryManage$StdlibAllocator'" in log
    assert not any("Initializing '" + name in log for name in ["org/lwjgl/stb/", "org/lwjgl/util/freetype/", "org/lwjgl/glfw/", "com/mojang/jtracy/"])
    assert output["allocatorProperty"] == "system" and output["libraryPathProperty"] == str(Path(native["nativePath"]).parent)
    assert Path(unquote(urlparse(output["imageClassLocation"]).path)).resolve() == client and output["originalSigners"] == 4
    assert output["os"] == "Mac OS X" and output["architecture"] == "aarch64" and output["javaVersion"] == "21.0.13.1"
    assert output["finallyCloseReturned"] is True and r["processReadback"] == []
    for name, command in zip(["compile", "execute"], r["commands"], strict=True):
        assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
        for stream in ["stdout", "stderr"]: assert sha(capture / (name + "." + stream)) == command[stream + "Sha256"]
    public = HERE / "evidence" / capture.name
    if export:
        public.mkdir(exist_ok=True)
        for name in ["request.json", "compile.stdout", "compile.stderr", "execute.stdout", "execute.stderr"]:
            shutil.copyfile(capture / name, public / name)
        normalized_output = {k: v for k, v in output.items() if k not in ["imageClassLocation", "libraryPathProperty"]}
        (public / "observed.json").write_text(json.dumps(normalized_output, indent=2) + "\n")
        normalized = {k: v for k, v in r.items() if k not in ["libraries", "native", "tools", "commands", "outputs"]}
        normalized["libraries"] = [{k: v for k, v in lib.items() if k != "path"} for lib in r["libraries"]]
        normalized["native"] = {k: v for k, v in r["native"].items() if k != "path"} | dict(name=Path(native["nativePath"]).name)
        normalized["tools"] = {k: dict(sha256=v["sha256"]) for k, v in r["tools"].items()}
        normalized["commands"] = [{k: v for k, v in c.items() if k != "argv"} for c in r["commands"]]
        normalized["privateOutputsSha256"] = r["outputs"]
        normalized["observedSha256"] = sha(public / "observed.json")
        normalized["originalClientClassesLoaded"] = loaded
        normalized["loggedNativeLoads"] = [Path(path).name for path in native_loads]
        normalized["stdlibAllocatorInitialized"] = True
        normalized["excludedInitializerPrefixesObserved"] = []
        normalized["normalization"] = "Only two absolute location fields omitted from authored observations;all event fields/streams/requests unchanged. Full commands,VM logs,original inputs/frozen producers/binaries private. JVM logged loads do not enumerate all transitive OS loader dependencies."
        (public / "receipt.json").write_text(json.dumps(normalized, indent=2) + "\n")
        manifest = dict(schema=1, capture=capture.name, privateReceiptSha256=sha(capture / "receipt.json"), exporterSha256=sha(Path(__file__)),
                        profile={k: output[k] for k in ["os", "osVersion", "architecture", "javaVersion"]},
                        publicPayloadSha256={p.name: sha(p) for p in sorted(public.iterdir()) if p.is_file()})
        (HERE / "native-image-capture.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return dict(schema=1, steps=16, requestedPixelBytes=16, originalClasses=loaded, stdlibAllocatorInitialized=True,
                loggedLibraries=[Path(path).name for path in native_loads], groupsAbsent=True,
                limits="Serial successful tiny CPU allocation only;no OS/JNI translation,physical-memory reclamation,decoder/GPU/game or other profile qualification.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()
    print(json.dumps(audit(args.private.resolve(), args.export)))
