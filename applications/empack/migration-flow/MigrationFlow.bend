import Base
# Current captured one-root provider profile only. IDs1/2 are equality labels;
# target eligibility comes from independently checked sampled metadata.
type State is Data:
  State{pin: Nat,selected: Nat,game: Nat,payload: Nat}
def pin(s: State) -> Nat:
  match s:
    case State{p,_,_,_}: p
def selected(s: State) -> Nat:
  match s:
    case State{_,v,_,_}: v
def game(s: State) -> Nat:
  match s:
    case State{_,_,g,_}: g
def eligible(s: State) -> Bool:
  Bool.not(Nat.is_eq(pin(s),2n))
# operations:0sync,1prefix-preview,2preview,3apply,4unpin,5check.
def canonical(proposed: Bool,+op: Nat) -> Nat:
  Bool.pick(Nat,Bool.and(proposed,Nat.is_eq(op,1n)),2n,op)
def code(s: State,+op: Nat,proposed: Bool) -> Nat:
  +actual = canonical(proposed,op)
  Bool.pick(Nat,Nat.is_eq(actual,1n),2n,Bool.pick(Nat,Bool.or(Nat.is_eq(actual,2n),Nat.is_eq(actual,3n)),Bool.pick(Nat,eligible(s),0n,4n),0n))
def step(+s: State,+op: Nat) -> State:
  match s:
    case State{+p,+v,+g,+b}:
      Bool.pick(State,Nat.is_eq(op,0n),State{p,p,g,b},
        Bool.pick(State,Nat.is_eq(op,4n),State{0n,v,g,b},
          Bool.pick(State,Bool.and(Nat.is_eq(op,3n),Bool.not(Nat.is_eq(p,2n))),State{p,1n,2n,b},State{p,v,g,b})))
def changes(+s: State,+op: Nat) -> String:
  Bool.pick(String,Nat.is_eq(op,0n),Bool.pick(String,Nat.is_eq(selected(s),0n),"[\"empack.lock\"]","[]"),
    Bool.pick(String,Bool.or(Bool.and(Nat.is_eq(op,4n),Bool.not(Nat.is_eq(pin(s),0n))),Bool.and(Nat.is_eq(op,3n),Bool.and(eligible(s),Bool.not(Nat.is_eq(game(s),2n))))),"[\"empack.lock\",\"empack.yml\"]","[]"))
def state_changed(s: State,op: Nat) -> Bool:
  Bool.not(String.eq(changes(s,op),"[]"))
def facet(s: State,op: Nat,proposed: Bool) -> String:
  +actual = canonical(proposed,op)
  Bool.pick(String,Nat.is_eq(actual,2n),Bool.pick(String,eligible(s),"[1,1,2,0]","[]"),Bool.pick(String,Nat.is_eq(actual,5n),"[1,0,1]","[]"))
def render_state(s: State) -> String:
  match s:
    case State{p,v,g,b}:
      "{\"pin\":" ++ Nat.show(p) ++ ",\"selected\":" ++ Nat.show(v) ++ ",\"game\":" ++ Nat.show(g) ++ ",\"payload\":" ++ Nat.show(b) ++ "}"
def bit(b: Bool) -> String:
  Bool.pick(String,b,"true","false")
def render(id: String,project: String,+before: State,+op: Nat) -> String:
  "{\"id\":\"" ++ id ++ "\",\"project\":\"" ++ project ++ "\",\"before\":" ++ render_state(before) ++ ",\"after\":" ++ render_state(step(before,op)) ++ ",\"exit\":" ++ Nat.show(code(before,op,False{})) ++ ",\"projectChanges\":" ++ changes(before,op) ++ ",\"stateChanged\":" ++ bit(state_changed(before,op)) ++ ",\"cacheChanged\":false,\"facet\":" ++ facet(before,op,False{}) ++ "}"
# Proposed post-parse guard; no production parser was changed.
def json_mode_allowed(preview: Bool) -> Bool:
  preview

law unpin_retains_selection:
  {selected(step(State{2n,2n,1n,0n},4n)) == 2n : Nat}
def unpin_retains_selection(): {==}
law unpin_is_not_migration:
  {game(step(State{2n,2n,1n,0n},4n)) == 1n : Nat}
def unpin_is_not_migration(): {==}
law preview_keeps_state:
  {render_state(step(State{1n,1n,1n,0n},2n)) == render_state(State{1n,1n,1n,0n}) : String}
def preview_keeps_state(): {==}
law incompatible_pin_refuses:
  {code(State{2n,2n,1n,0n},3n,False{}) == 4n : Nat}
def incompatible_pin_refuses(): {==}
law refused_apply_keeps_state:
  {render_state(step(State{2n,2n,1n,0n},3n)) == render_state(State{2n,2n,1n,0n}) : String}
def refused_apply_keeps_state(): {==}
law compatible_pin_kept:
  {render_state(step(State{1n,1n,1n,0n},3n)) == render_state(State{1n,1n,2n,0n}) : String}
def compatible_pin_kept(): {==}
law automatic_not_repinned:
  {render_state(step(State{0n,2n,1n,0n},3n)) == render_state(State{0n,1n,2n,0n}) : String}
def automatic_not_repinned(): {==}
law sync_records_reference:
  {render_state(step(State{1n,0n,1n,0n},0n)) == render_state(State{1n,1n,1n,0n}) : String}
def sync_records_reference(): {==}
law apply_changes_two_documents:
  {changes(State{1n,1n,1n,0n},3n) == "[\"empack.lock\",\"empack.yml\"]" : String}
def apply_changes_two_documents(): {==}
law check_not_materialization:
  {render_state(step(State{1n,1n,2n,0n},5n)) == render_state(State{1n,1n,2n,0n}) : String}
def check_not_materialization(): {==}
law reference_can_be_complete:
  {facet(State{1n,1n,2n,0n},5n,False{}) == "[1,0,1]" : String}
def reference_can_be_complete(): {==}
law current_prefix_usage:
  {code(State{1n,1n,1n,0n},1n,False{}) == 2n : Nat}
def current_prefix_usage(): {==}
law suffix_preview_ready:
  {facet(State{1n,1n,1n,0n},2n,False{}) == "[1,1,2,0]" : String}
def suffix_preview_ready(): {==}
law proposed_prefix_matches_suffix:
  {code(State{1n,1n,1n,0n},1n,True{}) == code(State{1n,1n,1n,0n},2n,False{}) : Nat}
def proposed_prefix_matches_suffix(): {==}
law proposed_prefix_facet_matches:
  {facet(State{1n,1n,1n,0n},1n,True{}) == facet(State{1n,1n,1n,0n},2n,False{}) : String}
def proposed_prefix_facet_matches(): {==}
law proposed_json_still_requires_preview:
  {json_mode_allowed(False{}) == False{} : Bool}
def proposed_json_still_requires_preview(): {==}
