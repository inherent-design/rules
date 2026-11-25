import Lean
import applications.«cargo-install».Install
open Lean ApplicationStudy.CargoInstall
private structure Row where
  kind : Nat
  aBody : Nat
  aOwner : Nat
  bBody : Nat
  bOwner : Nat
  metadata : Bool
  force : Bool
  compileOk : Bool
  version : Nat
  selectA : Bool
  selectB : Bool
  action : Nat
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson
private def body (n : Nat) : Body :=
  match n with | 0 => .missing | 1 => .v1 | 2 => .v2 | 3 => .manual | 4 => .untracked | _ => .directory
private def number (b : Body) : Nat :=
  match b with | .missing => 0 | .v1 => 1 | .v2 => 2 | .manual => 3 | .untracked => 4 | .directory => 5
private def render (r : Result) : String :=
  String.intercalate "/" ([number r.state.a.body,r.state.a.owner,number r.state.b.body,
    r.state.b.owner,if r.state.metadata then 1 else 0,r.exitCode].map toString)
private def evaluate (r : Row) : Except String Json := do
  if r.kind > 3 || r.aBody > 5 || r.bBody > 5 || r.aOwner > 2 || r.bOwner > 2 ||
      r.version < 1 || r.version > 2 || r.action > 5 then throw "Unsupported install research value."
  let s : State := ⟨⟨body r.aBody,r.aOwner⟩,⟨body r.bBody,r.bOwner⟩,r.metadata⟩
  -- No selected directory deletion, unknown package, or arbitrary IO branches.
  if r.kind == 1 && ((r.selectA && r.aOwner != 0 && r.aBody == 5) ||
      (r.selectB && r.bOwner != 0 && r.bBody == 5)) then throw "Directory unlink not qualified."
  if r.kind == 1 && r.aOwner != 0 && r.bOwner != 0 && r.aOwner != r.bOwner then
    throw "Mixed-package selection is not qualified."
  if r.kind == 1 && ((!r.selectA && !r.selectB) ||
      (r.selectA && r.aOwner == 0) || (r.selectB && r.bOwner == 0)) then
    throw "Removal requires admitted registered binary selection."
  let v := match r.kind with
    | 0 => install s r.force r.compileOk r.version
    | 1 => uninstall s r.selectA r.selectB
    | 3 => Result.mk (control s r.action) 0
    | _ => observe s
  pure (Json.mkObj [("current",toJson (render v)),("proposal",if r.kind == 0 then
    toJson (some (render (install s r.force r.compileOk r.version true))) else toJson (none : Option String))])
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one install research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "owned-two-bin-path-install" || input.rows.length > 128 then
      IO.eprintln "Unsupported install research profile."; return 2
    match input.rows.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok values => IO.println (toJson values).compress; return 0
