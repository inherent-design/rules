import applications.restic.Selection
import applications.restic.Retention

namespace ApplicationStudy.ResticPolicyJoin

def forgetMany (ids : List String) (repo : Restic.Repository) : Restic.Repository :=
  ids.foldl (fun r id => Restic.forget id r) repo

structure Outcome where
  planned : List String
  removed : List String
  snapshots : List String
  available : List String
  prunePhase : Bool
  code : Nat
  deriving BEq, DecidableEq, Repr

/-- Selected keep-last-one/host-path recipe. The caller supplies matching exact
snapshot IDs and a closed file-data reachability projection. Refused IDs are
backend outcomes, not an inferred absence. Partial refusal is source-modeled;
the native fixture exercises all-refused and successful removal. -/
def run (metadata : List ResticSelection.Snapshot) (repo : Restic.Repository) (dry : Bool)
    (refused : List String) : Outcome :=
  let planned := (ResticSelection.remove metadata ResticSelection.hostPaths []).map (·.id)
  let removed := if dry then [] else planned.filter (fun id => !refused.contains id)
  let failed := !dry && planned.any refused.contains
  let changed := forgetMany removed repo
  let prunePhase := !failed && !planned.isEmpty
  let final := if !dry && prunePhase then Restic.prune true changed else changed
  { planned := planned
    removed := removed
    snapshots := final.snapshots.map (·.id)
    available := final.availableData
    prunePhase := prunePhase
    code := if failed then 3 else 0 }

theorem forget_many_preserves_backing (ids : List String) (r : Restic.Repository) :
    (forgetMany ids r).availableData = r.availableData := by
  induction ids generalizing r with
  | nil => rfl
  | cons head tail ih => exact ih (Restic.forget head r)

theorem preview_preserves_backing (m : List ResticSelection.Snapshot) (r : Restic.Repository) (f : List String) :
    (run m r true f).available = r.availableData := rfl
theorem preview_preserves_snapshots (m : List ResticSelection.Snapshot) (r : Restic.Repository) (f : List String) :
    (run m r true f).snapshots = r.snapshots.map (·.id) := rfl
theorem preview_removes_no_references (m : List ResticSelection.Snapshot) (r : Restic.Repository) (f : List String) :
    (run m r true f).removed = [] := rfl
theorem every_removed_id_was_planned (m : List ResticSelection.Snapshot) (r : Restic.Repository) (d : Bool)
    (f : List String) (id : String) (h : id ∈ (run m r d f).removed) :
    id ∈ (run m r d f).planned := by
  cases d with
  | true => simp [run] at h
  | false => exact (List.mem_filter.mp h).1
theorem failed_removal_has_no_prune_phase (m : List ResticSelection.Snapshot) (r : Restic.Repository)
    (f : List String) (h : ((ResticSelection.remove m ResticSelection.hostPaths []).map (·.id)).any f.contains = true) :
    (run m r false f).prunePhase = false := by simp [run, h]
theorem failed_removal_preserves_backing (m : List ResticSelection.Snapshot) (r : Restic.Repository)
    (f : List String) (h : ((ResticSelection.remove m ResticSelection.hostPaths []).map (·.id)).any f.contains = true) :
    (run m r false f).available = r.availableData := by
  simp [run, h, forget_many_preserves_backing]
theorem planned_json_does_not_depend_on_backend_result
    (m : List ResticSelection.Snapshot) (r : Restic.Repository) (d : Bool) (a b : List String) :
    (run m r d a).planned = (run m r d b).planned := rfl

end ApplicationStudy.ResticPolicyJoin
