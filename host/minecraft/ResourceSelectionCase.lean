import Lean
import host.minecraft.ResourceSelection
open Lean MinecraftHost.ResourceSelection

private structure PackInput where
  id : Nat
  body : Nat
  metadata : Nat
  blocksBody : Bool
  blocksMetadata : Bool
  deriving FromJson
private structure Row where
  packs : List PackInput
  pathAdmitted : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def render (r : Resource) : String := s!"{r.source}:{r.body}:{r.metadata}"
private def evaluate (r : Row) : Except String String := do
  if r.packs.length > 8 then throw "Outside bounded pack fixture scope."
  if r.packs.any (fun p => p.id == 0 || p.id > 2 || p.body > 3 || p.metadata > 3) then
    throw "Unsupported generated source, byte, or metadata identity."
  let packs := r.packs.map (fun p => Pack.mk p.id p.body p.metadata p.blocksBody p.blocksMetadata)
  let selected := ((single packs r.pathAdmitted).map render).getD "none"
  pure (selected ++ "|" ++ String.intercalate "," ((stack packs r.pathAdmitted).map render))

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one resource-selection input path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported schema."; return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok values => IO.println (toJson values).compress; return 0
