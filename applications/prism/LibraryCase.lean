import Lean
import applications.prism.Library
open Lean ApplicationStudy.PrismLibrary
private structure Row where
  kind : String
  current : String
  requested : String
  role : Bool
  present : Bool
  alias : Bool
  candidate : Bool
  trashMode : Bool
  mode : Nat
  hasHistory : Bool
  mainPending : Bool
  mainMoved : Bool
  shortcutsMoved : Bool
  shortcutsPending : Nat
  probed : Bool
  writeSucceeded : Bool
  members : List Nat
  prior : Bool
  incoming : Bool
  configs : List Bool
  aliases : List Bool
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson
private def bit (b : Bool) : String := if b then "1" else "0"
private def evaluate (r : Row) : Except String String := do
  unless r.mode ≤ 2 && r.shortcutsPending ≤ 1 && r.members.length ≤ 3 &&
      r.members.all (fun n => n > 0 && n ≤ 3) && r.configs.length ≤ 6 && r.aliases.length == r.configs.length &&
      ["a","b","Renamed"].contains r.current && ["a","b","Renamed"].contains r.requested do
    throw "Outside selected library profile."
  match r.kind with
  | "rename" =>
    let result := renameLabel r.current r.requested r.role
    pure (bit result.1 ++ "|" ++ result.2)
  | "group" => pure (groupText r.present r.alias r.candidate)
  | "lookup" => pure (toString (firstMatch r.mode 2 [⟨1,0,2⟩,⟨2,2,3⟩]))
  | "unique" => pure (toString (uniqueMatch r.mode 2 [⟨1,0,2⟩,⟨2,2,3⟩]))
  | "remove" => pure (removeText r.trashMode r.writeSucceeded)
  | "undo" => pure (undoText r.hasHistory r.mainMoved r.shortcutsMoved)
  | "retry" =>
    let s := advance ⟨r.mainPending,r.shortcutsPending⟩ r.mainMoved r.shortcutsMoved
    pure (bit s.mainPending ++ "|" ++ toString s.shortcutsPending ++ "|" ++ bit (canForget s))
  | "save" => pure (saveText r.probed r.writeSucceeded)
  | "counts" => pure (String.intercalate "|" [toString (loadedCount r.members),toString (bindingCount r.members),toString (savedCount [1,2] r.members)])
  | "collapse" => pure (bit (collapsedAfterLoad r.prior r.incoming))
  | "discover" => pure (String.intercalate "," ((List.zip r.configs r.aliases).map fun (c,a) => bit (discovered c a)))
  | _ => throw "Unknown library comparison kind."
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one library research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok v =>
    if v.schema != 1 || v.profile != "prism-library-methods" || v.rows.isEmpty || v.rows.length > 64 then
      IO.eprintln "Unsupported library research schema/profile/count."; return 2
    match v.rows.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok rows => IO.println (toJson rows).compress; return 0
