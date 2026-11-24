namespace ApplicationStudy.ResticIntegrity

/-- Scope projection for a finite local repository, not a restic wire codec.
    `healthy` is supplied by the controlled fault image, not inferred from a
    successful metadata check. Each pack's bucket is its first ID byte mod 2. -/
structure Pack where
  id : String
  bucket : Nat
  healthy : Bool
  deriving Repr

structure Repository where
  indexOK : Bool
  structureOK : Bool
  headersRecoverable : Bool
  packs : List Pack
  deriving Repr

def selected (scope : Nat) (pack : Pack) : Bool :=
  if scope == 1 then true else
  if scope == 2 then pack.bucket == 0 else
  if scope == 3 then pack.bucket == 1 else false

def metadata (repo : Repository) : Bool := repo.indexOK && repo.structureOK

def check (repo : Repository) (scope : Nat) : Bool :=
  metadata repo && repo.packs.all (fun p => !selected scope p || p.healthy)

/-- Permitted claim from request plus success, not a field printed by restic.
    Limited to the repository set already captured by this model. -/
def fullDataClaim (repo : Repository) (scope : Nat) : Bool :=
  scope == 1 && check repo scope

def readOne (repo : Repository) (target : String) : Bool :=
  metadata repo && repo.packs.any (fun p => p.id == target && p.healthy)

/-- Successful header reconstruction repairs index availability only. The
    premise is explicit; this is not a model of arbitrary repair failures. -/
def rebuild (repo : Repository) : Repository :=
  if repo.headersRecoverable then {repo with indexOK := true} else repo

def fixture : Repository :=
  ⟨true, true, true, [⟨"unaffected", 0, true⟩, ⟨"damaged", 1, false⟩]⟩

theorem metadata_success_is_not_body_success :
    check fixture 0 = true ∧ check fixture 1 = false := by constructor <;> rfl

theorem successful_half_does_not_claim_all :
    check fixture 2 = true ∧ fullDataClaim fixture 2 = false := by constructor <;> rfl

theorem other_half_detects_fault : check fixture 3 = false := rfl

theorem metadata_has_no_full_data_claim (repo : Repository) :
    fullDataClaim repo 0 = false := rfl

theorem damaged_content_cannot_be_dumped : readOne fixture "damaged" = false := rfl

theorem rebuild_preserves_data_health (repo : Repository) :
    (rebuild repo).packs = repo.packs := by unfold rebuild; split <;> rfl

theorem rebuild_requires_header_premise (repo : Repository) (h : repo.headersRecoverable = false) :
    rebuild repo = repo := by simp [rebuild, h]

theorem successful_rebuild_does_not_repair_body :
    (rebuild fixture).indexOK = true ∧ check (rebuild fixture) 1 = false := by constructor <;> rfl

theorem missing_index_blocks_check (scope : Nat) :
    check {fixture with indexOK := false} scope = false := rfl

theorem rebuilding_missing_index_preserves_damaged_data :
    check (rebuild {fixture with indexOK := false}) 1 = false := rfl

end ApplicationStudy.ResticIntegrity
