namespace ApplicationStudy.EmpackOwnership

structure Content where
  id : Nat
  bytes : Nat
  readonly : Bool
  executable : Bool
  deriving DecidableEq, Repr

def equivalent (left right : Content) (execBits : Bool) : Bool :=
  left.id == right.id && left.bytes == right.bytes && left.readonly == right.readonly &&
    (!execBits || left.executable == right.executable)

inductive Policy | managed | seed deriving DecidableEq, Repr
structure FileEntry where
  content : Content
  policy : Policy
  deriving Repr

inductive Observation | absent | directory | file (content : Content) deriving Repr
inductive Decision
  | unchanged | preserve | create (content : Content) | replace (content : Content) | remove
  | unowned | modified | wrongKind | seedOwnership
  deriving DecidableEq, Repr

/-- Pure current planner projection. Native root, links, worlds, choices,
    accepted overrides, grants, and expected-old publication are caller proofs. -/
def plan (previous : Option FileEntry) (current : Observation)
    (incoming : Option FileEntry) (execBits : Bool) : Decision :=
  match incoming with
  | none => match previous with
    | none => .preserve
    | some old => match old.policy with
      | .seed => .preserve
      | .managed => match current with
        | .absent => .unchanged
        | .directory => .wrongKind
        | .file actual => if equivalent actual old.content execBits then .remove else .modified
  | some next => match current with
    | .directory => .wrongKind
    | _ => match next.policy with
      | .seed => match current with
        | .absent => .create next.content
        | _ => .preserve
      | .managed =>
        if previous.any (fun old => old.policy == .seed) then .seedOwnership
        else match current with
          | .absent => .create next.content
          | .file actual => match previous with
            | none => .unowned
            | some old =>
              if equivalent actual next.content execBits then .unchanged
              else if equivalent actual old.content execBits then .replace next.content
              else .modified
          | .directory => .wrongKind

def label : Decision → String
  | .unchanged => "unchanged" | .preserve => "preserve" | .create _ => "create"
  | .replace _ => "replace" | .remove => "remove" | .unowned => "unowned"
  | .modified => "modified" | .wrongKind => "wrong-kind" | .seedOwnership => "seed-ownership"

theorem incoming_seed_preserves_existing (old : Option FileEntry) (actual next : Content) (caps : Bool) :
    plan old (.file actual) (some ⟨next, .seed⟩) caps = .preserve := rfl

theorem absent_seed_is_created (old : Option FileEntry) (next : Content) (caps : Bool) :
    plan old .absent (some ⟨next, .seed⟩) caps = .create next := rfl

theorem removing_seed_preserves_user_state (old : Content) (current : Observation) (caps : Bool) :
    plan (some ⟨old, .seed⟩) current none caps = .preserve := rfl

theorem unowned_removal_grants_no_deletion (current : Observation) (caps : Bool) :
    plan none current none caps = .preserve := rfl

theorem incoming_file_refuses_directory (old : Option FileEntry) (next : FileEntry) (caps : Bool) :
    plan old .directory (some next) caps = .wrongKind := rfl

theorem matching_bytes_do_not_adopt_unowned (next : Content) (caps : Bool) :
    plan none (.file next) (some ⟨next, .managed⟩) caps = .unowned := rfl

theorem seed_to_managed_requires_ownership_decision (old next actual : Content) (caps : Bool) :
    plan (some ⟨old, .seed⟩) (.file actual) (some ⟨next, .managed⟩) caps = .seedOwnership := rfl

theorem missing_seed_does_not_authorize_managed_adoption (old next : Content) (caps : Bool) :
    plan (some ⟨old, .seed⟩) .absent (some ⟨next, .managed⟩) caps = .seedOwnership := rfl

theorem executable_difference_ignored_without_capability (a b : Content) :
    equivalent a {b with executable := !b.executable} false = equivalent a b false := by
  simp [equivalent]

theorem equivalent_reflexive (a : Content) (caps : Bool) : equivalent a a caps = true := by
  simp [equivalent]

end ApplicationStudy.EmpackOwnership
