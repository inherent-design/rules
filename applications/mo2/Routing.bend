import Base

type RouteMod is Data:
  RouteMod{identity: Nat, reserved: Bool, regular: Bool}
type RouteOrigin is Data:
  ModOrigin{identity: Nat}
  OverwriteOrigin{}
  SaveOrigin{profile: Nat}
  PluginOrigin{identity: Nat}
type RouteRow is Data:
  RouteRow{origin: RouteOrigin, destination: Nat, directory: Bool, create_target: Bool}
type RoutePlugin is Data:
  RoutePlugin{enabled: Bool, rows: List<&2, RouteRow>}
type RouteRequest is Data:
  RouteRequest{active: List<&2, RouteMod>, paths: List<&2, Nat>, custom: Nat, requested: Nat, current: Nat, current_local: Bool, requested_local: Bool, local_feature: Bool, plugins: List<&2, RoutePlugin>}
type RouteResult is Data:
  RouteResult{accepted: Bool, warning: Bool, rows: List<&2, RouteRow>}

def mod_id(m: RouteMod) -> Nat:
  match m:
    case RouteMod{id,reserved,regular}: id

def mod_regular(m: RouteMod) -> Bool:
  match m:
    case RouteMod{id,reserved,regular}: regular

def mod_eligible(m: RouteMod) -> Bool:
  match m:
    case RouteMod{id,reserved,regular}: Bool.and(Bool.not(reserved),regular)

def name_matches(custom: Nat, m: RouteMod) -> Bool:
  match m:
    case RouteMod{id,reserved,regular}: Bool.and(Bool.not(reserved),Nat.is_eq(id,custom))

def matching_any(active: List<&2, RouteMod>, +custom: Nat, +strong: Bool) -> Bool:
  match active:
    case Nil{}: False{}
    case Con{m,rest}:
      +entry = m
      Bool.or(Bool.and(name_matches(custom,entry),Bool.or(Bool.not(strong),mod_regular(entry))),matching_any(rest,custom,strong))

def admits(active: List<&2, RouteMod>, +custom: Nat, strong: Bool) -> Bool:
  Bool.or(Nat.is_eq(custom,0n),matching_any(active,custom,strong))

def rows_for_mod(paths: List<&2, Nat>, +identity: Nat, +custom: Nat) -> List<&2, RouteRow>:
  match paths:
    case Nil{}: Nil{}
    case Con{head,tail}: Con{RouteRow{ModOrigin{identity},head,True{},Nat.is_eq(identity,custom)},rows_for_mod(tail,identity,custom)}

def prepend_mod(+m: RouteMod, paths: List<&2, Nat>, custom: Nat, +rest: List<&2, RouteRow>) -> List<&2, RouteRow>:
  Bool.pick(List<&2, RouteRow>,mod_eligible(m),List.append(&2,RouteRow,rows_for_mod(paths,mod_id(m),custom),rest),rest)

def ordinary(active: List<&2, RouteMod>, +paths: List<&2, Nat>, +custom: Nat) -> List<&2, RouteRow>:
  match active:
    case Nil{}: Nil{}
    case Con{m,rest}: prepend_mod(m,paths,custom,ordinary(rest,paths,custom))

def overwrite(paths: List<&2, Nat>, +custom: Nat) -> List<&2, RouteRow>:
  match paths:
    case Nil{}: Nil{}
    case Con{head,tail}: Con{RouteRow{OverwriteOrigin{},head,True{},Nat.is_eq(custom,0n)},overwrite(tail,custom)}

def plugin_append(p: RoutePlugin, +rest: List<&2, RouteRow>) -> List<&2, RouteRow>:
  match p:
    case RoutePlugin{enabled,rows}: Bool.pick(List<&2, RouteRow>,enabled,List.append(&2,RouteRow,rows,rest),rest)

def plugin_rows(plugins: List<&2, RoutePlugin>) -> List<&2, RouteRow>:
  match plugins:
    case Nil{}: Nil{}
    case Con{p,rest}: plugin_append(p,plugin_rows(rest))

def save_rows(profile: Nat, enabled: Bool, feature: Bool) -> List<&2, RouteRow>:
  Bool.pick(List<&2, RouteRow>,Bool.and(enabled,feature),Con{RouteRow{SaveOrigin{profile},3n,True{},True{}},Nil{}},Nil{})

def assemble(active: List<&2, RouteMod>, +paths: List<&2, Nat>, +custom: Nat, profile: Nat, enabled: Bool, feature: Bool, plugins: List<&2, RoutePlugin>) -> List<&2, RouteRow>:
  List.append(&2,RouteRow,ordinary(active,paths,custom),List.append(&2,RouteRow,save_rows(profile,enabled,feature),List.append(&2,RouteRow,overwrite(paths,custom),plugin_rows(plugins))))

def plan_fields(+active: List<&2, RouteMod>, paths: List<&2, Nat>, +custom: Nat, requested: Nat, current: Nat, current_local: Bool, requested_local: Bool, +feature: Bool, plugins: List<&2, RoutePlugin>, +proposed: Bool) -> RouteResult:
  +admitted = admits(active,custom,proposed)
  +enabled = Bool.pick(Bool,proposed,requested_local,current_local)
  profile = Bool.pick(Nat,proposed,requested,current)
  Bool.pick(RouteResult,admitted,RouteResult{True{},Bool.and(enabled,Bool.not(feature)),assemble(active,paths,custom,profile,enabled,feature,plugins)},RouteResult{False{},False{},Nil{}})

def plan(r: RouteRequest, proposed: Bool) -> RouteResult:
  match r:
    case RouteRequest{active,paths,custom,requested,current,current_local,requested_local,feature,plugins}:
      plan_fields(active,paths,custom,requested,current,current_local,requested_local,feature,plugins,proposed)

def accepted(r: RouteResult) -> Bool:
  match r:
    case RouteResult{a,w,rows}: a

def rows(r: RouteResult) -> List<&2, RouteRow>:
  match r:
    case RouteResult{a,w,value}: value

def base_mods() -> List<&2, RouteMod>:
  Con{RouteMod{5n,True{},False{}},Con{RouteMod{1n,False{},True{}},Con{RouteMod{2n,False{},False{}},Nil{}}}}

law default_accepts_empty_active:
  {accepted(plan(RouteRequest{Nil{},Con{1n,Nil{}},0n,1n,1n,False{},False{},True{},Nil{}},False{})) == True{} : Bool}
def default_accepts_empty_active():
  {==}

law inactive_target_refuses:
  {accepted(plan(RouteRequest{base_mods(),Con{1n,Nil{}},4n,1n,1n,False{},False{},True{},Nil{}},False{})) == False{} : Bool}
def inactive_target_refuses():
  {==}

law reserved_target_refuses:
  {admits(base_mods(),5n,False{}) == False{} : Bool}
def reserved_target_refuses():
  {==}

law current_accepts_nonregular:
  {admits(base_mods(),2n,False{}) == True{} : Bool}
def current_accepts_nonregular():
  {==}

law proposed_refuses_nonregular:
  {admits(base_mods(),2n,True{}) == False{} : Bool}
def proposed_refuses_nonregular():
  {==}

law regular_custom_gets_flag:
  {rows(plan(RouteRequest{base_mods(),Con{1n,Nil{}},1n,1n,1n,False{},False{},True{},Nil{}},False{})) == Con{RouteRow{ModOrigin{1n},1n,True{},True{}},Con{RouteRow{OverwriteOrigin{},1n,True{},False{}},Nil{}}} : List<&2, RouteRow>}
def regular_custom_gets_flag():
  {==}

law current_local_uses_current_profile:
  {rows(plan(RouteRequest{base_mods(),Con{1n,Nil{}},0n,2n,1n,True{},False{},True{},Nil{}},False{})) == Con{RouteRow{ModOrigin{1n},1n,True{},False{}},Con{RouteRow{SaveOrigin{1n},3n,True{},True{}},Con{RouteRow{OverwriteOrigin{},1n,True{},True{}},Nil{}}}} : List<&2, RouteRow>}
def current_local_uses_current_profile():
  {==}

law proposed_does_not_use_current_local_flag:
  {rows(plan(RouteRequest{base_mods(),Con{1n,Nil{}},0n,2n,1n,True{},False{},True{},Nil{}},True{})) == Con{RouteRow{ModOrigin{1n},1n,True{},False{}},Con{RouteRow{OverwriteOrigin{},1n,True{},True{}},Nil{}}} : List<&2, RouteRow>}
def proposed_does_not_use_current_local_flag():
  {==}

law disabled_plugin_contributes_no_rows:
  {plugin_rows(Con{RoutePlugin{False{},Con{RouteRow{PluginOrigin{1n},1n,True{},True{}},Nil{}}},Nil{}}) == Nil{} : List<&2, RouteRow>}
def disabled_plugin_contributes_no_rows():
  {==}
