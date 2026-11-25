#!/usr/bin/env python3
"""Validate scoped family evidence links without promoting family or profile qualification."""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def validate(data):
    assert data["schema"] == 1 and len(data["families"]) == 52
    families = data["families"]
    assert len({f["id"] for f in families}) == len(families)
    known_cases = {c["id"] for c in json.loads((HERE / "item-program-cases.json").read_text())["cases"]}
    for family in families:
        assert family["scope"] and family["review"]
        for key in ["rules", "proofs", "nativeComparisons"]:
            assert type(family[key]) is list
            for name in family[key]:
                assert (ROOT / name).is_file(), (family["id"], key, name)
        components = family.get("componentEvidence", [])
        assert len({c["id"] for c in components}) == len(components), family["id"]
        for component in components:
            assert component["status"] and component["limits"]
            for key in ["report", "sources", "map", "conformance", "verification"]:
                if key in component:
                    assert (ROOT / component[key]).is_file(), (family["id"], key, component[key])
            for key in ["rules", "proofs"]:
                for name in component.get(key, []):
                    assert (ROOT / name).is_file(), (family["id"], key, name)
            if component["id"] == "compat-generic-item-program":
                assert component["caseIds"] and set(component["caseIds"]) <= known_cases
                assert len(component["caseIds"]) == len(set(component["caseIds"]))
                assert component["conformance"] == "host/minecraft/evidence/item-program-conformance.json"
            if component["id"] == "property-context-source-contracts":
                assert component["evidenceKind"] == "source-inspection" and "conformance" not in component
            if component["id"] == "breadth-source-linework":
                assert component["evidenceKind"] == "source-inspection" and "conformance" not in component
                assert not component.get("proofs") and not component.get("rules")
                assert component["sources"] == "host/minecraft/breadth-sources.json"
                assert component["map"] == "host/minecraft/breadth-contracts.json"
            if component["id"] == "vanilla-pack-detector":
                assert family["id"] == "packs.discovery"
                assert component["conformance"] == "host/minecraft/evidence/pack-detector-conformance.json"
            if component["id"] == "compat-host-free-value-cache":
                assert family["id"] == "host.compat"
                assert component["conformance"] == "host/minecraft/evidence/resource-cache-conformance.json"
    return [f["id"] for f in families if not any(f[k] for k in ["rules", "proofs", "nativeComparisons"]) and not f.get("componentEvidence")]


def main():
    data = json.loads((HERE / "inventory.json").read_text())
    thin = validate(data)
    mutations = []
    for name in ["duplicate-family", "broken-report", "unknown-case", "duplicate-component", "source-as-native", "breadth-as-native", "cache-as-game-values"]:
        changed = copy.deepcopy(data)
        if name == "duplicate-family":
            changed["families"][1]["id"] = changed["families"][0]["id"]
        else:
            target = "compat-generic-item-program" if name in ["unknown-case", "duplicate-component", "broken-report"] else "property-context-source-contracts" if name == "source-as-native" else "breadth-source-linework" if name == "breadth-as-native" else "compat-host-free-value-cache"
            family, component = next((f, c) for f in changed["families"] for c in f.get("componentEvidence", []) if c["id"] == target)
            if name == "broken-report": component["report"] = "host/minecraft/unrecorded-report.md"
            elif name == "unknown-case": component["caseIds"].append("unmeasured-full-renderer")
            elif name == "duplicate-component": family["componentEvidence"].append(copy.deepcopy(component))
            elif name in ["source-as-native", "breadth-as-native"]: component["conformance"] = "host/minecraft/evidence/resource-cache-conformance.json"
            else:
                family["componentEvidence"].remove(component)
                changed["families"][0]["componentEvidence"].append(component)
        try:
            validate(changed)
        except (AssertionError, KeyError):
            mutations.append(name)
        else:
            raise AssertionError("Changed family evidence admitted: " + name)
    print(json.dumps(dict(families=len(data["families"]), scopedLinks=sum(len(f.get("componentEvidence", [])) for f in data["families"]),
        familiesWithoutLinkedSlice=thin, rejectedMutations=mutations,
        limits="References and declared scopes only; no completion percentage or consumer/profile qualification.")))


if __name__ == "__main__":
    main()
