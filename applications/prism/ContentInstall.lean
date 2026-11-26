namespace ApplicationStudy.PrismContentInstall

inductive Policy | current | guarded | staged
  deriving Repr, BEq, DecidableEq
inductive Source | regular | samePath | destinationAlias | missing
  deriving Repr, BEq, DecidableEq

/-- Payload numbers are opaque fixture content keys. Zero denotes absence,
    not an empty file. Source/path identity is a separate observation. -/
structure Request where
  policy : Policy
  source : Source
  destination : Nat
  sourcePayload : Nat
  disabledSibling : Bool
  drop : Bool
  extraMissing : Bool
  watching : Bool
  refreshResult : Bool
  cancelBeforeCommit : Bool
  deriving Repr

structure Transfer where
  reported : Bool
  destination : Nat
  sourceAlive : Bool
  refreshCalls : Nat
  deriving Repr, BEq, DecidableEq

def copied (r : Request) : Transfer :=
  ⟨r.watching || r.refreshResult, r.sourcePayload, true, if r.watching then 0 else 1⟩

/-- Selected regular-file method projection. The staged path assumes admitted
    immutable input bytes and an accepted commit unless the explicit hook
    cancels. General filesystem faults/atomicity are not supplied by this model. -/
def transfer (r : Request) : Transfer :=
  match r.source with
  | .missing => ⟨false, r.destination, false, 0⟩
  | .samePath => ⟨false, r.destination, r.destination != 0, 0⟩
  | .destinationAlias =>
    if r.policy == .guarded then ⟨false, r.destination, true, 0⟩
    else if r.policy == .current then ⟨false, 0, false, 0⟩
    else if r.cancelBeforeCommit then ⟨false, r.destination, true, 0⟩
    else copied r
  | .regular =>
    if r.policy == .staged && r.cancelBeforeCommit then ⟨false, r.destination, true, 0⟩
    else copied r

structure Outcome where
  surface : Bool
  items : List Bool
  destination : Nat
  sourceAlive : Bool
  disabledSibling : Bool
  refreshCalls : Nat
  deriving Repr, BEq, DecidableEq

def run (r : Request) : Outcome :=
  let item := transfer r
  ⟨if r.drop then true else item.reported,
   [item.reported] ++ (if r.extraMissing then [false] else []),
   item.destination, item.sourceAlive, r.disabledSibling, item.refreshCalls⟩

def plain (policy : Policy) : Request :=
  ⟨policy, .regular, 0, 2, false, false, false, true, true, false⟩
def aliasRequest (policy : Policy) : Request :=
  { plain policy with source := .destinationAlias, destination := 1, sourcePayload := 1 }

theorem fresh_copy_has_new_payload : (run (plain .current)).destination = 2 := by decide
theorem ordinary_overwrite_has_new_payload :
    (run { plain .current with destination := 1 }).destination = 2 := by decide
theorem exact_same_path_is_refused (r : Request) :
    transfer { r with source := .samePath } = ⟨false, r.destination, r.destination != 0, 0⟩ := rfl
theorem original_false_can_lose_destination :
    run (aliasRequest .current) = ⟨false, [false], 0, false, false, 0⟩ := by decide
theorem handled_drop_can_contain_loss :
    run { aliasRequest .current with drop := true } = ⟨true, [false], 0, false, false, 0⟩ := by decide
theorem guarded_alias_preserves_old_payload :
    run (aliasRequest .guarded) = ⟨false, [false], 1, true, false, 0⟩ := by decide
theorem staged_alias_uses_captured_payload :
    run (aliasRequest .staged) = ⟨true, [true], 1, true, false, 0⟩ := by decide
theorem equal_content_is_not_self_identity :
    run { plain .guarded with destination := 2 } = ⟨true, [true], 2, true, false, 0⟩ := by decide
theorem staged_cancel_preserves_destination (r : Request) :
    (transfer { r with policy := .staged, cancelBeforeCommit := true }).destination = r.destination := by
  cases r.source <;> rfl
theorem refresh_refusal_does_not_undo_copy :
    run { plain .current with watching := false, refreshResult := false } = ⟨false, [false], 2, true, false, 1⟩ := by decide
theorem drop_reports_items_separately :
    run { plain .current with drop := true, extraMissing := true } = ⟨true, [true,false], 2, true, false, 0⟩ := by decide
theorem disabled_sibling_is_framed (r : Request) : (run r).disabledSibling = r.disabledSibling := rfl
theorem missing_source_does_not_write (r : Request) :
    (transfer { r with source := .missing }).destination = r.destination := rfl
theorem drop_acceptance_does_not_change_item_result (r : Request) :
    (run { r with drop := true }).items = (run r).items := rfl

end ApplicationStudy.PrismContentInstall
