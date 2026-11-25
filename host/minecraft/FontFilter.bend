import Base

type FontFilter is Data:
  FontFilter{uniform: Nat,japanese: Nat}
def font_filter_of(+code: Nat) -> FontFilter:
  FontFilter{Nat.mod(code,3n),Nat.div(code,3n)}
def font_field_override(+left: Nat,right: Nat) -> Nat:
  Bool.pick(Nat,Nat.is_eq(left,0n),right,left)
def font_filter_merge(left: FontFilter,right: FontFilter) -> FontFilter:
  match left:
    case FontFilter{a,b}:
      match right:
        case FontFilter{c,d}: FontFilter{font_field_override(a,c),font_field_override(b,d)}
def font_field_allows(+mode: Nat,+enabled: Bool) -> Bool:
  Bool.or(Nat.is_eq(mode,0n),Bool.not(Bool.xor(enabled,Nat.is_eq(mode,2n))))
def font_filter_allows(filter: FontFilter,+mask: Nat) -> Bool:
  match filter:
    case FontFilter{a,b}: Bool.and(font_field_allows(a,Nat.is_eq(Nat.mod(mask,2n),1n)),font_field_allows(b,Nat.is_eq(Nat.div(mask,2n),1n)))
def font_filter_evaluate(+left: Nat,right: Nat,mask: Nat,merged: Bool) -> Nat:
  Bool.pick(Nat,font_filter_allows(Bool.pick(FontFilter,merged,font_filter_merge(font_filter_of(left),font_filter_of(right)),font_filter_of(left)),mask),1n,0n)

law font_absent_uses_right:
  {font_field_override(0n,2n) == 2n : Nat}
def font_absent_uses_right():
  {==}
law font_false_overrides_true:
  {font_field_override(1n,2n) == 1n : Nat}
def font_false_overrides_true():
  {==}
law font_true_overrides_false:
  {font_field_override(2n,1n) == 2n : Nat}
def font_true_overrides_false():
  {==}
law font_disjoint_predicates_can_merge_allow:
  {font_filter_evaluate(1n,2n,0n,True{}) == 1n : Nat}
def font_disjoint_predicates_can_merge_allow():
  {==}
law font_reverse_merge_differs:
  {font_filter_evaluate(2n,1n,0n,True{}) == 0n : Nat}
def font_reverse_merge_differs():
  {==}
law font_other_option_is_preserved:
  {font_filter_merge(FontFilter{1n,0n},FontFilter{0n,2n}) == FontFilter{1n,2n} : FontFilter}
def font_other_option_is_preserved():
  {==}
law font_unset_allows:
  {font_filter_evaluate(0n,0n,3n,False{}) == 1n : Nat}
def font_unset_allows():
  {==}
law font_false_requirement_refuses_enabled:
  {font_filter_evaluate(1n,0n,1n,False{}) == 0n : Nat}
def font_false_requirement_refuses_enabled():
  {==}
