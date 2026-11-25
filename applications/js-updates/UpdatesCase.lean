import Lean
import applications.«js-updates».Updates
open Lean ApplicationStudy.JsUpdates

private structure RawCatalog where
  stable : List String
  latest : String
  deriving FromJson
private structure RawDependency where
  name : String
  spec : String
  installed : String
  saved : String
  selected : Bool
  evidence : String
  lookupStatus : Nat
  catalog : Option RawCatalog
  deriving FromJson
private structure Row where
  profile : String
  action : String
  dependencies : List RawDependency
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson

private def version (s : String) : Except String Version := do
  let [a,b,c] := s.splitOn "." | throw "Admitted stable version requires three components."
  let some major := a.toNat? | throw "Invalid major."
  let some minor := b.toNat? | throw "Invalid minor."
  let some patch := c.toNat? | throw "Invalid patch."
  let v : Version := ⟨major,minor,patch⟩
  unless major > 0 && major ≤ 32 && minor ≤ 4096 && patch ≤ 4096 && versionText v == s do
    throw "Outside the canonical positive-major stable profile."
  pure v
private def selection (s : String) : Except String Selection := do
  if s.startsWith "local:" then
    let some basis := (s.drop 6).toString.toNat? | throw "Invalid local witness."
    unless basis > 0 && basis ≤ 4096 && s == s!"local:{basis}" do throw "Local witness bound."
    pure (.local basis)
  else pure (.registry (← version s))
private def specification (s : String) : Except String Spec := do
  if s.startsWith "file:" then
    unless s == "file:../local" do throw "Unadmitted opaque local fixture reference."
    pure (.local s)
  else if s.startsWith "^" then pure (.caret (← version (s.drop 1).toString))
  else pure (.exact (← version s))
private def catalog (r : RawCatalog) : Except String Catalog := do
  if r.stable.isEmpty || r.stable.length > 32 then throw "Catalog bound."
  let values ← r.stable.mapM version
  let tag ← version r.latest
  unless values.eraseDups.length == values.length && values.contains tag do throw "Duplicate version or tag without available target."
  pure ⟨values,tag⟩
private def dependency (r : RawDependency) : Except String Dependency := do
  unless !r.name.isEmpty && r.name.length ≤ 128 && r.name.toList.all (fun c =>
      c.toNat < 128 && (c.isAlphanum || c == '-')) do throw "Unadmitted research name."
  let spec ← specification r.spec
  let installed ← selection r.installed
  let saved ← selection r.saved
  let source ← r.catalog.mapM catalog
  let evidence ← match r.evidence with
    | "online" => pure Evidence.online | "prior" => pure .prior
    | "missing" => pure .missing | "not-queried" => pure .notQueried
    | _ => throw "Unknown metadata evidence."
  match evidence with
  | .online => unless r.lookupStatus == 200 && source.isSome do throw "Online evidence needs a successful response and catalog."
  | .prior => unless [0,404].contains r.lookupStatus && source.isSome do throw "Prior evidence needs an earlier catalog and qualified request status."
  | .missing => unless r.lookupStatus == 404 && source.isNone do throw "Missing evidence is this fixture's selected 404, not every network failure."
  | .notQueried => unless r.lookupStatus == 0 && source.isNone do throw "Unqueried evidence cannot invent a response."
  match spec,installed,saved with
  | .local _,.local _,.local _ => pure ()
  | .exact _,.registry _,.registry _ => pure ()
  | .caret _,.registry _,.registry _ => pure ()
  | _,_,_ => throw "Declaration and selected source kinds disagree."
  if let some c := source then
    -- Native fixtures never have a satisfying tag below another permitted
    -- stable version. Refuse that unqualified resolver-preference boundary.
    if permits spec c.latest && within c spec != some c.latest then
      throw "Unqualified tag versus highest-in-range preference."
  pure ⟨r.name,spec,installed,saved,r.selected,evidence,source⟩
private def evaluate (r : Row) : Except String String := do
  let profile ← match r.profile with
    | "npm" => pure Profile.npm | "pnpm" => pure .pnpm | "yarn" => pure .yarn
    | _ => throw "Unknown application profile."
  let action ← match r.action with
    | "refresh" => pure Action.refresh | "rewrite-latest" => pure .rewriteLatest
    | "inspect" => pure .inspect | _ => throw "Unknown update operation."
  if profile == .yarn && action == .inspect then throw "Yarn inspector is not a selected native command."
  if r.dependencies.isEmpty || r.dependencies.length > 16 then throw "Dependency bound."
  let ds ← r.dependencies.mapM dependency
  unless (ds.map (·.name)).eraseDups.length == ds.length do throw "Duplicate dependency identity."
  if profile == .pnpm && action == .inspect && ds.any (fun d => d.selected && match d.spec with
      | .local _ => false | _ => d.catalog.isNone) then
    throw "Cold missing-catalog pnpm result is source-modeled, not native-qualified here."
  pure (reportText (run profile action ds))

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one research update input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error e => IO.eprintln e; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "positive-major-stable-caret-tags" || input.rows.isEmpty || input.rows.length > 128 then
      IO.eprintln "Unsupported update research schema, profile, or count."; return 2
    match input.rows.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok values => IO.println (toJson values).compress; return 0
