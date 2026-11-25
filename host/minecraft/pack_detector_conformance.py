#!/usr/bin/env python3
"""Retained-data/model comparison only; no Java, game, pack opening or filesystem fixture."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def observe(spec, row, index):
    assert row["id"] == spec["id"] and row["inputAttributes"] == row["inputAttributesAfter"]
    assert type(row["issues"]) is int and row["issues"] in [0, 1]
    assert len(row["matcherEvents"]) <= 1 and len(row["factoryEvents"]) <= 1
    assert all(e["allowed"] is spec["allowLinks"] for e in row["matcherEvents"])
    error, value = 0, 0
    if row["status"] == "threw":
        error = {"java.nio.file.NoSuchFileException": 1, "java.io.IOException": 2}[row["errorClass"]]
    else:
        assert row["status"] == "returned"
        value = {"null": 0, "zip": 1, "directory": 2}[row["result"]]
    factory, binding = 0, 0
    if row["factoryEvents"]:
        event = row["factoryEvents"][0]
        factory = {"zip": 1, "directory": 2}[event["kind"]]
        path = event["absoluteNormalizedPath"]
        if path == spec["path"]: binding = 1
        elif path in ["<capture>/fixtures/regular/payload.zip", "<capture>/fixtures/relative-missing/payload.zip", "<capture>/fixtures/relative-shadow/shadow.zip"]: binding = 2
        elif path == "<capture>/shadow.zip": binding = 3
        else: raise AssertionError("Unselected factory binding: " + path)
    return dict(id=index, error=error, value=value, factory=factory, binding=binding, issues=row["issues"], matcherCalls=len(row["matcherEvents"]))


def load():
    manifest = json.loads((HERE / "pack-detector-captures.json").read_text())
    targets = {t["release"]: t for t in json.loads((HERE / "targets.json").read_text())["javaReferences"]}
    authored = json.loads((HERE / "pack-detector-cases.json").read_text())["cases"]
    assert len(authored) == 16 and len({r["case"] for r in authored}) == 16
    rows, observations, raw_basis = [], [], []
    assert len(manifest["profiles"]) == 5 and {p["release"] for p in manifest["profiles"]} == set(targets)
    for profile in manifest["profiles"]:
        assert profile["target"] == targets[profile["release"]]["id"]
        assert profile["clientSha256"] == targets[profile["release"]]["source"]["clientSha256"]
        capture = HERE / "evidence" / profile["capture"]
        for name, value in profile["publicPayloadSha256"].items(): assert sha(capture / name) == value
        request = json.loads((capture / "request.json").read_text())
        raw = json.loads((capture / "observed.json").read_text())
        receipt = json.loads((capture / "receipt.json").read_text())
        assert raw["schema"] == request["schema"] == receipt["schema"] == 1
        assert raw["cwd"] == "<capture>" and raw["adapterHasSeparateLoader"] is True and raw["adapterSigners"] == 0
        assert raw["originalDetectorSigners"] > 0 and raw["originalValidatorSigners"] > 0
        assert {k: raw[k] for k in profile["profile"]} == profile["profile"]
        assert raw["os"] == "Mac OS X" and raw["architecture"] == "aarch64" and raw["filesystemType"] == "apfs"
        assert raw["javaVersion"].startswith("25." if profile["release"] == "26.3" else "21.")
        assert receipt["fixturesBefore"] == receipt["fixturesAfter"] and receipt["cwdShadowBefore"] == receipt["cwdShadowAfter"]
        assert receipt["cwdShadowBefore"] != receipt["fixturesBefore"]["relative-shadow/shadow.zip"]["sha256"]
        assert len(raw["cases"]) == len(request["cases"]) == 16
        suffix_cases = {r["id"]: r for r in raw["cases"]}
        lower_key = suffix_cases["regular-lowercase-zip"]["inputAttributes"]["fileKey"]
        assert lower_key != "null" and lower_key == suffix_cases["regular-uppercase-zip"]["inputAttributes"]["fileKey"]
        for source, spec, original in zip(authored, request["cases"], raw["cases"], strict=True):
            assert source["case"] == spec["id"] == original["id"]
            assert spec["allowLinks"] is source["allowLinks"] and ["return", "null", "throw"][source["factoryMode"]] == spec["factoryMode"]
            kind = 0 if original["inputAttributes"].get("errorClass") == "java.nio.file.NoSuchFileException" else {"regular": 1, "directory": 2, "symlink": 3, "other": 4}[original["inputAttributes"]["kind"]]
            assert kind == source["entry"]["kind"]
            if kind == 1: assert source["entry"]["zipSuffix"] is spec["path"].endswith(".zip")
            index = len(rows)
            row = {k: copy.deepcopy(v) for k, v in source.items() if k != "case"}
            row.update(id=index, release=profile["release"])
            rows.append(row)
            observations.append(observe(spec, original, index))
            raw_basis.append((spec, original))
    return dict(schema=1, contract="original-pack-detector-v1", callbackProfile="authored-matcher-factories-v1", policy=0, rows=rows), observations, raw_basis


def lean(packet, work, label, batch=False):
    path = work / (label + ".json")
    path.write_text(json.dumps(packet, indent=2) + "\n")
    return subprocess.run([os.environ.get("LEAN", "lean"), "--run", str(HERE / "PackDetectionCase.lean"), *(["--batch"] if batch else []), str(path)],
        cwd=ROOT, env=os.environ | {"LEAN_PATH": os.environ.get("LEAN_PATH", str(ROOT / ".build/formal"))}, text=True, capture_output=True, timeout=30)


def bend(packet, work, label):
    def boolean(value): return "True{}" if value else "False{}"
    def node(raw):
        if raw is None: return "M.Node{0n,0n,False{},False{},0n}"
        return "M.Node{" + ",".join([str(raw["kind"]) + "n", str(raw["identity"] or 0) + "n", boolean(raw["zipSuffix"]), boolean(raw["metadataRegular"]), str(raw["nestedLinks"] or 0) + "n"]) + "}"
    calls = []
    for row in packet["rows"]:
        value = "M.Input{" + ",".join([node(row["entry"]), node(row["rawTarget"]), node(row["parentTarget"]), boolean(row["targetAbsolute"]), boolean(row["allowLinks"]), str(row["factoryMode"]) + "n"]) + "}"
        calls.append("row(" + str(row["id"]) + "n,M.pd_run(" + value + "," + boolean(packet["policy"] == 1) + "))")
    renderer = r'''
def row(id: Nat,result: M.PDOutcome) -> String:
  match result:
    case M.Outcome{error,value,factory,binding,issues,matchers}:
      "{\"id\":" ++ Nat.show(id) ++ ",\"error\":" ++ Nat.show(error) ++ ",\"value\":" ++ Nat.show(value) ++ ",\"factory\":" ++ Nat.show(factory) ++ ",\"binding\":" ++ Nat.show(binding) ++ ",\"issues\":" ++ Nat.show(issues) ++ ",\"matcherCalls\":" ++ Nat.show(matchers) ++ "}"
'''
    path = work / (label + ".bend")
    path.write_text("import Base\nimport ../../../host/minecraft/PackDetection.bend as M\n" + renderer + '\ndef main() -> IO(Unit):\n  IO.write("[" ++ ' + ' ++ "," ++ '.join(calls) + ' ++ "]")\n')
    result = subprocess.run([os.environ.get("BEND", "bend"), str(path)], cwd=ROOT, env=os.environ | {"BEND_NO_TELEMETRY": "1"}, text=True, capture_output=True, timeout=30)
    (work / (label + ".stdout")).write_text(result.stdout)
    (work / (label + ".stderr")).write_text(result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def main():
    work = ROOT / ".build/minecraft/pack-detection-conformance"
    work.mkdir(parents=True, exist_ok=True)
    packet, observed, basis = load()
    result = lean(packet, work, "current")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == observed
    assert bend(packet, work, "current") == observed
    candidate = copy.deepcopy(packet); candidate["policy"] = 1
    proposed = lean(candidate, work, "parent-proposal")
    assert proposed.returncode == 0, proposed.stdout + proposed.stderr
    proposed_rows = json.loads(proposed.stdout)
    assert bend(candidate, work, "parent-proposal") == proposed_rows
    changed = [i for i, (current, later) in enumerate(zip(observed, proposed_rows, strict=True)) if current != later]
    assert changed == [offset + index for offset in range(0, 80, 16) for index in [10, 11]]
    for i in changed: assert proposed_rows[i] == dict(id=i, error=0, value=1, factory=1, binding=2, issues=0, matcherCalls=1)
    negatives = []
    for name in ["schema", "callback", "policy", "release", "duplicate", "needed-suffix", "needed-metadata", "needed-target", "needed-candidate-anchor", "binding", "directory-bound"]:
        changed_packet = copy.deepcopy(packet)
        if name == "schema": changed_packet["schema"] = 2
        elif name == "callback": changed_packet["callbackProfile"] = "production-default-policy"
        elif name == "policy": changed_packet["policy"] = 2
        elif name == "release": changed_packet["rows"][0]["release"] = "unselected"
        elif name == "duplicate": changed_packet["rows"][1]["id"] = 0
        elif name == "needed-suffix": changed_packet["rows"][0]["entry"]["zipSuffix"] = None
        elif name == "needed-metadata": changed_packet["rows"][5]["entry"]["metadataRegular"] = None
        elif name == "needed-target": changed_packet["rows"][8]["rawTarget"] = None
        elif name == "needed-candidate-anchor": changed_packet["policy"] = 1; changed_packet["rows"][8]["targetAbsolute"] = None
        elif name == "binding": changed_packet["rows"][0]["entry"]["identity"] = 0
        else: changed_packet["rows"][5]["entry"]["nestedLinks"] = 2
        negatives.append((name, changed_packet))
    result = lean([p for _, p in negatives], work, "refusals", True)
    assert result.returncode == 0 and json.loads(result.stdout) == [2] * len(negatives)
    unneeded = copy.deepcopy(packet)
    unneeded["rows"][9]["rawTarget"] = None
    unneeded["rows"][12]["entry"]["metadataRegular"] = None
    unneeded["rows"][12]["entry"]["identity"] = None
    accepted = lean(unneeded, work, "unneeded-unknowns")
    assert accepted.returncode == 0 and json.loads(accepted.stdout) == observed
    assert bend(unneeded, work, "unneeded-unknowns") == observed
    premise_controls = []
    for name in ["uppercase-name-is-zip", "relative-target-assumed-parent", "ignored-directory-link-policy", "null-factory-assumed-value"]:
        altered = copy.deepcopy(packet)
        if name == "uppercase-name-is-zip": altered["rows"][2]["entry"]["zipSuffix"] = True
        elif name == "relative-target-assumed-parent": altered["rows"][11]["rawTarget"]["identity"] = 2
        elif name == "ignored-directory-link-policy": altered["rows"][12]["allowLinks"] = True
        else: altered["rows"][14]["factoryMode"] = 0
        changed_result = lean(altered, work, name)
        assert changed_result.returncode == 0 and json.loads(changed_result.stdout) != observed
        assert bend(altered, work, name) == json.loads(changed_result.stdout)
        premise_controls.append(name)
    raw_controls = []
    for index, change in [(0, "lost-factory"), (10, "lost-error"), (11, "parent-target"), (12, "lost-issue")]:
        spec, original = copy.deepcopy(basis[index])
        if change == "lost-factory": original["factoryEvents"] = []
        elif change == "lost-error": original.pop("errorClass"); original.pop("message"); original.update(status="returned", result="null")
        elif change == "parent-target": original["factoryEvents"][0]["absoluteNormalizedPath"] = "<capture>/fixtures/relative-shadow/shadow.zip"
        else: original["issues"] = 0
        try: different = observe(spec, original, index) != observed[index]
        except (AssertionError, KeyError): different = True
        assert different; raw_controls.append(change)
    receipt = dict(schema=1, nativeRows=80, scalarOutcomeFields=6, leanLaws=15, bendLaws=10, proposedDifferentRows=10,
        decoderRefusals=[name for name, _ in negatives], acceptedUnneededUnknowns=["denied-link-target", "denied-directory-metadata-and-binding"],
        rejectedInterpretations=premise_controls, rawObservationControls=raw_controls,
        formalSha256={n: sha(HERE / n) for n in ["PackDetection.lean", "PackDetectionCase.lean", "PackDetection.bend"]},
        basisSha256={n: sha(HERE / n) for n in ["pack-detector-cases.json", "pack-detector-captures.json", "pack_detector_conformance.py"]},
        limits="Quiescent authored fixtures, matcher and pack factories; candidate parent anchoring is model-only, not a native patch or full-game qualification.")
    (work / "conformance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
