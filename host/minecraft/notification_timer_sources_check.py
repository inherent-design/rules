#!/usr/bin/env python3
"""Check source attribution; optional retained-input readback, never Java or game."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate(data):
    assert data["schema"] == 1 and data["evidenceKind"] == "source-inspection"
    assert [r["release"] for r in data["profiles"]] == ["1.21.1", "26.3"]
    targets = {t["release"]: t for t in json.loads((HERE / "targets.json").read_text())["javaReferences"]}
    breadth = {p["release"]: p for p in json.loads((HERE / "breadth-sources.json").read_text())["profiles"]}
    for name in [data["report"], data["hostContract"], data["hostComparison"]]: assert (ROOT / name).is_file()
    for row in data["profiles"]:
        t, b = targets[row["release"]], breadth[row["release"]]
        assert row["target"] == b["target"] == t["id"]
        assert row["clientSha256"] == b["clientSha256"] == t["source"]["clientSha256"]
        assert row["metadataSha256"] == b["metadataSha256"] == t["source"]["metadataSha256"]
        assert row["mappingSha256"] == b["mappingSha256"]
        m, c = row["manager"], row["caller"]
        assert m["canonical"] == "net.minecraft.client.PeriodicNotificationManager" and c["canonical"] == "net.minecraft.client.Minecraft"
        assert m["view"] == "net/minecraft/client/PeriodicNotificationManager.java"
        assert m["viewSha256"] == b["viewsSha256"][m["view"]] and m["breadthReceiptSha256"] == b["receiptSha256"]
        assert m["breadthCapture"] == b["capture"]
        expected = {k: v for k, v in b["originalClassMembers"].items() if k.startswith(m["canonical"])}
        assert m["originalClassMembers"] == expected and len(expected) == 3
        assert c["originalClass"] == ("fgo" if row["release"] == "1.21.1" else c["canonical"])
        assert c["selectedReferences"] == 7 and len(row["reviewedClauses"]) == 4 and row["limits"]
        for key in ["originalClassSha256", "receiptSha256", "streamSha256", "selectedSha256"]: assert re.fullmatch("[0-9a-f]{64}", c[key])
    return data


def readback(data, private):
    for row in data["profiles"]:
        m, c = row["manager"], row["caller"]
        breadth = private / m["breadthCapture"]
        assert sha(breadth / "receipt.json") == m["breadthReceiptSha256"]
        assert sha(breadth / "source" / m["view"]) == m["viewSha256"]
        capture = private / c["capture"]
        assert sha(capture / "receipt.json") == c["receiptSha256"]
        receipt = json.loads((capture / "receipt.json").read_text())
        for name, digest in receipt["producerSha256"].items(): assert sha(capture / name) == digest
        assert sha(Path(receipt["tool"]["path"])) == receipt["tool"]["sha256"]
        actual = next(p for p in receipt["profiles"] if p["release"] == row["release"])
        command = actual["command"]
        assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
        for stream in ["stdout", "stderr"]: assert sha(capture / (row["release"] + "." + stream)) == command[stream + "Sha256"]
        assert c["streamSha256"] == command["stdoutSha256"] and sha(capture / (row["release"] + "-selected.json")) == c["selectedSha256"]
        assert actual["originalClass"] == c["originalClass"] and actual["classEntrySha256"] == c["originalClassSha256"]
        plan = json.loads((capture / "inputs.json").read_text())["profiles"][row["release"]]
        client = Path(plan["client"])
        assert sha(client) == row["clientSha256"] and sha(Path(plan["metadata"])) == row["metadataSha256"]
        assert (sha(Path(plan["mappings"])) if "mappings" in plan else None) == row["mappingSha256"]
        with zipfile.ZipFile(client) as archive:
            assert hashlib.sha256(archive.read(c["originalClass"].replace(".", "/") + ".class")).hexdigest() == c["originalClassSha256"]
            for member in m["originalClassMembers"].values():
                assert hashlib.sha256(archive.read(member["member"])).hexdigest() == member["sha256"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path)
    args = parser.parse_args()
    data = validate(json.loads((HERE / "notification-timer-sources.json").read_text()))
    mutations = []
    for name in ["source-as-runtime", "wrong-client", "wrong-manager", "changed-view", "missing-class"]:
        d = copy.deepcopy(data)
        if name == "source-as-runtime": d["evidenceKind"] = "game-tested"
        elif name == "wrong-client": d["profiles"][0]["clientSha256"] = "0" * 64
        elif name == "wrong-manager": d["profiles"][0]["manager"]["canonical"] = "java.util.Timer"
        elif name == "changed-view": d["profiles"][0]["manager"]["viewSha256"] = "0" * 64
        else: d["profiles"][0]["manager"]["originalClassMembers"].popitem()
        try: validate(d)
        except (AssertionError, KeyError): mutations.append(name)
        else: raise AssertionError("Altered source attribution admitted: " + name)
    if args.private: readback(data, args.private.resolve())
    print(json.dumps(dict(profiles=2, originalClassIdentities=8, rejectedMutations=mutations,
        privateReadback=bool(args.private), limits="Attribution only;source consumer and authored JDK Timer evidence remain distinct. No Java/game or new native qualification.")))


if __name__ == "__main__":
    main()
