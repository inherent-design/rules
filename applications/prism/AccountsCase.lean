import Lean
import applications.prism.Accounts
open Lean ApplicationStudy.PrismAccounts

private structure Actor where
  id : String
  name : String
  profileId : String
  kind : Nat
  owns : Bool
  hasToken : Bool
  validity : Nat
  hasExpiry : Bool
  expiresIn : Int
  hasIssue : Bool
  issuedAgo : Int
  deriving FromJson
private structure Row where
  kind : Nat
  actor : Actor
  actors : List Actor
  selected : String
  mode : Nat
  mutation : Nat
  fill : Bool
  inUse : Bool
  accepted : Bool
  profileId : String
  profileName : String
  shapeValid : Bool
  missingUuid : String
  demoUuid : String
  deriving FromJson
private structure Input where
  schema : Nat
  profile : String
  rows : List Row
  deriving FromJson

private def safe (s : String) : Bool :=
  s.length ≤ 256 && !s.toList.any (fun c => c == '|' || c == '\n' || c == '\r' || c == '\x00')
private def uuidShape (s : String) : Bool :=
  s.length == 32 && s.toList.all (fun c => ('0' ≤ c && c ≤ '9') || ('a' ≤ c && c ≤ 'f'))
private def nameShape (s : String) : Bool :=
  3 ≤ s.length && s.length ≤ 16 && s.toList.all (fun c =>
    ('0' ≤ c && c ≤ '9') || ('a' ≤ c && c ≤ 'z') || ('A' ≤ c && c ≤ 'Z') || c == '_')
private def actor (r : Actor) : Except String Account := do
  if r.kind > 1 || r.validity > 2 then throw "Unsupported account kind or validity."
  if r.expiresIn < -200000 || r.expiresIn > 200000 || r.issuedAgo < -200000 || r.issuedAgo > 200000 then
    throw "Relative time outside the fixture bound."
  if r.id.isEmpty || !([r.id,r.name,r.profileId].all safe) then throw "Invalid research actor or line field."
  pure ⟨r.id,r.name,r.profileId,if r.kind == 0 then .msa else .offline,r.owns,r.hasToken,
    if r.validity == 0 then .none else if r.validity == 1 then .assumed else .certain,
    remaining r.hasExpiry r.expiresIn r.hasIssue r.issuedAgo⟩
private def evaluate (r : Row) : Except String (List String) := do
  if r.kind > 3 || r.mode > 2 || r.mutation > 2 || r.actors.length > 8 then throw "Unsupported fixture operation."
  if !([r.selected,r.profileId,r.profileName,r.missingUuid,r.demoUuid].all safe) then throw "Invalid research line field."
  if !uuidShape r.missingUuid || !uuidShape r.demoUuid then throw "Invalid external UUID witness shape."
  if r.shapeValid != (uuidShape r.profileId && nameShape r.profileName) then throw "Profile shape witness disagrees with fields."
  let a ← actor r.actor
  let actors ← r.actors.mapM actor
  let ids := actors.map (·.id)
  if ids.eraseDups.length != ids.length then throw "Duplicate fixture actor identity."
  if r.kind == 2 && !ids.contains r.selected then throw "Claim selection is not an admitted actor."
  let mode : Mode := if r.mode == 0 then .normal else if r.mode == 1 then .offline else .demo
  let mutation : Mutation := if r.mutation == 0 then .keep else if r.mutation == 1 then .offline else .demo
  pure (match r.kind with
    | 0 => identityFields a mode r.fill mutation r.missingUuid r.demoUuid
    | 1 => refreshFields a r.inUse
    | 2 => claimFields actors r.selected mode
    | _ => loginFields a mode r.accepted r.shapeValid ⟨r.profileId,r.profileName⟩ r.missingUuid r.demoUuid)

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one account-method comparison input JSON path."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "prism-account-method-components" || input.rows.isEmpty || input.rows.length > 128 then
      IO.eprintln "Unsupported account comparison schema, profile, or count."
      return 2
    match input.rows.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok rows => IO.println (toJson rows).compress; return 0
