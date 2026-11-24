import Base

# Closed native profile. These IDs are research equality labels, not hashes.
type PatchProfile is Data:
  Pnpm{}
  Yarn{}
type PatchImage is Data:
  PatchImage{recipe: Nat, lock: Nat, live: Nat, payload: Nat, patch_file: Bool}
type PatchAction is Data:
  Observe{}
  Prepare{import_existing: Bool}
  Commit{}
  Install{frozen: Bool, force: Bool}
  Remove{key_matches: Bool}
  Unplug{}
type PatchOutcome is Data:
  PatchOutcome{status: Nat, image: PatchImage, prepared: Nat}

def is_pnpm(p: PatchProfile) -> Bool:
  match p:
    case Pnpm{}: True{}
    case Yarn{}: False{}
def recipe(s: PatchImage) -> Nat:
  match s:
    case PatchImage{r,k,l,b,f}: r
def lock(s: PatchImage) -> Nat:
  match s:
    case PatchImage{r,k,l,b,f}: k
def payload(s: PatchImage) -> Nat:
  match s:
    case PatchImage{r,k,l,b,f}: b
def target(s: PatchImage) -> Nat:
  Nat.add(recipe(s),1n)
def okay(s: PatchImage) -> PatchOutcome:
  PatchOutcome{0n,s,0n}
def refused(s: PatchImage) -> PatchOutcome:
  PatchOutcome{1n,s,0n}
def save(s: PatchImage) -> PatchImage:
  match s:
    case PatchImage{r,k,l,b,f}: PatchImage{1n,k,l,b,True{}}
def clear(s: PatchImage) -> PatchImage:
  match s:
    case PatchImage{r,k,l,b,f}: PatchImage{0n,k,l,b,False{}}
def invalid_live(s: PatchImage) -> PatchImage:
  match s:
    case PatchImage{r,k,l,b,f}: PatchImage{r,k,3n,1n,f}
def materialize(p: PatchProfile,s: PatchImage) -> PatchImage:
  match s:
    case PatchImage{+r,k,l,b,f}:
      PatchImage{r,Nat.add(r,1n),Bool.pick(Nat,is_pnpm(p),Nat.add(r,1n),1n),Bool.pick(Nat,Nat.is_eq(r,0n),1n,2n),f}

# This is the measured profile's projection, not the full source admission gate.
def install_current(+p: PatchProfile,+s: PatchImage,frozen: Bool,force: Bool) -> PatchOutcome:
  mismatch = Bool.and(frozen,Bool.not(Nat.is_eq(lock(s),target(s))))
  bad = Nat.is_eq(recipe(s),2n)
  reuse = Bool.and(is_pnpm(p),Bool.and(Bool.not(force),Bool.and(Nat.is_eq(lock(s),target(s)),Bool.not(Nat.is_eq(payload(s),0n)))))
  Bool.pick(PatchOutcome,mismatch,refused(s),
    Bool.pick(PatchOutcome,bad,Bool.pick(PatchOutcome,is_pnpm(p),PatchOutcome{1n,invalid_live(s),0n},refused(s)),
      Bool.pick(PatchOutcome,reuse,okay(s),okay(materialize(p,s)))))

# Proposed conservative private-candidate/finalization policy, not native proof.
def install_proposed(p: PatchProfile,+s: PatchImage,frozen: Bool) -> PatchOutcome:
  fail = Bool.or(Bool.and(frozen,Bool.not(Nat.is_eq(lock(s),target(s)))),Nat.is_eq(recipe(s),2n))
  Bool.pick(PatchOutcome,fail,refused(s),okay(materialize(p,s)))
def install(p: PatchProfile,s: PatchImage,frozen: Bool,force: Bool,proposed: Bool) -> PatchOutcome:
  match proposed:
    case True{}: install_proposed(p,s,frozen)
    case False{}: install_current(p,s,frozen,force)
def run(+p: PatchProfile,+s: PatchImage,a: PatchAction,+proposed: Bool) -> PatchOutcome:
  match a:
    case Observe{}: okay(s)
    case Prepare{existing}: PatchOutcome{0n,s,Bool.pick(Nat,Bool.and(existing,Nat.is_eq(recipe(s),1n)),2n,1n)}
    case Commit{}: Bool.pick(PatchOutcome,is_pnpm(p),install(p,save(s),False{},False{},proposed),okay(save(s)))
    case Install{frozen,force}: install(p,s,frozen,force,proposed)
    case Remove{key_matches}: Bool.pick(PatchOutcome,Bool.and(is_pnpm(p),key_matches),install(p,clear(s),False{},False{},proposed),refused(s))
    case Unplug{}: refused(s)

law preparation_retains_published_scope:
  for p: PatchProfile
  for +s: PatchImage
  for existing: Bool
  {run(p,s,Prepare{existing},False{}) == PatchOutcome{0n,s,Bool.pick(Nat,Bool.and(existing,Nat.is_eq(recipe(s),1n)),2n,1n)} : PatchOutcome}
def preparation_retains_published_scope(p,s,existing):
  {==}
law pnpm_commit_installs:
  {run(Pnpm{},PatchImage{0n,1n,1n,1n,False{}},Commit{},False{}) == PatchOutcome{0n,PatchImage{1n,2n,2n,2n,True{}},0n} : PatchOutcome}
def pnpm_commit_installs():
  {==}
law yarn_saved_recipe_is_not_installed:
  {run(Yarn{},PatchImage{0n,1n,1n,1n,False{}},Commit{},False{}) == PatchOutcome{0n,PatchImage{1n,1n,1n,1n,True{}},0n} : PatchOutcome}
def yarn_saved_recipe_is_not_installed():
  {==}
law yarn_immutable_refuses_new_recipe:
  {run(Yarn{},PatchImage{1n,1n,1n,1n,True{}},Install{True{},False{}},False{}) == PatchOutcome{1n,PatchImage{1n,1n,1n,1n,True{}},0n} : PatchOutcome}
def yarn_immutable_refuses_new_recipe():
  {==}
law current_failed_patch_can_change_live_target:
  {run(Pnpm{},PatchImage{2n,2n,2n,2n,True{}},Install{False{},False{}},False{}) == PatchOutcome{1n,PatchImage{2n,2n,3n,1n,True{}},0n} : PatchOutcome}
def current_failed_patch_can_change_live_target():
  {==}
law restored_recipe_can_leave_wrong_bytes_after_success:
  {run(Pnpm{},PatchImage{1n,2n,3n,1n,True{}},Install{False{},False{}},False{}) == PatchOutcome{0n,PatchImage{1n,2n,3n,1n,True{}},0n} : PatchOutcome}
def restored_recipe_can_leave_wrong_bytes_after_success():
  {==}
law force_repairs_selected_counterexample:
  {run(Pnpm{},PatchImage{1n,2n,3n,1n,True{}},Install{False{},True{}},False{}) == PatchOutcome{0n,PatchImage{1n,2n,2n,2n,True{}},0n} : PatchOutcome}
def force_repairs_selected_counterexample():
  {==}
law missing_selector_is_not_patch_removal:
  {run(Pnpm{},PatchImage{1n,2n,2n,2n,True{}},Remove{False{}},False{}) == PatchOutcome{1n,PatchImage{1n,2n,2n,2n,True{}},0n} : PatchOutcome}
def missing_selector_is_not_patch_removal():
  {==}
law proposed_failure_preserves_live_target:
  {run(Pnpm{},PatchImage{2n,2n,2n,2n,True{}},Install{False{},False{}},True{}) == PatchOutcome{1n,PatchImage{2n,2n,2n,2n,True{}},0n} : PatchOutcome}
def proposed_failure_preserves_live_target():
  {==}
law proposed_materialization_restores_valid_selection:
  {run(Pnpm{},PatchImage{1n,2n,3n,1n,True{}},Install{False{},False{}},True{}) == PatchOutcome{0n,PatchImage{1n,2n,2n,2n,True{}},0n} : PatchOutcome}
def proposed_materialization_restores_valid_selection():
  {==}
