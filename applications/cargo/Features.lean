namespace ApplicationStudy.CargoFeatures

/-- Closed source-derived profile: three packages, one shared library, native
    macOS target, and normal/build/dev/Windows-conditioned uses. Workspace
    requests are admitted only for the captured no-default build profile;
    direct library-root all-feature contributions are not modeled. Not a solver. -/
inductive Feature | normal | build | dev | platform | extra | explicit | defaulted | sibling | default
  deriving BEq, DecidableEq, Repr
inductive Resolver | one | two | three
  deriving BEq, DecidableEq, Repr
inductive Role | normal | build
  deriving BEq, DecidableEq, Repr
inductive Edge | normal | build | dev | windows | sibling
  deriving BEq, DecidableEq, Repr
inductive FeatureArg | none | bare | qualified
  deriving BEq, DecidableEq, Repr

structure Request where
  resolver : Resolver
  noDefault : Bool
  allFeatures : Bool
  featureArg : FeatureArg
  workspace : Bool
  tests : Bool
  deriving BEq, DecidableEq, Repr

abbrev FeatureSet := Feature → Bool
def union (a b : FeatureSet) : FeatureSet := fun f => a f || b f
def singleton (f : Feature) : FeatureSet := (· == f)
def edges : List Edge := [.normal,.build,.dev,.windows,.sibling]
def features : List Feature := [.normal,.build,.dev,.platform,.extra,.explicit,.defaulted,.sibling,.default]
def split (r : Resolver) : Bool := r != .one

/-- Root defaults and a dependency declaration's own default request are
    separate positive contributions. No-default is not a global negation. -/
def appDefaults (q : Request) : Bool := !q.noDefault || q.allFeatures
def siblingDefaults (q : Request) : Bool :=
  q.workspace && (!split q.resolver || appDefaults q)
def appForward (q : Request) : FeatureSet := fun f =>
  (f == .extra && appDefaults q) ||
  (f == .explicit && (q.featureArg != .none || q.allFeatures))
def siblingForward (q : Request) : FeatureSet := fun f => f == .sibling && siblingDefaults q
def libraryDefaults : FeatureSet := fun f => f == .default || f == .defaulted
def declared : Edge → FeatureSet
  | .normal => singleton .normal
  | .build => singleton .build
  | .dev => singleton .dev
  | .windows => singleton .platform
  | .sibling => libraryDefaults
def forwarded (q : Request) : Edge → FeatureSet
  | .sibling => siblingForward q
  | _ => appForward q

/-- Resolver 1 unifies these roles, including dev and inactive target features.
    Resolvers 2/3 split host build uses and admit dev only for this test mode.
    Windows-conditioned edges are inactive on the captured Mac. -/
def admitted (q : Request) (role : Role) (edge : Edge) : Bool :=
  if !split q.resolver then edge != .sibling || q.workspace
  else match edge with
    | .normal => role == .normal
    | .build => role == .build
    | .dev => role == .normal && q.tests
    | .windows => false
    | .sibling => role == .normal && q.workspace
def contribution (q : Request) (role : Role) (edge : Edge) : FeatureSet := fun f =>
  admitted q role edge && union (declared edge) (forwarded q edge) f
def selected (q : Request) (role : Role) : FeatureSet := fun f =>
  edges.any (fun e => contribution q role e f)

/-- Qualified self syntax from the app-member CWD is refused in the legacy
    resolver context. This is not a general parser or workspace CLI model. -/
def refused (q : Request) : Bool := q.resolver == .one && q.featureArg == .qualified
def names (s : FeatureSet) : List Feature := features.filter s
def weight : Feature → Nat
  | .normal => 1 | .build => 2 | .dev => 4 | .platform => 8 | .extra => 16
  | .explicit => 32 | .defaulted => 64 | .sibling => 128 | .default => 256
def mask (s : FeatureSet) : Nat := (features.filter s).foldl (fun n f => n + weight f) 0

theorem union_idempotent (a : FeatureSet) : union a a = a := by
  funext f; simp [union]
theorem union_commutative (a b : FeatureSet) : union a b = union b a := by
  funext f; simp [union, Bool.or_comm]
theorem positive_contribution_survives (a b : FeatureSet) (f : Feature) (h : a f = true) :
    union a b f = true := by simp [union,h]
theorem legacy_roles_equal (n a w t : Bool) (arg : FeatureArg) :
    selected ⟨.one,n,a,arg,w,t⟩ .normal = selected ⟨.one,n,a,arg,w,t⟩ .build := rfl
theorem resolver_three_feature_projection (n a w t : Bool) (arg : FeatureArg) (role : Role) :
    selected ⟨.two,n,a,arg,w,t⟩ role = selected ⟨.three,n,a,arg,w,t⟩ role := rfl
theorem inactive_windows_not_admitted (n a w t : Bool) (arg : FeatureArg) (role : Role) :
    admitted ⟨.two,n,a,arg,w,t⟩ role .windows = false := rfl
theorem default_forwarding_reaches_both_roles :
    selected ⟨.two,false,false,.none,false,false⟩ .normal .extra = true ∧
    selected ⟨.two,false,false,.none,false,false⟩ .build .extra = true := by decide
theorem explicit_forwarding_reaches_both_roles :
    selected ⟨.two,true,false,.bare,false,false⟩ .normal .explicit = true ∧
    selected ⟨.two,true,false,.bare,false,false⟩ .build .explicit = true := by decide
theorem dependency_defaults_survive_root_no_default :
    selected ⟨.two,true,false,.none,true,false⟩ .normal .default = true ∧
    selected ⟨.two,true,false,.none,true,false⟩ .normal .defaulted = true ∧
    selected ⟨.two,true,false,.none,true,false⟩ .normal .sibling = false := by decide
theorem legacy_sibling_root_default_remains :
    selected ⟨.one,true,false,.none,true,false⟩ .normal .sibling = true := by decide
theorem test_dev_contribution_is_normal_only :
    selected ⟨.two,true,false,.none,false,true⟩ .normal .dev = true ∧
    selected ⟨.two,true,false,.none,false,true⟩ .build .dev = false := by decide
theorem all_root_features_is_not_all_dependency_features :
    selected ⟨.two,false,true,.none,false,false⟩ .normal .extra = true ∧
    selected ⟨.two,false,true,.none,false,false⟩ .normal .explicit = true ∧
    selected ⟨.two,false,true,.none,false,false⟩ .normal .defaulted = false := by decide
theorem qualified_self_legacy_refused (n a w t : Bool) :
    refused ⟨.one,n,a,.qualified,w,t⟩ = true := rfl
theorem qualified_self_split_admitted (n a w t : Bool) :
    refused ⟨.two,n,a,.qualified,w,t⟩ = false := rfl
theorem same_package_different_role_features :
    mask (selected ⟨.two,true,false,.none,false,false⟩ .normal) = 1 ∧
    mask (selected ⟨.two,true,false,.none,false,false⟩ .build) = 2 := by decide

end ApplicationStudy.CargoFeatures
