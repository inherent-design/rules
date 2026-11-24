namespace ApplicationStudy.PrismCleanup

deriving instance DecidableEq for Except

inductive Choice | unasked | yes | no
  deriving BEq, DecidableEq, Repr
structure Request where
  path : String
  pairDisabled : Bool
  deriving BEq, DecidableEq, Repr
structure Plan where
  choice : Choice
  prompts : Nat
  paths : List String
  answers : List Choice
  deriving BEq, DecidableEq, Repr

/-- Small executable character-list operations keep the finite laws reducible
    in the kernel; they do not claim Qt's complete UTF-16/string API. -/
def isPrefixChars : List Char → List Char → Bool
  | [], _ => true
  | _, [] => false
  | a :: aa, b :: bb => a == b && isPrefixChars aa bb
def starts (value needle : String) : Bool := isPrefixChars needle.toList value.toList
def splitChar (separator : Char) : List Char → List (List Char)
  | [] => [[]]
  | c :: tail =>
    match splitChar separator tail with
    | [] => [[c]]
    | head :: rest => if c == separator then [] :: head :: rest else (c :: head) :: rest
def lastSuffix (needle : List Char) : List Char → List Char → List Char
  | [], best => best
  | c :: tail, best => lastSuffix needle tail (if isPrefixChars needle (c :: tail) then (c :: tail).drop needle.length else best)

/-- Lexical normalization for the captured relative, forward-slash host profile.
    It establishes neither realpath containment nor symlink-ancestor safety. -/
def normalize (path : String) : String :=
  let stack := ((splitChar '/' path.toList).map String.ofList).foldl (fun stack part =>
    if part == "" || part == "." then stack
    else if part == ".." then
      match stack with
      | h :: t => if h != ".." then t else part :: stack
      | [] => [part]
    else part :: stack) ([] : List String)
  if stack.isEmpty then "." else String.intercalate "/" stack.reverse

def alternate (path : String) : String :=
  if isPrefixChars ".disabled".toList.reverse path.toList.reverse then String.ofList (path.toList.reverse.drop 9).reverse
  else path ++ ".disabled"
def protectedPath (proposed : Bool) (path : String) : Bool :=
  if proposed then let p := normalize path; p == "saves" || starts p "saves/"
  else starts path "saves/"

/-- Initial choice and answers are admitted fixture inputs. No native
    constructor, actual dialog, or indeterminate enum state is modeled. -/
def scheduleOne (proposed : Bool) (plan : Plan) (request : Request) : Except String Plan := do
  if request.path == "" then return plan
  let plan ← if protectedPath proposed request.path && plan.choice == .unasked then
    match plan.answers with
    | [] => throw "Missing save-choice answer."
    | .unasked :: _ => throw "An answer must be yes or no."
    | answer :: tail => pure {plan with choice := answer, prompts := plan.prompts + 1, answers := tail}
    else pure plan
  if protectedPath proposed request.path && plan.choice == .no then return plan
  let added := if request.pairDisabled then [request.path,alternate request.path] else [request.path]
  return {plan with paths := plan.paths ++ added.map normalize}
def schedule (proposed : Bool) (initial : Choice) (answers : List Choice) (requests : List Request) : Except String Plan :=
  requests.foldlM (scheduleOne proposed) ⟨initial,0,[],answers⟩

inductive Kind | file | directory | brokenLink | fileLink
  deriving BEq, DecidableEq, Repr
structure Cell where
  path : String
  kind : Kind
  deriving BEq, DecidableEq, Repr
structure Effect where
  cells : List Cell
  failed : Bool
  deriving BEq, DecidableEq, Repr

/-- Typed, static fixture nodes and no concurrent writer. A broken referent
    makes QFile::exists false although the symlink object still exists. -/
def deleteOne (effect : Effect) (path : String) : Effect :=
  match effect.cells.find? (·.path == path) with
  | none => effect
  | some cell => match cell.kind with
    | .brokenLink => effect
    | .directory => {effect with failed := true}
    | .file | .fileLink => {effect with cells := effect.cells.filter (·.path != path)}
def cleanup (overrideExisting : Bool) (cells : List Cell) (paths : List String) : Effect :=
  if overrideExisting then paths.foldl deleteOne ⟨cells,false⟩ else ⟨cells,false⟩

/-- Source split(name).last.remove(0,1), restricted to the captured slash/dash
    suffix starts; this is not arbitrary QString UTF-16 slicing. -/
def recordedPath (name path : String) : String :=
  let raw := ("/" ++ path).toList
  String.ofList (lastSuffix name.toList raw raw).tail
def selectedWhitespace (c : Char) : Bool :=
  c == ' ' || c == '\t' || c == '\r' || c == '\n' || c == '\u00a0'
def trimRecord (path : String) : String :=
  String.ofList (((path.toList.dropWhile selectedWhitespace).reverse.dropWhile selectedWhitespace).reverse)
def readCurrentRecords (name : String) (paths : List String) : List String :=
  let serialized := if paths.isEmpty then "" else String.intercalate "\n" (paths.map (recordedPath name)) ++ "\n"
  ((splitChar '\n' serialized.toList).map String.ofList).map trimRecord

/-- Candidate preserves root-relative names and only admits representable line
    records. It is not implemented by the source or an encoder qualification. -/
def readProposedRecords (paths : List String) : Except String (List String) :=
  if paths.any (fun p => p.toList.contains '\n' || p.toList.contains '\r' || p.toList.contains '\x00') then
    .error "Filename cannot be represented by the proposed line record."
  else .ok (paths ++ [""])

theorem failure_is_sticky (effect : Effect) (path : String) (h : effect.failed = true) :
    (deleteOne effect path).failed = true := by
  unfold deleteOne
  split
  · exact h
  · rename_i cell _
    cases cell.kind <;> simp_all
theorem absent_target_changes_no_cell (effect : Effect) (path : String)
    (h : effect.cells.find? (·.path == path) = none) : deleteOne effect path = effect := by
  simp [deleteOne,h]
theorem known_no_blocks_proposed_target (p : Plan) (r : Request)
    (hChoice : p.choice = .no) (hTarget : protectedPath true r.path = true) :
    scheduleOne true p r = .ok p := by
  by_cases hEmpty : r.path = ""
  · simp [scheduleOne,hEmpty]; rfl
  · simp [scheduleOne,hEmpty,hTarget,hChoice]; rfl
theorem admitted_proposed_names_preserved (paths : List String)
    (h : paths.any (fun p => p.toList.contains '\n' || p.toList.contains '\r' || p.toList.contains '\x00') = false) :
    readProposedRecords paths = .ok (paths ++ [""]) := by
  unfold readProposedRecords
  rw [h]
  rfl

theorem empty_request_changes_nothing (proposed : Bool) (p : Plan) :
    scheduleOne proposed p ⟨"",true⟩ = .ok p := rfl
theorem no_override_has_no_cleanup_effect (cells : List Cell) (paths : List String) :
    cleanup false cells paths = ⟨cells,false⟩ := rfl
theorem legacy_alias_ignores_cached_no :
    schedule false .no [] [⟨"./saves/world/level.dat",false⟩] =
      .ok ⟨.no,0,["saves/world/level.dat"],[]⟩ := by decide
theorem proposed_alias_honors_cached_no :
    schedule true .no [] [⟨"./saves/world/level.dat",false⟩] = .ok ⟨.no,0,[],[]⟩ := by decide
theorem cached_no_does_not_prompt_again :
    schedule false .no [] [⟨"saves/a",false⟩,⟨"saves/b",false⟩] = .ok ⟨.no,0,[],[]⟩ := by decide
theorem missing_answer_is_unknown_not_permission :
    schedule false .unasked [] [⟨"saves/a",false⟩] = .error "Missing save-choice answer." := by decide
theorem pairing_uses_both_spellings :
    schedule false .unasked [] [⟨"mods/a.jar.disabled",true⟩] =
      .ok ⟨.unasked,0,["mods/a.jar.disabled","mods/a.jar"],[]⟩ := by decide
theorem broken_link_remains_despite_missing_referent :
    cleanup true [⟨"mods/link",.brokenLink⟩] ["mods/link"] = ⟨[⟨"mods/link",.brokenLink⟩],false⟩ := by rfl
theorem valid_link_removal_preserves_target :
    cleanup true [⟨"link",.fileLink⟩,⟨"target",.file⟩] ["link"] = ⟨[⟨"target",.file⟩],false⟩ := by rfl
theorem failure_does_not_undo_or_stop_other_deletions :
    cleanup true [⟨"first",.file⟩,⟨"dir",.directory⟩,⟨"last",.file⟩] ["first","dir","last"] =
      ⟨[⟨"dir",.directory⟩],true⟩ := by rfl
theorem marker_in_filename_loses_destination :
    recordedPath "overrides" "config/my-overrides-settings.toml" = "settings.toml" := by decide
theorem trimmed_filename_loses_spaces :
    readCurrentRecords "overrides" ["  options.txt  "] = ["options.txt",""] := by decide
theorem newline_filename_becomes_two_records :
    readCurrentRecords "overrides" ["config/line\nbreak.txt"] = ["config/line","break.txt",""] := by decide
theorem proposed_record_retains_destination :
    readProposedRecords ["config/my-overrides-settings.toml"] = .ok ["config/my-overrides-settings.toml",""] := by decide
theorem proposed_record_retains_spaces :
    readProposedRecords ["  options.txt  "] = .ok ["  options.txt  ",""] := by decide
theorem proposed_record_refuses_newline :
    readProposedRecords ["config/line\nbreak.txt"] = .error "Filename cannot be represented by the proposed line record." := by decide

end ApplicationStudy.PrismCleanup
