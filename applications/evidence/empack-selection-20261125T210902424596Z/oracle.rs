//! Actual core policy/update calls. Fixture wrappers retain the earlier caller source.
//! Fictional exact IDs and byte assertions; no catalog, codec, CLI or native writer.
#[path = "fixture.rs"]
mod fixture;
use empack_core::{addition::{AdditionError, AdditionGroup, AdditionPlan}, model::*};
use std::collections::BTreeMap;

fn q(s:&str)->String {assert!(s.is_ascii()&&!s.chars().any(char::is_control));format!("{s:?}")}
fn list(xs:impl IntoIterator<Item=String>)->String {format!("[{}]",xs.into_iter().map(|s|q(&s)).collect::<Vec<_>>().join(","))}
fn pin(p:&empack_core::identity::PinSelector)->String {
    match p {empack_core::identity::PinSelector::ModrinthVersion(v)=>v.as_str().to_owned(),_=>panic!("Fixture supports Modrinth pins only")}
}
fn root_pins(intent:&ProjectIntent)->String {
    format!("{{{}}}",intent.roots.iter().map(|(k,r)|format!("{}:{}",q(k.as_str()),match &r.selection {
        DependencySelection::Automatic=>"null".into(),DependencySelection::ProviderPin(p)=>q(&pin(p)),_=>panic!("Unsupported fixture selection")
    })).collect::<Vec<_>>().join(","))
}
fn policy(name:&str,root:Option<ReleasePolicy>,operation:Option<ReleasePolicy>,selected:Option<&str>) {
    let (mut intent,_)=fixture::base();
    intent.roots.get_mut(&fixture::key_of("a")).unwrap().releases=root;
    let key=selected.map(fixture::key_of);
    let result=intent.release_policy(key.as_ref(),operation);
    let optional=|p:Option<ReleasePolicy>|p.map(|p|q(p.as_str())).unwrap_or("null".into());
    println!("{{\"case\":{},\"kind\":\"preference\",\"project\":{},\"root\":{},\"operation\":{},\"key\":{},\"actual\":{}}}",
        q(name),q(intent.dependency_policy.as_str()),optional(root),optional(operation),selected.map(q).unwrap_or("null".into()),q(result.as_str()));
}
fn error_code(error:&AdditionError)->&'static str {
    match error {AdditionError::InvalidUpdatePin(_)=>"invalid-pin",AdditionError::InvalidProject(_)=>"invalid-project",
        AdditionError::UpdateMissing(_)=>"not-installed",AdditionError::OccupiedKey(_)=>"occupied-key",
        AdditionError::RuntimeMismatch=>"runtime-mismatch",AdditionError::RequiredBy(_)=>"required-by",_=>"other"}
}
fn update(name:&str,held:bool,key:&str,version:u8,requested:Option<(&str,u8)>,runtime_mismatch:bool,foreign:bool) {
    let (mut intent,lock)=fixture::base();
    let a=fixture::key_of("a");
    intent.roots.get_mut(&a).unwrap().releases=Some(ReleasePolicy::StableOnly);
    if held {intent.roots.get_mut(&a).unwrap().set_provider_pin(fixture::version_of(1));}
    let current=ResolvedProject::validate(intent,lock.clone(),lock.intent_revision).unwrap();
    let (mut next_intent,mut next_lock)=fixture::base();
    let id=match key {"a"=>1,"b"=>2,"c"=>3,"d"=>4,_=>panic!("Fixture key")};
    let source_id=if foreign {4}else{id};
    let k=fixture::key_of(key);
    let mut root=fixture::root_of(source_id);
    root.releases=Some(ReleasePolicy::Any);
    root.set_provider_pin(fixture::version_of(version));
    next_intent.metadata.name="Request metadata is not pack metadata".into();
    next_intent.roots=BTreeMap::from([(k.clone(),root)]);
    next_lock.dependencies=BTreeMap::from([(k.clone(),fixture::dependency_of(source_id,version))]);
    next_lock.required_edges.clear();
    next_lock.coverage=BTreeMap::from([(k.clone(),Coverage::CompleteForSelection)]);
    if runtime_mismatch {next_lock.runtime.loader_version=Some(LoaderVersion::parse("0.16.1").unwrap());}
    let next=ResolvedProject::validate(next_intent,next_lock.clone(),next_lock.intent_revision).unwrap();
    let group=AdditionGroup::from_resolved(&next).unwrap();
    let pins=requested.map(|(k,v)|(fixture::key_of(k),fixture::version_of(v))).into_iter().collect();
    let before=format!("{:?}|{:?}",current.intent(),current.lock());
    let result=AdditionPlan::prepare_update_with_pins(&current,&group,&pins);
    let requested_json=requested.map(|(k,v)|format!("{{\"key\":{},\"pin\":{}}}",q(k),q(&pin(&fixture::version_of(v))))).unwrap_or("null".into());
    let facts=match result {
        Ok(plan)=>{
            let changed=list(plan.changed().iter().map(|k|k.as_str().into()));
            let existing=list(plan.existing_roots().iter().map(|k|k.as_str().into()));
            let after=plan.resolve(SemanticRevision([2;32])).unwrap();
            let selected=after.lock().dependencies[&k].selected.as_ref().unwrap();
            let mut restored=after.intent().clone();
            for (k,r) in &current.intent().roots {
                if requested.is_some_and(|(key,_)| key==k.as_str()) {
                    if let Some(n)=restored.roots.get_mut(k){n.selection=r.selection.clone();n.releases=r.releases;}
                }
            }
            format!("\"accepted\":true,\"error\":null,\"message\":null,\"afterPins\":{},\"afterIntentDebug\":{},\"otherIntentPreserved\":{},\"selected\":{},\"changed\":{},\"existing\":{}",
                root_pins(after.intent()),q(&format!("{:?}",after.intent())),restored==*current.intent(),q(&pin(&selected.selection)),changed,existing)
        }
        Err(error)=>format!("\"accepted\":false,\"error\":{},\"message\":{},\"afterPins\":null,\"afterIntentDebug\":null,\"otherIntentPreserved\":null,\"selected\":null,\"changed\":null,\"existing\":null",q(error_code(&error)),q(&error.to_string()))
    };
    println!("{{\"case\":{},\"kind\":\"update\",\"held\":{},\"key\":{},\"version\":{},\"request\":{},\"runtimeMismatch\":{},\"foreignIdentity\":{},\"beforePins\":{},\"beforeIntentDebug\":{},\"inputUnchanged\":{}, {facts}}}",
        q(name),held,q(key),version,requested_json,runtime_mismatch,foreign,root_pins(current.intent()),q(&format!("{:?}",current.intent())),before==format!("{:?}|{:?}",current.intent(),current.lock()));
}
fn invalid_pin_preference() {
    let (mut intent,lock)=fixture::base();
    let root=intent.roots.get_mut(&fixture::key_of("a")).unwrap();
    root.releases=Some(ReleasePolicy::StableOnly);
    root.selection=DependencySelection::ProviderPin(fixture::version_of(1));
    let result=ResolvedProject::validate(intent,lock.clone(),lock.intent_revision);
    println!("{{\"case\":\"pin-and-preference-invalid\",\"kind\":\"admission\",\"accepted\":{},\"message\":{}}}",result.is_ok(),result.err().map(|e|q(&e.to_string())).unwrap_or("null".into()));
}
fn main() {
    policy("project-default",None,None,Some("a"));
    policy("root-preference",Some(ReleasePolicy::StableOnly),None,Some("a"));
    policy("operation-override",Some(ReleasePolicy::StableOnly),Some(ReleasePolicy::Any),Some("a"));
    policy("missing-key-default",Some(ReleasePolicy::StableOnly),None,Some("missing"));
    policy("retained-key-default",Some(ReleasePolicy::StableOnly),None,Some("c"));
    policy("operation-without-key",None,Some(ReleasePolicy::StableOnly),None);
    invalid_pin_preference();
    update("automatic-keeps-author-policy",false,"a",2,None,false,false);
    update("explicit-pin-replaces-root-preference",false,"a",2,Some(("a",2)),false,false);
    update("held-without-reviewed-pin",true,"a",2,None,false,false);
    update("held-reviewed-pin",true,"a",2,Some(("a",2)),false,false);
    update("held-mismatched-pin",true,"a",2,Some(("a",3)),false,false);
    update("pin-not-requested",false,"a",2,Some(("b",1)),false,false);
    update("pin-retained-not-author-root",false,"c",2,Some(("c",2)),false,false);
    update("retained-without-promotion",false,"c",2,None,false,false);
    update("same-held-pin",true,"a",1,Some(("a",1)),false,false);
    update("new-identity-is-not-update",false,"d",2,None,false,false);
    update("runtime-change-is-not-update",false,"a",2,None,true,false);
    update("project-change-is-not-update",false,"a",2,None,false,true);
}
