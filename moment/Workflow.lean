import moment.Model
namespace Moment.Workflow
open Rules

/-- One incident and proposal identity. An exact replay supplies the same
    digest. Readers and reviewers must pass the outer authorization gate. -/
structure State where
  rev : Nat
  graph : List Assertion
  pendingBasis : Option Nat
  outbox : List Nat
  receipt : Option Nat
  deriving DecidableEq

def propose (s : State) (expected : Nat) (allowed : Bool) : State :=
  if allowed && s.rev == expected && s.pendingBasis.isNone && s.receipt.isNone then
    {s with rev := s.rev + 1, pendingBasis := some (s.rev + 1)}
  else s

def publish (s : State) (assertion : Assertion) (intent : Nat) (allowed : Bool) : State :=
  if allowed && s.receipt.isNone && s.pendingBasis == some s.rev then
    { rev := s.rev+1, graph := assertion :: s.graph, pendingBasis := none,
      outbox := intent :: s.outbox, receipt := some (s.rev+1) }
  else s

theorem proposal_no_dispatch (s : State) (e : Nat) (ok : Bool) :
    (propose s e ok).outbox = s.outbox := by unfold propose; split <;> rfl

theorem committed_no_duplicate (s : State) (a : Assertion) (i : Nat) (ok : Bool)
    (r : Nat) (h : s.receipt = some r) : publish s a i ok = s := by simp [publish,h]

inductive Outcome | queued | leased | running | cancelling | unknown | succeeded | failed | cancelled
  deriving DecidableEq, Repr
inductive Signal | claim | dispatch | cancelRequest | cancelledReceipt | success | failure | lost | safeReplay
  deriving DecidableEq
/-- Signals represent already validated receipts, lease/fence checks or proof
    of safe replay. Only their order is abstracted here. -/
def step : Outcome → Signal → Outcome
  | .queued,.claim => .leased
  | .queued,.cancelRequest => .cancelled
  | .leased,.dispatch => .running
  | .leased,.cancelRequest | .running,.cancelRequest => .cancelling
  | .leased,.lost | .running,.lost | .cancelling,.lost => .unknown
  | .running,.success | .cancelling,.success | .unknown,.success => .succeeded
  | .running,.failure | .cancelling,.failure | .unknown,.failure => .failed
  | .leased,.cancelledReceipt | .cancelling,.cancelledReceipt | .unknown,.cancelledReceipt => .cancelled
  | .unknown,.safeReplay => .queued
  | s,_ => s

example : replay step .queued [.claim,.dispatch,.lost,.claim] = .unknown := rfl
example : replay step .queued [.claim,.dispatch,.cancelRequest,.success] = .succeeded := rfl

def empty : State := ⟨3,[],none,[],none⟩
def support : Assertion := ⟨6,⟨0,3,2⟩,true,true⟩
def staged := propose empty 3 true
example : (publish staged support 9 true).outbox = [9] := rfl
example : (publish { staged with rev := 5 } support 9 true).graph = [] := rfl
example : (publish staged support 9 false).receipt = none := rfl
end Moment.Workflow

namespace Moment.Workflow
open Rules
/-- Deny precedence with incomplete evidence, after exact action matching. -/
def policy (denies permits : List Evidence) : Evidence :=
  if denies.contains .yes then .no
  else if denies.contains .unknown then .unknown
  else if permits.contains .yes then .yes
  else if permits.contains .unknown then .unknown else .no

def authorize (chain : List Bool) (denies permits : List Evidence) (capacity : Bool) :=
  chain.all id && policy denies permits == .yes && capacity

example : authorize [true,true] [.unknown] [.yes] true = false := rfl
example : authorize [true,false] [] [.yes] true = false := rfl
example : authorize [true,true] [] [.yes] true = true := rfl
end Moment.Workflow

namespace Moment.Workflow
/-- One event with a proposed graph mutation as its reaction. Policy and
    capacity are sampled again when the prepared mutation reaches commit. -/
def react (edge : EdgeState) (eventSeq : Nat) (readable matchesAtEvent : Bool)
    (s : State) (allowedAtProposal allowedAtCommit : Bool) (remaining cost : Nat) :
    EdgeState × State :=
  let after := scan edge eventSeq readable matchesAtEvent
  if after.pending ≤ edge.pending then (after,s)
  else
    let stagedState := propose s s.rev (dispatch after allowedAtProposal remaining cost)
    if stagedState.rev = s.rev then (after,s)
    else (after, publish stagedState support eventSeq (dispatch after allowedAtCommit remaining cost))

example : (react ⟨0,false,0⟩ 1 true true empty true true 1 1).2.outbox = [1] := rfl
example : (react ⟨0,false,0⟩ 1 true true empty true false 1 1).2 = staged := rfl
example : (react ⟨0,false,0⟩ 1 false true empty true true 1 1).2 = empty := rfl
example : (react ⟨0,false,0⟩ 1 true true staged true true 1 1).2 = staged := rfl
end Moment.Workflow
