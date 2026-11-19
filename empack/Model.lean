import common.Core
namespace Empack
inductive Intent | never | auto | always deriving DecidableEq, Repr
inductive Color | disabled | ansi256 | trueColor deriving DecidableEq, Repr
structure Observation where
  stderrTty : Bool
  colorsEnabled : Bool
  colorterm : String
  locale : Option String
  fallbackUtf : Bool
  columns : Nat
  deriving DecidableEq, Repr
structure Terminal where
  tty : Bool
  color : Color
  unicode : Bool
  columns : Nat
  deriving DecidableEq, Repr
def detect (i : Intent) (o : Observation) : Terminal :=
  let enabled := match i with
    | .never => false
    | .always => true
    | .auto => o.colorsEnabled
  let color := if !enabled then Color.disabled else if ["truecolor","24bit"].contains o.colorterm
    then Color.trueColor else Color.ansi256
  ⟨o.stderrTty, color, o.stderrTty && (o.locale.any (fun s => s.toLower.contains "utf") || o.fallbackUtf), o.columns⟩

theorem redirected_ascii (i : Intent) (o : Observation) :
    (detect i {o with stderrTty := false}).unicode = false := rfl

/-- File identities denote equivalence classes under the selected platform's
    portable-attribute capabilities. The adapter refuses links before planning. -/
inductive Policy | managed | seed deriving DecidableEq
structure File where
  identity : Nat
  policy : Policy
  deriving DecidableEq
inductive Path | absent | directory | file (identity : Nat) deriving DecidableEq
inductive Clash | unowned | modified | wrongKind | seedOwnership deriving DecidableEq
inductive Action | preserve | unchanged | create (id : Nat) | replace (id : Nat)
  | remove | conflict (reason : Clash) deriving DecidableEq

def planFile (old : Option File) (live : Path) (next : Option File) : Action :=
  match next, old, live with
  | none, none, _ | none, some ⟨_,.seed⟩, _ => .preserve
  | none, some _, .absent => .unchanged
  | none, some _, .directory => .conflict .wrongKind
  | none, some f, .file n => if n = f.identity then .remove else .conflict .modified
  | some _, _, .directory => .conflict .wrongKind
  | some ⟨n,.seed⟩, _, .absent => .create n
  | some ⟨_,.seed⟩, _, .file _ => .preserve
  | some _, some ⟨_,.seed⟩, _ => .conflict .seedOwnership
  | some f, _, .absent => .create f.identity
  | some _, none, .file _ => .conflict .unowned
  | some f, some b, .file n => if n = f.identity then .unchanged
    else if n = b.identity then .replace f.identity else .conflict .modified

theorem unowned_matching_file (id : Nat) :
    planFile none (.file id) (some ⟨id,.managed⟩) = .conflict .unowned := rfl

example : planFile (some ⟨1,.managed⟩) (.file 2) (some ⟨2,.managed⟩) = .unchanged := rfl
example : planFile (some ⟨1,.managed⟩) (.file 2) none = .conflict .modified := rfl
example : (detect .always ⟨false,false,"24bit",none,true,80⟩) = ⟨false,.trueColor,false,80⟩ := by decide
end Empack

namespace Empack
inductive Verdict | closed | tooLarge | busy | granted deriving DecidableEq, Repr
inductive Resource | jobs | memory | scratch | files deriving DecidableEq, Repr
abbrev Envelope := Resource → Nat
def dimensions := [Resource.jobs, .memory, .scratch, .files]
def classify (closed : Bool) (limit used ask : Envelope) :=
  if closed then Verdict.closed
  else if dimensions.any (fun r => ask r > limit r) then Verdict.tooLarge
  else if dimensions.all (fun r => Rules.admit (used r) (ask r) (limit r))
       then Verdict.granted else Verdict.busy
def reserve (closed : Bool) (limit used ask : Envelope) : Envelope :=
  if classify closed limit used ask = .granted then fun r => used r + ask r else used
theorem no_partial_charge (c : Bool) (limit used ask : Envelope)
    (h : classify c limit used ask ≠ .granted) : reserve c limit used ask = used := by
  simp [reserve,h]

/-- Observation adapter. Both a captured environment and a fake interpreter
    supply the same four probe results, including a failed charmap as false. -/
structure Probe where
  tty : Bool
  enabled : Bool
  colorterm : String
  lcAll : Option String
  lcCtype : Option String
  lang : Option String
  osUtf : Bool
  cols : Nat
  deriving Repr

def observe (p : Probe) : Observation :=
  ⟨p.tty,p.enabled,p.colorterm,p.lcAll.or (p.lcCtype.or p.lang),p.osUtf,p.cols⟩

def displayStep (intent : Intent) (_old : Terminal) (p : Probe) := detect intent (observe p)

theorem replay_observations (i : Intent) (ps : List Probe) (start : Terminal) :
    Rules.replay (displayStep i) start ps =
    Rules.replay (fun _ obs => detect i obs) start (ps.map observe) :=
  Rules.project_replay (displayStep i) (fun _ obs => detect i obs) id observe
    (fun _ _ => rfl) ps start

example : classify false (fun _ => 3) (fun _ => 3)
    (fun r => if r = .files then 4 else 1) = .tooLarge := by decide
example : classify false (fun _ => 3) (fun _ => 3) (fun _ => 1) = .busy := by decide
end Empack
