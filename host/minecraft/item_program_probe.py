#!/usr/bin/env python3
"""Owner-run original generic resource compiler fixture; no game, loader, or renderer."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "java"))
from arena_probe import command


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    private = ROOT / ".build/minecraft"
    base = private / "provider-policy-20261125T174555987623Z"
    basis = json.loads((base / "receipt.json").read_text())
    artifact = private / "inputs/compat_delivered-4ae402eaa858eef4.jar"
    assert sha(artifact) == basis["artifactSha256"]
    pin = next(x for x in json.loads((HERE / "targets.json").read_text())["providers"] if x["id"] == "compat-4ae402eaa858eef4")
    assert sha(artifact) == pin["sha256"]
    tools = {k: Path(v["path"]) for k,v in basis["tools"].items()}
    for name, path in tools.items():
        assert sha(path) == basis["tools"][name]["sha256"]
    jdk = tools["java"].parent.parent
    assert sha(jdk / "release") == basis["jdkReleaseSha256"]
    gson = next(x for x in basis["libraries"] if x["name"] == "com.google.code.gson:gson:2.10.1")
    assert sha(Path(gson["path"])) == gson["sha256"]
    cap = private / ("item-program-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    cap.mkdir()
    for name in ["classes", "home", "tmp"]:
        (cap / name).mkdir()
    producers = [HERE / "ItemProgramProbe.java", Path(__file__), HERE / "item-program-cases.json", HERE.parent / "java/arena_probe.py"]
    for path in producers:
        shutil.copyfile(path, cap / path.name)
    shutil.copyfile(cap / "item-program-cases.json", cap / "request.json")
    request = json.loads((cap / "request.json").read_text())
    selected = {}
    with zipfile.ZipFile(artifact) as archive:
        for member in archive.namelist():
            if member.startswith("design/inherent/skyweavecompat/client/model/ResourceDefinitions") and member.endswith(".class"):
                selected[member] = hashlib.sha256(archive.read(member)).hexdigest()
    receipt = dict(schema=1, target=pin["id"], artifactSha256=sha(artifact), selectedClassSha256=selected,
        parentReceiptSha256=sha(base / "receipt.json"), tools=basis["tools"], libraries=[gson],
        profile=basis["profile"], jdkReleaseSha256=sha(jdk / "release"),
        sourcesSha256={path.name:sha(cap / path.name) for path in producers}, requestSha256=sha(cap / "request.json"),
        commands=[], scope="Original generic ResourceDefinitions.compile and Root.layers with authored Values/context adapters. No NativeResourceValues, game, ModList, config load, Mixin application, renderer or filesystem publication.")

    def save():
        (cap / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    save()
    env = os.environ | {"TMPDIR":str(cap / "tmp")}
    cp = os.pathsep.join([str(artifact), gson["path"]])
    compile_argv = [str(tools["javac"]), "-J-XX:ActiveProcessorCount=2", "-J-Xmx128m", "--release", "21", "-proc:none", "-Xlint:all,-classfile", "-Werror", "-cp", cp, "-d", str(cap / "classes"), str(cap / "ItemProgramProbe.java")]
    receipt["commands"].append(command(compile_argv, cap, "compile", env, 30)); save()
    assert receipt["commands"][-1]["exitCode"] == 0, "Retain compiler failure; do not run observer."
    execute_argv = [str(tools["java"]), "-XX:ActiveProcessorCount=2", "-Xmx256m", "-Djava.awt.headless=true", "-Duser.home="+str(cap / "home"), "-Djava.io.tmpdir="+str(cap / "tmp"), "-Xlog:class+load=info:file="+str(cap / "class-load.log"), "-cp", os.pathsep.join([str(cap / "classes"), cp]), "study.minecraft.ItemProgramProbe", str(cap / "request.json"), str(cap / "observed.json")]
    receipt["commands"].append(command(execute_argv, cap, "execute", env, 30)); save()
    assert receipt["commands"][-1]["exitCode"] == 0
    for item in receipt["commands"]:
        assert item["ownedGroupAbsent"] and not item["timedOut"]
    observed = json.loads((cap / "observed.json").read_text())
    assert [x["id"] for x in observed["cases"]] == [x["id"] for x in request["cases"]]
    assert all(x["inputSerializationUnchanged"] for x in observed["cases"])
    assert not any(x in (cap / "class-load.log").read_text() for x in ["] net.minecraft.", "] net.neoforged."])
    receipt["compilerRequests"] = len(observed["cases"])
    receipt["returnedRequests"] = sum(x["status"] == "returned" for x in observed["cases"])
    receipt["returnedContexts"] = sum(len(x.get("results", [])) for x in observed["cases"])
    receipt["observerClassesSha256"] = {str(p.relative_to(cap / "classes")):sha(p) for p in (cap / "classes").rglob("*.class")}
    for name in ["observed.json", "class-load.log"]:
        receipt[name + "Sha256"] = sha(cap / name)
    assert sha(artifact) == receipt["artifactSha256"]
    for name, digest in receipt["sourcesSha256"].items():
        assert sha(cap / name) == digest
    save()
    (private / "latest-item-program.json").write_text(json.dumps(dict(capture=str(cap))) + "\n")
    print(json.dumps(dict(capture=str(cap), compilerRequests=receipt["compilerRequests"], returned=receipt["returnedRequests"], returnedContexts=receipt["returnedContexts"], ownedGroupsAbsent=True)))


if __name__ == "__main__":
    main()
