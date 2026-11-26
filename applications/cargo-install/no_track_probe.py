#!/usr/bin/env python3
"""Compare owned replacement failure with and without Cargo install tracking."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "rules-no-track-ownership"
A, B = "rules-no-track-a", "rules-no-track-b"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image(root):
    result = {}
    for path in sorted(root.rglob("*")):
        value = path.lstat()
        row = {"mode": stat.S_IMODE(value.st_mode), "inode": value.st_ino,
               "device": value.st_dev, "mtimeNs": value.st_mtime_ns}
        if stat.S_ISDIR(value.st_mode):
            row["kind"] = "directory"
        elif stat.S_ISREG(value.st_mode):
            row.update(kind="file", bytes=value.st_size, sha256=digest(path))
        else:
            raise RuntimeError("Unexpected nonregular fixture entry: " + str(path))
        result[str(path.relative_to(root))] = row
    return result


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    capture = ROOT / "applications/evidence" / ("cargo-install-no-track-" + stamp)
    capture.mkdir()
    work = Path(tempfile.mkdtemp(prefix="rules-cargo-no-track-", dir="/private/tmp"))
    project = work / "project"
    for name in ["project/src", "home", "cargo-home", "tmp", "target"]:
        (work / name).mkdir(parents=True, exist_ok=True)
    for parent in [project, *project.parents]:
        for name in ["config", "config.toml"]:
            if (parent / ".cargo" / name).exists():
                raise RuntimeError("Ancestor Cargo configuration; refusing before collection")
    (work / "cargo-home/config.toml").write_text("[net]\noffline=true\n")
    (project / "Cargo.toml").write_text(
        '[package]\nname="' + PACKAGE + '"\nversion="0.1.0"\nedition="2021"\n'
        'autobins=false\n[workspace]\n[[bin]]\nname="' + A + '"\npath="src/a.rs"\n'
        '[[bin]]\nname="' + B + '"\npath="src/b.rs"\n[profile.release]\n'
        'opt-level=0\ndebug=0\nstrip="symbols"\ncodegen-units=1\n')
    for name in ["a", "b"]:
        (project / "src" / (name + ".rs")).write_text(
            'fn main() { println!("owned-' + name + '"); }\n')
    pins = json.loads((ROOT / "applications/sources/local-pins.json").read_text())["tools"]
    cargo = Path(pins["cargo"]["path"])
    previous = json.loads((ROOT / "applications/evidence/cargo-install-20261125T003504421536Z/receipt.json").read_text())
    tools = previous["tools"]
    for row in tools.values():
        if digest(Path(row["path"])) != row["sha256"]:
            raise RuntimeError("Pinned tool changed: " + row["path"])
    env = dict(PATH=str(cargo.parent) + ":/usr/bin:/bin", HOME=str(work / "home"),
               CARGO_HOME=str(work / "cargo-home"), TMPDIR=str(work / "tmp"),
               RUSTC=str(cargo.with_name("rustc")), RUSTDOC=str(cargo.with_name("rustdoc")),
               CARGO_NET_OFFLINE="true", CARGO_BUILD_JOBS="1", CARGO_INCREMENTAL="0",
               CARGO_TERM_COLOR="never", LANG="en_US.UTF-8")
    (capture / "producer.py").write_bytes(Path(__file__).read_bytes())
    frozen = {str(p.relative_to(project)): p.read_text()
              for p in sorted(project.rglob("*")) if p.is_file()}
    (capture / "initial-source.json").write_text(json.dumps(frozen, indent=2) + "\n")
    rows = []
    roots = {}
    for mode in ["untracked", "tracked"]:
        root = work / mode
        (root / "bin" / A).mkdir(parents=True)
        (root / "bin" / A / "owned-marker").write_text("Preserve this owned blocker.\n")
        (root / "bin/unrelated-marker").write_text("Outside the requested binary set.\n")
        roots[mode] = root

    def command(label, argv, root):
        before, source_before = image(root), image(project)
        start = time.monotonic()
        with (capture / (label + ".stdout")).open("xb") as out, (capture / (label + ".stderr")).open("xb") as err:
            process = subprocess.Popen([str(a) for a in argv], cwd=project, env=env,
                                       stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                       start_new_session=True)
            (capture / "active-process.json").write_text(json.dumps({"pid": process.pid, "case": label}) + "\n")
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
        row = dict(case=label, argv=[str(a) for a in argv], before=before, after=image(root),
                   sourceBefore=source_before, sourceAfter=image(project),
                   outcome=dict(exitCode=process.returncode, timedOut=timed_out, ownedGroupAbsent=absent),
                   seconds=time.monotonic() - start,
                   streams={s: {"file": label + "." + s, "sha256": digest(capture / (label + "." + s))}
                            for s in ["stdout", "stderr"]})
        rows.append(row)
        (capture / "commands.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(label, process.returncode, round(row["seconds"], 2), flush=True)
        if timed_out or not absent:
            raise RuntimeError("Owned process did not retire normally")
        for key in ["bin/" + A + "/owned-marker", "bin/unrelated-marker"]:
            if row["before"][key] != row["after"][key]:
                raise RuntimeError("Command changed protected owned marker: " + key)
        return row

    def install(label, mode, flags):
        return command(label, [cargo, "install", "--offline", "--path", project,
                               "--root", roots[mode], "--target-dir", work / "target", *flags], roots[mode])

    command("version", [cargo, "--version"], roots["untracked"])
    install("untracked-no-force", "untracked", ["--no-track"])
    install("untracked-force", "untracked", ["--no-track", "--force"])
    if (roots["untracked"] / "bin" / B).is_file():
        command("untracked-b-runtime", [roots["untracked"] / "bin" / B], roots["untracked"])
    install("tracked-force-control", "tracked", ["--force"])
    command("tracked-list", [cargo, "install", "--list", "--root", roots["tracked"]], roots["tracked"])
    for mode, root in roots.items():
        for name in [".crates.toml", ".crates2.json"]:
            path = root / name
            if path.is_file():
                (capture / (mode + "-" + name.lstrip("."))).write_bytes(path.read_bytes())
    receipt = dict(schema=1, tools=tools, producerSha256=digest(capture / "producer.py"),
                   work=str(work), source=str(project), roots={k: str(v) for k, v in roots.items()},
                   commands=len(rows), allOwnedGroupsAbsent=all(r["outcome"]["ownedGroupAbsent"] for r in rows),
                   limits=["Generated two-bin path crate on one Mac; no other source, install root, or config is used.",
                           "No injected tracking-write failure, interruption, concurrency, or other host qualification."])
    (capture / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    (ROOT / ".build/cargo-install-no-track-capture.json").write_text(json.dumps({"capture": str(capture.relative_to(ROOT))}) + "\n")
    print("capture", capture.relative_to(ROOT), flush=True)


if __name__ == "__main__":
    main()
