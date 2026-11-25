import Lean
import host.minecraft.bedrock.TextureSets
open Lean MinecraftHost.Bedrock.TextureSets

private structure IssuesRow where
  color : Bool
  normal : Bool
  height : Bool
  mer : Bool
  mers : Bool
  backing : Nat
  vibrant : Bool
  textureObject : Bool
  uniformMersVariation : Bool
  deriving FromJson
private structure ChannelRow where
  layer : Nat
  image : Bool
  count : Nat
  deriving FromJson
private structure ImageRow where
  pack : Nat
  name : Nat
  extension : Nat
  contentToken : Nat
  deriving FromJson
private structure ResolveRow where
  pack : Nat
  name : Nat
  images : List ImageRow
  deriving FromJson
private structure DefinitionRow where
  name : Nat
  pack : Nat
  layers : Nat
  deriving FromJson
private structure SelectRow where
  name : Nat
  eligible : List DefinitionRow
  deriving FromJson
private structure DeclareRow where
  pbr : Bool
  raytraced : Bool
  major : Nat
  minor : Nat
  patch : Nat
  deriving FromJson
private structure MaterialRow where
  metal : Nat
  subsurface : Nat
  deriving FromJson
private structure Row where
  action : String
  data : Json
  deriving FromJson
private structure Envelope where
  schema : Nat
  edition : String
  documentationRevision : String
  cases : List Row
  deriving FromJson

private def evaluate (row : Row) : Except String String := do
  match row.action with
  | "issues" =>
    let r ← fromJson? (α := IssuesRow) row.data
    if r.backing > 2 then throw "Unsupported backing evidence state."
    let b := if r.backing == 0 then Backing.resolved else if r.backing == 1 then Backing.unavailable else Backing.unknown
    pure (toString (issues ⟨r.color,r.normal,r.height,r.mer,r.mers,b,r.vibrant,r.textureObject,r.uniformMersVariation⟩))
  | "channels" =>
    let r ← fromJson? (α := ChannelRow) row.data
    if r.layer > 4 || r.count > 4 then throw "Unselected layer/channel profile."
    pure (toString (if channels r.layer r.image r.count then 1 else 0))
  | "resolve" =>
    let r ← fromJson? (α := ResolveRow) row.data
    if r.images.length > 8 || r.images.any (fun i => i.extension > 3) then throw "Unselected image profile."
    let keys := r.images.map (fun i => (i.pack,i.name,i.extension))
    if keys.eraseDups.length != keys.length then throw "Ambiguous physical image candidates."
    let images := r.images.map (fun i => Image.mk i.pack i.name i.extension i.contentToken)
    pure ((resolveImage r.pack r.name images).map toString |>.getD "none")
  | "select" =>
    let r ← fromJson? (α := SelectRow) row.data
    if r.eligible.length > 8 then throw "Unselected definition profile."
    let definitions := r.eligible.map (fun d => Definition.mk d.name d.pack d.layers)
    pure ((selectDefinition r.name definitions).map (fun d => s!"{d.name}/{d.pack}/{d.layers}") |>.getD "none")
  | "declare" =>
    let r ← fromJson? (α := DeclareRow) row.data
    if r.major > 2 || r.minor > 99 || r.patch > 999 then throw "Unselected version profile."
    let (pbr,rtx) := declarationEvidence r.pbr r.raytraced r.major r.minor r.patch
    pure s!"{pbr}/{rtx}"
  | "material" =>
    let r ← fromJson? (α := MaterialRow) row.data
    if r.metal > 255 || r.subsurface > 255 then throw "Unselected channel magnitude."
    let (m,s) := predominant r.metal r.subsurface
    pure s!"{m}/{s}"
  | _ => throw "Unselected documented operation."

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one documentation-model request."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Envelope) with
  | .error e => IO.eprintln e; return 2
  | .ok r =>
    if r.schema != 1 || r.edition != "bedrock" || r.documentationRevision != "80b7b1713df821debb4a8022e32e6b0ad840a273" then
      IO.eprintln "Unselected schema, edition, or documentation revision."; return 2
    match r.cases.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok values => IO.println (toJson values).compress; return 0
