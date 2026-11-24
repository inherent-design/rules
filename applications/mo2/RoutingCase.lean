import Lean
import applications.mo2.Routing
open Lean ApplicationStudy.Mo2Routing
private structure ModRow where
  identity : Nat
  reserved : Bool
  regular : Bool
  deriving FromJson
private structure MappingRow where
  kind : String
  identity : Nat
  destination : Nat
  directory : Bool
  createTarget : Bool
  deriving FromJson
private structure PluginRow where
  enabled : Bool
  rows : List MappingRow
  deriving FromJson
private structure InputRow where
  active : List ModRow
  dataPaths : List Nat
  custom : Nat
  requestedProfile : Nat
  currentProfile : Nat
  currentLocal : Bool
  requestedLocal : Bool
  localFeature : Bool
  plugins : List PluginRow
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List InputRow
  deriving FromJson
private def decode (r : InputRow) : Except String Request := do
  if r.custom > 5 || r.requestedProfile == 0 || r.requestedProfile > 2 || r.currentProfile == 0 || r.currentProfile > 2 then
    throw "Unknown fixture name/profile."
  if r.dataPaths != [1] && r.dataPaths != [1,2] then throw "Unsupported game-path profile."
  if !(r.active.map ModRow.identity).Nodup then throw "Duplicate fixture mod identity."
  if r.active.any (fun m => !(m.identity == 1 || m.identity == 2 || m.identity == 5) || m.reserved != (m.identity == 5)) then
    throw "Unsupported mod witness."
  if r.currentProfile == r.requestedProfile && r.currentLocal != r.requestedLocal then
    throw "One supplied profile cannot carry conflicting local-save flags."
  if r.plugins.length > 1 then throw "Unsupported plugin profile."
  let plugins ← r.plugins.mapM fun p => do
    if p.rows.length != 1 then throw "Unsupported plugin callback."
    let rows ← p.rows.mapM fun row => do
      if row.kind != "plugin" || row.identity != 1 || row.destination != 1 || !row.directory || !row.createTarget then
        throw "Unknown fixture plugin mapping."
      pure ({origin := .plugin 1,destination := 1,directory := true,createTarget := true} : Row)
    pure ({enabled := p.enabled,rows := rows} : ApplicationStudy.Mo2Routing.Plugin)
  pure ⟨r.active.map (fun m => ⟨m.identity,m.reserved,m.regular⟩),r.dataPaths,r.custom,
    r.requestedProfile,r.currentProfile,r.currentLocal,r.requestedLocal,r.localFeature,plugins⟩
private def bit (b : Bool) : String := if b then "1" else "0"
private def origin : Origin → String
  | .mod n => "m" ++ toString n | .overwrite => "o0"
  | .saves n => "s" ++ toString n | .plugin n => "p" ++ toString n
private def row (r : Row) : String :=
  String.intercalate ":" [origin r.origin,toString r.destination,bit r.directory,bit r.createTarget]
private def render (r : Result) : String := match r.mappings with
  | none => "refuse/" ++ bit r.localWarning
  | some rows => "accept/" ++ bit r.localWarning ++ "/" ++ String.intercalate ";" (rows.map row)
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one routing-model input."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported routing research schema."; return 2
    match input.cases.mapM decode with
    | .error error => IO.eprintln error; return 2
    | .ok values =>
      IO.println (Json.mkObj [("current",toJson (values.map (render ∘ planCurrent))),
        ("proposed",toJson (values.map (render ∘ planProposed)))]).compress
      return 0
