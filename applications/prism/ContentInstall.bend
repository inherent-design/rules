import Base

# Policies0=current,1=canonical guard,2=staged proposal.
# Sources0=regular,1=exact path,2=destination symlink alias,3=missing.
# Payload0=absent,1=OLD,2=NEW;not file sizes or pathname identities.
type Request is Data:
  Request{policy: Nat,source: Nat,destination: Nat,payload: Nat,disabled: Bool,drop: Bool,extra_missing: Bool,watching: Bool,refresh: Bool,cancel: Bool}
type Transfer is Data:
  Transfer{reported: Bool,destination: Nat,source_alive: Bool,refresh_calls: Nat}
type Outcome is Data:
  Outcome{surface: Bool,first_item: Bool,extra_missing: Bool,destination: Nat,source_alive: Bool,disabled: Bool,refresh_calls: Nat}
def copied(payload: Nat,+watching: Bool,refresh: Bool) -> Transfer:
  Transfer{Bool.or(watching,refresh),payload,True{},Bool.pick(Nat,watching,0n,1n)}
def transfer(r: Request) -> Transfer:
  match r:
    case Request{+policy,source,+destination,payload,_,_,_,watching,refresh,+cancel}:
      match source:
        case 0n: Bool.pick(Transfer,Bool.and(Nat.is_eq(policy,2n),cancel),Transfer{False{},destination,True{},0n},copied(payload,watching,refresh))
        case 1n: Transfer{False{},destination,Nat.is_ne(destination,0n),0n}
        case 2n:
          Bool.pick(Transfer,Nat.is_eq(policy,1n),Transfer{False{},destination,True{},0n},Bool.pick(Transfer,Nat.is_eq(policy,0n),Transfer{False{},0n,False{},0n},Bool.pick(Transfer,cancel,Transfer{False{},destination,True{},0n},copied(payload,watching,refresh))))
        case _: Transfer{False{},destination,False{},0n}
def result(t: Transfer,drop: Bool,extra_missing: Bool,disabled: Bool) -> Outcome:
  match t:
    case Transfer{+reported,destination,alive,calls}: Outcome{Bool.or(drop,reported),reported,extra_missing,destination,alive,disabled,calls}
def run(r: Request) -> Outcome:
  match r:
    case Request{policy,source,destination,payload,+disabled,+drop,+extra,watching,refresh,cancel}:
      result(transfer(Request{policy,source,destination,payload,disabled,drop,extra,watching,refresh,cancel}),drop,extra,disabled)
def boolean(b: Bool) -> String:
  Bool.pick(String,b,"1","0")
def render(o: Outcome) -> String:
  match o:
    case Outcome{surface,first,extra,destination,alive,disabled,calls}:
      boolean(surface) ++ "/" ++ boolean(first) ++ Bool.pick(String,extra,",0","") ++ "/" ++ Nat.show(destination) ++ "/" ++ boolean(alive) ++ "/" ++ boolean(disabled) ++ "/" ++ Nat.show(calls)

law fresh_copy_has_new_payload:
  {render(run(Request{0n,0n,0n,2n,False{},False{},False{},True{},True{},False{}})) == "1/1/2/1/0/0" : String}
def fresh_copy_has_new_payload(): {==}
law ordinary_overwrite_has_new_payload:
  {render(run(Request{0n,0n,1n,2n,False{},False{},False{},True{},True{},False{}})) == "1/1/2/1/0/0" : String}
def ordinary_overwrite_has_new_payload(): {==}
law same_path_is_refused:
  {render(run(Request{0n,1n,1n,1n,False{},False{},False{},True{},True{},False{}})) == "0/0/1/1/0/0" : String}
def same_path_is_refused(): {==}
law original_refusal_loses_old_payload:
  {render(run(Request{0n,2n,1n,1n,False{},False{},False{},True{},True{},False{}})) == "0/0/0/0/0/0" : String}
def original_refusal_loses_old_payload(): {==}
law handled_drop_can_contain_loss:
  {render(run(Request{0n,2n,1n,1n,False{},True{},False{},True{},True{},False{}})) == "1/0/0/0/0/0" : String}
def handled_drop_can_contain_loss(): {==}
law guarded_alias_keeps_old_payload:
  {render(run(Request{1n,2n,1n,1n,False{},False{},False{},True{},True{},False{}})) == "0/0/1/1/0/0" : String}
def guarded_alias_keeps_old_payload(): {==}
law staged_alias_uses_captured_payload:
  {render(run(Request{2n,2n,1n,1n,False{},False{},False{},True{},True{},False{}})) == "1/1/1/1/0/0" : String}
def staged_alias_uses_captured_payload(): {==}
law same_payload_is_not_same_identity:
  {render(run(Request{1n,0n,2n,2n,False{},False{},False{},True{},True{},False{}})) == "1/1/2/1/0/0" : String}
def same_payload_is_not_same_identity(): {==}
law canceled_stage_keeps_old_payload:
  {render(run(Request{2n,0n,1n,2n,False{},False{},False{},True{},True{},True{}})) == "0/0/1/1/0/0" : String}
def canceled_stage_keeps_old_payload(): {==}
law refresh_refusal_does_not_undo_copy:
  {render(run(Request{0n,0n,0n,2n,False{},False{},False{},False{},False{},False{}})) == "0/0/2/1/0/1" : String}
def refresh_refusal_does_not_undo_copy(): {==}
law drop_has_per_item_results:
  {render(run(Request{0n,0n,0n,2n,False{},True{},True{},True{},True{},False{}})) == "1/1,0/2/1/0/0" : String}
def drop_has_per_item_results(): {==}
law disabled_sibling_is_preserved:
  {render(run(Request{0n,0n,0n,2n,True{},False{},False{},True{},True{},False{}})) == "1/1/2/1/1/0" : String}
def disabled_sibling_is_preserved(): {==}
law missing_source_does_not_write:
  {render(run(Request{0n,3n,1n,0n,False{},False{},False{},True{},True{},False{}})) == "0/0/1/0/0/0" : String}
def missing_source_does_not_write(): {==}
