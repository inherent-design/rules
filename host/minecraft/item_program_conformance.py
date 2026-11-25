#!/usr/bin/env python3
"""Compare retained original generic-compiler observations with selected models; no JVM."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAPTURE = "item-program-20261125T183811870111Z"
ARTIFACT = "4ae402eaa858eef4141858554a3f9f0867f6e2ddc72e68313668187a3058e5d5"
KINDS = {"minecraft:empty":0,"minecraft:model":1,"minecraft:composite":2,"minecraft:condition":3,"minecraft:select":4,"minecraft:range_dispatch":5}
ALLOWED = [
    {"type"}, {"type","model","tints"}, {"type","models"},
    {"type","property","predicate","value","component","ignore_default","keybind","fluid","on_true","on_false"},
    {"type","property","component","cases","fallback","block_state_property","ignore_default","ignore_unknown"},
    {"type","property","entries","fallback","target","wobble","normalize","source","period","remaining","scale"},
]
EVENTS = {"compile:tint:study:color":1,"compile:condition:study:condition":2,
          "compile:select:study:pick":3,"compile:range:study:number":5,
          "evaluate:condition":6,"evaluate:select":7,"evaluate:range":8,"evaluate:tint":9}
ERRORS = {"Empty select alternatives":7,"Duplicate decoded resource case":8,
          "Conflicting resource range threshold":12,"Expected finite float: threshold":11,
          "Missing resource field: model":4,"Unsupported resource model type: study:unknown":2,
          "Unsupported minecraft:model field: unselected":3,"Unsupported root field: unselected":1,
          "Expected resource object":9,"Nonfinite hand-swap scale":14,
          "Resource model exceeds tint limit":5,"Resource definition exceeds node/depth limit":13,
          "Resource select exceeds case limit":6,"Resource select exceeds alternative limit":6,
          "Resource range exceeds entry limit":10}


class ProfileError(ValueError):
    """Outside the research projection; never reinterpret as a native refusal."""


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identifier(value):
    if type(value) is not str:
        raise ProfileError("Identifier needs selected string evidence.")
    result = value if ":" in value else "minecraft:" + value
    if len(result) > 512 or not re.fullmatch(r"[a-z0-9_.-]+:[a-z0-9/._-]+", result):
        raise ProfileError("Identifier spelling outside the selected inputs.")
    return result


def f32bits(value):
    if type(value) not in [int,float] or not math.isfinite(value):
        raise ProfileError("Selected finite numeric primitive required.")
    try:
        packed = struct.pack(">f", value)
    except (OverflowError, struct.error):
        return None
    number = struct.unpack(">f", packed)[0]
    return struct.unpack(">I", packed)[0] if math.isfinite(number) else None


def body_identity(value):
    # This cohort's threshold bodies are numeric-free JSON. Do not substitute a
    # convenient serializer for unreviewed Gson numeric equality/coercion.
    if type(value) in [int,float]:
        raise ProfileError("Numeric JSON body equality is outside this cohort.")
    if isinstance(value, dict):
        return ("object", tuple(sorted((k,body_identity(v)) for k,v in value.items())))
    if isinstance(value, list):
        return ("array", tuple(body_identity(v) for v in value))
    if type(value) in [str,bool] or value is None:
        return (type(value).__name__, value)
    raise ProfileError("Unselected JSON equality value.")


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def bindings(request):
    models = {"minecraft:builtin/missing"}
    keys = set()
    bodies = set()
    for spec in request["cases"]:
        keys.update(c["pick"] for c in spec["contexts"])
        for node in walk(spec["input"]):
            if "type" not in node or type(node["type"]) is not str:
                continue
            kind = identifier(node["type"])
            if kind == "minecraft:model" and "model" in node:
                models.add(identifier(node["model"]))
            if kind == "minecraft:select":
                for row in node["cases"]:
                    values = row["when"] if isinstance(row["when"], list) else [row["when"]]
                    if not all(type(value) is str for value in values):
                        raise ProfileError("Only the authored string selector is selected.")
                    keys.update(values)
            if kind == "minecraft:range_dispatch":
                bodies.update(body_identity(row["model"]) for row in node["entries"])
    model_names = ["minecraft:builtin/missing", *sorted(models - {"minecraft:builtin/missing"})]
    key_names = sorted(keys)
    body_names = sorted(bodies, key=repr)
    return dict(models={v:i for i,v in enumerate(model_names)},keys={v:i for i,v in enumerate(key_names)},bodies={v:i for i,v in enumerate(body_names)})


def instruction(kind):
    return dict(kind=kind,fieldsValid=True,hasReference=False,reference=0,tints=0,
        children=[],keys=[],rowFieldsValid=[],fallbackKind=0,fallbackChild=0,
        thresholds=[],bodies=[],flipScale=False,emptyRun=0)


def project(spec, names):
    source = spec["input"]
    root = dict.fromkeys(["scaleOverflow","handAnimation","oversized","swapBits","index","program","contexts"])
    root["badFields"] = not set(source) <= {"model","hand_animation_on_swap","oversized_in_gui","swap_animation_scale"}
    if root["badFields"]:
        return root
    program = []

    def build(node):
        if not isinstance(node, dict) or "type" not in node:
            raise ProfileError("Unselected object/type shape.")
        kind = KINDS.get(identifier(node["type"]), 6)
        result = instruction(kind)
        result["fieldsValid"] = kind == 6 or set(node) <= ALLOWED[kind]
        if kind == 6 or not result["fieldsValid"]:
            program.append(result)
            return len(program)-1
        if kind == 1:
            result["hasReference"] = node.get("model") is not None
            if result["hasReference"]:
                result["reference"] = names["models"][identifier(node["model"])]
            tints = node.get("tints", [])
            if not isinstance(tints, list) or any(tint != {"type":"study:color"} for tint in tints):
                raise ProfileError("Only authored marker-tint factories are selected.")
            result["tints"] = len(tints)
        elif kind == 2:
            children = node["models"]
            if children and all(child == {"type":"minecraft:empty"} for child in children):
                result["emptyRun"] = len(children)
            else:
                result["children"] = [build(child) for child in children]
        elif kind == 3:
            if node["property"] != "study:condition":
                raise ProfileError("Actual game predicates are not this fixture.")
            result["children"] = [build(node[k]) for k in ["on_true","on_false"]]
        elif kind == 4:
            if node["property"] != "study:pick":
                raise ProfileError("Actual game selectors are not this fixture.")
            for row in node["cases"]:
                result["rowFieldsValid"].append(set(row) <= {"model","when"})
                result["children"].append(build(row["model"]))
                values = row["when"] if isinstance(row["when"], list) else [row["when"]]
                result["keys"].append([names["keys"][v] for v in values])
        elif kind == 5:
            if node["property"] != "study:number":
                raise ProfileError("Actual game numeric properties are not this fixture.")
            scale = node.get("scale", 1)
            if type(scale) not in [int,float] or scale not in [1,-1]:
                raise ProfileError("Only exact scale+1/-1 is selected.")
            result["flipScale"] = scale == -1
            for row in node["entries"]:
                bits = f32bits(row["threshold"])
                tag = 4 if bits is None else {0xc1200000:0,0x80000000:1,0:2,0x41200000:3}.get(bits)
                if tag is None:
                    raise ProfileError("Threshold outside selected finite atoms.")
                result["thresholds"].append(tag)
                result["rowFieldsValid"].append(set(row) <= {"model","threshold"})
                result["bodies"].append(names["bodies"][body_identity(row["model"])])
                result["children"].append(build(row["model"]))
        if kind in [4,5] and "fallback" in node:
            result["fallbackKind"] = 1 if node["fallback"] is None else 2
            if result["fallbackKind"] == 2:
                result["fallbackChild"] = build(node["fallback"])
        program.append(result)
        return len(program)-1

    root["index"] = build(source["model"])
    root["program"] = program
    bits = f32bits(source.get("swap_animation_scale", 1))
    root["scaleOverflow"] = bits is None
    root["swapBits"] = bits
    root["handAnimation"] = source.get("hand_animation_on_swap", True)
    root["oversized"] = source.get("oversized_in_gui", False)
    if type(root["handAnimation"]) is not bool or type(root["oversized"]) is not bool:
        raise ProfileError("Root Boolean coercion is not selected.")
    root["contexts"] = []
    for i, context in enumerate(spec["contexts"]):
        if context["number"] not in ["-10.0","-0.0","0.0","10.0","NaN"]:
            raise ProfileError("Unselected callback number.")
        root["contexts"].append(dict(id=i,pick=names["keys"][context["pick"]],condition=context["condition"],
            number={"-10.0":0,"-0.0":1,"0.0":2,"10.0":3,"NaN":4}[context["number"]],color=context["color"]))
    return root


def observe(spec, raw, names):
    assert raw["id"] == spec["id"] and raw["inputSerializationUnchanged"] is True
    events = []
    for value in raw["events"]:
        events.append(100 + names["keys"][value[7:]] if value.startswith("decode:") else EVENTS[value])
    result = dict(error=0,dependencies=[],events=events,handAnimation=None,oversized=None,swapBits=None,contexts=[])
    if raw["status"] == "threw":
        assert "compile" not in raw and "results" not in raw
        assert raw["errorClass"] == "JsonParseException" and raw["message"] in ERRORS
        result["error"] = ERRORS[raw["message"]]
        return result
    assert raw["status"] == raw["compile"] == "returned"
    assert [v["contextId"] for v in raw["results"]] == [c["id"] for c in spec["contexts"]]
    assert type(raw["handAnimation"]) is bool and type(raw["oversizedInGui"]) is bool
    result.update(dependencies=sorted(names["models"][v] for v in raw["dependencies"]),
        handAnimation=raw["handAnimation"],oversized=raw["oversizedInGui"],swapBits=int(raw["swapScaleBits"]))
    for i, value in enumerate(raw["results"]):
        layers = []
        for layer in value["layers"]:
            assert set(layer) == {"model","tints"} and all(type(v) is int for v in layer["tints"])
            layers.append(dict(model=names["models"][layer["model"]],tints=layer["tints"]))
        result["contexts"].append(dict(id=i,layers=layers))
    return result


def packet(rows):
    return dict(schema=1,contract="generic-resource-program-v1",artifact=ARTIFACT,contextContract="authored-values-json-v1",rows=rows)


def lean(data, work, label, batch=False):
    path = work / (label + ".json")
    path.write_text(json.dumps(data) + "\n")
    args = ["--batch",str(path)] if batch else [str(path)]
    return subprocess.run([os.environ.get("LEAN","lean"),"--run",str(HERE / "ItemProgramCase.lean"),*args],
        cwd=ROOT,env=os.environ | {"LEAN_PATH":os.environ.get("LEAN_PATH",str(ROOT / ".build/formal"))},capture_output=True,text=True,timeout=60)


def bend_instruction(node):
    boolean = lambda x: "True{}" if x else "False{}"
    natural = lambda x: str(x) + "n"
    values = lambda xs: "[" + ",".join(natural(x) for x in xs) + "]"
    fields = boolean(node["fieldsValid"])
    fallback = ["M.Absent{}", "M.ExplicitNull{}", "M.Child{" + natural(node["fallbackChild"]) + "}"][node["fallbackKind"]]
    kind = node["kind"]
    if kind == 0:
        return "M.Empty{" + fields + "}"
    if kind == 1:
        return "M.Leaf{" + ",".join([fields,boolean(node["hasReference"]),natural(node["reference"]),natural(node["tints"])]) + "}"
    if kind == 2:
        return "M.Composite{" + ",".join([fields,values(node["children"]),natural(node["emptyRun"])]) + "}"
    if kind == 3:
        children = node["children"] or [0,0]  # unused when fieldsValid is false
        return "M.Condition{" + ",".join([fields,*[natural(x) for x in children]]) + "}"
    if kind == 4:
        cases = ["M.Case{" + ",".join([boolean(f),natural(c),values(k)]) + "}" for f,c,k in zip(node["rowFieldsValid"],node["children"],node["keys"],strict=True)]
        return "M.Select{" + ",".join([fields,"["+",".join(cases)+"]",fallback]) + "}"
    if kind == 5:
        entries = ["M.Entry{" + ",".join([natural(t),boolean(f),natural(b),natural(c)]) + "}" for t,f,b,c in zip(node["thresholds"],node["rowFieldsValid"],node["bodies"],node["children"],strict=True)]
        return "M.Range{" + ",".join([fields,"["+",".join(entries)+"]",boolean(node["flipScale"]),fallback]) + "}"
    assert kind == 6
    return "M.Unsupported{}"


BEND_RENDERER = r'''
type RequestContext is Data:
  RC{id: Nat,color: Nat,value: M.IPContext}
def bshow(value: Bool) -> String:
  Bool.pick(String,value,"true","false")
def ntail(xs: List<&2,Nat>) -> String:
  match xs:
    case Nil{}: ""
    case Con{head,tail}: "," ++ Nat.show(head) ++ ntail(tail)
def nshow(xs: List<&2,Nat>) -> String:
  match xs:
    case Nil{}: "[]"
    case Con{head,tail}: "[" ++ Nat.show(head) ++ ntail(tail) ++ "]"
def repeat(count: Nat,+value: Nat) -> List<&2,Nat>:
  match count:
    case 0n: Nil{}
    case 1n+remaining: Con{value,repeat(remaining,value)}
def tint_count(layers: List<&2,M.IPLayer>) -> Nat:
  match layers:
    case Nil{}: 0n
    case Con{M.Layer{reference,tints},tail}: Nat.add(tints,tint_count(tail))
def ltail(layers: List<&2,M.IPLayer>,+color: Nat) -> String:
  match layers:
    case Nil{}: ""
    case Con{M.Layer{reference,tints},tail}: ",{" ++ "\"model\":" ++ Nat.show(reference) ++ ",\"tints\":" ++ nshow(repeat(tints,color)) ++ "}" ++ ltail(tail,color)
def lshow(layers: List<&2,M.IPLayer>,+color: Nat) -> String:
  match layers:
    case Nil{}: "[]"
    case Con{M.Layer{reference,tints},tail}: "[{" ++ "\"model\":" ++ Nat.show(reference) ++ ",\"tints\":" ++ nshow(repeat(tints,color)) ++ "}" ++ ltail(tail,color) ++ "]"
def eval_show(value: M.IPEvaluation,id: Nat,color: Nat) -> String:
  match value:
    case M.Evaluation{valid,+layers,events}:
      "{\"id\":" ++ Nat.show(id) ++ ",\"valid\":" ++ bshow(valid) ++ ",\"layers\":" ++ lshow(layers,color) ++ ",\"events\":" ++ nshow(List.append(&2,Nat,events,repeat(tint_count(layers),9n))) ++ "}"
def one_context(program: List<&2,M.IPInstruction>,index: Nat,context: RequestContext) -> String:
  match context:
    case RC{id,color,value}: eval_show(M.ip_eval(program,index,value),id,color)
def contexts_tail(contexts: List<&2,RequestContext>,+program: List<&2,M.IPInstruction>,+index: Nat) -> String:
  match contexts:
    case Nil{}: ""
    case Con{head,tail}: "," ++ one_context(program,index,head) ++ contexts_tail(tail,program,index)
def contexts_show(contexts: List<&2,RequestContext>,+program: List<&2,M.IPInstruction>,+index: Nat) -> String:
  match contexts:
    case Nil{}: "[]"
    case Con{head,tail}: "[" ++ one_context(program,index,head) ++ contexts_tail(tail,program,index) ++ "]"
def row_state(program: List<&2,M.IPInstruction>,index: Nat,hand: Bool,oversized: Bool,bits: String,contexts: List<&2,RequestContext>,state: M.IPState) -> String:
  match state:
    case M.State{+error,used,dependencies,events}:
      +ok = Nat.is_eq(error,0n)
      "{\"error\":" ++ Nat.show(error) ++ ",\"dependencies\":" ++ Bool.pick(String,ok,nshow(dependencies),"[]") ++ ",\"events\":" ++ nshow(List.reverse(&2,Nat,events)) ++ ",\"handAnimation\":" ++ Bool.pick(String,ok,bshow(hand),"null") ++ ",\"oversized\":" ++ Bool.pick(String,ok,bshow(oversized),"null") ++ ",\"swapBits\":" ++ Bool.pick(String,ok,bits,"null") ++ ",\"contexts\":" ++ Bool.pick(String,ok,contexts_show(contexts,program,index),"[]") ++ "}"
def row_show(+program: List<&2,M.IPInstruction>,+index: Nat,bad: Bool,overflow: Bool,hand: Bool,oversized: Bool,bits: String,contexts: List<&2,RequestContext>) -> String:
  row_state(program,index,hand,oversized,bits,contexts,M.ip_root(bad,overflow,program,index))
'''


def bend(rows, work, label):
    boolean = lambda x: "True{}" if x else "False{}"
    atoms = ["NegativeTen", "NegativeZero", "PositiveZero", "PositiveTen", "NotANumber"]
    definitions = []
    calls = []
    for i, row in enumerate(rows):
        program = row["program"] or []
        definitions.append("def program"+str(i)+"() -> List<&2,M.IPInstruction>:\n  ["+",".join(bend_instruction(x) for x in program)+"]\n")
        contexts = []
        for c in row["contexts"] or []:
            value = "M.Context{" + ",".join([str(c["pick"])+"n",boolean(c["condition"]),"F."+atoms[c["number"]]+"{}",str(c["color"])+"n"]) + "}"
            contexts.append("RC{" + str(c["id"]) + "n," + str(c["color"]) + "n," + value + "}")
        args = ["program"+str(i)+"()",str(row["index"] or 0)+"n",boolean(row["badFields"]),boolean(row["scaleOverflow"]),boolean(row["handAnimation"]),boolean(row["oversized"]),json.dumps(str(row["swapBits"] or 0)),"["+",".join(contexts)+"]"]
        calls.append("row_show(" + ",".join(args) + ")")
    source = "import Base\nimport ../../../host/minecraft/ItemProgram.bend as M\nimport ../../../host/java/FloatOrder.bend as F\n" + BEND_RENDERER + "\n".join(definitions)
    source += '\ndef main() -> IO(Unit):\n  IO.write("[" ++ ' + ' ++ "," ++ '.join(calls) + ' ++ "]")\n'
    path = work / (label + ".bend")
    path.write_text(source)
    result = subprocess.run([os.environ.get("BEND","bend"),str(path)],cwd=ROOT,
        env=os.environ | {"BEND_NO_TELEMETRY":"1"},capture_output=True,text=True,timeout=60)
    (work / (label + ".bend.stdout")).write_text(result.stdout)
    (work / (label + ".bend.stderr")).write_text(result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    outputs = json.loads(result.stdout)
    for row in outputs:
        row["dependencies"].sort()
        for context in row["contexts"]:
            assert context.pop("valid") is True
            row["events"] += context.pop("events")
    return outputs


def integrity(cap):
    receipt = json.loads((cap / "receipt.json").read_text())
    assert receipt["artifactSha256"] == ARTIFACT
    assert receipt["selectedClassSha256"]["design/inherent/skyweavecompat/client/model/ResourceDefinitions.class"] == "7130da45e369de613ccbeeefdb928bdd25ff3b4305618806f6c7624f9c3391da"
    for name, digest in receipt["sourcesSha256"].items():
        assert sha(cap / name) == digest
    for name, key in [("request.json","requestSha256"),("observed.json","observed.jsonSha256")]:
        assert sha(cap / name) == receipt[key]
    for stem, command in zip(["compile","execute"], receipt["commands"], strict=True):
        assert command["exitCode"] == 0 and command["ownedGroupAbsent"] and not command["timedOut"]
        for channel in ["stdout","stderr"]:
            assert sha(cap / (stem + "." + channel)) == command[channel + "Sha256"]
    return receipt


def equal(actual, wanted, specs):
    assert len(actual) == len(wanted) == len(specs)
    for a, b, spec in zip(actual, wanted, specs, strict=True):
        assert a == b, (spec["id"], [key for key in set(a)|set(b) if a.get(key) != b.get(key)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private",action="store_true",help="Use original owner-local capture rather than the exported corpus.")
    args = parser.parse_args()
    cap = (ROOT / ".build/minecraft" if args.private else HERE / "evidence") / CAPTURE
    receipt = integrity(cap)
    request = json.loads((cap / "request.json").read_text())
    raw = json.loads((cap / "observed.json").read_text())
    assert request["schema"] == raw["schema"] == 1
    assert receipt["compilerRequests"] == len(request["cases"]) == len(raw["cases"]) == 36
    names = bindings(request)
    rows = [project(spec,names) for spec in request["cases"]]
    wanted = [observe(spec,value,names) for spec,value in zip(request["cases"],raw["cases"],strict=True)]
    work = ROOT / ".build/minecraft/item-program-replay"
    work.mkdir(parents=True,exist_ok=True)
    frames = {role:[dict(id=i,value=value) for value,i in sorted(table.items(),key=lambda pair:pair[1])] for role,table in names.items()}
    (work / "identity-frames.json").write_text(json.dumps(frames,indent=2)+"\n")
    result = lean(packet(rows),work,"plan")
    (work / "lean.stdout").write_text(result.stdout)
    (work / "lean.stderr").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    predicted = json.loads(result.stdout)
    equal(predicted,wanted,request["cases"])
    equal(bend(rows,work,"plan"),wanted,request["cases"])

    index = {spec["id"]:i for i,spec in enumerate(request["cases"])}
    good = rows[index["model-default-namespace"]]
    invalid = [packet([good]) | dict(schema=2), packet([good]) | dict(contract="full-renderer"),
        packet([good]) | dict(artifact="unselected"),packet([good]) | dict(contextContract="native-game-values"),packet([good]*65)]
    for change in [dict(badFields=None),dict(badFields=1),dict(program=None),dict(swapBits=2139095040)]:
        invalid.append(packet([copy.deepcopy(good)|change]))
    for field,value in [("kind",7),("reference",256),("hasReference",1),("emptyRun",1)]:
        changed = copy.deepcopy(good); changed["program"][0][field] = value; invalid.append(packet([changed]))
    changed = copy.deepcopy(good); changed["contexts"][0]["number"] = 5; invalid.append(packet([changed]))
    changed = copy.deepcopy(good); changed["contexts"][0]["color"] = 256; invalid.append(packet([changed]))
    changed = copy.deepcopy(good); changed["contexts"] = [changed["contexts"][0]]*2; invalid.append(packet([changed]))
    for kind in ["cyclic","shared","keys"]:
        changed = copy.deepcopy(rows[index["select-list-and-missing"]])
        node = changed["program"][-1]
        if kind == "cyclic":node["children"][0] = changed["index"]
        elif kind == "shared":
            node["children"] *= 2; node["keys"] *= 2; node["rowFieldsValid"] *= 2
        else:node["keys"][0][0] = 4097
        invalid.append(packet([changed]))
    changed = copy.deepcopy(rows[index["range-unsorted"]]); changed["program"][-1]["thresholds"].pop(); invalid.append(packet([changed]))
    changed = copy.deepcopy(rows[index["select-list-and-missing"]]); changed["program"][-1]["fallbackKind"] = 3; invalid.append(packet([changed]))
    negative = lean(invalid,work,"decoder-refusals",batch=True)
    assert negative.returncode == 0 and json.loads(negative.stdout) == [2]*len(invalid), negative.stdout+negative.stderr
    # Keep one direct CLI refusal, in addition to independently decoding each batch packet.
    direct = lean(invalid[0],work,"direct-cli-refusal")
    assert direct.returncode == 2

    unknown = [dict.fromkeys(good)|dict(badFields=True)]
    missing = copy.deepcopy(rows[index["missing-model-reference"]])
    for field in ["scaleOverflow","handAnimation","oversized","swapBits","contexts"]:missing[field] = None
    late = copy.deepcopy(rows[index["late-root-scale-overflow"]])
    for field in ["handAnimation","oversized","swapBits","contexts"]:late[field] = None
    unknown += [missing,late]
    accepted = lean(packet(unknown),work,"unused-unknowns")
    assert accepted.returncode == 0, accepted.stderr
    unneeded = json.loads(accepted.stdout)
    assert [v["error"] for v in unneeded] == [1,4,14]
    assert unneeded == bend(unknown,work,"unused-unknowns")

    changed_rows = []
    original_outcomes = []
    premise_labels = []
    for identity,kind in [("range-signed-zero","threshold"),("select-duplicate-in-one-case","key"),
                          ("late-root-scale-overflow","root-scale"),("composite-children-4096","budget"),
                          ("range-scaled","flip"),("identifier-lexical-traversal","reference")]:
        changed = copy.deepcopy(rows[index[identity]]); node = changed["program"][-1]
        if kind == "threshold":node["thresholds"][0] = 2
        elif kind == "key":node["keys"][0][-1] = names["keys"]["missing"]
        elif kind == "root-scale":changed["scaleOverflow"] = False;changed["swapBits"] = 1065353216
        elif kind == "budget":node["emptyRun"] = 4095
        elif kind == "flip":node["flipScale"] = False
        else:node["reference"] = 0
        changed_rows.append(changed);original_outcomes.append(wanted[index[identity]]);premise_labels.append(identity+"/"+kind)
    result = lean(packet(changed_rows),work,"changed-premises")
    assert result.returncode == 0, result.stderr
    changed_predictions = json.loads(result.stdout)
    assert changed_predictions == bend(changed_rows,work,"changed-premises")
    assert all(a != b for a,b in zip(changed_predictions,original_outcomes,strict=True))

    observations = []
    tests = [("empty","preservation"),("late-root-scale-overflow","known-reason"),
             ("condition","dependencies"),("select-empty-cases","fallback"),
             ("composite-order-and-duplicate","order"),("range-signed-zero","negative-zero"),
             ("range-signed-zero","nan"),("late-root-scale-overflow","callback"),
             ("model-with-tints","tint"),("empty","root-flag"),("empty","context-id"),
             ("late-root-scale-overflow","exception-class")]
    for identity,kind in tests:
        i = index[identity]; changed = copy.deepcopy(raw["cases"][i])
        if kind == "preservation":changed["inputSerializationUnchanged"] = False
        elif kind == "known-reason":changed["message"] = "Resource model exceeds tint limit"
        elif kind == "dependencies":changed["dependencies"].pop()
        elif kind == "fallback":changed["results"][0]["layers"] = []
        elif kind == "order":
            # The retained a,b,a list is palindromic; swap distinct neighbors.
            layers = changed["results"][0]["layers"]
            layers[0],layers[1] = layers[1],layers[0]
        elif kind == "negative-zero":changed["results"][0]["layers"][0]["model"] = "study:b"
        elif kind == "nan":changed["results"][-1]["layers"][0]["model"] = "study:a"
        elif kind == "callback":changed["events"] = []
        elif kind == "tint":changed["results"][0]["layers"][0]["tints"][0] = 99
        elif kind == "root-flag":changed["handAnimation"] = False
        elif kind == "context-id":changed["results"][0]["contextId"] = "unrecorded"
        else:changed["errorClass"] = "IllegalArgumentException"
        try:
            altered = observe(request["cases"][i],changed,names)
        except (AssertionError,KeyError):
            observations.append(dict(case=identity,kind=kind,rejection="observation-shape/profile"))
        else:
            assert altered != predicted[i], "Changed native observation admitted: "+identity+"/"+kind
            observations.append(dict(case=identity,kind=kind,rejection="model-outcome-difference"))
    basis = [cap/"receipt.json",cap/"request.json",cap/"observed.json",work/"identity-frames.json",
        *[HERE/n for n in ["ItemProgram.lean","ItemProgramCase.lean","ItemProgram.bend","item_program_conformance.py"]],
        *[HERE.parent/"java"/n for n in ["FloatOrder.lean","FloatOrder.bend"]]]
    report = dict(schema=1,status="passed-retained-original-generic-program",privateCapture=args.private,
        compilerRequests=len(rows),returnedRoots=sum(v["error"]==0 for v in wanted),contexts=sum(len(v["contexts"])for v in wanted),
        layers=sum(len(c["layers"])for v in wanted for c in v["contexts"]),programLeanLaws=21,programBendLaws=8,
        floatLeanLaws=15,floatBendLaws=8,decoderRefusals=len(invalid),directCliRefusals=1,unusedUnknownExamples=3,
        changedPremiseControls=premise_labels,changedObservationControls=observations,
        basisSha256={str(p.relative_to(ROOT)):sha(p)for p in basis},limits=[
            "Original generic compiler/layer consumer with authored Values/context;not actual NativeResourceValues,game,loader,publication or renderer.",
            "Postorder tree projection with role-specific opaque model/key/body IDs;shared projection and body-identity fidelity are premises,not a parser/translation proof.",
            "Selected threshold-body equality admits numeric-free JSON only;numeric Gson equality is held,not guessed.",
            "Generated raw requests are pinned;alternate numeric token spellings,duplicate JSON members and a general Gson parser correspondence remain outside this projection.",
            "Verified homogeneous empty runs preserve the selected node-count/no-callback/no-layer contract;not a general compression or optimization proof.",
            "Selected float atoms -10,-0,+0,+10,NaN and exact scales+1/-1;not full float arithmetic,NaN payload identity or arbitrary callbacks.",
            "Research tree/step/marker bounds are separate from product limits;decoder refusal is not a native product failure.",
            "Batched negative controls independently call the same research decoder;known native refusal payloads remain accepted research inputs.",
            "Event lists are authored callback logs;error placeholders are not empty allocation/physical state or rollback evidence."])
    (work / "conformance.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items()if k not in ["basisSha256","limits","changedObservationControls"]}))


if __name__ == "__main__":
    main()
