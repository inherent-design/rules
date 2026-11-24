import Lean

namespace ApplicationStudy.VscodeConfiguration
open Lean

/-- Bounded JSON-object merge for the captured local configuration profile.
    Scalars, null, and arrays replace. The adapter refuses depth above 16;
    32 recursive object levels are available here. No policy/remote/memory
    scope, combined language selector, or configuration parser is modeled. -/
def mergeValue : Nat → Json → Json → Json
  | 0, _, upper => upper
  | depth + 1, .obj lower, .obj upper =>
    .obj (upper.foldl (init := lower) fun fields key value =>
      fields.insert key (match fields.get? key with
        | none => value
        | some old => mergeValue depth old value))
  | _ + 1, _, upper => upper

def applyLayer (lower upper : Option Json) : Option Json :=
  match lower, upper with
  | _, none => lower
  | none, some value => some value
  | some old, some value => some (mergeValue 32 old value)

/-- Caller supplies the eight documented slots in low-to-high order:
    defaults, user, workspace, folder, then the four language counterparts. -/
def resolve (slots : List (Option Json)) : Option Json :=
  slots.foldl applyLayer none

theorem absent_layer_preserves (lower : Option Json) :
    applyLayer lower none = lower := by cases lower <;> rfl

theorem explicit_null_is_present (lower : Option Json) :
    applyLayer lower (some .null) = some .null := by
  cases lower with
  | none => rfl
  | some value => cases value <;> rfl

theorem arrays_replace (lower : Json) (items : Array Json) :
    applyLayer (some lower) (some (.arr items)) = some (.arr items) := by
  cases lower <;> rfl

theorem strings_replace (lower : Json) (text : String) :
    applyLayer (some lower) (some (.str text)) = some (.str text) := by
  cases lower <;> rfl

theorem trailing_absent_preserves (slots : List (Option Json)) :
    resolve (slots ++ [none]) = resolve slots := by
  simp only [resolve, List.foldl_append, List.foldl_cons, List.foldl_nil]
  exact absent_layer_preserves _

theorem language_default_masks_generic_folder :
    resolve [some (.str "default"), some (.str "user"),
      some (.str "workspace"), some (.str "folder"),
      some (.str "language-default"), none, none, none] =
      some (.str "language-default") := rfl

theorem source_change_can_be_masked :
    resolve [some (.str "user"), some (.str "workspace")] =
      resolve [some (.str "user-new"), some (.str "workspace")] := rfl

/-- Source projection of the documented globalValue wrapper in the pinned
    extension host: local null/undefined falls through to application value. -/
def currentGlobalInspection (localValue applicationValue : Option Json) : Option Json :=
  match localValue with
  | none | some .null => applicationValue
  | some value => some value

/-- Candidate: provenance carriers preserve present-null distinctly from absent.
    This is a candidate API rule, not an upstream implementation change. -/
def preservingGlobalInspection (localValue applicationValue : Option Json) : Option Json :=
  match localValue with
  | none => applicationValue
  | some value => some value

theorem current_projection_drops_local_null :
    currentGlobalInspection (some .null) none = none := rfl

theorem proposed_projection_preserves_null (fallback : Option Json) :
    preservingGlobalInspection (some .null) fallback = some .null := rfl

end ApplicationStudy.VscodeConfiguration
