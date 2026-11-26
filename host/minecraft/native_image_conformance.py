#!/usr/bin/env python3
"""Compare retained tiny CPU-image observations with Lean/Bend; never runs Java."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROFILE = "mc1.21.1-java21-macos-arm64-lwjgl333-system"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def word(value):
    assert type(value) is str and re.fullmatch("[0-9a-f]{8}", value)
    return int(value, 16)


def observe(spec, raw, index):
    assert spec["id"] == raw["id"]
    meta = raw["metadata"]
    assert type(meta["width"]) is int and type(meta["height"]) is int and meta["format"] == "RGBA"
    error = 0
    if raw["status"] == "threw":
        assert "word" not in raw
        if raw["errorClass"] == "java.lang.IllegalArgumentException":
            assert raw["message"] == f'({spec["x"]}, {spec["y"]}) outside of image bounds (2, 2)'
            error = 1
        else:
            assert raw["errorClass"] == "java.lang.IllegalStateException" and raw["message"] == "Image is not allocated."
            error = 2
    else:
        assert raw["status"] == "returned" and "errorClass" not in raw and "message" not in raw
    pixels = list(map(word, raw["pixels"])) if "pixels" in raw else None
    assert pixels is None or len(pixels) == 4
    return dict(id=index, error=error, word=word(raw["word"]) if "word" in raw else None,
                pixels=pixels, width=meta["width"], height=meta["height"])


def load():
    manifest = json.loads((HERE / "native-image-capture.json").read_text())
    capture = HERE / "evidence" / manifest["capture"]
    assert manifest["schema"] == 1
    assert manifest["exporterSha256"] == sha(HERE / "native_image_observations.py")
    for name, digest in manifest["publicPayloadSha256"].items(): assert sha(capture / name) == digest
    receipt, request, output = [json.loads((capture / n).read_text()) for n in ["receipt.json", "request.json", "observed.json"]]
    assert receipt["schema"] == request["schema"] == output["schema"] == 1 and receipt["release"] == "1.21.1"
    target = next(t for t in json.loads((HERE / "targets.json").read_text())["javaReferences"] if t["release"] == "1.21.1")
    assert receipt["clientSha256"] == target["source"]["clientSha256"] and receipt["metadataSha256"] == target["source"]["metadataSha256"]
    assert sha(capture / "request.json") == receipt["requestSha256"] and sha(capture / "observed.json") == receipt["observedSha256"]
    assert {k: output[k] for k in manifest["profile"]} == manifest["profile"]
    assert output["os"] == "Mac OS X" and output["architecture"] == "aarch64" and output["javaVersion"] == "21.0.13.1"
    assert output["allocatorProperty"] == "system" and output["finallyCloseReturned"] is True and output["originalSigners"] == 4
    assert receipt["originalClientClassesLoaded"] == [request["bindings"]["imageClass"], request["bindings"]["formatClass"]]
    assert receipt["stdlibAllocatorInitialized"] is True and receipt["native"]["name"] == "liblwjgl.dylib"
    assert receipt["loggedNativeLoads"] == ["libnio.dylib", "libzip.dylib", "libnet.dylib", "libjimage.dylib", "liblwjgl.dylib"]
    assert receipt["excludedInitializerPrefixesObserved"] == [] and receipt["processReadback"] == []
    for name, c in zip(["compile", "execute"], receipt["commands"], strict=True):
        assert c["exitCode"] == 0 and c["ownedGroupAbsent"] and not c["timedOut"]
        for stream in ["stdout", "stderr"]: assert sha(capture / (name + "." + stream)) == c[stream + "Sha256"]
    rows, observed, raw_basis = [], [], []
    operations = dict(construct=0, get=1, set=2, close=3, metadata=4)
    for i, (spec, raw) in enumerate(zip(request["steps"], output["events"], strict=True)):
        op = operations[spec["operation"]]
        row = dict(id=i, operation=op, x=None, y=None, word=None)
        if op in [1, 2]:
            assert type(spec["x"]) is int and type(spec["y"]) is int and -1 <= spec["x"] <= 2 and -1 <= spec["y"] <= 2
            row.update(x=spec["x"] + 1, y=spec["y"] + 1)
        if op == 2: row["word"] = word(spec["word"])
        rows.append(row); observed.append(observe(spec, raw, i)); raw_basis.append((spec, raw))
    assert len(rows) == 16 and rows[0]["operation"] == 0
    return dict(schema=1, contract="original-cpu-image-v1", profile=PROFILE, rows=rows), observed, raw_basis


def lean(packet, work, label, batch=False):
    path = work / (label + ".json"); path.write_text(json.dumps(packet, indent=2) + "\n")
    result = subprocess.run([os.environ.get("LEAN", "lean"), "--run", str(HERE / "NativeImageCase.lean"), *(["--batch"] if batch else []), str(path)],
        cwd=ROOT, env=os.environ | {"LEAN_PATH": os.environ.get("LEAN_PATH", str(ROOT / ".build/formal"))}, text=True, capture_output=True, timeout=30)
    (work / (label + ".lean.stdout")).write_text(result.stdout); (work / (label + ".lean.stderr")).write_text(result.stderr)
    return result


def bend(packet, work, label):
    rows = ["Input{" + ",".join(str(r[k] or 0) + ("" if k == "word" else "n") for k in ["id", "operation", "x", "y", "word"]) + "}" for r in packet["rows"]]
    renderer = r'''
type Input is Data:
  Input{id: Nat,operation: Nat,x: Nat,y: Nat,word: U32}
def nums_tail(xs: List<&2,U32>) -> String:
  match xs:
    case Nil{}: ""
    case head <> tail: "," ++ U32.show(head) ++ nums_tail(tail)
def nums(xs: List<&2,U32>) -> String:
  match xs:
    case Nil{}: "[]"
    case head <> tail: "[" ++ U32.show(head) ++ nums_tail(tail) ++ "]"
def optional(xs: List<&2,U32>) -> String:
  match xs:
    case Nil{}: "null"
    case head <> tail: U32.show(head)
def row(id: Nat,reply: M.ImageReply) -> String:
  match reply:
    case M.Reply{state,error,word}:
      match state:
        case M.State{closed,words}:
          "{\"id\":" ++ Nat.show(id) ++ ",\"error\":" ++ Nat.show(error) ++ ",\"word\":" ++ optional(word) ++ ",\"pixels\":" ++ Bool.pick(String,closed,"null",nums(words)) ++ ",\"width\":2,\"height\":2}"
def trace(inputs: List<&2,Input>,state: M.ImageState) -> String:
  match inputs:
    case Nil{}: ""
    case input <> +tail:
      match input:
        case Input{id,op,x,y,word}:
          +reply=M.image_step(state,op,x,y,word)
          row(id,reply) ++ Bool.pick(String,List.is_empty(&2,Input,tail),"","," ++ trace(tail,M.image_state(reply)))
'''
    path = work / (label + ".bend")
    path.write_text("import Base\nimport CpuImage.bend as M\n" + renderer + '\ndef main() -> IO(Unit):\n  IO.write("[" ++ trace([' + ",".join(rows) + '],M.image_initial()) ++ "]")\n')
    # Place a model copy beside the generated renderer so the import is stable
    # in both normal and isolated public checkouts, independent of work depth.
    (work / "CpuImage.bend").write_bytes((HERE.parent / "java/CpuImage.bend").read_bytes())
    result = subprocess.run([os.environ.get("BEND", "bend"), str(path)], cwd=ROOT,
        env=os.environ | {"BEND_NO_TELEMETRY": "1"}, text=True, capture_output=True, timeout=30)
    (work / (label + ".bend.stdout")).write_text(result.stdout); (work / (label + ".bend.stderr")).write_text(result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def require_receipt(computed, path):
    assert json.loads(path.read_text()) == computed, "Portable CPU image receipt is stale; review and explicitly refresh."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-receipt", action="store_true")
    args = parser.parse_args()
    work = ROOT / ".build/minecraft/native-image-conformance"; work.mkdir(parents=True, exist_ok=True)
    packet, observed, basis = load()
    result = lean(packet, work, "current"); assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == observed
    assert bend(packet, work, "current") == observed
    negatives = []
    for name in ["schema", "contract", "profile", "operation", "needed-coordinate", "coordinate-range", "needed-word", "word-range", "duplicate", "missing-construction", "second-construction", "too-many"]:
        p = copy.deepcopy(packet)
        if name == "schema": p["schema"] = 2
        elif name == "contract": p["contract"] = "decoded-image-safe"
        elif name == "profile": p["profile"] = "mc26.3-java25-windows"
        elif name == "operation": p["rows"][1]["operation"] = 5
        elif name == "needed-coordinate": p["rows"][1]["x"] = None
        elif name == "coordinate-range": p["rows"][1]["y"] = 4
        elif name == "needed-word": p["rows"][2]["word"] = None
        elif name == "word-range": p["rows"][2]["word"] = 4294967296
        elif name == "duplicate": p["rows"][1]["id"] = 0
        elif name == "missing-construction": p["rows"] = p["rows"][1:]
        elif name == "second-construction": p["rows"][1]["operation"] = 0
        else: p["rows"] = p["rows"] * 5
        negatives.append((name, p))
    r = lean([p for _, p in negatives], work, "refusals", True)
    assert r.returncode == 0 and json.loads(r.stdout) == [2] * len(negatives)
    changed = []
    for name, i, delta in [("different-word", 2, dict(word=0)), ("different-coordinate", 2, dict(x=2)),
                            ("close-as-metadata", 9, dict(operation=4)), ("valid-closed-as-outside", 10, dict(x=3))]:
        p = copy.deepcopy(packet); p["rows"][i].update(delta)
        r = lean(p, work, name); assert r.returncode == 0
        assert json.loads(r.stdout) != observed and bend(p, work, name) != observed
        changed.append(name)
    controls = []
    for name, i in [("lost-write", 2), ("cleared-metadata", 9), ("read-after-close", 10), ("bounds-as-closed", 12), ("repeat-close-failure", 15), ("fabricated-closed-pixels", 14)]:
        spec, raw = copy.deepcopy(basis[i])
        if name == "lost-write": raw["pixels"][0] = "00000000"
        elif name == "cleared-metadata": raw["metadata"]["width"] = 0
        elif name == "read-after-close": raw = dict(id=raw["id"], status="returned", word="12345678", metadata=raw["metadata"])
        elif name == "bounds-as-closed": raw.update(errorClass="java.lang.IllegalStateException", message="Image is not allocated.")
        elif name == "repeat-close-failure": raw.update(status="threw", errorClass="java.lang.IllegalStateException", message="Image is not allocated.")
        else: raw["pixels"] = ["12345678", "89abcdef", "ffffffff", "00000000"]
        try: refused = observe(spec, raw, i) != observed[i]
        except (AssertionError, KeyError): refused = True
        assert refused; controls.append(name)
    receipt = dict(schema=1, traceSteps=16, leanLaws=14, bendLaws=9, requestedPixelBytes=16,
        decoderRefusals=[n for n, _ in negatives], changedPremises=changed, rawObservationControls=controls,
        formalSha256={p: sha(ROOT / p) for p in ["host/java/CpuImage.lean", "host/java/CpuImage.bend", "host/minecraft/NativeImageCase.lean"]},
        basisSha256={p: sha(HERE / p) for p in ["native-image-capture.json", "native_image_conformance.py"]},
        limits="One original1.21.1 successful zeroed2x2 CPU allocation,Java21/macOSarm64/LWJGL3.3.3 system;no decode,GPU,physical reclamation,concurrency or other host/client qualification.")
    public = HERE / "evidence/native-image-conformance.json"
    if args.refresh_receipt: public.write_text(json.dumps(receipt, indent=2) + "\n")
    require_receipt(receipt, public)
    stale = copy.deepcopy(receipt); stale["traceSteps"] = 15
    try: require_receipt(stale, public)
    except AssertionError: pass
    else: raise AssertionError("Stale receipt control passed.")
    (work / "conformance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
