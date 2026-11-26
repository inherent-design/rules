// Public fixture seed only; not a real publisher credential.
use engine::release::trust::{ChannelDocument, ChannelRelease, EnvelopeKind, PublisherTrust, sign};
use ed25519_dalek::SigningKey;
use serde_json::json;
use sha2::{Digest, Sha256};

fn hash(bytes: &[u8]) -> String {
    Sha256::digest(bytes).iter().map(|b| format!("{b:02x}")).collect()
}

fn main() {
    let key = SigningKey::from_bytes(&[7; 32]);
    let public = key.verifying_key();
    let trust = PublisherTrust::enroll("fixture-pack".into(), "https://publisher.invalid", vec![public]).unwrap();
    let base = ChannelDocument {
        schema: 2, pack: "fixture-pack".into(), channel: "stable".into(), sequence: 3,
        release: ChannelRelease { id: hash(b"fixture release, not decoded"),
            url: "https://publisher.invalid/releases/fixture/release.json".into(), maximum_bytes: 4096 },
        minimum_engine: ">=0.8.5-beta".into(),
    };
    for name in ["exact-retry", "prior-payload-whitespace", "prior-payload-key-order", "prior-envelope-whitespace",
                 "changed-release-same-sequence", "changed-bound-same-sequence", "older-candidate", "advanced-same-release",
                 "advanced-after-whitespace", "advanced-after-old-engine-bound", "invalid-prior-signature"] {
        let mut prior = base.clone();
        let mut candidate = base.clone();
        if name == "changed-release-same-sequence" { candidate.release.id = hash(b"different release"); }
        if name == "changed-bound-same-sequence" { candidate.release.maximum_bytes += 1; }
        if name == "older-candidate" { candidate.sequence = 2; }
        if name.starts_with("advanced-") { candidate.sequence = 4; }
        if name == "advanced-after-old-engine-bound" { prior.minimum_engine = ">=99.0.0".into(); }
        let mut prior_payload = prior.encode().unwrap();
        if name == "prior-payload-whitespace" || name == "advanced-after-whitespace" {
            prior_payload = format!(" \n{}\n", String::from_utf8(prior_payload).unwrap()).into_bytes();
        }
        if name == "prior-payload-key-order" {
            // Value uses its deterministic map order, distinct from struct field order.
            prior_payload = serde_json::to_vec(&serde_json::to_value(&prior).unwrap()).unwrap();
        }
        let candidate_payload = candidate.encode().unwrap();
        let mut prior_envelope = sign(EnvelopeKind::Channel, &prior_payload, &[&key]).unwrap();
        if name == "prior-envelope-whitespace" {
            prior_envelope = format!(" \n{}\n", String::from_utf8(prior_envelope).unwrap()).into_bytes();
        }
        if name == "invalid-prior-signature" {
            let mut envelope: serde_json::Value = serde_json::from_slice(&prior_envelope).unwrap();
            envelope["signatures"][0]["signature"] = json!("00".repeat(64));
            prior_envelope = serde_json::to_vec(&envelope).unwrap();
        }
        let candidate_envelope = sign(EnvelopeKind::Channel, &candidate_payload, &[&key]).unwrap();
        let publisher = engine::fixture_publisher(&prior_envelope, candidate.clone(), public);
        let prior_engine = if name == "advanced-after-old-engine-bound" { "99.0.0" } else { "0.8.8-beta" };
        let prior_auth = trust.channel(&prior_envelope, "stable", &semver::Version::parse(prior_engine).unwrap(), None);
        let floor = prior_auth.as_ref().ok().map(|p| p.floor().clone());
        let subscriber = floor.as_ref().map(|floor| trust.channel(&candidate_envelope, "stable", &semver::Version::parse("0.8.8-beta").unwrap(), Some(floor)));
        println!("{}", json!({"case":name,"request":{
            "prior":prior,"candidate":candidate,"priorEngine":prior_engine,"candidateEngine":"0.8.8-beta",
            "priorPayloadUtf8":String::from_utf8(prior_payload.clone()).unwrap(),
            "candidatePayloadUtf8":String::from_utf8(candidate_payload.clone()).unwrap(),
            "priorEnvelope":serde_json::from_slice::<serde_json::Value>(&prior_envelope).unwrap(),
            "candidateEnvelope":serde_json::from_slice::<serde_json::Value>(&candidate_envelope).unwrap(),
            "priorPayloadSha256":hash(&prior_payload),"candidatePayloadSha256":hash(&candidate_payload),
            "priorEnvelopeSha256":hash(&prior_envelope),"candidateEnvelopeSha256":hash(&candidate_envelope),
            "publicKey":public.as_bytes().iter().map(|b|format!("{b:02x}")).collect::<String>()},
            "observed":{"publisherAccepted":publisher.is_ok(),"publisherError":publisher.as_ref().err().map(|e|format!("{e:#}")),
                "priorAuthenticated":prior_auth.is_ok(),"priorError":prior_auth.as_ref().err().map(|e|format!("{e:#}")),
                "subscriberAccepted":subscriber.as_ref().map(|r|r.is_ok()),
                "subscriberError":subscriber.as_ref().and_then(|r|r.as_ref().err()).map(|e|format!("{e:#}")),
                "priorFloor":floor,"nextFloor":subscriber.as_ref().and_then(|r|r.as_ref().ok()).map(|r|r.floor()),
                "sameDocument":prior==candidate,"samePayload":prior_payload==candidate_payload,"sameEnvelope":prior_envelope==candidate_envelope}}));
    }
}
