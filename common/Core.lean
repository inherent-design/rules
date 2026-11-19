import Std

namespace Rules

/-- An absent relational witness is distinct from a known value of zero. -/
abbrev Query (A B : Type) := A → Option B

def follow (f : Query A B) (g : Query B C) : Query A C := fun a => (f a).bind g

theorem follow_assoc (f : Query A B) (g : Query B C) (h : Query C D) :
    follow (follow f g) h = follow f (follow g h) := by
  funext a
  cases e : f a <;> simp [follow, e]

/-- A revision vector has a clock per owner. A projection declares every input
    it depends on, including visibility and policy when those affect the view. -/
abbrev Clock (K : Type) := K → Nat
def Fresh (deps : List K) (seen now : Clock K) := ∀ k ∈ deps, seen k = now k

theorem joined_fresh (a b : List K) (s t : Clock K) :
    Fresh (a ++ b) s t ↔ Fresh a s t ∧ Fresh b s t := by
  simp [Fresh, List.mem_append, or_imp, forall_and]

theorem unrelated_update [DecidableEq K] (deps : List K) (k : K)
    (away : k ∉ deps) (s : Clock K) (n : Nat) :
    Fresh deps s (fun j => if j = k then n else s j) := by
  intro j hj
  have h : j ≠ k := fun eq => away (eq ▸ hj)
  simp [h]

theorem changed_input (deps : List K) (k : K) (h : k ∈ deps)
    (s t : Clock K) (diff : s k ≠ t k) : ¬ Fresh deps s t :=
  fun fresh => diff (fresh k h)

/-- Capacity quantities share a unit within one invocation. -/
def admit (used cost limit : Nat) : Bool := decide (used + cost ≤ limit)

theorem nested_budget (used cost inner outer : Nat) :
    admit used cost (min inner outer) = (admit used cost inner && admit used cost outer) := by
  by_cases a : used + cost ≤ inner <;> by_cases b : used + cost ≤ outer <;> simp [admit, Nat.le_min, a, b]

/-- The observation boundary includes failures and elapsed-time events when
    those are visible to the decision function. -/
def replay (step : S → E → S) (start : S) (events : List E) : S :=
  events.foldl step start

theorem replay_chunks (step : S → E → S) (s : S) (xs ys : List E) :
    replay step s (xs ++ ys) = replay step (replay step s xs) ys := by
  simp [replay, List.foldl_append]

/-- A one-step commuting square is the obligation for replacing an adapter
    or analyzing a trace at coarser resolution. -/
theorem project_replay (micro : S → E → S) (macroStep : T → F → T)
    (view : S → T) (decode : E → F)
    (square : ∀ s e, view (micro s e) = macroStep (view s) (decode e))
    (xs : List E) (s : S) :
    view (replay micro s xs) = replay macroStep (view s) (xs.map decode) := by
  induction xs generalizing s with
  | nil => rfl
  | cons x xs ih => exact (ih (micro s x)).trans (by rw [square]; rfl)

/-- Existential composition keeps one-to-many evidence, unlike a partial lookup. -/
def joinRel (r : A → B → Prop) (s : B → C → Prop) (a : A) (c : C) :=
  ∃ b, r a b ∧ s b c

theorem join_assoc (r : A → B → Prop) (s : B → C → Prop) (t : C → D → Prop)
    (a : A) (d : D) : joinRel (joinRel r s) t a d ↔ joinRel r (joinRel s t) a d := by
  constructor
  · rintro ⟨c, ⟨b, ab, bc⟩, cd⟩
    exact ⟨b, ab, c, bc, cd⟩
  · rintro ⟨b, ab, c, bc, cd⟩
    exact ⟨c, ⟨b, ab, bc⟩, cd⟩

structure Snapshot (A : Type) where
  revision : Nat
  value : A
  deriving DecidableEq, Repr

def commit (old : Snapshot A) (expected : Nat) (candidate : Option A) :=
  if old.revision = expected then
    candidate.elim old (fun a => ⟨expected + 1, a⟩)
  else old

theorem stale_commit (old : Snapshot A) (e : Nat) (v : Option A)
    (h : old.revision ≠ e) : commit old e v = old := by simp [commit, h]

theorem missing_holds (old : Snapshot A) (e : Nat) : commit old e none = old := by
  simp [commit, Option.elim]

end Rules

namespace Rules
/-- Identical-shaped intervals from different frames cannot be passed to
    contains without an explicit coordinate/clock conversion. Half-open. -/
structure Interval (frame : Type) where
  lo : Nat
  hi : Nat
  ordered : lo ≤ hi

def contains (outer inner : Interval f) := outer.lo ≤ inner.lo ∧ inner.hi ≤ outer.hi
theorem nested_contains (a b c : Interval f) (ab : contains a b) (bc : contains b c) :
    contains a c := ⟨Nat.le_trans ab.1 bc.1, Nat.le_trans bc.2 ab.2⟩

/-- A time-dependent query may expire even when no source revision changes. -/
def reusable (deps : List K) (seen now : Clock K) (clock : Nat) (expires : Option Nat) :=
  Fresh deps seen now ∧ ∀ deadline ∈ expires, clock < deadline

theorem expiry_requires_refresh (deps : List K) (s : Clock K) (t : Nat) :
    ¬ reusable deps s s t (some t) := by
  intro h
  exact (Nat.lt_irrefl t) (h.2 t rfl)
end Rules

namespace Rules
/-- Two hidden microstates with the same view and visibly different successors
    rule out *every* deterministic macro step on that view. -/
theorem loss_obstruction (view : S → T) (step : S → S) (a b : S)
    (same : view a = view b) (different : view (step a) ≠ view (step b)) :
    ¬ ∃ coarse : T → T, ∀ s, view (step s) = coarse (view s) := by
  rintro ⟨coarse, square⟩
  apply different
  rw [square a, square b, same]

inductive Evidence | yes | no | unknown deriving DecidableEq, Repr
def both : Evidence → Evidence → Evidence
  | .no, _ | _, .no => .no
  | .yes, .yes => .yes
  | _, _ => .unknown
theorem both_assoc (x y z : Evidence) : both (both x y) z = both x (both y z) := by
  cases x <;> cases y <;> cases z <;> rfl

end Rules
