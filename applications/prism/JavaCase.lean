import Lean
import applications.prism.Java
open Lean ApplicationStudy.PrismJava

private structure RawAction where
  op : String
  text : Option String := none
  flag : Option Bool := none
  deriving FromJson
private structure RawSetting where
  passthrough : Bool
  gate : Bool
  globalDefault : String
  globalValue : String
  localValue : Option String
  actions : List RawAction
  deriving FromJson
private structure RawMetadata where
  version : String
  architecture : String
  realArchitecture : String
  vendor : String
  deriving FromJson
private structure RawPipeline where
  executable : Bool
  checkerAvailable : Bool
  override : Bool
  signatureMatches : Bool
  stored : RawMetadata
  probe : Nat
  result : RawMetadata
  memory : Nat
  ignore : Bool
  majors : List Nat
  deriving FromJson
private structure Row where
  kind : String
  setting : Option RawSetting := none
  pipeline : Option RawPipeline := none
  deriving FromJson
private structure Document where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson

private def admittedString (s : String) : Bool :=
  !s.isEmpty && s.length ≤ 64 && s.toList.all (fun c => c.isAlphanum || c == '-') && s != "-"

private def action (a : RawAction) : Except String Action := do
  match a.op, a.text, a.flag with
  | "set", some v, none =>
    unless admittedString v do throw "Unadmitted setting value."
    pure (.set v)
  | "global", some v, none =>
    unless admittedString v do throw "Unadmitted global value."
    pure (.global v)
  | "gate", none, some v => pure (.gate v)
  | "reset", none, none => pure .reset
  | _, _, _ => throw "Unknown action or contradictory payload."

private def metadata (m : RawMetadata) : Except String Metadata := do
  let major ← match m.version with
    | "21.0.1" => pure 21 | "25.0.1" => pure 25 | "1.8.0_452" => pure 8
    | "" | "unknown" => pure 0
    | _ => throw "Version parser is qualified only for the selected fixture strings."
  unless ["", "32", "64"].contains m.architecture && ["", "aarch64"].contains m.realArchitecture &&
      ["", "old-vendor", "fixture-vendor"].contains m.vendor do
    throw "Unqualified metadata field."
  pure ⟨m.version, major, m.architecture, m.realArchitecture, m.vendor⟩

private def evaluate (row : Row) : Except String String := do
  match row.kind, row.setting, row.pipeline with
  | "setting", some s, none =>
    unless admittedString s.globalDefault && admittedString s.globalValue &&
        (s.localValue.toList.all admittedString) && s.actions.length ≤ 16 do
      throw "Outside the synchronous string-setting fixture profile."
    let actions ← s.actions.mapM action
    let initial : SettingState := ⟨s.passthrough, s.gate, s.globalDefault, s.globalValue, s.localValue⟩
    pure (String.intercalate ";" ((trace initial actions).map settingText))
  | "pipeline", none, some p =>
    unless p.probe ≤ 2 && p.memory ≤ 16384 && p.majors.length ≤ 8 &&
        p.majors.all (fun m => m > 0 && m ≤ 32) do
      throw "Outside the injected-result runtime profile."
    let input : Input := ⟨p.executable, p.checkerAvailable, p.override, p.signatureMatches,
      ← metadata p.stored, p.probe, ← metadata p.result, p.memory, p.ignore, p.majors⟩
    pure (resultText (run input))
  | _, _, _ => throw "Unknown or contradictory case kind."

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one Prism Java research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Document) with
  | .error e => IO.eprintln e; return 2
  | .ok document =>
    if document.schema != 1 || document.profile != "prism-settings-injected-probe" ||
        document.rows.isEmpty || document.rows.length > 128 then
      IO.eprintln "Unsupported research schema, profile, or count."; return 2
    match document.rows.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok rows => IO.println (toJson rows).compress; return 0
