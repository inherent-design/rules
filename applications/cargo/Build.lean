namespace ApplicationStudy.Cargo

/- Projection of the fixture's normal dependency features, not a full Cargo
   resolver. Package versions and identities are opaque; metadata's workspace
   union and the selected build's units answer different questions. -/
structure Features where
  red : Bool
  blue : Bool
  deriving DecidableEq, Repr

inductive Selection where
  | app | workspace
  deriving DecidableEq, Repr

def selectedFeatures : Selection → Features
  | .app => ⟨true, false⟩
  | .workspace => ⟨true, true⟩

structure UnitIdentity where
  package : String
  target : String
  profile : String
  compileKind : String
  mode : String
  features : Features
  flags : List String
  dependencyContext : String
  deriving DecidableEq, Repr

theorem different_features_different_units (a b : UnitIdentity)
    (h : a.features ≠ b.features) : a ≠ b := by
  intro same
  exact h (congrArg UnitIdentity.features same)

theorem workspace_selection_changes_features :
    selectedFeatures .app ≠ selectedFeatures .workspace := by decide

/- Host/compiler identity must also qualify any reusable artifact evidence.
   UnitIdentity mirrors selected source fields, not Cargo's entire cache key. -/
structure ArtifactEvidence where
  unit : UnitIdentity
  compiler : String
  hostProfile : String
  inputSignature : String
  deriving DecidableEq, Repr

structure CachedScript where
  watchedSignature : String
  capturedValue : String
  deriving DecidableEq, Repr

/-- Reuse decision in a stationary, successful, already-cached build-script
    projection. Signature construction/mtime detection is an adapter premise;
    this is not a Cargo fingerprint implementation. -/
def capture (previous : CachedScript) (signature actual : String) : CachedScript :=
  if previous.watchedSignature = signature then previous else ⟨signature, actual⟩

theorem unchanged_signature_reuses_capture (c : CachedScript) (actual : String) :
    capture c c.watchedSignature actual = c := by simp [capture]

theorem changed_signature_captures_current (c : CachedScript) (signature actual : String)
    (changed : c.watchedSignature ≠ signature) :
    (capture c signature actual).capturedValue = actual := by simp [capture, changed]

theorem complete_signature_yields_current (c : CachedScript) (signature actual : String)
    (complete : c.watchedSignature = signature → c.capturedValue = actual) :
    (capture c signature actual).capturedValue = actual := by
  by_cases same : c.watchedSignature = signature
  · simpa [capture, same] using complete same
  · simp [capture, same]

structure Effects where
  targetPresent : Bool
  scriptOutputOutsideTarget : String
  deriving DecidableEq, Repr

def clean (e : Effects) : Effects := { e with targetPresent := false }

theorem clean_keeps_unowned_effect (e : Effects) :
    (clean e).scriptOutputOutsideTarget = e.scriptOutputOutsideTarget := rfl

theorem clean_idempotent (e : Effects) : clean (clean e) = clean e := rfl

end ApplicationStudy.Cargo
