namespace ApplicationStudy.PrismAccounts

inductive Kind where | msa | offline deriving BEq, DecidableEq, Repr
inductive Mode where | normal | offline | demo deriving BEq, DecidableEq, Repr
inductive Validity where | none | assumed | certain deriving BEq, DecidableEq, Repr
inductive Mutation where | keep | offline | demo deriving BEq, DecidableEq, Repr
inductive Variant where | current | refillOnly | admitThenRefill deriving BEq, DecidableEq, Repr

/-- Relative seconds under the declared fixed-clock Qt source adapter. Invalid
    timestamps remain none; the policy's Qt invalid-secsTo fallback is separate. -/
def remaining (hasExpiry : Bool) (expiresIn : Int) (hasIssue : Bool) (issuedAgo : Int) : Option Int :=
  if hasExpiry then some expiresIn else if hasIssue then some (86400-issuedAgo) else none
def refresh (validity : Validity) (uses : Nat) (expiry : Option Int) : Bool :=
  if uses != 0 then false else match validity with
  | .none => false
  | .assumed => true
  | .certain => expiry.getD 0 < 43200

structure Account where
  id : String -- unique fixture actor label, not a display name or persistent key
  name : String
  profileId : String
  kind : Kind
  ownsFlag : Bool
  hasToken : Bool
  validity : Validity
  expiry : Option Int
  deriving BEq, DecidableEq, Repr
def profileName (a : Account) : String := if a.name.isEmpty then "No Minecraft profile" else a.name
def ownsMinecraft (a : Account) : Bool := a.kind != .offline && a.ownsFlag
def hasProfile (a : Account) : Bool := !a.profileId.isEmpty
def token (a : Account) : String := if a.hasToken then (if a.kind == .offline then "0" else "fixture") else ""
structure Session where
  session : String
  accessToken : String
  name : String
  uuid : String
  userType : String
  mode : Mode
  deriving BEq, DecidableEq, Repr
def emptySession (mode : Mode) : Session := ⟨"","","","","",mode⟩
/-- missingUuid is an independently checked name-UUID witness for this input,
    not a modeled MD5 implementation or authentication/entitlement evidence. -/
def fillSession (a : Account) (mode : Mode) (missingUuid : String) : Session :=
  let t := token a
  ⟨if t.isEmpty then "-" else "token:"++t++":"++a.profileId,t,profileName a,
    if a.profileId.isEmpty then missingUuid else a.profileId,
    if a.kind == .msa then "msa" else "offline",mode⟩
def makeOffline (s : Session) (name : String) : Session :=
  {s with session := "-",accessToken := "0",name := name}
def makeDemo (s : Session) (name uuid : String) : Session :=
  {s with session := "-",accessToken := "0",name := name,uuid := uuid,mode := .demo}
def identity (a : Account) (mode : Mode) (fill : Bool) (mutation : Mutation)
    (missingUuid demoUuid : String) : Session × Session :=
  let before := if fill then fillSession a mode missingUuid else emptySession mode
  let after := match mutation with
    | .keep => before
    | .offline => makeOffline before "Offline_Alias"
    | .demo => makeDemo before "Demo_Player" demoUuid
  (before,after)

/-- Actual name lookup and the candidate captured-actor selection. All fixture
    actors are retained; this models neither QObject destruction nor UI changes. -/
def byName (accounts : List Account) (selected : String) (mode : Mode) : Option String :=
  if mode != .normal then none else do
    let chosen ← accounts.find? (fun a => a.id == selected)
    let found ← accounts.find? (fun a => profileName a == profileName chosen)
    pure found.id
def captured (accounts : List Account) (selected : String) (mode : Mode) : Option String :=
  if mode == .normal && accounts.any (fun a => a.id == selected) then some selected else none
def usesFor (holder : Option String) (count : Nat) (a : Account) : Nat :=
  if holder == some a.id then count else 0

structure Profile where
  id : String
  name : String
  deriving BEq, DecidableEq, Repr
structure LoginResult where
  account : Account
  session : Session
  dialogs : Nat
  launchRequests : Nat -- the fixture launchInstance stub, not a game start
  aborted : Bool
  error : String
  deriving BEq, DecidableEq, Repr
/-- Prefix after mode admission, synchronous accept-only dialog, stable input
    account, and no network/GUI execution. shapeValid witnesses only the private
    candidate's format check; authentic same-actor response admission is external. -/
def login (a : Account) (mode : Mode) (accepted shapeValid : Bool) (profile : Profile)
    (missingUuid demoUuid : String) (variant : Variant) : LoginResult :=
  if mode == .demo then ⟨a,makeDemo (emptySession .normal) "Demo_Player" demoUuid,0,1,false,""⟩
  else
    let initial := fillSession a mode missingUuid
    let needsProfile := a.kind != .offline && mode == .normal && !hasProfile a
    if needsProfile then
      if !accepted then ⟨a,initial,1,0,true,""⟩
      else if variant == .admitThenRefill then
        if !shapeValid then ⟨a,initial,1,0,false,"Fixture profile admission failed"⟩ else
        let updated := {a with name := profile.name,profileId := profile.id}
        ⟨updated,fillSession updated mode missingUuid,1,1,false,""⟩
      else
        let session := if variant == .refillOnly then fillSession a mode missingUuid else initial
        ⟨a,session,1,1,false,""⟩
    else
      let session := if mode == .offline && a.kind != .offline then makeOffline initial "Offline_Alias" else initial
      ⟨a,session,0,1,false,""⟩

def bit (b : Bool) : String := if b then "1" else "0"
def modeNumber : Mode → Nat | .normal => 0 | .offline => 1 | .demo => 2
def sessionFields (s : Session) : List String :=
  [s.session,s.accessToken,toString (modeNumber s.mode),s.name,s.uuid,s.userType]
def accountFields (a : Account) : List String :=
  [a.id,a.name,profileName a,a.profileId,bit (ownsMinecraft a),bit (hasProfile a),"0"]
def identityFields (a : Account) (mode : Mode) (fill : Bool) (mutation : Mutation) (missingUuid demoUuid : String) : List String :=
  let (before,after) := identity a mode fill mutation missingUuid demoUuid
  [bit (ownsMinecraft a),bit (hasProfile a),profileName a] ++ sessionFields before ++ sessionFields after
def refreshFields (a : Account) (inUse : Bool) : List String :=
  [a.expiry.map toString |>.getD "?",if inUse then "1" else "0",bit (refresh a.validity (if inUse then 1 else 0) a.expiry)]
def countFields (accounts : List Account) (holder : Option String) (count : Nat) : List String :=
  accounts.flatMap fun a => let n := usesFor holder count a
    [a.id,toString n,bit (refresh a.validity n a.expiry)]
def claimFields (accounts : List Account) (selected : String) (mode : Mode) : List String :=
  let source := byName accounts selected mode
  let candidate := captured accounts selected mode
  [source.getD "",candidate.getD ""] ++ countFields accounts none 0 ++ countFields accounts source 2 ++
    countFields accounts source 1 ++ countFields accounts none 0 ++ countFields accounts candidate 2 ++ countFields accounts none 0
def loginFields (a : Account) (mode : Mode) (accepted shapeValid : Bool) (p : Profile)
    (missingUuid demoUuid : String) : List String :=
  [Variant.current,.refillOnly,.admitThenRefill].flatMap fun v =>
    let r := login a mode accepted shapeValid p missingUuid demoUuid v
    accountFields a ++ accountFields r.account ++ sessionFields r.session ++
      [toString r.dialogs,toString r.launchRequests,bit r.aborted,r.error]

def localAlex : Account := ⟨"A","Alex","profile-A",.offline,false,true,.none,some 21600⟩
def onlineAlex : Account := ⟨"B","Alex","profile-B",.msa,true,true,.certain,some 21600⟩
def missingProfile : Account := {onlineAlex with name := "",profileId := ""}
def freshProfile : Profile := ⟨"fresh-id","Fresh_Player"⟩

theorem in_use_blocks_refresh (v : Validity) (t : Option Int) : refresh v 1 t = false := rfl
theorem certain_unknown_expiry_is_not_reported_as_a_known_zero :
    remaining false 0 false 0 = none ∧ refresh .certain 0 none = true := by decide
theorem exact_twelve_hours_is_not_inside_cutoff : refresh .certain 0 (some 43200) = false := by decide
theorem one_second_inside_cutoff_refreshes : refresh .certain 0 (some 43199) = true := by decide
theorem absent_expiry_uses_issue_plus_day : remaining false 0 true 43201 = some 43199 := by decide
theorem local_ownership_flag_does_not_supply_entitlement : ownsMinecraft {localAlex with ownsFlag := true} = false := by decide
theorem offline_conversion_preserves_identity_type_and_mode (s : Session) (n : String) :
    (makeOffline s n).uuid = s.uuid ∧ (makeOffline s n).userType = s.userType ∧ (makeOffline s n).mode = s.mode := by simp [makeOffline]
theorem demo_sets_mode_and_uuid_but_preserves_user_type (s : Session) (n u : String) :
    (makeDemo s n u).mode = .demo ∧ (makeDemo s n u).uuid = u ∧ (makeDemo s n u).userType = s.userType := by simp [makeDemo]
theorem source_name_collision_can_hold_the_other_actor :
    byName [localAlex,onlineAlex] "B" .normal = some "A" := by decide
theorem source_name_selection_changes_with_order :
    byName [onlineAlex,localAlex] "B" .normal = some "B" := by decide
theorem captured_selection_is_stable_across_that_order :
    captured [localAlex,onlineAlex] "B" .normal = some "B" ∧
    captured [onlineAlex,localAlex] "B" .normal = some "B" := by decide
theorem wrong_hold_leaves_selected_actor_refreshable :
    refresh onlineAlex.validity (usesFor (some "A") 2 onlineAlex) onlineAlex.expiry = true ∧
    refresh onlineAlex.validity (usesFor (some "B") 2 onlineAlex) onlineAlex.expiry = false := by decide
theorem one_finalized_claim_does_not_clear_its_sibling : usesFor (some "B") 1 onlineAlex = 1 := by decide
theorem finalization_releases_the_selected_use_count : usesFor none 0 onlineAlex = 0 := by decide
theorem accept_only_dialog_does_not_make_refill_a_fix (a : Account) (m : Mode) (accepted shape : Bool)
    (p : Profile) (u d : String) : login a m accepted shape p u d .refillOnly = login a m accepted shape p u d .current := rfl
theorem current_accept_can_request_launch_without_profile :
    (login missingProfile .normal true true freshProfile "missing-uuid" "demo-uuid" .current).launchRequests = 1 ∧
    hasProfile (login missingProfile .normal true true freshProfile "missing-uuid" "demo-uuid" .current).account = false := by decide
theorem adopted_profile_is_captured_after_update :
    (login missingProfile .normal true true freshProfile "missing-uuid" "demo-uuid" .admitThenRefill).session.uuid = "fresh-id" ∧
    (login missingProfile .normal true true freshProfile "missing-uuid" "demo-uuid" .admitThenRefill).session.name = "Fresh_Player" := by decide
theorem candidate_refuses_unadmitted_profile_shape :
    (login missingProfile .normal true false freshProfile "missing-uuid" "demo-uuid" .admitThenRefill).launchRequests = 0 := by decide
theorem rejected_dialog_keeps_the_already_captured_session :
    (login missingProfile .normal false true freshProfile "missing-uuid" "demo-uuid" .current).aborted = true ∧
    (login missingProfile .normal false true freshProfile "missing-uuid" "demo-uuid" .current).session.uuid = "missing-uuid" := by decide

end ApplicationStudy.PrismAccounts
