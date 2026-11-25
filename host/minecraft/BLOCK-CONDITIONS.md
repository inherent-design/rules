# Blockstate condition atoms and consumer domains

This band follows a condition string through **literal record admission, encoding, property lookup, and state-domain validation**. These are separate stages. It retains 72 original record scenarios across Java 1.21.5, 1.21.11, and 26.3, including 60 explicit reparse attempts. Older whole-condition behavior and the property builder are source-inspected across all five selected clients; they were not executed by this fixture.

## Actual version and dependency boundaries

The [source ledger](block-condition-sources.json) binds 26 original class identities in ten disassembly profiles. Five profiles inspect `KeyValueCondition`, its later nested records where present, and their initialization boundaries. Five inspect `StateDefinition`, its builder, and `Property`. [Source checks](block_condition_sources_check.py) preserve attribution and optional original-byte readback without running Java. Complete property/state, codec, registry, and renderer qualification remain open.

| Scope | Selected source behavior |
| --- | --- |
| 1.21.1 and 1.21.4 whole condition | Remove an initial negation marker before splitting, omit empty split strings, construct property predicates, and optionally negate the combined result. There is no separate `Term` record. |
| 1.21.5, 1.21.11, and 26.3 literal `Term` | Reject an empty stored value; parsing removes one initial ASCII `!`; encoding prefixes the stored value when its flag is true. No split, trim, property lookup, or value-domain validation occurs in this atom helper. |
| Later `Terms` and outer condition | Separate splitter, codecs, logging, property lookup, predicate instantiation, and codec/library initialization. A small parsing method does not establish host-free initialization of its declaring class. |
| All five state builders | Check property names and names rendered for possible values against `^[a-z0-9_]+$`. Canonical rendered names and custom `Property.getValue` input aliases remain distinct. |

The selected builder validation also refuses a possible-value collection of size at most one and a property name already present in its map. This remains source evidence; builder execution, custom aliases, and batch mutation order are not modeled by the atom fixture.

Whole-expression and per-term negation are not interchangeable. Empty segments cannot be silently normalized across these consumers. Accepting an atom containing `|`, spaces, or another `!` does not establish that the full `Terms` decoder or an actual property accepts it. Full predicate execution also requires the actual property, complete possible-value domain, and consuming state.

## Original literal-record observations

The [capture manifest](block-term-captures.json) binds 24 authored scenarios per modern client: sixteen parses and eight direct constructor calls. Each successful result is inspected, encoded with the original `toString`, and reparsed with the original parser. These are 72 initial scenarios and 60 additional explicit reparse attempts, not a claim that getter, encoder, constructor-internal, and equality calls total 72.

The two older modern clients run on the pinned Java 21.0.13.1; 26.3 runs on Java 25.0.4.1. All run on macOS 26.7.1/aarch64. Class-load logs show **only the selected original `Term` record** loading from each client, with signatures intact. Six compiler/JVM groups exited and were observed absent. No outer condition, `Terms` codec, property/state, registry, game, browser, GPU, or renderer runs. Java 17, other JDK builds, Windows, and GNU/Linux native record execution are not qualified here.

| Authored operation | Original result |
| --- | --- |
| Parse empty text or `!` | `IllegalArgumentException`: empty stored value. |
| Parse `!!north` | Stored value `!north`, negated flag true. One prefix is removed. |
| Parse `north\|south` | The separator remains literal in the stored atom. This does not invoke `Terms` splitting. |
| Parse ` !north` | Leading space remains; negated flag false. |
| Parse a fullwidth exclamation mark | It remains literal. It is not ASCII `!`. |
| Parse `!🤖` | The supplementary character remains intact; three input UTF-16 units correspond to two Unicode scalars. |
| Construct value `!`, flag false | Constructor succeeds, encoder emits `!`, reparse refuses. |
| Construct value `!north`, flag false | Constructor succeeds, encoder emits `!north`, reparse produces value `north` with flag true; record equality is false. |

The constructor examples are **admitted public record shapes**, not demonstrated outputs of parsing or valid property-domain values. No normal pack producer, custom-property reachability, game failure, or product defect is claimed. Builder validation of canonical value names is relevant context, not proof that every custom `getValue` implementation admits only those names.

## Rules and comparisons

[BlockTerm.lean](BlockTerm.lean) proves that every successful result of the model parser round-trips through its encoder. It separately proves round-tripping for nonempty flagged constructor values and for unflagged values without an initial bang. Direct construction has a wider domain; the counterexamples do not contradict the parser-image theorem. [BlockTerm.bend](BlockTerm.bend) checks eleven corresponding bounded laws; the universal parser-image theorem is a Lean result, not a second universal Bend proof.

The modules provide 14 Lean and 11 Bend laws. The [typed codec](BlockTermCase.lean) admits only the three modern record profiles and well-formed Unicode scalar lists within 32 UTF-16 units. A needed constructor flag cannot be unknown; parsing does not require that flag. Empty text is a program refusal, distinct from an unsupported research packet. The model's scalar list is not a Java UTF-16 index model or a proof about arbitrary surrogate sequences.

The [independent retained observer and comparison](block_term_conformance.py) match all 72 records, their encodings, and their reparse observations in both models. Ten unsupported DTO variants, four changed interpretations, and five altered raw observations refuse or disagree as required. A portable receipt must match the current computed basis; explicit refresh is required after reviewed changes. [Owner-only readback](block_term_observations.py) rehashes actual clients, class members, source producers, tools, requests, streams, and class-load closure. Private artifacts are not dependencies of ordinary replay.

The original requests, observations, and streams are unchanged. Public receipts omit private tool/argv locations while binding the full private receipt and trace. An initial audit compared Python's `file:///` spelling with Java's `file:/` spelling and selected no load records. Decoded absolute-path comparison corrected the audit; no native observation was changed or recollected. Initial Bend renderer errors were harness-only; the original runtime captures remained intact.

## Design choices and remaining work

Keep the current distinction between a literal record, a decoded term list, a property value, and a predicate. Preserve errors and warnings at their actual stage. Avoid a single “valid condition” flag that hides which consumer and domain have been checked.

For a new public API, choose deliberately whether callers may construct arbitrary records or only parser-image/canonical-domain records. A stricter constructor, an explicitly partial encoder, or a different escaped representation are independent proposals with compatibility costs. The current parser already round-trips its own admitted output; this study selects no implementation change.

Complete later `Terms` codec behavior, older whole-condition native comparison, actual property lookup, custom aliases, state instantiation, blockstate dispatch, baking, provider coexistence, reload effects, and rendering remain open. The source-name regex is not an independently verified complete regex translation. This advances a bounded `models.blockstates` component, not the whole family or a backport.

Ordinary CI runs the source-attribution checker and retained Lean/Bend comparison after the formal gate. It never invokes `block_term_probe.py`. Owner collection requires the existing private pinned client/input plan and cached Gson; no inputs are downloaded. `block_term_observations.py --private .build/minecraft` audits retained inputs without executing Java; `--export` and `block_term_conformance.py --refresh-receipt` deliberately refresh reviewed public artifacts and are not CI actions.
