import Base

def lower(+am: Nat,+an: Nat,ap: Nat,+bm: Nat,+bn: Nat,bp: Nat) -> Bool:
  Bool.or(Nat.is_lt(am,bm),Bool.and(Nat.is_eq(am,bm),Bool.or(Nat.is_lt(an,bn),Bool.and(Nat.is_eq(an,bn),Nat.is_lt(ap,bp)))))
def scope(+root: Nat,+candidate: Nat,recursive: Bool) -> Bool:
  Bool.pick(Bool,recursive,Bool.not(Nat.is_lt(root,candidate)),Nat.is_eq(root,candidate))
def documented_candidate(root: Nat,candidate: Nat) -> Bool:
  Bool.not(Nat.is_lt(candidate,root))
def record_allowed(decline: Bool,lower: Bool,force: Bool) -> Bool:
  Bool.or(decline,Bool.or(Bool.not(lower),force))
def record_decision(+allowed: Bool,+dry: Bool,prior: Bool) -> Bool:
  Bool.or(prior,Bool.and(allowed,Bool.not(dry)))
def record_bump(+allowed: Bool,+dry: Bool,decline: Bool,prior: Bool) -> Bool:
  Bool.pick(Bool,Bool.and(allowed,Bool.not(dry)),Bool.not(decline),prior)
def allowed(lower: Bool,force: Bool) -> Bool:
  Bool.or(Bool.not(lower),force)
def announced(allowed: Bool,release: Bool,selected: Bool) -> Bool:
  Bool.and(allowed,Bool.and(release,selected))
def saved(allowed: Bool,release: Bool,dry: Bool,available: Bool,selected: Bool) -> Bool:
  Bool.and(allowed,Bool.and(release,Bool.and(selected,Bool.and(Bool.not(dry),available))))
def retained(allowed: Bool,+release: Bool,dry: Bool,selected: Bool) -> Bool:
  Bool.and(release,Bool.not(Bool.and(allowed,Bool.and(selected,Bool.and(release,Bool.not(dry))))))
def successful(allowed: Bool,dry: Bool,available: Bool) -> Bool:
  Bool.and(allowed,Bool.or(dry,available))
def selected_number(old: Nat,target: Nat,saved: Bool) -> Nat:
  Bool.pick(Nat,saved,target,old)
def check(ca: Bool,cb: Bool,cc: Bool,+da: Bool,+db: Bool,+dc: Bool,ba: Bool,bb: Bool) -> Bool:
  Bool.and(Bool.or(Bool.not(ca),da),Bool.and(Bool.or(Bool.not(cb),db),Bool.and(Bool.or(Bool.not(cc),dc),Bool.and(Bool.or(Bool.not(ba),db),Bool.or(Bool.not(bb),dc)))))
# Proposed acknowledgement:0 unobserved,1 confirmed exact target,2 conflict,3 unknown.
def candidate_retained(evidence: Nat) -> Bool:
  Bool.not(Nat.is_eq(evidence,1n))
def candidate_retry(evidence: Nat,basis: Bool) -> Bool:
  Bool.and(Nat.is_eq(evidence,0n),basis)

law lower_stable_version:
  {lower(1n,1n,0n,1n,2n,3n) == True{} : Bool}
def lower_stable_version(): {==}
law scope_direction_counterexample:
  {scope(0n,1n,True{}) == False{} : Bool}
def scope_direction_counterexample(): {==}
law dependency_selected:
  {scope(1n,0n,True{}) == True{} : Bool}
def dependency_selected(): {==}
law documented_direction_differs:
  {documented_candidate(0n,1n) == True{} : Bool}
def documented_direction_differs(): {==}
law lower_record_refused:
  {record_allowed(False{},True{},False{}) == False{} : Bool}
def lower_record_refused(): {==}
law lower_apply_needs_force_again:
  {allowed(True{},False{}) == False{} : Bool}
def lower_apply_needs_force_again(): {==}
law preview_retains:
  {retained(True{},True{},True{},True{}) == True{} : Bool}
def preview_retains(): {==}
law failed_input_consumes:
  {retained(True{},True{},False{},True{}) == False{} : Bool}
def failed_input_consumes(): {==}
law failed_input_not_saved:
  {saved(True{},True{},False{},False{},True{}) == False{} : Bool}
def failed_input_not_saved(): {==}
law absent_decision_not_saved:
  {saved(True{},False{},False{},True{},True{}) == False{} : Bool}
def absent_decision_not_saved(): {==}
law announcement_can_precede_failure:
  {announced(True{},True{},True{}) == True{} : Bool}
def announcement_can_precede_failure(): {==}
law decline_resolves_check:
  {check(True{},False{},False{},True{},True{},False{},True{},False{}) == True{} : Bool}
def decline_resolves_check(): {==}
law missing_dependent_decision_blocks:
  {check(True{},False{},False{},True{},False{},False{},True{},False{}) == False{} : Bool}
def missing_dependent_decision_blocks(): {==}
law candidate_unknown_retained:
  {candidate_retained(3n) == True{} : Bool}
def candidate_unknown_retained(): {==}
law candidate_stale_basis_blocks:
  {candidate_retry(0n,False{}) == False{} : Bool}
def candidate_stale_basis_blocks(): {==}

law unselected_release_retained:
  {retained(True{},True{},False{},False{}) == True{} : Bool}
def unselected_release_retained(): {==}
