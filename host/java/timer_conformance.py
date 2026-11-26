#!/usr/bin/env python3
"""Retained Timer admission/model comparison; no Java, timer, callback, or app run."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

from timer_observations import definitions, observe, packet

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load():
    manifest = json.loads((HERE / "timer-captures.json").read_text())
    assert manifest["schema"] == 1 and manifest["exporterSha256"] == sha(HERE / "timer_observations.py")
    assert manifest["operationAdapter"]["producerSha256"] == sha(HERE / "TimerProbe.java")
    assert manifest["operationAdapter"]["definitions"] == definitions()
    assert [p["java"] for p in manifest["profiles"]] == [17, 21, 25]
    profiles = []
    for p in manifest["profiles"]:
        capture = HERE / "evidence" / p["capture"]
        for name, digest in p["publicPayloadSha256"].items(): assert sha(capture / name) == digest
        receipt = json.loads((capture / "receipt.json").read_text())
        raw = json.loads((capture / "execute.stdout").read_text())
        assert receipt["schema"] == 1 and receipt["profile"]["JAVA_VERSION"] == p["javaVersion"] == raw["java"]
        assert raw["java"].startswith(str(p["java"]) + ".") and raw["os"] == p["os"] and raw["architecture"] == p["architecture"]
        assert receipt["profile"]["OS_NAME"] == "Darwin" and receipt["profile"]["OS_ARCH"] == "aarch64"
        assert receipt["exactCaptureProcessReadback"] == []
        assert receipt["producerSha256"]["TimerProbe.java"] == sha(HERE / "TimerProbe.java")
        assert receipt["producerSha256"]["timer_probe.py"] == sha(HERE / "timer_probe.py")
        assert receipt["producerSha256"]["arena_probe.py"] == sha(HERE / "arena_probe.py")
        for label, command in zip(["compile", "execute"], receipt["commands"], strict=True):
            assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
            for stream in ["stdout", "stderr"]: assert sha(capture / (label + "." + stream)) == command[stream + "Sha256"]
        profiles.append((packet(p["java"], definitions()), observe(raw, definitions()), raw))
    return profiles


def lean(value, work, label, batch=False):
    path = work / (label + ".json"); path.write_text(json.dumps(value, indent=2) + "\n")
    result = subprocess.run([os.environ.get("LEAN", "lean"), "--run", str(HERE / "TimerPolicyCase.lean"), *(["--batch"] if batch else []), str(path)],
        cwd=ROOT, env=os.environ | {"LEAN_PATH": os.environ.get("LEAN_PATH", str(ROOT / ".build/formal"))}, text=True, capture_output=True, timeout=30)
    (work / (label + ".lean.stdout")).write_text(result.stdout); (work / (label + ".lean.stderr")).write_text(result.stderr)
    return result


def bend(p, work, label):
    calls = []
    for row in p["rows"]:
        values = [str(row[k] or 0) + "n" for k in ["id", "operation", "timer", "task"]]
        values.append("False{}" if row["validArguments"] is False else "True{}")
        calls.append("Input{" + ",".join(values) + "}")
    renderer = r'''
import Base
import TimerPolicy.bend as M
type Input is Data:
  Input{id: Nat,op: Nat,timer: Nat,task: Nat,valid: Bool}
def optional(values: List<&2,Bool>) -> String:
  match values:
    case Nil{}: "null"
    case head <> tail: Bool.pick(String,head,"true","false")
def row(id: Nat,reply: M.TimerReply) -> String:
  match reply:
    case M.Reply{state,error,value}:
      "{\"id\":" ++ Nat.show(id) ++ ",\"error\":" ++ Nat.show(error) ++ ",\"value\":" ++ optional(value) ++ "}"
def trace(inputs: List<&2,Input>,state: M.TimerState) -> String:
  match inputs:
    case Nil{}: ""
    case input <> +tail:
      match input:
        case Input{id,op,timer,task,valid}:
          +reply=M.timer_step(state,op,timer,task,valid)
          row(id,reply) ++ Bool.pick(String,List.is_empty(&2,Input,tail),"","," ++ trace(tail,M.state(reply)))
'''
    path = work / (label + ".bend")
    path.write_text(renderer + '\ndef main() -> IO(Unit):\n  IO.write("[" ++ trace([' + ",".join(calls) + '],M.timer_initial()) ++ "]")\n')
    (work / "TimerPolicy.bend").write_bytes((HERE / "TimerPolicy.bend").read_bytes())
    result = subprocess.run([os.environ.get("BEND", "bend"), str(path)], cwd=ROOT,
        env=os.environ | {"BEND_NO_TELEMETRY": "1"}, text=True, capture_output=True, timeout=30)
    (work / (label + ".bend.stdout")).write_text(result.stdout); (work / (label + ".bend.stderr")).write_text(result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def require_receipt(result, path):
    assert json.loads(path.read_text()) == result, "Timer comparison receipt stale; review and explicitly refresh."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-receipt", action="store_true")
    args = parser.parse_args()
    work = ROOT / ".build/java-timer-conformance"; work.mkdir(parents=True, exist_ok=True)
    profiles = load()
    for p, observed, raw in profiles:
        r = lean(p, work, "java" + str(p["java"])); assert r.returncode == 0, r.stdout + r.stderr
        assert json.loads(r.stdout) == observed == bend(p, work, "java" + str(p["java"]))
    current, observed, raw = profiles[0]
    negatives = []
    for label in ["schema", "contract", "java18", "operation", "needed-timer", "needed-task", "needed-validity", "timer-range", "task-range", "duplicate", "too-many"]:
        p = copy.deepcopy(current)
        if label == "schema": p["schema"] = 2
        elif label == "contract": p["contract"] = "callback-retired"
        elif label == "java18": p["java"] = 18
        elif label == "operation": p["rows"][0]["operation"] = 3
        elif label == "needed-timer": p["rows"][1]["timer"] = None
        elif label == "needed-task": p["rows"][0]["task"] = None
        elif label == "needed-validity": p["rows"][1]["validArguments"] = None
        elif label == "timer-range": p["rows"][1]["timer"] = 2
        elif label == "task-range": p["rows"][1]["task"] = 6
        elif label == "duplicate": p["rows"][1]["id"] = 0
        else: p["rows"] = p["rows"] * 5
        negatives.append((label, p))
    r = lean([p for _, p in negatives], work, "refusals", True)
    assert r.returncode == 0 and json.loads(r.stdout) == [2] * len(negatives)
    premises = []
    for label, i, change in [("cancel-timer-instead", 0, dict(operation=2, timer=0, task=None)),
                            ("bad-delay-as-valid", 7, dict(validArguments=True)),
                            ("fresh-task-instead", 6, dict(task=4)), ("open-timer-instead", 13, dict(timer=1))]:
        p = copy.deepcopy(current); p["rows"][i].update(change)
        r = lean(p, work, label); assert r.returncode == 0
        assert json.loads(r.stdout) != observed and bend(p, work, label) != observed
        premises.append(label)
    mutations = []
    for label in ["fresh-cancel-as-true", "double-schedule-accepted", "scheduled-cancel-false", "bad-delay-accepted", "callback-executed", "worker-still-live", "boolean-error-code", "numeric-retirement"]:
        changed = copy.deepcopy(raw)
        if label == "fresh-cancel-as-true": changed["events"][0]["value"] = True
        elif label == "double-schedule-accepted": changed["events"][3]["error"] = 0
        elif label == "scheduled-cancel-false": changed["events"][4]["value"] = False
        elif label == "bad-delay-accepted": changed["events"][7]["error"] = 0
        elif label == "callback-executed": changed["events"][8]["callbacks"] = 1
        elif label == "worker-still-live": changed["events"][-1]["value"] = False
        elif label == "boolean-error-code": changed["events"][3]["error"] = True
        else: changed["events"][-1]["value"] = 1
        try: refused = observe(changed, definitions()) != observed
        except (AssertionError, KeyError): refused = True
        assert refused; mutations.append(label)
    result = dict(schema=1, profiles=3, nativeAdmissionOperations=45, semanticResultScalars=54,
        independentRetirementWitnesses=3, zeroCallbackSamples=48, leanLaws=14, bendLaws=9,
        sourceModelOnlyLaws=["invalid_arguments_precede_closed_timer", "canceled_timer_does_not_make_task_cancel_false", "argument_guard_first_source_example"],
        decoderRefusals=[n for n, _ in negatives], changedPremises=premises, changedRawObservations=mutations,
        formalSha256={n: sha(HERE / n) for n in ["TimerPolicy.lean", "TimerPolicy.bend", "TimerPolicyCase.lean"]},
        basisSha256={n: sha(HERE / n) for n in ["timer-captures.json", "timer_observations.py", "timer_conformance.py"]},
        limits="Far-future owned tasks on JDK17/21/25 macOSarm64;OS build not recorded. Retirement/zero callbacks observed separately,not inferred from admission model. No callbacks run,clock/latency/concurrent retirement,Minecraft/application/GUI or other-host qualification.")
    public = HERE / "evidence/timer-conformance.json"
    if args.refresh_receipt: public.write_text(json.dumps(result, indent=2) + "\n")
    require_receipt(result, public)
    stale = copy.deepcopy(result); stale["nativeAdmissionOperations"] = 44
    try: require_receipt(stale, public)
    except AssertionError: pass
    else: raise AssertionError("Stale receipt accepted.")
    (work / "conformance.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
