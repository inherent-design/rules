import Lean
import applications.vscode.WorkspaceSearch
open Lean ApplicationStudy.VscodeWorkspaceSearch

private structure RawResource where
  identity : String
  root : String
  present : Bool
  excluded : Bool
  providerMatch : Bool
  openEligible : Bool
  openMatch : Bool
  deriving FromJson
private structure RawGroup where
  admitted : Bool
  effects : List String
  deriving FromJson
private structure Row where
  kind : String
  roots : List String := []
  respect : Bool := false
  resources : List RawResource := []
  cancelled : Bool := false
  start : Nat := 0
  count : Nat := 0
  adds : List String := []
  planned : Nat := 0
  submitted : Nat := 0
  actual : Nat := 0
  groups : List RawGroup := []
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson

private def admittedRoot (s : String) : Bool := ["a", "b", "c"].contains s
private def admittedResource (s : String) : Bool :=
  ["a/visible.txt", "a/hidden.txt", "a/search-hidden.txt", "b/visible.txt",
   "c/visible.txt", "outside.txt"].contains s

private def evaluate (row : Row) : Except String String := do
  unless row.roots.length ≤ 3 && row.roots.all admittedRoot &&
      row.roots.eraseDups.length == row.roots.length do throw "Unadmitted root identities."
  match row.kind with
  | "file" | "text" =>
    unless row.resources.length ≤ 8 && row.resources.all (fun r =>
        admittedResource r.identity && r.root == (if r.identity == "outside.txt" then "" else
          (r.identity.splitOn "/").head!) &&
        (!r.openEligible || ["a/visible.txt", "outside.txt"].contains r.identity)) &&
        (row.resources.map (·.identity)).eraseDups.length == row.resources.length do
      throw "Unadmitted resource or duplicate identity."
    let resources := row.resources.map fun r =>
      Resource.mk r.identity r.root r.present r.excluded r.providerMatch r.openEligible r.openMatch
    if row.kind == "file" then
      pure ("F|" ++ String.intercalate "," (fileQuery row.roots row.respect row.cancelled resources))
    else
      if row.cancelled then throw "In-flight text cancellation is not this native profile."
      pure ("T|" ++ String.intercalate "," ((textResults row.roots row.respect resources).map (·.1)))
  | "workspace" =>
    unless row.start ≤ 3 && row.count ≤ 3 && row.adds.length ≤ 3 && row.adds.all admittedRoot &&
        row.adds.eraseDups.length == row.adds.length do throw "Outside validated workspace request profile."
    let result := request ⟨row.roots, none⟩ row.start row.count row.adds
    pure ("W|" ++ (if result.1 then "1" else "0") ++ "|" ++
      String.intercalate "," (visible result.2) ++ "|" ++ String.intercalate "," (visible (confirm result.2)))
  | "version" =>
    unless row.planned > 0 && row.submitted > 0 && row.actual > 0 &&
        row.planned ≤ 32 && row.submitted ≤ 32 && row.actual ≤ 32 do throw "Unadmitted version witness."
    pure ("E|" ++ (if currentVersionGuard row.submitted row.actual then "1" else "0"))
  | "groups" =>
    unless !row.groups.isEmpty && row.groups.length ≤ 8 && row.groups.all (fun g =>
        g.effects.length ≤ 2 && g.effects.all (fun s =>
          ["created:a/interleaved.txt", "buffer-prefix", "later"].contains s)) do
      throw "Outside prepared-group comparison profile."
    let result := runGroups (row.groups.map fun g => Group.mk g.admitted g.effects)
    pure ("G|" ++ (if result.1 then "1" else "0") ++ "|" ++ String.intercalate "," result.2)
  | _ => throw "Unknown workspace/search comparison kind."

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one workspace/search research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "vscode-workspace-search-edits" ||
        input.rows.isEmpty || input.rows.length > 64 then
      IO.eprintln "Unsupported research schema, profile, or case count."; return 2
    match input.rows.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok rows => IO.println (toJson rows).compress; return 0
