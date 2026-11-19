import empack.Model
namespace Empack.Workflow
open Rules
/-- IDs stand for normalized content fingerprints, including metadata relevant
    on this host. The three stages have different types so that a fetched
    artifact cannot be published before the integrity check. -/
structure Lock where
  selection : Nat
  content : Nat
  deriving DecidableEq
structure Verified where
  lock : Lock
  bytesId : Nat
  verified : bytesId = lock.content

def acquire (lock : Lock) (readBytes : Nat → Option Nat) : Option Verified := do
  let bytes ← readBytes lock.selection
  if h : bytes = lock.content then pure ⟨lock, bytes, h⟩ else none

structure Plan where
  base : Nat
  before : Option Nat
  after : Verified

def prepare (base : Snapshot (Option Nat)) (baseline : Option Nat) (payload : Verified) : Option Plan :=
  match planFile (baseline.map (fun n => ⟨n,.managed⟩)) (base.value.elim .absent .file)
      (some ⟨payload.bytesId,.managed⟩) with
  | .create _ | .replace _ => some ⟨base.revision,base.value,payload⟩
  | _ => none

def publish (world : Snapshot (Option Nat)) (p : Plan) :=
  commit world p.base (if world.value = p.before then some (some p.after.bytesId) else none)

theorem changed_disk_holds (world : Snapshot (Option Nat)) (p : Plan) (h : world.value ≠ p.before) :
    publish world p = world := by simp [publish,h,missing_holds]

def install (world : Snapshot (Option Nat)) (baseline : Option Nat)
    (lock : Lock) (reader : Nat → Option Nat) :=
  ((acquire lock reader).bind (prepare world baseline)).elim world (publish world)

example : install ⟨1,none⟩ none ⟨3,8⟩ (fun _ => some 8) = ⟨2,some 8⟩ := rfl
example : install ⟨1,none⟩ none ⟨3,8⟩ (fun _ => some 9) = ⟨1,none⟩ := rfl
example : install ⟨1,some 4⟩ (some 3) ⟨3,8⟩ (fun _ => some 8) = ⟨1,some 4⟩ := rfl
end Empack.Workflow

namespace Empack.Workflow
structure Channel where
  seq : Nat
  digest : Nat
  deriving DecidableEq

def observeChannel (saved incoming : Channel) (authentic : Bool) : Option Channel :=
  if authentic && (saved.seq < incoming.seq || saved == incoming) then some incoming else none

theorem floor (a b c : Channel) (ok : Bool) (h : observeChannel a b ok = some c) :
    a.seq ≤ c.seq := by
  unfold observeChannel at h
  split at h
  · rename_i g
    simp only [Option.some.injEq] at h
    subst c
    have g' : a.seq < b.seq ∨ a = b := by simpa using (Bool.and_eq_true_iff.mp g).2
    rcases g' with lt | eq
    · omega
    · simp [eq]
  · contradiction

example : observeChannel ⟨4,8⟩ ⟨4,9⟩ true = none := rfl
example : observeChannel ⟨4,8⟩ ⟨4,8⟩ true = some ⟨4,8⟩ := rfl
end Empack.Workflow

namespace Empack.Workflow
open Rules
/-- The adapter supplies a selection bound to the authenticated channel.
    Record its high-water mark even if the resource or installation gate fails. -/
def installSelected (saved incoming : Channel) (authentic : Bool) (lockFor : Channel → Option Lock)
    (limit used ask : Envelope) (world : Snapshot (Option Nat)) (baseline : Option Nat)
    (reader : Nat → Option Nat) : Channel × Snapshot (Option Nat) :=
  match observeChannel saved incoming authentic with
  | none => (saved,world)
  | some next =>
    if classify false limit used ask = .granted then
      (next,(lockFor next).elim world (fun lock => install world baseline lock reader))
    else (next,world)

def releaseCase (digest available readId : Nat) :=
  installSelected ⟨1,5⟩ ⟨2,digest⟩ true (fun c => if c.digest = 6 then some ⟨9,8⟩ else none)
    (fun _ => available) (fun _ => 0) (fun _ => 1) ⟨1,none⟩ none (fun _ => some readId)
example : releaseCase 6 1 8 = (⟨2,6⟩,⟨2,some 8⟩) := rfl
example : releaseCase 6 0 8 = (⟨2,6⟩,⟨1,none⟩) := rfl
example : releaseCase 6 1 7 = (⟨2,6⟩,⟨1,none⟩) := rfl
end Empack.Workflow
