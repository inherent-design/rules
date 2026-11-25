namespace ApplicationStudy.CargoTesting

/-- IDs name this std-only fixture's library, two external API tests, custom
    harness, example test harness, and documentation phase, respectively. -/
def selected (scope : Nat) : List Nat :=
  if scope == 1 then [0]
  else if scope == 2 then [3]
  else if scope == 3 then [5]
  else if scope == 4 then [0,1,2,3,4]
  else [0,1,2,3,5]

/-- Body IDs distinguish two ordinary unit tests, an ignored unit test,
    two external public-API checks, custom main, and one runnable doctest. -/
def unitBodies (id filter : Nat) : List Nat :=
  if id == 0 then
    if filter == 1 then [1] else if filter == 2 then [] else if filter == 3 then [2] else [0,1]
  else if id == 1 then [3]
  else if id == 2 then [4]
  else if id == 3 then [5]
  else if id == 5 then [6]
  else []

def failed (id filter : Nat) (failUnit : Bool) : Bool := id == 0 && filter == 0 && failUnit

structure Result where
  invoked : List Nat
  bodies : List Nat
  successful : Bool
  refused : Bool
  deriving DecidableEq, Repr

def execute : List Nat → Nat → Bool → Bool → Result
  | [], _, _, _ => ⟨[], [], true, false⟩
  | id :: rest, filter, failUnit, keepGoing =>
    if failed id filter failUnit && !keepGoing then
      ⟨[id], unitBodies id filter, false, false⟩
    else
      let tail := execute rest filter failUnit keepGoing
      ⟨id :: tail.invoked, unitBodies id filter ++ tail.bodies,
        !failed id filter failUnit && tail.successful, false⟩

def run (scope filter : Nat) (noRun keepGoing failUnit : Bool) : Result :=
  if scope == 3 && noRun then ⟨[], [], false, true⟩
  else if noRun then ⟨[], [], true, false⟩
  else execute (selected scope) filter failUnit keepGoing

theorem compile_only_no_bodies : (run 0 0 true false false).bodies = [] := by decide
theorem compile_only_success : (run 0 0 true false false).successful = true := by decide
theorem doc_no_run_refused : (run 3 0 true false false).refused = true := by decide
theorem empty_filter_can_succeed : run 1 2 false false false = ⟨[0],[],true,false⟩ := by decide
theorem selected_unit_only : (run 1 1 false false false).bodies = [1] := by decide
theorem explicit_ignored_only : (run 1 3 false false false).bodies = [2] := by decide
theorem custom_filter_is_not_libtest : (run 2 2 false false false).bodies = [5] := by decide
theorem failure_completes_current_harness :
    run 0 0 false false true = ⟨[0],[0,1],false,false⟩ := by decide
theorem continuation_retains_failure : (run 0 0 false true true).successful = false := by decide
theorem continuation_reaches_docs : (run 0 0 false true true).invoked = [0,1,2,3,5] := by decide
theorem all_targets_excludes_docs : (run 4 0 false false false).invoked = [0,1,2,3,4] := by decide
theorem example_harness_does_not_run_main : unitBodies 4 0 = [] := by decide
theorem empty_execution_success (filter : Nat) (failUnit keepGoing : Bool) :
    execute [] filter failUnit keepGoing = ⟨[],[],true,false⟩ := by rfl
theorem failure_stops_later (id filter : Nat) (rest : List Nat) (failUnit : Bool)
    (h : failed id filter failUnit = true) :
    execute (id :: rest) filter failUnit false = ⟨[id], unitBodies id filter, false, false⟩ := by
  simp [execute, h]

end ApplicationStudy.CargoTesting
