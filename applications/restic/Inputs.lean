namespace ApplicationStudy.ResticInputs

/-- A finite, independently checked pattern/path witness, not a Go glob parser.
    Match spelling, case normalization, and filesystem target expansion remain
    adapter obligations. List order is semantic, including negation. -/
structure Rule where
  negated : Bool
  hits : List String
  deriving BEq, DecidableEq, Repr
def rejected (rules : List Rule) (path : String) : Bool :=
  rules.foldl (fun excluded r =>
    if r.negated then excluded && !r.hits.contains path
    else excluded || r.hits.contains path) false

/-- All rules in one exclusion group are folded together. Distinct ordinary
    and case-insensitive groups independently reject; negation in one group
    cannot undo another group's rejection. -/
def excluded (groups : List (List Rule)) (path : String) : Bool :=
  groups.any (fun rules => rejected rules path)

inductive Entry where
  | file (name : String)
  | directory (name : String) (children : List Entry)
def entryName : Entry → String | .file name => name | .directory name _ => name

/-- The caller admits the exact selected root. Filters run on its descendants;
    a rejected directory stops traversal before a matching child can be seen. -/
def walk (groups : List (List Rule)) (explicit : Bool) : Entry → List String
  | .file name => if !explicit && excluded groups name then [] else [name]
  | .directory name children =>
    if !explicit && excluded groups name then []
    else children.flatMap (walk groups false)
termination_by e => sizeOf e

structure Selection where
  /-- Existing, explicit roots after normal/verbatim/raw list admission. -/
  roots : List Entry
  skippedMissing : Bool
  framingValid : Bool
structure Outcome where
  files : List String
  exitCode : Nat
  snapshot : Bool
  deriving BEq, DecidableEq, Repr
def backup (groups : List (List Rule)) (s : Selection) : Outcome :=
  if !s.framingValid || s.roots.isEmpty then ⟨[],1,false⟩ else
  ⟨(s.roots.flatMap (walk groups true)).eraseDups,if s.skippedMissing then 3 else 0,true⟩

theorem explicit_file_bypasses_exclusions (groups : List (List Rule)) (name : String) :
    walk groups true (.file name) = [name] := by simp [walk]
theorem rejected_directory_is_not_walked (groups : List (List Rule)) (name : String)
    (children : List Entry) (h : excluded groups name = true) :
    walk groups false (.directory name children) = [] := by simp [walk,h]
theorem invalid_framing_refuses_before_snapshot (groups : List (List Rule)) (roots : List Entry) (missing : Bool) :
    backup groups ⟨roots,missing,false⟩ = ⟨[],1,false⟩ := by simp [backup]
theorem no_admitted_root_refuses (groups : List (List Rule)) (missing valid : Bool) :
    backup groups ⟨[],missing,valid⟩ = ⟨[],1,false⟩ := by simp [backup]
theorem partial_selection_can_save_snapshot :
    backup [] ⟨[.file "keep.txt"],true,true⟩ = ⟨["keep.txt"],3,true⟩ := by
  simp [backup,walk,excluded,rejected] <;> decide

def rejectParent : Rule := ⟨false,["pruned","pruned/keep.txt"]⟩
def includeChild : Rule := ⟨true,["pruned/keep.txt"]⟩
def includeParent : Rule := ⟨true,["pruned","pruned/keep.txt"]⟩
def child : Entry := .directory "pruned" [.file "pruned/keep.txt"]
def tree : Entry := .directory "." [child]

theorem child_negation_does_not_reopen_parent :
    rejected [rejectParent,includeChild] "pruned/keep.txt" = false ∧
    walk [[rejectParent,includeChild]] true tree = [] := by
  simp [walk,excluded,rejected,tree,child,rejectParent,includeChild]
theorem parent_negation_allows_traversal :
    walk [[rejectParent,includeParent,includeChild]] true tree = ["pruned/keep.txt"] := by
  simp [walk,excluded,rejected,tree,child,rejectParent,includeParent,includeChild]
theorem negation_order_is_not_commutative :
    rejected [rejectParent,includeChild] "pruned/keep.txt" = false ∧
    rejected [includeChild,rejectParent] "pruned/keep.txt" = true := by decide
theorem exact_directory_root_does_not_exempt_its_child :
    walk [[rejectParent]] true child = [] := by simp [walk,excluded,rejected,child,rejectParent]
theorem negation_does_not_cross_exclusion_groups :
    excluded [[rejectParent],[includeChild]] "pruned/keep.txt" = true := by decide
theorem empty_filtered_tree_still_has_a_snapshot :
    backup [[rejectParent]] ⟨[child],false,true⟩ = ⟨[],0,true⟩ := by
  simp [backup,walk,excluded,rejected,child,rejectParent]

end ApplicationStudy.ResticInputs
