import Lean
import host.minecraft.bedrock.SchemaContracts
open Lean MinecraftHost.Bedrock.SchemaContracts

private structure ProfileRow where
  conditionDeclared : Bool
  opaqueDeclared : Bool
  opaqueDefaultAnnotation : Bool
  deriving FromJson
private structure RuleRow where
  object : Bool
  direction : Bool
  geometry : Bool
  bone : Bool
  cube : Bool
  face : Bool
  condition : Nat
  opaqueState : Nat
  deriving FromJson
private structure CullingRow where
  object : Bool
  description : Bool
  identifier : Bool
  rulesArray : Bool
  rules : List RuleRow
  deriving FromJson
private structure BiomeRow where
  object : Bool
  requiredString : Bool
  deriving FromJson
private structure Row where
  kind : String
  profile : ProfileRow
  input : Json
  deriving FromJson
private structure Envelope where
  schema : Nat
  edition : String
  oracle : String
  cases : List Row
  deriving FromJson

private def evaluate (row : Row) : Except String Bool := do
  if row.kind == "biome-identifier" then
    let r ← fromJson? (α := BiomeRow) row.input
    pure (validBiomeIdentifier r.object r.requiredString)
  else if row.kind == "culling" then
    let r ← fromJson? (α := CullingRow) row.input
    if r.rules.length > 2 || r.rules.any (fun r => r.condition > 2 || r.opaqueState > 3) then
      throw "Unselected rule-list/evidence profile."
    let p := row.profile
    let s : CullingSchema := ⟨p.conditionDeclared,p.opaqueDeclared,p.opaqueDefaultAnnotation⟩
    let input : Culling := ⟨r.object,r.description,r.identifier,r.rulesArray,
      r.rules.map (fun r => ⟨r.object,r.direction,r.geometry,r.bone,r.cube,r.face,r.condition,r.opaqueState⟩)⟩
    pure (validCulling s input)
  else throw "Unselected schema family."

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one schema-model request."; return 2
  let raw ← IO.FS.readFile path
  match Json.parse raw >>= fromJson? (α := Envelope) with
  | .error e => IO.eprintln e; return 2
  | .ok request =>
    if request.schema != 1 || request.edition != "bedrock" || request.oracle != "jsonschema-4.26.0-draft7" then
      IO.eprintln "Unselected schema, edition, or validator profile."; return 2
    match request.cases.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok values => IO.println (toJson values).compress; return 0
