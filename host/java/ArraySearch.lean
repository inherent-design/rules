namespace Host.Java.ArraySearch

/-- Ordered integer-valued float subset only. The adapter excludes NaN, infinities,
    signed-zero distinctions, fractional values, and unsorted inputs. -/
def sorted (values : List Nat) : Bool :=
  (values.zip (values.drop 1)).all (fun (a,b) => a ≤ b)
def partition (values : List Nat) (query cut : Nat) (strict : Bool) : Bool :=
  cut ≤ values.length && (values.take cut).all (fun n => if strict then n < query else n ≤ query) &&
  (values.drop cut).all (query < ·)

/-- A decoded Java binarySearch result. A negative Java result represents the
    insertion point (-result-1), not a failed operation or stable duplicate index. -/
def binaryResultAllowed (values : List Nat) (query : Nat) (found : Bool) (index : Nat) : Bool :=
  sorted values && if found then values[index]? == some query else partition values query index true

/-- The caller's conversion of a binary-search result to a threshold/fallback index.
    Any matching duplicate is allowed by the API; absent keys have one insertion floor. -/
def binaryFloorAllowed (values : List Nat) (query : Nat) (result : Option Nat) : Bool :=
  match result with
  | none => binaryResultAllowed values query false 0
  | some i => binaryResultAllowed values query true i || binaryResultAllowed values query false (i+1)

/-- Last <= query on the same subset. This is a stronger caller policy than the
    library's permitted choice among duplicates. -/
def upperFloorAllowed (values : List Nat) (query : Nat) (result : Option Nat) : Bool :=
  sorted values && match result with
  | none => partition values query 0 false
  | some i => i < values.length && partition values query (i+1) false

theorem empty_search_inserts_at_zero : binaryResultAllowed [] 2 false 0 = true := by decide
theorem empty_search_cannot_find : binaryResultAllowed [] 2 true 0 = false := by decide
theorem before_first_insertion : binaryResultAllowed [2,3] 1 false 0 = true := by decide
theorem after_last_insertion : binaryResultAllowed [2,3] 4 false 2 = true := by decide
theorem between_values_insertion : binaryResultAllowed [1,3] 2 false 1 = true := by decide
theorem insertion_is_not_found : binaryResultAllowed [1,3] 2 true 1 = false := by decide
theorem matching_key_not_reported_missing : binaryResultAllowed [1,2,3] 2 false 1 = false := by decide
theorem duplicate_first_permitted : binaryResultAllowed [2,2,2] 2 true 0 = true := by decide
theorem duplicate_middle_permitted : binaryResultAllowed [2,2,2] 2 true 1 = true := by decide
theorem duplicate_last_permitted : binaryResultAllowed [2,2,2] 2 true 2 = true := by decide
theorem out_of_range_refuses : binaryResultAllowed [2,2,2] 2 true 3 = false := by decide
theorem unsorted_outside_contract : binaryResultAllowed [3,1] 1 true 1 = false := by decide
theorem binary_can_use_earlier_tie : binaryFloorAllowed [2,2,2] 2 (some 0) = true := by decide
theorem upper_floor_uses_last_tie : upperFloorAllowed [2,2,2] 2 (some 2) = true := by decide
theorem upper_floor_refuses_earlier_tie : upperFloorAllowed [2,2,2] 2 (some 0) = false := by decide
theorem empty_floor_is_fallback : binaryFloorAllowed [] 2 none = true ∧ upperFloorAllowed [] 2 none = true := by decide
theorem below_first_is_fallback : binaryFloorAllowed [2,3] 1 none = true ∧ upperFloorAllowed [2,3] 1 none = true := by decide
theorem after_last_is_last : binaryFloorAllowed [2,3] 4 (some 1) = true ∧ upperFloorAllowed [2,3] 4 (some 1) = true := by decide

end Host.Java.ArraySearch
