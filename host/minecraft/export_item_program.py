#!/usr/bin/env python3
"""Export authored item-program evidence; verify existing export with --check. No JVM."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAPTURE = "item-program-20261125T183811870111Z"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payloads():
    cap = ROOT / ".build/minecraft" / CAPTURE
    r = json.loads((cap / "receipt.json").read_text())
    artifact = ROOT / ".build/minecraft/inputs/compat_delivered-4ae402eaa858eef4.jar"
    assert sha(artifact) == r["artifactSha256"]
    assert sha(cap / "class-load.log") == r["class-load.logSha256"]
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
    assert loaded == r["selectedClassSha256"]
    for tool in r["tools"].values():
        assert sha(Path(tool["path"])) == tool["sha256"]
    for library in r["libraries"]:
        assert sha(Path(library["path"])) == library["sha256"]
    for name, digest in r["observerClassesSha256"].items():
        assert sha(cap / "classes" / name) == digest
    selected = set(r["sourcesSha256"]) | {"request.json", "observed.json"}
    for name, digest in r["sourcesSha256"].items():
        assert sha(cap / name) == digest
    assert sha(cap / "request.json") == r["requestSha256"]
    assert sha(cap / "observed.json") == r["observed.jsonSha256"]
    for stem, command in zip(["compile", "execute"], r["commands"], strict=True):
        assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
        for channel in ["stdout", "stderr"]:
            name = stem + "." + channel
            assert sha(cap / name) == command[channel + "Sha256"]
            selected.add(name)
    public = {k: v for k, v in r.items() if k not in ["commands", "tools", "libraries"]}
    public["commands"] = [{k: v for k, v in c.items() if k != "argv"} | dict(
        argvDisclosure="Exact owner-local argv stays private; frozen producer constructs it.") for c in r["commands"]]
    public["tools"] = {n: dict(executable=Path(t["path"]).name, sha256=t["sha256"]) for n, t in r["tools"].items()}
    public["libraries"] = [{k: v for k, v in lib.items() if k != "path"} | dict(file=Path(lib["path"]).name) for lib in r["libraries"]]
    public["privateReceiptSha256"] = sha(cap / "receipt.json")
    public["loadedOriginalClassSha256"] = loaded
    public["serializationLimits"] = [
        "inputSerializationUnchanged compares Gson serialization before/after, not raw request bytes or intervening mutation.",
        "Original classes, exact argv/class paths and class-load log stay owner-local; only identities and the audited original-class selection are exported."]
    return {name: (cap / name).read_bytes() for name in selected} | {"receipt.json": (json.dumps(public, indent=2) + "\n").encode()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    dest = HERE / "evidence" / CAPTURE
    files = payloads()
    if args.check:
        assert {p.name for p in dest.iterdir()} == set(files)
    for name, data in files.items():
        path = dest / name
        if args.check:
            assert path.read_bytes() == data, name
        else:
            assert not path.exists(), "Do not overwrite retained evidence: " + name
            dest.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print(json.dumps(dict(checked=args.check, files=len(files), bytes=sum(map(len, files.values())),
        loadedOriginalClasses=14, originalBodiesExported=False)))


if __name__ == "__main__":
    main()
