#!/usr/bin/env python3
"""Pure retained codec comparison. Never downloads or starts Minecraft."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess

from codec_projection import project

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def expected(row, observation, aliases):
    ok = observation["accepted"]
    aux = 0
    if ok:
        fields = observation.get("fields", {})
        if row["kind"] == "metadata": aux = int(fields["supportedFormats"]["present"])
        elif row["kind"] == "texture": aux = int(fields["blur"]) + 2*int(fields["clamp"])
        elif row["kind"] == "post":
            values = fields["internalTargets"]["values"]
            if values:
                assert len(values) == 1
                name = values[0]["nativeClass"]
                full = "net.minecraft.client.renderer.PostChainConfig$FullScreenTarget"
                fixed = "net.minecraft.client.renderer.PostChainConfig$FixedSizedTarget"
                assert name in [aliases[full], aliases[fixed]]
                aux = 1 if name == aliases[full] else 2
    return f"{int(ok)}/{aux}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    work = ROOT / ".build/minecraft/replay"
    work.mkdir(parents=True, exist_ok=True)
    sources = json.loads((HERE / "codec-selections.json").read_text())
    aliases = sources["selectedRuntimeTypeLocators"]
    rows, answers, refs, retained = [], [], [], []
    basis_paths = [HERE / name for name in ["Decoding.lean","Decoding.bend","DecodingCase.lean",
        "codec_projection.py","codec_conformance.py","codec-selections.json"]]
    for capture in sorted((HERE / "evidence").glob("codecs-*")):
        receipt = json.loads((capture / "receipt.json").read_text())
        assert sha(capture / "observed.json") == receipt["observedSha256"]
        assert sha(capture / "cases.json") == receipt["publicCasesSha256"]
        assert receipt["observerErrors"] == 0
        for name, digest in receipt["sourceSha256"].items(): assert sha(capture / name) == digest
        assert all(r["exitCode"]==0 and r["ownedGroupAbsent"] and not r["timedOut"] for r in receipt["commands"])
        cases = json.loads((capture / "cases.json").read_text())
        observations = json.loads((capture / "observed.json").read_text())
        assert [x["id"] for x in cases] == [x["id"] for x in observations]
        assert len(cases) == receipt["cases"]
        retained.append(dict(capture=capture.name, cases=len(cases)))
        basis_paths += sorted(p for p in capture.iterdir() if p.is_file())
        for c,o in zip(cases,observations):
            assert not o.get("observerError",False)
            r = project(c, receipt["minecraft"])
            if r is None: continue
            rows.append(r); answers.append(expected(r,o,aliases)); refs.append(dict(capture=capture.name,case=c["id"]))
    payload = dict(schema=1,cases=rows)
    data = work / "inputs.json"
    data.write_text(json.dumps(payload,indent=2)+"\n")
    env = dict(os.environ, LEAN_PATH=str(ROOT/".build/formal"), BEND_NO_TELEMETRY="1")
    lean,bend = os.environ.get("LEAN","lean"),os.environ.get("BEND","bend")

    def lean_run(p):
        return subprocess.run([lean,"--run",str(HERE/"DecodingCase.lean"),str(p)],cwd=ROOT,env=env,capture_output=True,text=True)

    result = lean_run(data)
    assert result.returncode == 0, result.stdout+result.stderr
    lean_actual = json.loads(result.stdout)
    assert lean_actual == answers, [(refs[i],a,b) for i,(a,b) in enumerate(zip(lean_actual,answers)) if a!=b]
    bit = lambda b: "True{}" if b else "False{}"
    number = lambda n: str(n)+"n"
    calls = []
    for r in rows:
        b,n,v = [bit(x) for x in r["bits"]],[number(x) for x in r["numbers"]],bit(r["successor"])
        kind = r["kind"]; aux = "0n"
        if kind == "metadata":
            ok = "M.metadata("+",".join(b[:2])+")"
            aux = "Bool.pick(Nat,M.optional_range("+",".join(b[2:])+"),1n,0n)"
        elif kind == "identifier": ok = "M.identifier("+",".join(b)+")"
        elif kind == "gui": ok = "M.gui("+",".join(n+b)+")"
        elif kind == "animation": ok = "M.animation("+",".join([v]+b)+")"
        elif kind == "texture":
            ok = "M.texture("+",".join([v]+n)+")"
            aux = "M.texture_value("+",".join(n)+")"
        elif kind == "geometry": ok = "M.geometry("+",".join(n+b)+")"
        elif kind == "equipment": ok = "M.equipment("+",".join(b+n)+")"
        elif kind == "post":
            ok = "True{}"
            aux = "Bool.pick(Nat,"+b[0]+",M.post_target("+",".join(n)+"),0n)"
        else: raise AssertionError(kind)
        calls.append("render("+ok+","+aux+") ++ \"\\n\"")
    runner = work / "CodecCase.bend"
    runner.write_text('import Base\nimport ../../../host/minecraft/Decoding.bend as M\n\ndef render(+ok: Bool, aux: Nat) -> String:\n  Bool.pick(String,ok,"1","0") ++ "/" ++ Nat.show(Bool.pick(Nat,ok,aux,0n))\n\ndef main() -> IO(Unit):\n  IO.write('+" ++ ".join(calls)+')\n')
    result = subprocess.run([bend,str(runner)],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode == 0,result.stdout+result.stderr
    bend_actual = result.stdout.splitlines()
    assert bend_actual == answers

    negative_payloads = [dict(schema=2,cases=rows),dict(schema=1,cases=[dict(rows[0],kind="unknown")]),
        dict(schema=1,cases=[dict(rows[0],bits=[])]),dict(schema=1,cases=[dict(rows[0],numbers=[-1])]),
        dict(schema=1,cases=[dict(kind="texture",successor=True,bits=[],numbers=[6,0])]),
        dict(schema=1,cases=[dict(rows[0],successor="true")])]
    for i,p in enumerate(negative_payloads):
        path = work / f"negative-{i}.json";path.write_text(json.dumps(p))
        assert lean_run(path).returncode == 2
    for i in [0,1,10,20,40,len(answers)-1]:
        wrong = list(answers);wrong[i] = ("0" if wrong[i][0]=="1" else "1")+wrong[i][1:]
        assert lean_actual != wrong and bend_actual != wrong
    # Measured auxiliary fields matter independently of acceptance.
    for kind in ["metadata","texture","post"]:
        i = next(i for i,r in enumerate(rows) if r["kind"]==kind and answers[i].startswith("1/"))
        wrong = list(answers);wrong[i] = "1/999"
        assert lean_actual != wrong and bend_actual != wrong
    unsupported = [
        dict(family="models.geometry",input={"elements":[{},{}]}),
        dict(family="textures.metadata",input={"blur":None}),
        dict(family="textures.animation",input={"frames":[None]}),
        dict(family="shaders.post_effects",input={"passes":[{}]}),
        dict(family="equipment.definitions",input={"layers":{"humanoid":[{}]}}),
        dict(family="packs.identifiers",input=42),
    ]
    for c in unsupported:
        try: project(c,"1.21.5")
        except ValueError: pass
        else: raise AssertionError("Unsupported adapter input silently admitted")
    report = dict(schema=1,status="passed",retained=retained,comparisons=len(rows),references=refs,
        modeledFamilies=sorted(set(c["family"] for cap in (HERE/"evidence").glob("codecs-*") for c in json.loads((cap/"cases.json").read_text()) if project(c,json.loads((cap/"receipt.json").read_text())["minecraft"]) is not None)),
        decoderRefusals=len(negative_payloads),adapterRefusals=len(unsupported),changedObservationControls=9,
        projectedInputSha256=sha(data),basisSha256={str(p.relative_to(ROOT)):sha(p) for p in basis_paths},
        limits=["96 selected acceptance/projection cases, not a general Minecraft JSON codec or consumer proof.",
            "Lexical/type/finite fixture projection is authored Python; Lean and Bend share these premises and independently evaluate domain decisions.",
            "Other retained cases are native observations only. No game/render/network run occurs in this comparison."])
    assert len(rows)==96 and sum(r["cases"] for r in retained)==169
    if args.output:
        args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ["status","comparisons","decoderRefusals","adapterRefusals","changedObservationControls"]}))


if __name__ == "__main__": main()
