#!/usr/bin/env python3
"""Read-only owner-local original-byte and observation audit; not model conformance."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def references(node):
    kind = node["type"]
    if kind == "minecraft:model":
        name = node["model"]
        return {name if ":" in name else "minecraft:" + name}
    if kind == "minecraft:empty":
        return set()
    if kind == "minecraft:composite":
        children = node["models"]
    elif kind == "minecraft:condition":
        children = [node["on_true"], node["on_false"]]
    elif kind == "minecraft:select":
        children = [case["model"] for case in node["cases"]]
    elif kind == "minecraft:range_dispatch":
        children = [entry["model"] for entry in node["entries"]]
    else:
        raise AssertionError("Unselected successful node grammar")
    if "fallback" in node:
        children = [*children, node["fallback"]]
    return set().union(*(references(child) for child in children))


def main():
    cap = Path(json.loads((ROOT / ".build/minecraft/latest-item-program.json").read_text())["capture"])
    receipt = json.loads((cap / "receipt.json").read_text())
    artifact = ROOT / ".build/minecraft/inputs/compat_delivered-4ae402eaa858eef4.jar"
    assert sha(artifact) == receipt["artifactSha256"]
    assert sha(cap / "request.json") == receipt["requestSha256"]
    for name in ["observed.json", "class-load.log"]:
        assert sha(cap / name) == receipt[name + "Sha256"]
    for name, digest in receipt["sourcesSha256"].items():
        assert sha(cap / name) == digest
    for name, digest in receipt["observerClassesSha256"].items():
        assert sha(cap / "classes" / name) == digest
    for tool in receipt["tools"].values():
        assert sha(Path(tool["path"])) == tool["sha256"]
    for library in receipt["libraries"]:
        assert sha(Path(library["path"])) == library["sha256"]
    for stem, command in zip(["compile", "execute"], receipt["commands"], strict=True):
        assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
        for channel in ["stdout", "stderr"]:
            assert sha(cap / (stem + "." + channel)) == command[channel + "Sha256"]
    loaded = set()
    with zipfile.ZipFile(artifact) as archive:
        for line in (cap / "class-load.log").read_text().splitlines():
            match = re.search(r"\] ([^ ]+) source: (.*)", line)
            if not match:
                continue
            assert not match[1].startswith(("net.minecraft.", "net.neoforged."))
            if artifact.name in match[2]:
                member = match[1].replace(".", "/") + ".class"
                assert hashlib.sha256(archive.read(member)).hexdigest() == receipt["selectedClassSha256"][member]
                loaded.add(member)
        assert loaded == set(receipt["selectedClassSha256"])
    request = json.loads((cap / "request.json").read_text())
    observed = json.loads((cap / "observed.json").read_text())
    assert [x["id"] for x in request["cases"]] == [x["id"] for x in observed["cases"]]
    returned = contexts = layers = 0
    for spec, raw in zip(request["cases"], observed["cases"], strict=True):
        assert raw["inputSerializationUnchanged"] is True
        assert all(type(event) is str for event in raw["events"])
        if raw["status"] == "threw":
            assert raw["errorClass"] == "JsonParseException" and type(raw["message"]) is str
            assert "compile" not in raw and "results" not in raw
            continue
        assert raw["status"] == raw["compile"] == "returned"
        assert raw["dependencies"] == sorted(references(spec["input"]["model"]))
        assert [x["contextId"] for x in raw["results"]] == [x["id"] for x in spec["contexts"]]
        for result in raw["results"]:
            for layer in result["layers"]:
                assert set(layer) == {"model", "tints"} and type(layer["model"]) is str
                assert all(type(tint) is int for tint in layer["tints"])
                layers += 1
        returned += 1
        contexts += len(raw["results"])
    print(json.dumps(dict(status="owner-local-byte-and-shape-audit-passed", requests=len(request["cases"]), returned=returned,
        contexts=contexts, layers=layers, loadedOriginalClasses=len(loaded),
        limits="References checked for successful selected syntax; no compiler/evaluator model, codec equivalence, actual game context or renderer qualification.")))


if __name__ == "__main__":
    main()
