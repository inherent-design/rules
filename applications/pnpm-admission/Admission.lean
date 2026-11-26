namespace ApplicationStudy.PnpmAdmission

inductive Kind | tasks | placeholder | explicitRun | declaredFallback
  deriving BEq, DecidableEq, Repr

/-- Arguments exclude the program name. This is the selected original
    leading-token rule, not a general CLI argument parser. -/
def splitLeadingPm (args : List String) : Bool × List String :=
  match args with
  | "pm" :: rest => (true,rest)
  | _ => (false,args)

structure Request where
  kind : Kind
  forcedBuiltin : Bool
  builtinHelp : Bool
  inMember : Bool
  localBody : Bool
  rootBody : Bool
  scriptLabel : String
  args : List String
  deriving Repr

structure Outcome where
  action : String
  status : Nat
  scriptLabel : Option String
  args : List String
  childNpmCommand : Option String
  deriving BEq, DecidableEq, Repr

def noChild (action : String) (status : Nat) : Outcome := ⟨action,status,none,[],none⟩

/-- Admitted controlled scripts complete successfully. General script parsing,
    process failure, runtime selection, and group scheduling are not modeled. -/
def script (r : Request) : Outcome :=
  ⟨"script",0,some r.scriptLabel,r.args,some "run-script"⟩

def run (r : Request) : Outcome :=
  match r.kind with
  | .placeholder => noChild "unsupported" 1
  | .explicitRun | .declaredFallback => script r
  | .tasks =>
    if r.builtinHelp then noChild "builtin-help" 0
    else if r.forcedBuiltin then noChild "builtin-status" 0
    else if r.localBody then script r
    else if r.inMember && r.rootBody then noChild "root-shadow" 1
    else noChild "builtin-status" 0

def base : Request := ⟨.tasks,false,false,false,true,true,"tasks",["status"]⟩

theorem local_script_overrides_tasks : run base = script base := by decide
theorem forced_tasks_do_not_run_the_script :
    run { base with forcedBuiltin := true } = noChild "builtin-status" 0 := by decide
theorem root_shadow_refuses_member_builtin :
    run { base with inMember := true, localBody := false, scriptLabel := "" } = noChild "root-shadow" 1 := by decide
theorem forced_explicit_run_still_selects_script :
    run { base with kind := .explicitRun, forcedBuiltin := true } = script base := by decide
theorem placeholder_does_not_dispatch_script (r : Request) :
    run { r with kind := .placeholder } = noChild "unsupported" 1 := rfl
theorem parser_help_precedes_script_override (r : Request) :
    run { r with kind := .tasks, builtinHelp := true } = noChild "builtin-help" 0 := rfl
theorem empty_root_body_does_not_shadow :
    run { base with inMember := true, localBody := false, rootBody := false, scriptLabel := "" } = noChild "builtin-status" 0 := by decide
theorem explicit_run_forwards_script_help :
    (run { base with kind := .explicitRun, args := ["--help"] }).args = ["--help"] := rfl
theorem leading_pm_is_removed (rest : List String) :
    splitLeadingPm ("pm" :: rest) = (true,rest) := rfl
theorem global_option_before_pm_is_not_a_prefix :
    splitLeadingPm ["--dir",".","pm","tasks","status"] =
      (false,["--dir",".","pm","tasks","status"]) := by decide

end ApplicationStudy.PnpmAdmission
