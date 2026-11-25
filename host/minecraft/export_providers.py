#!/usr/bin/env python3
"""Export authored provider observations and identities; original classes/views stay private."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
CAPTURES = ["provider-policy-20261125T174555987623Z", "provider-matrix-20261125T180956818393Z"]
INSPECTIONS = {
    "modefite": "provider-views-modefite-20261125T174921609571Z",
    "compat": "provider-views-compat-20261125T174922577048Z",
    "polytone": "provider-views-polytone-20261125T174923791182Z",
}
ARTIFACTS = {
    "modefite": "modefite-959272d5a7acc809.jar",
    "compat": "compat_delivered-4ae402eaa858eef4.jar",
    "polytone": "polytone-7c78b6f425d84a85.jar",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    def retain(path, value):
        if args.check:
            assert path.read_bytes() == value, str(path)
        else:
            assert not path.exists(), "Do not overwrite existing evidence: " + str(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value)

    def retain_json(path, value):
        retain(path, (json.dumps(value, indent=2) + "\n").encode())

    providers = []
    for name, capture in INSPECTIONS.items():
        cap = ROOT / ".build/minecraft" / capture
        r = json.loads((cap / "receipt.json").read_text())
        artifact = ROOT / ".build/minecraft/inputs" / ARTIFACTS[name]
        assert sha(artifact) == r["artifactSha256"]
        with zipfile.ZipFile(artifact) as archive:
            for member, digest in r["originalClassSha256"].items():
                assert hashlib.sha256(archive.read(member)).hexdigest() == digest
        # Preserve source identities, not decompiled copyrighted bodies.
        views = {str(p.relative_to(cap / "source")): sha(p) for p in sorted((cap / "source").rglob("*.java"))}
        declared = r.get("sourceSha256", r.get("viewsSha256", r.get("sourceViewsSha256")))
        assert declared == views, "Unexpected inspection view ledger."
        for n, digest in r["producersSha256"].items():
            assert sha(cap / n) == digest
        assert sha(cap / "inputs.json") == r["inputsSha256"]
        command = r["command"]
        assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
        assert sha(Path(command["argv"][0])) == r["javaSha256"]
        assert sha(Path(command["argv"][command["argv"].index("-jar") + 1])) == r["toolSha256"]
        for channel in ["stdout", "stderr"]:
            assert sha(cap / ("inspect." + channel)) == command[channel + "Sha256"]
        providers.append(dict(provider=r["provider"], artifactSha256=r["artifactSha256"],
            privateReceiptSha256=sha(cap / "receipt.json"), selectedRoots=r["selectedRoots"],
            originalClassSha256=r["originalClassSha256"], privateViewSha256=views,
            scope="Selected static inspection; views are aids, not translation or runtime equivalence."))
    retain_json(HERE / "provider-sources.json", dict(schema=1, providers=providers,
        limits=["Modefite outer class census; selected Compat and Polytone roots, not complete provider effect closure.",
                "Private view identity does not mean every body has a completed semantic contract.",
                "No original class, archive, or decompiled body is exported."]))

    parent = ROOT / ".build/minecraft" / CAPTURES[0]
    for name in CAPTURES:
        cap = ROOT / ".build/minecraft" / name
        r = json.loads((cap / "receipt.json").read_text())
        dest = HERE / "evidence" / name
        assert sha(ROOT / ".build/minecraft/inputs" / ARTIFACTS["compat"]) == r["artifactSha256"]
        for filename in ["request.json", "observed.json", "class-load.log"]:
            assert sha(cap / filename) == r["requestSha256" if filename == "request.json" else filename + "Sha256"]
        for filename, digest in r["sourcesSha256"].items():
            assert sha(cap / filename) == digest
            retain(dest / filename, (cap / filename).read_bytes())
        classes = cap / "classes" if name == CAPTURES[0] else parent / "classes"
        for filename, digest in r["observerClassesSha256"].items():
            assert sha(classes / filename) == digest
        for tool in r["tools"].values():
            assert sha(Path(tool["path"])) == tool["sha256"]
        for lib in r["libraries"]:
            assert sha(Path(lib["path"])) == lib["sha256"]
        if "parentReceiptSha256" in r:
            assert sha(parent / "receipt.json") == r["parentReceiptSha256"]
        loaded = {}
        with zipfile.ZipFile(ROOT / ".build/minecraft/inputs" / ARTIFACTS["compat"]) as archive:
            for line in (cap / "class-load.log").read_text().splitlines():
                match = re.search(r"\] ([^ ]+) source: (.*)", line)
                if not match:
                    continue
                assert not match[1].startswith(("net.minecraft.", "net.neoforged."))
                if ARTIFACTS["compat"] in match[2]:
                    member = match[1].replace(".", "/") + ".class"
                    loaded[member] = hashlib.sha256(archive.read(member)).hexdigest()
            for member, digest in r.get("selectedClassSha256", {}).items():
                assert loaded[member] == digest
        for filename in ["request.json", "observed.json"]:
            retain(dest / filename, (cap / filename).read_bytes())
        stems = ["compile", "execute"] if name == CAPTURES[0] else ["execute"]
        for stem, command in zip(stems, r["commands"], strict=True):
            assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
            for channel in ["stdout", "stderr"]:
                filename = stem + "." + channel
                assert sha(cap / filename) == command[channel + "Sha256"]
                retain(dest / filename, (cap / filename).read_bytes())
        public = {k:v for k,v in r.items() if k not in ["commands", "tools", "libraries"]}
        public["commands"] = [{k:v for k,v in c.items() if k != "argv"} | dict(argvDisclosure="Exact local argv stays private; frozen producer constructs it.") for c in r["commands"]]
        public["tools"] = {n: dict(executable=Path(t["path"]).name, sha256=t["sha256"]) for n,t in r["tools"].items()}
        public["libraries"] = [{k:v for k,v in lib.items() if k != "path"} | dict(file=Path(lib["path"]).name) for lib in r["libraries"]]
        public["privateReceiptSha256"] = sha(cap / "receipt.json")
        public["loadedOriginalClassSha256"] = loaded
        public["serializationLimits"] = ["inputBytesUnchanged is Gson serialization before/after, not raw input-file equality or proof of no intervening mutation.", "The default Gson producer omits the output member for the selected JsonNull result; its sameObject flag is retained."]
        retain_json(dest / "receipt.json", public)
    print(json.dumps(dict(checked=args.check, providers=len(providers), captures=len(CAPTURES))))


if __name__ == "__main__":
    main()
