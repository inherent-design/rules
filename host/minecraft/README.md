# Minecraft resource hosts

This study maps Minecraft resource and graphics definitions, their actual consumers, relevant gameplay state, user operations, and native effects across selected editions, releases, loaders, renderers, and providers. It supports later choices about a possible mod combining selected Modefite and Polytone roles. Research remains in progress. An inventory row, source inspection, model theorem, codec comparison, and rendered observation establish different things.

The [expanded research contract](intent.md) owns target-selection and completion requirements. Java 1.21.1 remains the deployment baseline. Java 1.21.4, 1.21.5, 1.21.11, an exact selected 26.3 revision, applicable later changes, and separately selected Bedrock contracts are first-class comparison targets. Modefite, Polytone, and current Compat need independent capability, consumer, configuration, and coexistence contracts.

The current [selected target graph](TARGETS.md) pins five Java releases, three separate Bedrock sample-source milestones, and eight provider variants. It preserves major/minor artifact format declarations and the Java 25 requirement for 26.3. The [static host API map](HOST-APIS.md) identifies actual 26.3 bytecode consumers without launching the game. Neither target selection nor a source census establishes runtime or rendering support.

These are the initial comparison nodes, retained with their evidence; they are not the final target set:

| Model | Runtime and composition |
| --- | --- |
| `minecraft-1.21.1` | Vanilla Java Edition 1.21.1 baseline. Loader extensions are identified separately. |
| `minecraft-1.21.1+1.21.5` | The 1.21.5 vanilla successor, sharing unchanged baseline definitions and replacing changed ones. This name does not claim 1.21.5 support on a 1.21.1 executable. |
| `minecraft-1.21.1+modefite` | Minecraft 1.21.1 with the exact NeoForge and Modefite artifacts selected by Create: Skyweave. |
| `minecraft-1.21.1+modefite+skyweave-compat` | The preceding profile with the pack's exact Compatibility Patches artifact, source correspondence, startup gates, and resource selection. |

Shared definitions and explicit profile refinements keep the models comparable. The inventory begins with resource domains and follows their consumer dependencies; it must not stop at the item-model or foliage subsystem. The [old four-profile contract](history/four-profile-intent.md) is historical. Valid scoped laws and observations remain useful, while obsolete abstractions can be replaced with an explicit disposition.

The first [decoding band](DECODING.md) retains 169 original-client parser calls across 15 families. Lean and Bend agree with 96 selected cases across eight families. These qualify bounded vanilla decoding behavior; consumer execution and both modded refinements remain unfinished.

The [resource-selection band](RESOURCES.md) compares 36 generated folder-pack scenarios in both versions, preserving distinct single/stack metadata ownership, filters, opened bytes, and later metadata failures. Repository selection, ZIPs, overlays, reloads, and rendering remain outside that band.

The [registry discovery map](REGISTRIES.md) expands item nodes, properties, tints, special renderers, atlas sources, and font providers into 161 source entries across the initial profiles. Its associated-file field candidates remain pending semantic review; they do not establish schema or capability equivalence.

The [Polytone breadth map](POLYTONE.md) separately locates all 28 built-in content managers, their definition roots, shared policies, and static consumer references. It is source discovery; semantic laws, original-method comparisons, live consumers and provider coexistence remain incomplete.

Its [codec and inheritance extension](POLYTONE-CONTRACTS.md) resolves effective reload hooks across all 28 managers, inspects three bundled libraries, and compares 30 original CodecUI API-call outcomes. Schema metadata, actual decoding, encoded field presence, and runtime dependency selection have separate contracts; the selected library fixture does not qualify manager or provider execution.

The [later Java schema map](LATER-SCHEMAS.md) adds 71 selected 26.3 registrations and six source contracts, including rotation dialects, pack-format endpoints and actual block-presentation consumers. The [later decoding band](LATER-DECODING.md) now compares 40 original 26.3 method/codec inputs with Lean and Bend. Actual provider hooks, full pack/model decoding, rendering and 1.21.11 remain independently unqualified.

The [consumer extension](CONSUMERS.md) closes the selected space-font inspection gap and follows the built-in block-presentation factory into registry/state dependencies. The [Bedrock source map](bedrock/README.md) separately indexes client schema declarations, documentation sketches and example anchors at three exact source tags. Neither source lane counts as native client or rendered qualification.

The [independent 1.21.11 lane](JAVA-1.21.11.md) adds its own 72-registration source map, 40 original full-element/face deserializations and 51 controlled original CPU-consumer outcomes. The static API comparison distinguishes its GLFW/OpenGL call sites from the selected 26.3 SDL/Vulkan/RenderPearl surfaces. Those facts do not establish active backends or rendered parity.

The study covers pack discovery, metadata and selection; identifiers, priority and resource stacks; decoding, references, validation and failure; models and item presentation; textures, atlases and animation; fonts and text; sounds and particles; equipment and entity presentation; GUI and accessibility resources; shader-facing resources; server-offered packs; reload preparation, publication and retirement; and the game state those definitions consume. Unrelated Minecraft systems remain explicit boundary nodes until a resource consumer needs their rules.

Original assets, Minecraft binaries, decompiled sources, downloaded tools, user accounts, worlds, and private game installations are not public study artifacts. Acquisition and native comparisons use attributed private inputs. Ordinary CI checks the authored rules and bounded retained comparisons without starting Minecraft or the studied applications.

Optimized Bushy Leaves triggered this work but does not define its scope. Later definition/graphics milestones belong in the main versioned comparison map with exact provenance. Evidence from one milestone does not silently qualify another profile or supply an implemented backport.

No production modification, pack installation, gameplay change, or backport is selected by this addendum.

The independent [Java 1.21.4 lane](JAVA-1.21.4.md) maps its own registrations and item consumers, compares an original range-index helper with a weak Java API contract, and retains a separate static host census. Matching IDs or observed duplicate indices do not establish cross-version semantics or a stable library tie policy.
