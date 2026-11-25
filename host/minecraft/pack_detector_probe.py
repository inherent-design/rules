#!/usr/bin/env python3
"""Owner-run original detector/validator calls on private generated paths, never pack loading."""
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
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "java"))
from arena_probe import command


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def image(root):
    result = {}
    for parent, directories, files in os.walk(root, followlinks=False):
        for name in sorted(directories + files):
            path = Path(parent) / name
            key = str(path.relative_to(root))
            if path.is_symlink(): result[key] = {"kind": "symlink", "target": os.readlink(path)}
            elif path.is_dir(): result[key] = {"kind": "directory"}
            else: result[key] = {"kind": "file", "sha256": sha(path), "bytes": path.stat().st_size}
    return result


def fixtures(capture):
    root = capture / "fixtures"
    root.mkdir()
    def file(name, content=b"authored opaque bytes; not a ZIP"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path
    regular = file("regular/payload.zip")
    jar = file("regular/payload.jar")
    upper = file("regular/payload.ZIP")
    text = file("regular/payload.txt")
    metadata = file("directory-meta/pack.mcmeta", b"authored invalid metadata")
    no_metadata = root / "directory-no-meta"; no_metadata.mkdir()
    metadata_directory = root / "directory-meta-is-directory/pack.mcmeta"; metadata_directory.mkdir(parents=True)
    absolute_link = root / "absolute-link.zip"; absolute_link.symlink_to(regular)
    relative_missing_target = file("relative-missing/payload.zip", b"LINK-TARGET")
    relative_missing = relative_missing_target.parent / "link.zip"; relative_missing.symlink_to("payload.zip")
    relative_shadow_target = file("relative-shadow/shadow.zip", b"LINK-TARGET")
    relative_shadow = relative_shadow_target.parent / "link.zip"; relative_shadow.symlink_to("shadow.zip")
    (capture / "shadow.zip").write_bytes(b"CWD-SHADOW-DIFFERENT")
    inner = file("directory-inner-link/pack.mcmeta", b"authored invalid metadata")
    (inner.parent / "inner-link").symlink_to(regular)
    rows = []
    def add(name, path, allow=True, mode="return"):
        rows.append(dict(id=name, path=str(path), allowLinks=allow, factoryMode=mode))
    add("regular-lowercase-zip", regular)
    add("regular-jar", jar)
    add("regular-uppercase-zip", upper)
    add("regular-text", text)
    add("missing", root / "absent.zip")
    add("directory-metadata", metadata.parent)
    add("directory-no-metadata", no_metadata)
    add("directory-metadata-is-directory", metadata_directory.parent)
    add("absolute-link-allowed", absolute_link)
    add("absolute-link-denied", absolute_link, False)
    add("relative-link-no-cwd-target", relative_missing)
    add("relative-link-cwd-shadow", relative_shadow)
    add("directory-inner-link-denied", inner.parent, False)
    add("directory-inner-link-allowed", inner.parent)
    add("factory-null", regular, mode="null")
    add("factory-throws", regular, mode="throw")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=["1.21.1", "1.21.4", "1.21.5", "1.21.11", "26.3"], required=True)
    parser.add_argument("--inputs", type=Path, required=True, help="Existing checked profile input plan; no acquisition.")
    parser.add_argument("--private", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.inputs.read_text())["profiles"][args.version]
    client = Path(plan["client"])
    target = next(t for t in json.loads((HERE / "targets.json").read_text())["javaReferences"] if t["release"] == args.version)
    assert sha(client) == target["source"]["clientSha256"]
    assert sha(Path(plan["metadata"])) == target["source"]["metadataSha256"]
    mapping_path = Path(plan["mappings"]) if "mappings" in plan else None
    mapping = read(mapping_path) if mapping_path else None
    owners = ["net.minecraft.server.packs.repository.PackDetector", "net.minecraft.world.level.validation.DirectoryValidator", "net.minecraft.world.level.validation.ForbiddenSymlinkInfo"]
    names = {name: mapping[name]["name"] if mapping else name for name in owners}
    detector, validator = (names[n] for n in owners[:2])
    methods = mapping[owners[0]]["methods"] if mapping else {n: n.split("(")[0] for n in ["detectPackResources(java.nio.file.Path,java.util.List)", "createZipPack(java.nio.file.Path)", "createDirectoryPack(java.nio.file.Path)"]}
    jdk = Path(plan["jdk"]) if args.version == "26.3" else Path("/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home")
    major = "25" if args.version == "26.3" else "21"
    assert f'JAVA_VERSION="{major}.' in (jdk / "release").read_text()
    cache = ROOT / ".build/minecraft/resource-cache-20261125T195402530738Z/receipt.json"
    gson = json.loads(cache.read_text())["libraries"][0]
    assert gson["name"] == "com.google.code.gson:gson:2.10.1" and sha(Path(gson["path"])) == gson["sha256"]
    capture = args.private.resolve() / ("pack-detector-" + args.version + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    capture.mkdir(parents=True)
    for name in ["home", "tmp", "classes", "adapters"]: (capture / name).mkdir()
    for path in [Path(__file__), HERE / "PackDetectorProbe.java", HERE / "mappings.py", HERE.parent / "java/arena_probe.py"]:
        shutil.copyfile(path, capture / path.name)
    shutil.copyfile(args.inputs, capture / "inputs.json")
    adapter = "public final class AuthoredDetector extends " + detector + "<Object> {\n"
    adapter += "  public AuthoredDetector(" + validator + " validator) { super(validator); }\n"
    for signature, kind in [("createZipPack(java.nio.file.Path)", "zip"), ("createDirectoryPack(java.nio.file.Path)", "directory")]:
        adapter += "  @Override protected Object " + methods[signature] + "(java.nio.file.Path path) throws java.io.IOException { return study.minecraft.PackDetectorProbe.factory(\"" + kind + "\", path); }\n"
    (capture / "AuthoredDetector.java").write_text(adapter + "}\n")
    cases = fixtures(capture)
    request = dict(schema=1, fixtureRoot=str(capture / "fixtures"), adapterDirectory=str(capture / "adapters"), bindings=dict(detectorClass=detector, validatorClass=validator, detectMethod=methods["detectPackResources(java.nio.file.Path,java.util.List)"]), cases=cases)
    (capture / "request.json").write_text(json.dumps(request, indent=2) + "\n")
    original = {}
    with zipfile.ZipFile(client) as archive:
        for owner in owners:
            prefix = names[owner].replace(".", "/")
            for member in archive.namelist():
                if member == prefix + ".class" or member.startswith(prefix + "$") and member.endswith(".class"):
                    original[member] = hashlib.sha256(archive.read(member)).hexdigest()
    record = dict(schema=1, target=target["id"], release=args.version, clientSha256=sha(client), metadataSha256=sha(Path(plan["metadata"])), mappingSha256=sha(mapping_path) if mapping_path else None,
        originalClassSha256=original, gson=gson, gsonBasisReceiptSha256=sha(cache), tools={n: dict(path=str(jdk / "bin" / n), sha256=sha(jdk / "bin" / n)) for n in ["java", "javac"]},
        jdkReleaseSha256=sha(jdk / "release"), producerSha256={n: sha(capture / n) for n in ["pack_detector_probe.py", "PackDetectorProbe.java", "AuthoredDetector.java", "mappings.py", "arena_probe.py", "inputs.json"]},
        requestSha256=sha(capture / "request.json"), fixturesBefore=image(capture / "fixtures"), cwdShadowBefore=sha(capture / "shadow.zip"), commands=[],
        limits=["Original detector and validator; authored all/none PathMatcher and pack factory callbacks, not real allowlist policy, ZIP opening, metadata, repository selection, game or renderer.", "One macOS filesystem profile; source original names/signatures intact. Relative-link target and cwd shadow are deliberate private fixtures."])
    def save(): (capture / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
    save()
    environment = dict(os.environ, TMPDIR=str(capture / "tmp"))
    classpath = os.pathsep.join([str(client.resolve()), gson["path"]])
    compile_args = [str(jdk / "bin/javac"), "-J-XX:ActiveProcessorCount=2", "-J-Xmx128m", "--release", major, "-proc:none", "-Xlint:all,-classfile", "-Werror", "-cp", classpath, "-d", str(capture / "classes"), str(capture / "PackDetectorProbe.java"), str(capture / "AuthoredDetector.java")]
    record["commands"].append(command(compile_args, capture, "compile", environment, 30)); save()
    assert record["commands"][-1]["exitCode"] == 0, "Retain compiler failure; no execution."
    shutil.move(capture / "classes/AuthoredDetector.class", capture / "adapters/AuthoredDetector.class")
    record["adapterClassSha256"] = sha(capture / "adapters/AuthoredDetector.class"); save()
    execute_args = [str(jdk / "bin/java"), "-XX:ActiveProcessorCount=2", "-Xmx96m", "-Djava.awt.headless=true", "-Duser.home=" + str(capture / "home"), "-Djava.io.tmpdir=" + str(capture / "tmp"), "-Xlog:class+load=info:file=" + str(capture / "class-load.log"), "-cp", os.pathsep.join([str(capture / "classes"), classpath]), "study.minecraft.PackDetectorProbe", str(capture / "request.json"), str(capture / "observed.json")]
    record["commands"].append(command(execute_args, capture, "execute", environment, 30))
    record["fixturesAfter"] = image(capture / "fixtures")
    record["cwdShadowAfter"] = sha(capture / "shadow.zip")
    for name in ["observed.json", "class-load.log"]:
        if (capture / name).is_file(): record[name + "Sha256"] = sha(capture / name)
    record["observerClassSha256"] = {str(p.relative_to(capture / "classes")): sha(p) for p in (capture / "classes").rglob("*.class")}
    save()
    assert all(c["exitCode"] == 0 and c["ownedGroupAbsent"] and not c["timedOut"] for c in record["commands"]), capture
    assert record["fixturesBefore"] == record["fixturesAfter"] and record["cwdShadowBefore"] == record["cwdShadowAfter"]
    assert sha(client) == record["clientSha256"] and all(sha(capture / n) == h for n, h in record["producerSha256"].items())
    observed = json.loads((capture / "observed.json").read_text())
    assert [c["id"] for c in cases] == [c["id"] for c in observed["cases"]]
    (args.private / ("latest-pack-detector-" + args.version + ".json")).write_text(json.dumps(dict(capture=str(capture))) + "\n")
    print(json.dumps(dict(capture=str(capture), cases=len(cases), groupsAbsent=True, fixturesUnchanged=True)))


if __name__ == "__main__":
    main()
