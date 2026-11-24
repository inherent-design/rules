//! Call the unchanged core policy. Inputs are research cases, not game launches.
use empack_core::java::JavaPolicy;

fn number(n: Option<u16>) -> String { n.map(|v| v.to_string()).unwrap_or_else(|| "-".into()) }
fn emit(name: &str, game: &str, constraints: &[(u16, Option<u16>)], preferred: Option<u16>, actual: Option<u16>) {
    let mut policy = JavaPolicy::for_game(game);
    let mut failure = None;
    for &(minimum, maximum) in constraints {
        match policy.constrain(minimum, maximum, "research constraint") {
            Ok(next) => policy = next,
            Err(error) => { failure = Some(("constraint", error.0)); break; }
        }
    }
    let mut selected = None;
    if failure.is_none() {
        if let Some(actual) = actual {
            match policy.check_actual(actual, preferred.expect("explicit preference in actual-check case")) {
                Ok(()) => selected = Some(actual),
                Err(error) => failure = Some(("actual", error.0)),
            }
        } else {
            match policy.select(preferred) {
                Ok(value) => selected = Some(value),
                Err(error) => failure = Some(("selection", error.0)),
            }
        }
    }
    let bounds = constraints.iter().map(|(a,b)| format!("{}:{}", a, number(*b))).collect::<Vec<_>>().join(",");
    let supported = policy.supported().map(|v| v.iter().map(u16::to_string).collect::<Vec<_>>().join(",")).unwrap_or_else(|| "-".into());
    let (stage, diagnostic) = failure.unwrap_or(("ok", String::new()));
    assert!(!diagnostic.contains(['\t', '\n']));
    println!("{name}\t{game}\t{bounds}\t{}\t{}\t{}\t{}\t{supported}\t{}\t{stage}\t{}\t{diagnostic}",
        number(preferred), number(actual), number(policy.historical_minimum()), policy.required_minimum(),
        number(policy.recommended()), number(selected));
}

fn main() {
    for line in include_str!("profiles.csv").lines().filter(|s| !s.starts_with('#') && !s.is_empty()) {
        let game = line.split('|').next().unwrap();
        emit(&format!("profile/{game}"), game, &[], None, None);
    }
    for game in ["1.17.99", "1.21.12", "26.9", "26.4-snapshot-999", "1.18-pre999", "custom"] {
        emit(&format!("unknown/{game}"), game, &[], None, None);
    }
    for game in ["1.0", "1.17.1", "1.20.4", "1.21.1", "26.1", "custom"] {
        for preferred in [0, 7, 8, 11, 16, 17, 18, 21, 25, 27, 65535] {
            emit(&format!("select/{game}/{preferred}"), game, &[], Some(preferred), None);
        }
        for preferred in [8, 16, 17, 21] {
            for actual in [8, 16, 17, 21, 25, 27] {
                emit(&format!("actual/{game}/{preferred}/{actual}"), game, &[], Some(preferred), Some(actual));
            }
        }
    }
    for (name, game, constraints, preferred, actual) in [
        ("upper16", "1.17.1", vec![(0,Some(16))], None, None),
        ("lower17", "1.17.1", vec![(17,None)], None, None),
        ("empty18", "1.17.1", vec![(18,None)], None, None),
        ("reversed", "1.17.1", vec![(17,Some(16))], None, None),
        ("raise-floor", "1.0", vec![(0,Some(7))], None, None),
        ("unknown-min", "custom", vec![(17,None)], Some(21), None),
        ("unknown-under", "custom", vec![(17,None)], Some(8), None),
        ("unknown-upper", "custom", vec![(17,Some(25))], Some(21), None),
        ("retained-pref-refused", "1.17.1", vec![(17,None)], Some(16), None),
        ("retained-pref-actual", "1.17.1", vec![(17,None)], Some(16), Some(17)),
        ("chain-empty", "1.17.1", vec![(0,Some(16)),(17,None)], None, None),
        ("chain-idempotent", "1.17.1", vec![(16,None),(16,None)], None, None),
        ("chain-narrow", "1.17.1", vec![(16,None),(0,Some(16))], None, None),
        ("unknown-actual-exact", "custom", vec![(17,None)], Some(21), Some(21)),
        ("unknown-actual-newer", "custom", vec![(17,None)], Some(21), Some(25)),
    ] {
        emit(&format!("constraint/{name}"), game, &constraints, preferred, actual);
    }
}
