# empack Java requirements and local executables

Empack's current Java policy separates five facts: the historical game minimum, the native Java 8 floor, the finite admitted set, the author's preferred major, and the observed executable. Keep those distinctions in portable authoring and native launch. Neither a preference nor an installed JDK establishes complete modpack compatibility.

## Current API evidence

The [source ledger](../sources/empack-java-selections.json) pins empack `0b4462e3032b4f09230b15329722eabefb7f574c`. [The caller](java_oracle.rs) executes the actual `empack_core::java::JavaPolicy` API using the unchanged library compiled for the earlier [projection study](../evidence/empack-projection-20261124T063515339963Z/receipt.json). That library's hash, original compile receipt, complete core source identities, and current Git objects are checked before reuse. Only a small caller is compiled here; no full engine or dependency build runs.

The [receipt](../evidence/empack-java-20261124T091040361206Z/receipt.json), [commands](../evidence/empack-java-20261124T091040361206Z/commands.json), and [343 API observations](../evidence/empack-java-20261124T091040361206Z/observed-core.stdout) cover all 112 checked-in exact-game profiles, six unlisted identifiers, 66 explicit preference cases, 144 actual-major cases, and 15 constraint sequences. These are API calls in one native caller execution, not 343 independent CLI, installation, or gameplay tests.

| Case | Actual core result |
| --- | --- |
| Game `1.0` | Historical minimum 5; execution floor and admitted major 8. |
| Game `1.17.1` | Admits 16 and 17; recommends 17. Preferring 16 does not change the recommendation. |
| Known profile prefers 17, actual 16 | Accepted when both are admitted. A preference is not an exact-major requirement. |
| Known profile has invalid preference 21, actual 17 | Refused. A valid actual executable cannot repair invalid author intent. |
| Unlisted `1.17.99`, `1.21.12`, snapshots, or `custom` | No inferred prefix profile or automatic recommendation. |
| Unknown game explicitly selects 21 | Preserved as unqualified; actual 25 is refused despite exceeding the minimum. |
| `1.17.1` constrained to maximum 16 | Admitted set narrows to 16, and recommendation becomes 16. |
| Same profile constrained to minimum 18 | Refused because no admitted major remains. |
| Unknown game constrained only to minimum 17 | Minimum rises; support remains unknown. An explicit eligible preference is still required. |
| Unknown game supplied a maximum | Refused. A bound alone cannot establish supported game compatibility. |
| A narrowed profile excludes an existing preference | Selection refuses it rather than silently choosing a different preference. |

The core API accepts `u16` majors. The large explicit-major boundary case tests representation and unknown-profile behavior, not the existence of such a JDK. Profile ceilings are finite admission policy; they do not prove that every excluded JVM would fail.

Two additional native commands run the installed Java 21 and 27 executables with `-XshowSettings:properties -version` in a private environment. Their unique specification-major observations are recorded; the full property output remains private because it includes unrelated system details. This fixture's small decoder is not empack's engine parser. The observation establishes which majors those executables reported, not that empack approved or launched them. In particular, having Java 27 installed does not change a game profile admitting Java 21.

## Constraints and execution are different layers

The core `constrain` method can intersect an existing profile with a verified minimum/maximum. A source search in this pinned checkout finds its direct calls in core tests, not a production pipeline aggregating all loader and mod constraints. Do not infer complete Java requirements from the method's availability.

The inspected release layer has a distinct `ReleaseJava`: preferred major, minimum, finite support or explicit unknown, and policy identity. Validation refuses unsupported policy identities and support sets outside the admitted game profile. `require_minimum` narrows the release while preserving the author's preference; an incompatible preference is an error. Production call sites use verified server metadata. Those release methods and call sites are source-inspected here, not executed by the core caller.

The host authoring chooser displays the recommendation and admitted set, accepts an explicit choice, and offers interactive alternatives when appropriate. It does not derive requirements from installed Java. Native server launch probes the caller-selected program only after approval and under the runtime lease, then checks the release's actual-major requirement. The probe has its own bounded capture, process retirement, and unique-property parsing. Those safeguards remain separate from pure policy admission. Prism's Java/component selection and generated standalone script checks are additional consumer boundaries, not qualified by this caller.

The existing source table pins an upstream metadata revision. This study verifies that the embedded table and current code agree; it does not refetch upstream profiles or establish their real-game compatibility. Vendor, patch level, architecture, JVM flags, native libraries, loader behavior, and mod-level requirements still need their own evidence.

## Models and counterexamples

[Lean](Java.lean) models exact-game lookup, historical/floor separation, finite or unknown support, recommendation, nonmutating constraint application, preference selection, and actual-major admission. Thirteen laws preserve unknown states and author preference while showing the distinctions above. The [research decoder](JavaCase.lean) refuses duplicate game identities, empty or unordered admitted sets, majors outside the source `u16` domain, and actual checks without a preference.

The [comparison](java_conformance.py) matches all 343 retained core results, including policy snapshots and failure phases, against Lean. [Bend](Java.bend) independently models explicit and actual-major admission: 210 decisions match the unconstrained explicit cases. Its five laws do not implement exact-profile lookup, recommendations, or constraint sequences; those remain the Lean comparison's scope. Six invalid research inputs are refused. Error messages remain attached in the native observations; the comparison checks their phase and presence, not a newly invented public diagnostic code.

The two native JVM observations and the source-only release/host paths are not added to that count as verified engine outcomes. Ordinary rules CI runs models and retained-rule comparisons, never the compiler, JVM collector, installed empack, or game.

## Design and UX direction

Keep the existing policy as the default. A useful reporting refinement is to name its basis: “Game profile admits Java 16 and 17; 17 is recommended,” followed by the selected preference when relevant. An actual-major refusal should lead with the executable's reported major and the admitted choices. The current “this pack's supported versions” wording comes from the game-profile validator; it should not imply that every selected mod has been checked.

For current and 0.9 APIs, keep these values separate:

| Value | Meaning and owner |
| --- | --- |
| Exact game policy | Policy identity, profile source, historical minimum, finite admission or unknown; shared interpretation. |
| Constraint evidence | Attributable loader/content/server constraints actually consumed, rather than assumed from a dependency's presence. |
| Author preference | Editable declared intent, preserved through runtime changes until deliberately replaced. |
| Resolved requirements | The admitted intersection carried by the selected output, with conflicts and unknown support preserved. |
| Runtime observation | A host-selected executable's observed major and execution basis; native host authority. |

This is a candidate decomposition, not five new required services or a replacement resolver. Portable validation must work without an installed JVM. A browser may edit and validate declared requirements but must not manufacture a native probe or execution grant. A background result needs the captured game/preference/constraint basis before it can update the current view. Changing a local JDK is not a project edit; changing the declared preference is.

Before changing APIs or copy, compare current and candidate reports against the retained cases: known lower-major execution, invalid preference with valid actual, unknown exact-major execution, empty intersections, and a constraint that excludes a retained preference. Keep text and structured reports based on the same facts. If fuller loader/mod constraint collection is selected later, qualify provider coverage, conflicting evidence, local/opaque content, and source provenance; do not turn missing metadata into proof of compatibility.

## Retention and remaining verification

The caller binary, private JVM streams, and temporary home occupy about 640 KiB in ignored work. The earlier core library remains attributed and unchanged. The collector does not open an author project or user instance, change JDK registration, or launch a game. Unrelated global JVM/cache effects were not audited. All four recorded processes were reaped. Full verification of private stream identities and reused compiled artifacts requires retained owner-local evidence; a clean public checkout cannot recreate that claim from hashes alone.

Interactive chooser behavior, encoded author/lock/release round trips, production probe parsing/retirement, installed CLI correspondence, server minimum conflicts, generated scripts, Prism selection, loader families, and real modpack execution remain separate verification work. None of the Java, runtime, launch, or portable-authoring families is fully qualified.
