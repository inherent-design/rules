import Base

# Kinds0=init,1=open,2=list migrations,3=apply migrations.
# Version0=absent config. Admitted IO/config/key evidence is external.
type Request is Data:
  Request{kind: Nat,requested: Nat,version: Nat,keys: Bool,snapshots: Bool,other_password: Bool,known: Bool,unknown: Bool,strict: Bool}
type Outcome is Data:
  Outcome{status: Nat,version: Nat,changed: Bool,unknown: Bool,skipped: Bool,applied: Bool,listed: Bool}
def initialize(+requested: Nat,+version: Nat,keys: Bool,snapshots: Bool) -> Outcome:
  refuses=Bool.or(Bool.not(Bool.or(Nat.is_eq(requested,1n),Nat.is_eq(requested,2n))),Bool.or(Nat.is_ne(version,0n),Bool.or(keys,snapshots)))
  Bool.pick(Outcome,refuses,Outcome{1n,version,False{},False{},False{},False{},False{}},Outcome{0n,requested,True{},False{},False{},False{},False{}})
def apply_migrations(+version: Nat,+known: Bool,+unknown: Bool,strict: Bool) -> Outcome:
  +applies=Bool.and(known,Nat.is_eq(version,1n))
  Outcome{Bool.pick(Nat,Bool.and(strict,unknown),1n,0n),Bool.pick(Nat,applies,2n,version),applies,unknown,Bool.and(known,Nat.is_ne(version,1n)),applies,False{}}
def run(r: Request) -> Outcome:
  match r:
    case Request{kind,+requested,+version,keys,snapshots,other_password,+known,+unknown,strict}:
      match kind:
        case 0n: initialize(requested,version,keys,snapshots)
        case 1n: Outcome{Bool.pick(Nat,Nat.is_eq(version,0n),10n,Bool.pick(Nat,other_password,12n,0n)),version,False{},False{},False{},False{},False{}}
        case 2n: Outcome{0n,version,False{},False{},False{},False{},Nat.is_eq(version,1n)}
        case _: apply_migrations(version,known,unknown,strict)
def bit(b: Bool) -> String:
  Bool.pick(String,b,"1","0")
def render(o: Outcome) -> String:
  match o:
    case Outcome{status,version,changed,unknown,skipped,applied,listed}:
      Nat.show(status) ++ "/" ++ Nat.show(version) ++ "/" ++ bit(changed) ++ "/" ++ bit(unknown) ++ "/" ++ bit(skipped) ++ "/" ++ bit(applied) ++ "/" ++ bit(listed)

law init_selects_requested_format:
  {render(run(Request{0n,1n,0n,False{},False{},False{},False{},False{},False{}})) == "0/1/1/0/0/0/0" : String}
def init_selects_requested_format(): {==}
law unsupported_init_keeps_config_absent:
  {render(run(Request{0n,99n,0n,False{},False{},False{},False{},False{},False{}})) == "1/0/0/0/0/0/0" : String}
def unsupported_init_keeps_config_absent(): {==}
law existing_keys_guard_initialization:
  {render(run(Request{0n,2n,0n,True{},False{},False{},False{},False{},False{}})) == "1/0/0/0/0/0/0" : String}
def existing_keys_guard_initialization(): {==}
law snapshots_guard_initialization:
  {render(run(Request{0n,2n,0n,False{},True{},False{},False{},False{},False{}})) == "1/0/0/0/0/0/0" : String}
def snapshots_guard_initialization(): {==}
law missing_config_precedes_authentication:
  {render(run(Request{1n,2n,0n,False{},False{},True{},False{},False{},False{}})) == "10/0/0/0/0/0/0" : String}
def missing_config_precedes_authentication(): {==}
law unknown_migration_can_return_zero:
  {render(run(Request{3n,2n,1n,True{},True{},False{},False{},True{},False{}})) == "0/1/0/1/0/0/0" : String}
def unknown_migration_can_return_zero(): {==}
law unknown_name_does_not_stop_known_upgrade:
  {render(run(Request{3n,2n,1n,True{},True{},False{},True{},True{},False{}})) == "0/2/1/1/0/1/0" : String}
def unknown_name_does_not_stop_known_upgrade(): {==}
law repeated_upgrade_can_skip_successfully:
  {render(run(Request{3n,2n,2n,True{},True{},False{},True{},False{},False{}})) == "0/2/0/0/1/0/0" : String}
def repeated_upgrade_can_skip_successfully(): {==}
law proposed_nonzero_does_not_undo_applied_upgrade:
  {render(run(Request{3n,2n,1n,True{},True{},False{},True{},True{},True{}})) == "1/2/1/1/0/1/0" : String}
def proposed_nonzero_does_not_undo_applied_upgrade(): {==}
