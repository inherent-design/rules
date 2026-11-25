import Std
namespace Host.Minecraft.ServerPacks

/-- Selected single-record serial branches. These return observation projections,
    not a complete manager, callback scheduler, network or pack filesystem model.
    prompt:0 pending/1 allowed/2 declined; download:0 requested/1 pending/2 done;
    activation:0 inactive/1 pending/2 active; reason:0 none/1 declined/2 download
    failed/3 activation failed/4 discarded/5 server removed. -/
def firstReason (old next : Nat) : Nat := if old == 0 then next else old
def wanted (accepted download reason : Nat) : Bool := accepted == 1 && download == 2 && reason == 0
def waiting (present accepted download reason : Nat) : Bool := present == 1 && accepted == 1 && download != 2 && reason == 0
def reloadKind (present accepted download activation reason : Nat) : Nat :=
  if present == 0 || waiting present accepted download reason || activation == 1 then 0
  else if wanted accepted download reason && activation == 0 then 1
  else if !(wanted accepted download reason) && activation == 2 then 2 else 0
def cleanup (present activation reason : Nat) : Bool := present == 1 && activation == 0 && reason != 0

def decideBranch (op prompt present accepted download activation reason load : Nat) : List Nat :=
  match op with
  | 0 | 1 =>
    if prompt == 2 then [1,0,0,0]
    else [0,(prompt == 1).toNat,if op == 1 then 2 else 0,1]
  | 2 =>
    let grant := present == 1 && accepted == 0 && reason == 0
    [1,if grant then 1 else accepted,grant.toNat,1]
  | 3 => [2,accepted,if present == 1 && accepted == 0 then firstReason reason 1 else reason,present]
  | 4 => [0,accepted,reason,0]
  | 5 =>
    let reload := reloadKind present accepted download activation reason
    let nextActivation := if reload != 0 then 1 else activation
    let gone := cleanup present nextActivation reason
    [(waiting present accepted download reason && download == 0).toNat,(reload != 0).toNat,
     if gone || present == 0 then 0 else nextActivation,gone.toNat]
  | 6 => [if present == 1 then 2 else 0,(present == 1 && reason == 0).toNat,1,0]
  | 7 => [if present == 1 && activation != 2 then firstReason reason 2 else reason,1,0,0]
  | 8 => [if present == 0 then 0 else if load == 1 then 2 else if activation == 1 then 0 else activation,
          (load == 1 && present == 1 && reason == 0).toNat,1,0]
  | 9 => [if activation == 1 then 0 else activation,
          if present == 0 then 0 else if activation == 1 then firstReason reason 3 else if activation == 0 then firstReason reason 4 else reason,1,0]
  | 10 => [if activation == 1 then 0 else activation,reason,0,0]
  | 11 | 12 => [if present == 1 then firstReason reason 5 else 0,
                (op == 12 || (present == 1 && reason == 0)).toNat,activation,0]
  | _ => []

theorem first_reason_preserved (old next : Nat) (h : old ≠ 0) : firstReason old next = old := by simp [firstReason,h]
theorem first_reason_set (next : Nat) : firstReason 0 next = next := rfl
theorem no_acceptance_no_wanted (download reason : Nat) : wanted 0 download reason = false := rfl
theorem incomplete_is_not_wanted (accepted reason : Nat) : wanted accepted 1 reason = false := by simp [wanted]
theorem pending_activation_blocks_reload (present accepted download reason : Nat) : reloadKind present accepted download 1 reason = 0 := by simp [reloadKind]
theorem pending_activation_keeps_removed_record (reason : Nat) : cleanup 1 1 reason = false := rfl
theorem active_activation_keeps_removed_record (reason : Nat) : cleanup 1 2 reason = false := rfl
theorem removed_inactive_can_leave_manager : cleanup 1 0 5 = true := rfl
theorem local_bytes_do_not_grant_consent : decideBranch 1 0 0 0 0 0 0 0 = [0,0,2,1] := rfl
theorem declined_push_creates_no_record : decideBranch 0 2 0 0 0 0 0 0 = [1,0,0,0] := rfl
theorem accepted_rejection_is_not_revocation : decideBranch 3 1 1 1 2 0 0 0 = [2,1,0,1] := rfl
theorem prompt_reset_is_not_revocation : decideBranch 4 1 1 1 0 0 0 0 = [0,1,0,0] := rfl
theorem removed_active_needs_unload : reloadKind 1 1 2 2 5 = 2 := rfl
theorem ordinary_failure_marks_activation_failed : decideBranch 9 1 1 1 2 1 0 1 = [0,3,1,0] := rfl
theorem recovery_failure_does_not_mark_removed : decideBranch 10 1 1 1 2 1 0 1 = [0,0,0,0] := rfl
theorem late_download_has_no_downloaded_report : decideBranch 6 1 0 0 0 0 0 0 = [0,0,1,0] := rfl
theorem removed_reload_has_no_applied_report : decideBranch 8 1 1 1 2 1 5 1 = [2,0,1,0] := rfl
end Host.Minecraft.ServerPacks
