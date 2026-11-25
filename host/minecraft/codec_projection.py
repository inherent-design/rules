"""Restricted JSON-to-domain adapter, independent of observed acceptance.

Reject unsupported shapes instead of pretending to implement general DFU/Gson,
component registries, floating point, filesystem admission, or model baking.
"""
import math
import re

FAMILIES = {"packs.metadata", "packs.identifiers", "textures.gui", "textures.animation",
            "textures.metadata", "models.geometry", "equipment.definitions", "shaders.post_effects"}


def nat(n):
    if type(n) is not int or not 0 <= n < 1000000:
        raise ValueError("Outside bounded natural fixture domain")
    return n


def boolean_shape(x):
    if x is None: return 0
    if type(x) is bool: return 2 if x else 1
    if type(x) is int: return 3
    if type(x) is str: return 5 if x.lower() == "true" else 4
    raise ValueError("Unsupported boolean JSON shape")


def project(c, version):
    f, x = c["family"], c["input"]
    if f not in FAMILIES: return None
    bits, numbers = [], []
    if f == "packs.metadata":
        if "description" in x and type(x["description"]) is not str: raise ValueError("Component text outside scalar fixture")
        n = x.get("pack_format")
        if type(n) in (int,float) and not (-2**31 < n < 2**31): raise ValueError("Integer narrowing outside fixture")
        r = x.get("supported_formats")
        valid = (type(r) is int or (type(r) is list and len(r)==2 and all(type(n) is int for n in r) and r[0] <= r[1]))
        bits = ["description" in x, type(n) in (int,float), "supported_formats" in x, valid]
        kind = "metadata"
    elif f == "packs.identifiers":
        if type(x) is not str: raise ValueError("Non-string resource ID outside fixture")
        namespace, path = x.split(":",1) if ":" in x else ("minecraft",x)
        namespace = namespace or "minecraft"
        bits = [re.fullmatch(r"[a-z0-9_.-]*",namespace) is not None, re.fullmatch(r"[a-z0-9/._-]*",path) is not None]
        kind = "identifier"
    elif f == "textures.gui":
        k = {"stretch":0,"tile":1,"nine_slice":2}.get(x["type"],3)
        b = x.get("border",0); scalar = type(b) is int
        sides = [b]*4 if scalar else [b[n] for n in ["left","top","right","bottom"]]
        numbers = [k,nat(x.get("width",0)),nat(x.get("height",0)),*[nat(n) for n in sides]]
        bits,kind = [scalar],"gui"
    elif f == "textures.animation":
        for key in ["width","height","frametime"]:
            if key in x and type(x[key]) is not int: raise ValueError("Noninteger animation outside fixture")
        frames = x.get("frames",[])
        if type(frames) is not list: raise ValueError("Non-list frames outside fixture")
        if any(type(n) not in (int,dict) for n in frames): raise ValueError("Other frame shape outside fixture")
        primitive = [n for n in frames if type(n) is int]
        objects = [n for n in frames if type(n) is dict]
        if any(set(n)-{"index","time"} or type(n.get("index")) is not int or type(n.get("time",1)) is not int for n in objects): raise ValueError("Other frame object outside fixture")
        bits = [all(x.get(n,1)>0 for n in ["width","height"]),
                x.get("frametime",1)>0 and all(n.get("time",1)>0 for n in objects),
                any(n<0 for n in primitive),any(n["index"]<0 for n in objects)]
        kind = "animation"
    elif f == "textures.metadata":
        if any(k in x and x[k] is None for k in ("blur","clamp")): raise ValueError("Explicit null not modeled")
        numbers,kind = [boolean_shape(x.get("blur")),boolean_shape(x.get("clamp"))],"texture"
    elif f == "models.geometry":
        elements = x.get("elements",[])
        if len(elements)>1: raise ValueError("Only empty/single-element projection modeled")
        negative,positive,angle,shape,axis = 0,0,0,True,True
        if elements:
            e = elements[0]
            points = [v for key in ["from","to"] for v in e[key]]
            if len(points)!=6 or any(type(v) is not int for v in points): raise ValueError("Only integer extent triples modeled")
            negative,positive = max([-v for v in points if v<0]+[0]),max([v for v in points if v>0]+[0])
            if e.get("faces")!={"north":{"texture":"#fixture"}}: raise ValueError("Other face structure not modeled")
            r = e.get("rotation")
            if r is not None:
                if r["origin"]!=[8,8,8]: raise ValueError("Other rotation origin outside fixture")
                axis = type(r.get("axis")) is str and r["axis"].lower() in ["x","y","z"]
                a = r.get("angle",0)
                if type(a) not in (int,float) or not math.isfinite(a) or (abs(a)*2)%1: raise ValueError("Other float angle outside fixture")
                angle = nat(int(abs(a)*2))
            if set(e)-{"from","to","faces","rotation","shade_direction_override"}: raise ValueError("Other geometry fields outside fixture")
        numbers,bits,kind = [nat(negative),nat(positive),angle],[shape,axis],"geometry"
    elif f == "equipment.definitions":
        groups = x["layers"]
        if any(type(v) is not list for v in groups.values()): raise ValueError("Layer list required")
        if any(set(v)!={"texture"} or type(v["texture"]) is not str for vs in groups.values() for v in vs): raise ValueError("Other layer schema outside fixture")
        bits = [all(k in ["humanoid","humanoid_leggings","wings","wolf_body","horse_body","llama_body"] for k in groups)]
        numbers,kind = [len(groups), min([len(v) for v in groups.values()]+[100000])],"equipment"
    else:
        if x.get("passes",[]) or len(x.get("targets",{}))>1: raise ValueError("Post passes/multiple targets outside fixture")
        target = next(iter(x.get("targets",{}).values()),{})
        if not target: numbers = [0,0]
        elif set(target)=={"width","height"}: numbers = [nat(target["width"]),nat(target["height"])]
        else: raise ValueError("Other target object outside fixture")
        bits,kind = [bool(x.get("targets",{}))],"post"
    return dict(kind=kind, successor=version=="1.21.5", bits=bits, numbers=numbers)
