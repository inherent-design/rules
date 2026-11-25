#!/usr/bin/env python3
"""Owner-run original cache fixture with synthetic identities; no game or renderer."""
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
    parent = private / "item-program-20261125T183811870111Z"
    basis = json.loads((parent / "receipt.json").read_text())
    artifact = private / "inputs/compat_delivered-4ae402eaa858eef4.jar"
    assert sha(artifact) == basis["artifactSha256"]
    tools = {name: Path(item["path"]) for name, item in basis["tools"].items()}
    for name, tool in tools.items():
        assert sha(tool) == basis["tools"][name]["sha256"]
    assert sha(tools["java"].parent.parent / "release") == basis["jdkReleaseSha256"]
    gson = basis["libraries"][0]
    assert gson["name"] == "com.google.code.gson:gson:2.10.1" and sha(Path(gson["path"])) == gson["sha256"]
    cap = private / ("resource-cache-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    cap.mkdir()
    for name in ["home", "tmp", "classes"]:
        (cap / name).mkdir()
    for source in [HERE / "ResourceCacheProbe.java", Path(__file__), HERE / "resource-cache-cases.json", HERE.parent / "java/arena_probe.py"]:
        shutil.copyfile(source, cap / source.name)
    shutil.copyfile(cap / "resource-cache-cases.json", cap / "request.json")
    request = json.loads((cap / "request.json").read_text())
    for spec in request["cases"]:
        for action in spec["actions"]:
            if action["op"] == "project":
                assert action["token"] in ["a", "b", "c", "null"]
    with zipfile.ZipFile(artifact) as archive:
        classes = {n: hashlib.sha256(archive.read(n)).hexdigest() for n in archive.namelist()
            if n.startswith("design/inherent/skyweavecompat/client/model/ResourceValueCache") and n.endswith(".class")}
    assert len(classes) == 2
    receipt = dict(schema=1, target="compat-4ae402eaa858eef4", artifactSha256=sha(artifact),
        parentReceiptSha256=sha(parent / "receipt.json"), tools=basis["tools"], libraries=[gson],
        profile=basis["profile"], jdkReleaseSha256=basis["jdkReleaseSha256"], selectedClassSha256=classes,
        sourcesSha256={p.name: sha(p) for p in cap.iterdir() if p.is_file() and p.name != "request.json"},
        requestSha256=sha(cap / "request.json"), commands=[],
        scope="Original ResourceValueCache constructor/project/onClear/clear/size with authored strings, projections and callback failures. No actual components, game/loader, registry binding, world, GUI or render operation.")

    def save():
        (cap / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    env = os.environ | {"TMPDIR": str(cap / "tmp")}
    cp = os.pathsep.join([str(artifact), gson["path"]])
    compile_argv = [str(tools["javac"]), "-J-XX:ActiveProcessorCount=2", "-J-Xmx128m", "--release", "21", "-proc:none", "-Xlint:all,-classfile", "-Werror", "-cp", cp, "-d", str(cap / "classes"), str(cap / "ResourceCacheProbe.java")]
    save()
    receipt["commands"].append(command(compile_argv, cap, "compile", env, 30)); save()
    assert receipt["commands"][-1]["exitCode"] == 0, "Retain compiler failure; do not execute observer."
    execute_argv = [str(tools["java"]), "-XX:ActiveProcessorCount=2", "-Xmx128m", "-Djava.awt.headless=true", "-Duser.home=" + str(cap / "home"), "-Djava.io.tmpdir=" + str(cap / "tmp"), "-Xlog:class+load=info:file=" + str(cap / "class-load.log"), "-cp", os.pathsep.join([str(cap / "classes"), cp]), "design.inherent.skyweavecompat.client.model.ResourceCacheProbe", str(cap / "request.json"), str(cap / "observed.json")]
    receipt["commands"].append(command(execute_argv, cap, "execute", env, 30)); save()
    assert all(c["exitCode"] == 0 and c["ownedGroupAbsent"] and not c["timedOut"] for c in receipt["commands"])
    raw = json.loads((cap / "observed.json").read_text())
    assert [s["id"] for s in request["cases"]] == [s["id"] for s in raw["cases"]]
    assert not any(n in (cap / "class-load.log").read_text() for n in ["] net.minecraft.", "] net.neoforged."])
    for name in ["observed.json", "class-load.log"]:
        receipt[name + "Sha256"] = sha(cap / name)
    receipt["observerClassesSha256"] = {str(p.relative_to(cap / "classes")): sha(p) for p in (cap / "classes").rglob("*.class")}
    receipt["scenarios"] = len(raw["cases"])
    receipt["steps"] = sum(len(s.get("steps", [])) for s in raw["cases"])
    assert sha(artifact) == receipt["artifactSha256"]
    for name, digest in receipt["sourcesSha256"].items():
        assert sha(cap / name) == digest
    save()
    (private / "latest-resource-cache.json").write_text(json.dumps(dict(capture=str(cap))) + "\n")
    print(json.dumps(dict(capture=str(cap), scenarios=receipt["scenarios"], steps=receipt["steps"], groupsAbsent=True)))


if __name__ == "__main__":
    main()
