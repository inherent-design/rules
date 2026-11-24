import Lean
import applications.empack.RootState
open Lean ApplicationStudy.EmpackRootState

private structure RecordRow where
  schema : Nat
  original : Option String
  token : Nat
  deriving FromJson
private structure EntryRow where
  name : String
  directory : Bool
  markerKind : Nat
  bytes : Nat
  record : Option RecordRow
  children : List String
  deriving FromJson
private structure Row where
  root : Nat
  current : String
  suffix : String
  token : Option Nat
  entries : List EntryRow
  deriving FromJson
private structure Request where
  schema : Nat
  profile : String
  cases : List Row
  deriving FromJson
private def canonical (xs : List String) : Bool := xs == xs.mergeSort (· ≤ ·) && xs.eraseDups.length == xs.length
private def hexPart (s : String) : Bool := !s.isEmpty && s.toList.all (fun c => c.isDigit || ('a' ≤ c && c ≤ 'f'))
private def key (s : String) : Bool :=
  match s.splitOn "-" with
  | [p,v,n,t,u] => p == "project" && v.length == 16 && n.length == 32 && [v,n,t,u].all hexPart
  | _ => false
private def label (n : Nat) : Bool := 0 < n && n ≤ 4096
private def checkedRecord (r : RecordRow) : Except String Record := do
  if r.schema > 4294967295 || !label r.token || r.original.any (fun n => !key n) then throw "Invalid decoded association witness."
  pure ⟨r.schema,r.original,r.token⟩
private def entry (r : EntryRow) : Except String Entry := do
  if r.name.isEmpty || r.name.length > 1024 || r.name.contains '/' || r.name.contains '\x00' then throw "Invalid immediate entry name."
  if !canonical r.children then throw "Invalid child order or duplicate."
  if !r.directory && (!r.children.isEmpty || r.markerKind != 0) then throw "Invalid nondirectory payload."
  let marker ← match r.markerKind with
    | 0 =>
      if r.bytes != 0 || r.record.isSome || r.children.contains "root-identity.json" then throw "Invalid absent marker witness."
      pure Marker.absent
    | 1 =>
      if r.bytes != 0 || r.record.isSome || !r.children.contains "root-identity.json" then throw "Invalid unreadable marker witness."
      pure Marker.unreadable
    | 2 =>
      if r.bytes > 1048576 || !r.children.contains "root-identity.json" then throw "Invalid wire marker witness."
      pure (Marker.wire r.bytes (← r.record.mapM checkedRecord))
    | _ => throw "Unknown marker kind."
  pure ⟨r.name,r.directory,marker,r.children⟩
private def checked (r : Row) : Except String Input := do
  if !key r.current then throw "Invalid current key."
  let expected := "-" ++ String.intercalate "-" ((r.current.splitOn "-").drop 2)
  if r.suffix != expected then throw "Invalid current suffix."
  if r.token.any (fun n => !label n) then throw "Invalid current token witness."
  if r.entries.length > 8192 || !canonical (r.entries.map (·.name)) then throw "Invalid entry order,count,or duplicate."
  let root ← match r.root with
    | 0 => pure RootEvidence.same | 1 => pure RootEvidence.missing | 2 => pure RootEvidence.replaced
    | _ => throw "Unknown root evidence."
  pure ⟨root,r.current,r.suffix,r.token,← r.entries.mapM entry⟩
private def output (r : Outcome) : Json := Json.mkObj [
  ("ok",toJson r.ok),("selected",toJson r.selected),("found",toJson r.found),("bound",toJson r.bound)]
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one discovery research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Request) with
  | .error e => IO.eprintln e; return 2
  | .ok r =>
    if r.schema != 1 || r.profile != "quiescent-mac-discovery" then
      IO.eprintln "Unsupported discovery research schema/profile."; return 2
    match r.cases.mapM (fun v => checked v >>= fun i => pure (output (evaluate i))) with
    | .error e => IO.eprintln e; return 2
    | .ok results => IO.println (toJson results).compress; return 0
