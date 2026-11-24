import Lean

namespace ApplicationStudy.EmpackInitialization

/-- A same-root, admitted-capability protocol projection. File presence is not a
    lease, API return is not command acknowledgement, and SIGKILL is not reboot. -/
structure Actor where
  variant : Nat := 0 -- 0 current operation.lock; 1 private metadata-lock candidate
  phase : Nat := 0 -- fresh, locked, allocated, returned, killed
  api : Nat := 0 -- pending, success, unassociated, busy
  command : Nat := 0 -- running, acknowledged, killed
  scratch : Bool := false
  found : Nat := 0 -- not a lookup, absent, present
  deriving BEq, DecidableEq, Repr
structure State where
  slot : Bool := false
  operation : Bool := false
  metadata : Bool := false
  association : Bool := false -- externally admitted matching schema-1 record
  unknown : Bool := false
  actors : List Actor := []
  writes : Nat := 0
  valid : Bool := true
  deriving BEq, DecidableEq, Repr
structure Event where
  kind : Nat -- 0..5 start/allocate/finish/kill/ack/lookup; 6..7 awaited init/lookup
  actor : Nat
  variant : Nat := 0
  deriving BEq, DecidableEq, Repr, Lean.FromJson
def holding (a : Actor) : Bool := a.phase == 1 || a.phase == 2
def held (s : State) (variant : Nat) : Bool :=
  s.actors.any (fun a => holding a && a.variant == variant)
def scratch (s : State) : Bool := s.actors.any (·.scratch)
def unassociated (s : State) : Bool :=
  !s.association && (s.operation || scratch s || s.unknown)
def put (s : State) (n : Nat) (a : Actor) : State := {s with actors := s.actors.set n a}
private def reject (s : State) : State := {s with valid := false}
private def returned (a : Actor) (api : Nat) (found : Nat := 0) : Actor :=
  {a with phase := 3, api := api, found := found}
def primitive (s : State) (e : Event) : State :=
  match s.actors[e.actor]? with
  | none => reject s
  | some a =>
    if !s.valid || e.variant > 1 then reject s else
    match e.kind with
    | 0 | 5 =>
      if a.phase != 0 then reject s else
      let a := {a with variant := e.variant}
      if unassociated s then put s e.actor (returned a 2) else
      if e.kind == 5 then put s e.actor (returned a 1 (if s.association then 2 else 1)) else
      if s.association then put s e.actor (returned a 1) else
      let s := {s with
        slot := true
        operation := s.operation || e.variant == 0
        metadata := s.metadata || e.variant == 1}
      if held s e.variant then put s e.actor (returned a 3)
      else put s e.actor {a with phase := 1}
    | 1 =>
      if a.phase != 1 || s.association then reject s
      else put s e.actor {a with phase := 2, scratch := true}
    | 2 =>
      if !holding a || (!s.association && a.phase != 2) then reject s else
      -- The second read can accept another writer's already-published record.
      let s := {s with association := true, writes := s.writes + (if s.association then 0 else 1)}
      put s e.actor {(returned a 1) with scratch := false}
    | 3 =>
      if a.phase == 0 || a.phase == 4 || a.command != 0 then reject s
      else put s e.actor {a with phase := 4, command := 2}
    | 4 =>
      if a.phase != 3 || a.command != 0 then reject s
      else put s e.actor {a with command := 1}
    | _ => reject s
/-- A fully awaited fixture command, with successful IO abstracted. Its branch
    comes from protocol state, never from the recorded expected API result. -/
def step (s : State) (e : Event) : State :=
  if e.kind == 6 || e.kind == 7 then
    let s := primitive s {e with kind := if e.kind == 6 then 0 else 5}
    let s := match s.actors[e.actor]? with
      | some a => if a.phase == 1 then
          let s := if s.association then s else primitive s {e with kind := 1}
          primitive s {e with kind := 2}
        else s
      | none => s
    primitive s {e with kind := 4}
  else primitive s e
def run (s : State) (events : List Event) : State := events.foldl step s
def mask (s : State) : Nat :=
  (if s.slot then 1 else 0) + (if s.operation then 2 else 0) +
  (if s.metadata then 4 else 0) + (if scratch s then 8 else 0) +
  (if s.association then 16 else 0) + (if s.unknown then 32 else 0)
def leases (s : State) : Nat := (if held s 0 then 1 else 0) + (if held s 1 then 2 else 0)

private def base : State := {actors := [{},{}]}
private def oldLocked := run base [⟨0,0,0⟩]
private def candidateLocked := run base [⟨0,0,1⟩]
theorem current_post_lock_kill_strands_retry :
    (run oldLocked [⟨3,0,0⟩,⟨0,1,0⟩]).actors[1]?.map (·.api) = some 2 := by decide
theorem metadata_only_post_lock_kill_allows_retry :
    (run candidateLocked [⟨3,0,0⟩,⟨0,1,1⟩]).actors[1]?.map (·.phase) = some 1 := by decide
theorem metadata_lock_does_not_fix_temporary_window :
    (run candidateLocked [⟨1,0,0⟩,⟨3,0,0⟩,⟨0,1,1⟩]).actors[1]?.map (·.api) = some 2 := by decide
theorem current_temporary_window_also_refuses :
    (run oldLocked [⟨1,0,0⟩,⟨3,0,0⟩,⟨5,1,0⟩]).actors[1]?.map (·.api) = some 2 := by decide
theorem kill_releases_lease_not_file :
    leases (step candidateLocked ⟨3,0,0⟩) = 0 ∧ mask (step candidateLocked ⟨3,0,0⟩) = 5 := by decide
theorem same_metadata_lock_contender_is_busy :
    (step candidateLocked ⟨0,1,1⟩).actors[1]?.map (·.api) = some 3 := by decide
theorem same_current_contender_refuses_before_lock :
    (step oldLocked ⟨0,1,0⟩).actors[1]?.map (·.api) = some 2 := by decide
theorem distinct_protocol_locks_can_coexist :
    leases (step candidateLocked ⟨0,1,0⟩) = 3 := by decide
theorem current_first_blocks_fresh_candidate :
    (step oldLocked ⟨0,1,1⟩).actors[1]?.map (·.api) = some 2 := by decide
private def both := step candidateLocked ⟨0,1,0⟩
theorem admitted_candidate_can_finish_after_current_dies :
    (run both [⟨3,1,0⟩,⟨1,0,0⟩,⟨2,0,0⟩]).association = true := by decide
theorem both_die_leaves_unknown_current_footprint :
    unassociated (run both [⟨3,0,0⟩,⟨3,1,0⟩]) = true := by decide
theorem second_read_accepts_existing_without_rewrite :
    (run both [⟨1,1,0⟩,⟨2,1,0⟩,⟨4,1,0⟩,⟨2,0,0⟩]).writes = 1 := by decide
theorem API_return_survives_killed_command :
    let s := run oldLocked [⟨1,0,0⟩,⟨2,0,0⟩,⟨3,0,0⟩]
    s.association = true ∧ s.actors[0]?.map (·.api) = some 1 ∧
    s.actors[0]?.map (·.command) = some 2 := by decide
theorem idempotent_start_never_adds_coordination_file :
    mask (step {base with slot := true, association := true} ⟨0,0,1⟩) = 17 := by decide
theorem unknown_bytes_are_not_recovery_authority :
    mask (step {base with slot := true, unknown := true} ⟨0,0,1⟩) = 33 ∧
    (step {base with slot := true, unknown := true} ⟨0,0,1⟩).association = false := by decide
theorem no_acknowledgement_before_API_return :
    (step oldLocked ⟨4,0,0⟩).valid = false := by decide
theorem dead_actor_cannot_publish :
    (run candidateLocked [⟨3,0,0⟩,⟨2,0,0⟩]).valid = false := by decide

/-- PROPOSED initialized-directory publication admission, not native behavior.
    The host must independently supply identity, root, no-replace, and sync facts.
    Private orphan retention/capacity and later recovery are not implemented here. -/
def proposedPublication (complete identity root hostReady : Bool) (target : Nat) : Nat :=
  if !(complete && identity && root && hostReady) then 0
  else if target == 0 then 1 else if target == 1 then 2 else 0
theorem proposed_unknown_target_is_never_replaced (c i r h : Bool) :
    proposedPublication c i r h 2 = 0 := by simp [proposedPublication]
theorem proposed_incomplete_private_image_is_not_published (i r h : Bool) (t : Nat) :
    proposedPublication false i r h t = 0 := by simp [proposedPublication]
theorem proposed_unverified_identity_is_not_published (c r h : Bool) (t : Nat) :
    proposedPublication c false r h t = 0 := by simp [proposedPublication]
theorem proposed_root_revalidation_is_required (c i h : Bool) (t : Nat) :
    proposedPublication c i false h t = 0 := by simp [proposedPublication]
theorem proposed_host_primitive_is_a_premise (c i r : Bool) (t : Nat) :
    proposedPublication c i r false t = 0 := by simp [proposedPublication]
theorem proposed_matching_existing_target_is_not_a_new_publication :
    proposedPublication true true true true 1 = 2 := by decide

end ApplicationStudy.EmpackInitialization
