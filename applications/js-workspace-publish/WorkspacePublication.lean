import applications.«js-peers».Publication

namespace ApplicationStudy.WorkspacePublication
open JsPublication

inductive Failure | none | producerLate | privateEarly
  deriving BEq, ReflBEq, LawfulBEq, DecidableEq, Repr

/-- Fixed generated graph: private leaf, consumer → producer. npm selects in
declaration order; the pnpm recursive and explicit Yarn -t profiles are ordered
by that edge. This is not a general workspace scheduler or range resolver. -/
structure Result where
  privateHook : Bool
  producerAccepted : Bool
  consumerAccepted : Bool
  consumerBlocked : Bool
  order : Nat
  rewritten : Bool
  summaryCount : Nat
  code : Nat
  deriving BEq, DecidableEq, Repr

def run (p : Profile) (f : Failure) : Result :=
  let npm := p == .npm
  let early := npm && f == .privateEarly
  let producer := publish p { hooks := true, hookFailure := if f == .producerLate then .afterUpload else .none }
  let consumer := publish p { hooks := true }
  let producerAccepted := !early && producer.acceptedHere
  let consumerAccepted := !early && (npm || producer.exitCode == 0) && consumer.acceptedHere
  { privateHook := npm
    producerAccepted := producerAccepted
    consumerAccepted := consumerAccepted
    consumerBlocked := !early && !npm && producer.exitCode != 0
    order := if early then 0 else if npm then 12 else if consumerAccepted then 21 else 2
    rewritten := !npm && consumerAccepted
    summaryCount := if p == .pnpm then (if producerAccepted then 1 else 0) + (if consumerAccepted then 1 else 0) else 0
    code := if early then 7 else producer.exitCode }

theorem npm_private_failure_prevents_publication :
    (run .npm .privateEarly).producerAccepted = false ∧
    (run .npm .privateEarly).consumerAccepted = false := ⟨rfl, rfl⟩
theorem npm_private_flag_does_not_skip_preparation :
    (run .npm .none).privateHook = true := rfl
theorem pnpm_private_filter_is_before_hooks (f : Failure) :
    (run .pnpm f).privateHook = false := by cases f <;> rfl
theorem yarn_explicit_private_filter_is_before_hooks (f : Failure) :
    (run .yarn f).privateHook = false := by cases f <;> rfl
theorem npm_late_failure_keeps_both_uploads :
    (run .npm .producerLate).producerAccepted = true ∧
    (run .npm .producerLate).consumerAccepted = true ∧
    (run .npm .producerLate).code = 7 := ⟨rfl, rfl, rfl⟩
theorem pnpm_late_failure_keeps_producer :
    (run .pnpm .producerLate).producerAccepted = true ∧
    (run .pnpm .producerLate).consumerBlocked = true ∧
    (run .pnpm .producerLate).summaryCount = 1 := ⟨rfl, rfl, rfl⟩
theorem yarn_late_failure_keeps_producer :
    (run .yarn .producerLate).producerAccepted = true ∧
    (run .yarn .producerLate).consumerBlocked = true := ⟨rfl, rfl⟩
theorem npm_order_is_not_dependency_order :
    (run .npm .none).order = 12 := rfl
theorem selected_topological_orders_agree :
    (run .pnpm .none).order = 21 ∧ (run .yarn .none).order = 21 := ⟨rfl, rfl⟩
theorem workspace_protocol_is_projected_in_selected_archives :
    (run .pnpm .none).rewritten = true ∧ (run .yarn .none).rewritten = true := ⟨rfl, rfl⟩
theorem summary_is_not_whole_batch_success :
    (run .pnpm .producerLate).summaryCount = 1 ∧ (run .pnpm .producerLate).code = 1 := ⟨rfl, rfl⟩

end ApplicationStudy.WorkspacePublication
