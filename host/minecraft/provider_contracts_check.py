#!/usr/bin/env python3
"""Check provider-map references and qualification boundaries, without launching a provider."""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def validate(data):
    assert data["schema"] == 1
    families = {x["id"] for x in json.loads((HERE / "inventory.json").read_text())["families"]}
    targets = json.loads((HERE / "targets.json").read_text())
    sources = {x["provider"]: x for x in json.loads((HERE / "provider-sources.json").read_text())["providers"]}
    pins = {x["id"]: x for x in targets["providers"]}
    for identity, source in sources.items():
        assert source["artifactSha256"] == pins[identity]["sha256"]
    capabilities = data["capabilities"]
    ids = [x["id"] for x in capabilities]
    assert len(ids) == len(set(ids))
    for item in capabilities:
        source = sources[item["provider"]]
        assert item["families"] and set(item["families"]) <= families
        assert item["privateViews"] and set(item["privateViews"]) <= set(source["privateViewSha256"])
        assert item["evidenceKind"] in ["static-inspection", "original-method-and-model"]
        assert item["contract"] and item["limits"]
    variants = {x["id"] for x in targets["variants"]}
    assert {x["variant"] for x in data["variants"]} == variants
    assert len(data["variants"]) == len(variants)
    request = json.loads((HERE / "provider-cases.json").read_text())
    records = {x["id"]: x for x in request["metadata"]}
    for variant in data["variants"]:
        row = records[variant["metadataWitness"]]
        assert row["id"] == variant["variant"]
        assert variant["witnessKind"] == ("actual-isolated-select" if row["compatSelected"] else "authored-not-invoked")
        assert variant["appliedHooks"] == "unknown" and variant["rendering"] == "unqualified"
        assert variant["effectiveLibraries"] == "unknown" and variant["consumerSemantics"] == "incomplete"
        expected = "not-invoked" if not row["compatSelected"] else "eligible-two-selected-features" if "modefite" in row["mods"] else "missing-modefite-two-inactive"
        assert variant["isolatedCompatResult"] == expected
    for edge in data["coexistence"]:
        assert set(edge["participants"]) <= set(ids) and edge["required"]
    assert len({x["id"] for x in data["proposalOptions"]}) == 4
    return len(families), len(capabilities), len(variants)


def main():
    data = json.loads((HERE / "provider-contracts.json").read_text())
    counts = validate(data)
    mutations = []
    for name in ["unknown-family", "unknown-provider", "unknown-view", "duplicate-capability", "missing-variant", "applied-promotion", "skip-as-native", "unknown-edge"]:
        changed = copy.deepcopy(data)
        if name == "unknown-family":
            changed["capabilities"][0]["families"].append("all-new-gameplay")
        elif name == "unknown-provider":
            changed["capabilities"][0]["provider"] = "unselected"
        elif name == "unknown-view":
            changed["capabilities"][0]["privateViews"].append("uninspected.java")
        elif name == "duplicate-capability":
            changed["capabilities"].append(changed["capabilities"][0])
        elif name == "missing-variant":
            changed["variants"].pop()
        elif name == "applied-promotion":
            changed["variants"][0]["appliedHooks"] = "qualified"
        elif name == "skip-as-native":
            changed["variants"][0]["witnessKind"] = "actual-isolated-select"
        else:
            changed["coexistence"][0]["participants"].append("unproven-parity")
        try:
            validate(changed)
        except (AssertionError, KeyError):
            mutations.append(name)
        else:
            raise AssertionError("Changed provider map admitted: " + name)
    print(json.dumps(dict(canonicalFamilies=counts[0], scopedCapabilities=counts[1], variants=counts[2], rejectedMutations=mutations)))


if __name__ == "__main__":
    main()
