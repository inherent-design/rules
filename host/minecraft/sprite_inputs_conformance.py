#!/usr/bin/env python3
"""Retained constructed-sprite/model comparison; never runs Java or a game."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

from sprite_inputs_observations import observe

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load():
    manifest = json.loads((HERE / "sprite-inputs-capture.json").read_text())
    capture = HERE / "evidence" / manifest["capture"]
    assert manifest["schema"] == 1 and manifest["exporterSha256"] == sha(HERE / "sprite_inputs_observations.py")
    for name, digest in manifest["publicPayloadSha256"].items(): assert sha(capture / name) == digest
    r, request, output = [json.loads((capture / n).read_text()) for n in ["receipt.json", "request.json", "observed.json"]]
    assert r["schema"] == request["schema"] == output["schema"] == 1 and r["release"] == "1.21.1"
    assert sha(capture / "request.json") == r["requestSha256"] and sha(capture / "observed.json") == r["outputs"]["observed.json"]
    target = next(t for t in json.loads((HERE / "targets.json").read_text())["javaReferences"] if t["release"] == "1.21.1")
    assert r["clientSha256"] == target["source"]["clientSha256"] and r["metadataSha256"] == target["source"]["metadataSha256"]
    assert {k: output[k] for k in manifest["profile"]} == manifest["profile"]
    assert output["javaVersion"] == "21.0.13.1" and output["os"] == "Mac OS X" and output["architecture"] == "aarch64" and output["originalSigners"] == 4
    assert output["nameContext"] == "null adapter;no identifier construction" and output["metadataContext"] == "original ResourceMetadata.EMPTY;no metadata parsing"
    assert r["forbiddenInitializersObserved"] == [] and r["excludedLibraryInitializersObserved"] == [] and r["exactCaptureProcessReadback"] == []
    assert r["stdlibAllocatorInitialized"] is True and r["native"]["name"] == "liblwjgl.dylib" and len(r["loadedOriginalClassSha256"]) == 18
    assert r["loggedNativeLoads"] == ["libnio.dylib", "libzip.dylib", "libnet.dylib", "libjimage.dylib", "liblwjgl.dylib"]
    for name in ["sprite_inputs_probe.py", "SpriteInputsProbe.java", "mappings.py"]: assert sha(HERE / name) == r["producerSha256"][name]
    assert sha(HERE.parent / "java/arena_probe.py") == r["producerSha256"]["arena_probe.py"]
    for label, command in zip(["compile", "execute"], r["commands"], strict=True):
        assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
        for stream in ["stdout", "stderr"]: assert sha(capture / (label + "." + stream)) == command[stream + "Sha256"]
    rows, observed, basis = [], [], []
    for i, (spec, raw) in enumerate(zip(request["cases"], output["cases"], strict=True)):
        assert type(spec["aliasLifecycle"]) is bool
        rows.append({k: spec[k] for k in ["width", "height", "masks", "aliasLifecycle"]} | dict(id=i))
        observed.append(observe(spec, raw, i)); basis.append((spec, raw))
    assert len(rows) == 26
    return dict(schema=1, contract="constructed-sprite-inputs-v1", release="1.21.1", nameContext="null", metadataContext="empty", rows=rows), observed, basis


def lean(packet, work, label, batch=False):
    path = work / (label + ".json"); path.write_text(json.dumps(packet, indent=2) + "\n")
    r = subprocess.run([os.environ.get("LEAN", "lean"), "--run", str(HERE / "SpriteInputsCase.lean"), *(["--batch"] if batch else []), str(path)],
        cwd=ROOT, env=os.environ | {"LEAN_PATH": os.environ.get("LEAN_PATH", str(ROOT / ".build/formal"))}, text=True, capture_output=True, timeout=30)
    (work / (label + ".lean.stdout")).write_text(r.stdout); (work / (label + ".lean.stderr")).write_text(r.stderr)
    return r


def bend(packet, work, label):
    calls = ["row(" + str(r["id"]) + "n," + str(r["width"]) + "n,[" + ",".join(map(str, r["masks"])) + "]," + ("True{}" if r["aliasLifecycle"] else "False{}") + ")" for r in packet["rows"]]
    renderer = r'''
import Base
import host/minecraft/SpriteInputs.bend as M
def jb(b: Bool) -> String:
  Bool.pick(String,b,"true","false")
def num_tail(values: List<&2,Nat>) -> String:
  match values:
    case Nil{}: ""
    case head <> tail: "," ++ Nat.show(head) ++ num_tail(tail)
def nums(values: List<&2,Nat>) -> String:
  match values:
    case Nil{}: "[]"
    case head <> tail: "[" ++ Nat.show(head) ++ num_tail(tail) ++ "]"
def bool_tail(values: List<&2,Bool>) -> String:
  match values:
    case Nil{}: ""
    case head <> tail: "," ++ jb(head) ++ bool_tail(tail)
def bools(values: List<&2,Bool>) -> String:
  match values:
    case Nil{}: "[]"
    case head <> tail: "[" ++ jb(head) ++ bool_tail(tail) ++ "]"
def matrices(frames: List<&2,Nat>,+width: Nat,+masks: List<&2,U32>) -> String:
  match frames:
    case Nil{}: ""
    case +head <> +tail:
      "{\"frame\":" ++ Nat.show(head) ++ ",\"transparent\":" ++ bools(M.sprite_cells(width,M.mask_at(masks,head))) ++ "}" ++ Bool.pick(String,List.is_empty(&2,Nat,tail),"","," ++ matrices(tail,width,masks))
def alias_state(+frames: List<&2,Nat>) -> String:
  "{\"beforeMutation\":" ++ jb(M.alias_before_transparent()) ++ ",\"afterMutation\":" ++ jb(M.alias_after_transparent()) ++ ",\"inputError\":" ++ Nat.show(M.alias_closed_error()) ++ ",\"spriteError\":" ++ Nat.show(M.alias_closed_error()) ++ ",\"widthAfterClose\":2,\"heightAfterClose\":2,\"framesAfterClose\":" ++ nums(frames) ++ "}"
def row(id: Nat,+width: Nat,+masks: List<&2,U32>,alias: Bool) -> String:
  +frames=M.sprite_frames(masks)
  "{\"id\":" ++ Nat.show(id) ++ ",\"width\":" ++ Nat.show(width) ++ ",\"height\":2,\"uniqueFrames\":" ++ nums(frames) ++ ",\"matrices\":[" ++ matrices(frames,width,masks) ++ "],\"aliasState\":" ++ Bool.pick(String,alias,alias_state(frames),"null") ++ "}"
'''
    for name in ["host/minecraft/SpriteInputs.bend", "host/java/CpuImage.bend"]:
        p = work / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes((ROOT / name).read_bytes())
    path = work / (label + ".bend")
    path.write_text(renderer + '\ndef main() -> IO(Unit):\n  IO.write("[" ++ ' + (' ++ "," ++ '.join(calls) if calls else '""') + ' ++ "]")\n')
    r = subprocess.run([os.environ.get("BEND", "bend"), str(path)], cwd=ROOT,
        env=os.environ | {"BEND_NO_TELEMETRY": "1"}, text=True, capture_output=True, timeout=30)
    (work / (label + ".bend.stdout")).write_text(r.stdout); (work / (label + ".bend.stderr")).write_text(r.stderr)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)


def require_receipt(result, path):
    assert json.loads(path.read_text()) == result, "Constructed sprite comparison receipt stale; review and explicitly refresh."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-receipt", action="store_true")
    args = parser.parse_args()
    work = ROOT / ".build/minecraft/sprite-inputs-conformance"; work.mkdir(parents=True, exist_ok=True)
    packet, observed, basis = load()
    r = lean(packet, work, "current"); assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout) == observed == bend(packet, work, "current")
    negatives = []
    for name in ["schema", "contract", "release", "identifier-context", "metadata-context", "needed-masks", "empty-masks", "width", "height", "image-budget", "mask-range", "alias-profile", "duplicate", "too-many"]:
        p = copy.deepcopy(packet)
        if name == "schema": p["schema"] = 2
        elif name == "contract": p["contract"] = "full-sprite-loading"
        elif name == "release": p["release"] = "26.3"
        elif name == "identifier-context": p["nameContext"] = "resolved-resource"
        elif name == "metadata-context": p["metadataContext"] = "decoded-animation"
        elif name == "needed-masks": p["rows"][0]["masks"] = None
        elif name == "empty-masks": p["rows"][0]["masks"] = []
        elif name == "width": p["rows"][0]["width"] = 1
        elif name == "height": p["rows"][0]["height"] = 3
        elif name == "image-budget": p["rows"][16]["masks"] = [0, 0]
        elif name == "mask-range": p["rows"][0]["masks"] = [16]
        elif name == "alias-profile": p["rows"][1]["aliasLifecycle"] = True
        elif name == "duplicate": p["rows"][1]["id"] = 0
        else: p["rows"] = p["rows"] * 2
        negatives.append((name, p))
    r = lean([p for _, p in negatives], work, "refusals", True)
    assert r.returncode == 0 and json.loads(r.stdout) == [2] * len(negatives)
    premises = []
    for name, i, delta in [("different-static-mask", 0, dict(masks=[1])), ("different-animation-order", 21, dict(masks=[8, 1])),
                            ("different-width", 16, dict(width=2)), ("omit-alias-lifecycle", 25, dict(aliasLifecycle=False))]:
        p = copy.deepcopy(packet); p["rows"][i].update(delta)
        r = lean(p, work, name); assert r.returncode == 0
        assert json.loads(r.stdout) != observed and bend(p, work, name) != observed
        premises.append(name)
    controls = []
    for name, i in [("static-frame-as-zero", 0), ("lost-opacity", 15), ("swapped-animation", 21), ("copied-input-image", 25),
                    ("input-readable-after-sprite-close", 25), ("metadata-cleared-at-close", 25), ("numeric-transparency", 0), ("missing-cleanup", 0)]:
        spec, raw = copy.deepcopy(basis[i])
        if name == "static-frame-as-zero": raw["uniqueFrames"] = [0]; raw["matrices"][0]["frame"] = 0
        elif name == "lost-opacity": raw["matrices"][0]["transparent"][0] = True
        elif name == "swapped-animation": raw["matrices"][0]["transparent"] = list(reversed(raw["matrices"][0]["transparent"]))
        elif name == "copied-input-image": raw["afterMutation"] = True
        elif name == "input-readable-after-sprite-close": raw["inputImageAfterSpriteClose"] = "returned"
        elif name == "metadata-cleared-at-close": raw["widthAfterClose"] = 0
        elif name == "numeric-transparency": raw["matrices"][0]["transparent"][0] = 1
        else: raw["spriteCleanupReturned"] = False
        try: refused = observe(spec, raw, i) != observed[i]
        except (AssertionError, KeyError): refused = True
        assert refused; controls.append(name)
    result = dict(schema=1, scenarios=26, matrixQueries=130, aliasQueries=2, guardedClosedAccesses=2, maxRequestedPixelBytes=32,
        leanLaws=13, bendLaws=11, decoderRefusals=[n for n, _ in negatives], changedPremises=premises, changedRawObservations=controls,
        formalSha256={name: sha(ROOT / name) for name in ["host/minecraft/SpriteInputs.lean", "host/minecraft/SpriteInputs.bend", "host/minecraft/SpriteInputsCase.lean", "host/java/CpuImage.lean", "host/java/CpuImage.bend"]},
        basisSha256={name: sha(HERE / name) for name in ["sprite-inputs-capture.json", "sprite_inputs_observations.py", "sprite_inputs_conformance.py"]},
        limits="Constructed1.21.1 SpriteContents/explicitFrameSize/originalemptyMetadata/nullname on Java21/macOSarm64. Not metadata/identifier decode,fullsprite loading,ticker,generator,bake,GPU/game,other profile or physical-memory qualification.")
    public = HERE / "evidence/sprite-inputs-conformance.json"
    if args.refresh_receipt: public.write_text(json.dumps(result, indent=2) + "\n")
    require_receipt(result, public)
    stale = copy.deepcopy(result); stale["matrixQueries"] = 129
    try: require_receipt(stale, public)
    except AssertionError: pass
    else: raise AssertionError("Stale receipt accepted.")
    (work / "conformance.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
