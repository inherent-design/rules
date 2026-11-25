#!/usr/bin/env python3
"""Check property/source references and evidence lanes; no provider or JVM launch."""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def validate(data):
    assert data["schema"] == 1
    providers = {p["provider"]: p for p in json.loads((HERE / "provider-sources.json").read_text())["providers"]}
    for source in data["sourceViews"]:
        assert providers[source["provider"]]["privateViewSha256"][source["view"]] == source["sha256"]
    declared = {(s["provider"], s["view"]) for s in data["sourceViews"]}
    modefite, compat = data["modefiteHandlers"], data["compatReaders"]
    assert len(modefite) == len(compat) == 33
    for rows in [modefite, compat]:
        assert len({r["id"] for r in rows}) == len(rows)
        assert {k: sum(r["kind"] == k for r in rows) for k in ["select", "condition", "range"]} == {"select": 9, "condition": 14, "range": 10}
        for row in rows:
            assert (row["provider"], row["privateView"]) in declared
            assert row["evidence"] == "static-inspection-only" and row["nativeConformance"] == "unqualified"
    handlers = {r["id"]: r for r in modefite}
    assert {(r["kind"], r["property"]) for r in modefite} == {(r["kind"], r["property"]) for r in compat}
    for reader in compat:
        if reader["delegate"] is not None:
            original = handlers[reader["delegate"]]
            assert (reader["kind"], reader["property"]) == (original["kind"], original["property"])
            assert reader["implementation"] == "Modefite registry handler via sanitized metadata"
        else:
            assert reader["property"] == "minecraft:component" or reader["kind"] == "condition" and reader["property"] == "minecraft:has_component"
        assert reader["guards"]
    assert len(set(data["componentProjections"])) == len(data["componentProjections"]) == 6
    assert len(set(data["componentPredicates"])) == len(data["componentPredicates"]) == 3
    assert len({t["id"] for t in data["tints"]}) == len(data["tints"]) == 3
    assert all(t["nativeConformance"] == "unqualified" for t in data["tints"])
    assert data["cache"]["capture"] == "resource-cache-20261125T195402530738Z"
    assert data["cache"]["nativeScenarios"] == 13 and data["cache"]["nativeActionSnapshots"] == 41


def main():
    data = json.loads((HERE / "property-context-contracts.json").read_text())
    validate(data)
    mutations = []
    for name in ["view-pin", "missing-handler", "native-promotion", "wrong-delegate", "extra-component", "wrong-capture"]:
        changed = copy.deepcopy(data)
        if name == "view-pin": changed["sourceViews"][0]["sha256"] = "0" * 64
        elif name == "missing-handler": changed["modefiteHandlers"].pop()
        elif name == "native-promotion": changed["compatReaders"][0]["nativeConformance"] = "qualified"
        elif name == "wrong-delegate": changed["compatReaders"][0]["delegate"] = changed["modefiteHandlers"][-1]["id"]
        elif name == "extra-component": changed["componentProjections"].append("minecraft:arbitrary-future-component")
        else: changed["cache"]["capture"] = "live-component-evaluation"
        try:
            validate(changed)
        except (AssertionError, KeyError):
            mutations.append(name)
        else:
            raise AssertionError("Changed map admitted: " + name)
    print(json.dumps(dict(sourceViewIdentities=len(data["sourceViews"]), modefiteHandlers=33, compatReaders=33,
        originalCacheScenarios=13, originalCacheSteps=41, rejectedMutations=mutations,
        limits="Reference/qualification bookkeeping; no native game-property or rendering claim.")))


if __name__ == "__main__":
    main()
