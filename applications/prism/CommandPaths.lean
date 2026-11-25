namespace ApplicationStudy.PrismCommandPaths

/-- Inner payload of a quoted Java program token, excluding quote delimiters.
    Correspondence is restricted to the admitted no-quote/nontrailing-backslash profile. -/
def wrapperProgram : List Nat → List Nat
  | [] => []
  | c :: rest =>
      if c == 92 then match rest with
        | [] => []
        | next :: tail => next :: wrapperProgram tail
      else c :: wrapperProgram rest

/-- Candidate escaping belongs after variable expansion and only at this consumer boundary. -/
def escapeBackslashes : List Nat → List Nat
  | [] => []
  | c :: rest => if c == 92 then 92 :: 92 :: escapeBackslashes rest
                else c :: escapeBackslashes rest

def program (wrapper : Bool) (input : List Nat) : List Nat :=
  if wrapper then wrapperProgram input else input
def preserved (wrapper : Bool) (input : List Nat) : Bool := program wrapper input == input

theorem preparation_preserves (input : List Nat) : program false input = input := by rfl
theorem preparation_preserved (input : List Nat) : preserved false input = true := by
  simp [preserved, program]
theorem wrapper_uses_quoted_payload (input : List Nat) : program true input = wrapperProgram input := by rfl
theorem ordinary_character (c : Nat) (rest : List Nat) (h : c ≠ 92) :
    wrapperProgram (c :: rest) = c :: wrapperProgram rest := by
  rw [wrapperProgram.eq_def]; simp [h]
theorem backslash_consumes_escape (next : Nat) (rest : List Nat) :
    wrapperProgram (92 :: next :: rest) = next :: wrapperProgram rest := by rfl
theorem doubled_backslash_is_literal (rest : List Nat) :
    wrapperProgram (92 :: 92 :: rest) = 92 :: wrapperProgram rest := by rfl
theorem candidate_roundtrip (input : List Nat) : wrapperProgram (escapeBackslashes input) = input := by
  induction input with
  | nil => rfl
  | cons c rest ih =>
    by_cases h : c = 92
    · subst c; simp [escapeBackslashes, wrapperProgram, ih]
    · rw [escapeBackslashes]; simp only [beq_iff_eq, h, ↓reduceIte]
      rw [ordinary_character c _ h, ih]
theorem no_backslash_identity (input : List Nat) (h : ∀ c ∈ input, c ≠ 92) :
    wrapperProgram input = input := by
  induction input with
  | nil => rfl
  | cons c rest ih =>
    have head : c ≠ 92 := h c (by simp)
    have tail : ∀ n ∈ rest, n ≠ 92 := by intro n hn; exact h n (by simp [hn])
    rw [ordinary_character c rest head, ih tail]
theorem native_separator_counterexample : wrapperProgram [67,58,92,74] = [67,58,74] := by decide
theorem native_separator_not_preserved : preserved true [67,58,92,74] = false := by decide

end ApplicationStudy.PrismCommandPaths
