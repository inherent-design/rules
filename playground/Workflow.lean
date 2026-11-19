import playground.Model
namespace Playground.Workflow
open Rules
/-- Owners version dependencies independently. Rendering consumes tint and
    occupancy while a collision fixture consumes occupancy alone. -/
inductive Input | occupancy | halo | tint | device deriving DecidableEq
def cpuMesh : List Input := [.occupancy,.halo,.tint]
def collision : List Input := [.occupancy,.halo]
def realization : List Input := cpuMesh ++ [.device]

structure Product where
  readAt : Clock Input
  payload : Nat
def finish (deps : List Input) (now : Clock Input) (old : Option Product) (p : Product) :=
  if deps.all (fun k => p.readAt k == now k) then some p else old

theorem late_keeps_prior (deps : List Input) (now : Clock Input) (old : Option Product)
    (p : Product) (k : Input) (used : k ∈ deps) (h : p.readAt k ≠ now k) :
    finish deps now old p = old := by
  unfold finish
  split
  · rename_i ok
    have eq := List.all_eq_true.mp ok k used
    simp [h] at eq
  · rfl

def start : Clock Input := fun _ => 0
def changed (k : Input) : Clock Input := fun x => if x = k then 1 else 0
def oldMesh : Product := ⟨start,7⟩
example : ((finish cpuMesh (changed .tint) none oldMesh).map (·.payload)) = none := rfl
example : ((finish collision (changed .tint) none oldMesh).map (·.payload)) = some 7 := rfl
example : ((finish cpuMesh (changed .device) none oldMesh).map (·.payload)) = some 7 := rfl
example : ((finish realization (changed .device) none oldMesh).map (·.payload)) = none := rfl
end Playground.Workflow

namespace Playground.Workflow
structure Replica where
  epoch : Nat
  baseline : Nat
  interest : Nat
  seq : Nat
  revision : Nat
  value : Nat
  deriving DecidableEq, Repr
structure Delta where
  epoch : Nat
  baseline : Nat
  interest : Nat
  seq : Nat
  fromRev : Nat
  toRev : Nat
  value : Nat

/-- Apply only the next complete delta against its exact view basis. Caller
    retains gap/reorder policy and requests resync on incompatible history. -/
def applyDelta (r : Replica) (d : Delta) : Option Replica :=
  if r.epoch == d.epoch && r.baseline == d.baseline && r.interest == d.interest &&
      r.seq + 1 == d.seq && r.revision == d.fromRev then
    some {r with seq := d.seq, revision := d.toRev, value := d.value}
  else none

def joined : Replica := ⟨8,5,3,0,42,1⟩
def update : Delta := ⟨8,5,3,1,42,44,9⟩
example : applyDelta joined update = some ⟨8,5,3,1,44,9⟩ := rfl
example : applyDelta joined {update with interest := 1} = none := rfl
end Playground.Workflow

namespace Playground.Workflow
open Rules
/-- A single tick followed by a local mesh preparation and a later device
    observation. The old device product can remain visible during recovery. -/
def tickAndRender (old : Snapshot Regions) (left right : Option Nat) (budget : Option Charge)
    (prior : Option Product) (readAt deviceNow : Clock Input) : Snapshot Regions × Option Product :=
  let world := advance old old.revision left right budget
  if world.revision == old.revision then (world,prior)
  else
    let basis : Clock Input := fun k => if k = .occupancy then world.revision else readAt k
    (world,finish realization deviceNow prior ⟨basis,world.value.1⟩)

def tickClock (device : Nat) : Clock Input :=
  fun k => match k with | .occupancy => 5 | .device => device | _ => 0
def oneTick (right : Option Nat) (device : Nat) :=
  tickAndRender ⟨4,(1,9)⟩ (some 0) right (reserve ⟨3,1⟩ 2 5 3) none (tickClock 0) (tickClock device)

example : ((oneTick (some 0) 0).2.map (·.payload)) = some 9 := rfl
example : ((oneTick (some 0) 1).1.revision, (oneTick (some 0) 1).2.map (·.payload)) = (5,none) := rfl
example : ((oneTick none 0).1.revision, (oneTick none 0).2.map (·.payload)) = (4,none) := rfl
end Playground.Workflow
