//! Actual unchanged core calls; supplied fictional selections, no observed native bytes.
#[path = "fixture.rs"]
mod fixture;
use empack_core::{addition::{AdditionError, AdditionGroup, AdditionPlan}, model::*};
use std::collections::{BTreeMap, BTreeSet};

fn q(s: &str) -> String { assert!(s.is_ascii() && !s.chars().any(char::is_control)); format!("{s:?}") }
fn pin_of(intent: &ProjectIntent) -> String {
    match &intent.roots[&fixture::key_of("a")].selection {
        DependencySelection::Automatic => "null".into(),
        DependencySelection::ProviderPin(p) if *p == fixture::version_of(1) => q("Version1"),
        _ => panic!("Unsupported authored policy in fixture")
    }
}
fn keys<'a>(xs: impl IntoIterator<Item = &'a DependencyKey>) -> String {
    format!("[{}]", xs.into_iter().map(|k| q(k.as_str())).collect::<Vec<_>>().join(","))
}
fn view(project: &ResolvedProject, source: &ProjectIntent) -> String {
    let selected = &project.lock().dependencies[&fixture::key_of("a")].selected.as_ref().unwrap().selection;
    let selected = if *selected == fixture::version_of(1) { 1 } else if *selected == fixture::version_of(2) { 2 } else { panic!("Unsupported selection") };
    let lock = project.lock();
    format!("{{\"rootPin\":{},\"roots\":{},\"locked\":{},\"selected\":{selected},\"intentPreserved\":{},\"runtime\":{},\"edges\":{},\"coverageComplete\":{}}}",
        pin_of(project.intent()), keys(project.intent().roots.keys()), keys(lock.dependencies.keys()),
        project.intent() == source, q(lock.runtime.minecraft.as_str()),
        keys(lock.required_edges.get(&fixture::key_of("a")).into_iter().flatten()),
        lock.coverage.values().all(|v| *v == Coverage::CompleteForSelection))
}
fn run(name: &str, phase: &str, held: bool, version: u8, request_pinned: bool, missing: bool, runtime_matches: bool) {
    let (mut source, mut prior) = fixture::base();
    if held { source.roots.get_mut(&fixture::key_of("a")).unwrap().set_provider_pin(fixture::version_of(1)); }
    if missing { source.roots.insert(fixture::key_of("c"), fixture::root_of(3)); }
    // A fully valid old project exists only for the existing-lock operation.
    let current = ResolvedProject::validate(source.clone(), prior.clone(), prior.intent_revision).unwrap();
    let mut requested_intent = fixture::base().0;
    let mut requested_lock = prior.clone();
    requested_lock.dependencies.remove(&fixture::key_of("c"));
    requested_lock.coverage.remove(&fixture::key_of("c"));
    requested_lock.dependencies.insert(fixture::key_of("a"), fixture::dependency_of(1, version));
    if request_pinned { requested_intent.roots.get_mut(&fixture::key_of("a")).unwrap().set_provider_pin(fixture::version_of(version)); }
    if phase == "validate-target" {
        source.runtime.minecraft = GameVersion::parse("1.21.2").unwrap();
        if runtime_matches { prior.runtime.minecraft = source.runtime.minecraft.clone(); }
        prior.dependencies.insert(fixture::key_of("a"), fixture::dependency_of(1, version));
    } else if !runtime_matches {
        requested_intent.runtime.minecraft = GameVersion::parse("1.21.2").unwrap();
        requested_lock.runtime.minecraft = requested_intent.runtime.minecraft.clone();
    }
    let requested = ResolvedProject::validate(requested_intent, requested_lock.clone(), requested_lock.intent_revision).unwrap();
    let group = AdditionGroup::from_resolved(&requested).unwrap();
    let before = format!("{source:?}|{prior:?}|{current:?}|{group:?}");
    let (result, changed, bindings): (Result<ResolvedProject, String>, Option<String>, Option<String>) = if phase == "validate-target" {
        (ResolvedProject::validate(source.clone(), prior.clone(), prior.intent_revision).map_err(|_| "invalid-project".into()), None, None)
    } else {
        let result = if phase == "existing-adopt" { AdditionPlan::prepare_adoption(&current, &group) }
                     else if phase == "initial-adopt" { AdditionPlan::prepare_initial_adoption(&source, &group) }
                     else { panic!("Unknown phase") };
        match result {
            Ok(plan) => {
                let changed = keys(plan.changed());
                let bindings = keys(plan.bindings().keys());
                (Ok(plan.resolve(SemanticRevision([2;32])).unwrap()), Some(changed), Some(bindings))
            }
            Err(e) => (Err(match e { AdditionError::RuntimeMismatch => "runtime-mismatch", AdditionError::InvalidProject(_) => "invalid-project", _ => panic!("Unexpected error {e:?}") }.into()), None, None)
        }
    };
    assert_eq!(before, format!("{source:?}|{prior:?}|{current:?}|{group:?}"));
    let accepted = result.is_ok();
    let (error, after) = match result { Ok(p) => ("null".into(), view(&p, &source)), Err(e) => (q(&e), "null".into()) };
    println!("{{\"case\":{},\"phase\":{},\"held\":{held},\"version\":{version},\"requestPinned\":{request_pinned},\"missingRoot\":{missing},\"runtimeMatches\":{runtime_matches},\"inputUnchanged\":true,\"accepted\":{accepted},\"error\":{error},\"after\":{after},\"changed\":{},\"bindings\":{}}}",
        q(name), q(phase), changed.unwrap_or("null".into()), bindings.unwrap_or("null".into()));
}
fn main() {
    run("existing-auto-same", "existing-adopt", false, 1, false, false, true);
    run("existing-auto-new", "existing-adopt", false, 2, false, false, true);
    run("existing-auto-new-group-pin", "existing-adopt", false, 2, true, false, true);
    run("existing-held-same", "existing-adopt", true, 1, true, false, true);
    run("existing-held-new", "existing-adopt", true, 2, false, false, true);
    run("existing-held-new-group-pin", "existing-adopt", true, 2, true, false, true);
    run("existing-runtime-different", "existing-adopt", false, 2, false, false, false);
    run("initial-auto-new", "initial-adopt", false, 2, true, false, true);
    run("initial-held-same", "initial-adopt", true, 1, true, false, true);
    run("initial-held-new", "initial-adopt", true, 2, true, false, true);
    run("initial-missing-authored-root", "initial-adopt", false, 1, false, true, true);
    run("target-old-runtime", "validate-target", false, 1, false, false, false);
    run("target-retagged-auto", "validate-target", false, 1, false, false, true);
    run("target-retagged-held", "validate-target", true, 1, false, false, true);
    run("target-changed-held", "validate-target", true, 2, false, false, true);
}
