import Lean
import host.minecraft.ArtifactVersions
open Lean MinecraftHost.ArtifactVersions

private structure Row where
  edition : String
  declaredJava : Nat
  availableJava : Nat
  resource : Nat
  data : Nat
  resourceMinor : Nat
  dataMinor : Nat
  encoding : String
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson

private def evaluate (r : Row) : Except String String := do
  if r.edition != "java" then throw "Different edition needs its own metadata contract."
  if r.declaredJava == 0 || r.availableJava == 0 then throw "Missing runtime requirement or available major."
  let (resource,data) ← match r.encoding with
    | "legacy-integer" =>
      if r.resourceMinor != 0 || r.dataMinor != 0 then throw "Mixed legacy/pair encoding."
      pure (normalize (.legacy r.resource),normalize (.legacy r.data))
    | "major-minor-fields" => pure (normalize (.majorMinor r.resource r.resourceMinor),normalize (.majorMinor r.data r.dataMinor))
    | _ => throw "Unsupported artifact metadata encoding."
  pure s!"{resource.major}.{resource.minor}/{data.major}.{data.minor}/{if declaredJavaSatisfied r.declaredJava r.availableJava then 1 else 0}"

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one artifact-metadata input path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported schema."; return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok values => IO.println (toJson values).compress; return 0
