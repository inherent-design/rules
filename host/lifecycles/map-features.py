"""Link application feature witness requests to host contracts without promoting their evidence status."""
import argparse
import hashlib
import json
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--write",action="store_true")
args=parser.parse_args()
root=Path(__file__).resolve().parents[2]
inventory_file=root/"applications/inventory.json"
raw=inventory_file.read_bytes()
inventory=json.loads(raw)
contracts=json.loads((root/"host/lifecycles/contracts.json").read_bytes())["contracts"]
result={"formatVersion":1,"inventorySha256":hashlib.sha256(raw).hexdigest(),
        "meaning":"A host contract link names an obligation. Application conformance remains with its owner.","applications":[]}
for app in inventory["applications"]:
    features=[]
    for feature in app["features"]:
        missing=set(feature["hostWitnesses"])-set(contracts)
        if missing:raise SystemExit(f'{feature["id"]}: unassigned host witnesses {missing}')
        features.append(dict(id=feature["id"],contracts=feature["hostWitnesses"],
              operations=[x["id"] for x in feature["operations"]],
              owner="application-study",conformance="requires-per-application-evidence"))
    result["applications"].append(dict(id=app["id"],features=features))
content=json.dumps(result,indent=2)+"\n"
path=root/"host/lifecycles/features.json"
if args.write:path.write_text(content)
else:
    if not path.is_file():
        raise SystemExit("Missing feature map; inspect the inventory and run map-features.py --write.")
    saved=json.loads(path.read_text())
    # Source observations can advance while the contract projection is stable.
    # Preserve the originally inspected full-source digest as provenance.
    saved.pop("inventorySha256")
    current={k:v for k,v in result.items() if k!="inventorySha256"}
    if saved!=current:
        raise SystemExit("Feature obligations changed; inspect mappings and run map-features.py --write.")
print(sum(len(a["features"]) for a in result["applications"]),"feature obligations assigned across",
      len(result["applications"]),"applications")
