"""Typecheck tracked Lean modules and recheck tracked Bend laws, with no application execution."""
import os
from pathlib import Path
import re
import subprocess

root=Path(__file__).resolve().parents[1]
os.chdir(root)
files=subprocess.check_output(["git","ls-files","--","*.lean","*.bend"],text=True).splitlines()
lean=os.environ.get("LEAN","lean")
bend=os.environ.get("BEND","bend")
out=root/".build/formal"
out.mkdir(parents=True,exist_ok=True)
env={**os.environ,"LEAN_PATH":str(out),"BEND_NO_TELEMETRY":"1"}
modules={str(Path(p).with_suffix("")).replace("/","."):p for p in files if p.endswith(".lean")}
done=set()
active=set()
def check(name):
    if name in done:return
    if name in active:raise ValueError(f"Local import cycle at {name}")
    active.add(name)
    path=modules[name]
    for line in Path(path).read_text().splitlines():
        match=re.match(r"^import (.+)",line)
        if match:
            for dependency in match[1].split():
                dependency=dependency.replace("«","").replace("»","")
                if dependency in modules:check(dependency)
    target=out/Path(path).with_suffix(".olean")
    target.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([lean,"-DwarningAsError=true","-o",str(target),path],env=env,check=True)
    active.remove(name)
    done.add(name)
for name in modules:check(name)
for path in files:
    if path.endswith(".bend"):
        result=subprocess.run([bend,path,"--verdict"],env=env,text=True,capture_output=True)
        if result.returncode or "ALL PROOFS CHECK" not in result.stdout or "SOME PROOFS FAIL" in result.stdout+result.stderr:
            raise RuntimeError(f"{path}: {result.stdout}{result.stderr}")
        print(path+": kernel checked")
print(f"Checked {len(done)} Lean modules and {sum(p.endswith('.bend') for p in files)} Bend files.")
