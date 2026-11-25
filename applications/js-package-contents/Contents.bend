import Base

def type_allowed(+manager: Nat,+kind: Nat) -> Bool:
  Bool.or(Nat.is_eq(kind,0n),Bool.or(Nat.is_eq(manager,2n),Bool.and(Nat.is_eq(manager,1n),Bool.or(Nat.is_eq(kind,1n),Nat.is_eq(kind,3n)))))
def root_ignored(npm_present: Bool,npm_match: Bool,git_match: Bool) -> Bool:
  Bool.pick(Bool,npm_present,npm_match,git_match)
def included(manager: Nat,kind: Nat,global_excluded: Bool,required: Bool,files_present: Bool,listed: Bool,npm_present: Bool,npm_match: Bool,git_match: Bool,+nested_match: Bool) -> Bool:
  Bool.and(type_allowed(manager,kind),Bool.and(Bool.not(global_excluded),
    Bool.or(required,Bool.pick(Bool,files_present,Bool.and(listed,Bool.not(nested_match)),Bool.and(Bool.not(root_ignored(npm_present,npm_match,git_match)),Bool.not(nested_match))))))

law npm_regular:
  {type_allowed(0n,0n) == True{} : Bool}
def npm_regular(): {==}
law npm_omits_internal:
  {type_allowed(0n,1n) == False{} : Bool}
def npm_omits_internal(): {==}
law pnpm_internal:
  {type_allowed(1n,1n) == True{} : Bool}
def pnpm_internal(): {==}
law pnpm_dangling_internal:
  {type_allowed(1n,3n) == True{} : Bool}
def pnpm_dangling_internal(): {==}
law pnpm_external_omitted:
  {type_allowed(1n,2n) == False{} : Bool}
def pnpm_external_omitted(): {==}
law yarn_external_retained:
  {type_allowed(2n,2n) == True{} : Bool}
def yarn_external_retained(): {==}
law empty_npmignore_replaces_git:
  {root_ignored(True{},False{},True{}) == False{} : Bool}
def empty_npmignore_replaces_git(): {==}
law root_files_overrides_ignore:
  {included(0n,0n,False{},False{},True{},True{},True{},True{},False{},False{}) == True{} : Bool}
def root_files_overrides_ignore(): {==}
law nested_ignore_excludes:
  {included(0n,0n,False{},False{},True{},True{},True{},True{},False{},True{}) == False{} : Bool}
def nested_ignore_excludes(): {==}
