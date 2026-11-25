#!/usr/bin/env python3
"""Export generated observations and authored producers, never game payloads."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def export(capture):
    receipt = json.loads((capture / "receipt.json").read_text())
    assert receipt["observerErrors"] == 0
    assert all(x["exitCode"] == 0 and x["ownedGroupAbsent"] and not x["timedOut"] for x in receipt["commands"])
    assert sha(capture / "observed.json") == receipt["observedSha256"]
    for name, digest in receipt["sourceSha256"].items():
        assert sha(capture / name) == digest
    request = json.loads((capture / "request.json").read_text())
    assert sha(capture / "request.json") == receipt["requestSha256"]
    destination = HERE / "evidence" / capture.name
    destination.mkdir(parents=True, exist_ok=False)
    for name in receipt["sourceSha256"]:
        shutil.copyfile(capture / name, destination / name)
    shutil.copyfile(capture / "observed.json", destination / "observed.json")
    (destination / "cases.json").write_text(json.dumps(request["cases"], indent=2, ensure_ascii=False) + "\n")
    public = {k: v for k, v in receipt.items() if k not in ("libraries", "commands", "tools")}
    public["libraries"] = [{"file": Path(x["path"]).name, "sha1": x["sha1"], "sha256": x["sha256"]} for x in receipt["libraries"]]
    public["tools"] = {k: {"executable": Path(v["path"]).name, "sha256": v["sha256"]} for k,v in receipt["tools"].items()}
    public["commands"] = [{k: v for k,v in row.items() if k != "argv"} | {
        "argvSha256": hashlib.sha256(json.dumps(row["argv"], ensure_ascii=True).encode()).hexdigest(),
        "argvDisclosure": "Exact owner-local argv retained privately; authored collector records argument construction."
    } for row in receipt["commands"]]
    public["publicCasesSha256"] = sha(destination / "cases.json")
    public["exportPolicy"] = "Generated JSON observations and authored fixtures/producers only; original clients, mappings, libraries, transformed/decompiled sources and user installations excluded."
    (destination / "receipt.json").write_text(json.dumps(public, indent=2) + "\n")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    print(export(parser.parse_args().capture.resolve()))
