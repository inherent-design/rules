namespace ApplicationStudy.PrismLibrary

/-- Label editing is independent of directory/UUID identity and has no promise
    here about the real INI backend. -/
def renameLabel (current requested : String) (editRole : Bool) : Bool × String :=
  if editRole then (true, requested) else (false, current)

/-- 0 canonical directory key,1 supplied UUID key. Existing canonical slots
    update correctly; only the missing-slot branch uses the caller spelling. -/
def insertionKey (canonicalPresent viaUuid candidate : Bool) : Nat :=
  if canonicalPresent || candidate || !viaUuid then 0 else 1

def groupText (canonicalPresent viaUuid candidate : Bool) : String :=
  let key := insertionKey canonicalPresent viaUuid candidate
  toString key ++ "|" ++ (if key == 0 then "1|1" else "0|0")

structure Instance where
  owner : Nat
  directory : Nat
  uuid : Nat
  deriving Repr

def selectorMatches (i : Instance) (mode query : Nat) : Bool :=
  if mode == 1 then i.directory == query else if mode == 2 then i.uuid == query
  else i.directory == query || i.uuid == query

def firstMatch (mode query : Nat) : List Instance → Nat
  | [] => 0
  | i :: rest => if selectorMatches i mode query then i.owner else firstMatch mode query rest
/-- Proposed unique selector. 0 missing,3 ambiguous for the admitted two-owner
    research profile. Current legacy lookup still takes the first match. -/
def uniqueMatch (mode query : Nat) (instances : List Instance) : Nat :=
  match instances.filter (fun i => selectorMatches i mode query) with
  | [] => 0
  | [i] => i.owner
  | _ => 3

/-- Selected existing-instance trash/delete prefixes remove grouping before
    the filesystem call. This predicts metadata/history, not physical effects. -/
def removeText (trash succeeded : Bool) : String :=
  "0|" ++ (if trash && succeeded then "1" else "0")

/-- Current undo Boolean and this-attempt effects. It pops history before the
    rename; a second no-history call returns true without moving anything. -/
def undoText (hasHistory mainMoved shortcutsMoved : Bool) : String :=
  let ok := !hasHistory || (mainMoved && shortcutsMoved)
  (if ok then "1" else "0") ++ "|" ++
    (if hasHistory && mainMoved then "1" else "0") ++ "|0"

structure Retry where
  mainPending : Bool
  shortcutsPending : Nat
  deriving Repr, DecidableEq
/-- Proposed retry-reference state, not exclusive custody of OS trash or
    authority to overwrite a destination. Host facts require revalidation. -/
def advance (s : Retry) (mainMoved shortcutsMoved : Bool) : Retry :=
  if s.mainPending && !mainMoved then s
  else ⟨false, if shortcutsMoved then 0 else s.shortcutsPending⟩
def canForget (s : Retry) : Bool := !s.mainPending && s.shortcutsPending == 0

def saveText (probed writeSucceeded : Bool) : String :=
  -- Source gate + atomic fixture-writer outcome, not a product return enum.
  if !probed then "skipped|0" else if writeSucceeded then "saved|1" else "failed|0"

/-- Source group parsing counts raw entries; map bindings and emitted saved
    membership are distinct. QMap/QSet iteration order is not modeled. -/
def loadedCount (members : List Nat) : Nat := members.length
def bindingCount (members : List Nat) : Nat := members.eraseDups.length
def savedCount (known members : List Nat) : Nat :=
  (members.filter known.contains).eraseDups.length

def collapsedAfterLoad (prior incoming : Bool) : Bool := prior || incoming
/-- Already admitted readable directories; no arbitrary directory walker,
    permissions, or general symlink security model. -/
def discovered (hasConfig internalSiblingAlias : Bool) : Bool := hasConfig && !internalSiblingAlias

theorem rename_keeps_identity_separate : (renameLabel "a" "b" true).2 = "b" := rfl
theorem other_role_cannot_rename (a b : String) : renameLabel a b false = (false,a) := rfl
theorem first_uuid_assignment_uses_alias : insertionKey false true false = 1 := rfl
theorem existing_canonical_slot_uses_directory : insertionKey true true false = 0 := rfl
theorem candidate_always_uses_directory (present alias : Bool) : insertionKey present alias true = 0 := by simp [insertionKey]
theorem first_match_can_choose_uuid_before_directory :
    firstMatch 0 2 [⟨1,0,2⟩,⟨2,2,3⟩] = 1 := by decide
theorem typed_directory_selects_second_owner :
    uniqueMatch 1 2 [⟨1,0,2⟩,⟨2,2,3⟩] = 2 := by decide
theorem ambiguous_untyped_query_is_distinct :
    uniqueMatch 0 2 [⟨1,0,2⟩,⟨2,2,3⟩] = 3 := by decide
theorem failed_trash_still_removes_group : removeText true false = "0|0" := rfl
theorem failed_main_restore_loses_current_history : undoText true false true = "0|0|0" := rfl
theorem no_history_is_success_without_work : undoText false false false = "1|0|0" := rfl
theorem candidate_main_failure_keeps_reference (n : Nat) : advance ⟨true,n⟩ false true = ⟨true,n⟩ := rfl
theorem partial_shortcut_keeps_remaining_reference : canForget (advance ⟨true,1⟩ true false) = false := rfl
theorem retry_does_not_require_another_main_move : advance ⟨false,1⟩ false true = ⟨false,0⟩ := rfl
theorem all_observed_restores_allow_forgetting : canForget (advance ⟨true,1⟩ true true) = true := rfl
theorem unprobed_save_skips_writer (good : Bool) : saveText false good = "skipped|0" := rfl
theorem duplicate_group_entries_count_twice : loadedCount [1,1] = 2 := rfl
theorem duplicate_bindings_save_once : savedCount [1,2] [1,1] = 1 := by decide
theorem unknown_member_does_not_save : savedCount [1,2] [3] = 0 := by decide
theorem load_does_not_clear_collapsed_marker : collapsedAfterLoad true false = true := rfl
theorem sibling_alias_is_not_discovered (config : Bool) : discovered config true = false := by simp [discovered]

end ApplicationStudy.PrismLibrary
