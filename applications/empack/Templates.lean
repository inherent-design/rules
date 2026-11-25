namespace ApplicationStudy.EmpackTemplates

/-- Study result: ignored=0, invalid destination=1, explicit render=2, auto=3.
    Destination parsing remains the attributed real core API, not this predicate. -/
def address (recognized : Bool) (valid : Option Bool) (explicit : Bool) : Option Nat :=
  if !recognized then some 0 else do
    let accepted ← valid
    if !accepted then some 1 else some (if explicit then 2 else 3)

theorem ignored_layer_needs_no_path : address false none true = some 0 := rfl
theorem recognized_needs_path (explicit : Bool) : address true none explicit = none := rfl
theorem invalid_destination_precedes_mode (explicit : Bool) :
    address true (some false) explicit = some 1 := by simp [address]
theorem explicit_suffix_selects_render : address true (some true) true = some 2 := rfl
theorem ordinary_file_selects_auto : address true (some true) false = some 3 := rfl

/-- Accepted mode tags: copy=0, handlebars=1, text-or-binary=2.
    Body tags: copy=0, render=1, invalid UTF-8=2, unknown variable=3.
    This is a closed literal/NAME/shell_quote fixture interpreter, not Handlebars. -/
def body (mode : Nat) (utf8 known : Bool) : Nat :=
  if mode == 0 then 0
  else if !utf8 then (if mode == 2 then 0 else 2)
  else if known then 1 else 3

theorem copy_does_not_interpret (utf8 known : Bool) : body 0 utf8 known = 0 := rfl
theorem explicit_binary_rejected (known : Bool) : body 1 false known = 2 := rfl
theorem auto_binary_copied (known : Bool) : body 2 false known = 0 := rfl
theorem auto_text_is_not_literal : body 2 true false = 3 := rfl

def selectedLayer (common side : Bool) : Option Nat :=
  if side then some 1 else if common then some 0 else none
theorem side_shadows_common (common : Bool) : selectedLayer common true = some 1 := rfl
theorem missing_side_keeps_common : selectedLayer true false = some 0 := rfl

/-- Stage tags are research values, not empack exit codes. -/
def gate (fact : Option Bool) (code : Nat) (next : Option Nat) : Option Nat :=
  match fact with
  | none => none
  | some false => some code
  | some true => next
def prepare (addresses sameLayer namespaceValid bodies game : Option Bool) : Option Nat :=
  gate addresses 1 (gate sameLayer 2 (gate namespaceValid 3 (gate bodies 4 (gate game 5 (some 0)))))

theorem needed_unknown_is_not_success (code : Nat) (next : Option Nat) :
    gate none code next = none := rfl
theorem known_refusal_can_ignore_later_unknown (code : Nat) :
    gate (some false) code none = some code := rfl
theorem same_layer_collision_precedes_render (namespaceValid bodies game : Option Bool) :
    prepare (some true) (some false) namespaceValid bodies game = some 2 := rfl
theorem bad_render_cannot_publish (game : Option Bool) :
    prepare (some true) (some true) (some true) (some false) game = some 4 := rfl

end ApplicationStudy.EmpackTemplates
