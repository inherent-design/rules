#!/usr/bin/env python3
"""Audit/export retained original-method observations; never execute Java or open a pack."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

from pack_detector_probe import image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAPTURES = {
    "1.21.1": "pack-detector-1.21.1-20261125T211922315320Z",
    "1.21.4": "pack-detector-1.21.4-20261125T211949963972Z",
    "1.21.5": "pack-detector-1.21.5-20261125T211951358405Z",
    "1.21.11": "pack-detector-1.21.11-20261125T211952750580Z",
    "26.3": "pack-detector-26.3-20261125T211953699350Z",
}
FAILED = "pack-detector-1.21.1-20261125T211815457930Z"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit(release, name):
    capture = ROOT / ".build/minecraft" / name
    receipt = json.loads((capture / "receipt.json").read_text())
    request = json.loads((capture / "request.json").read_text())
    raw = json.loads((capture / "observed.json").read_text())
    inputs = json.loads((capture / "inputs.json").read_text())["profiles"][release]
    target = next(t for t in json.loads((HERE / "targets.json").read_text())["javaReferences"] if t["release"] == release)
    assert receipt["clientSha256"] == target["source"]["clientSha256"] == sha(Path(inputs["client"]))
    assert receipt["metadataSha256"] == target["source"]["metadataSha256"] == sha(Path(inputs["metadata"]))
    if receipt["mappingSha256"] is not None: assert sha(Path(inputs["mappings"])) == receipt["mappingSha256"]
    for path, expected in receipt["producerSha256"].items(): assert sha(capture / path) == expected
    for tool in receipt["tools"].values(): assert sha(Path(tool["path"])) == tool["sha256"]
    assert sha(Path(receipt["tools"]["java"]["path"]).parent.parent / "release") == receipt["jdkReleaseSha256"]
    assert sha(Path(receipt["gson"]["path"])) == receipt["gson"]["sha256"]
    assert sha(capture / "request.json") == receipt["requestSha256"]
    for name in ["observed.json", "class-load.log"]: assert sha(capture / name) == receipt[name + "Sha256"]
    assert sha(capture / "adapters/AuthoredDetector.class") == receipt["adapterClassSha256"]
    for path, expected in receipt["observerClassSha256"].items(): assert sha(capture / "classes" / path) == expected
    for stem, command in zip(["compile", "execute"], receipt["commands"], strict=True):
        assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
        for channel in ["stdout", "stderr"]: assert sha(capture / (stem + "." + channel)) == command[channel + "Sha256"]
    loaded = {}
    with zipfile.ZipFile(inputs["client"]) as archive:
        for line in (capture / "class-load.log").read_text().splitlines():
            match = re.search(r"\] ([^ ]+) source: (.*)", line)
            if match and inputs["client"] in match[2]:
                member = match[1].replace(".", "/") + ".class"
                loaded[member] = hashlib.sha256(archive.read(member)).hexdigest()
    assert loaded == receipt["originalClassSha256"] and len(loaded) == 4
    assert image(capture / "fixtures") == receipt["fixturesBefore"] == receipt["fixturesAfter"]
    assert sha(capture / "shadow.zip") == receipt["cwdShadowBefore"] == receipt["cwdShadowAfter"]
    assert [r["id"] for r in request["cases"]] == [r["id"] for r in raw["cases"]] and len(raw["cases"]) == 16
    assert raw["adapterHasSeparateLoader"] is True and raw["adapterSigners"] == 0
    assert raw["originalDetectorSigners"] > 0 and raw["originalValidatorSigners"] > 0
    for row in raw["cases"]: assert row["inputAttributes"] == row["inputAttributesAfter"]
    return capture, receipt, request, raw, loaded


def normalize(value, capture):
    if isinstance(value, str): return value.replace(str(capture), "<capture>")
    if isinstance(value, list): return [normalize(item, capture) for item in value]
    if isinstance(value, dict): return {key: normalize(item, capture) for key, item in value.items()}
    return value


def payloads(capture, receipt, request, raw, loaded):
    public = {k: v for k, v in receipt.items() if k not in ["tools", "gson", "commands"]}
    public = normalize(public, capture)
    public["privateReceiptSha256"] = sha(capture / "receipt.json")
    public["loadedOriginalClassSha256"] = loaded
    public["tools"] = {n: {"executable": Path(t["path"]).name, "sha256": t["sha256"]} for n, t in receipt["tools"].items()}
    public["gson"] = {k: v for k, v in receipt["gson"].items() if k != "path"}
    public["commands"] = [{k: v for k, v in command.items() if k != "argv"} for command in receipt["commands"]]
    public["normalization"] = "Only this private capture's absolute path prefix is replaced with <capture>; original hashes/argv/class-load log remain owner-local. Public payload hashes bind normalized bytes."
    data = {"receipt.json": public, "request.json": normalize(request, capture), "observed.json": normalize(raw, capture)}
    files = {n: (json.dumps(v, indent=2) + "\n").encode() for n, v in data.items()}
    for stem in ["compile", "execute"]:
        for channel in ["stdout", "stderr"]:
            name = stem + "." + channel
            files[name] = (capture / name).read_text().replace(str(capture), "<capture>").encode()
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--export", action="store_true")
    mode.add_argument("--check-export", action="store_true")
    args = parser.parse_args()
    profiles = []
    for release, name in CAPTURES.items():
        capture, receipt, request, raw, loaded = audit(release, name)
        files = payloads(capture, receipt, request, raw, loaded)
        if args.export or args.check_export:
            destination = HERE / "evidence" / name
            if args.export: destination.mkdir(exist_ok=True)
            for filename, content in files.items():
                path = destination / filename
                if path.exists(): assert path.read_bytes() == content, "Preserve existing evidence: " + str(path)
                elif args.check_export: raise AssertionError("Missing normalized export: " + str(path))
                else: path.write_bytes(content)
        profiles.append(dict(release=release, capture=name, target=receipt["target"], clientSha256=receipt["clientSha256"], privateReceiptSha256=sha(capture / "receipt.json"),
            publicPayloadSha256={n: hashlib.sha256(b).hexdigest() for n, b in files.items()}, profile={k: raw[k] for k in ["os", "osVersion", "architecture", "javaVersion", "filesystemType"]}))
    failed = ROOT / ".build/minecraft" / FAILED
    failure = json.loads((failed / "receipt.json").read_text())
    assert [c["exitCode"] for c in failure["commands"]] == [0, 1] and all(c["ownedGroupAbsent"] for c in failure["commands"])
    assert not (failed / "observed.json").exists()
    assert "signer information does not match" in (failed / "execute.stderr").read_text()
    manifest = dict(schema=1, scope="80 original detector/validator calls with authored factory and link-matcher policies; no pack opened.", profiles=profiles,
        excluded=dict(capture=FAILED, privateReceiptSha256=sha(failed / "receipt.json"), reason="Unsigned default-package helper conflicted with signed client classes before any detection calls; preserved and excluded. Corrected helper package and separate adapter loader leave original JAR/signature checks intact."))
    path = HERE / "pack-detector-captures.json"
    if args.export:
        content = json.dumps(manifest, indent=2) + "\n"
        if path.exists(): assert path.read_text() == content
        else: path.write_text(content)
    elif args.check_export: assert json.loads(path.read_text()) == manifest
    print(json.dumps(dict(profiles=5, originalCalls=80, loadedOriginalClassesPerProfile=4, ownedGroupsAbsent=10, excludedZeroCallRuns=1, exportChecked=bool(args.export or args.check_export))))


if __name__ == "__main__":
    main()
