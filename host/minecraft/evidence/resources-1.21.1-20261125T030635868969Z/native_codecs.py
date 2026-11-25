#!/usr/bin/env python3
"""Owner-run original-client codec comparisons. No download or game launch.

Requires the explicitly acquired private inputs. Ordinary rules CI must not run
this collector. Original mappings, clients and libraries remain private inputs.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import zipfile

from mappings import read as read_mappings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
JDK = Path("/Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home/bin")


def sha(path, algorithm="sha256"):
    return hashlib.new(algorithm, path.read_bytes()).hexdigest()


def run_command(argv, directory, name, env, timeout=45):
    with (directory / (name + ".stdout")).open("wb") as out, (directory / (name + ".stderr")).open("wb") as err:
        process = subprocess.Popen(argv, cwd=directory, env=env, stdout=out, stderr=err, start_new_session=True)
        timed_out = False
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait()
    try:
        os.killpg(process.pid, 0)
        absent = False
    except ProcessLookupError:
        absent = True
    return {
        "argv": argv, "exitCode": code, "timedOut": timed_out,
        "ownedGroupAbsent": absent,
        "stdoutSha256": sha(directory / (name + ".stdout")),
        "stderrSha256": sha(directory / (name + ".stderr")),
    }


def collect(private, version):
    sources = {row["id"]: row for row in json.loads((HERE / "sources.json").read_text())["sources"]}
    metadata = json.loads((private / (version + ".json")).read_text())
    local = json.loads((private / "local-basis.json").read_text())
    client = Path(local["vanilla_1.21.1"]["path"]) if version == "1.21.1" else private / (version + "-client.jar")
    mapping_path = private / (version + "-client-mappings.txt")
    assert sha(client) == sources[f"mojang:{version}:client"]["sha256"]
    assert sha(mapping_path) == sources[f"mojang:{version}:client_mappings"]["sha256"]
    libraries = []
    omitted = []
    for row in json.loads((private / "library-locators.json").read_text())[version]:
        if row["cachedPath"] is None:
            assert row["name"].startswith("io.netty:netty-transport-native-epoll:") and ":linux-" in row["name"]
            omitted.append(row["name"])
            continue
        path = Path(row["cachedPath"])
        assert sha(path, "sha1") == row["artifact"]["sha1"]
        libraries.append({"path": str(path), "sha1": row["artifact"]["sha1"], "sha256": sha(path)})
    mappings = read_mappings(mapping_path)
    cases = [dict(row) for row in json.loads((HERE / "codec_cases.json").read_text())["cases"] if version in row["versions"]]
    initializers = [
        {"class": "net.minecraft.SharedConstants", "method": "tryDetectVersion()"},
        {"class": "net.minecraft.server.Bootstrap", "method": "bootStrap()"},
    ]
    client_registries = [
        "net.minecraft.client.renderer.texture.atlas.SpriteSources",
        "net.minecraft.client.renderer.item.ItemModels",
        "net.minecraft.client.renderer.item.properties.conditional.ConditionalItemModelProperties",
        "net.minecraft.client.renderer.item.properties.select.SelectItemModelProperties",
        "net.minecraft.client.renderer.item.properties.numeric.RangeSelectItemModelProperties",
        "net.minecraft.client.color.item.ItemTintSources",
        "net.minecraft.client.renderer.special.SpecialModelRenderers",
    ]
    if version == "1.21.5":
        initializers += [{"class": name, "method": "bootstrap()"} for name in client_registries]
    wanted = {item["class"] for item in initializers}
    for case in cases:
        if case["action"] == "block_model" and version == "1.21.5":
            case.update(reader=True, fields=["geometry"])
        for key in ["class", "holder", "serializer", "observationClass"]:
            if key in case:
                wanted.add(case[key])
        owner = case["class"]
        if case["action"] == "codec":
            assert case["member"] in mappings[owner]["fields"], (version, case["id"], "missing codec member")
        elif case["action"] == "metadata_serializer":
            assert case["member"] in mappings[case["holder"]]["fields"]
    for item in initializers:
        assert item["method"] in mappings[item["class"]]["methods"], item
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = private / ("codecs-" + version + "-" + stamp)
    directory.mkdir()
    for name in ["classes", "home", "tmp"]:
        (directory / name).mkdir()
    for name in ["CodecProbe.java", "mappings.py", "codec_cases.json", "native_codecs.py"]:
        shutil.copyfile(HERE / name, directory / name)
    request = {"mappings": {name: mappings[name] for name in sorted(wanted)}, "initializers": initializers, "cases": cases}
    (directory / "request.json").write_text(json.dumps(request, indent=2, ensure_ascii=False) + "\n")
    with zipfile.ZipFile(client) as archive:
        classes = {name: hashlib.sha256(archive.read(mappings[name]["name"].replace(".", "/") + ".class")).hexdigest() for name in wanted}
    receipt = {
        "schema": 1, "minecraft": version, "scope": "Original-client headless decoding with explicit vanilla registry bootstrap;not a client launch or consumer render.",
        "clientSha256": sha(client), "mappingSha256": sha(mapping_path),
        "requestSha256": sha(directory / "request.json"), "classEntrySha256": classes,
        "sourceSha256": {name: sha(directory / name) for name in ["CodecProbe.java", "mappings.py", "codec_cases.json", "native_codecs.py"]},
        "libraries": libraries, "omittedLinuxNativeTransportArtifacts": omitted,
        "tools": {name: {"path": str(JDK / name), "sha256": sha(JDK / name)} for name in ["java", "javac"]},
        "commands": [], "limits": [
            "JSON inputs exercise codecs/selected parsers only. Resource lookup,reference resolution,baking,rendering and arbitrary syntax are separate obligations.",
            "Vanilla registry bootstrap and explicitly selected client codec registries supply context;no world or dynamic registry from a server is loaded.",
            "Original-client signatures remain intact. Only the study observer is compiled. No renamed/decompiled client is executed.",
            "The request includes private mapping locators;public retained evidence must omit wholesale mapping/client/library payloads.",
        ],
    }
    receipt_path = directory / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    env = dict(os.environ, HOME=str(directory / "home"), TMPDIR=str(directory / "tmp"))
    classpath = os.pathsep.join(row["path"] for row in libraries)
    # Gson 2.11 references optional compile-only InlineMe annotations that the
    # official runtime classpath omits. Keep observer warnings fatal; omit only
    # dependency-classfile annotation diagnostics, without adding runtime jars.
    compile_args = [str(JDK / "javac"), "-proc:none", "-Xlint:all,-classfile", "-Werror", "-encoding", "UTF-8", "-cp", classpath,
                    "-d", str(directory / "classes"), str(directory / "CodecProbe.java")]
    compiled = run_command(compile_args, directory, "compile", env)
    receipt["commands"].append(compiled)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    if compiled["exitCode"] != 0 or not compiled["ownedGroupAbsent"]:
        raise RuntimeError(f"Observer compilation failed; retained {directory}")
    classpath = os.pathsep.join([str(directory / "classes"), str(client), classpath])
    execute_args = [str(JDK / "java"), "-XX:ActiveProcessorCount=2", "-Xmx1G", "-Djava.awt.headless=true",
                    "-Duser.home=" + str(directory / "home"), "-Djava.io.tmpdir=" + str(directory / "tmp"),
                    "-cp", classpath, "study.minecraft.CodecProbe", str(directory / "request.json"), str(directory / "observed.json")]
    executed = run_command(execute_args, directory, "execute", env)
    receipt["commands"].append(executed)
    if (directory / "observed.json").exists():
        results = json.loads((directory / "observed.json").read_text())
        receipt.update(observedSha256=sha(directory / "observed.json"), cases=len(results), observerErrors=sum(row.get("observerError", False) for row in results))
    assert sha(client) == receipt["clientSha256"] and sha(mapping_path) == receipt["mappingSha256"]
    assert all(sha(Path(row["path"])) == row["sha256"] for row in libraries)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"capture": str(directory), "version": version, "exitCode": executed["exitCode"],
                      "cases": receipt.get("cases"), "observerErrors": receipt.get("observerErrors"),
                      "ownedGroupsAbsent": all(row["ownedGroupAbsent"] for row in receipt["commands"])}))
    if executed["exitCode"] != 0 or not executed["ownedGroupAbsent"] or receipt.get("observerErrors"):
        raise RuntimeError(f"Headless observer incomplete; inspect retained {directory}")
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--version", choices=["1.21.1", "1.21.5"], required=True)
    args = parser.parse_args()
    collect(args.private.resolve(), args.version)


if __name__ == "__main__":
    main()
