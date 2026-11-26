import Base

def reason(first: Bool,all_roots: Bool,repeated: Bool,local_source: Bool,+source: Nat,+installed: Nat) -> Nat:
  Bool.pick(Nat,repeated,2n,Bool.pick(Nat,Bool.and(first,Bool.not(all_roots)),1n,
    Bool.pick(Nat,Nat.is_eq(installed,0n),3n,Bool.pick(Nat,Bool.and(local_source,Bool.not(Nat.is_eq(source,installed))),4n,0n))))
def candidate(r: Nat,installed: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(r,0n),installed,0n)
def publish(preview: Bool,r: Nat) -> Bool:
  Bool.and(Bool.not(preview),Nat.is_eq(r,0n))
def accepted(preview: Bool,r: Nat,before: Nat,installed: Nat) -> Nat:
  Bool.pick(Nat,publish(preview,r),installed,before)
def changed(preview: Bool,r: Nat,before: Nat,installed: Nat) -> Bool:
  Bool.and(publish(preview,r),Bool.not(Nat.is_eq(before,installed)))

law duplicate_refused:
  for first: Bool
  for all_roots: Bool
  for local_source: Bool
  for source: Nat
  for installed: Nat
  {reason(first,all_roots,True{},local_source,source,installed) == 2n : Nat}
def duplicate_refused(first,all_roots,local_source,source,installed): {==}
law incomplete_first_refused:
  for local_source: Bool
  for source: Nat
  for installed: Nat
  {reason(True{},False{},False{},local_source,source,installed) == 1n : Nat}
def incomplete_first_refused(local_source,source,installed): {==}
law preview_keeps_accepted:
  for r: Nat
  for before: Nat
  for installed: Nat
  {accepted(True{},r,before,installed) == before : Nat}
def preview_keeps_accepted(r,before,installed): {==}
law preview_no_write:
  for r: Nat
  for before: Nat
  for installed: Nat
  {changed(True{},r,before,installed) == False{} : Bool}
def preview_no_write(r,before,installed): {==}
law failure_keeps_accepted:
  for before: Nat
  for installed: Nat
  {accepted(False{},4n,before,installed) == before : Nat}
def failure_keeps_accepted(before,installed): {==}
law successful_apply_records:
  for before: Nat
  for installed: Nat
  {accepted(False{},0n,before,installed) == installed : Nat}
def successful_apply_records(before,installed): {==}
law url_changed_bytes_admitted:
  {reason(False{},True{},False{},False{},0n,2n) == 0n : Nat}
def url_changed_bytes_admitted(): {==}
law local_mismatch_refused:
  {reason(False{},True{},False{},True{},1n,2n) == 4n : Nat}
def local_mismatch_refused(): {==}
law local_matching_changes_admitted:
  {reason(False{},True{},False{},True{},2n,2n) == 0n : Nat}
def local_matching_changes_admitted(): {==}
