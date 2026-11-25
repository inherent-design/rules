#!/usr/bin/env python3
"""Retained literal-record/model comparison only; no Java, codec, state, or game run."""
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


def scalars(value):
    assert type(value) is str
    result = list(map(ord, value))
    assert all(n <= 1114111 and not 55296 <= n <= 57343 for n in result)
    return result


def observe(spec, raw, index):
    assert spec["id"] == raw["id"] and raw["inputUtf16Length"] == len(spec["value"].encode("utf-16-le")) // 2
    empty = dict(id=index, error=1, value=[], negated=False, encoded=[], reparseAttempted=False,
        reparseError=0, reparsedValue=[], reparsedNegated=False, equalAfterReparse=False)
    if raw["status"] == "threw":
        assert raw["errorClass"] == "java.lang.IllegalArgumentException" and raw["message"] == "Empty term"
        assert "term" not in raw and "reparseStatus" not in raw
        return empty
    assert raw["status"] == "returned" and type(raw["term"]["negated"]) is bool
    term = raw["term"]
    result = empty | dict(error=0, value=scalars(term["value"]), negated=term["negated"], encoded=scalars(term["encoded"]), reparseAttempted=True)
    if raw["reparseStatus"] == "threw":
        assert raw["reparseErrorClass"] == "java.lang.IllegalArgumentException" and "reparsed" not in raw
        result["reparseError"] = 1
    else:
        assert raw["reparseStatus"] == "returned" and type(raw["reparsed"]["negated"]) is bool and type(raw["equalAfterReparse"]) is bool
        next_term = raw["reparsed"]
        assert raw["equalAfterReparse"] == (term["value"] == next_term["value"] and term["negated"] == next_term["negated"])
        result.update(reparsedValue=scalars(next_term["value"]), reparsedNegated=next_term["negated"], equalAfterReparse=raw["equalAfterReparse"])
    return result


def load():
    manifest = json.loads((HERE / "block-term-captures.json").read_text())
    targets = {t["release"]: t for t in json.loads((HERE / "targets.json").read_text())["javaReferences"]}
    assert manifest["schema"] == 1 and [p["release"] for p in manifest["profiles"]] == ["1.21.5", "1.21.11", "26.3"]
    rows, observed, raw_basis = [], [], []
    for p in manifest["profiles"]:
        capture = HERE / "evidence" / p["capture"]
        for name, digest in p["publicPayloadSha256"].items(): assert sha(capture / name) == digest
        r, request, output = [json.loads((capture / n).read_text()) for n in ["receipt.json", "request.json", "observed.json"]]
        assert r["schema"] == request["schema"] == output["schema"] == 1 and r["release"] == p["release"]
        assert sha(capture / "request.json") == r["requestSha256"] and sha(capture / "observed.json") == r["observed.jsonSha256"]
        assert r["clientSha256"] == p["clientSha256"] == targets[p["release"]]["source"]["clientSha256"]
        assert r["originalClientClassesLoaded"] == [r["originalClass"]] and output["originalClass"] == r["originalClass"] and output["originalSigners"] > 0
        assert {k: output[k] for k in p["profile"]} == p["profile"] and output["os"] == "Mac OS X" and output["architecture"] == "aarch64"
        assert output["javaVersion"].startswith("25." if p["release"] == "26.3" else "21.")
        assert len(r["commands"]) == 2
        for name, command in zip(["compile", "execute"], r["commands"], strict=True):
            assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
            for stream in ["stdout", "stderr"]: assert sha(capture / (name + "." + stream)) == command[stream + "Sha256"]
        assert len(request["cases"]) == len(output["cases"]) == 24
        for spec, raw in zip(request["cases"], output["cases"], strict=True):
            assert type(spec["negated"]) is bool
            index = len(rows)
            rows.append(dict(id=index, release=p["release"], operation={"parse": 0, "construct": 1}[spec["operation"]], value=scalars(spec["value"]), negated=spec["negated"]))
            observed.append(observe(spec, raw, index)); raw_basis.append((spec, raw))
    assert len(rows) == 72 and sum(r["reparseAttempted"] for r in observed) == 60
    return dict(schema=1, contract="original-blockstate-term-v1", rows=rows), observed, raw_basis


def lean(packet, work, label, batch=False):
    path = work / (label + ".json"); path.write_text(json.dumps(packet, indent=2) + "\n")
    result = subprocess.run([os.environ.get("LEAN", "lean"), "--run", str(HERE / "BlockTermCase.lean"), *(["--batch"] if batch else []), str(path)], cwd=ROOT,
        env=os.environ | {"LEAN_PATH": os.environ.get("LEAN_PATH", str(ROOT / ".build/formal"))}, text=True, capture_output=True, timeout=30)
    (work / (label + ".lean.stdout")).write_text(result.stdout); (work / (label + ".lean.stderr")).write_text(result.stderr)
    return result


def bend(packet, work, label):
    def boolean(value): return "True{}" if value else "False{}"
    calls = []
    for r in packet["rows"]:
        value = "[" + ",".join(map(str, r["value"])) + "]"
        atom = "M.atom_parse(" + value + ")" if r["operation"] == 0 else "M.atom_construct(" + value + "," + boolean(r["negated"]) + ")"
        calls.append("row(" + str(r["id"]) + "n," + atom + ")")
    renderer = r'''
def jb(b: Bool) -> String:
  Bool.pick(String,b,"true","false")
def nums_tail(xs: List<&2,U32>) -> String:
  match xs:
    case Nil{}: ""
    case head <> tail: "," ++ U32.show(head) ++ nums_tail(tail)
def nums(xs: List<&2,U32>) -> String:
  match xs:
    case Nil{}: "[]"
    case head <> tail: "[" ++ U32.show(head) ++ nums_tail(tail) ++ "]"
def scalar_lists_equal(a: List<&2,U32>,b: List<&2,U32>) -> Bool:
  match a b:
    case Nil{} Nil{}: True{}
    case ah <> at bh <> bt: Bool.and(U32.is_eq(ah,bh),scalar_lists_equal(at,bt))
    case _ _: False{}
def atom_equal(a: M.BlockAtom,b: M.BlockAtom) -> Bool:
  match a b:
    case M.Atom{av,an} M.Atom{bv,bn}: Bool.and(scalar_lists_equal(av,bv),Bool.not(Bool.xor(an,bn)))
def reparsed(+original: M.BlockAtom,result: M.AtomResult) -> String:
  match result:
    case M.Refused{}: ",\"reparseError\":1,\"reparsedValue\":[],\"reparsedNegated\":false,\"equalAfterReparse\":false}"
    case M.Accepted{M.Atom{+value,+negated}}:
      ",\"reparseError\":0,\"reparsedValue\":" ++ nums(value) ++ ",\"reparsedNegated\":" ++ jb(negated) ++ ",\"equalAfterReparse\":" ++ jb(atom_equal(original,M.Atom{value,negated})) ++ "}"
def accepted_row(id: Nat,atom: M.BlockAtom) -> String:
  match atom:
    case M.Atom{+value,+negated}:
      +encoded=M.atom_encode(M.Atom{value,negated})
      "{\"id\":" ++ Nat.show(id) ++ ",\"error\":0,\"value\":" ++ nums(value) ++ ",\"negated\":" ++ jb(negated) ++ ",\"encoded\":" ++ nums(encoded) ++ ",\"reparseAttempted\":true" ++ reparsed(M.Atom{value,negated},M.atom_parse(encoded))
def row(id: Nat,result: M.AtomResult) -> String:
  match result:
    case M.Refused{}:
      "{\"id\":" ++ Nat.show(id) ++ ",\"error\":1,\"value\":[],\"negated\":false,\"encoded\":[],\"reparseAttempted\":false,\"reparseError\":0,\"reparsedValue\":[],\"reparsedNegated\":false,\"equalAfterReparse\":false}"
    case M.Accepted{atom}: accepted_row(id,atom)
'''
    path = work / (label + ".bend")
    path.write_text("import Base\nimport ../../../host/minecraft/BlockTerm.bend as M\n" + renderer + '\ndef main() -> IO(Unit):\n  IO.write("[" ++ ' + (' ++ "," ++ '.join(calls) if calls else '""') + ' ++ "]")\n')
    result = subprocess.run([os.environ.get("BEND", "bend"), str(path)], cwd=ROOT, env=os.environ | {"BEND_NO_TELEMETRY": "1"}, text=True, capture_output=True, timeout=30)
    (work / (label + ".bend.stdout")).write_text(result.stdout); (work / (label + ".bend.stderr")).write_text(result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def require_receipt(receipt, public):
    assert json.loads(public.read_text()) == receipt, "Portable block-term receipt is stale; review and explicitly refresh."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-receipt", action="store_true")
    args = parser.parse_args()
    work = ROOT / ".build/minecraft/block-term-conformance"; work.mkdir(parents=True, exist_ok=True)
    packet, observed, basis = load()
    result = lean(packet, work, "current"); assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == observed
    assert bend(packet, work, "current") == observed
    negatives = []
    for name in ["schema", "contract", "old-client-as-term-record", "operation", "needed-flag", "surrogate", "outside-unicode", "too-long", "duplicate", "too-many"]:
        p = copy.deepcopy(packet)
        if name == "schema": p["schema"] = 2
        elif name == "contract": p["contract"] = "full-condition"
        elif name == "old-client-as-term-record": p["rows"][0]["release"] = "1.21.1"
        elif name == "operation": p["rows"][0]["operation"] = 2
        elif name == "needed-flag": p["rows"][16]["negated"] = None
        elif name == "surrogate": p["rows"][0]["value"] = [55296]
        elif name == "outside-unicode": p["rows"][0]["value"] = [1114112]
        elif name == "too-long": p["rows"][0]["value"] = [129302] * 17
        elif name == "duplicate": p["rows"][1]["id"] = 0
        else: p["rows"] = p["rows"] * 2
        negatives.append((name, p))
    r = lean([p for _, p in negatives], work, "refusals", True)
    assert r.returncode == 0 and json.loads(r.stdout) == [2] * len(negatives)
    unneeded = copy.deepcopy(packet); unneeded["rows"][0]["negated"] = None
    r = lean(unneeded, work, "unneeded-parse-flag"); assert r.returncode == 0 and json.loads(r.stdout) == observed
    assert bend(unneeded, work, "unneeded-parse-flag") == observed
    premises = []
    for label, index, change in [("bang-as-double-negation", 4, dict(value=[110, 111, 114, 116, 104])),
            ("space-as-trimmed", 10, dict(value=[33, 110, 111, 114, 116, 104])),
            ("constructor-as-parser", 22, dict(operation=0)), ("literal-separator-as-split", 6, dict(value=[110, 111, 114, 116, 104]))]:
        p = copy.deepcopy(packet); p["rows"] = [p["rows"][index] | change]
        r = lean(p, work, label); assert r.returncode == 0 and json.loads(r.stdout) != [observed[index]]
        assert bend(p, work, label) == json.loads(r.stdout); premises.append(label)
    raw_controls = []
    for label, index in [("lost-value", 4), ("lost-flag", 3), ("lost-encoding", 3), ("false-record-equality", 22), ("lost-reparse-refusal", 20)]:
        spec, raw = copy.deepcopy(basis[index])
        if label == "lost-value": raw["term"]["value"] = "north"
        elif label == "lost-flag": raw["term"]["negated"] = False
        elif label == "lost-encoding": raw["term"]["encoded"] = "north"
        elif label == "false-record-equality": raw["equalAfterReparse"] = True
        else: raw.update(reparseStatus="returned", reparsed=raw["term"], equalAfterReparse=True)
        try: rejected = observe(spec, raw, index) != observed[index]
        except (AssertionError, KeyError): rejected = True
        assert rejected; raw_controls.append(label)
    receipt = dict(schema=1, scenarioRows=72, explicitReparseAttempts=60, leanLaws=14, bendLaws=11, decoderRefusals=[n for n, _ in negatives],
        acceptedUnneededUnknown="parse constructor flag", rejectedInterpretations=premises, rawObservationControls=raw_controls,
        formalSha256={n: sha(HERE / n) for n in ["BlockTerm.lean", "BlockTermCase.lean", "BlockTerm.bend"]},
        basisSha256={n: sha(HERE / n) for n in ["block-term-captures.json", "block_term_conformance.py"]},
        limits="Literal Term records only;no complete Terms codec,property/state admission,older whole-condition execution,custom provider,game or renderer qualification.")
    public = HERE / "evidence/block-term-conformance.json"
    if args.refresh_receipt: public.write_text(json.dumps(receipt, indent=2) + "\n")
    require_receipt(receipt, public)
    stale = copy.deepcopy(receipt); stale["scenarioRows"] -= 1
    try: require_receipt(stale, public)
    except AssertionError: pass
    else: raise AssertionError("Stale receipt control unexpectedly passed.")
    (work / "conformance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
