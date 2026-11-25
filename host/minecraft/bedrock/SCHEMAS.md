# Culling and biome schema boundaries

This band compares the [two formal models](SchemaContracts.lean) ([Bend](SchemaContracts.bend)) with 274 retained `jsonschema.Draft7Validator` results on 18 original source schemas. It adds five culling schemas and 13 biome-identifier schemas from the three selected sample tags. **No Bedrock client, renderer, mesh, world, or pipeline was executed.** The validator is an independent library, not the game's parser.

The [compiled declarations](schema-profiles.json), [findings](schema-findings.json), [owner-local source checks](schema-source-checks.json), and [original observation receipt](evidence/bedrock-schema-20261125T090157538761Z/receipt.json) preserve different evidence. The owner-local compiler rechecks the original schemas and refuses unmodeled drift. Ordinary CI checks retained facts, identities, and model comparisons without importing the validator or acquiring tools.

## The format label does not determine the declaration

| Selected sample source | Declared culling format | Condition fields declared | Opaque default annotation |
| --- | --- | --- | --- |
| 1.21.90.3 | 1.20.60 | Yes | Absent |
| 1.21.120.4 | 1.20.60 | No | Absent |
| 1.21.120.4 | 1.21.80 | Yes | Absent |
| 1.26.30.5 | 1.20.60 | No | Absent |
| 1.26.30.5 | 1.21.80 | Yes | True |

The earliest selected source's `1.20.60` declaration includes condition fields that the later selected `1.20.60` declarations do not. The sources have different immutable identities; matching format text cannot select their grammar alone. The earliest source schemas also carry `1.21.90-beta.3` annotations. A sample tag, schema annotation, format label, and executable build remain separate axes. The cause of the declaration difference is not established here.

These schemas leave additional properties open. A numeric `condition` and a string `cull_against_full_and_opaque` therefore pass the later old-format schemas as unknown properties, while the condition-aware schemas reject them by their declared types/enums. Acceptance is not recognition, application, or proof that a client supports those fields. Their omission from a schema is not proof of runtime rejection either.

The modeled culling structure requires description/identifier, an array of rules, direction/geometry, and a bone string. It checks the selected facing enums and nonnegative integral cube values. An empty rule array, duplicate rules, an empty identifier, or an empty bone string can satisfy these declarations. Geometry existence, actual cube/face selection, neighbor context, and culling effects are separate consumers.

The library accepts `1.0` as an integral cube value and rejects the selected fractional, negative, string, and Boolean cases. These are parsed Python/JSON values under Draft 7, not an arbitrary wire parser or proof of the game's number handling.

## An annotation does not insert an engine value

All 274 library evaluations leave their input instances unchanged. In particular, the later `true` default annotation does not add a missing opaque field during validation, and explicit false remains admissible. [JSON Schema's annotation guidance](https://json-schema.org/understanding-json-schema/reference/annotations) distinguishes validation from tools that fill missing values. Both formal models keep the annotation separate from the input-state classes. The Lean rules prove that toggling that annotation does not change the modeled validity decision.

This does not establish an engine's default, field retention, or transformation. The actual Bedrock consumer could apply its own defaults after parsing; that boundary remains unobserved.

## Biome references need a consumer and context

The selected atmosphere, color-grading, lighting, water, and later cubemap components require a string property. All 13 schemas accept the empty-string case and reject a present component object missing its required property. Their descriptions separately require appropriate definition identifiers under named resource directories and describe defaults when the component itself is absent.

Those are three obligations: component grammar, resource resolution, and consumer behavior. A present empty component is different from an absent component. The schema's local `$ref` resolves a schema definition whose type is string; it does not resolve the resource named by that string. No directory lookup or pipeline application occurs in this fixture. Cubemap presence in the later source does not establish absence or rejection in earlier clients.

Do not import texture-set pack-local lookup semantics into these biome references. Their source describes different reference domains, and actual stack lookup/ownership remains open. Likewise, material emissivity does not create gameplay light emission or authoritative world data.

## Verification, limits, and proposals

The owner-run [probe](schema_probe.py) uses a project-local `jsonschema` 4.26.0 installation. Five wheels total 545,432 bytes, each checked against its exact PyPI release metadata; 112 installed library/data inputs were checked against the wheels before evaluation. All schema references are local, and registry retrieval rejects every external URI. The fixture invokes no subprocess API and starts no service. Wheels, installed tooling, and original schema bodies stay private; public evidence contains authored requests, library results, immutable identities, and hashes.

Nonmutation here applies to the in-memory JSON instances. Tool setup, imports, capture, and model checks write project-local tooling, bytecode caches, receipts, and emitted models. This is not a host-wide write or network-syscall audit. The selected native wheel is specific to the recorded Python/macOS arm64 profile; a different platform requires its own tool receipt.

The [comparison](schema_conformance.py) models projected field/type states rather than all JSON or all Draft 7. The source compiler only accepts the inspected declaration subset. Five owner-local drift controls reject changed additional-property policy, root/condition enums, cube bounds, and the default annotation; that refusal is a research-coverage boundary, not a claim that those changed schemas are invalid. Seven DTO refusals, three altered profile controls, and five changed premises guard the retained comparison. The [verification receipt](schema-verification.json) binds those checks and the isolated new-module gate: 25 Lean laws and ten Bend laws, with two Lean modules and one Bend file checked.

A future report could show the exact source/profile, declared versus unknown fields, default annotation, unresolved resource, required consumer/pipeline, and actual observed phase. Keeping native content validation is a valid choice. Removing unknown fields, inserting defaults, rewriting identifiers, or adopting a new culling policy would be independently selectable behavior changes. None is selected or implemented here.

Actual Bedrock parsing, identifiers and resource-stack lookup, defaulting, geometry and neighbor evaluation, rendering, reload/retirement, and native platform qualification remain open. The broader host and Minecraft intents remain active.
