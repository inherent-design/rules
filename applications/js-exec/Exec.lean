namespace ApplicationStudy.JsExec

inductive App where
  | npm | pnpm | yarn
  deriving BEq, DecidableEq, Repr
inductive Mode where
  | exec | namedScript | npmCall
  deriving BEq, DecidableEq, Repr
inductive Meaning where
  | packageCommand | programAndArguments | shellSnippet | declaredScript
  deriving BEq, DecidableEq, Repr
structure Context where
  dependencyBin : Bool
  inheritedBin : Bool
  cwd : Nat -- exact requested directory token; zero reserved for no fixture event
  arguments : List String
  deriving BEq, DecidableEq, Repr
structure Outcome where
  selected : Nat -- 0 none, 1 dependency, 2 inherited PATH, 3 named root script
  stage : Nat -- 0 fixture ran, 1 offline package lookup, 2 program lookup, 3 shell lookup
  exitCode : Nat
  cwd : Nat
  arguments : List String
  deriving BEq, DecidableEq, Repr
def meaning (app : App) (mode : Mode) : Meaning :=
  match mode with
  | .namedScript => .declaredScript
  | .npmCall => .shellSnippet
  | .exec => match app with
    | .npm => .packageCommand
    | .pnpm => .programAndArguments
    | .yarn => .shellSnippet
def success (selected : Nat) (c : Context) : Outcome :=
  ⟨selected,0,0,c.cwd,c.arguments⟩
def failure (stage code : Nat) : Outcome := ⟨0,stage,code,0,[]⟩
def pathLookup (app : App) (c : Context) : Outcome :=
  if c.dependencyBin then success 1 c else if c.inheritedBin then success 2 c
  else match app with | .pnpm => failure 2 1 | _ => failure 3 127

/-- Closed offline fixture, literal executable name, known successful programs,
    installed project context, empty npm acquisition cache/global prefix, and an
    admitted named script. This does not parse shellcode or fetch a package. -/
def run (app : App) (mode : Mode) (c : Context) : Outcome :=
  match mode with
  | .namedScript => success 3 c
  | .npmCall => pathLookup app c -- decoder admits this mode for npm only
  | .exec => match app with
    | .npm => if c.dependencyBin then success 1 c else failure 1 1
    | _ => pathLookup app c

def sample : Context := ⟨false,true,1,["alpha β","literal; echo NOT_A_COMMAND","--flag=value"]⟩
theorem exec_names_have_distinct_meanings :
    meaning .npm .exec = .packageCommand ∧
    meaning .pnpm .exec = .programAndArguments ∧
    meaning .yarn .exec = .shellSnippet := by decide
theorem npm_default_does_not_use_only_inherited_path :
    run .npm .exec sample = failure 1 1 := by decide
theorem npm_call_can_use_that_same_path :
    run .npm .npmCall sample = success 2 sample := by decide
theorem pnpm_exec_uses_inherited_path : run .pnpm .exec sample = success 2 sample := by decide
theorem yarn_exec_uses_inherited_path : run .yarn .exec sample = success 2 sample := by decide
theorem named_script_is_a_different_target (app : App) (c : Context) :
    (run app .namedScript c).selected = 3 := rfl
theorem dependency_beats_inherited_path (app : App) (c : Context) (h : c.dependencyBin = true) :
    (run app .exec c).selected = 1 := by
  cases app <;> simp [run,pathLookup,h,success]
theorem success_keeps_requested_directory_and_arguments (app : App) (mode : Mode) (c : Context)
    (h : (run app mode c).selected != 0) :
    (run app mode c).cwd = c.cwd ∧ (run app mode c).arguments = c.arguments := by
  cases c with
  | mk dep inherited cwd args =>
    cases app <;> cases mode <;> cases dep <;> cases inherited <;>
      simp_all [run,pathLookup,success,failure]
theorem missing_default_codes_agree_without_agreeing_on_phase :
    (run .npm .exec {sample with inheritedBin := false}).exitCode = 1 ∧
    (run .pnpm .exec {sample with inheritedBin := false}).exitCode = 1 ∧
    (run .npm .exec {sample with inheritedBin := false}).stage !=
      (run .pnpm .exec {sample with inheritedBin := false}).stage := by decide
theorem yarn_shell_lookup_failure_is_127 :
    run .yarn .exec {sample with inheritedBin := false} = failure 3 127 := by decide
theorem npm_call_missing_is_not_default_package_lookup :
    run .npm .npmCall {sample with inheritedBin := false} = failure 3 127 := by decide
theorem a_declared_script_does_not_supply_an_exec_binary :
    (run .pnpm .namedScript {sample with inheritedBin := false}).selected = 3 ∧
    (run .pnpm .exec {sample with inheritedBin := false}).selected = 0 := by decide

end ApplicationStudy.JsExec
