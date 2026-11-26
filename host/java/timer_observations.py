#!/usr/bin/env python3
"""Audit/export retained authored timers; no JVM, callbacks, or application run."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

HERE = Path(__file__).resolve().parent


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def definitions():
    """Source adapter for the frozen helper's six objects, not a native RPC log."""
    values = [
        ("cancel-fresh-task", 1, None, 0, None, None),
        ("schedule-canceled-task", 0, 0, 0, 86400000, None),
        ("schedule-future-task", 0, 0, 1, 86400000, 86400000),
        ("schedule-same-task-again", 0, 0, 1, 86400000, 86400000),
        ("cancel-scheduled-task", 1, None, 1, None, None),
        ("cancel-task-again", 1, None, 1, None, None),
        ("move-canceled-task-to-new-timer", 0, 1, 1, 86400000, None),
        ("negative-delay", 0, 1, 2, -1, None),
        ("retry-same-task-valid-delay", 0, 1, 2, 86400000, None),
        ("zero-period", 0, 1, 3, 86400000, 0),
        ("retry-same-task-valid-period", 0, 1, 3, 86400000, 86400000),
        ("cancel-first-timer", 2, 0, None, None, None),
        ("cancel-first-timer-again", 2, 0, None, None, None),
        ("fresh-task-on-canceled-timer", 0, 0, 4, 86400000, None),
        ("fresh-task-on-second-timer", 0, 1, 5, 86400000, None),
    ]
    return [dict(id=i, name=name, operation=op, timer=timer, task=task, delayMs=delay, periodMs=period)
            for i, (name, op, timer, task, delay, period) in enumerate(values)]


def packet(major, definitions):
    rows = []
    for d in definitions:
        valid = None
        if d["operation"] == 0:
            assert d["delayMs"] in [-1, 86400000] and d["periodMs"] in [None, 0, 86400000]
            valid = d["delayMs"] >= 0 and (d["periodMs"] is None or d["periodMs"] > 0)
        rows.append({k: d[k] for k in ["id", "operation", "timer", "task"]} | dict(validArguments=valid))
    return dict(schema=1, contract="jdk-timer-admission-v1", java=int(major), rows=rows)


def observe(output, definitions):
    assert output["schema"] == 1 and output["ownedThreads"] == 2
    assert output["os"] == "Mac OS X" and output["architecture"] == "aarch64"
    events = output["events"]
    assert len(events) == 16 and events[-1] == dict(id="owned-timer-threads-retired", error=0, value=True, callbacks=0)
    assert type(events[-1]["value"]) is bool and type(events[-1]["error"]) is int and type(events[-1]["callbacks"]) is int
    rows = []
    for d, raw in zip(definitions, events[:-1], strict=True):
        assert raw["id"] == d["name"] and type(raw["error"]) is int and raw["error"] in [0, 1, 2]
        assert type(raw["callbacks"]) is int and raw["callbacks"] == 0
        if d["operation"] == 1:
            assert raw["error"] == 0 and type(raw["value"]) is bool
        else:
            assert "value" not in raw
        rows.append(dict(id=d["id"], error=raw["error"], value=raw.get("value")))
    return rows


def audit(private, export=False):
    profiles = []
    for major in ["17", "21", "25"]:
        capture = Path(json.loads((private / ("latest-timer-" + major + ".json")).read_text())["capture"])
        receipt = json.loads((capture / "receipt.json").read_text())
        output = json.loads((capture / "execute.stdout").read_text())
        assert output["java"].startswith(major + ".") and receipt["profile"]["JAVA_VERSION"] == output["java"]
        assert receipt["profile"]["OS_NAME"] == "Darwin" and receipt["profile"]["OS_ARCH"] == "aarch64"
        assert receipt["exactCaptureProcessReadback"] == []
        for name, digest in receipt["producerSha256"].items():
            assert sha(capture / name) == digest == sha(HERE / name)
        for name, digest in receipt["classSha256"].items():
            path = capture / "classes" / name
            assert sha(path) == digest and path.read_bytes()[:8] == bytes.fromhex("cafebabe0000003d")
        for name, tool in receipt["tools"].items(): assert sha(Path(tool["path"])) == tool["sha256"]
        jdk = Path(receipt["tools"]["java"]["path"]).parents[1]
        assert sha(jdk / "release") == receipt["jdkReleaseSha256"]
        with zipfile.ZipFile(jdk / "lib/src.zip") as archive:
            for name, digest in receipt["installedSourceEntrySha256"].items():
                assert hashlib.sha256(archive.read(name)).hexdigest() == digest
        for name, command in zip(["compile", "execute"], receipt["commands"], strict=True):
            assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
            for stream in ["stdout", "stderr"]:
                assert sha(capture / (name + "." + stream)) == command[stream + "Sha256"]
        observe(output, definitions())
        public = HERE / "evidence" / capture.name
        if export:
            public.mkdir(exist_ok=True)
            for name in ["compile.stdout", "compile.stderr", "execute.stdout", "execute.stderr"]:
                shutil.copyfile(capture / name, public / name)
            normalized = {k: v for k, v in receipt.items() if k not in ["tools", "commands"]}
            normalized["tools"] = {k: dict(sha256=v["sha256"]) for k, v in receipt["tools"].items()}
            normalized["commands"] = [{k: v for k, v in c.items() if k != "argv"} for c in receipt["commands"]]
            normalized["normalization"] = "Authored stdout/stderr unchanged;only tool/command locations omitted from receipt. Frozen producers,compiled helpers,JDK executables/source entries and original commands private. Exact OS build was not recorded."
            (public / "receipt.json").write_text(json.dumps(normalized, indent=2) + "\n")
        profile = dict(java=int(major), capture=capture.name, privateReceiptSha256=sha(capture / "receipt.json"),
                       javaVersion=output["java"], os=output["os"], architecture=output["architecture"])
        if public.exists(): profile["publicPayloadSha256"] = {p.name: sha(p) for p in sorted(public.iterdir()) if p.is_file()}
        profiles.append(profile)
    if export:
        manifest = dict(schema=1, exporterSha256=sha(Path(__file__)),
                        operationAdapter=dict(producerSha256=sha(HERE / "TimerProbe.java"), definitions=definitions(),
                            limits="Source-derived object labels/overload arguments from the frozen authored helper,not captured internal JDK state or an RPC stream."), profiles=profiles)
        (HERE / "timer-captures.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return dict(schema=1, profiles=3, admissionOperations=45, independentRetirementWitnesses=3,
                callbackSamples=48, callbackCount=0, recordedCompilerJvmGroupsAbsent=6,
                limits="macOSarm64 only;OS build unrecorded. No callbacks run,clock jumps,latency,arbitrary concurrent retirement,application or game qualification.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()
    print(json.dumps(audit(args.private.resolve(), args.export)))
