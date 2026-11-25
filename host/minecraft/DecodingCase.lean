import Lean
import host.minecraft.Decoding
open Lean MinecraftHost.Decoding

private structure Row where
  kind : String
  successor : Bool
  bits : List Bool
  numbers : List Nat
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def evaluate (r : Row) : Except String String := do
  let (ok, aux) ← match r.kind, r.bits, r.numbers with
    | "metadata", [d,n,p,v], [] => pure (metadata d n, if optionalRange p v then 1 else 0)
    | "identifier", [n,p], [] => pure (identifier n p, 0)
    | "gui", [s], [k,w,h,l,t,rr,b] => pure (gui k w h l t rr b s, 0)
    | "animation", [d,t,p,o], [] => pure (animation r.successor d t p o, 0)
    | "texture", [], [b,c] =>
      if b > 5 || c > 5 then throw "Unsupported boolean shape."
      pure (texture r.successor b c, textureValue b c)
    | "geometry", [s,a], [n,p,angle] => pure (geometry n p angle s a, 0)
    | "equipment", [k], [g,m] => pure (equipment k g m, 0)
    | "post", [present], [w,h] => pure (true, if present then postTarget w h else 0)
    | _ , _, _ => throw "Unsupported domain or input arity."
  pure s!"{if ok then 1 else 0}/{if ok then aux else 0}"

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one decoded input path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported schema."; return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok values => IO.println (toJson values).compress; return 0
