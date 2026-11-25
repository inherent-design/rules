# Minecraft resource hosts

This addendum studies Minecraft as a versioned host for resource definitions. It maps definitions, their actual consumers, relevant gameplay state, user operations, and native effects before selecting any backport. All four models are in progress. An inventory row, source inspection, model theorem, codec comparison, and rendered observation establish different things.

| Model | Runtime and composition |
| --- | --- |
| `minecraft-1.21.1` | Vanilla Java Edition 1.21.1 baseline. Loader extensions are identified separately. |
| `minecraft-1.21.1+1.21.5` | The 1.21.5 vanilla successor, sharing unchanged baseline definitions and replacing changed ones. This name does not claim 1.21.5 support on a 1.21.1 executable. |
| `minecraft-1.21.1+modefite` | Minecraft 1.21.1 with the exact NeoForge and Modefite artifacts selected by Create: Skyweave. |
| `minecraft-1.21.1+modefite+skyweave-compat` | The preceding profile with the pack's exact Compatibility Patches artifact, source correspondence, startup gates, and resource selection. |

The [study intent](intent.md) owns scope and completion requirements. Shared definitions and explicit profile refinements will keep the models comparable without copying one complete implementation into each version. The inventory begins with resource domains and follows their consumer dependencies; it must not stop at the item-model or foliage subsystem.

The first [decoding band](DECODING.md) retains 169 original-client parser calls across 15 families. Lean and Bend agree with 96 selected cases across eight families. These qualify bounded vanilla decoding behavior; consumer execution and both modded refinements remain unfinished.

The study covers pack discovery, metadata and selection; identifiers, priority and resource stacks; decoding, references, validation and failure; models and item presentation; textures, atlases and animation; fonts and text; sounds and particles; equipment and entity presentation; GUI and accessibility resources; shader-facing resources; server-offered packs; reload preparation, publication and retirement; and the game state those definitions consume. Unrelated Minecraft systems remain explicit boundary nodes until a resource consumer needs their rules.

Original assets, Minecraft binaries, decompiled sources, downloaded tools, user accounts, worlds, and private game installations are not public study artifacts. Acquisition and native comparisons use attributed private inputs. Ordinary CI checks the authored rules and bounded retained comparisons without starting Minecraft or the studied applications.

Optimized Bushy Leaves triggered this work but does not define its scope. Later-than-1.21.5 requirements discovered in that pack belong in an attributed extension annex. They do not silently change the four profiles or supply an implemented backport.

No production modification, pack installation, gameplay change, or backport is selected by this addendum.
