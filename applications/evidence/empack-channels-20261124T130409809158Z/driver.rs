// Fixed, public test seeds. These are not publisher credentials.
use ed25519_dalek::{SigningKey, VerifyingKey};
use engine::release::trust::{ChannelDocument, ChannelRelease, EnvelopeKind, PublisherTrust, SequenceFloor, sign};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

fn digest(bytes: &[u8]) -> String {
    Sha256::digest(bytes).iter().map(|b| format!("{b:02x}")).collect()
}

fn outcome(value: anyhow::Result<engine::release::trust::AuthenticatedChannel>) -> (Value, Option<SequenceFloor>) {
    match value {
        Ok(channel) => (json!({"accepted": true, "floor": channel.floor(), "document": channel.document()}), Some(channel.floor().clone())),
        Err(error) => {
            let diagnostic = error.chain().find_map(|e| e.downcast_ref::<engine::diagnostics::Diagnostic>())
                .map(|d| serde_json::to_value(d).unwrap());
            (json!({"accepted": false, "error": format!("{error:#}"), "diagnostic": diagnostic}), None)
        }
    }
}

fn evaluate(name: &str, document: &ChannelDocument, payload: &[u8], envelope: &[u8], pack: &str,
            origin: &str, keys: Vec<VerifyingKey>, expected_name: &str, engine: &str, floor: Option<&SequenceFloor>) -> Option<SequenceFloor> {
    let key_bytes: Vec<String> = keys.iter().map(|k| k.as_bytes().iter().map(|b| format!("{b:02x}")).collect()).collect();
    let trust = PublisherTrust::enroll(pack.into(), origin, keys);
    let (phase, result, next) = match trust {
        Ok(trust) => {
            let (result, next) = outcome(trust.channel(envelope, expected_name, &semver::Version::parse(engine).unwrap(), floor));
            ("channel", result, next)
        },
        Err(error) => ("enrollment", json!({"accepted": false, "error": format!("{error:#}")}), None),
    };
    println!("{}", json!({"case":name,"request":{"document":document,"payloadSha256":digest(payload),
        "envelope":serde_json::from_slice::<Value>(envelope).unwrap(),"payloadUtf8":String::from_utf8(payload.to_vec()).unwrap(),
        "enrolledPack":pack,"origin":origin,"publicKeys":key_bytes,"expectedName":expected_name,"engine":engine,"floor":floor},
        "observed":{"phase":phase,"result":result}}));
    next
}

fn encoded(doc: &ChannelDocument, keys: &[&SigningKey]) -> (Vec<u8>, Vec<u8>) {
    let payload = doc.encode().unwrap();
    let envelope = sign(EnvelopeKind::Channel, &payload, keys).unwrap();
    (payload, envelope)
}

fn main() {
    let a = SigningKey::from_bytes(&[7; 32]);
    let b = SigningKey::from_bytes(&[8; 32]);
    let va = a.verifying_key();
    let vb = b.verifying_key();
    let base = ChannelDocument { schema: 2, pack: "fixture-pack".into(), channel: "stable".into(), sequence: 3,
        release: ChannelRelease { id: digest(b"fixture release payload not decoded by this channel study"),
            url: "https://publisher.invalid/releases/fixture/release.json".into(), maximum_bytes: 4096 },
        minimum_engine: ">=0.8.5-beta".into() };
    let (payload, envelope) = encoded(&base, &[&a]);
    let floor = evaluate("baseline", &base, &payload, &envelope, "fixture-pack", "https://publisher.invalid",
        vec![va], "stable", "0.8.8-beta", None).unwrap();
    let run = |name: &str, doc: &ChannelDocument, keys: &[&SigningKey], enrolled: Vec<VerifyingKey>, selected_floor: Option<&SequenceFloor>| {
        let (p, e) = encoded(doc, keys);
        evaluate(name, doc, &p, &e, "fixture-pack", "https://publisher.invalid", enrolled, "stable", "0.8.8-beta", selected_floor)
    };
    run("same-offer-retry", &base, &[&a], vec![va], Some(&floor));
    let mut doc = base.clone(); doc.sequence = 2;
    run("older-offer-with-floor", &doc, &[&a], vec![va], Some(&floor));
    run("older-offer-without-floor", &doc, &[&a], vec![va], None);
    doc = base.clone(); doc.release.maximum_bytes += 1;
    run("same-sequence-changed-bound", &doc, &[&a], vec![va], Some(&floor));
    doc.sequence = 4;
    run("higher-sequence-changed-bound", &doc, &[&a], vec![va], Some(&floor));
    let pretty = format!(" \n{}\n", String::from_utf8(payload.clone()).unwrap()).into_bytes();
    let pretty_envelope = sign(EnvelopeKind::Channel, &pretty, &[&a]).unwrap();
    assert_eq!(serde_json::from_slice::<Value>(&pretty).unwrap(), serde_json::from_slice::<Value>(&payload).unwrap());
    evaluate("same-sequence-equivalent-json", &base, &pretty, &pretty_envelope, "fixture-pack", "https://publisher.invalid",
        vec![va], "stable", "0.8.8-beta", Some(&floor));
    run("extra-signature-same-payload", &base, &[&a, &b], vec![va], Some(&floor));
    run("new-key-not-enrolled", &base, &[&b], vec![va], Some(&floor));
    run("new-key-explicitly-enrolled", &base, &[&b], vec![va, vb], Some(&floor));
    run("any-one-enrolled-signer", &base, &[&a], vec![va, vb], Some(&floor));
    evaluate("no-enrolled-keys", &base, &payload, &envelope, "fixture-pack", "https://publisher.invalid", vec![], "stable", "0.8.8-beta", None);
    evaluate("duplicate-enrolled-keys", &base, &payload, &envelope, "fixture-pack", "https://publisher.invalid", vec![va, va], "stable", "0.8.8-beta", None);
    evaluate("wrong-enrolled-pack", &base, &payload, &envelope, "other-pack", "https://publisher.invalid", vec![va], "stable", "0.8.8-beta", None);
    evaluate("wrong-selected-channel", &base, &payload, &envelope, "fixture-pack", "https://publisher.invalid", vec![va], "other", "0.8.8-beta", None);
    evaluate("origin-path-query-not-authority", &base, &payload, &envelope, "fixture-pack", "https://publisher.invalid/path?fixture=1", vec![va], "stable", "0.8.8-beta", None);
    evaluate("enrollment-http-refused", &base, &payload, &envelope, "fixture-pack", "http://publisher.invalid", vec![va], "stable", "0.8.8-beta", None);
    evaluate("enrollment-credentials-refused", &base, &payload, &envelope, "fixture-pack", "https://fixture@publisher.invalid", vec![va], "stable", "0.8.8-beta", None);
    for (name, url) in [("other-release-origin", "https://other.invalid/release.json"),
        ("default-https-port", "https://publisher.invalid:443/release.json"),
        ("different-https-port", "https://publisher.invalid:444/release.json")] {
        doc = base.clone(); doc.release.url = url.into();
        run(name, &doc, &[&a], vec![va], None);
    }
    for (name, requirement) in [("stable-only-engine-requirement", ">=0.8.0"),
        ("exact-current-engine", "=0.8.8-beta"),
        ("upper-bound-still-enforced", ">=0.8.5-beta, <0.8.8-0"),
        ("other-prerelease-channel", ">=0.8.5-alpha"),
        ("higher-engine-required", ">=0.9.0-beta")] {
        doc = base.clone(); doc.minimum_engine = requirement.into();
        run(name, &doc, &[&a], vec![va], None);
    }
    for key in ["pack", "origin", "channel"] {
        let mut changed = floor.clone();
        match key { "pack" => changed.pack = "other-pack".into(), "origin" => changed.origin = "https://other.invalid".into(),
            _ => changed.channel = "other".into() }
        run(&format!("floor-{key}-mismatch"), &base, &[&a], vec![va], Some(&changed));
    }
    for name in ["wrong-envelope-kind", "unsupported-algorithm", "duplicate-signature", "uppercase-payload", "bad-known-signature",
        "unknown-envelope-field", "bad-unknown-cosigner", "bad-known-cosigner"] {
        let mut value: Value = serde_json::from_slice(&envelope).unwrap();
        match name {
            "wrong-envelope-kind" => value["kind"] = "release".into(),
            "unsupported-algorithm" => value["signatures"][0]["algorithm"] = "none".into(),
            "duplicate-signature" => { let sig = value["signatures"][0].clone(); value["signatures"].as_array_mut().unwrap().push(sig); },
            "uppercase-payload" => value["payload"] = value["payload"].as_str().unwrap().to_uppercase().into(),
            "bad-known-signature" => value["signatures"][0]["signature"] = "00".repeat(64).into(),
            "unknown-envelope-field" => value["unrecognized"] = true.into(),
            _ => value["signatures"].as_array_mut().unwrap().push(json!({"algorithm":"ed25519",
                "key":engine::release::trust::key_id(&vb),"signature":"00".repeat(64)})),
        }
        let changed = serde_json::to_vec(&value).unwrap();
        evaluate(name, &base, &payload, &changed, "fixture-pack", "https://publisher.invalid",
            if name == "bad-known-cosigner" {vec![va, vb]} else {vec![va]}, "stable", "0.8.8-beta", None);
    }
    let mut unknown = serde_json::to_value(&base).unwrap(); unknown["expires"] = "2000-01-01T00:00:00Z".into();
    let dated_payload = serde_json::to_vec(&unknown).unwrap();
    let decoded = ChannelDocument::decode(&dated_payload);
    println!("{}", json!({"case":"calendar-field-not-supported","request":{"payloadUtf8":String::from_utf8(dated_payload.clone()).unwrap()},
        "observed":{"phase":"decode","accepted":decoded.is_ok(),"error":decoded.err().map(|e|format!("{e:#}"))}}));
    let duplicated_signer = sign(EnvelopeKind::Channel, &payload, &[&a, &a]);
    println!("{}", json!({"case":"duplicate-signing-input","request":{"payloadSha256":digest(&payload)},
        "observed":{"phase":"sign","accepted":duplicated_signer.is_ok(),"error":duplicated_signer.err().map(|e|format!("{e:#}"))}}));
}
