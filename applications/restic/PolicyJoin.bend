import Base
import Selection.bend as S
import Retention.bend as R

# Group-key equality and strictly newer ordering are admitted adapter witnesses,
# as in Selection.bend. Reachability is the selected file-data projection.
type PolicyCandidate is Data:
  Candidate{id: String,newer_same_group: Bool}
type PolicyOutcome is Data:
  Outcome{planned: List<&2,String>,removed: List<&2,String>,snapshots: List<&2,String>,available: List<&2,String>,prune_phase: Bool,status: Nat}

def planned(values: List<&2,PolicyCandidate>) -> List<&2,String>:
  match values:
    case Nil{}: Nil{}
    case Con{head,tail}:
      match head:
        case Candidate{id,newer}: R.keep(String,S.removed(newer,False{}),id,planned(tail))
def admitted(+refused: List<&2,String>,ids: List<&2,String>) -> List<&2,String>:
  match ids:
    case Nil{}: Nil{}
    case Con{+head,tail}: R.keep(String,Bool.not(R.contains(head,refused)),head,admitted(refused,tail))
def has_failure(+refused: List<&2,String>,ids: List<&2,String>) -> Bool:
  match ids:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(R.contains(head,refused),has_failure(refused,tail))
def forget_many(ids: List<&2,String>,repo: R.Repository) -> R.Repository:
  match ids:
    case Nil{}: repo
    case Con{head,tail}: forget_many(tail,R.forget(head,repo))
def ids(values: List<&2,R.Snapshot>) -> List<&2,String>:
  match values:
    case Nil{}: Nil{}
    case Con{head,tail}: Con{R.snapshot_id(head),ids(tail)}
def nonempty(values: List<&2,String>) -> Bool:
  match values:
    case Nil{}: False{}
    case Con{_,_}: True{}
def finish(plan: List<&2,String>,removed: List<&2,String>,repo: R.Repository,phase: Bool,failed: Bool) -> PolicyOutcome:
  match repo:
    case R.Repo{snapshots,available}: Outcome{plan,removed,ids(snapshots),available,phase,Bool.pick(Nat,failed,3n,0n)}
def apply(+plan: List<&2,String>,+repo: R.Repository,+dry: Bool,+refused: List<&2,String>) -> PolicyOutcome:
  +removed=Bool.pick(List<&2,String>,dry,Nil{},admitted(refused,plan))
  +failed=Bool.and(Bool.not(dry),has_failure(refused,plan))
  +phase=Bool.and(Bool.not(failed),nonempty(plan))
  finish(plan,removed,R.prune(Bool.and(Bool.not(dry),phase),forget_many(removed,repo)),phase,failed)
def run(candidates: List<&2,PolicyCandidate>,repo: R.Repository,dry: Bool,refused: List<&2,String>) -> PolicyOutcome:
  apply(planned(candidates),repo,dry,refused)

def candidates() -> List<&2,PolicyCandidate>:
  [Candidate{"a0",True{}},Candidate{"a1",False{}},Candidate{"b0",True{}},Candidate{"b1",False{}}]
def repository() -> R.Repository:
  R.Repo{[R.Snap{"a0",None{},["shared","oldA"]},R.Snap{"a1",Some{"a0"},["shared","newA"]},R.Snap{"b0",None{},["shared","oldB"]},R.Snap{"b1",Some{"b0"},["shared","newB"]}],["shared","oldA","newA","oldB","newB"]}

law preview_keeps_references_and_backing:
  {run(candidates(),repository(),True{},Nil{}) == Outcome{["a0","b0"],Nil{},["a0","a1","b0","b1"],["shared","oldA","newA","oldB","newB"],True{},0n} : PolicyOutcome}
def preview_keeps_references_and_backing(): {==}
law refusal_stops_prune:
  {run(candidates(),repository(),False{},["a0","b0"]) == Outcome{["a0","b0"],Nil{},["a0","a1","b0","b1"],["shared","oldA","newA","oldB","newB"],False{},3n} : PolicyOutcome}
def refusal_stops_prune(): {==}
law success_reclaims_only_unretained_projection:
  {run(candidates(),repository(),False{},Nil{}) == Outcome{["a0","b0"],["a0","b0"],["a1","b1"],["shared","newA","newB"],True{},0n} : PolicyOutcome}
def success_reclaims_only_unretained_projection(): {==}
# Partial refusal is source-modeled, not a native observation in this band.
law partial_refusal_can_remove_one_reference:
  {run(candidates(),repository(),False{},["b0"]) == Outcome{["a0","b0"],["a0"],["a1","b0","b1"],["shared","oldA","newA","oldB","newB"],False{},3n} : PolicyOutcome}
def partial_refusal_can_remove_one_reference(): {==}
law backend_failure_does_not_change_plan:
  {planned(candidates()) == ["a0","b0"] : List<&2,String>}
def backend_failure_does_not_change_plan(): {==}
law one_group_newest_is_not_displaced:
  {planned([Candidate{"keeper",False{}}]) == Nil{} : List<&2,String>}
def one_group_newest_is_not_displaced(): {==}
law excluded_candidate_is_not_attempted:
  {admitted(["a0"],["a0","b0"]) == ["b0"] : List<&2,String>}
def excluded_candidate_is_not_attempted(): {==}
law no_candidates_has_no_prune_phase:
  {run(Nil{},repository(),False{},Nil{}) == Outcome{Nil{},Nil{},["a0","a1","b0","b1"],["shared","oldA","newA","oldB","newB"],False{},0n} : PolicyOutcome}
def no_candidates_has_no_prune_phase(): {==}

def joined(values: List<&2,String>) -> String:
  match values:
    case Nil{}: ""
    case Con{head,tail}: head ++ ":" ++ joined(tail)
def render(value: PolicyOutcome) -> String:
  match value:
    case Outcome{a,b,c,d,e,f}: joined(a) ++ "|" ++ joined(b) ++ "|" ++ joined(c) ++ "|" ++ joined(d) ++ "|" ++ Bool.pick(String,e,"1","0") ++ "|" ++ Nat.show(f)
def main() -> IO(Unit): IO.print("Planned removals, completed removals, and prune remain separate phases.")
