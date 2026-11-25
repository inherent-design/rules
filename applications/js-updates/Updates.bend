import Base

# Positive-major stable exact/caret research profile. General semver, tag
# preference, graph resolution and materialization are outside this projection.
type V is Data:
  V{major: Nat,minor: Nat,patch: Nat}
type Spec is Data:
  Exact{version: V}
  Caret{minimum: V}
  Local{reference: String}
type Selection is Data:
  Registry{version: V}
  LocalBasis{basis: Nat}
type Catalog is Data:
  Catalog{stable: List<&2,V>,latest: V}
type Profile is Data:
  Npm{}
  Pnpm{}
  Yarn{}
type Action is Data:
  Refresh{}
  RewriteLatest{}
  Inspect{}
type Evidence is Data:
  Online{}
  Prior{}
  Missing{}
  NotQueried{}
type Dep is Data:
  Dep{name: String,spec: Spec,installed: Selection,saved: Selection,selected: Bool,evidence: Evidence,catalog: Maybe<&2,Catalog>}
type QRow is Data:
  QRow{name: String,current: V,wanted: V,latest: V}
type QResult is Data:
  QResult{row: Maybe<&2,QRow>,unhandled: Bool}

def version_text(v: V) -> String:
  match v:
    case V{major,minor,patch}: Nat.show(major) ++ "." ++ Nat.show(minor) ++ "." ++ Nat.show(patch)
def older(a: V,b: V) -> Bool:
  match a b:
    case V{+am,+an,ap} V{+bm,+bn,bp}:
      Bool.or(Nat.is_lt(am,bm),Bool.and(Nat.is_eq(am,bm),Bool.or(Nat.is_lt(an,bn),Bool.and(Nat.is_eq(an,bn),Nat.is_lt(ap,bp)))))
def same(+a: V,+b: V) -> Bool:
  Bool.not(Bool.or(older(a,b),older(b,a)))
def newer(+a: V,+b: V) -> V:
  Bool.pick(V,older(a,b),b,a)
def spec_text(s: Spec) -> String:
  match s:
    case Exact{v}: version_text(v)
    case Caret{v}: "^" ++ version_text(v)
    case Local{s}: s
def selection_text(s: Selection) -> String:
  match s:
    case Registry{v}: version_text(v)
    case LocalBasis{basis}: "local:" ++ Nat.show(basis)
def permits(s: Spec,+v: V) -> Bool:
  match s:
    case Exact{wanted}: same(wanted,v)
    case Caret{+low}:
      match low v:
        case V{+lm,_,_} V{vm,_,_}: Bool.and(Nat.is_gt(lm,0n),Bool.and(Nat.is_eq(lm,vm),Bool.not(older(v,low))))
    case Local{_}: False{}
def greatest_step(a: V,b: Maybe<&2,V>) -> V:
  match b:
    case None{}: a
    case Some{v}: newer(a,v)
def greatest(vs: List<&2,V>,+s: Spec) -> Maybe<&2,V>:
  match vs:
    case Nil{}: None{}
    case Con{+head,tail}:
      +rest=greatest(tail,s)
      Bool.pick(Maybe<&2,V>,permits(s,head),Some{greatest_step(head,rest)},rest)
def within(c: Catalog,s: Spec) -> Maybe<&2,V>:
  match c:
    case Catalog{vs,_}: greatest(vs,s)
def is_pnpm(p: Profile) -> Bool:
  match p:
    case Pnpm{}: True{}
    case _: False{}
def is_npm(p: Profile) -> Bool:
  match p:
    case Npm{}: True{}
    case _: False{}
def is_yarn(p: Profile) -> Bool:
  match p:
    case Yarn{}: True{}
    case _: False{}
def is_latest(a: Action) -> Bool:
  match a:
    case RewriteLatest{}: True{}
    case _: False{}
def keep_style(s: Spec,v: V) -> Spec:
  match s:
    case Exact{_}: Exact{v}
    case Caret{_}: Caret{v}
    case Local{reference}: Local{reference}
def declaration(p: Profile,a: Action,+before: Spec,+chosen: V) -> Spec:
  Bool.pick(Spec,is_pnpm(p),keep_style(before,chosen),Bool.pick(Spec,is_latest(a),Caret{chosen},before))
def target(+p: Profile,a: Action,+s: Spec,+c: Catalog) -> Maybe<&2,V>:
  match a c:
    case Refresh{} Catalog{vs,_}: greatest(vs,s)
    case _ Catalog{_,+tag}: Some{Bool.pick(V,is_pnpm(p),greatest_step(tag,within(c,s)),tag)}
def demands_registry(p: Profile,a: Action,s: Spec) -> Bool:
  match s:
    case Local{_}: Bool.and(is_yarn(p),is_latest(a))
    case _: True{}
def planned(p: Profile,a: Action,d: Dep,chosen: Maybe<&2,V>) -> Maybe<&2,Dep>:
  match d chosen:
    case Dep{name,spec,_,_,selected,evidence,catalog} Some{+v}:
      Some{Dep{name,declaration(p,a,spec,v),Registry{v},Registry{v},selected,evidence,catalog}}
    case _ None{}: None{}
def with_catalog(+p: Profile,+a: Action,+d: Dep,catalog: Maybe<&2,Catalog>) -> Maybe<&2,Dep>:
  match d catalog:
    case Dep{_,spec,_,_,_,_,_} Some{c}: planned(p,a,d,target(p,a,spec,c))
    case _ None{}: None{}
def plan_one(+p: Profile,+a: Action,+d: Dep) -> Maybe<&2,Dep>:
  match d:
    case Dep{_,spec,_,_,selected,_,catalog}:
      Bool.pick(Maybe<&2,Dep>,Bool.and(selected,demands_registry(p,a,spec)),with_catalog(p,a,d,catalog),Some{d})
def plan_step(head: Maybe<&2,Dep>,tail: Maybe<&2,List<&2,Dep>>) -> Maybe<&2,List<&2,Dep>>:
  match head tail:
    case Some{h} Some{t}: Some{Con{h,t}}
    case _ _: None{}
def plan(ds: List<&2,Dep>,+p: Profile,+a: Action) -> Maybe<&2,List<&2,Dep>>:
  match ds:
    case Nil{}: Some{[]}
    case Con{head,tail}: plan_step(plan_one(p,a,head),plan(tail,p,a))
def current(p: Profile,installed: Selection,saved: Selection) -> Selection:
  match p:
    case Pnpm{}: saved
    case _: installed
def query_values(+p: Profile,name: String,actual: Selection,allowed: Maybe<&2,V>,+latest: V) -> QResult:
  match actual allowed:
    case Registry{+v} Some{+w}:
      +wanted=Bool.pick(V,is_pnpm(p),v,w)
      show=Bool.pick(Bool,is_pnpm(p),older(v,latest),Bool.or(Bool.not(same(v,wanted)),Bool.not(same(wanted,latest))))
      QResult{Bool.pick(Maybe<&2,QRow>,show,Some{QRow{name,v,wanted,latest}},None{}),False{}}
    case Registry{_} None{}: QResult{None{},Bool.not(is_npm(p))}
    case LocalBasis{_} _: QResult{None{},True{}}
def query_catalog(+p: Profile,name: String,+spec: Spec,installed: Selection,saved: Selection,c: Maybe<&2,Catalog>) -> QResult:
  match c:
    case None{}: QResult{None{},Bool.not(is_npm(p))}
    case Some{+catalog}:
      match catalog:
        case Catalog{_,tag}: query_values(p,name,current(p,installed,saved),within(catalog,spec),tag)
def query_spec(p: Profile,name: String,spec: Spec,installed: Selection,saved: Selection,c: Maybe<&2,Catalog>) -> QResult:
  match spec:
    case Local{_}: QResult{None{},False{}}
    case _: query_catalog(p,name,spec,installed,saved,c)
def query_one(+p: Profile,d: Dep) -> QResult:
  match d:
    case Dep{name,spec,installed,saved,selected,_,catalog}:
      Bool.pick(QResult,selected,query_spec(p,name,spec,installed,saved,catalog),QResult{None{},False{}})
def dep_text(d: Dep) -> String:
  match d:
    case Dep{name,spec,installed,saved,_,_,_}:
      name ++ "=" ++ spec_text(spec) ++ "," ++ selection_text(saved) ++ "," ++ selection_text(installed) ++ ";"
def states_text(ds: List<&2,Dep>) -> String:
  match ds:
    case Nil{}: ""
    case Con{head,tail}: dep_text(head) ++ states_text(tail)
def row_text(r: Maybe<&2,QRow>) -> String:
  match r:
    case None{}: ""
    case Some{QRow{name,current,wanted,latest}}: name ++ "=" ++ version_text(current) ++ "," ++ version_text(wanted) ++ "," ++ version_text(latest) ++ ";"
def query_text(q: QResult) -> String:
  match q:
    case QResult{row,_}: row_text(row)
def queries_text(ds: List<&2,Dep>,+p: Profile) -> String:
  match ds:
    case Nil{}: ""
    case Con{head,tail}: query_text(query_one(p,head)) ++ queries_text(tail,p)
def query_nonempty(q: QResult) -> Bool:
  match q:
    case QResult{None{},error}: error
    case QResult{Some{_},_}: True{}
def query_status(ds: List<&2,Dep>,+p: Profile) -> Bool:
  match ds:
    case Nil{}: False{}
    case Con{head,tail}: Bool.or(query_nonempty(query_one(p,head)),query_status(tail,p))
def render_plan(prior: List<&2,Dep>,after: Maybe<&2,List<&2,Dep>>) -> String:
  match after:
    case None{}: "1/" ++ states_text(prior) ++ "/"
    case Some{ds}: "0/" ++ states_text(ds) ++ "/"
def run_text(+p: Profile,+a: Action,+ds: List<&2,Dep>) -> String:
  match a:
    case Inspect{}: Bool.pick(String,query_status(ds,p),"1/","0/") ++ states_text(ds) ++ "/" ++ queries_text(ds,p)
    case _: render_plan(ds,plan(ds,p,a))
def one() -> V: V{1n,0n,0n}
def minor() -> V: V{1n,1n,0n}
def two() -> V: V{2n,0n,0n}
def advanced() -> Catalog: Catalog{[one(),minor(),two()],two()}
def dep(spec: Spec) -> Dep: Dep{"sample",spec,Registry{one()},Registry{one()},True{},Online{},Some{advanced()}}
def retagged_dep() -> Dep:
  Dep{"sample",Caret{two()},Registry{two()},Registry{two()},True{},Online{},Some{Catalog{[one(),minor(),two()],minor()}}}
type Direction is Data:
  Older{}
  Same{}
  Newer{}
  Unknown{}
type Explanation is Data:
  Explanation{evidence: Evidence,saved_basis: Bool,constrained: Maybe<&2,V>,direction: Direction,exact: Bool}
def direction(current: Selection,catalog: Maybe<&2,Catalog>) -> Direction:
  match current catalog:
    case Registry{+v} Some{Catalog{_,+tag}}:
      Bool.pick(Direction,older(v,tag),Newer{},Bool.pick(Direction,older(tag,v),Older{},Same{}))
    case _ _: Unknown{}
def constrained(catalog: Maybe<&2,Catalog>,spec: Spec) -> Maybe<&2,V>:
  match catalog:
    case None{}: None{}
    case Some{c}: within(c,spec)
def is_exact(spec: Spec) -> Bool:
  match spec:
    case Exact{_}: True{}
    case _: False{}
def explain(+p: Profile,d: Dep) -> Explanation:
  match d:
    case Dep{_,+spec,installed,saved,_,evidence,+catalog}:
      Explanation{evidence,is_pnpm(p),constrained(catalog,spec),direction(current(p,installed,saved),catalog),is_exact(spec)}
def explained_direction(e: Explanation) -> Direction:
  match e:
    case Explanation{_,_,_,direction,_}: direction
def explained_evidence(e: Explanation) -> Evidence:
  match e:
    case Explanation{evidence,_,_,_,_}: evidence

law caret_admits_minor:
  {within(advanced(),Caret{one()}) == Some{minor()} : Maybe<&2,V>}
def caret_admits_minor(): {==}
law exact_pin_remains_exact:
  {within(advanced(),Exact{one()}) == Some{one()} : Maybe<&2,V>}
def exact_pin_remains_exact(): {==}
law npm_refresh_keeps_range:
  {run_text(Npm{},Refresh{},[dep(Caret{one()})]) == "0/sample=^1.0.0,1.1.0,1.1.0;/" : String}
def npm_refresh_keeps_range(): {==}
law pnpm_refresh_advances_range:
  {run_text(Pnpm{},Refresh{},[dep(Caret{one()})]) == "0/sample=^1.1.0,1.1.0,1.1.0;/" : String}
def pnpm_refresh_advances_range(): {==}
law yarn_recursive_keeps_range:
  {run_text(Yarn{},Refresh{},[dep(Caret{one()})]) == "0/sample=^1.0.0,1.1.0,1.1.0;/" : String}
def yarn_recursive_keeps_range(): {==}
law rewrite_can_change_pin_style:
  {run_text(Npm{},RewriteLatest{},[dep(Exact{one()})]) == "0/sample=^2.0.0,2.0.0,2.0.0;/" : String}
def rewrite_can_change_pin_style(): {==}
law pnpm_latest_preserves_exact_style:
  {run_text(Pnpm{},RewriteLatest{},[dep(Exact{one()})]) == "0/sample=2.0.0,2.0.0,2.0.0;/" : String}
def pnpm_latest_preserves_exact_style(): {==}
law npm_wanted_is_in_range_target:
  {run_text(Npm{},Inspect{},[dep(Caret{one()})]) == "1/sample=^1.0.0,1.0.0,1.0.0;/sample=1.0.0,1.1.0,2.0.0;" : String}
def npm_wanted_is_in_range_target(): {==}
law pnpm_wanted_is_saved_current:
  {run_text(Pnpm{},Inspect{},[dep(Caret{one()})]) == "1/sample=^1.0.0,1.0.0,1.0.0;/sample=1.0.0,1.0.0,2.0.0;" : String}
def pnpm_wanted_is_saved_current(): {==}
law unavailable_npm_catalog_can_be_silent_success:
  {run_text(Npm{},Inspect{},[Dep{"sample",Exact{one()},Registry{one()},Registry{one()},True{},Missing{},None{}}]) == "0/sample=1.0.0,1.0.0,1.0.0;/" : String}
def unavailable_npm_catalog_can_be_silent_success(): {==}
law explicit_tag_can_downgrade:
  {run_text(Npm{},RewriteLatest{},[retagged_dep()]) == "0/sample=^1.1.0,1.1.0,1.1.0;/" : String}
def explicit_tag_can_downgrade(): {==}
law pnpm_latest_keeps_higher_permitted_version:
  {run_text(Pnpm{},RewriteLatest{},[retagged_dep()]) == "0/sample=^2.0.0,2.0.0,2.0.0;/" : String}
def pnpm_latest_keeps_higher_permitted_version(): {==}
law npm_can_report_an_older_target:
  {run_text(Npm{},Inspect{},[retagged_dep()]) == "1/sample=^2.0.0,2.0.0,2.0.0;/sample=2.0.0,2.0.0,1.1.0;" : String}
def npm_can_report_an_older_target(): {==}
law pnpm_filters_an_older_target:
  {run_text(Pnpm{},Inspect{},[retagged_dep()]) == "0/sample=^2.0.0,2.0.0,2.0.0;/" : String}
def pnpm_filters_an_older_target(): {==}
law explanation_names_older_target:
  {explained_direction(explain(Npm{},retagged_dep())) == Older{} : Direction}
def explanation_names_older_target(): {==}
law explanation_retains_failed_lookup:
  {explained_evidence(explain(Npm{},Dep{"sample",Exact{one()},Registry{one()},Registry{one()},True{},Missing{},None{}})) == Missing{} : Evidence}
def explanation_retains_failed_lookup(): {==}
law explanation_retains_prior_catalog_basis:
  {explained_evidence(explain(Pnpm{},Dep{"sample",Exact{one()},Registry{one()},Registry{one()},True{},Prior{},Some{advanced()}})) == Prior{} : Evidence}
def explanation_retains_prior_catalog_basis(): {==}
