import Lean
import applications.restic.Inputs
open Lean ApplicationStudy.ResticInputs

private structure RuleInput where
  negated : Bool
  hits : List String
  deriving FromJson
private structure Row where
  groups : List (List RuleInput)
  roots : List String
  skippedMissing : Bool
  framingValid : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson

private def files : List String := ["#literal.txt","[literal].txt","keep.txt","line\nbreak.txt",
  "nested/keep.txt","nested/secret.tmp","pruned/keep.txt","secret.tmp","space name.txt","Ω 日本.txt"]
private def directory (name : String) : Entry :=
  .directory name ((files.filter (fun f => f.startsWith (name++"/"))).map Entry.file)
private def fullTree : Entry := .directory "."
  ((files.filter (fun f => !(f.toList.contains '/'))).map Entry.file ++ [directory "nested",directory "pruned"])
private def root (name : String) : Except String Entry :=
  if name == "." then pure fullTree
  else if name == "nested" || name == "pruned" then pure (directory name)
  else if files.contains name then pure (.file name)
  else throw "Unadmitted explicit fixture root."
private def rule (r : RuleInput) : Except String Rule := do
  if r.hits.length > 16 || r.hits.eraseDups.length != r.hits.length ||
      !(r.hits.all (fun p => files.contains p || [".","nested","pruned"].contains p)) then
    throw "Unadmitted path in finite pattern witness."
  pure ⟨r.negated,r.hits⟩
private def evaluate (r : Row) : Except String Json := do
  if r.groups.length > 4 || r.groups.any (fun g => g.length > 16) || r.roots.length > 16 then
    throw "Research input exceeds the finite comparison bound."
  let groups ← r.groups.mapM (fun g => g.mapM rule)
  let roots ← r.roots.mapM root
  let result := backup groups ⟨roots,r.skippedMissing,r.framingValid⟩
  pure (Json.mkObj [("exitCode",toJson result.exitCode),("snapshot",toJson result.snapshot),
    ("selected",toJson (files.map (fun f => result.files.contains f)))])

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one finite input-policy comparison JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "local-relative-regular-inputs" || input.rows.isEmpty || input.rows.length > 128 then
      IO.eprintln "Unsupported input-policy comparison schema, profile, or count."
      return 2
    match input.rows.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok rows => IO.println (toJson rows).compress; return 0
