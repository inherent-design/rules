#!/usr/bin/env python3
"""Owner-local cache byte/identity audit and guarded public export; no Java invocation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAPTURE = "resource-cache-20261125T195402530738Z"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit():
    cap = ROOT / ".build/minecraft" / CAPTURE
    receipt = json.loads((cap / "receipt.json").read_text())
    artifact = ROOT / ".build/minecraft/inputs/compat_delivered-4ae402eaa858eef4.jar"
    assert sha(artifact) == receipt["artifactSha256"]
    assert sha(ROOT / ".build/minecraft/item-program-20261125T183811870111Z/receipt.json") == receipt["parentReceiptSha256"]
    for name, digest in receipt["sourcesSha256"].items():
        assert sha(cap / name) == digest
    for name, key in [("request.json", "requestSha256"), ("observed.json", "observed.jsonSha256"), ("class-load.log", "class-load.logSha256")]:
        assert sha(cap / name) == receipt[key]
    for tool in receipt["tools"].values():
        assert sha(Path(tool["path"])) == tool["sha256"]
    java_home = Path(receipt["tools"]["java"]["path"]).parent.parent
    assert sha(java_home / "release") == receipt["jdkReleaseSha256"]
    for library in receipt["libraries"]:
        assert sha(Path(library["path"])) == library["sha256"]
    for name, digest in receipt["observerClassesSha256"].items():
        assert sha(cap / "classes" / name) == digest
    for stem, command in zip(["compile", "execute"], receipt["commands"], strict=True):
        assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
        for channel in ["stdout", "stderr"]:
            assert sha(cap / (stem + "." + channel)) == command[channel + "Sha256"]
    loaded = {}
    with zipfile.ZipFile(artifact) as archive:
        for line in (cap / "class-load.log").read_text().splitlines():
            match = re.search(r"\] ([^ ]+) source: (.*)", line)
            if not match:
                continue
            assert not match[1].startswith(("net.minecraft.", "net.neoforged."))
            if artifact.name in match[2]:
                member = match[1].replace(".", "/") + ".class"
                loaded[member] = hashlib.sha256(archive.read(member)).hexdigest()
    assert loaded == receipt["selectedClassSha256"] and len(loaded) == 2
    request = json.loads((cap / "request.json").read_text())
    raw = json.loads((cap / "observed.json").read_text())
    assert request["schema"] == raw["schema"] == 1
    for spec, case in zip(request["cases"], raw["cases"], strict=True):
        assert spec["id"] == case["id"]
        if case["construction"] == "threw":
            assert spec["capacity"] < 1 and case["errorClass"] == "IllegalArgumentException"
            continue
        assert case["construction"] == "returned" and case["aEqualsB"] is True and case["aIdenticalB"] is False
        previous = []
        for action, step in zip(spec["actions"], case["steps"], strict=True):
            assert step["op"] == action["op"] and step["status"] in ["returned", "threw"]
            assert type(step["size"]) is int and 0 <= step["size"] <= spec["capacity"]
            assert step["events"][:len(previous)] == previous
            previous = step["events"]
            if step["status"] == "threw":
                assert step["errorClass"] == "IllegalStateException" and step["message"].startswith("authored ")
    return cap, receipt, loaded


def payloads(cap, receipt, loaded):
    selected = set(receipt["sourcesSha256"]) | {"request.json", "observed.json", "compile.stdout", "compile.stderr", "execute.stdout", "execute.stderr"}
    public = {k: v for k, v in receipt.items() if k not in ["commands", "tools", "libraries"]}
    public["commands"] = [{k: v for k, v in c.items() if k != "argv"} | dict(
        argvDisclosure="Exact owner-local argv stays private; frozen producer constructs it.") for c in receipt["commands"]]
    public["tools"] = {n: dict(executable=Path(t["path"]).name, sha256=t["sha256"]) for n, t in receipt["tools"].items()}
    public["libraries"] = [{k: v for k, v in lib.items() if k != "path"} | dict(file=Path(lib["path"]).name) for lib in receipt["libraries"]]
    public["privateReceiptSha256"] = sha(cap / "receipt.json")
    public["loadedOriginalClassSha256"] = loaded
    public["limits"] = ["Case-local authored equal/distinct string objects and non-reentrant projections/clear callbacks; no actual game component or registry.",
        "Returned labels, cache size and callback logs are observed; full cache entries, callback internals and physical reclamation are not inspected.",
        "Original classes, exact paths, argv and class-load log stay private; retained source identities do not prove translation fidelity."]
    return {name: (cap / name).read_bytes() for name in selected} | {"receipt.json": (json.dumps(public, indent=2) + "\n").encode()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--export", action="store_true")
    mode.add_argument("--check-export", action="store_true")
    args = parser.parse_args()
    cap, receipt, loaded = audit()
    if args.export or args.check_export:
        files = payloads(cap, receipt, loaded)
        dest = HERE / "evidence" / CAPTURE
        if args.check_export:
            assert {p.name for p in dest.iterdir()} == set(files)
        for name, data in files.items():
            path = dest / name
            if args.check_export:
                assert path.read_bytes() == data, name
            else:
                assert not path.exists(), "Do not overwrite retained evidence: " + name
                dest.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
    print(json.dumps(dict(status="original-byte-identity-shape-audit-passed", scenarios=receipt["scenarios"],
        steps=receipt["steps"], loadedOriginalClasses=len(loaded), exported=args.export, exportChecked=args.check_export,
        limits="No native game/component/registry/render qualification; model conformance is separate.")))


if __name__ == "__main__":
    main()
