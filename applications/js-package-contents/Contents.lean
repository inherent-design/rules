namespace ApplicationStudy.PackageContents

/-- Manager IDs: npm=0, pnpm=1, Yarn=2. Link classes: regular=0,
    internal=1, external=2, dangling internal=3, for the admitted fixture. -/
def typeAllowed (manager kind : Nat) : Bool :=
  kind == 0 || manager == 2 || (manager == 1 && (kind == 1 || kind == 3))

def rootIgnored (npmPresent npmMatch gitMatch : Bool) : Bool :=
  if npmPresent then npmMatch else gitMatch

/-- Glob results and link classifications are source/fixture premises.
    This does not implement a full ignore parser or symlink traversal. -/
def included (manager kind : Nat) (globalExcluded required filesPresent listed
    npmPresent npmMatch gitMatch nestedMatch : Bool) : Bool :=
  typeAllowed manager kind && !globalExcluded &&
    (required || (if filesPresent then listed && !nestedMatch
                 else !rootIgnored npmPresent npmMatch gitMatch && !nestedMatch))

theorem npm_regular : typeAllowed 0 0 = true := by decide
theorem npm_omits_links (kind : Nat) (h : kind ≠ 0) : typeAllowed 0 kind = false := by
  simp [typeAllowed, h]
theorem pnpm_internal : typeAllowed 1 1 = true := by decide
theorem pnpm_dangling_internal : typeAllowed 1 3 = true := by decide
theorem pnpm_external_omitted : typeAllowed 1 2 = false := by decide
theorem yarn_external_retained : typeAllowed 2 2 = true := by decide
theorem npmignore_replaces_git (npmMatch gitMatch : Bool) :
    rootIgnored true npmMatch gitMatch = npmMatch := by rfl
theorem gitignore_fallback (gitMatch : Bool) : rootIgnored false false gitMatch = gitMatch := by rfl
theorem root_files_overrides_ignore (npmPresent npmMatch gitMatch : Bool) :
    included 0 0 false false true true npmPresent npmMatch gitMatch false = true := by
  simp [included, typeAllowed]
theorem nested_ignore_excludes : included 0 0 false false true true false false false true = false := by decide
theorem required_regular_retained (filesPresent listed npmPresent npmMatch gitMatch nested : Bool) :
    included 0 0 false true filesPresent listed npmPresent npmMatch gitMatch nested = true := by
  simp [included, typeAllowed]
theorem global_exclusion_wins (manager kind : Nat) (required filesPresent listed npmPresent npmMatch gitMatch nested : Bool) :
    included manager kind true required filesPresent listed npmPresent npmMatch gitMatch nested = false := by
  simp [included]

end ApplicationStudy.PackageContents
