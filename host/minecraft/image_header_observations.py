#!/usr/bin/env python3
"""Audit frozen owner-run inputs/artifacts; export authored data, never client source."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from image_header_probe import arithmetic, cases

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VERSIONS = ["1.21.1", "1.21.4", "1.21.5", "1.21.11", "26.3", "java17"]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit(private, export=False):
    profiles = []
    bytecode = json.loads((private / "image-header-bytecode-20261125T215553523243Z/receipt.json").read_text())
    sources = {r["release"]: r for r in bytecode["profiles"]}
    for version in VERSIONS:
        capture = Path(json.loads((private / ("latest-image-header-" + version + ".json")).read_text())["capture"])
        r = json.loads((capture / "receipt.json").read_text())
        request = json.loads((capture / "request.json").read_text())
        observed = json.loads((capture / "observed.json").read_text())
        assert r["release"] == version and r["schema"] == request["schema"] == observed["schema"] == 1
        assert request["cases"] == ([] if version == "java17" else cases())
        assert request["arithmetic"] == (arithmetic() if version in ["java17", "1.21.1", "26.3"] else [])
        assert sha(capture / "request.json") == r["requestSha256"]
        for name, digest in r["producerSha256"].items(): assert sha(capture / name) == digest
        for name, current in [("ImageHeaderProbe.java", HERE / "ImageHeaderProbe.java"), ("image_header_probe.py", HERE / "image_header_probe.py"),
                ("mappings.py", HERE / "mappings.py"), ("arena_probe.py", HERE.parent / "java/arena_probe.py")]:
            assert sha(current) == r["producerSha256"][name]
        for name, digest in r["observerClassSha256"].items(): assert sha(capture / "classes" / name) == digest
        for name in ["observed.json", "class-load.log"]: assert sha(capture / name) == r[name + "Sha256"]
        for name, tool in r["tools"].items(): assert sha(Path(tool["path"])) == tool["sha256"]
        jdk = Path(r["tools"]["java"]["path"]).parents[1]
        assert sha(jdk / "release") == r["jdkReleaseSha256"]
        gson = r["gson"]
        assert sha(Path(gson["path"])) == gson["sha256"]
        assert sha(ROOT / ".build/minecraft/resource-cache-20261125T195402530738Z/receipt.json") == r["gsonBasisSha256"]
        assert len(r["commands"]) == 2
        for name, command in zip(["compile", "execute"], r["commands"], strict=True):
            assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
            for stream in ["stdout", "stderr"]: assert sha(capture / (name + "." + stream)) == command[stream + "Sha256"]
        client_loads = [line for line in (capture / "class-load.log").read_text().splitlines() if " source: file:" in line and "minecraft" in line.split(" source: file:")[1] and ".jar" in line.split(" source: file:")[1]]
        if version != "java17":
            plan = json.loads((capture / "inputs.json").read_text())["profiles"][version]
            client = Path(plan["client"])
            assert sha(client) == r["clientSha256"] == sources[version]["clientSha256"]
            assert sha(Path(plan["metadata"])) == r["metadataSha256"]
            if "mappings" in plan: assert sha(Path(plan["mappings"])) == r["mappingSha256"] == sources[version]["mappingSha256"]
            with zipfile.ZipFile(client) as archive:
                digest = hashlib.sha256(archive.read(r["originalClass"].replace(".", "/") + ".class")).hexdigest()
            assert digest == r["originalClassSha256"] == sources[version]["classEntrySha256"]
            assert len(client_loads) == 1 and (" " + r["originalClass"] + " source:") in client_loads[0]
            assert observed["originalClass"] == r["originalClass"] and observed["originalSigners"] > 0
        else:
            assert r["clientSha256"] is None and not client_loads and "originalClass" not in observed
        expected_java = "17." if version == "java17" else "25." if version == "26.3" else "21."
        assert observed["javaVersion"].startswith(expected_java)
        assert observed["os"] == "Mac OS X" and observed["architecture"] == "aarch64"
        assert [row["id"] for row in request["cases"]] == [row["id"] for row in observed["cases"]]
        for spec, row in zip(request["cases"], observed["cases"], strict=True):
            data = bytes.fromhex(spec["hex"])
            before = dict(order=spec["order"], position=spec["position"], limit=spec["limit"], capacity=len(data), remaining=spec["limit"] - spec["position"], readOnly=spec["readOnly"], bytesSha256=hashlib.sha256(data).hexdigest())
            assert len(data) == 33 and row["before"] == before
            assert {k: v for k, v in row["after"].items() if k != "order"} == {k: v for k, v in before.items() if k != "order"}
            assert row["status"] in ["returned", "threw"]
        public = HERE / "evidence" / capture.name
        profile = dict(release=version, capture=capture.name, target=r["target"], clientSha256=r["clientSha256"],
            privateReceiptSha256=sha(capture / "receipt.json"), profile={k: observed[k] for k in ["os", "osVersion", "architecture", "javaVersion"]})
        if export:
            public.mkdir(exist_ok=True)
            for name in ["request.json", "observed.json", "compile.stdout", "compile.stderr", "execute.stdout", "execute.stderr"]: shutil.copyfile(capture / name, public / name)
            # Omit private filesystem/tool/argv locations; the original receipt
            # and complete class-load trace remain private and digest-bound.
            normalized = {k: v for k, v in r.items() if k not in ["gson", "tools", "commands"]}
            normalized["gson"] = {k: v for k, v in gson.items() if k != "path"}
            normalized["tools"] = {k: {"sha256": v["sha256"]} for k, v in r["tools"].items()}
            normalized["commands"] = [{k: v for k, v in command.items() if k != "argv"} for command in r["commands"]]
            normalized["originalClientClassesLoaded"] = [] if version == "java17" else [r["originalClass"]]
            normalized["normalization"] = "Authored request/observations/streams unchanged. Only private receipt locations/argv omitted; full class-load trace and original client retained privately."
            (public / "receipt.json").write_text(json.dumps(normalized, indent=2) + "\n")
        if public.exists(): profile["publicPayloadSha256"] = {p.name: sha(p) for p in sorted(public.iterdir()) if p.is_file()}
        profiles.append(profile)
    if export:
        (HERE / "image-header-captures.json").write_text(json.dumps(dict(schema=1, scope="165 original header calls and 12 JDK arithmetic checks; no decoding or image allocation.", profiles=profiles), indent=2) + "\n")
    return dict(schema=1, profiles=len(profiles), originalCalls=165, arithmeticCalls=12, producerAndArtifactAudit=True, allRecordedGroupsAbsent=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private", type=Path, required=True)
    p.add_argument("--export", action="store_true")
    args = p.parse_args()
    print(json.dumps(audit(args.private.resolve(), args.export)))


if __name__ == "__main__":
    main()
