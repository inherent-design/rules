#!/usr/bin/env python3
"""Owner-run read-only census of attributed private Minecraft inputs.

This neither downloads nor launches Minecraft. It writes facts to one explicitly
selected output; semantic inventory annotations and models are maintained apart.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile


def digest(path, algorithm="sha256"):
    return hashlib.new(algorithm, path.read_bytes()).hexdigest()


def scan(private, baseline):
    result = {"schema": 1, "versions": {}, "sources": []}
    for version in ["1.21.1", "1.21.5"]:
        metadata = json.loads((private / (version + ".json")).read_text())
        client = baseline if version == "1.21.1" else private / (version + "-client.jar")
        families, markers = Counter(), []
        with zipfile.ZipFile(client) as archive:
            identity = json.loads(archive.read("version.json"))
            for name in archive.namelist():
                if name.startswith("assets/") and not name.endswith("/"):
                    parts = name.split("/")
                    if len(parts) < 3:
                        markers.append(name)
                    else:
                        families[parts[2]] += 1
        assets = json.loads((private / (version + "-assets.json")).read_text())
        external = Counter(
            name.split("/")[1] if "/" in name else "<root>"
            for name in assets["objects"]
        )
        with zipfile.ZipFile(private / (version + "-mapped.jar")) as archive:
            classes = sorted(
                name[:-6].replace("/", ".")
                for name in archive.namelist() if name.endswith(".class")
            )
        result["versions"][version] = {
            "resourcePackFormat": identity["pack_version"]["resource"],
            "dataPackFormat": identity["pack_version"]["data"],
            "clientAssetFamilies": dict(sorted(families.items())),
            "clientRootMarkers": sorted(markers),
            "externalAssetFamilies": dict(sorted(external.items())),
            "externalObjects": len(assets["objects"]),
            "mappedClasses": classes,
        }
        for kind, path, entry in [
            ("client", client, metadata["downloads"]["client"]),
            ("client_mappings", private / (version + "-client-mappings.txt"), metadata["downloads"]["client_mappings"]),
            ("asset_index", private / (version + "-assets.json"), metadata["assetIndex"]),
        ]:
            if digest(path, "sha1") != entry["sha1"]:
                raise ValueError(f"Official input hash mismatch: {version}/{kind}")
            result["sources"].append({
                "id": f"mojang:{version}:{kind}", "kind": kind,
                "version": version, "url": entry["url"], "sha1": entry["sha1"],
                "sha256": digest(path), "bytes": path.stat().st_size,
                "publicPayload": False,
            })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--baseline-client", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    facts = scan(args.private, args.baseline_client)
    args.output.write_text(json.dumps(facts, indent=2) + "\n")
    print(json.dumps({
        version: {"assetFamilies": len(value["clientAssetFamilies"]),
                  "externalObjects": value["externalObjects"],
                  "mappedClasses": len(value["mappedClasses"])}
        for version, value in facts["versions"].items()
    }))


if __name__ == "__main__":
    main()
