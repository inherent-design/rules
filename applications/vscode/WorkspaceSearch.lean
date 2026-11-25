namespace ApplicationStudy.VscodeWorkspaceSearch

/-- URI identities are admitted by the fixture adapter. This is not a generic
    path normalizer, host case policy, or remote workspace decoder. -/
structure Workspace where
  confirmed : List String
  provisional : Option (List String) := none
  deriving Repr, BEq, DecidableEq

def visible (w : Workspace) : List String := w.provisional.getD w.confirmed

def proposedFolders (w : Workspace) (start count : Nat) (additions : List String) : List String :=
  w.confirmed.take start ++ additions ++ w.confirmed.drop (start + count)

/-- Additions have already passed URI validation and source duplicate filtering.
    Names, invalid raw entries, and platform identity normalization are outside
    this fixture projection. -/
def request (w : Workspace) (start count : Nat) (additions : List String) : Bool × Workspace :=
  let proposed := proposedFolders w start count additions
  if w.provisional.isSome || start + count > w.confirmed.length ||
      (count == 0 && additions.isEmpty) || proposed.eraseDups.length != proposed.length ||
      proposed == w.confirmed then
    (false, w)
  else (true, { w with provisional := some proposed })

/-- Source confirmation updates the confirmed API view. It is not a filesystem
    durability receipt. Failure clears a provisional view without committing it. -/
def confirm (w : Workspace) : Workspace := ⟨visible w, none⟩
def refuse (w : Workspace) : Workspace := { w with provisional := none }

inductive Origin | disk | buffer
  deriving Repr, BEq, DecidableEq

structure Resource where
  identity : String
  root : String
  present : Bool
  excluded : Bool
  providerMatch : Bool
  openEligible : Bool
  openMatch : Bool
  deriving Repr

/-- Literal/glob/URI membership and match facts are independently observed
    adapter inputs. This model studies result selection and masking, not rg,
    regex, encoding, directory walking, or the general glob implementation. -/
def providerEligible (roots : List String) (respectFileExcludes : Bool) (r : Resource) : Bool :=
  r.present && roots.contains r.root && (!respectFileExcludes || !r.excluded)

def fileResults (roots : List String) (respectFileExcludes : Bool) (rs : List Resource) : List String :=
  (rs.filter (providerEligible roots respectFileExcludes)).map (·.identity)

def fileQuery (roots : List String) (respectFileExcludes cancelled : Bool) (rs : List Resource) : List String :=
  if cancelled then [] else fileResults roots respectFileExcludes rs

/-- Some false represents an observed open editor with no match, not absence
    of an open-editor observation. The asynchronous disk result stays masked. -/
def textResult (roots : List String) (respectFileExcludes : Bool) (r : Resource) : Option Origin :=
  if r.openEligible then
    if r.openMatch then some .buffer else none
  else if providerEligible roots respectFileExcludes r && r.providerMatch then some .disk
  else none

def textResults (roots : List String) (respectFileExcludes : Bool) (rs : List Resource) : List (String × Origin) :=
  rs.filterMap fun r => (textResult roots respectFileExcludes r).map (r.identity, ·)

/-- Caller-planned ranges and RPC submission have different version bases.
    The present source carries the submission version into ResourceTextEdit. -/
def currentVersionGuard (submitted actual : Nat) : Bool := submitted == actual
def plannedVersionGuard (planned submitted actual : Nat) : Bool :=
  planned == submitted && submitted == actual

def replaceRange (text : List Char) (start stop : Nat) (replacement : List Char) : List Char :=
  text.take start ++ replacement ++ text.drop stop

/-- Abstract execution groups are already prepared by their owner. The
    lifecycle retains earlier completed groups on a later refusal. Group
    preparation/validation and its filesystem effects need native evidence. -/
structure Group where
  admitted : Bool
  effects : List String
  deriving Repr

def runGroups : List Group → Bool × List String
  | [] => (true, [])
  | g :: rest =>
    if !g.admitted then (false, [])
    else
      let later := runGroups rest
      (later.1, g.effects ++ later.2)

theorem pending_refuses_another_request (w : Workspace) (s c : Nat) (a : List String)
    (h : w.provisional.isSome = true) : request w s c a = (false, w) := by simp [request, h]

theorem request_does_not_confirm (w : Workspace) (s c : Nat) (a : List String) :
    (request w s c a).2.confirmed = w.confirmed := by
  unfold request
  dsimp only
  split <;> rfl

theorem refusal_restores_confirmed_view (w : Workspace) : visible (refuse w) = w.confirmed := rfl

theorem confirmation_clears_pending (w : Workspace) : (confirm w).provisional = none := rfl

theorem confirmation_preserves_visible_view (w : Workspace) : visible (confirm w) = visible w := rfl

theorem precancelled_query_has_no_results (roots : List String) (respect : Bool) (rs : List Resource) :
    fileQuery roots respect true rs = [] := rfl

theorem observed_no_match_masks_disk (roots : List String) (respect : Bool) (r : Resource)
    (e : r.openEligible = true) (m : r.openMatch = false) : textResult roots respect r = none := by
  simp [textResult, e, m]

theorem eligible_open_match_wins (roots : List String) (respect : Bool) (r : Resource)
    (e : r.openEligible = true) (m : r.openMatch = true) : textResult roots respect r = some .buffer := by
  simp [textResult, e, m]

theorem excluded_disk_is_not_returned (roots : List String) (r : Resource)
    (e : r.openEligible = false) (x : r.excluded = true) : textResult roots true r = none := by
  simp [textResult, providerEligible, e, x]

theorem unavailable_disk_is_not_returned (roots : List String) (respect : Bool) (r : Resource)
    (e : r.openEligible = false) (x : r.present = false) : textResult roots respect r = none := by
  simp [textResult, providerEligible, e, x]

theorem matching_submission_can_have_stale_plan :
    currentVersionGuard 3 3 = true ∧ plannedVersionGuard 2 3 3 = false := by decide

theorem range_is_not_rebased_by_version_admission :
    replaceRange "prefix needle base\n".toList 0 6 "fixed".toList = "fixed needle base\n".toList := by decide

theorem failed_group_retains_earlier_effect :
    runGroups [⟨true, ["created"]⟩, ⟨false, []⟩, ⟨true, ["later"]⟩] = (false, ["created"]) := by decide

theorem first_refusal_has_no_prior_group_effect (rest : List Group) (effects : List String) :
    runGroups (⟨false, effects⟩ :: rest) = (false, []) := rfl

theorem source_request_can_expose_unconfirmed_membership :
    let result := request ⟨["a", "b"], none⟩ 2 0 ["c"]
    result.1 = true ∧ visible result.2 = ["a", "b", "c"] ∧ result.2.confirmed = ["a", "b"] := by decide

theorem duplicate_identity_is_refused :
    request ⟨["a", "b", "c"], none⟩ 3 0 ["c"] = (false, ⟨["a", "b", "c"], none⟩) := by decide

end ApplicationStudy.VscodeWorkspaceSearch
