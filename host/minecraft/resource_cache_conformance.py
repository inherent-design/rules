#!/usr/bin/env python3
"""Replay selected original cache observations through pure models; no Java invocation."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAPTURE = "resource-cache-20261125T195402530738Z"
ARTIFACT = "4ae402eaa858eef4141858554a3f9f0867f6e2ddc72e68313668187a3058e5d5"
KINDS = ["ENCHANTMENTS", "STEW", "PAINTING", "AXOLOTL", "POTION"]
TOKENS = {"null": 0, "a": 1, "b": 2, "c": 3}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frames(request):
    values, events = set(), set()
    for case in request["cases"]:
        for action in case["actions"]:
            if action["op"] == "project":
                if action["value"] is not None:
                    assert type(action["value"]) is str
                    values.add(action["value"])
                events.add("project:" + action["marker"])
            elif action["op"] == "onClear":
                events.add("clear:" + action["marker"])
            else:
                assert action == {"op": "clear"}
    return {v: i + 1 for i, v in enumerate(sorted(values))}, {v: i + 1 for i, v in enumerate(sorted(events))}


def project(request, values, events):
    rows = []
    for i, case in enumerate(request["cases"]):
        assert type(case["capacity"]) is int
        actions = []
        for action in case["actions"]:
            row = dict(op=0, identity=0, kind=0, event=0, projection=0, value=0, failures=0)
            if action["op"] == "project":
                assert type(action["throw"]) is bool
                row.update(identity=TOKENS[action["token"]], kind=KINDS.index(action["kind"]), event=events["project:" + action["marker"]],
                    projection=2 if action["throw"] else 0 if action["value"] is None else 1,
                    value=0 if action["throw"] or action["value"] is None else values[action["value"]])
            elif action["op"] == "onClear":
                assert type(action["failures"]) is int
                row.update(op=1, event=events["clear:" + action["marker"]], failures=action["failures"])
            else:
                assert action == {"op": "clear"}
                row["op"] = 2
            actions.append(row)
        rows.append(dict(id=i, capacity=case["capacity"], actions=actions))
    return dict(schema=1, contract="isolated-resource-cache-v1", artifact=ARTIFACT,
        identityProfile="case-local-equal-distinct-strings-v1", callbackProfile="authored-nonreentrant-v1", rows=rows)


def observe(request, raw, values, events):
    assert raw["schema"] == 1 and len(raw["cases"]) == len(request["cases"])
    rows = []
    for i, (spec, case) in enumerate(zip(request["cases"], raw["cases"], strict=True)):
        assert case["id"] == spec["id"]
        if case["construction"] == "threw":
            assert set(case) == {"id", "construction", "errorClass", "message"}
            assert case["errorClass"] == "IllegalArgumentException" and case["message"] == "Component cache capacity must be positive"
            rows.append(dict(id=i, constructorError=1, steps=[]))
            continue
        assert case["construction"] == "returned"
        assert set(case) == {"id", "construction", "aEqualsB", "aIdenticalB", "steps"}
        assert case["aEqualsB"] is True and case["aIdenticalB"] is False
        assert len(case["steps"]) == len(spec["actions"])
        steps = []
        for action, step in zip(spec["actions"], case["steps"], strict=True):
            assert step["op"] == action["op"] and type(step["size"]) is int and step["size"] >= 0
            assert type(step["events"]) is list and all(type(e) is str and e in events for e in step["events"])
            value, error = None, 0
            keys = {"op", "status", "size", "events"}
            if step["status"] == "threw":
                keys |= {"errorClass", "message"}
                assert step["errorClass"] == "IllegalStateException"
                if action["op"] == "project":
                    assert step["message"] == "authored projection:" + action["marker"]
                    error = 1
                else:
                    assert action["op"] == "clear" and step["message"].startswith("authored clear:")
                    assert "clear:" + step["message"].removeprefix("authored clear:") in events
                    error = 2
            else:
                assert step["status"] == "returned"
                if action["op"] == "project":
                    keys.add("value")
                    returned = step["value"]
                    assert type(returned) is str
                    if returned == "absent":
                        value = 0
                    else:
                        assert returned.startswith("string:") and returned[7:] in values
                        value = values[returned[7:]]
            assert set(step) == keys
            steps.append(dict(error=error, value=value, size=step["size"], events=[events[e] for e in step["events"]]))
        rows.append(dict(id=i, constructorError=0, steps=steps))
    return rows


def lean(packet, work, label, batch=False):
    path = work / (label + ".json")
    path.write_text(json.dumps(packet, indent=2) + "\n")
    return subprocess.run([os.environ.get("LEAN", "lean"), "--run", str(HERE / "ResourceCacheCase.lean"),
        *(["--batch"] if batch else []), str(path)], cwd=ROOT,
        env=os.environ | {"LEAN_PATH": os.environ.get("LEAN_PATH", str(ROOT / ".build/formal"))},
        text=True, capture_output=True, timeout=30)


BEND_RENDERER = r'''
type Action is Data:
  Project{identity: Nat,kind: Nat,event: Nat,projection: M.RCProjection}
  OnClear{event: Nat,failures: Nat}
  Clear{}
def apply(state: M.RCState,action: Action) -> M.RCStep:
  match action:
    case Project{identity,kind,event,projection}: M.rc_project(state,identity,kind,event,projection)
    case OnClear{event,failures}: M.rc_on_clear(state,M.Callback{event,failures})
    case Clear{}: M.rc_clear(state)
def step_state(step: M.RCStep) -> M.RCState:
  match step:
    case M.Step{state,error,value}: state
def state_events(state: M.RCState) -> List<&2,Nat>:
  match state:
    case M.State{capacity,entries,callbacks,events}: events
def n_tail(xs: List<&2,Nat>) -> String:
  match xs:
    case Nil{}: ""
    case Con{head,tail}: "," ++ Nat.show(head) ++ n_tail(tail)
def n_show(xs: List<&2,Nat>) -> String:
  match xs:
    case Nil{}: "[]"
    case Con{head,tail}: "[" ++ Nat.show(head) ++ n_tail(tail) ++ "]"
def value_show(value: M.RCValue) -> String:
  match value:
    case M.Absent{}: "0"
    case M.CachedText{identity}: Nat.show(identity)
def found_show(value: M.RCFound) -> String:
  match value:
    case M.Missing{}: "null"
    case M.Found{value}: value_show(value)
def step_show(step: M.RCStep) -> String:
  match step:
    case M.Step{+state,error,value}:
      "{\"error\":" ++ Nat.show(error) ++ ",\"value\":" ++ found_show(value) ++ ",\"size\":" ++ Nat.show(List.length(&2,M.RCEntry,M.rc_entries(state))) ++ ",\"events\":" ++ n_show(state_events(state)) ++ "}"
def trace(actions: List<&2,Action>,state: M.RCState) -> List<&2,String>:
  match actions:
    case Nil{}: Nil{}
    case Con{action,tail}:
      +step = apply(state,action)
      Con{step_show(step),trace(tail,step_state(step))}
def s_tail(xs: List<&2,String>) -> String:
  match xs:
    case Nil{}: ""
    case Con{head,tail}: "," ++ head ++ s_tail(tail)
def s_show(xs: List<&2,String>) -> String:
  match xs:
    case Nil{}: "[]"
    case Con{head,tail}: "[" ++ head ++ s_tail(tail) ++ "]"
def row_show(id: Nat,actions: List<&2,Action>,start: M.RCStart) -> String:
  match start:
    case M.CreateRefused{}: "{\"id\":" ++ Nat.show(id) ++ ",\"constructorError\":1,\"steps\":[]}"
    case M.Created{state}: "{\"id\":" ++ Nat.show(id) ++ ",\"constructorError\":0,\"steps\":" ++ s_show(trace(actions,state)) ++ "}"
'''


def bend(rows, work, label):
    calls = []
    for row in rows:
        actions = []
        for action in row["actions"] or []:
            if action["op"] == 0:
                projection = "M.Failed{}" if action["projection"] == 2 else "M.Returned{" + (
                    "M.Absent{}" if action["projection"] == 0 else "M.CachedText{" + str(action["value"]) + "n}") + "}"
                actions.append("Project{" + ",".join(str(action[k]) + "n" for k in ["identity", "kind", "event"]) + "," + projection + "}")
            elif action["op"] == 1:
                actions.append("OnClear{" + str(action["event"]) + "n," + str(action["failures"]) + "n}")
            else:
                actions.append("Clear{}")
        # The selected nonpositive Int capacities have the same refusal outcome.
        capacity = max(row["capacity"], 0)
        calls.append("row_show(" + str(row["id"]) + "n,[" + ",".join(actions) + "],M.rc_create(" + str(capacity) + "n))")
    path = work / (label + ".bend")
    path.write_text("import Base\nimport ../../../host/minecraft/ResourceCache.bend as M\n" + BEND_RENDERER +
        '\ndef main() -> IO(Unit):\n  IO.write("[" ++ ' + ' ++ "," ++ '.join(calls) + ' ++ "]")\n')
    result = subprocess.run([os.environ.get("BEND", "bend"), str(path)], cwd=ROOT,
        env=os.environ | {"BEND_NO_TELEMETRY": "1"}, text=True, capture_output=True, timeout=30)
    (work / (label + ".bend.stdout")).write_text(result.stdout)
    (work / (label + ".bend.stderr")).write_text(result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", action="store_true")
    args = parser.parse_args()
    cap = (ROOT / ".build/minecraft" if args.private else HERE / "evidence") / CAPTURE
    receipt = json.loads((cap / "receipt.json").read_text())
    assert receipt["artifactSha256"] == ARTIFACT
    selected = next(p for p in json.loads((HERE / "provider-sources.json").read_text())["providers"] if p["provider"] == receipt["target"])
    assert receipt["selectedClassSha256"] == {n: h for n, h in selected["originalClassSha256"].items()
        if n.startswith("design/inherent/skyweavecompat/client/model/ResourceValueCache")}
    for name, digest in receipt["sourcesSha256"].items():
        assert sha(cap / name) == digest
    for name, key in [("request.json", "requestSha256"), ("observed.json", "observed.jsonSha256")]:
        assert sha(cap / name) == receipt[key]
    for stem, command in zip(["compile", "execute"], receipt["commands"], strict=True):
        assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
        for channel in ["stdout", "stderr"]:
            assert sha(cap / (stem + "." + channel)) == command[channel + "Sha256"]
    request = json.loads((cap / "request.json").read_text())
    raw = json.loads((cap / "observed.json").read_text())
    assert request["schema"] == 1
    values, events = frames(request)
    packet = project(request, values, events)
    wanted = observe(request, raw, values, events)
    work = ROOT / ".build/minecraft/resource-cache-replay"
    work.mkdir(parents=True, exist_ok=True)
    (work / "identity-frames.json").write_text(json.dumps(dict(caseLocalIdentities=TOKENS, kinds=KINDS, values=values, events=events), indent=2) + "\n")
    result = lean(packet, work, "plan")
    (work / "lean.stdout").write_text(result.stdout)
    (work / "lean.stderr").write_text(result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == wanted
    assert bend(packet["rows"], work, "plan") == wanted
    valid = copy.deepcopy(packet)
    valid["rows"] = [copy.deepcopy(packet["rows"][3])]
    invalid = [dict(valid, schema=2), dict(valid, artifact="unselected"), dict(valid, callbackProfile="arbitrary-reentrant"),
        dict(valid, identityProfile="equal-values-are-identical"), dict(valid, rows=valid["rows"] * 2)]
    for label in ["unknown-actions", "capacity", "trace", "operation", "identity", "kind", "unknown-event", "unknown-projection", "clear-with-project", "failed-result", "typed-identity"]:
        bad = copy.deepcopy(valid)
        row, action = bad["rows"][0], bad["rows"][0]["actions"][0]
        if label == "unknown-actions": row["actions"] = None
        elif label == "capacity": row["capacity"] = 1025
        elif label == "trace": row["actions"] *= 33
        elif label == "operation": action["op"] = 3
        elif label == "identity": action["identity"] = 4
        elif label == "kind": action["kind"] = 5
        elif label == "unknown-event": action["event"] = None
        elif label == "unknown-projection": action["projection"] = None
        elif label == "clear-with-project": action["op"] = 2
        elif label == "failed-result": action["projection"] = 2
        else: action["identity"] = True
        invalid.append(bad)
    result = lean(invalid, work, "decoder-refusals", batch=True)
    assert result.returncode == 0 and json.loads(result.stdout) == [2] * len(invalid), result.stdout + result.stderr
    assert lean(invalid[0], work, "direct-refusal").returncode == 2
    unknown = copy.deepcopy(packet)
    unknown["rows"] = [dict(row, actions=None) for row in packet["rows"] if row["capacity"] < 1]
    result = lean(unknown, work, "unused-unknown")
    assert result.returncode == 0 and json.loads(result.stdout) == wanted[:2]
    assert bend(unknown["rows"], work, "unused-unknown") == wanted[:2]

    by_name = {s["id"]: i for i, s in enumerate(request["cases"])}
    premises = []
    for name, change in [("equal-value-distinct-identities", "identity"), ("fifo-hit-not-promoted", "capacity"),
            ("null-projection-memoized", "negative-result"), ("clear-callback-failure-partial", "callback-failure")]:
        index = by_name[name]
        row = copy.deepcopy(packet["rows"][index])
        if change == "identity": row["actions"][1]["identity"] = 1
        elif change == "capacity": row["capacity"] = 1
        elif change == "negative-result": row["actions"][0].update(projection=1, value=values["v1"])
        else: row["actions"][0]["failures"] = 0
        changed = dict(packet, rows=[row])
        result = lean(changed, work, "premise-" + change)
        assert result.returncode == 0, result.stdout + result.stderr
        predicted = json.loads(result.stdout)
        assert predicted != [wanted[index]] and bend([row], work, "premise-" + change) == predicted
        premises.append(dict(case=name, change=change))

    mutations = []
    for name, change in [("equal-value-distinct-identities", "identity-fact"), ("same-identity-hit", "cached-value"),
            ("null-no-projection", "null-size"), ("null-projection-memoized", "negative-hit"),
            ("fifo-hit-not-promoted", "eviction-callback"), ("projection-throw-partial-entry", "failure-size"),
            ("clear-callback-failure-partial", "clear-size"), ("clear-callback-failure-partial", "error-class"),
            ("clear-keeps-registrations", "callback-order"), ("same-object-different-kinds", "kind-value")]:
        altered = copy.deepcopy(raw)
        case = altered["cases"][by_name[name]]
        if change == "identity-fact": case["aIdenticalB"] = True
        elif change == "cached-value": case["steps"][-1]["value"] = "string:v2"
        elif change == "null-size": case["steps"][0]["size"] = 1
        elif change == "negative-hit": case["steps"][-1]["value"] = "string:v2"
        elif change == "eviction-callback": case["steps"][-1]["events"].pop()
        elif change == "failure-size": case["steps"][0]["size"] = 0
        elif change == "clear-size": case["steps"][3]["size"] = 1
        elif change == "error-class": case["steps"][3]["errorClass"] = "UnknownFailure"
        elif change == "callback-order":
            calls = case["steps"][-1]["events"]
            calls[-2], calls[-1] = calls[-1], calls[-2]
        else: case["steps"][1]["value"] = "string:v1"
        try:
            changed = observe(request, altered, values, events)
        except (AssertionError, KeyError):
            rejection = "observation-shape/profile"
        else:
            assert changed != wanted, "Changed native result admitted: " + change
            rejection = "model-outcome-difference"
        mutations.append(dict(case=name, change=change, rejection=rejection))

    report = dict(schema=1, status="passed-retained-original-host-free-cache", scenarios=len(wanted),
        actions=sum(len(r["steps"]) for r in wanted), privateCapture=args.private,
        leanLaws=17, bendLaws=10, decoderRefusals=len(invalid), directCliRefusals=1, unusedUnknownCases=len(unknown["rows"]),
        changedPremiseControls=premises, changedObservationControls=mutations,
        basisSha256={str(p.relative_to(ROOT)): sha(p) for p in [cap / "receipt.json", cap / "request.json", cap / "observed.json",
            *[HERE / n for n in ["ResourceCache.lean", "ResourceCacheCase.lean", "ResourceCache.bend", "resource_cache_conformance.py"]]]},
        limits=["Original host-free cache with non-reentrant authored callbacks, not native components/game registries/rendering.",
            "Only API results, size and callback traces are compared; full modeled entries are not raw native field observations.",
            "Role-specific identity/value/event frames and nonpositive-capacity refusal projection are named premises; not JSON or translation proof.",
            "No arbitrary callback mutation/reentrancy, concurrent access, lifetime reclamation or physical-memory proof."])
    (work / "conformance.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ["basisSha256", "limits", "changedObservationControls"]}))


if __name__ == "__main__":
    main()
