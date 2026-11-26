#!/usr/bin/env python3
"""Execute only selected MO2 callback registration/drain cuts with real Boost."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def body(text, name):
    start = text.index(name)
    brace = text.index("{", start)
    depth = 0
    for end in range(brace, len(text)):
        depth += (text[end] == "{") - (text[end] == "}")
        if depth == 0:
            return text[start:end + 1]
    raise RuntimeError("Unterminated selected method")


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    capture = ROOT / "applications/evidence" / ("mo2-refresh-callbacks-" + stamp)
    capture.mkdir()
    work = Path(tempfile.mkdtemp(prefix="rules-mo2-refresh-callbacks-", dir="/private/tmp"))
    selection = json.loads((ROOT / "applications/sources/mo2-profile-selections.json").read_text())
    rows = selection if isinstance(selection, list) else selection["sources"]
    source = next(row for row in rows if row["path"] == "src/organizercore.cpp")
    original = ROOT / source["cache"]
    if digest(original) != source["sha256"]:
        raise RuntimeError("Selected source changed")
    text = original.read_text()
    registration = "boost::signals2::connection\n" + body(text, "OrganizerCore::onNextRefresh(")
    drain_statements = ["m_DirectoryUpdate = false;", "m_OnNextRefreshCallbacks();",
                        "m_OnNextRefreshCallbacks.disconnect_all_slots();"]
    completion = body(text, "OrganizerCore::onDirectoryRefreshed()")
    positions = [completion.index(line) for line in drain_statements]
    if positions != sorted(positions):
        raise RuntimeError("Drain order changed")
    header = json.loads((ROOT / ".build/mo2-architecture-header-source.json").read_text())
    header_text = (ROOT / header["cache"]).read_text()
    if digest(ROOT / header["cache"]) != header["sha256"]:
        raise RuntimeError("Header changed")
    if "boost::signals2::signal<void()> m_OnNextRefreshCallbacks;" not in header_text:
        raise RuntimeError("Signal shape differs from research adapter")
    template = HERE / "refresh_callbacks_driver.cpp"
    generated = template.read_text().replace("/*SOURCE_REGISTRATION*/", registration).replace(
        "/*SOURCE_CURRENT_DRAIN*/", "\n    ".join(drain_statements))
    if "/*SOURCE_" in generated:
        raise RuntimeError("Unfilled cut")
    cpp, binary = work / "probe.cpp", work / "probe"
    cpp.write_text(generated)
    (capture / "producer.py").write_bytes(Path(__file__).read_bytes())
    (capture / "driver.cpp").write_bytes(template.read_bytes())
    sdk = subprocess.check_output(["/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-path"], text=True).strip()
    compiler = Path(subprocess.check_output(["/usr/bin/xcrun", "--find", "clang++"], text=True).strip()).resolve()
    boost = Path("/opt/homebrew/include/boost").resolve()
    if not (boost / "signals2.hpp").is_file():
        raise RuntimeError("No installed Boost; do not install for this probe")
    env = dict(PATH="/usr/bin:/bin", HOME=str(work), TMPDIR=str(work), LANG="en_US.UTF-8")
    commands = []

    def command(name, argv):
        start = time.monotonic()
        with (capture / (name + ".stdout")).open("xb") as out, (capture / (name + ".stderr")).open("xb") as err:
            process = subprocess.Popen([str(value) for value in argv], cwd=work, env=env,
                                       stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
            timed_out = False
            try:
                process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        try:
            os.killpg(process.pid, 0)
            absent = False
        except ProcessLookupError:
            absent = True
        row = dict(case=name, argv=[str(value) for value in argv], pid=process.pid,
                   exitCode=process.returncode, timedOut=timed_out, ownedGroupAbsent=absent,
                   seconds=time.monotonic() - start,
                   streams={s: {"file": name + "." + s, "sha256": digest(capture / (name + "." + s))}
                            for s in ["stdout", "stderr"]})
        commands.append(row)
        (capture / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        print(name, process.returncode, round(row["seconds"], 2), flush=True)
        if timed_out or not absent or process.returncode:
            raise RuntimeError("Selected command failed; preserve capture without retry")

    dep = work / "dependencies.d"
    command("compile", [compiler, "-std=c++20", "-O0", "-isysroot", sdk,
                        "-I", boost.parent, "-MD", "-MF", dep, cpp, "-o", binary])
    command("observe", [binary])
    dependency_paths = shlex.split(dep.read_text().replace("\\\n", " ").split(":", 1)[1])
    dependencies = [{"path": name, "sha256": digest(Path(name))}
                    for name in sorted(set(dependency_paths)) if Path(name).is_file()]
    results = [json.loads(line) for line in (capture / "observe.stdout").read_text().splitlines()]
    if len(results) != 10:
        raise RuntimeError("Unexpected record count")
    receipt = dict(schema=1, source=source, header=header, work=str(work),
                   producerSha256=digest(capture / "producer.py"), driverSha256=digest(capture / "driver.cpp"),
                   generatedSha256=digest(cpp), binarySha256=digest(binary), compiler={"path": str(compiler), "sha256": digest(compiler)},
                   sdk=sdk, boostRoot=str(boost), boostVersionHeaderSha256=digest(boost / "version.hpp"),
                   dependencies=dependencies, commands=len(commands), records=len(results),
                   allOwnedGroupsAbsent=all(row["ownedGroupAbsent"] for row in commands),
                   registrationSha256=hashlib.sha256(registration.encode()).hexdigest(),
                   drainStatements=drain_statements,
                   limits=["Unchanged registration body plus three drain statements, not full OrganizerCore or MO2 execution.",
                           "Real installed Boost; profile, refresh work, Qt signals, UI, VFS and Windows remain outside this fixture.",
                           "Detached-batch alternative executes only in the research adapter; exceptions, cross-thread use and application adoption unqualified."])
    (capture / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    (ROOT / ".build/mo2-refresh-callbacks-capture.json").write_text(json.dumps({"capture": str(capture.relative_to(ROOT))}) + "\n")
    print("capture", capture.relative_to(ROOT), flush=True)


if __name__ == "__main__":
    main()
