# Polytone codec and reload contracts

The [manager contract map](polytone-contracts.json) extends the [28-manager breadth map](POLYTONE.md) with effective reload-hook ownership, definition-file locators, and the libraries that supply codec semantics. Every manager remains incomplete. These records support feature-by-feature investigation; they do not qualify a pack, renderer, or replacement mod.

## Definitions and inherited behavior

The map resolves six hooks for each built-in manager: early processing, preparation, parsing with and without a world, application, and reset. Of 168 bindings, 74 inherit an implementation. Each binding identifies its nearest declaration, source line, body hash, and whether that body is empty. A declaration is not a dispatch or effect trace. An override can call its parent, and a nonempty method can delegate to another system.

For example, configs implement parsing both with and without a world. The other 27 managers inherit the empty worldless hook. Colors inherit `prepare` from `SingleFileContentManager`, which scans resource stacks rather than the default directory-only implementation. Post chains inherit the empty `applyWithLevel`; their later consumers are separate. Treating only explicitly declared methods as the manager's available behavior would miss these distinctions.

Across 62 original-class/private-view identities, the map locates 294 field declarations. It retains the containing Java types, call kind, argument count, literal or dynamic name, and selected default candidates. These are whole-file locators, including helper and nested codecs. They must not be combined into one JSON object or counted as fully decoded features. The same field name can belong to different types or phases.

The constructor's `.CODEC` references were never a complete grammar map. Sound types use `DIRECT_CODEC`; custom particles use a local labeled codec and early model-only decoding; custom models and variant textures decode in later methods; custom item models have distinct early model-only and world-aware codecs. Colors have bespoke property/JSON conversion. Voxel volume primarily registers callbacks and consumes other managers' state. Their absence from the old constructor reference list does not mean they have no inputs or rules. Named codec references and local symbols are now retained separately, with unresolved external owners preserved as unknown.

This remains a bounded first level of the definition graph. Reference resolution, recursive alternatives, expressions, custom decoders, validation, conditional enablement, consumers, resource custody, and UX require their own contracts. The field extractor neither supplies those semantics nor proves unsupported cases.

## Bundled libraries and runtime selection

The exact Polytone JAR contains these three JarJar artifacts:

| Library | Bundled version | Declared compatible range | Class entries / private views |
| --- | --- | --- | --- |
| CodecUI | `1.21.1-1.4.10` | `[1.21.1-1.4.10,)` | 123 / 51 |
| nexp | `1.2.1` | `[1.2.0,)` | 54 / 18 |
| exp4j | `0.4.8` | `[0.4.8,)` | 51 / 19 |

Their exact bytes total 407,696. They were omitted from the earlier outer-JAR census of 595 class entries and 403 views. CodecUI and nexp have class headers 65.0; exp4j has 50.0. Headers establish class-file versions, not complete runtime compatibility. Suffix-based inspection found no nested archives or native payload candidates within these three JARs; this is not an effect-closure proof.

Bundled versions are distinct from runtime-selected versions. NeoForge's [JarJar documentation](https://docs.neoforged.net/toolchain/docs/plugins/mdg/#jar-in-jar) describes selecting one copy when multiple mods embed a library, subject to version compatibility. No actual loaded-mod graph or JarJar negotiation was observed here. The study's class path selects the exact bundled CodecUI explicitly. A future capability receipt must identify the effective library bytes as well as the outer provider, loader, applied transformations, and consumer context.

## Schema metadata and actual decoding

CodecUI's record builder creates a value codec and descriptive schema. Its wrappers delegate encoding and decoding to the value codec. Lazy schema access calls a separate supplier. The inspected resolver also has tags, handlers, structural and reflective paths, curated bootstrap, and construction-interception state. The native fixture supplies an explicit primitive schema and qualifies none of those inference paths.

The [original-class witness](evidence/schema-record-20261125T103534782983Z/receipt.json) executes six authored one-field callers against unchanged bundled CodecUI and the exact selected vanilla 1.21.1 DFU/Gson dependencies. On Temurin 21.0.13.1+2-LTS, macOS arm64, 30 calls distinguish missing, zero, seven, wrong-string, and explicit-null input. No Minecraft or Polytone class appears in the retained class-load audit. The JVM did not start the provider or game.

| Authored builder form | Schema says optional | Schema default | Missing input | Re-encoding the missing-input result |
| --- | --- | --- | --- | --- |
| Required field | No | None | Refuses | No decoded value |
| Optional-returning field | Yes | None | Empty optional | Omits field |
| Optional with default zero | Yes | Zero | Value zero | Omits field |
| Optional with null default | Yes | None | Refuses | No decoded value |
| Explicit required `MapCodec` | Yes | None | Refuses | No decoded value |
| Explicit `MapCodec` with default two | Yes | None | Value two | Omits field |

All six forms accept the selected integer values. Wrong-string input refuses rather than selecting a default. Explicit null follows the missing-input policy in this selected DFU profile. These are finite observations, not a general JSON, numeric, duplicate-key, partial-result, or multi-field codec proof. In particular, the null-default and explicit `MapCodec` callers have not been shown reachable through a Polytone pack.

The [Lean model](SchemaRecord.lean) and [Bend model](SchemaRecord.bend) retain schema metadata, decoder admission, returned optional/value, and encoded field presence separately. Eighteen Lean laws and twelve Bend laws explain the selected policy. The [comparison](evidence/schema-record-conformance.json) matches all 30 native outcomes, rejects eight unsupported DTOs and four malformed observations, and rejects six changed measured outcomes. Error wording is retained but not predicted. Schema metadata alone is insufficient evidence for admission or a default value; this is a consumer-contract limitation, not an accepted Polytone defect.

A resource editor can preserve schema hints for presentation while validating through the effective codec before claiming that a definition is accepted. Missing, explicit null, absent optional value, selected default, and omitted encoded field are separate facts. A proposed replacement should choose those policies explicitly and preserve useful diagnostics, rather than silently treating every optional label as decoder authority. No implementation change is selected here.

## Evidence and remaining work

The owner-run collectors are [inspect_polytone_libraries.py](inspect_polytone_libraries.py) and [schema_record_probe.py](schema_record_probe.py). They freeze authored producers, use explicit JDK 21 with bounded JVM settings, retain raw channels, and check owned process-group retirement. The inspection ran three decompiler processes; the witness ran one compiler and one JVM. All groups exited. JVM settings and process retirement do not measure physical-memory use or host-wide reclamation. Original library bytes, inspection views, exact local command paths, and class-loading log stay private; only authored callers, observations, identities, and normalized receipts are exported.

The initial collector preflight incorrectly looked for the metadata pin in `sources.json`; the pin lives in `targets.json`. It failed before any native command and is retained privately with a disposition. The exporter initially compared Java's `file:/` origin spelling with Python's `file:///` spelling; URI parsing corrected that audit without changing or recollecting native observations.

After compiling formal rules, ordinary CI runs only the retained comparison:

```sh
python3 host/minecraft/schema_record_conformance.py
```

Owner-local source reinspection uses `polytone_contracts.py --check` with the exact original provider, outer inspection receipt, and nested-library capture. It verifies original class bytes, source views, nested declarations, frozen producers, tools, and stream identities. It does not rerun a provider or prove decompilation equivalence.

The [cohort check receipt](evidence/polytone-contract-checks.json) binds the source audit, comparison, full tracked-source proof gate, and owned-process retirement. It keeps unready application work outside this publication snapshot.

Next work joins each manager's actual parse/apply/reset and live consumer with its typed definitions, resource ownership, error reporting, and UX. Parallel preparation, barrier admission, logging, partial effects, and GPU retirement remain separate obligations. Full library negotiation, codec inference, manager loading, renderer hooks, provider coexistence, and cross-platform native qualification remain open.
