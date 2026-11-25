import Base

# Signed relative seconds under the declared fixed-clock adapter. Unknown time
# stays separate even though the source Qt secsTo policy substitutes zero.
# U32 arithmetic avoids unary-Nat proof reduction at clock-scale values. The
# research decoder bounds every magnitude to 200000, so day addition cannot wrap.
type ATime is Data:
  UnknownTime{}
  Seconds{negative: Bool,magnitude: U32}
def remaining(has_expiry: Bool,+expiry_negative: Bool,+expiry: U32,has_issue: Bool,age_negative: Bool,+age: U32) -> ATime:
  day=Bool.pick(ATime,age_negative,Seconds{False{},U32.add(86400,age)},Bool.pick(ATime,U32.is_gt(age,86400),Seconds{True{},U32.sub(age,86400)},Seconds{False{},U32.sub(86400,age)}))
  Bool.pick(ATime,has_expiry,Seconds{expiry_negative,expiry},Bool.pick(ATime,has_issue,day,UnknownTime{}))
def soon(t: ATime) -> Bool:
  match t:
    case UnknownTime{}: True{}
    case Seconds{negative,magnitude}: Bool.or(negative,U32.is_lt(magnitude,43200))
def refresh(+validity: Nat,uses: Nat,t: ATime) -> Bool:
  Bool.and(Nat.is_eq(uses,0n),Bool.pick(Bool,Nat.is_eq(validity,0n),False{},Bool.pick(Bool,Nat.is_eq(validity,1n),True{},soon(t))))
def time_field(t: ATime) -> String:
  match t:
    case UnknownTime{}: "?"
    case Seconds{negative,magnitude}: Bool.pick(String,negative,"-","") ++ U32.show(magnitude)
def bit(b: Bool) -> String:
  Bool.pick(String,b,"1","0")

type AAccount is Data:
  AAccount{id: String,name: String,profile: String,kind: Nat,owns: Bool,has_token: Bool,validity: Nat,expiry: ATime}
type ASession is Data:
  ASession{session: String,token: String,name: String,uuid: String,user_type: String,mode: Nat}
def actor_id(a: AAccount) -> String:
  match a:
    case AAccount{id,_,_,_,_,_,_,_}: id
def profile_name(a: AAccount) -> String:
  match a:
    case AAccount{_,+name,_,_,_,_,_,_}: Bool.pick(String,String.eq(name,""),"No Minecraft profile",name)
def owns(a: AAccount) -> Bool:
  match a:
    case AAccount{_,_,_,kind,flag,_,_,_}: Bool.and(Nat.is_eq(kind,0n),flag)
def has_profile(a: AAccount) -> Bool:
  match a:
    case AAccount{_,_,profile,_,_,_,_,_}: Bool.not(String.eq(profile,""))
def local_kind(a: AAccount) -> Bool:
  match a:
    case AAccount{_,_,_,kind,_,_,_,_}: Nat.is_eq(kind,1n)
def fill(a: AAccount,mode: Nat,missing_uuid: String) -> ASession:
  match a:
    case AAccount{+id,+name,+profile,+kind,+flag,+has_token,+validity,+expiry}:
      +a : AAccount = AAccount{id,name,profile,kind,flag,has_token,validity,expiry}
      +t=Bool.pick(String,has_token,Bool.pick(String,Nat.is_eq(kind,1n),"0","fixture"),"")
      session=Bool.pick(String,String.eq(t,""),"-","token:" ++ t ++ ":" ++ profile)
      ASession{session,t,profile_name(a),Bool.pick(String,String.eq(profile,""),missing_uuid,profile),Bool.pick(String,Nat.is_eq(kind,0n),"msa","offline"),mode}
def empty_session(mode: Nat) -> ASession:
  ASession{"","","","","",mode}
def offline(s: ASession,name: String) -> ASession:
  match s:
    case ASession{_,_,_,uuid,user_type,mode}: ASession{"-","0",name,uuid,user_type,mode}
def demo(s: ASession,name: String,uuid: String) -> ASession:
  match s:
    case ASession{_,_,_,_,user_type,_}: ASession{"-","0",name,uuid,user_type,2n}
def session_fields(s: ASession) -> List<&2,String>:
  match s:
    case ASession{session,token,name,uuid,user_type,mode}: [session,token,Nat.show(mode),name,uuid,user_type]
def account_fields(a: AAccount) -> List<&2,String>:
  match a:
    case AAccount{+id,+name,+profile,+kind,+flag,+has_token,+validity,+expiry}:
      +a : AAccount = AAccount{id,name,profile,kind,flag,has_token,validity,expiry}
      [id,name,profile_name(a),profile,bit(owns(a)),bit(has_profile(a)),"0"]
def append(left: List<&2,String>,right: List<&2,String>) -> List<&2,String>:
  match left:
    case Nil{}: right
    case Con{head,tail}: Con{head,append(tail,right)}
def identity_fields(+a: AAccount,+mode: Nat,do_fill: Bool,+mutation: Nat,missing_uuid: String,demo_uuid: String) -> List<&2,String>:
  +before=Bool.pick(ASession,do_fill,fill(a,mode,missing_uuid),empty_session(mode))
  after=Bool.pick(ASession,Nat.is_eq(mutation,1n),offline(before,"Offline_Alias"),Bool.pick(ASession,Nat.is_eq(mutation,2n),demo(before,"Demo_Player",demo_uuid),before))
  append([bit(owns(a)),bit(has_profile(a)),profile_name(a)],append(session_fields(before),session_fields(after)))
def refresh_fields(a: AAccount,+in_use: Bool) -> List<&2,String>:
  match a:
    case AAccount{_,_,_,_,_,_,validity,+expiry}:
      [time_field(expiry),bit(in_use),bit(refresh(validity,Bool.pick(Nat,in_use,1n,0n),expiry))]

def find_actor(accounts: List<&2,AAccount>,+id: String) -> Maybe<&2,AAccount>:
  match accounts:
    case Nil{}: None{}
    case Con{+head,tail}: Bool.pick(Maybe<&2,AAccount>,String.eq(actor_id(head),id),Some{head},find_actor(tail,id))
def find_name(accounts: List<&2,AAccount>,+name: String) -> String:
  match accounts:
    case Nil{}: ""
    case Con{+head,tail}: Bool.pick(String,String.eq(profile_name(head),name),actor_id(head),find_name(tail,name))
def named_result(accounts: List<&2,AAccount>,mode: Nat,selected: Maybe<&2,AAccount>) -> String:
  match selected:
    case None{}: ""
    case Some{a}: Bool.pick(String,Nat.is_eq(mode,0n),find_name(accounts,profile_name(a)),"")
def named_holder(+accounts: List<&2,AAccount>,id: String,mode: Nat) -> String:
  named_result(accounts,mode,find_actor(accounts,id))
def captured_result(id: String,mode: Nat,selected: Maybe<&2,AAccount>) -> String:
  match selected:
    case None{}: ""
    case Some{_}: Bool.pick(String,Nat.is_eq(mode,0n),id,"")
def captured_holder(accounts: List<&2,AAccount>,+id: String,mode: Nat) -> String:
  captured_result(id,mode,find_actor(accounts,id))
def count_fields(accounts: List<&2,AAccount>,+holder: String,+n: Nat) -> List<&2,String>:
  match accounts:
    case Nil{}: Nil{}
    case Con{AAccount{+id,_,_,_,_,_,validity,expiry},tail}:
      +used=Bool.pick(Nat,String.eq(holder,id),n,0n)
      append([id,Nat.show(used),bit(refresh(validity,used,expiry))],count_fields(tail,holder,n))
def claim_fields(+accounts: List<&2,AAccount>,+selected: String,+mode: Nat) -> List<&2,String>:
  +source=named_holder(accounts,selected,mode)
  +candidate=captured_holder(accounts,selected,mode)
  append([source,candidate],append(count_fields(accounts,"",0n),append(count_fields(accounts,source,2n),append(count_fields(accounts,source,1n),append(count_fields(accounts,"",0n),append(count_fields(accounts,candidate,2n),count_fields(accounts,"",0n)))))))

type AProfile is Data:
  AProfile{id: String,name: String}
type ALogin is Data:
  ALogin{account: AAccount,session: ASession,dialogs: Nat,requests: Nat,aborted: Bool,error: String}
def update_profile(a: AAccount,p: AProfile) -> AAccount:
  match a:
    case AAccount{id,_,_,kind,flag,has_token,validity,expiry}:
      match p:
        case AProfile{profile,name}: AAccount{id,name,profile,kind,flag,has_token,validity,expiry}
def after_accept(+a: AAccount,+initial: ASession,mode: Nat,+shape: Bool,p: AProfile,missing_uuid: String,variant: Nat) -> ALogin:
  +updated=update_profile(a,p)
  candidate=Bool.pick(ALogin,shape,ALogin{updated,fill(updated,mode,missing_uuid),1n,1n,False{},""},ALogin{a,initial,1n,0n,False{},"Fixture profile admission failed"})
  Bool.pick(ALogin,Nat.is_eq(variant,2n),candidate,ALogin{a,initial,1n,1n,False{},""})
def login(+a: AAccount,+mode: Nat,accepted: Bool,shape: Bool,p: AProfile,+missing_uuid: String,demo_uuid: String,variant: Nat) -> ALogin:
  +initial=fill(a,mode,missing_uuid)
  need=Bool.and(Bool.not(local_kind(a)),Bool.and(Nat.is_eq(mode,0n),Bool.not(has_profile(a))))
  profile=Bool.pick(ALogin,accepted,after_accept(a,initial,mode,shape,p,missing_uuid,variant),ALogin{a,initial,1n,0n,True{},""})
  ordinary : ALogin = ALogin{a,Bool.pick(ASession,Bool.and(Nat.is_eq(mode,1n),Bool.not(local_kind(a))),offline(initial,"Offline_Alias"),initial),0n,1n,False{},""}
  Bool.pick(ALogin,Nat.is_eq(mode,2n),ALogin{a,demo(empty_session(0n),"Demo_Player",demo_uuid),0n,1n,False{},""},Bool.pick(ALogin,need,profile,ordinary))
def login_result_fields(+before: AAccount,r: ALogin) -> List<&2,String>:
  match r:
    case ALogin{account,session,dialogs,requests,aborted,error}:
      append(account_fields(before),append(account_fields(account),append(session_fields(session),[Nat.show(dialogs),Nat.show(requests),bit(aborted),error])))
def login_fields(+a: AAccount,+mode: Nat,+accepted: Bool,+shape: Bool,+p: AProfile,+missing_uuid: String,+demo_uuid: String) -> List<&2,String>:
  append(login_result_fields(a,login(a,mode,accepted,shape,p,missing_uuid,demo_uuid,0n)),append(login_result_fields(a,login(a,mode,accepted,shape,p,missing_uuid,demo_uuid,1n)),login_result_fields(a,login(a,mode,accepted,shape,p,missing_uuid,demo_uuid,2n))))
def joined(fields: List<&2,String>) -> String:
  match fields:
    case Nil{}: ""
    case Con{head,tail}: head ++ "|" ++ joined(tail)
def local_alex() -> AAccount:
  AAccount{"A","Alex","profile-A",1n,False{},True{},0n,Seconds{False{},21600}}
def online_alex() -> AAccount:
  AAccount{"B","Alex","profile-B",0n,True{},True{},2n,Seconds{False{},21600}}
def missing_profile() -> AAccount:
  AAccount{"B","","",0n,True{},True{},2n,Seconds{False{},21600}}
def request_count(r: ALogin) -> Nat:
  match r:
    case ALogin{_,_,_,requests,_,_}: requests
def session_uuid(s: ASession) -> String:
  match s:
    case ASession{_,_,_,uuid,_,_}: uuid
def login_uuid(r: ALogin) -> String:
  match r:
    case ALogin{_,s,_,_,_,_}: session_uuid(s)

law in_use_blocks_assumed_refresh:
  {refresh(1n,1n,UnknownTime{}) == False{} : Bool}
def in_use_blocks_assumed_refresh(): {==}
law unknown_time_remains_distinct_but_refreshes:
  {time_field(remaining(False{},False{},0,False{},False{},0)) == "?" : String}
def unknown_time_remains_distinct_but_refreshes(): {==}
law certain_unknown_time_refreshes:
  {refresh(2n,0n,UnknownTime{}) == True{} : Bool}
def certain_unknown_time_refreshes(): {==}
law exact_twelve_hours_is_outside:
  {refresh(2n,0n,Seconds{False{},43200}) == False{} : Bool}
def exact_twelve_hours_is_outside(): {==}
law one_second_inside_refreshes:
  {refresh(2n,0n,Seconds{False{},43199}) == True{} : Bool}
def one_second_inside_refreshes(): {==}
law issue_fallback_uses_one_day:
  {time_field(remaining(False{},False{},0,True{},False{},43201)) == "43199" : String}
def issue_fallback_uses_one_day(): {==}
law name_collision_holds_first_actor:
  {named_holder([local_alex(),online_alex()],"B",0n) == "A" : String}
def name_collision_holds_first_actor(): {==}
law reversal_changes_source_choice:
  {named_holder([online_alex(),local_alex()],"B",0n) == "B" : String}
def reversal_changes_source_choice(): {==}
law capture_uses_selected_identity:
  {captured_holder([local_alex(),online_alex()],"B",0n) == "B" : String}
def capture_uses_selected_identity(): {==}
law finalization_clears_uses_without_erasing_actor:
  {joined(count_fields([online_alex()],"",0n)) == "B|0|1|" : String}
def finalization_clears_uses_without_erasing_actor(): {==}
law empty_profile_getter_is_not_ready_identity:
  {joined(account_fields(update_profile(online_alex(),AProfile{"",""}))) == "B||No Minecraft profile||1|0|0|" : String}
def empty_profile_getter_is_not_ready_identity(): {==}
law source_accept_keeps_missing_identity:
  {login_uuid(login(missing_profile(),0n,True{},True{},AProfile{"fresh","Fresh_Player"},"missing","demo",0n)) == "missing" : String}
def source_accept_keeps_missing_identity(): {==}
law adopted_profile_is_captured_after_update:
  {login_uuid(login(missing_profile(),0n,True{},True{},AProfile{"fresh","Fresh_Player"},"missing","demo",2n)) == "fresh" : String}
def adopted_profile_is_captured_after_update(): {==}
law candidate_refuses_unadmitted_profile_shape:
  {request_count(login(missing_profile(),0n,True{},False{},AProfile{"",""},"missing","demo",2n)) == 0n : Nat}
def candidate_refuses_unadmitted_profile_shape(): {==}
