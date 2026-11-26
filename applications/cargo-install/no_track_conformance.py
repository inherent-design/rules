#!/usr/bin/env python3
"""Read retained Cargo evidence and replay the scoped completion models only."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUN = ROOT / "applications/evidence/cargo-install-no-track-20261126T092200557280Z"
A, B = "rules-no-track-a", "rules-no-track-b"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(public_only=False):
    receipt = json.loads((RUN / "receipt.json").read_text())
    commands = json.loads((RUN / "commands.json").read_text())
    assert len(commands) == receipt["commands"] == 6
    assert receipt["allOwnedGroupsAbsent"]
    assert digest(RUN / "producer.py") == receipt["producerSha256"]
    source = json.loads((RUN / "initial-source.json").read_text())
    by_case = {row["case"]: row for row in commands}
    for row in commands:
        assert not row["outcome"]["timedOut"] and row["outcome"]["ownedGroupAbsent"]
        for stream in row["streams"].values():
            assert digest(RUN / stream["file"]) == stream["sha256"]
        for side in ["sourceBefore", "sourceAfter"]:
            assert set(row[side]) <= set(source) | {"src", "Cargo.lock"}
            for name, content in source.items():
                assert row[side][name]["sha256"] == hashlib.sha256(content.encode()).hexdigest()
        for name in ["bin/" + A + "/owned-marker", "bin/unrelated-marker"]:
            assert row["before"][name] == row["after"][name]
    for mode, labels in [("untracked", ["version", "untracked-no-force", "untracked-force", "untracked-b-runtime"]),
                         ("tracked", ["tracked-force-control", "tracked-list"])]:
        for first, second in zip(labels, labels[1:]):
            assert by_case[first]["after"] == by_case[second]["before"]
    for first, second in zip(commands, commands[1:]):
        assert first["sourceAfter"] == second["sourceBefore"]
    for name in ["version", "untracked-no-force", "untracked-b-runtime", "tracked-list"]:
        assert by_case[name]["before"] == by_case[name]["after"]
    no_force = by_case["untracked-no-force"]
    assert no_force["outcome"]["exitCode"] == 101
    assert "Add --force to overwrite" in (RUN / no_force["streams"]["stderr"]["file"]).read_text()
    untracked, tracked = by_case["untracked-force"], by_case["tracked-force-control"]
    for row in [untracked, tracked]:
        assert row["before"]["bin/" + A]["kind"] == row["after"]["bin/" + A]["kind"] == "directory"
        assert "bin/" + B not in row["before"]
    assert all(name not in untracked["after"] for name in [".crates.toml", ".crates2.json"])
    assert "Is a directory (os error 21)" in (RUN / tracked["streams"]["stderr"]["file"]).read_text()
    catalog = json.loads((RUN / "tracked-crates2.json").read_text())
    assert len(catalog["installs"]) == 1
    assert next(iter(catalog["installs"].values()))["bins"] == [B]
    assert digest(RUN / "tracked-crates2.json") == tracked["after"][".crates2.json"]["sha256"]
    assert digest(RUN / "tracked-crates.toml") == tracked["after"][".crates.toml"]["sha256"]
    assert B in (RUN / by_case["tracked-list"]["streams"]["stdout"]["file"]).read_text()
    assert (RUN / by_case["untracked-b-runtime"]["streams"]["stdout"]["file"]).read_bytes() == b"owned-b\n"
    assert (RUN / by_case["version"]["streams"]["stdout"]["file"]).read_text().startswith("cargo 1.92.0 ")
    if not public_only:
        for tool in receipt["tools"].values():
            assert digest(Path(tool["path"])) == tool["sha256"]
        for mode, label in [("untracked", "untracked-b-runtime"), ("tracked", "tracked-list")]:
            root = Path(receipt["roots"][mode])
            actual = {str(path.relative_to(root)) for path in root.rglob("*")}
            assert actual == set(by_case[label]["after"])
            for name, entry in by_case[label]["after"].items():
                path = root / name
                assert not path.is_symlink()
                if entry["kind"] == "file":
                    assert digest(path) == entry["sha256"]
                else:
                    assert path.is_dir()
        for name, entry in commands[-1]["sourceAfter"].items():
            path = Path(receipt["source"]) / name
            if entry["kind"] == "file":
                assert digest(path) == entry["sha256"]
    return commands, by_case


def observed(row, stderr):
    code = row["outcome"]["exitCode"]
    assert code in [0, 101]
    b = row["after"].get("bin/" + B)
    survives = b is not None and b["kind"] == "file"
    headline = bool(re.search(r"^\s*Replaced package .*\(executable `" + re.escape(A) + r"`\)\s*$", stderr, re.M))
    return [int(code != 0), int(survives), int(headline)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-only", action="store_true")
    args = parser.parse_args()
    commands, by_case = inspect(args.public_only)
    output = ROOT / ".build/cargo-no-track-formal"
    output.mkdir(parents=True, exist_ok=True)
    lean, bend = os.environ.get("LEAN", "lean"), os.environ.get("BEND", "bend")
    env = dict(os.environ, LEAN_PATH=str(output), BEND_NO_TELEMETRY="1")
    module = output / "applications/cargo-install/Completion.olean"
    module.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run([lean, "-DwarningAsError=true", "-o", str(module), "applications/cargo-install/Completion.lean"],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
    assert p.returncode == 0, p.stdout + p.stderr
    rows = [dict(tracking=mode, replacementFailed=failed, stagedPrefixAdmitted=True, laterFailureExcluded=True)
            for mode in range(3) for failed in [False, True]]
    data = dict(schema=1, profile="staged-new-bin-and-replacement", rows=rows)
    input_path = output / "input.json"

    def replay(value):
        input_path.write_text(json.dumps(value) + "\n")
        return subprocess.run([lean, "--run", "applications/cargo-install/CompletionCase.lean", str(input_path)],
                              cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)

    p = replay(data)
    assert p.returncode == 0, p.stdout + p.stderr
    actual = json.loads(p.stdout)
    calls = ["C.render(" + str(row["tracking"]) + "n," + ("True{}" if row["replacementFailed"] else "False{}") + ') ++ "\\n"'
             for row in rows]
    driver = output / "driver.bend"
    driver.write_text('import Base\nimport ../../applications/cargo-install/Completion.bend as C\n'
                      '\ndef main() -> IO(Unit):\n  IO.write(' + " ++ ".join(calls) + ')\n')
    p = subprocess.run([bend, str(driver)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
    assert p.returncode == 0, p.stdout + p.stderr
    assert p.stdout.splitlines() == actual
    measured = []
    for name, index in [("untracked-force", 1), ("tracked-force-control", 3)]:
        row = by_case[name]
        stderr = (RUN / row["streams"]["stderr"]["file"]).read_text()
        observation = observed(row, stderr)
        assert observation == [int(v) for v in actual[index].split("/")[:3]], (name, observation, actual[index])
        measured.append(dict(case=name, input=rows[index], observation=observation, nativeFields=3))
    refusals = []
    for name, edit in [
        ("schema", lambda d: d.update(schema=2)),
        ("profile", lambda d: d.update(profile="arbitrary-install")),
        ("tracking", lambda d: d["rows"][0].update(tracking=3)),
        ("prefix", lambda d: d["rows"][0].update(stagedPrefixAdmitted=False)),
        ("later-failure", lambda d: d["rows"][0].update(laterFailureExcluded=False)),
        ("boolean", lambda d: d["rows"][0].update(replacementFailed="true")),
        ("count", lambda d: d.update(rows=d["rows"] * 3)),
    ]:
        bad = copy.deepcopy(data)
        edit(bad)
        p = replay(bad)
        assert p.returncode == 2 and not p.stdout, (name, p.stdout, p.stderr)
        refusals.append(name)
    mutations = []
    row = by_case["untracked-force"]
    stderr = (RUN / row["streams"]["stderr"]["file"]).read_text()
    wanted = measured[0]["observation"]
    for label in ["exit", "new-bin", "headline"]:
        bad = copy.deepcopy(row)
        text = stderr
        if label == "exit":
            bad["outcome"]["exitCode"] = 101
        elif label == "new-bin":
            del bad["after"]["bin/" + B]
        else:
            text = text.replace("Replaced package", "Replacement not confirmed")
        assert observed(bad, text) != wanted
        mutations.append(label)
    input_path.write_text(json.dumps(data) + "\n")
    result = dict(schema=1, nativeCommandBoundaries=len(commands), measuredCompletionCases=measured,
                  finiteCases=[dict(input=row, result=value,
                                    evidenceKind="native-compared" if index in [1, 3] else "source-only")
                               for index, (row, value) in enumerate(zip(rows, actual))],
                  decoderRefusals=refusals, changedObservationControls=mutations,
                  models={str(path.relative_to(ROOT)): digest(path) for path in [HERE / "Completion.lean", HERE / "CompletionCase.lean", HERE / "Completion.bend"]},
                  privateChecksExcluded=args.public_only,
                  excludedPrivateChecks=["installed-cargo-rustc", "current-owned-install-contents", "current-known-source-files"] if args.public_only else [],
                  limits=["Only two staged completion cases have native comparisons; other tracking outcomes are source interpretations.",
                          "The proposed result contract is model-only; cleanup and metadata reconciliation are not implemented."])
    (RUN / ("completion-public.json" if args.public_only else "completion.json")).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(nativeCompletionCases=2, nativeScalars=6, sourceCases=6, decoderRefusals=len(refusals), changedControls=len(mutations))))


if __name__ == "__main__":
    main()
