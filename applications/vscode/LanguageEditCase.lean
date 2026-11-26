import Lean
import applications.vscode.LanguageEdit
open Lean ApplicationStudy.VscodeLanguageEdit

private structure Raw where
  mode : String
  basis : Nat
  secondBasis : Nat
  intervened : Bool
  secondEmpty : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  cases : List Raw
  deriving FromJson

private def evaluate (r : Raw) : Except String Json := do
  unless 0 < r.basis && r.basis ≤ 64 && 0 < r.secondBasis && r.secondBasis ≤ 64 do
    throw "Outside the captured version profile."
  let mode ← match r.mode with
    | "workspace" => pure Mode.workspace
    | "guarded" => pure Mode.guarded
    | "editor-pair" => pure Mode.editorPair
    | "format-compute" => pure Mode.formatCompute
    | "format-apply" => pure Mode.formatApply
    | "format-command" => pure Mode.formatCommand
    | "rename-compute" => pure Mode.renameCompute
    | "rename-apply" => pure Mode.renameApply
    | _ => throw "Unknown language-edit route."
  unless mode == .editorPair || (!r.secondEmpty && r.secondBasis == r.basis) do
    throw "Second editor basis is only admitted for an editor pair."
  unless mode != .editorPair || (!r.intervened && (r.secondBasis == r.basis || r.secondBasis == r.basis + 1)) do
    throw "Outside the controlled editor-pair schedule."
  let result := run ⟨mode, r.basis, r.secondBasis, r.intervened, r.secondEmpty⟩
  pure (toJson (result.response, result.text, result.changes, result.canceled))

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one retained language-edit input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "vscode-1.148-language-edit" || input.cases.isEmpty || input.cases.length > 16 then
      IO.eprintln "Unsupported language-edit schema, profile, or case count."; return 2
    match input.cases.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok results => IO.println (toJson results).compress; return 0
