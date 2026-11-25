#!/usr/bin/env python3
"""Check condition/property source attribution; optional frozen private readback, no Java."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import zipfile

HERE = Path(__file__).resolve().parent
VERSIONS = {"1.21.1", "1.21.4", "1.21.5", "1.21.11", "26.3"}


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def digest(value):
    assert re.fullmatch("[0-9a-f]{64}", value)


def validate(data):
    assert data["schema"] == 1 and data["evidenceKind"] == "source-inspection" and data["remaining"]
    assert len(data["parts"]) == 2 and {p["id"] for p in data["parts"]} == {"condition-terms", "property-domain"}
    assert set(data["reviewedClauses"]) == {p["id"] for p in data["parts"]} and all(data["reviewedClauses"].values())
    targets = {t["release"]: t for t in json.loads((HERE / "targets.json").read_text())["javaReferences"]}
    for part in data["parts"]:
        assert part["capture"] == Path(part["capture"]).name
        for key in ["privateReceiptSha256", "toolSha256", "jdkReleaseSha256"]: digest(part[key])
        for value in part["producerSha256"].values(): digest(value)
        assert len(part["profiles"]) == 5 and {p["release"] for p in part["profiles"]} == VERSIONS
        for p in part["profiles"]:
            version = p["release"]
            assert p["target"] == targets[version]["id"] and p["clientSha256"] == targets[version]["source"]["clientSha256"]
            assert p["command"] == dict(exitCode=0, ownedGroupAbsent=True, timedOut=False)
            for key in ["disassemblySha256", "stderrSha256"]: digest(p[key])
            if p["mappingSha256"] is not None: digest(p["mappingSha256"])
            if part["id"] == "property-domain":
                expected = {"net.minecraft.world.level.block.state.StateDefinition", "net.minecraft.world.level.block.state.StateDefinition$Builder", "net.minecraft.world.level.block.state.properties.Property"}
            else:
                prefix = "net.minecraft.client.renderer.block." + ("dispatch" if version == "26.3" else "model") + ".multipart.KeyValueCondition"
                expected = {prefix} if version in ["1.21.1", "1.21.4"] else {prefix, prefix + "$Term", prefix + "$Terms"}
            assert set(p["classes"]) == expected
            for item in p["classes"].values():
                assert item["original"] and "/" not in item["original"]
                digest(item["sha256"])


def readback(data, root):
    total = 0
    for part in data["parts"]:
        capture = root / part["capture"]
        assert sha(capture / "receipt.json") == part["privateReceiptSha256"]
        receipt = json.loads((capture / "receipt.json").read_text())
        assert receipt["producerSha256"] == part["producerSha256"] and receipt["toolSha256"] == part["toolSha256"] and receipt["jdkReleaseSha256"] == part["jdkReleaseSha256"]
        for name, value in receipt["producerSha256"].items(): assert sha(capture / name) == value
        profiles = {r["release"]: r for r in receipt["profiles"]}
        plan = json.loads((capture / "inputs.json").read_text())["profiles"]
        for p in part["profiles"]:
            r, inputs = profiles[p["release"]], plan[p["release"]]
            assert r["clientSha256"] == p["clientSha256"] and r["mappingSha256"] == p["mappingSha256"]
            assert sha(Path(inputs["client"])) == p["clientSha256"]
            if p["mappingSha256"] is not None: assert sha(Path(inputs["mappings"])) == p["mappingSha256"]
            assert r["command"]["exitCode"] == 0 and r["command"]["ownedGroupAbsent"] and not r["command"]["timedOut"]
            assert sha(Path(r["command"]["argv"][0])) == part["toolSha256"]
            for suffix, key in [("stdout", "disassemblySha256"), ("stderr", "stderrSha256")]:
                value = sha(capture / (p["release"] + "." + suffix))
                assert value == p[key] == r["command"][suffix + "Sha256"]
            assert r["classEntrySha256"] == {i["original"]: i["sha256"] for i in p["classes"].values()}
            with zipfile.ZipFile(inputs["client"]) as archive:
                for item in p["classes"].values():
                    assert hashlib.sha256(archive.read(item["original"].replace(".", "/") + ".class")).hexdigest() == item["sha256"]
                    total += 1
    return dict(profiles=10, originalClasses=total, frozenProducersAndStreams=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path)
    args = parser.parse_args()
    data = json.loads((HERE / "block-condition-sources.json").read_text()); validate(data)
    refused = []
    for label in ["native-promotion", "missing-profile", "wrong-client", "missing-term-class", "property-as-term", "closed-dependency-list"]:
        p = copy.deepcopy(data)
        if label == "native-promotion": p["evidenceKind"] = "native-conformance"
        elif label == "missing-profile": p["parts"][0]["profiles"].pop()
        elif label == "wrong-client": p["parts"][0]["profiles"][0]["clientSha256"] = "0" * 64
        elif label == "missing-term-class":
            classes = p["parts"][0]["profiles"][2]["classes"]
            classes.pop(next(k for k in classes if k.endswith("$Term")))
        elif label == "property-as-term": p["parts"][0]["profiles"][0]["classes"] = p["parts"][1]["profiles"][0]["classes"]
        else: p["remaining"] = []
        try: validate(p)
        except (AssertionError, KeyError): refused.append(label)
        else: raise AssertionError("Unsupported source promotion admitted: " + label)
    private = readback(data, args.private.resolve()) if args.private else "not requested;no native/source semantic promotion"
    print(json.dumps(dict(sourceProfiles=10, originalClassIdentities=26, rejectedMutations=refused, privateReadback=private,
        limits="Attribution/qualification only;original atom runtime records are separate from whole-condition/property-state or rendering support.")))


if __name__ == "__main__":
    main()
