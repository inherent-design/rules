# Versioned Minecraft host and resource-definition analysis

The owner requested four complete, comparable models: `minecraft-1.21.1`, `minecraft-1.21.1+1.21.5`, `minecraft-1.21.1+modefite`, and `minecraft-1.21.1+modefite+skyweave-compat`. Treat Minecraft as a host, as native platforms and Java versions are treated elsewhere in this repository. The purpose is to make future subsystem choices for newer resource-pack support informed and reviewable. It is not to choose or implement those backports now.

## Breadth and decomposition

Start with the whole bounded resource-definition surface. Refine the map from domain families to definitions, fields, operations, consumers, state requirements, failure policies, and effects. Include relevant game mechanics and technical structure where they determine resource behavior. Follow dependencies outward rather than assuming a JSON parser alone defines support. Keep unrelated systems as named boundaries rather than pretending to model all of Minecraft.

Cover resource discovery and selection, pack metadata and overlays, namespace/path rules, priority and merging, reference resolution, missing or refused resources, models and geometry, blockstates, item overrides and item-definition programs, predicates and component-derived values, rendering contexts and tints, equipment and entity presentation, textures and atlas sources, animation, GUI scaling, fonts and language, sound, particles, shader/post-effect interfaces, reload lifecycle, server-offered packs, user choice and consent, diagnostics and recovery. Add omitted families when the source/asset closure reveals them. Record consumers and operational rules even when a version does not change them.

Use shared common definitions and version/profile refinements. Preserve identifiers and relationships across profiles. Resolve each profile independently: support is not inferred from a union of advertised features, a high pack-format declaration, a mod being present, or one successful resource load. NeoForge capabilities, Modefite behavior, Compat behavior, configuration, resource priority, physical side, and actual artifact versions remain separate premises.

## Source and evidence

Pin official Minecraft 1.21.1 and 1.21.5 metadata, mappings, code and relevant resources. Distinguish official vanilla code from patched loader development artifacts. Pin Create: Skyweave, NeoForge, Modefite, and the selected Compat source/artifact/configuration basis. Coordinate read-only locators and existing findings with mc-modpacks; preserve the independent empack application study and its ownership.

For every consequential capability or refusal, retain the exact source boundary, profile, evidence kind, assumptions, and counterexample. Keep source interpretation, actual codec/method execution, native reload/rendering, model agreement, and proposal distinct. A valid definition need not have a usable reference, available game context, successful bake, published reload, visible draw, or equivalent gameplay effect. Finite comparisons and conditional laws do not establish a complete renderer or cryptographic/host implementation proof.

Construct Bend rules and Lean proofs for the mapped domain and operational obligations. Exercise appropriate actual parsers or consumer boundaries where feasible, with malformed, missing, stale, conflicting and unsupported controls. Keep retained observations immutable and correct observer mistakes separately. Do not weaken failed observations to obtain agreement. Source-execution premises and unexercised native/GPU behavior must remain visible.

Preserve user choice, selected stack order, pack ownership and consent. Distinguish downloading, selecting, validating, preparing, baking, publishing, applying, rendering and retiring. Cover cancellation, failed reloads, partial or uncertain results, retained prior resources, stale asynchronous work, memory/GPU ownership, diagnostics, and side effects where actual consumers require them. Resource presentation does not itself create a registry entry, component, gameplay action, or server authority.

## Future choices

The attempted inclusion of Optimized Bushy Leaves is a motivating example, not the only target or limitation. Inspect its exact inputs without installing it. Record later features, including those outside 1.21.5, with their real version provenance. Do not imply that a later field is present in the 1.21.5 model. Organize possible future work into independently selectable systems/subsystems with their dependency closure, required host/Modefite/Compat changes, preservation rules, and falsifiable acceptance checks. Leave implementation and product selection unstarted.

## Completion checks

1. All four requested profiles exist with immutable source/artifact/configuration identities and explicit common/refined definitions.
2. A source/asset-derived breadth inventory accounts for every relevant resource family and consuming subsystem in those profiles, including unchanged and unavailable branches. Unresolved inventory omissions prevent completion.
3. Each mapped rule/field/operation has attributable semantics, consumer relationships, evidence status and material applicability limits. Unsupported, unknown, absent and refused remain distinct.
4. Bend and Lean definitions/laws cover the selected domain and operational obligations in each model; meaningful retained/native comparisons and negative controls validate the actual claimed boundaries.
5. A cross-analysis and dependency map support incremental future decisions across multiple resource systems, without treating the leaf pack as the whole task or selecting a production change.
6. Public artifacts exclude proprietary game code/binaries, imported artwork, credentials, worlds and private installation state. Appropriate local checks and one coordinated rules-only cross-platform CI batch pass on the published snapshot.
7. The final audit checks these requirements against current artifacts and evidence, identifies any remaining limitation honestly, and notifies the owner only when all four models meet their stated scope. Model compilation or a populated inventory alone is insufficient.

The current work is active. No existing Moment core, native production repository, game instance, or other owner's application study is changed by this intent.
