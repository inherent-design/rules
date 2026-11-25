# Cargo test selection, execution, and evidence

A successful Cargo command establishes its requested outcome, not that every test body ran or that a complete product flow was checked. This band separates compilation, executable invocation, individual bodies, expected compiler rejection, ignored cases, and the final status. It uses pinned Cargo 1.92.0, Rust 1.92.0, and rustdoc on macOS arm64; it does not execute empack's tests.

## Domain and source contract

A package target is a compilation and access boundary. An external test target can call a library's public API, but its location does not establish that it exercises an integration or an end-to-end workflow. The fixture deliberately places two single-function checks under `tests/` to preserve this distinction. Source and assertions determine their semantic depth.

The [source ledger](../sources/cargo-testing-selections.json) pins Cargo `344c4567c634a25837e3c3476aac08af84cf9203`. Its command decoder separates target selection, test-name filtering, forwarded harness arguments, compilation-only mode, and executable-level continuation. The [runner](https://github.com/rust-lang/cargo/blob/344c4567c634a25837e3c3476aac08af84cf9203/src/cargo/ops/cargo_test.rs) compiles first, returns early for compilation-only requests, then invokes ordinary test executables and the documentation phase. [Target documentation](https://github.com/rust-lang/cargo/blob/344c4567c634a25837e3c3476aac08af84cf9203/src/doc/src/reference/cargo-targets.md) distinguishes library, example, and external test targets, including custom harnesses. The [test command documentation](https://github.com/rust-lang/cargo/blob/344c4567c634a25837e3c3476aac08af84cf9203/src/doc/src/commands/cargo-test.md) makes executable-level failure continuation explicit.

Keep these records separate:

| Record | What it establishes here |
| --- | --- |
| Metadata target | A declared target and its configured test/doctest roles |
| Compiler artifact | A selected output was produced or reused |
| Cargo invocation line | Cargo invoked the selected executable or documentation phase |
| Fixture body trace | The identified code body reached its owned witness write |
| Harness result | That harness accepted its selected checks under its policy |
| Final command status | Compilation, execution, and relevant CLI validation succeeded or failed |

None alone establishes API fidelity, useful assertions, complete product behavior, or coverage on another host.

## Native fixture and outcomes

The [collector](testing_probe.py) creates one dependency-free package outside ancestor Cargo configuration. Its library has two ordinary tests and one ignored test. Two external test crates call only the public `answer()` API. A custom `harness = false` target has its own main. An example has a main that writes a marker if executed. Library documentation contains runnable, compile-only, expected-compilation-failure, and ignored blocks.

All executable bodies write distinct labels to a private per-command file; an assertion failure occurs after the first unit test writes its marker. Harness threads are explicitly set to one where supported. The producer checks exact authored bytes before and after every command. Private HOME, Cargo home, target, and temporary directories and offline mode exclude user configuration and registry dependencies from the selected procedure. This is not a general compiler or process sandbox.

The [capture](../evidence/cargo-testing-20261125T175749444083Z/receipt.json) contains thirteen commands: metadata, eleven test requests, and scoped cleanup. All process groups were absent after completion. Peak target allocation was 5,216 KiB, and `cargo clean` removed that fixture's generated target directory. Source, requests, body witnesses, tool hashes, original streams, and artifact records remain retained.

The following commands omit the producer's global offline flag and private environment for readability:

| Request | Observed execution and outcome |
| --- | --- |
| `cargo test --no-run --message-format=json` | Five executable artifacts reported; no test target invoked and no body marker; exit 0 |
| `cargo test --lib nothing_matches` | Library harness invoked, zero selected bodies, exit 0 |
| `cargo test --lib tests::b_public -- --exact` | Only the selected ordinary unit body runs; exit 0 |
| `cargo test --lib -- --ignored` | Only the explicitly requested ignored unit body runs; exit 0 |
| `cargo test --test custom nothing_matches` | Custom main receives the filter text and runs; it does not implement libtest filtering; exit 0 |
| `cargo test` | Ordinary unit bodies, two external API bodies, custom main, and runnable doctest run; ignored bodies and example main do not; exit 0 |
| Same request with the owned failing-unit input | Both ordinary library bodies run before the harness fails; later executables and doctests do not; exit 101 |
| `cargo test --no-fail-fast` with that input | Later external targets, custom main, and doctests also run; final status remains 101 |
| `cargo test --doc` | Three checks pass and one is ignored; only one runnable doctest body writes a marker |
| `cargo test --doc --no-run` | CLI refuses the combination before target execution; exit 101 |
| `cargo test --all-targets` | Example test harness is invoked with zero test bodies; documentation phase is excluded; exit 0 |

The doctest summary's three passing checks include one runnable block, one compile-only block, and one expected compiler rejection. The captured summary labels the latter two accordingly. This is useful differentiated evidence, not a bug or three interchangeable runtime checks. A zero-match filter is likewise a legitimate successful harness request; success alone must not be promoted to evidence that a test body ran.

The custom harness illustrates an ownership boundary: Cargo forwards test arguments, while the selected executable interprets them. A wrapper must not promise libtest semantics for arbitrary harnesses. The marker proves the custom main reached its write; its own assertion and process status are separate facts.

## Models and verification

The [Lean model](Testing.lean), [decoder](TestingCase.lean), and [Bend model](Testing.bend) project this fixture's selected targets, bodies, failure flag, and continuation policy. Fourteen Lean laws and eight Bend laws separate early refusal, compile-only success, empty selections, explicit ignored execution, custom main, per-executable stopping, and documentation selection. The target list/order and fixed body definitions are fixture-specific premises, not a general Cargo resolver, scheduler, libtest parser, or rustdoc implementation.

The [pure replay](testing_conformance.py) reads requests from retained argv, invocation order from original Cargo stderr, body evidence from independent marker files, and outcomes from process status. Both models match eleven requests, twenty-one target/phase invocations, and twenty-three body events. Eight changed interpretations are rejected; four invalid decoder packets are refused. The focused tracked snapshot passes `scripts/check-rules.py` for the two new Lean modules and one Bend file. Replays execute only the models and read retained evidence; they do not run Cargo, Rust tests, or a sibling project.

## Preservation and UX decisions

Preserve Cargo's target and harness separation, legitimate zero-match success, expected compiler-rejection tests, ignored tests, and nonzero status after continued failures. An external test crate is a useful public-API boundary, not a promise about semantic test depth. Changing these policies to manufacture a stronger green status would break reasonable callers.

The terse `--no-fail-fast` help could say that it continues to later test executables after a failure. The detailed documentation already explains this. Keep the existing flag and behavior; this is a wording candidate, not a new execution policy. No production CLI change is selected.

A test/API fidelity review should instead connect each test's intended claim to its actual entry point, exercised API, assertions, selected invocation, and failure controls. Treat compile checks, runtime bodies, expected failures, skipped cases, and complete flows as different evidence. Reuse existing artifact and harness records, and keep custom-harness knowledge unknown when no adapter establishes it. Do not introduce a second test framework merely to normalize counts. These are review implications; the deferred empack test/API pass is not activated or completed by this band.

## Remaining qualification

Run and benchmark commands, custom runner failures, test-process descendants, crashes, cancellation, compile failure before execution, parallel and cross-target scheduling, arbitrary target order, malformed harness output, other Rust generations, and other platforms remain pending. The ordinary package lock and cache are incidental state here. The fixture does not prove that an existing application's tests match their intent or establish complete unit/integration/end-to-end coverage. No product code, CI policy, or saved testing intent was changed.
