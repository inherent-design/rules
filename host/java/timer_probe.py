#!/usr/bin/env python3
"""Owner-run JDK17/21/25 far-future timer admission/cancel fixture; outside CI."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

from arena_probe import command

HERE = Path(__file__).resolve().parent


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jdk", type=Path, required=True)
    parser.add_argument("--private", type=Path, required=True)
    args = parser.parse_args()
    jdk = args.jdk.resolve()
    fields = dict(re.findall(r'^([A-Z_]+)="([^"]*)"', (jdk / "release").read_text(), re.M))
    major = fields["JAVA_VERSION"].split(".")[0]
    assert major in ["17", "21", "25"] and fields["OS_NAME"] == "Darwin"
    capture = args.private.resolve() / ("timer-" + major + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    capture.mkdir(parents=True)
    for name in ["classes", "home", "tmp"]: (capture / name).mkdir()
    sources = ["timer_probe.py", "TimerProbe.java", "arena_probe.py"]
    for name in sources: shutil.copyfile(HERE / name, capture / name)
    with zipfile.ZipFile(jdk / "lib/src.zip") as archive:
        source_entries = {name: hashlib.sha256(archive.read(name)).hexdigest()
                          for name in ["java.base/java/util/Timer.java", "java.base/java/util/TimerTask.java"]}
    record = dict(schema=1, profile={k: fields[k] for k in ["JAVA_VERSION", "JAVA_RUNTIME_VERSION", "OS_NAME", "OS_ARCH", "IMPLEMENTOR"]},
                  jdkReleaseSha256=sha(jdk / "release"), tools={n: dict(path=str(jdk / "bin" / n), sha256=sha(jdk / "bin" / n)) for n in ["java", "javac"]},
                  producerSha256={n: sha(capture / n) for n in sources}, installedSourceEntrySha256=source_entries, commands=[],
                  scope="Owned authored Timer/TimerTask objects and far-future scheduling only;no callbacks selected to run,UI/game,otherapp,wall-clock-change,timing guarantee or arbitrary concurrent retirement.")
    def save(): (capture / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
    env = dict(os.environ, TMPDIR=str(capture / "tmp"))
    startup = ["JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS", "CLASSPATH", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH", "DYLD_FALLBACK_LIBRARY_PATH"]
    record["removedChildEnvironmentKeys"] = [k for k in startup if k in env]
    for key in startup: env.pop(key, None)
    save()
    compile_args = [str(jdk / "bin/javac"), "-J-XX:ActiveProcessorCount=2", "-J-Xmx96m", "--release", "17", "-proc:none", "-Xlint:all", "-Werror", "-d", str(capture / "classes"), str(capture / "TimerProbe.java")]
    record["commands"].append(command(compile_args, capture, "compile", env, 30)); save()
    assert record["commands"][-1]["exitCode"] == 0, capture
    execute = [str(jdk / "bin/java"), "-XX:ActiveProcessorCount=2", "-Xmx96m", "-Djava.awt.headless=true",
               "-Duser.home=" + str(capture / "home"), "-Djava.io.tmpdir=" + str(capture / "tmp"),
               "-cp", str(capture / "classes"), "study.host.TimerProbe"]
    record["commands"].append(command(execute, capture, "execute", env, 30))
    record["classSha256"] = {str(p.relative_to(capture / "classes")): sha(p) for p in (capture / "classes").rglob("*.class")}
    record["exactCaptureProcessReadback"] = [line for line in subprocess.check_output(["ps", "-axo", "pid=,ppid=,pgid=,command="], text=True).splitlines() if str(capture) in line]
    save()
    assert not record["exactCaptureProcessReadback"] and all(r["exitCode"] == 0 and r["ownedGroupAbsent"] and not r["timedOut"] for r in record["commands"]), capture
    observed = json.loads((capture / "execute.stdout").read_text())
    assert len(observed["events"]) == 16 and all(row["callbacks"] == 0 for row in observed["events"])
    assert all(sha(capture / n) == digest for n, digest in record["producerSha256"].items())
    (args.private / ("latest-timer-" + major + ".json")).write_text(json.dumps(dict(capture=str(capture))) + "\n")
    print(json.dumps(dict(capture=str(capture), events=16, callbacks=0, groupsAbsent=True)))


if __name__ == "__main__":
    main()
