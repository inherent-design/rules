import Base

type Policy is Data:
  Free{}
  AlwaysOn{}
  AlwaysOff{}

type Entry is Data:
  Entry{id: Nat, policy: Policy, enabled: Bool}

type Work is Data:
  Work{entries: List<&2, Entry>, dirty: List<&2, Nat>, errors: Nat}

def single_value(policy: Policy, wanted: Bool) -> Bool:
  match policy:
    case Free{}: wanted
    case AlwaysOn{}: True{}
    case AlwaysOff{}: False{}

def on_value(policy: Policy, old: Bool) -> Bool:
  match policy:
    case Free{}: True{}
    case AlwaysOn{}: True{}
    case AlwaysOff{}: old

def off_value(policy: Policy, old: Bool) -> Bool:
  match policy:
    case Free{}: False{}
    case AlwaysOn{}: old
    case AlwaysOff{}: False{}

def batch_value(wanted: Bool, policy: Policy, old: Bool) -> Bool:
  match wanted:
    case True{}: on_value(policy, old)
    case False{}: off_value(policy, old)

def find_entry(entries: List<&2, Entry>, +id: Nat) -> Maybe<&2, Entry>:
  match entries:
    case Nil{}: None{}
    case Con{+head, tail}:
      match head:
        case Entry{+key, policy, enabled}:
          Bool.pick(Maybe<&2, Entry>,Nat.is_eq(key,id),Some{Entry{key,policy,enabled}},find_entry(tail,id))

def set_enabled(entries: List<&2, Entry>, +id: Nat, +value: Bool) -> List<&2, Entry>:
  match entries:
    case Nil{}: []
    case Con{head, +tail}:
      match head:
        case Entry{+key, +policy, +old}:
          Bool.pick(List<&2, Entry>,Nat.is_eq(key,id),Con{Entry{key,policy,value},tail},Con{Entry{key,policy,old},set_enabled(tail,id,value)})

def choose_value(batch: Bool, +wanted: Bool, +policy: Policy, old: Bool) -> Bool:
  match batch:
    case True{}: batch_value(wanted,policy,old)
    case False{}: single_value(policy,wanted)

def changed(same: Bool, +entries: List<&2, Entry>, +dirty: List<&2, Nat>, errors: Nat, +id: Nat, value: Bool) -> Work:
  match same:
    case True{}: Work{entries,dirty,errors}
    case False{}: Work{set_enabled(entries,id,value),List.append(&2,Nat,dirty,[id]),errors}

def apply_value(+value: Bool, old: Bool, entries: List<&2, Entry>, dirty: List<&2, Nat>, errors: Nat, id: Nat) -> Work:
  changed(Bool.not(Bool.xor(old,value)),entries,dirty,errors,id,value)

def observed(found: Maybe<&2, Entry>, entries: List<&2, Entry>, dirty: List<&2, Nat>, errors: Nat, batch: Bool, id: Nat, wanted: Bool) -> Work:
  match found:
    case None{}: Work{entries,dirty,Nat.add(errors,1n)}
    case Some{entry}:
      match entry:
        case Entry{key,+policy,+old}:
          apply_value(choose_value(batch,wanted,policy,old),old,entries,dirty,errors,id)

def request(work: Work, batch: Bool, +id: Nat, wanted: Bool) -> Work:
  match work:
    case Work{+entries,dirty,errors}:
      observed(find_entry(entries,id),entries,dirty,errors,batch,id,wanted)

def pass(ids: List<&2, Nat>, work: Work, +wanted: Bool) -> Work:
  match ids:
    case Nil{}: work
    case Con{head,tail}: pass(tail,request(work,True{},head,wanted),wanted)

def single(entries: List<&2, Entry>, id: Nat, wanted: Bool) -> Work:
  request(Work{entries,[],0n},False{},id,wanted)

def batch(entries: List<&2, Entry>, enable: List<&2, Nat>, disable: List<&2, Nat>) -> Work:
  pass(disable,pass(enable,Work{entries,[],0n},True{}),False{})

law single_forces_on:
  for wanted: Bool
  {single_value(AlwaysOn{},wanted) == True{} : Bool}
def single_forces_on(wanted):
  {==}

law single_forces_off:
  for wanted: Bool
  {single_value(AlwaysOff{},wanted) == False{} : Bool}
def single_forces_off(wanted):
  {==}

law single_free_uses_request:
  for +wanted: Bool
  {single_value(Free{},wanted) == wanted : Bool}
def single_free_uses_request(wanted):
  {==}

law batch_does_not_repair_inconsistent_forced_state:
  {batch_value(False{},AlwaysOn{},False{}) == False{} : Bool}
def batch_does_not_repair_inconsistent_forced_state():
  {==}

def main() -> IO(Unit):
  IO.print("Profile activation projection;signals are not completed VFS or persistence receipts.")
