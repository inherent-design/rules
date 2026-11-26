import Std

namespace Host.Java.CpuImage

/-- One successful zeroed 2x2 allocation. Retained mathematical words after close
    are model history, never permission to read a freed address. -/
structure State where
  closed : Bool
  words : List UInt32
  deriving BEq, DecidableEq, Repr

def initial : State := ⟨false, [0, 0, 0, 0]⟩

/-- Coordinates -1,0,1,2 are encoded as 0,1,2,3. -/
def inside (x y : Nat) : Bool := (x == 1 || x == 2) && (y == 1 || y == 2)
def index (x y : Nat) : Nat := (y - 1) * 2 + (x - 1)

structure Reply where
  error : Nat
  word : Option UInt32
  deriving BEq, DecidableEq, Repr

/-- Operation 0 constructs, 1 gets, 2 sets, 3 closes, 4 reads metadata.
    The research codec admits exactly one initial construction. Errors distinguish
    bounds (1) from closed allocation (2); no allocation failure is modeled. -/
def step (s : State) (operation x y : Nat) (word : UInt32) : State × Reply :=
  if operation == 0 then (initial, ⟨0, none⟩)
  else if operation == 3 then ({ s with closed := true }, ⟨0, none⟩)
  else if operation == 4 then (s, ⟨0, none⟩)
  else if !inside x y then (s, ⟨1, none⟩)
  else if s.closed then (s, ⟨2, none⟩)
  else if operation == 1 then (s, ⟨0, some (s.words[index x y]!)⟩)
  else ({ s with words := s.words.set (index x y) word }, ⟨0, none⟩)

def visibleWords (s : State) : Option (List UInt32) := if s.closed then none else some s.words
def metadata (_s : State) : Nat × Nat := (2, 2)

theorem initial_zeroed : initial.words = [0, 0, 0, 0] := rfl
theorem close_sets_closed (s : State) : (step s 3 0 0 0).1.closed = true := by simp [step]
theorem close_keeps_model_history (s : State) : (step s 3 0 0 0).1.words = s.words := by simp [step]
theorem close_is_idempotent (s : State) :
    (step (step s 3 0 0 0).1 3 0 0 0).1 = (step s 3 0 0 0).1 := by simp [step]
theorem closed_words_are_unobservable (s : State) : visibleWords { s with closed := true } = none := rfl
theorem close_preserves_metadata (s : State) : metadata (step s 3 0 0 0).1 = metadata s := rfl
theorem metadata_does_not_reopen (s : State) : (step s 4 0 0 0).1 = s := by simp [step]
theorem metadata_reads_after_close (s : State) : (step { s with closed := true } 4 0 0 0).2.error = 0 := rfl
theorem closed_valid_get_refuses (words : List UInt32) : (step ⟨true, words⟩ 1 1 1 0).2.error = 2 := rfl
theorem closed_valid_set_refuses (words : List UInt32) (word : UInt32) :
    (step ⟨true, words⟩ 2 1 1 word).1 = ⟨true, words⟩ := rfl
theorem bounds_precedes_closed (words : List UInt32) : (step ⟨true, words⟩ 1 3 1 0).2.error = 1 := rfl
theorem refused_bounds_preserves_words (s : State) (word : UInt32) : (step s 2 0 1 word).1 = s := rfl
theorem opaque_word_roundtrips :
    (step (step initial 2 1 1 0x89abcdef).1 1 1 1 0).2.word = some 0x89abcdef := by decide
theorem selected_cell_does_not_change_neighbors :
    (step initial 2 2 1 0x12345678).1.words = [0, 0x12345678, 0, 0] := by decide

end Host.Java.CpuImage
