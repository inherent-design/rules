import Base

type Backings is Data:
  Backings{source: Nat, destination: Nat}
type SyncFailure is Data:
  NoFailure{}
  RemoveFailure{}
  MoveFailure{}
type SyncOutcome is Data:
  SyncOutcome{files: Backings, failure: SyncFailure, retained: Nat}

def non_overwrite(xs: List<&2, Nat>) -> List<&2, Nat>:
  match xs:
    case Nil{}: Nil{}
    case Con{head,tail}:
      +h = head
      +remaining = non_overwrite(tail)
      Bool.pick(List<&2, Nat>,Nat.is_eq(h,0n),remaining,Con{h,remaining})

def options(metadata: Bool, known: Bool, primary: Nat, alternatives: List<&2, Nat>) -> List<&2, Nat>:
  Bool.pick(List<&2, Nat>,metadata,Nil{},Bool.pick(List<&2, Nat>,known,Con{3n,non_overwrite(Con{primary,alternatives})},Con{3n,Nil{}}))

def last_with(xs: List<&2, Nat>, acc: Nat) -> Nat:
  match xs:
    case Nil{}: acc
    case Con{head,tail}: last_with(tail,head)

def last_or_zero(xs: List<&2, Nat>) -> Nat:
  last_with(xs,0n)

def contains(+value: Nat, xs: List<&2, Nat>) -> Bool:
  match xs:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(Nat.is_eq(value,head),contains(value,tail))

def choose(+xs: List<&2, Nat>, +requested: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(requested,0n),last_or_zero(xs),Bool.pick(Nat,contains(requested,xs),requested,0n))

def apply_fields(+source: Nat, +destination: Nat, +choice: Nat, remove_ok: Bool, move_ok: Bool) -> SyncOutcome:
  Bool.pick(SyncOutcome,Bool.or(Nat.is_eq(choice,0n),Nat.is_eq(choice,3n)),SyncOutcome{Backings{source,destination},NoFailure{},0n},Bool.pick(SyncOutcome,remove_ok,Bool.pick(SyncOutcome,move_ok,SyncOutcome{Backings{0n,source},NoFailure{},0n},SyncOutcome{Backings{source,0n},MoveFailure{},0n}),SyncOutcome{Backings{source,destination},RemoveFailure{},0n}))

def apply(files: Backings, choice: Nat, remove_ok: Bool, move_ok: Bool) -> SyncOutcome:
  match files:
    case Backings{source,destination}: apply_fields(source,destination,choice,remove_ok,move_ok)

def retain_fields(files: Backings, failure: SyncFailure, prior: Nat, retained: Nat) -> SyncOutcome:
  match failure:
    case NoFailure{}: SyncOutcome{files,NoFailure{},retained}
    case RemoveFailure{}: SyncOutcome{files,RemoveFailure{},retained}
    case MoveFailure{}: SyncOutcome{files,MoveFailure{},prior}

def retain_if_move_error(out: SyncOutcome, prior: Nat) -> SyncOutcome:
  match out:
    case SyncOutcome{files,failure,retained}: retain_fields(files,failure,prior,retained)

def kept_prior(out: SyncOutcome) -> Nat:
  match out:
    case SyncOutcome{files,failure,retained}: retained

def files(out: SyncOutcome) -> Backings:
  match out:
    case SyncOutcome{value,failure,retained}: value

def failure_text(failure: SyncFailure) -> String:
  match failure:
    case NoFailure{}: "none"
    case RemoveFailure{}: "remove"
    case MoveFailure{}: "move"

def failure_name(out: SyncOutcome) -> String:
  match out:
    case SyncOutcome{files,failure,retained}: failure_text(failure)

law no_metadata_widget:
  {options(True{},True{},0n,Con{1n,Nil{}}) == Nil{} : List<&2, Nat>}
def no_metadata_widget():
  {==}

law unknown_entry_offers_only_no_sync:
  {options(False{},False{},0n,Con{1n,Nil{}}) == Con{3n,Nil{}} : List<&2, Nat>}
def unknown_entry_offers_only_no_sync():
  {==}

law overwrite_origin_is_not_a_target:
  {options(False{},True{},0n,Nil{}) == Con{3n,Nil{}} : List<&2, Nat>}
def overwrite_origin_is_not_a_target():
  {==}

law explicit_no_sync_preserves_backings:
  {files(apply(Backings{1n,2n},3n,True{},True{})) == Backings{1n,2n} : Backings}
def explicit_no_sync_preserves_backings():
  {==}

law remove_refusal_preserves_backings:
  {files(apply(Backings{1n,2n},1n,False{},False{})) == Backings{1n,2n} : Backings}
def remove_refusal_preserves_backings():
  {==}

law failed_move_has_no_current_destination:
  {files(apply(Backings{1n,2n},1n,True{},False{})) == Backings{1n,0n} : Backings}
def failed_move_has_no_current_destination():
  {==}

law missing_source_does_not_save_old_destination:
  {files(apply(Backings{0n,2n},1n,True{},False{})) == Backings{0n,0n} : Backings}
def missing_source_does_not_save_old_destination():
  {==}

law successful_move_transfers_object:
  {files(apply(Backings{3n,2n},1n,True{},True{})) == Backings{0n,3n} : Backings}
def successful_move_transfers_object():
  {==}
