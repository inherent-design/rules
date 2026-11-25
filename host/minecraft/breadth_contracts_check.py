#!/usr/bin/env python3
"""Check source-map attribution and qualification; never launch a client or JVM."""
import argparse
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

HERE = Path(__file__).resolve().parent
VERSIONS = {"1.21.1", "1.21.4", "1.21.5", "1.21.11", "26.3"}
FAMILIES = {"packs.selection", "models.blockstates", "models.generated", "textures.images", "text.builtin_lists"}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checked_hash(value):
    assert isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value)


def safe_member(value):
    path = PurePosixPath(value)
    assert not path.is_absolute() and ".." not in path.parts and "\\" not in value


def validate(data, sources):
    assert data["schema"] == sources["schema"] == 1
    assert data["state"] == "partial-source-linework"
    assert sources["evidence"] == "private-source-inspection-only" and sources["limits"]
    assert data["sourceLedger"] == "host/minecraft/breadth-sources.json"
    assert data["report"] == "host/minecraft/BREADTH-LINEWORK.md" and (HERE / "BREADTH-LINEWORK.md").is_file()
    targets = {t["release"]: t for t in json.loads((HERE / "targets.json").read_text())["javaReferences"]}
    profiles = {p["release"]: p for p in sources["profiles"]}
    assert len(sources["profiles"]) == len(profiles) == 5 and set(profiles) == VERSIONS
    for release, profile in profiles.items():
        target = targets[release]
        assert profile["target"] == target["id"]
        assert profile["clientSha256"] == target["source"]["clientSha256"]
        assert profile["metadataSha256"] == target["source"]["metadataSha256"]
        assert profile["command"] == {"exitCode": 0, "timedOut": False, "ownedGroupAbsent": True}
        assert profile["capture"].startswith("breadth-views-" + release + "-") and "/" not in profile["capture"]
        for key in ["receiptSha256", "namedJarSha256", "toolSha256", "javaSha256", "jdkReleaseSha256"]:
            checked_hash(profile[key])
        for name, value in profile["viewsSha256"].items():
            safe_member(name)
            assert name.endswith(".java")
            checked_hash(value)
        for item in profile["originalClassMembers"].values():
            safe_member(item["member"])
            assert item["member"].endswith(".class")
            checked_hash(item["sha256"])
        assert set(profile["categories"]) == FAMILIES and all(profile["categories"].values())
        assert all(set(names) <= set(profile["originalClassMembers"]) for names in profile["categories"].values())
    family_map = {f["id"]: f for f in data["families"]}
    assert len(data["families"]) == len(family_map) == 5 and set(family_map) == FAMILIES
    for family in family_map.values():
        assert family["inputs"] and family["consumer"] and family["effects"] and family["openDependencies"]
        for field in family["inputs"]:
            assert field["name"] and field["domain"] and field["absence"]
    assert len(data["slices"]) == 25
    assert {(s["release"], s["family"]) for s in data["slices"]} == {(v, f) for v in VERSIONS for f in FAMILIES}
    assert len({s["id"] for s in data["slices"]}) == 25
    for item in data["slices"]:
        profile = profiles[item["release"]]
        assert item["target"] == profile["target"] and item["id"] == item["release"] + ":" + item["family"]
        assert item["evidenceKind"] == "source-inspection" and item["nativeConformance"] == "unqualified"
        assert item["formalClaims"] == [] and "conformance" not in item
        assert item["versionBoundary"] and item["openDependencies"] == family_map[item["family"]]["openDependencies"]
        assert item["reviewedViews"]
        assert len({v["view"] for v in item["reviewedViews"]}) == len(item["reviewedViews"])
        for view in item["reviewedViews"]:
            assert profile["viewsSha256"][view["view"]] == view["sha256"] and view["reviewedClauses"]
            root = view["view"][:-5].replace("/", ".")
            expected = {n for n in profile["originalClassMembers"] if n == root or n.startswith(root + "$")}
            assert expected and set(view["originalClasses"]) == expected
            assert expected <= set(profile["categories"][item["family"]])


def private_readback(sources, root):
    totals = {"profiles": 0, "views": 0, "originalClasses": 0}
    for profile in sources["profiles"]:
        capture = root / profile["capture"]
        assert digest(capture / "receipt.json") == profile["receiptSha256"]
        receipt = json.loads((capture / "receipt.json").read_text())
        for key in ["target", "clientSha256", "metadataSha256", "mappingSha256", "namedJarSha256", "toolSha256", "javaSha256", "jdkReleaseSha256", "producersSha256", "originalClassMembers", "viewsSha256", "categories"]:
            assert receipt[key] == profile[key], (profile["release"], key)
        assert receipt["command"]["exitCode"] == 0 and receipt["command"]["ownedGroupAbsent"] and not receipt["command"]["timedOut"]
        for name, value in profile["producersSha256"].items():
            assert digest(capture / name) == value
        for name, value in profile["viewsSha256"].items():
            assert digest(capture / "source" / name) == value
            totals["views"] += 1
        assert digest(capture / "inputs.json") == receipt["inputsSha256"]
        inputs = json.loads((capture / "inputs.json").read_text())["profiles"][profile["release"]]
        for key, expected in [("client", "clientSha256"), ("metadata", "metadataSha256"), ("named", "namedJarSha256"), ("decompiler", "toolSha256")]:
            assert digest(Path(inputs[key])) == profile[expected], (profile["release"], key)
        if profile["mappingSha256"] is not None:
            assert digest(Path(inputs["mappings"])) == profile["mappingSha256"]
        assert digest(Path(inputs["jdk"]) / "bin/java") == profile["javaSha256"]
        assert digest(Path(inputs["jdk"]) / "release") == profile["jdkReleaseSha256"]
        with zipfile.ZipFile(inputs["client"]) as original:
            for item in profile["originalClassMembers"].values():
                assert hashlib.sha256(original.read(item["member"])).hexdigest() == item["sha256"]
                totals["originalClasses"] += 1
        with zipfile.ZipFile(inputs["named"]) as named:
            for member, expected in receipt["inspectionClassSha256"].items():
                assert hashlib.sha256(named.read(member)).hexdigest() == expected
                assert digest(capture / "classes" / member) == expected
        totals["profiles"] += 1
    return totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, help="Owner-local capture root; also reads original retained inputs, no launches.")
    args = parser.parse_args()
    data = json.loads((HERE / "breadth-contracts.json").read_text())
    sources = json.loads((HERE / "breadth-sources.json").read_text())
    validate(data, sources)
    rejected = []
    for name in ["missing-slice", "wrong-target", "missing-dependency", "native-promotion", "proof-promotion", "unbound-view", "wrong-original-owner"]:
        changed = copy.deepcopy(data)
        first = changed["slices"][0]
        if name == "missing-slice": changed["slices"].pop()
        elif name == "wrong-target": first["target"] = "unselected-runtime"
        elif name == "missing-dependency": first["openDependencies"] = []
        elif name == "native-promotion": first["nativeConformance"] = "qualified"
        elif name == "proof-promotion": first["formalClaims"] = ["source-implies-runtime"]
        elif name == "unbound-view": first["reviewedViews"][0]["sha256"] = "0" * 64
        else: first["reviewedViews"][0]["originalClasses"] = sources["profiles"][0]["categories"]["text.builtin_lists"]
        try:
            validate(changed, sources)
        except (AssertionError, KeyError):
            rejected.append(name)
        else:
            raise AssertionError("Invalid source map admitted: " + name)
    readback = private_readback(sources, args.private) if args.private else "not requested; original inputs remain owner-local"
    print(json.dumps(dict(profiles=5, families=5, sourceSlices=25, rejectedMutations=rejected, privateReadback=readback,
        limits="Attribution and declared qualification only; no semantic equivalence, native behavior or proof claim.")))


if __name__ == "__main__":
    main()
