import Base

# Bounded admitted-success trace, not a resolver or filesystem writer.
# Operations:0syncOld,1inspect,2held,3unpin,4automaticPreview,5exactPreview,
# 6applyExact,7checkRecorded,8materialize,9checkOnline,10bundled,
# 11references,12ensure,13checkRecipient. Identity labels0absent/1old/2target.
def pin(+op: Nat,prior: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(op,3n),0n,Bool.pick(Nat,Nat.is_eq(op,6n),2n,prior))
def selected(+op: Nat,pin: Nat,prior: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(op,0n),pin,Bool.pick(Nat,Nat.is_eq(op,6n),2n,prior))
def payload(+op: Nat,pin: Nat,selected: Nat,prior: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(op,0n),pin,Bool.pick(Nat,Nat.is_eq(op,6n),0n,Bool.pick(Nat,Nat.is_eq(op,8n),selected,prior)))
def recipient(op: Nat,prior: Bool) -> Bool:
  Bool.or(Nat.is_eq(op,12n),prior)
def verified(selected: Nat,payload: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(selected,payload),1n,0n)
def references(selected: Nat,payload: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(selected,payload),0n,1n)
def recipient_version(present: Bool) -> Nat:
  Bool.pick(Nat,present,2n,0n)
# Snapshot-export profile only; not subscription or general representation policy.
def embedded_mod(op: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(op,10n),1n,0n)
def embedded_bootstrap(op: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(op,11n),1n,0n)

law unpin_changes_pin:
  {pin(3n,1n) == 0n : Nat}
def unpin_changes_pin(): {==}
law unpin_keeps_selection:
  {selected(3n,0n,1n) == 1n : Nat}
def unpin_keeps_selection(): {==}
law unpin_keeps_payload:
  {payload(3n,0n,1n,1n) == 1n : Nat}
def unpin_keeps_payload(): {==}
law preview_keeps_pin:
  {pin(5n,0n) == 0n : Nat}
def preview_keeps_pin(): {==}
law preview_keeps_payload:
  {payload(4n,0n,1n,1n) == 1n : Nat}
def preview_keeps_payload(): {==}
law apply_pins:
  {pin(6n,0n) == 2n : Nat}
def apply_pins(): {==}
law apply_selects:
  {selected(6n,2n,1n) == 2n : Nat}
def apply_selects(): {==}
law apply_leaves_reference:
  {payload(6n,2n,2n,1n) == 0n : Nat}
def apply_leaves_reference(): {==}
law materialize_keeps_pin:
  {pin(8n,2n) == 2n : Nat}
def materialize_keeps_pin(): {==}
law materialize_keeps_selection:
  {selected(8n,2n,2n) == 2n : Nat}
def materialize_keeps_selection(): {==}
law materialize_selected:
  {payload(8n,2n,2n,0n) == 2n : Nat}
def materialize_selected(): {==}
law missing_not_verified:
  {verified(2n,0n) == 0n : Nat}
def missing_not_verified(): {==}
law missing_is_reference:
  {references(2n,0n) == 1n : Nat}
def missing_is_reference(): {==}
law matching_verified:
  {verified(2n,2n) == 1n : Nat}
def matching_verified(): {==}
law ensure_idempotent:
  {recipient(12n,recipient(12n,False{})) == True{} : Bool}
def ensure_idempotent(): {==}
law ensure_target:
  {recipient_version(recipient(12n,False{})) == 2n : Nat}
def ensure_target(): {==}
law bundled_mod:
  {embedded_mod(10n) == 1n : Nat}
def bundled_mod(): {==}
law reference_omits_mod:
  {embedded_mod(11n) == 0n : Nat}
def reference_omits_mod(): {==}
law reference_embeds_tool:
  {embedded_bootstrap(11n) == 1n : Nat}
def reference_embeds_tool(): {==}
