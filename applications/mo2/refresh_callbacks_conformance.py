#!/usr/bin/env python3
"""Pure model replay of retained callback cuts; never compile or run C++ here."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUN = ROOT / "applications/evidence/mo2-refresh-callbacks-20261126T101529108336Z"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(public_only):
    receipt = json.loads((RUN / "receipt.json").read_text())
    commands = json.loads((RUN / "commands.json").read_text())
    assert receipt["commands"] == len(commands) == 2
    assert receipt["allOwnedGroupsAbsent"]
    for row in commands:
        assert row["exitCode"] == 0 and not row["timedOut"] and row["ownedGroupAbsent"]
        for stream in row["streams"].values():
            assert digest(RUN / stream["file"]) == stream["sha256"]
    assert digest(RUN / "producer.py") == receipt["producerSha256"]
    assert digest(RUN / "driver.cpp") == receipt["driverSha256"]
    assert digest(HERE / "refresh_callbacks_probe.py") == receipt["producerSha256"]
    assert digest(HERE / "refresh_callbacks_driver.cpp") == receipt["driverSha256"]
    assert commands[0]["argv"][0] == receipt["compiler"]["path"]
    assert Path(commands[0]["argv"][0]).name == "clang++"
    observations = [json.loads(line) for line in (RUN / "observe.stdout").read_text().splitlines()]
    assert receipt["records"] == len(observations) == 10
    cases = {"queued", "immediate", "reentrant-forced", "reentrant-immediate", "groups"}
    assert {(r["case"], r["policy"]) for r in observations} == {
        (name, policy) for name in cases for policy in ["current", "detached-batch"]}
    for row in observations:
        assert set(row) == {"case", "policy", "before", "first", "second"}
        for phase in ["before", "first", "second"]:
            value = row[phase]
            assert set(value) == {"trace", "connected", "pending"}
            assert value["connected"] == sorted(set(value["connected"]))
            assert value["pending"] == len(value["connected"])
    if not public_only:
        work = Path(receipt["work"])
        assert work.parent == Path("/private/tmp") and work.name.startswith("rules-mo2-refresh-callbacks-")
        assert work.resolve() == work
        assert digest(work / "probe.cpp") == receipt["generatedSha256"]
        assert digest(work / "probe") == receipt["binarySha256"]
        compiler = Path(receipt["compiler"]["path"])
        assert compiler.is_relative_to("/Applications/Xcode.app/Contents/Developer")
        assert str(compiler.resolve()) == receipt["compiler"]["resolvedPath"]
        assert digest(compiler) == receipt["compiler"]["sha256"]
        boost = Path(receipt["boostRoot"])
        assert boost.is_relative_to("/opt/homebrew/Cellar/boost")
        assert digest(boost / "version.hpp") == receipt["boostVersionHeaderSha256"]
        allowed = [work, Path("/Applications/Xcode.app/Contents/Developer"), boost]
        for dependency in receipt["dependencies"]:
            path = Path(dependency["path"]).resolve()
            assert any(path.is_relative_to(parent) for parent in allowed), path
            assert digest(path) == dependency["sha256"], path
        import refresh_callbacks_probe as producer
        source = ROOT / "applications/tools/source-cache/launchers/mo2__src__organizercore.cpp"
        header = ROOT / "applications/tools/source-cache/mo2-architecture/src__organizercore.h"
        assert digest(source) == receipt["source"]["sha256"]
        assert digest(header) == receipt["header"]["sha256"]
        registration = "boost::signals2::connection\n" + producer.body(source.read_text(), "OrganizerCore::onNextRefresh(")
        assert hashlib.sha256(registration.encode()).hexdigest() == receipt["registrationSha256"]
        generated = (RUN / "driver.cpp").read_text().replace("/*SOURCE_REGISTRATION*/", registration).replace(
            "/*SOURCE_CURRENT_DRAIN*/", "\n    ".join(receipt["drainStatements"]))
        assert hashlib.sha256(generated.encode()).hexdigest() == receipt["generatedSha256"]
    return receipt, observations


def inputs(name, detached):
    def request(token, group, force=True, child=None):
        return dict(token=token, group=group, force=force, child=child)
    requests = [request(1, 0, name != "immediate")]
    if name in ["reentrant-forced", "reentrant-immediate"]:
        requests[0]["child"] = dict(token=2, group=2, force=name == "reentrant-forced")
    if name == "groups":
        requests = [request(3, 2), request(1, 0), request(2, 1)]
    return dict(active=name != "immediate", detached=detached, requests=requests)


def compare(observation, value):
    assert {phase: observation[phase] for phase in ["before", "first", "second"]} == value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-only", action="store_true")
    args = parser.parse_args()
    receipt, observations = inspect(args.public_only)
    scenarios = [inputs(row["case"], row["policy"] == "detached-batch") for row in observations]
    data = dict(schema=1, profile="single-thread-leaf-callback-drain", singleThreaded=True,
                callbacksDoNotThrowOrCancel=True, scenarios=scenarios)
    out = ROOT / ".build/mo2-refresh-callbacks-formal"
    out.mkdir(parents=True, exist_ok=True)
    lean, bend = os.environ.get("LEAN", "lean"), os.environ.get("BEND", "bend")
    env = dict(os.environ, LEAN_PATH=str(out), BEND_NO_TELEMETRY="1")
    module = out / "applications/mo2/RefreshCallbacks.olean"
    module.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run([lean, "-DwarningAsError=true", "-o", str(module), "applications/mo2/RefreshCallbacks.lean"],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
    assert p.returncode == 0, p.stdout + p.stderr
    input_path = out / "input.json"

    def replay(value):
        input_path.write_text(json.dumps(value) + "\n")
        return subprocess.run([lean, "--run", "applications/mo2/RefreshCallbacksCase.lean", str(input_path)],
                              cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)

    p = replay(data)
    assert p.returncode == 0, p.stdout + p.stderr
    actual = json.loads(p.stdout)
    assert len(actual) == len(observations)
    for row, value in zip(observations, actual):
        compare(row, value)
    b = lambda value: "True{}" if value else "False{}"

    def request(row):
        child = row["child"]
        encoded = "R.NoChild{}" if child is None else "R.Child{" + str(child["token"]) + "n," + str(child["group"]) + "n," + b(child["force"]) + "}"
        return "R.Request{R.Callback{" + str(row["token"]) + "n," + str(row["group"]) + "n," + encoded + "}," + b(row["force"]) + "}"

    calls = []
    for scenario in scenarios:
        values = "Nil{}"
        for row in reversed(scenario["requests"]):
            values = "Con{" + request(row) + "," + values + "}"
        calls.append("R.render(" + b(scenario["detached"]) + "," + b(scenario["active"]) + "," + values + ') ++ "\\n"')
    driver = out / "driver.bend"
    driver.write_text('import Base\nimport ../../applications/mo2/RefreshCallbacks.bend as R\n\ndef main() -> IO(Unit):\n  IO.write(' + " ++ ".join(calls) + ')\n')
    p = subprocess.run([bend, str(driver)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
    assert p.returncode == 0, p.stdout + p.stderr
    bend_values = [json.loads(line) for line in p.stdout.splitlines()]
    assert bend_values == actual
    refusals = []
    for name, edit, message in [
        ("schema", lambda d: d.update(schema=2), "Unsupported callback research scope"),
        ("profile", lambda d: d.update(profile="all-refreshes"), "Unsupported callback research scope"),
        ("threading", lambda d: d.update(singleThreaded=False), "Unsupported callback research scope"),
        ("exception-cancel", lambda d: d.update(callbacksDoNotThrowOrCancel=False), "Unsupported callback research scope"),
        ("group", lambda d: d["scenarios"][0]["requests"][0].update(group=3), "Unsupported callback value"),
        ("zero-token", lambda d: d["scenarios"][0]["requests"][0].update(token=0), "Unsupported callback value"),
        ("child-group", lambda d: d["scenarios"][4]["requests"][0]["child"].update(group=3), "Unsupported leaf callback value"),
        ("duplicate-token", lambda d: d["scenarios"][4]["requests"][0]["child"].update(token=1), "Registration tokens must be unique"),
        ("request-count", lambda d: d["scenarios"][0].update(requests=d["scenarios"][0]["requests"] * 9), "Too many selected callback requests"),
        ("scenario-count", lambda d: d.update(scenarios=d["scenarios"] * 2), "Unsupported callback research scope"),
    ]:
        bad = copy.deepcopy(data)
        edit(bad)
        p = replay(bad)
        assert p.returncode == 2 and not p.stdout and message in p.stderr, (name, p.stdout, p.stderr)
        refusals.append(name)
    mutations = []
    for phase, field in [("first", "trace"), ("first", "connected"), ("first", "pending"), ("second", "trace")]:
        index = next(i for i, row in enumerate(observations) if row["case"] == "reentrant-forced" and row["policy"] == "current")
        bad = copy.deepcopy(observations[index])
        if field == "pending":
            bad[phase][field] += 1
        else:
            bad[phase][field].append(2)
        try:
            compare(bad, actual[index])
        except AssertionError:
            mutations.append(phase + "-" + field)
        else:
            raise RuntimeError("Changed observation escaped")
    input_path.write_text(json.dumps(data) + "\n")
    excluded = ["current-source-cuts", "generated-binary-and-source", "compiler-and-header-dependencies"] if args.public_only else []
    result = dict(schema=1, profile=data["profile"], requests=scenarios,
                  comparison=[dict(case=row["case"], policy=row["policy"], snapshots=value) for row, value in zip(observations, actual)],
                  modelIdentities=[{"path": "applications/mo2/" + name, "sha256": digest(HERE / name)} for name in ["RefreshCallbacks.lean", "RefreshCallbacksCase.lean", "RefreshCallbacks.bend"]],
                  decoderRefusals=refusals, changedObservationControls=mutations, excludedPrivateChecks=excluded,
                  limits=["Five scenarios, two research implementations, three snapshots; not Windows MO2, Qt refresh, VFS or profile persistence.",
                          "No exceptions, cancellation, deeper registration chains, parallel delivery or full application reachability qualified."])
    (RUN / ("comparison-public.json" if args.public_only else "comparison.json")).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(fragmentCases=10, snapshots=30, decoderRefusals=len(refusals), changedControls=len(mutations), headerDependencies=len(receipt["dependencies"]))))


if __name__ == "__main__":
    main()
