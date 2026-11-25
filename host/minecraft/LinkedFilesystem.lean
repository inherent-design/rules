import common.FilesystemGuard
namespace Host.Minecraft.LinkedFilesystem

/-- Canonical keys within the selected virtual namespace,not backing-file IDs. -/
def logicalSame (sameFilesystem sameNode : Bool) : Bool := sameFilesystem && sameNode
/-- checkAccess uses the path's present virtual contents;read resolves relative paths. -/
def entryExists (absolute registered : Bool) : Bool := absolute && registered
/-- Selected one-byte owned backing states:0 absent,1 A,2 B. Permission/other IO
    errors and arbitrary byte strings are outside this comparison. -/
def read (mapped : Bool) (backing : Nat) : Nat :=
  if !mapped || backing == 0 then 0 else if backing == 1 then 3 else 4
/-- Outcome0 NoSuchFile;1 false;2 true;3 A;4 B;5 size zero;6 unsupported write. -/
def evaluate (kind : Nat) (sameFilesystem sameNode absolute registered mapped : Bool) (backing : Nat) : Nat :=
  if kind == 0 then 2
  else if kind == 1 then (if logicalSame sameFilesystem sameNode then 2 else 1)
  else if kind == 2 then (if entryExists absolute registered then 2 else 1)
  else if kind == 3 then read mapped backing
  else if kind == 4 then (if registered then 5 else 0)
  else if kind == 5 then 6
  else 0

theorem other_filesystem_is_not_same (node : Bool) : logicalSame false node = false := by simp [logicalSame]
theorem distinct_logical_nodes_are_not_same (fs : Bool) : logicalSame fs false = false := by simp [logicalSame]
theorem same_logical_key : logicalSame true true = true := rfl
theorem absent_backing_does_not_change_logical_equality :
    logicalSame true true = true ∧ read true 0 = 0 := by decide
theorem registered_absolute_entry_exists : entryExists true true = true := rfl
theorem unmapped_entry_absent (absolute : Bool) : entryExists absolute false = false := by simp [entryExists]
theorem relative_existence_differs_from_read : entryExists false true = false ∧ read true 1 = 3 := by decide
theorem virtual_existence_does_not_prove_backing : entryExists true true = true ∧ read true 0 = 0 := by decide
theorem external_bytes_change_read : read true 1 = 3 ∧ read true 2 = 4 := by decide
theorem deletion_changes_read : read true 2 = 4 ∧ read true 0 = 0 := by decide
theorem unmapped_read_refuses (backing : Nat) : read false backing = 0 := by simp [read]
theorem readonly_flag_does_not_freeze_backing :
    evaluate 0 false false false false false 0 = 2 ∧ read true 1 ≠ read true 2 := by decide
theorem close_request_does_not_revoke_selected_fs : evaluate 0 false false false false false 0 = 2 := by decide
theorem write_open_refuses : evaluate 5 false false true true false 1 = 6 := by decide
theorem dummy_size_not_backing_data : evaluate 4 false false true true false 1 = 5 ∧ read true 1 = 3 := by decide
theorem metadata_cannot_determine_read :
    ¬ ∃ f : Bool → Nat, ∀ state ∈ ([0,1,2] : List Nat), read true state = f (entryExists true true) := by
  rintro ⟨f,h⟩
  have a := h 1 (by simp)
  have b := h 2 (by simp)
  simp [read] at a b
  omega
theorem logical_evidence_needs_physical_scope (r : Host.FilesystemGuard.Evidence) :
    Host.FilesystemGuard.preflight {r with policyAllows := true,scopeMatches := false} = 1 :=
  Host.FilesystemGuard.wrong_scope_requires_evidence r
end Host.Minecraft.LinkedFilesystem
