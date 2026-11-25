namespace Host.Java.FloatOrder

/-- A selected exact subset, not a full IEEE-754 representation or arithmetic model. -/
inductive Atom where
  | negativeTen | negativeZero | positiveZero | positiveTen | nan
  deriving Repr, DecidableEq, BEq

def rank : Atom → Nat
  | .negativeTen => 0 | .negativeZero => 1 | .positiveZero => 2
  | .positiveTen => 3 | .nan => 4

/-- Selected Float.compare order, including its NaN equivalence class. -/
def totalLe (a b : Atom) : Bool := rank a <= rank b

def numericRank : Atom → Option Nat
  | .negativeTen => some 0 | .negativeZero | .positiveZero => some 1
  | .positiveTen => some 2 | .nan => none

/-- Selected primitive <= relation; NaN has no numeric comparison result. -/
def numericLe (a b : Atom) : Bool :=
  match numericRank a, numericRank b with
  | some x, some y => x <= y
  | _, _ => false

def negate : Atom → Atom
  | .negativeTen => .positiveTen | .positiveTen => .negativeTen
  | .negativeZero => .positiveZero | .positiveZero => .negativeZero
  | .nan => .nan

/-- Only multiplication by the selected exact scales +1 or -1 is represented. -/
def scale (flip : Bool) (value : Atom) : Atom := if flip then negate value else value

def isNaN (value : Atom) : Bool := value == .nan

theorem total_reflexive (x : Atom) : totalLe x x = true := by cases x <;> decide
theorem negative_zero_precedes_positive : totalLe .negativeZero .positiveZero = true := rfl
theorem positive_zero_not_before_negative : totalLe .positiveZero .negativeZero = false := rfl
theorem numeric_zeros_compare_both_ways :
    numericLe .negativeZero .positiveZero = true ∧ numericLe .positiveZero .negativeZero = true := by decide
theorem zeros_are_distinct_keys : (Atom.negativeZero == .positiveZero) = false := rfl
theorem nan_has_greatest_selected_total_rank (x : Atom) : totalLe x .nan = true := by cases x <;> decide
theorem nan_numeric_left_refuses (x : Atom) : numericLe .nan x = false := by cases x <;> rfl
theorem nan_numeric_right_refuses (x : Atom) : numericLe x .nan = false := by cases x <;> rfl
theorem nan_total_self_matches : totalLe .nan .nan = true := rfl
theorem negation_involutive (x : Atom) : negate (negate x) = x := by cases x <;> rfl
theorem scale_one_preserves (x : Atom) : scale false x = x := rfl
theorem scale_minus_one_flips_negative_zero : scale true .negativeZero = .positiveZero := rfl
theorem scale_minus_one_flips_positive_zero : scale true .positiveZero = .negativeZero := rfl
theorem nan_scale_preserves_class (flip : Bool) : scale flip .nan = .nan := by cases flip <;> rfl
theorem total_antisymmetric (x y : Atom) (hxy : totalLe x y = true) (hyx : totalLe y x = true) :
    x = y := by cases x <;> cases y <;> simp_all [totalLe, rank]

end Host.Java.FloatOrder
