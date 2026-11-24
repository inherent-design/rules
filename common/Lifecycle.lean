import common.Core
namespace Lifecycle

def draft (retained current writable : Bool) := (retained && current && writable).toNat
def execute (capable complete approved : Bool) := (capable && complete && approved).toNat
def saveStatus (confirmed newer : Bool) : Nat := if confirmed then (if newer then 1 else 0) else 2
def collect (covered saved undo plan active : Bool) := (covered && !(saved || undo || plan || active)).toNat
def retire (_closed ended : Bool) := ended.toNat
def consume (identity compatible covered : Bool) := (identity && compatible && covered).toNat
def finalized (receipt valid : Bool) := (receipt && valid).toNat

structure Project where
  revision : Nat
  refs : List Nat
  deriving DecidableEq, Repr

/-- Same-context transaction, with immutable asset identities backed by bytes. -/
def save (old : Project) (expected : Nat) (refs stored : List Nat) (writable : Bool) : Project :=
  if writable && old.revision == expected && refs.all (fun a => stored.contains a) then
    ⟨old.revision + 1, refs⟩
  else old
def Sound (p : Project) (stored : List Nat) := ∀ a ∈ p.refs, a ∈ stored

theorem save_preserves_sound (p : Project) (base : Nat) (refs stored : List Nat) (w : Bool)
    (old : Sound p stored) : Sound (save p base refs stored w) stored := by
  unfold save
  split
  · rename_i h
    intro a ha
    have all := (Bool.and_eq_true_iff.mp h).2
    simpa using List.all_eq_true.mp all a ha
  · exact old

theorem stale_save_holds (p : Project) (base : Nat) (r s : List Nat) (w : Bool)
    (stale : p.revision ≠ base) : save p base r s w = p := by simp [save,stale]

theorem only_one_base (p : Project) (a b stored : List Nat) (w : Bool)
    (first : (save p p.revision a stored w).revision = p.revision+1) :
    save (save p p.revision a stored w) p.revision b stored w = save p p.revision a stored w := by
  apply stale_save_holds
  omega

/-- Every source of retained custody contributes its transitive asset closure. -/
def gc (roots stored : List Nat) := stored.filter (fun a => roots.contains a)
theorem retained_survives (roots stored : List Nat) (a : Nat) (root : a ∈ roots) (present : a ∈ stored) :
    a ∈ gc roots stored := by simp [gc,root,present]
theorem orphan_removed (roots stored : List Nat) (a : Nat) (h : a ∉ roots) :
    a ∉ gc roots stored := by simp [gc,h]
theorem plan_keeps_asset (saved undo plans active stored : List Nat) (a : Nat)
    (held : a ∈ plans) (present : a ∈ stored) :
    a ∈ gc (saved ++ undo ++ plans ++ active) stored := by
  apply retained_survives _ _ _ _ present
  simp [held]
theorem repeated_gc (r s : List Nat) : gc r (gc r s) = gc r s := by
  simp [gc,List.filter_filter]

structure Editor where
  incarnation : Nat
  current : Nat
  saved : Nat
  deriving DecidableEq
def edit (e : Editor) : Editor := {e with current := e.current + 1}
def saveComplete (e : Editor) (receipt : Nat) : Editor := {e with saved := max e.saved receipt}
def dirty (e : Editor) := e.current ≠ e.saved

theorem late_save_keeps_edit (e : Editor) (ordered : e.saved ≤ e.current) :
    dirty (saveComplete (edit e) e.current) := by simp [dirty,saveComplete,edit]; omega
theorem receipt_monotonic (e : Editor) (r : Nat) : e.saved ≤ (saveComplete e r).saved := Nat.le_max_left _ _
theorem receipt_does_not_rewrite_buffer (e : Editor) (r : Nat) :
    (saveComplete e r).current = e.current := rfl

structure Work where
  closed : Bool
  lease : Bool
  ended : Bool
  deriving DecidableEq
def close (s : Work) : Work := {s with closed := true}
def finish (s : Work) : Work := {s with ended := true, lease := false}
theorem close_keeps_lease (s : Work) : (close s).lease = s.lease := rfl
theorem finish_then_close (s : Work) : close (finish s) = finish (close s) := rfl

structure SaveReceipt where
  document : Nat
  sourceRevision : Nat
  storeRevision : Nat
def acknowledge (e : Editor) (r : SaveReceipt) : Editor :=
  if r.document = e.incarnation ∧ r.sourceRevision ≤ e.current then
    saveComplete e r.sourceRevision else e
theorem foreign_document_keeps_editor (e : Editor) (r : SaveReceipt)
    (h : r.document ≠ e.incarnation) : acknowledge e r = e := by simp [acknowledge,h]
theorem storage_counter_is_separate (e : Editor) (document source a b : Nat) :
    acknowledge e ⟨document,source,a⟩ = acknowledge e ⟨document,source,b⟩ := rfl

/-- Resource identity includes its namespace, even when a display name collides. -/
structure Resource where
  owner : Nat
  key : Nat
  deriving DecidableEq
def lookup (want : Resource) (view : List (Resource × Nat)) :=
  (view.find? (fun row => row.1 == want)).map (·.2)
example : lookup ⟨1,7⟩ [(⟨2,7⟩,8)] = none := by decide
example : save ⟨0,[]⟩ 0 [7] [] true = ⟨0,[]⟩ := by decide
example : save ⟨0,[]⟩ 0 [7] [7] true = ⟨1,[7]⟩ := by decide
end Lifecycle

namespace Lifecycle
structure Custody where
  project : Project
  stored : List Nat
  undo : List Nat
  plans : List Nat
  workers : List Nat
  recovery : List Nat
def roots (s : Custody) := s.project.refs ++ s.undo ++ s.plans ++ s.workers ++ s.recovery
def coherent (s : Custody) := ∀ a ∈ roots s, a ∈ s.stored

/-- These two atomic transitions share a root-publication/reclamation protocol.
    The persistent metadata and bytes may be on separate physical stores. -/
def publish (s : Custody) (base : Nat) (refs : List Nat) (writable : Bool) :=
  {s with project := save s.project base refs s.stored writable}
def reclaim (s : Custody) := {s with stored := gc (roots s) s.stored}

theorem reclaim_preserves_roots (s : Custody) (h : coherent s) : coherent (reclaim s) := by
  intro a ha
  apply retained_survives _ _ _ ha (h a ha)
theorem publication_preserves_roots (s : Custody) (base : Nat) (refs : List Nat)
    (writable : Bool) (h : coherent s) : coherent (publish s base refs writable) := by
  have projectSound : Sound s.project s.stored := by
    intro a ha
    apply h a
    simp [roots,ha]
  have result := save_preserves_sound s.project base refs s.stored writable projectSound
  intro a ha
  simp only [roots,publish,List.mem_append] at ha
  rcases ha with ((((hp|hu)|hl)|hw)|hr)
  · exact result a hp
  · exact h a (by simp [roots,hu])
  · exact h a (by simp [roots,hl])
  · exact h a (by simp [roots,hw])
  · exact h a (by simp [roots,hr])

inductive CustodyEvent
  | publish (base : Nat) (refs : List Nat) (writable : Bool)
  | reclaim
def custodyStep (s : Custody) : CustodyEvent → Custody
  | .publish base refs w => publish s base refs w
  | .reclaim => reclaim s
theorem coherent_trace (s : Custody) (events : List CustodyEvent) (h : coherent s) :
    coherent (Rules.replay custodyStep s events) := by
  induction events generalizing s with
  | nil => exact h
  | cons event rest ih =>
    apply ih
    cases event with
    | publish b r w => exact publication_preserves_roots s b r w h
    | reclaim => exact reclaim_preserves_roots s h

/-- A collector snapshot taken outside that protocol cannot justify deletion. -/
def staleGcCounterexample : Custody :=
  let before : Custody := ⟨⟨0,[]⟩,[7],[],[],[],[]⟩
  let saved := publish before 0 [7] true
  {saved with stored := gc (roots before) saved.stored}
example : ¬ coherent staleGcCounterexample := by
  simp [coherent,staleGcCounterexample,roots,publish,save,gc]
end Lifecycle


namespace Lifecycle
structure Edge where
  source : Nat
  target : Nat
  retaining : Bool
def retainingEdges (edges : List Edge) :=
  (edges.filter (·.retaining)).map (fun e => (e.source,e.target))
theorem history_edge_does_not_retain (edges : List Edge) (source target : Nat) :
    retainingEdges (⟨source,target,false⟩ :: edges) = retainingEdges edges := by
  simp [retainingEdges]
theorem unknown_roots_block_collection (s u p a : Bool) :
    collect false s u p a = 0 := rfl
end Lifecycle
