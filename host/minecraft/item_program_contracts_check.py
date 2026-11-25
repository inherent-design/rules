#!/usr/bin/env python3
"""Check retained source/field boundaries; --private also rechecks original bytes. No JVM."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(fields, ledger):
    assert fields["schema"] == ledger["schema"] == 1
    targets = {x["id"]: x for x in json.loads((HERE / "targets.json").read_text())["javaReferences"]}
    providers = {x["provider"]: x for x in json.loads((HERE / "provider-sources.json").read_text())["providers"]}
    profiles = {p["id"]: p for p in ledger["profiles"]}
    assert len(profiles) == 4
    assert set(profiles) == {"java-" + r + "-vanilla" for r in ["1.21.4", "1.21.5", "1.21.11", "26.3"]}
    for profile in profiles.values():
        assert profile["clientSha256"] == targets[profile["id"]]["source"]["clientSha256"]
        assert profile["evidence"] == "static-inspection-only"
        assert len(profile["sources"]) == 9 and len(set(profile["sources"])) == 9
        for sid in profile["sources"]:
            source = ledger["sources"][sid]
            assert source["profile"] == profile["id"]
            assert source["originalClasses"] and source["readableViewSha256"]
    assert len(ledger["sources"]) == 36
    assert {s for p in profiles.values() for s in p["sources"]} == set(ledger["sources"])
    assert len(fields["nodes"]) == 12
    for row in fields["nodes"]:
        assert row["privateView"] in providers[row["provider"]]["privateViewSha256"]
    rows = fields["vanillaNodes"]
    assert len(rows) == len({r["id"] for r in rows}) == 24
    kinds = {"model", "empty", "composite", "condition", "select", "range_dispatch"}
    for profile in profiles:
        assert {r["type"].removeprefix("minecraft:") for r in rows if r["profile"] == profile} == kinds
    for row in rows:
        assert row["profile"] in profiles and row["nativeConformance"] == "unqualified"
        assert row["dispatchSource"] in ledger["sources"]
        assert row["bodySources"] and set(row["bodySources"]) <= set(ledger["sources"])
        assert all(ledger["sources"][s]["profile"] == row["profile"] for s in row["bodySources"])
        names = [x["name"] for x in row["fields"]]
        assert len(names) == len(set(names))
        transformed = row["profile"] == "java-26.3-vanilla" and row["type"] != "minecraft:empty"
        assert ("transformation" in names) == transformed
        assert row["nullUnknownPolicy"] == "effective DFU/property codec behavior unqualified"
    assert len(fields["vanillaProfiles"]) == 4
    for profile in fields["vanillaProfiles"]:
        assert profile["profile"] in profiles
        assert set(profile["sources"]) <= set(ledger["sources"])
        expected = {"hand_animation_on_swap"}
        if profile["profile"] in ["java-1.21.11-vanilla", "java-26.3-vanilla"]:
            expected |= {"oversized_in_gui", "swap_animation_scale"}
        assert {x["name"] for x in profile["rootProperties"]} == expected
    assert len(ledger["assetDistinction"]) == 2
    for asset in ledger["assetDistinction"]:
        assert asset["registrationSource"] in ledger["sources"]
        assert asset["kind"] == "geometry/model asset, not item-program type registration"
    assert fields["baselineBoundary"]["profile"] == "java-1.21.1-vanilla"


def original_bytes(ledger):
    for profile in ledger["profiles"]:
        assert sha(ROOT / profile["clientPath"]) == profile["clientSha256"]
        if "mappingPath" in profile:
            assert sha(ROOT / profile["mappingPath"]) == profile["mappingSha256"]
        if "privateReceipt" in profile:
            assert sha(ROOT / profile["privateReceipt"]) == profile["privateReceiptSha256"]
        with zipfile.ZipFile(ROOT / profile["clientPath"]) as archive:
            for sid in profile["sources"]:
                source = ledger["sources"][sid]
                assert sha(ROOT / profile["viewsRoot"] / source["view"]) == source["readableViewSha256"]
                for member in source["originalClasses"]:
                    assert hashlib.sha256(archive.read(member["member"])).hexdigest() == member["sha256"]
            for asset in ledger["assetDistinction"]:
                if asset["profile"] == profile["id"]:
                    payload = archive.read(asset["member"])
                    assert hashlib.sha256(payload).hexdigest() == asset["sha256"]
                    assert json.loads(payload)["parent"] == asset["parent"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", action="store_true")
    args = parser.parse_args()
    fields = json.loads((HERE / "item-program-field-contracts.json").read_text())
    ledger = json.loads((HERE / "item-program-sources.json").read_text())
    validate(fields, ledger)
    rejected = []
    for name in ["unknown-source", "cross-version-source", "native-promotion", "transformation-loss", "root-property-loss", "asset-as-node"]:
        changed, sources = copy.deepcopy(fields), copy.deepcopy(ledger)
        if name == "unknown-source":
            changed["vanillaNodes"][0]["bodySources"] = ["uninspected"]
        elif name == "cross-version-source":
            changed["vanillaNodes"][0]["bodySources"] = [changed["vanillaNodes"][-1]["bodySources"][0]]
        elif name == "native-promotion":
            changed["vanillaNodes"][0]["nativeConformance"] = "qualified"
        elif name == "transformation-loss":
            changed["vanillaNodes"][-1]["fields"] = [x for x in changed["vanillaNodes"][-1]["fields"] if x["name"] != "transformation"]
        elif name == "root-property-loss":
            changed["vanillaProfiles"][-1]["rootProperties"].pop()
        else:
            sources["assetDistinction"][0]["kind"] = "registered item-program node"
        try:
            validate(changed, sources)
        except (AssertionError, KeyError):
            rejected.append(name)
        else:
            raise AssertionError("Changed qualification admitted: " + name)
    if args.private:
        original_bytes(ledger)
    print(json.dumps(dict(profiles=len(ledger["profiles"]), sourceViews=len(ledger["sources"]),
        originalClassIdentities=sum(len(s["originalClasses"]) for s in ledger["sources"].values()),
        providerNodes=len(fields["nodes"]), vanillaNodeBodies=len(fields["vanillaNodes"]),
        rejectedMutations=rejected, originalBytesChecked=args.private,
        limits="Bookkeeping and selected source identities; not codec equivalence or native vanilla/render conformance.")))


if __name__ == "__main__":
    main()
