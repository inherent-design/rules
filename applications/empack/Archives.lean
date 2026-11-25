namespace ApplicationStudy.EmpackArchives

/-- Lexical facts only. Neither accepted namespace supplies native I/O authority. -/
structure PathFacts where
  commonUnsafe : Bool
  drivePrefix : Bool
  portableOnlyUnsafe : Bool
  deriving Repr
def opaqueName (p : PathFacts) : Bool := !p.commonUnsafe && !p.drivePrefix
def portableName (p : PathFacts) : Bool := opaqueName p && !p.portableOnlyUnsafe

theorem portable_implies_opaque (p : PathFacts) (h : portableName p = true) :
    opaqueName p = true := by
  cases p with
  | mk common drive extra => cases common <;> cases drive <;> cases extra <;> simp_all [portableName, opaqueName]
theorem opaque_is_not_extraction :
    opaqueName ⟨false, false, true⟩ = true ∧ portableName ⟨false, false, true⟩ = false := by decide
theorem traversal_refused_in_both (drive extra : Bool) :
    opaqueName ⟨true, drive, extra⟩ = false ∧ portableName ⟨true, drive, extra⟩ = false := by
  simp [opaqueName, portableName]

/-- Study stage tags, not empack's public exit codes:
  0 admitted, 1 end record, 2 disk, 3 ZIP64 shape, 4 entries, 5 metadata,
  6 directory overflow, 7 directory bounds, 8 callback cancellation,
  9 signature, 10 short read, 11 declared UTF-8, 12 raw duplicate,
  13 final count, 14 member span. A missing needed fact is unknown. -/
structure Outcome where
  code : Nat
  checks : Nat
  deriving Repr, DecidableEq
abbrev Decision := Option Outcome
def stop (code : Nat) : Decision := some ⟨code, 0⟩
def gate (fact : Option Bool) (code : Nat) (next : Decision) : Decision :=
  match fact with
  | none => none
  | some false => stop code
  | some true => next

structure RecordFacts where
  headerReadable : Option Bool
  signature : Option Bool
  nameReadable : Option Bool
  utf8Declaration : Option Bool
  rawUnique : Option Bool
  spanWithin : Option Bool
  deriving Repr
def recordDecision (r : RecordFacts) : Decision :=
  gate r.headerReadable 10 (gate r.signature 9 (gate r.nameReadable 10
    (gate r.utf8Declaration 11 (gate r.rawUnique 12 (gate r.spanWithin 14 (stop 0))))))

def scan : List RecordFacts → Nat → Option Nat → Option Bool → Decision
  | [], _, _, ending => gate ending 13 (stop 0)
  | r :: rest, index, cancelAfter, ending =>
    if cancelAfter.any (fun cutoff => cutoff ≤ index) then some ⟨8, 1⟩
    else do
      let checked ← recordDecision r
      if checked.code != 0 then pure ⟨checked.code, 1⟩
      else (scan rest (index + 1) cancelAfter ending).map fun result =>
        { result with checks := result.checks + 1 }

structure MetadataFacts where
  endValid : Option Bool
  singleDisk : Option Bool
  zip64Shape : Option Bool
  entries : Option Nat
  entryLimit : Nat
  metadataBytes : Option Nat
  noDirectoryOverflow : Option Bool
  directoryWithin : Option Bool
  records : List RecordFacts
  cancelAfter : Option Nat
  finalCount : Option Bool
  deriving Repr
def metadataLimit : Nat := 16 * 1024 * 1024
def numbers (entries : Option Nat) (entryLimit : Nat) (metadata : Option Nat)
    (next : Decision) : Decision := do
  let count ← entries
  if count > entryLimit then stop 4
  else do
    let bytes ← metadata
    if bytes > metadataLimit then stop 5 else next
def metadataDecision (m : MetadataFacts) : Decision :=
  gate m.endValid 1 (gate m.singleDisk 2 (gate m.zip64Shape 3
    (numbers m.entries m.entryLimit m.metadataBytes
      (gate m.noDirectoryOverflow 6 (gate m.directoryWithin 7
        (scan m.records 0 m.cancelAfter m.finalCount))))))

theorem rejection_does_not_need_later_facts (code : Nat) :
    gate (some false) code none = stop code := rfl
theorem needed_unknown_is_not_acceptance (code : Nat) (next : Decision) :
    gate none code next = none := rfl
theorem entry_cap_precedes_metadata (count limit : Nat) (h : limit < count) :
    numbers (some count) limit none none = stop 4 := by simp [numbers, h]
theorem metadata_cap_precedes_directory (bytes : Nat) (h : metadataLimit < bytes) :
    numbers (some 0) 0 (some bytes) none = stop 5 := by simp [numbers, h]
theorem empty_has_no_entry_check : scan [] 0 (some 0) (some true) = some ⟨0, 0⟩ := rfl
theorem entry_cancel_precedes_header (r : RecordFacts) (rest : List RecordFacts) (endFact : Option Bool) :
    scan (r :: rest) 0 (some 0) endFact = some ⟨8, 1⟩ := rfl

/-- Closed local mrpack corpus: stored unencrypted payloads, valid fixed manifest,
    no remote selections, a fresh destination, and explicit approval.
    Not a general importer, codec selector, or solver. -/
def mayPublishAuthor (metadata paths tree regular payload : Bool) : Bool :=
  metadata && paths && tree && regular && payload
theorem invalid_metadata_cannot_publish (paths tree regular payload : Bool) :
    mayPublishAuthor false paths tree regular payload = false := rfl
theorem crc_failure_cannot_publish (metadata paths tree regular : Bool) :
    mayPublishAuthor metadata paths tree regular false = false := by simp [mayPublishAuthor]
theorem valid_path_alone_is_insufficient : mayPublishAuthor true true true false true = false := rfl

end ApplicationStudy.EmpackArchives
