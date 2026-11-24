"""Check portable metadata and links whose targets belong to this repository."""
from pathlib import Path
import re
import subprocess

root=Path(__file__).resolve().parents[1]
paths=subprocess.check_output(["git","ls-files"],cwd=root,text=True).splitlines()
owned={str(Path(p)) for p in paths}
for name in ["README.md","CONTRIBUTING.md","AGENTS.md","SECURITY.md","THIRD_PARTY_NOTICES.md"]:
    text=(root/name).read_text()
    for link in re.findall(r"\]\(([^)]+)\)",text):
        if "://" in link or link.startswith("#"):continue
        target=((root/name).parent/link.split("#")[0]).resolve()
        if not target.is_relative_to(root):continue
        if not target.is_file():raise SystemExit(f"{name}: missing local link {link}")
        if str(target.relative_to(root)) not in owned:
            raise SystemExit(f"{name}: link points to unpublished file {link}")
print("Repository metadata and local navigation checked.")
