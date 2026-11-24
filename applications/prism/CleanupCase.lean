import Lean
import applications.prism.Cleanup
open Lean ApplicationStudy.PrismCleanup

private structure RequestInput where
  path : String
  pairDisabled : Bool
  deriving FromJson
private structure CellInput where
  path : String
  kind : Nat
  target : Option String
  deriving FromJson
private structure Row where
  kind : String
  choice : Nat
  answers : List Nat
  requests : List RequestInput
  overrideExisting : Bool
  cells : List CellInput
  paths : List String
  name : String
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  cases : List Row
  deriving FromJson

private def choice (n : Nat) : Except String Choice :=
  match n with
  | 0 => .ok .unasked | 1 => .ok .yes | 2 => .ok .no
  | _ => .error "Unknown save-choice state."
private def choiceCode : Choice → Nat
  | .unasked => 0 | .yes => 1 | .no => 2
private def kindCode : Kind → Nat
  | .file => 0 | .directory => 1 | .brokenLink => 2 | .fileLink => 3
private def validatePath (path : String) (empty : Bool := false) : Except String Unit := do
  if path == "" && empty then return ()
  let n := normalize path
  if path == "" || path.startsWith "/" || path.contains '\\' || path.contains '\x00' ||
      n == "." || n == ".." || n.startsWith "../" then
    throw "Path is outside the admitted relative fixture profile."
private def cells (row : Row) : Except String (List Cell) := do
  if (row.cells.map (·.path)).eraseDups.length != row.cells.length then throw "Duplicate fixture cell."
  row.cells.mapM fun c => do
    validatePath c.path
    if normalize c.path != c.path then throw "Cell identity must already be normalized."
    let kind ← match c.kind with
      | 0 => pure Kind.file | 1 => pure Kind.directory | 2 => pure Kind.brokenLink | 3 => pure Kind.fileLink
      | _ => throw "Unknown fixture node kind."
    if c.kind >= 2 then
      let some target := c.target | throw "Link target witness is missing."
      validatePath target
      if normalize target != target then throw "Link target must already be normalized."
      let known := row.cells.find? (·.path == target)
      if c.kind == 2 && known.isSome then throw "Broken-link witness has a known referent."
      if c.kind == 3 && !(known.any (·.kind == 0)) then throw "Only static regular-file referents are modeled."
    else if c.target.isSome then throw "A non-link cell cannot have a target witness."
    pure ⟨c.path,kind⟩
private def checkStaticLinks (row : Row) (paths : List String) : Except String Unit := do
  for cell in row.cells do
    if cell.kind == 3 && cell.target.any paths.contains then
      throw "Removing a link referent is outside the static-link profile."
    if paths.any (fun path => path.startsWith (cell.path ++ "/")) && cell.kind >= 2 then
      throw "Symlinked ancestors are outside the admitted fixture profile."
private def output (p : Plan) (effect : Effect) (records : List String) : Json :=
  Json.mkObj [("choice",toJson (choiceCode p.choice)),("prompts",toJson p.prompts),("paths",toJson p.paths),
    ("remaining",toJson (effect.cells.map (fun c => Json.mkObj [("path",toJson c.path),("kind",toJson (kindCode c.kind))]))),
    ("failed",toJson effect.failed),("cleanupPassed",toJson (!effect.failed)),("recordRefused",toJson false),("records",toJson records)]
private def evaluate (row : Row) (proposed : Bool) : Except String Json := do
  let initial ← choice row.choice
  let answers ← row.answers.mapM choice
  if answers.contains .unasked then throw "An answer must be yes or no."
  let before ← cells row
  let (requests,records) ← if row.kind == "cleanup" then do
    if !row.paths.isEmpty || row.name != "" then throw "Cleanup input must not contain override records."
    let requests ← row.requests.mapM fun r => do
      validatePath r.path true
      pure (⟨r.path,r.pairDisabled⟩ : Request)
    pure (requests,[])
    else if row.kind == "overrides" then do
      if !row.requests.isEmpty || row.choice != 0 || !row.answers.isEmpty || !row.overrideExisting then
        throw "Override input is outside the joined fixture profile."
      if row.name != "overrides" && row.name != "client-overrides" then throw "Unknown override root name."
      for path in row.paths do
        validatePath path
        let raw := ("/" ++ path).toList
        if (lastSuffix row.name.toList raw raw).head?.any (fun c => c.toNat > 65535) then
          throw "Unmodeled UTF-16 suffix slicing."
      let records ← if proposed then match readProposedRecords row.paths with
        | .ok records => pure records
        | .error _ => return Json.mkObj [("recordRefused",toJson true),("remaining",toJson (before.map (fun c =>
            Json.mkObj [("path",toJson c.path),("kind",toJson (kindCode c.kind))])))]
        else pure (readCurrentRecords row.name row.paths)
      pure (records.map (fun path => (⟨path,false⟩ : Request)),records)
    else throw "Unknown cleanup research operation."
  let plan ← schedule proposed initial answers requests
  checkStaticLinks row plan.paths
  pure (output plan (cleanup row.overrideExisting before plan.paths) records)

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one Prism cleanup research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported Prism cleanup schema."; return 2
    if input.profile != "qt6-mac-relative-static-links" then IO.eprintln "Unsupported cleanup host profile."; return 2
    let values := input.cases.mapM fun row => do
      let current ← evaluate row false
      let proposed ← evaluate row true
      pure (Json.mkObj [("current",current),("proposed",proposed)])
    match values with
    | .error error => IO.eprintln error; return 2
    | .ok rows => IO.println (toJson rows).compress; return 0
