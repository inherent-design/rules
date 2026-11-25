#!/usr/bin/env python3
"""Audit/export authored literal-record observations; never runs Java or a game."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from urllib.parse import unquote, urlparse
import zipfile

from block_term_probe import cases

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VERSIONS = ["1.21.5", "1.21.11", "26.3"]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit(private, export=False):
    profiles = []
    source = json.loads((private / "blockstate-term-bytecode-20261125T223910545705Z/receipt.json").read_text())
    originals = {r["release"]: r for r in source["profiles"]}
    targets = {t["release"]: t for t in json.loads((HERE / "targets.json").read_text())["javaReferences"]}
    for version in VERSIONS:
        capture = Path(json.loads((private / ("latest-block-term-" + version + ".json")).read_text())["capture"])
        r, request, observed = [json.loads((capture / n).read_text()) for n in ["receipt.json", "request.json", "observed.json"]]
        assert r["schema"] == request["schema"] == observed["schema"] == 1 and r["release"] == version
        assert request["cases"] == cases() and [c["id"] for c in observed["cases"]] == [c["id"] for c in cases()]
        for name, digest in r["producerSha256"].items(): assert sha(capture / name) == digest
        for name, current in [("BlockTermProbe.java", HERE / "BlockTermProbe.java"), ("block_term_probe.py", HERE / "block_term_probe.py"), ("mappings.py", HERE / "mappings.py"), ("arena_probe.py", HERE.parent / "java/arena_probe.py")]:
            assert sha(current) == r["producerSha256"][name]
        assert sha(capture / "request.json") == r["requestSha256"]
        for name in ["observed.json", "class-load.log"]: assert sha(capture / name) == r[name + "Sha256"]
        for name, digest in r["observerClassSha256"].items(): assert sha(capture / "classes" / name) == digest
        for name, tool in r["tools"].items(): assert sha(Path(tool["path"])) == tool["sha256"]
        jdk = Path(r["tools"]["java"]["path"]).parents[1]
        assert sha(jdk / "release") == r["jdkReleaseSha256"]
        assert sha(Path(r["gson"]["path"])) == r["gson"]["sha256"]
        plan = json.loads((capture / "inputs.json").read_text())["profiles"][version]
        client = Path(plan["client"]).resolve()
        assert sha(client) == r["clientSha256"] == targets[version]["source"]["clientSha256"] == originals[version]["clientSha256"]
        assert sha(Path(plan["metadata"])) == r["metadataSha256"] == targets[version]["source"]["metadataSha256"]
        if "mappings" in plan: assert sha(Path(plan["mappings"])) == r["mappingSha256"] == originals[version]["mappingSha256"]
        with zipfile.ZipFile(client) as archive:
            assert hashlib.sha256(archive.read(r["originalClass"].replace(".", "/") + ".class")).hexdigest() == r["originalClassSha256"] == originals[version]["classEntrySha256"][r["originalClass"]]
        loaded = []
        for line in (capture / "class-load.log").read_text().splitlines():
            if " source: file:" not in line: continue
            name, uri = line.split(" source: ", 1)
            if Path(unquote(urlparse(uri).path)).resolve() == client: loaded.append(name.split("[class,load]")[-1].strip())
        assert loaded == [r["originalClass"]] and observed["originalClass"] == r["originalClass"] and observed["originalSigners"] > 0
        assert len(r["commands"]) == 2
        for name, command in zip(["compile", "execute"], r["commands"], strict=True):
            assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
            for stream in ["stdout", "stderr"]: assert sha(capture / (name + "." + stream)) == command[stream + "Sha256"]
        profile = dict(release=version, target=r["target"], capture=capture.name, privateReceiptSha256=sha(capture / "receipt.json"),
            clientSha256=r["clientSha256"], profile={k: observed[k] for k in ["os", "osVersion", "architecture", "javaVersion"]})
        public = HERE / "evidence" / capture.name
        if export:
            public.mkdir(exist_ok=True)
            for name in ["request.json", "observed.json", "compile.stdout", "compile.stderr", "execute.stdout", "execute.stderr"]: shutil.copyfile(capture / name, public / name)
            normalized = {k: v for k, v in r.items() if k not in ["gson", "tools", "commands"]}
            normalized["gson"] = {k: v for k, v in r["gson"].items() if k != "path"}
            normalized["tools"] = {k: {"sha256": v["sha256"]} for k, v in r["tools"].items()}
            normalized["commands"] = [{k: v for k, v in cmd.items() if k != "argv"} for cmd in r["commands"]]
            normalized["originalClientClassesLoaded"] = loaded
            normalized["normalization"] = "Authored request/observations/streams unchanged;private receipt tool/argv locations omitted;full class-load trace,original client and frozen producers remain private."
            (public / "receipt.json").write_text(json.dumps(normalized, indent=2) + "\n")
        if public.exists(): profile["publicPayloadSha256"] = {p.name: sha(p) for p in sorted(public.iterdir()) if p.is_file()}
        profiles.append(profile)
    if export: (HERE / "block-term-captures.json").write_text(json.dumps(dict(schema=1, scope="72 literal record scenarios/60 explicit reparses;not full conditions or property/state admission.", profiles=profiles), indent=2) + "\n")
    return dict(schema=1, profiles=3, scenarioRows=72, explicitReparseAttempts=60, originalClassClosure=True, frozenProducersAndArtifacts=True, allRecordedGroupsAbsent=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private", type=Path, required=True)
    p.add_argument("--export", action="store_true")
    args = p.parse_args()
    print(json.dumps(audit(args.private.resolve(), args.export)))


if __name__ == "__main__":
    main()
