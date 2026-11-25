#!/usr/bin/env python3
"""Pure retained-data/model replay. Never invokes Java, Minecraft, or a PNG decoder."""
import argparse
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


def observe(spec, raw, index):
    assert spec["id"] == raw["id"]
    data = bytes.fromhex(spec["hex"])
    before = dict(order=spec["order"], position=spec["position"], limit=spec["limit"], capacity=33,
        remaining=spec["limit"] - spec["position"], readOnly=spec["readOnly"], bytesSha256=hashlib.sha256(data).hexdigest())
    assert len(data) == 33 and raw["before"] == before
    after = raw["after"]
    assert after["capacity"] == 33 and after["order"] in ["LITTLE_ENDIAN", "BIG_ENDIAN"]
    assert raw["status"] in ["returned", "threw"]
    error = 0 if raw["status"] == "returned" else {"java.io.IOException": 1, "java.lang.IndexOutOfBoundsException": 2}[raw["errorClass"]]
    return dict(id=index, error=error, littleEndian=after["order"] == "LITTLE_ENDIAN", position=after["position"],
        limit=after["limit"], remaining=after["remaining"], readOnly=after["readOnly"], bytesUnchanged=after["bytesSha256"] == before["bytesSha256"])


def load():
    manifest = json.loads((HERE / "image-header-captures.json").read_text())
    targets = {t["release"]: t for t in json.loads((HERE / "targets.json").read_text())["javaReferences"]}
    assert manifest["schema"] == 1 and len(manifest["profiles"]) == 6
    assert [p["release"] for p in manifest["profiles"]] == [*targets, "java17"]
    rows, arithmetic, outcomes, math_outcomes, raw_basis = [], [], [], [], []
    for p in manifest["profiles"]:
        capture = HERE / "evidence" / p["capture"]
        for name, digest in p["publicPayloadSha256"].items(): assert sha(capture / name) == digest
        r, request, observed = [json.loads((capture / name).read_text()) for name in ["receipt.json", "request.json", "observed.json"]]
        assert r["schema"] == request["schema"] == observed["schema"] == 1 and r["release"] == p["release"]
        assert sha(capture / "request.json") == r["requestSha256"] and sha(capture / "observed.json") == r["observed.jsonSha256"]
        assert {k: observed[k] for k in p["profile"]} == p["profile"]
        assert observed["os"] == "Mac OS X" and observed["architecture"] == "aarch64"
        assert observed["javaVersion"].startswith("17." if p["release"] == "java17" else "25." if p["release"] == "26.3" else "21.")
        if p["release"] == "java17": assert r["clientSha256"] is None and r["originalClientClassesLoaded"] == [] and request["cases"] == []
        else:
            assert p["clientSha256"] == r["clientSha256"] == targets[p["release"]]["source"]["clientSha256"]
            assert r["originalClientClassesLoaded"] == [r["originalClass"]] and observed["originalSigners"] > 0
        assert len(r["commands"]) == 2
        for name, command in zip(["compile", "execute"], r["commands"], strict=True):
            assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
            for stream in ["stdout", "stderr"]: assert sha(capture / (name + "." + stream)) == command[stream + "Sha256"]
        for spec, raw in zip(request["cases"], observed["cases"], strict=True):
            data = bytes.fromhex(spec["hex"])
            index = len(rows)
            rows.append(dict(id=index, release=p["release"], limit=spec["limit"], position=spec["position"], littleEndian=spec["order"] == "LITTLE_ENDIAN", readOnly=spec["readOnly"],
                magic=data[:8] == bytes.fromhex("89504e470d0a1a0a"), length13=int.from_bytes(data[8:12], "big") == 13,
                ihdr=data[12:16] == b"IHDR", widthBits=int.from_bytes(data[16:20], "big"), heightBits=int.from_bytes(data[20:24], "big"), depth=data[24], color=data[25]))
            outcomes.append(observe(spec, raw, index)); raw_basis.append((spec, raw))
        for spec, raw in zip(request["arithmetic"], observed["arithmetic"], strict=True):
            assert spec["id"] == raw["id"]
            index = len(arithmetic)
            arithmetic.append(dict(id=index, java=int(observed["javaVersion"].split(".")[0]), widthBits=spec["width"], heightBits=spec["height"]))
            checked = "checked" in raw
            if not checked: assert raw["checkedError"] == "java.lang.ArithmeticException"
            else: assert int(raw["checked"]) == 4 * spec["width"] * spec["height"] * 2
            assert -(2**63) <= int(raw["wrappedLong"]) < 2**63 and -(2**31) <= int(raw["narrowedInt"]) < 2**31
            math_outcomes.append(dict(id=index, word=str(int(raw["wrappedLong"]) % 2**64), narrowWord=str(int(raw["narrowedInt"]) % 2**64), roundtrip=raw["roundtrip"], checked=checked))
    assert len(rows) == 165 and len(arithmetic) == 12
    return dict(schema=1, contract="original-png-header-v1", rows=rows, arithmetic=arithmetic), dict(rows=outcomes, arithmetic=math_outcomes), raw_basis


def lean(packet, work, label, batch=False):
    path = work / (label + ".json"); path.write_text(json.dumps(packet, indent=2) + "\n")
    result = subprocess.run([os.environ.get("LEAN", "lean"), "--run", str(HERE / "ImageHeaderCase.lean"), *(["--batch"] if batch else []), str(path)], cwd=ROOT,
        env=os.environ | {"LEAN_PATH": os.environ.get("LEAN_PATH", str(ROOT / ".build/formal"))}, capture_output=True, text=True, timeout=40)
    (work / (label + ".lean.stdout")).write_text(result.stdout); (work / (label + ".lean.stderr")).write_text(result.stderr)
    return result


def bend(packet, work, label):
    def boolean(v): return "True{}" if v else "False{}"
    headers = []
    for r in packet["rows"]:
        generation = 2 if r["release"] == "26.3" else 1 if r["release"] == "1.21.11" else 0
        args = [str(generation) + "n", str(r["limit"]) + "n", *[boolean(bool(r[k])) for k in ["magic", "length13", "ihdr"]],
            str(r["widthBits"] or 0), str(r["heightBits"] or 0), str(r["depth"] or 0) + "n", str(r["color"] or 0) + "n"]
        headers.append("header(" + ",".join([str(r["id"]) + "n", "H.Input{" + ",".join(args) + "}", str(r["position"]) + "n", str(r["limit"]) + "n", boolean(r["littleEndian"]), boolean(r["readOnly"])]) + ")")
    math = ["arithmetic(" + str(r["id"]) + "n," + str(r["widthBits"]) + "," + str(r["heightBits"]) + ")" for r in packet["arithmetic"]]
    render = r'''
def jsbool(v: Bool) -> String:
  Bool.pick(String,v,"true","false")
def header(id: Nat,input: H.HeaderInput,+position: Nat,+limit: Nat,little: Bool,readonly: Bool) -> String:
  +error=H.header_error(input)
  "{\"id\":" ++ Nat.show(id) ++ ",\"error\":" ++ Nat.show(error) ++ ",\"littleEndian\":" ++ jsbool(H.header_little(error,little)) ++ ",\"position\":" ++ Nat.show(position) ++ ",\"limit\":" ++ Nat.show(limit) ++ ",\"remaining\":" ++ Nat.show(Nat.sub(limit,position)) ++ ",\"readOnly\":" ++ jsbool(readonly) ++ ",\"bytesUnchanged\":true}"
def words(word: W.LongBits) -> String:
  match word:
    case W.Bits{low,high}: "[" ++ U32.show(low) ++ "," ++ U32.show(high) ++ "]"
def arithmetic(id: Nat,+width: U32,+height: U32) -> String:
  +word=W.long_estimate(width,height)
  "{\"id\":" ++ Nat.show(id) ++ ",\"word\":" ++ words(word) ++ ",\"narrowWord\":" ++ words(W.long_narrow(word)) ++ ",\"roundtrip\":" ++ jsbool(W.long_roundtrip(word)) ++ ",\"checked\":" ++ jsbool(W.long_checked(width,height)) ++ "}"
'''
    def array(calls): return '"[" ++ ' + (' ++ "," ++ '.join(calls) if calls else '""') + ' ++ "]"'
    path = work / (label + ".bend")
    # work is a direct child of .build/minecraft, matching existing retained runners.
    path.write_text("import Base\nimport ../../../host/minecraft/ImageHeader.bend as H\nimport ../../../host/java/Word64.bend as W\n" + render + '\ndef main() -> IO(Unit):\n  IO.write("{\\"rows\\":" ++ (' + array(headers) + ') ++ ",\\"arithmetic\\":" ++ (' + array(math) + ') ++ "}")\n')
    result = subprocess.run([os.environ.get("BEND", "bend"), str(path)], cwd=ROOT, env=os.environ | {"BEND_NO_TELEMETRY": "1"}, capture_output=True, text=True, timeout=50)
    (work / (label + ".bend.stdout")).write_text(result.stdout); (work / (label + ".bend.stderr")).write_text(result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    raw = json.loads(result.stdout)
    for r in raw["arithmetic"]:
        for key in ["word", "narrowWord"]:
            low, high = r[key]; assert 0 <= low < 2**32 and 0 <= high < 2**32
            r[key] = str(low + high * 2**32)
    return raw


def require_receipt(receipt, public):
    assert json.loads(public.read_text()) == receipt, "Portable image-header receipt is stale; review and explicitly refresh."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-receipt", action="store_true", help="Explicitly refresh the portable proof/replay receipt after reviewed changes.")
    args = parser.parse_args()
    work = ROOT / ".build/minecraft/image-header-conformance"; work.mkdir(parents=True, exist_ok=True)
    packet, observed, basis = load()
    result = lean(packet, work, "current"); assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == observed
    assert bend(packet, work, "current") == observed
    negatives = []
    for name in ["schema", "contract", "release", "limit", "position", "duplicate", "needed-magic", "needed-depth", "needed-width", "wide-int", "java18", "nonpositive-math", "too-many"]:
        p = copy.deepcopy(packet)
        if name == "schema": p["schema"] = 2
        elif name == "contract": p["contract"] = "full-png-decoder"
        elif name == "release": p["rows"][0]["release"] = "unselected"
        elif name == "limit": p["rows"][0]["limit"] = 34
        elif name == "position": p["rows"][0]["position"] = 34
        elif name == "duplicate": p["rows"][1]["id"] = 0
        elif name == "needed-magic": p["rows"][0]["magic"] = None
        elif name == "needed-depth": p["rows"][132]["depth"] = None
        elif name == "needed-width": p["rows"][151]["widthBits"] = None
        elif name == "wide-int": p["rows"][151]["widthBits"] = 2**32
        elif name == "java18": p["arithmetic"][0]["java"] = 18
        elif name == "nonpositive-math": p["arithmetic"][0]["widthBits"] = 0
        else: p["rows"] = p["rows"] * 2
        negatives.append((name, p))
    refusals = lean([p for _, p in negatives], work, "refusals", True)
    assert refusals.returncode == 0 and json.loads(refusals.stdout) == [2] * len(negatives), refusals.stdout + refusals.stderr
    unneeded = copy.deepcopy(packet)
    unneeded["rows"][1]["magic"] = None
    unneeded["rows"][0]["depth"] = None
    unneeded["rows"][132]["widthBits"] = None
    accepted = lean(unneeded, work, "unneeded")
    assert accepted.returncode == 0 and json.loads(accepted.stdout) == observed
    assert bend(unneeded, work, "unneeded") == observed
    model_only = copy.deepcopy(packet); model_only["rows"] = []; model_only["arithmetic"] = []
    for width, height in [(0, 0), (65535, 65535), (65536, 65536), (2147483647, 2147483647),
            (4294967295, 1), (2147483648, 1), (4294967295, 4294967295), (2147483648, 4294967295)]:
        row = copy.deepcopy(packet["rows"][132]); row.update(id=len(model_only["rows"]), widthBits=width, heightBits=height, depth=16)
        model_only["rows"].append(row)
    modeled = lean(model_only, work, "model-only-word-boundaries")
    assert modeled.returncode == 0 and bend(model_only, work, "model-only-word-boundaries") == json.loads(modeled.stdout)
    interpretations = []
    for name, index, key, value in [("old-size-as-new", 10, "release", "26.3"), ("absolute-as-relative", 31, "limit", 1), ("invalid-depth-as-allowed", 148, "depth", 8), ("huge-pair-as-small", 152, "widthBits", 2)]:
        p = copy.deepcopy(packet); p["rows"] = [p["rows"][index]]; p["arithmetic"] = []; p["rows"][0][key] = value
        if name == "absolute-as-relative": p["rows"][0]["position"] = 0
        r = lean(p, work, name); assert r.returncode == 0, r.stdout + r.stderr
        assert json.loads(r.stdout)["rows"] != [observed["rows"][index]]
        assert bend(p, work, name) == json.loads(r.stdout); interpretations.append(name)
    raw_controls = []
    for name, index, key, value in [("lost-order-effect", 11, "order", "LITTLE_ENDIAN"), ("lost-position", 31, "position", 0), ("lost-limit", 10, "limit", 33), ("changed-byte-content", 0, "bytesSha256", "0" * 64), ("lost-readonly", 27, "readOnly", False), ("lost-remaining", 31, "remaining", 33)]:
        spec, raw = copy.deepcopy(basis[index]); raw["after"][key] = value
        assert observe(spec, raw, index) != observed["rows"][index]; raw_controls.append(name)
    spec, raw = copy.deepcopy(basis[11]); raw["status"] = "returned"
    assert observe(spec, raw, 11) != observed["rows"][11]; raw_controls.append("lost-error")
    formal = ["ImageHeader.lean", "ImageHeaderCase.lean", "ImageHeader.bend", "../java/Word64.lean", "../java/Word64.bend"]
    receipt = dict(schema=1, headerCalls=165, arithmeticCalls=12, scalarHeaderFields=7, leanLaws=26, bendLaws=20,
        decoderRefusals=[n for n, _ in negatives], acceptedUnneededUnknowns=["short-magic", "old-depth", "depth8-width"],
        rejectedInterpretations=interpretations, rawObservationControls=raw_controls, additionalModelOnlyWordCases=8,
        formalSha256={n: sha(HERE / n) for n in formal}, basisSha256={n: sha(HERE / n) for n in ["image-header-captures.json", "image_header_conformance.py"]},
        limits="Only original header predicate and buffer effects; JDK arithmetic calibration, not PNG validity, downstream STB/NativeImage allocation or GPU/game behavior.")
    public = HERE / "evidence/image-header-conformance.json"
    if args.refresh_receipt: public.write_text(json.dumps(receipt, indent=2) + "\n")
    require_receipt(receipt, public)
    stale = copy.deepcopy(receipt); stale["headerCalls"] -= 1
    try: require_receipt(stale, public)
    except AssertionError: pass
    else: raise AssertionError("Stale image-header receipt control unexpectedly passed.")
    (work / "conformance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
