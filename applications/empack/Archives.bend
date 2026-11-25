import Base

def opaque_name(common: Bool, drive: Bool) -> Bool:
  Bool.and(Bool.not(common), Bool.not(drive))
def portable_name(common: Bool, drive: Bool, extra: Bool) -> Bool:
  Bool.and(opaque_name(common, drive), Bool.not(extra))
type ArchiveOutcome is Data:
  Outcome{code: Nat, checks: Nat}
type ArchiveRecord is Data:
  Record{header: Maybe<&2, Bool>, signature: Maybe<&2, Bool>, name: Maybe<&2, Bool>, utf8: Maybe<&2, Bool>, unique: Maybe<&2, Bool>, span: Maybe<&2, Bool>}
def stop(code: Nat) -> Maybe<&2, ArchiveOutcome>:
  Some{Outcome{code, 0n}}
def gate(fact: Maybe<&2, Bool>, code: Nat, next: Maybe<&2, ArchiveOutcome>) -> Maybe<&2, ArchiveOutcome>:
  match fact:
    case None{}: None{}
    case Some{value}: Bool.pick(Maybe<&2, ArchiveOutcome>, value, next, stop(code))
def record_decision(r: ArchiveRecord) -> Maybe<&2, ArchiveOutcome>:
  match r:
    case Record{header, signature, name, utf8, unique, span}:
      gate(header,10n,gate(signature,9n,gate(name,10n,gate(utf8,11n,gate(unique,12n,gate(span,14n,stop(0n)))))))
def add_check(value: Maybe<&2, ArchiveOutcome>) -> Maybe<&2, ArchiveOutcome>:
  match value:
    case None{}: None{}
    case Some{out}:
      match out:
        case Outcome{code, checks}: Some{Outcome{code, (checks + 1n : Nat)}}
def cancelled(at: Maybe<&2, Nat>, index: Nat) -> Bool:
  match at:
    case None{}: False{}
    case Some{n}: Bool.not(Nat.is_lt(index, n))
def prepend_checked(checked: Maybe<&2, ArchiveOutcome>, next: Maybe<&2, ArchiveOutcome>) -> Maybe<&2, ArchiveOutcome>:
  match checked:
    case None{}: None{}
    case Some{out}:
      match out:
        case Outcome{+code, checks}:
          Bool.pick(Maybe<&2, ArchiveOutcome>,Nat.is_eq(code,0n),next,Some{Outcome{code,1n}})
def scan(records: List<&2, ArchiveRecord>, +index: Nat, +cancel: Maybe<&2, Nat>, ending: Maybe<&2, Bool>) -> Maybe<&2, ArchiveOutcome>:
  match records:
    case Nil{}: gate(ending,13n,stop(0n))
    case Con{head, tail}:
      Bool.pick(Maybe<&2, ArchiveOutcome>,cancelled(cancel,index),Some{Outcome{8n,1n}},
        prepend_checked(record_decision(head),add_check(scan(tail,(index+1n : Nat),cancel,ending))))
def metadata_bytes(metadata: Maybe<&2, Nat>, next: Maybe<&2, ArchiveOutcome>) -> Maybe<&2, ArchiveOutcome>:
  match metadata:
    case None{}: None{}
    case Some{bytes}: Bool.pick(Maybe<&2, ArchiveOutcome>,Nat.is_lt(16777216n,bytes),stop(5n),next)
def numbers(entries: Maybe<&2, Nat>, limit: Nat, metadata: Maybe<&2, Nat>, next: Maybe<&2, ArchiveOutcome>) -> Maybe<&2, ArchiveOutcome>:
  match entries:
    case None{}: None{}
    case Some{n}: Bool.pick(Maybe<&2, ArchiveOutcome>,Nat.is_lt(limit,n),stop(4n),metadata_bytes(metadata,next))
def metadata_decision(end: Maybe<&2, Bool>, disk: Maybe<&2, Bool>, zip64: Maybe<&2, Bool>, entries: Maybe<&2, Nat>, limit: Nat, bytes: Maybe<&2, Nat>, overflow: Maybe<&2, Bool>, within: Maybe<&2, Bool>, records: List<&2, ArchiveRecord>, cancel: Maybe<&2, Nat>, ending: Maybe<&2, Bool>) -> Maybe<&2, ArchiveOutcome>:
  gate(end,1n,gate(disk,2n,gate(zip64,3n,numbers(entries,limit,bytes,gate(overflow,6n,gate(within,7n,scan(records,0n,cancel,ending)))))))
def published(metadata: Bool, paths: Bool, tree: Bool, regular: Bool, payload: Bool) -> Bool:
  Bool.and(Bool.and(Bool.and(Bool.and(metadata,paths),tree),regular),payload)
def show_outcome(value: Maybe<&2, ArchiveOutcome>) -> String:
  match value:
    case None{}: "unknown"
    case Some{out}:
      match out:
        case Outcome{code,checks}: Nat.show(code) ++ ":" ++ Nat.show(checks)

law opaque_is_not_extraction:
  {portable_name(False{},False{},True{}) == False{} : Bool}
def opaque_is_not_extraction():
  {==}
law false_guard_ignores_unknown:
  for +code: Nat
  {gate(Some{False{}},code,None{}) == stop(code) : Maybe<&2, ArchiveOutcome>}
def false_guard_ignores_unknown(code):
  {==}
law needed_unknown_is_not_acceptance:
  for code: Nat
  for next: Maybe<&2, ArchiveOutcome>
  {gate(None{},code,next) == None{} : Maybe<&2, ArchiveOutcome>}
def needed_unknown_is_not_acceptance(code,next):
  {==}
law entry_cap_precedes_unknown_metadata:
  {numbers(Some{2n},1n,None{},None{}) == stop(4n) : Maybe<&2, ArchiveOutcome>}
def entry_cap_precedes_unknown_metadata():
  {==}
law empty_has_no_entry_check:
  {scan(Nil{},0n,Some{0n},Some{True{}}) == Some{Outcome{0n,0n}} : Maybe<&2, ArchiveOutcome>}
def empty_has_no_entry_check():
  {==}
law invalid_metadata_cannot_publish:
  for paths: Bool
  for tree: Bool
  for regular: Bool
  for payload: Bool
  {published(False{},paths,tree,regular,payload) == False{} : Bool}
def invalid_metadata_cannot_publish(paths,tree,regular,payload):
  {==}

def main() -> IO(Unit):
  IO.print("Archive namespace, raw metadata guards, and closed local import publication.")
