import common.Core
namespace Moment.Guidance
open Rules
inductive Input | source | task | policy deriving DecidableEq
def deps : List Input := [.source,.task,.policy]
structure Candidate where
  observed : Clock Input
  excerpt : String
  interpretation : String

/-- Explicit refresh advances observed source revision. A read samples the
    last admitted observations and independently checks current authority. -/
inductive Read | denied | current (excerpt interpretation : String) | stale deriving DecidableEq
def read (c : Candidate) (now : Clock Input) (allowed : Bool) : Read :=
  if !allowed then .denied
  else if deps.all (fun k => c.observed k == now k) then .current c.excerpt c.interpretation
  else .stale

theorem revoked_hides (c : Candidate) (now : Clock Input) : read c now false = .denied := rfl

example : read ⟨fun _ => 1, "quoted evidence", "candidate"⟩
    (fun k => if k = .task then 2 else 1) true = .stale := rfl
end Moment.Guidance
