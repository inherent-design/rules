namespace ApplicationStudy.VscodeTrust

inductive Support | deny | allow | limited
  deriving BEq, DecidableEq, Repr

/-- Admitted settings/product maps for one lowercase generated extension ID.
    Exact version equality is represented by versionMatches. Map loading,
    identifier normalization, trust persistence, and extension execution are
    not part of this source-method projection. -/
def support (trustEnabled hasEntry versionMatches : Bool)
    (configured productOverride declared productDefault : Option Support) : Support :=
  if !trustEnabled || !hasEntry then .allow
  else ((if versionMatches then configured else none).or
    (productOverride.or (declared.or productDefault))).getD .deny

/-- Only the trust-related disable predicate. Passing it does not establish
    full enablement: other pipeline predicates and dependency gates remain. -/
def blocked (trusted inside : Bool) (value : Support) : Bool :=
  !trusted && (inside || value == .deny)

/-- The environment switch wins; an absent/non-Boolean setting defaults on. -/
def trustEnabled (environmentDisabled : Bool) (setting : Option Bool) : Bool :=
  !environmentDisabled && setting.getD true

theorem disabled_feature_reports_support (entry version : Bool)
    (user override manifest fallback : Option Support) :
    support false entry version user override manifest fallback = .allow := rfl

theorem declarative_extension_reports_support (enabled version : Bool)
    (user override manifest fallback : Option Support) :
    support enabled false version user override manifest fallback = .allow := by
  cases enabled <;> rfl

theorem matching_user_deny_wins (override manifest fallback : Option Support) :
    support true true true (some .deny) override manifest fallback = .deny := rfl

theorem mismatched_user_is_ignored (user : Option Support) :
    support true true false user none (some .limited) none = .limited := rfl

theorem untrusted_workspace_local_blocked (value : Support) :
    blocked false true value = true := rfl

theorem trusted_passes_only_this_predicate (inside : Bool) (value : Support) :
    blocked true inside value = false := rfl

theorem limited_is_not_false : blocked false false .limited = false := rfl

theorem environment_disable_wins (setting : Option Bool) :
    trustEnabled true setting = false := rfl

end ApplicationStudy.VscodeTrust
