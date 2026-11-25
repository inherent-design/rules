# Per-ID priority and collection views

This band executes the unchanged `Parsed$SortedMap` class from the exact Polytone 1.21-5.3.8 NeoForge artifact. It compares 48 retained cases with [Lean](Priority.lean) and [Bend](Priority.bend). It does not start an installed provider or Minecraft.

The original class bytes are copied privately and remain unchanged. The JVM's resource read independently reports their SHA-256, which matches the selected JAR entry. The private classpath contains this one original class, authored adapters and the authored observer; it does not contain the full provider or game JAR. The [receipt](../evidence/polytone-priority-20261125T051441802200Z/receipt.json) retains exact class, source, adapter, JDK/tool and raw-stream identities. Temurin 21.0.13.1+2-LTS on macOS arm64 compiled and ran the observer, with both owned process groups confirmed absent afterward.

The explicit adapters are:

- `Parsed` supplies the enabled predicate, signed priority and a nonnull opaque marker. The original outer codec and static initialization do not run.
- `ResourceLocation` supplies opaque integer-key equality. No identifier grammar or resource-path behavior is qualified.
- `Polytone.LOGGER` counts nonthrowing warnings. No real root/config initialization, logger, file or UI operation runs.
- The observer supplies fresh cases and reads the original map's `size`, `get`, `keySet`, `values`, `iterator` and `entrySet`.

The original method's decision is narrow: insert an absent ID even if disabled; refuse an incoming disabled replacement; replace an existing ID only when the enabled candidate has strictly higher priority. The old entry's own enablement does not override that comparison. Equal priority preserves the old value. A successful replacement keeps that ID's insertion position and produces one warning.

The collection views differ. Keys and values retain insertion order; iterator and entry-set views sort by priority and keep insertion order on ties. A consumer choosing one view rather than another can therefore change application order. The comparison preserves those distinctions rather than sorting every observation by ID.

Six empty cases and 36 old/candidate pairs use priorities -1, 0 and 1, followed by six multi-ID ordering cases. A disabled high-priority survivor is observed under admitted scalar inputs. This does not show that every pair can arise from ordinary pack selection or every manager's parser. The [provider map](../POLYTONE.md) keeps that reachability work open.

The models shift Java signed-int priority by 2^31 into a natural-number rank. Lean proves that this preserves strict order under the stated lower bounds; the input adapter separately bounds values to Java int32. It represents the parsed entry's priority. Pack priority and folder-alias order belong to different stages; the rank is not a new user-visible number. Disabled markers also do not imply absent content: actual condition/content decode behavior is outside this class.

[Pure replay](conformance.py) matches all 48 observed outcomes and collection views. [The conformance record](../evidence/polytone-priority-conformance.json) retains twelve Lean laws, seven Bend laws, six decoder refusals, four signed-priority projection refusals and six changed-observation controls. The controls reject false warning/count/get values, treating disabled as absent, bypassing priority for disabled entries and sorting ties by ID. They do not run the provider again.

Run `conformance.py` after the proof compiler has built the two Lean modules. `native.py` is a separate owner-selected procedure requiring the exact private artifact and an explicit JDK 21. It is outside ordinary CI. The exporter retains authored adapters and observations but excludes the original provider class binary.

Preserve this policy until consumer intent and compatibility are understood. A proposal to make enabled entries override disabled ones, to accept equal priority, or to reorder ties would be a deliberate behavior change. This band selects none of those changes and supplies no full-loader, renderer, reload, config, GPU, platform-parity or application-UX proof.
