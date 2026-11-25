#!/usr/bin/env python3
"""Owner-run original literal Term records, not condition codecs or state predicates."""
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


def cases():
    values = ["", "!", "north", "!north", "!!north", "!!", "north|south", "!north|south", "north||south",
        " north ", " !north", "! north", "!\t", "！north", "🤖", "!🤖"]
    rows = [dict(id="parse-" + str(i), operation="parse", value=value, negated=False) for i, value in enumerate(values)]
    rows += [dict(id="construct-" + str(i), operation="construct", value=value, negated=negated)
        for i, (value, negated) in enumerate([("", False), ("", True), ("north", False), ("north", True),
            ("!", False), ("!", True), ("!north", False), ("!north", True)])]
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=["1.21.5", "1.21.11", "26.3"], required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--private", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.inputs.read_text())["profiles"][args.version]
    client = Path(plan["client"])
    target = next(t for t in json.loads((HERE / "targets.json").read_text())["javaReferences"] if t["release"] == args.version)
    assert sha(client) == target["source"]["clientSha256"] and sha(Path(plan["metadata"])) == target["source"]["metadataSha256"]
    mapping_path = Path(plan["mappings"]) if "mappings" in plan else None
    owner = "net.minecraft.client.renderer.block." + ("dispatch" if args.version == "26.3" else "model") + ".multipart.KeyValueCondition$Term"
    mapping = read(mapping_path)[owner] if mapping_path else None
    original = mapping["name"] if mapping else owner
    methods = mapping["methods"] if mapping else {k: k.split("(")[0] for k in ["parse(java.lang.String)", "value()", "negated()"]}
    jdk = Path(plan["jdk"]) if args.version == "26.3" else Path("/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home")
    major = "25" if args.version == "26.3" else "21"
    assert f'JAVA_VERSION="{major}.' in (jdk / "release").read_text()
    gson_basis = ROOT / ".build/minecraft/resource-cache-20261125T195402530738Z/receipt.json"
    gson = json.loads(gson_basis.read_text())["libraries"][0]
    assert gson["name"] == "com.google.code.gson:gson:2.10.1" and sha(Path(gson["path"])) == gson["sha256"]
    capture = args.private.resolve() / ("block-term-" + args.version + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    capture.mkdir(parents=True)
    for name in ["classes", "home", "tmp"]: (capture / name).mkdir()
    for path in [Path(__file__), HERE / "BlockTermProbe.java", HERE / "mappings.py", HERE.parent / "java/arena_probe.py"]: shutil.copyfile(path, capture / path.name)
    shutil.copyfile(args.inputs, capture / "inputs.json")
    request = dict(schema=1, bindings=dict(className=original, parse=methods["parse(java.lang.String)"], value=methods["value()"], negated=methods["negated()"]), cases=cases())
    (capture / "request.json").write_text(json.dumps(request, indent=2) + "\n")
    with zipfile.ZipFile(client) as archive: original_sha = hashlib.sha256(archive.read(original.replace(".", "/") + ".class")).hexdigest()
    record = dict(schema=1, target=target["id"], release=args.version, clientSha256=sha(client), metadataSha256=sha(Path(plan["metadata"])),
        mappingSha256=sha(mapping_path) if mapping_path else None, originalClass=original, originalClassSha256=original_sha,
        gson=gson, gsonBasisSha256=sha(gson_basis), tools={name: dict(path=str(jdk / "bin" / name), sha256=sha(jdk / "bin" / name)) for name in ["java", "javac"]},
        jdkReleaseSha256=sha(jdk / "release"), producerSha256={n: sha(capture / n) for n in ["block_term_probe.py", "BlockTermProbe.java", "mappings.py", "arena_probe.py", "inputs.json"]},
        requestSha256=sha(capture / "request.json"), commands=[], scope="Original Term record parse/constructor/accessors/toString/reparse only. No outer condition,Terms codec,property/state/registry/game/renderer.")
    def save(): (capture / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
    save()
    env = dict(os.environ, TMPDIR=str(capture / "tmp"))
    compile_args = [str(jdk / "bin/javac"), "-J-XX:ActiveProcessorCount=2", "-J-Xmx96m", "--release", major, "-proc:none", "-Xlint:all,-classfile", "-Werror", "-cp", gson["path"], "-d", str(capture / "classes"), str(capture / "BlockTermProbe.java")]
    record["commands"].append(command(compile_args, capture, "compile", env, 30)); save()
    assert record["commands"][-1]["exitCode"] == 0, capture
    execute = [str(jdk / "bin/java"), "-XX:ActiveProcessorCount=2", "-Xmx96m", "-Djava.awt.headless=true", "-Duser.home=" + str(capture / "home"), "-Djava.io.tmpdir=" + str(capture / "tmp"), "-Xlog:class+load=info:file=" + str(capture / "class-load.log"), "-cp", os.pathsep.join([str(capture / "classes"), str(client.resolve()), gson["path"]]), "study.minecraft.BlockTermProbe", str(capture / "request.json"), str(capture / "observed.json")]
    record["commands"].append(command(execute, capture, "execute", env, 30))
    for name in ["observed.json", "class-load.log"]:
        if (capture / name).is_file(): record[name + "Sha256"] = sha(capture / name)
    record["observerClassSha256"] = {str(p.relative_to(capture / "classes")): sha(p) for p in (capture / "classes").rglob("*.class")}
    save()
    assert all(c["exitCode"] == 0 and c["ownedGroupAbsent"] and not c["timedOut"] for c in record["commands"]), capture
    assert sha(client) == record["clientSha256"] and all(sha(capture / n) == h for n, h in record["producerSha256"].items())
    observed = json.loads((capture / "observed.json").read_text())
    assert [r["id"] for r in request["cases"]] == [r["id"] for r in observed["cases"]]
    (args.private / ("latest-block-term-" + args.version + ".json")).write_text(json.dumps(dict(capture=str(capture))) + "\n")
    print(json.dumps(dict(capture=str(capture), initialCalls=len(observed["cases"]), groupsAbsent=True)))


if __name__ == "__main__":
    main()
