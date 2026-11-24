import Lean
import applications.empack.Identity
open Lean ApplicationStudy.EmpackIdentity

private structure ObjectRow where
  volume : Nat
  number : Nat
  created : Option Nat
  token : Option Nat
  deriving FromJson
private structure NodeRow where
  path : String
  kind : Nat
  object : Option ObjectRow
  content : Option Nat
  bytes : Option Nat
  readonly : Option Bool
  mode : Option Nat
  members : List String
  deriving FromJson
private structure SnapshotRow where
  root : ObjectRow
  entries : List NodeRow
  deriving FromJson
private structure AtomRow where
  number : Bool
  negative : Bool
  magnitude : Nat
  deriving FromJson
private structure MemberRow where
  name : String
  array : Bool
  atoms : List AtomRow
  deriving FromJson
private structure Request where
  schema : Nat
  profile : String
  cases : List Json
  deriving FromJson
private def label (n : Nat) : Bool := 0 < n && n ≤ 4096
private def object (r : ObjectRow) : Except String Object := do
  if !label r.volume || !label r.number || r.created.any (fun n => !label n) || r.token.any (fun n => !label n) then
    throw "Invalid equality label."
  pure ⟨r.volume,r.number,r.created,r.token⟩
private def optionalObject (r : Option ObjectRow) : Except String (Option Object) := r.mapM object
private def canonical (xs : List String) : Bool := xs == xs.mergeSort (· ≤ ·) && xs.eraseDups.length == xs.length
private def node (r : NodeRow) : Except String Entry := do
  if r.path.isEmpty || r.path.length > 512 then throw "Invalid fixture path."
  let payload := r.content.isSome || r.bytes.isSome || r.readonly.isSome || r.mode.isSome
  let n ← match r.kind with
    | 0 =>
      if r.object.isSome || payload || !r.members.isEmpty then throw "Invalid absent payload."
      pure Node.absent
    | 1 =>
      if payload || !r.members.isEmpty then throw "Invalid ancestor payload."
      let some o := r.object | throw "Missing node object."
      pure (Node.ancestor (← object o))
    | 2 =>
      let (some o,some c,some b,some ro,some m) := (r.object,r.content,r.bytes,r.readonly,r.mode)
        | throw "Missing file payload."
      if !label c || !label b || !label m || !r.members.isEmpty then throw "Invalid file payload."
      pure (Node.file (← object o) c b ro m)
    | 3 =>
      if payload || !canonical r.members then throw "Invalid directory payload/order."
      let some o := r.object | throw "Missing node object."
      pure (Node.directory (← object o) r.members)
    | _ => throw "Unknown node kind."
  pure ⟨r.path,n⟩
private def snapshot (r : SnapshotRow) : Except String Snapshot := do
  if !canonical (r.entries.map (·.path)) then throw "Invalid entry order or repeated path."
  pure ⟨← object r.root, ← r.entries.mapM node⟩
private def member (r : MemberRow) : Except String Member := do
  let atoms ← r.atoms.mapM fun a => do
    if !a.number && (a.negative || a.magnitude != 0) then throw "Invalid nonnumber atom."
    if a.magnitude > 256 then throw "Atom outside research bound."
    pure (if a.number then Atom.number a.negative a.magnitude else Atom.other)
  if !r.array && !atoms.isEmpty then throw "Invalid scalar member payload."
  pure ⟨r.name,r.array,atoms⟩
private def bit (b : Bool) : String := if b then "1" else "0"
private def optionalBit : Option Bool → String | none => "-" | some b => bit b
private def journalText : JournalResult → String
  | .unavailable => "0/-"
  | .comparison b => "1/" ++ bit b
private def field [FromJson α] (r : Json) (key : String) : Except String α := r.getObjValAs? α key
private def evaluate (r : Json) : Except String String := do
  let kind : String ← field r "kind"
  match kind with
  | "identity" =>
    let a ← object (← field r "left"); let b ← object (← field r "right")
    pure (bit (liveEqual a b) ++ "/" ++ bit (durableEqual a b) ++ "/" ++ journalText (journal (some a) (some b)))
  | "journal" =>
    pure (journalText (journal (← optionalObject (← field r "saved")) (← optionalObject (← field r "observed"))))
  | "wire" =>
    let members : List MemberRow ← field r "members"
    pure (bit (bindingCodec (← field r "object") (← members.mapM member)))
  | "snapshot" =>
    let a ← snapshot (← field r "left"); let b ← snapshot (← field r "right")
    pure (bit (project a).isSome ++ "/" ++ bit (project b).isSome ++ "/" ++ optionalBit (projectionEqual a b) ++ "/" ++
      bit (liveEqual a.root b.root) ++ "/" ++ bit (decide (a.entries = b.entries)))
  | "association" =>
    let saved : Nat ← field r "saved"; let observed : Option Nat ← field r "observed"
    if !label saved || observed.any (fun n => !label n) then throw "Invalid equality label."
    pure (match association (← field r "original") (← field r "selected") saved observed with
      | .misnamed => "name-error" | .unavailable => "unavailable-error" | .comparison b => bit b)
  | "availability" =>
    let reason : String ← field r "reason"
    if !["ENOTSUP","ENOTTY","ENOSYS","EACCES","EPERM","ENOENT","EINVAL","EIO"].contains reason then
      throw "Unknown errno profile."
    pure (match availability reason with | .unavailable => "unavailable" | .error => "error")
  | _ => throw "Unknown identity case."
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one identity research input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Request) with
  | .error e => IO.eprintln e; return 2
  | .ok r =>
    if r.schema != 1 || r.profile != "mac-native-identity-labels" then
      IO.eprintln "Unsupported identity research schema/profile."; return 2
    match r.cases.mapM evaluate with
    | .error e => IO.eprintln e; return 2
    | .ok results => IO.println (toJson results).compress; return 0
