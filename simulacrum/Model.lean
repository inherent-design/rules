import common.Core
namespace Simulacrum
def eligible (cursor : Option Nat) (mtime : Nat) :=
  cursor.elim true (fun last => decide (mtime > last))
def acknowledge (cursor : Option Nat) (mtime : Nat) (flushed updateCursor : Bool) :=
  if flushed && updateCursor then some mtime else cursor
theorem failed_flush (c : Option Nat) (t : Nat) (enabled : Bool) :
    acknowledge c t false enabled = c := rfl
example : eligible (some 12) 12 = false := rfl
end Simulacrum
