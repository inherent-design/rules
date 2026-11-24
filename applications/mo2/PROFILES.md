# Profile activation and effective-view completion

This band extends the [origin-ranking study](README.md) with profile-local enabled state. It executes MO2 v2.5.2's scalar and bulk activation method bodies with explicit fixture adapters. It does not execute the Windows application, Qt signal delivery, profile persistence, or the injected game view.

## Domain and source

Installed mod metadata and a profile's enabled state have separate owners. `Profile` keeps its own `m_ModStatus` vector; the setters obtain policy through `ModInfo::getByIndex`. A catalog index is a position in that admitted catalog, not a persistent identity independent of a later catalog refresh. The selected source and ranges are pinned in [the profile source record](../sources/mo2-profile-selections.json).

The scalar setter normalizes the requested value through `alwaysEnabled` and then `alwaysDisabled`, changes only a differing enabled bit, and emits that index. An invalid index throws before changing the profile. The fixture covers three disjoint metadata policies: free, forced on, and forced off. It does not classify every concrete `ModInfo` subtype or the combination where both flags are set.

The bulk setter walks enable requests first, then disable requests. It skips forbidden requests, logs and skips invalid indices, and appends an index each time its enabled bit changes. It emits one list if that list is nonempty. The header explicitly calls this an abbreviated operation requiring a full refresh afterward. Its treatment of an inconsistent forced-policy prestate therefore need not match the scalar setter's normalization.

The surrounding source already distinguishes the later stages. `OrganizerCore` updates origins, sorts files, clears caches, and notifies the mod list. A full directory refresh captures active mods, schedules worker work, and later swaps in the resulting structure. It has `onNextRefresh` callbacks and `directoryStructureReady`; these are existing mechanisms to investigate before adding another completion API. The inspected UI disables the main window during reported refresh progress and connects the ready signal to its dependent views. No stale-view defect is established here. Profile switching during an in-progress refresh, plugin entry points, and the full ordering of those guards remain native verification obligations.

Profile-list writing is also separate. The inspected mod-list notification schedules a writer, and the actual writer persists enabled/disabled markers and reversed priority order. A callback invocation recorded by a unit fixture is not proof that the corresponding profile file was committed or that the effective view contains the intended bytes.

## Executed method cases

The [retained receipt](../evidence/mo2-profile-20261124T044104299077Z/receipt.json), input, raw output, and captured collector identify 24 cases. The original method bodies are inserted unchanged into a small C++20 fixture. `QList`, logging, translation, signal callbacks, metadata objects, and profile construction are adapters. The executable uses no Qt or MO2 installation. Apple Clang 21 compiled and ran it on this Mac; the ignored work occupies about 192 KiB.

| Case group | Observation |
| --- | --- |
| Scalar free/forced policies, both old values and requests | The resulting bit follows scalar normalization; unchanged values emit nothing. |
| Scalar invalid index | Throws; the selected profile remains unchanged. |
| Bulk free and forced policies | Permitted transitions apply; already-satisfied or forbidden transitions add no notification index. |
| Duplicate enable request | Only the first actual transition adds the index. |
| Enable and then disable the same free mod | Final state equals the initial state, but the emitted list is `[0, 0]`. |
| Invalid index followed by a valid index | Logs one error and still applies the valid request. |
| Changes requested in index order `[1, 0]` | The emitted list preserves `[1, 0]`. |
| Constructed inconsistent forced-policy prestates | Bulk skipping can leave them unchanged; the scalar normalizer repairs the corresponding state. |

Every case leaves the independent fixture profile and catalog policy flags unchanged. This is a source-method isolation observation with manually admitted fields, not a test of the real profile copy constructor, mod directories, or concurrent profile switching. Inconsistent prestates are constructed controls; they are not evidence that normal loading produces those states.

The overlapping-request case rejects equating notification length with the number of net edited mods. The inconsistent-prestate controls reject an unconditional claim that the bulk setter normalizes every forced state. Neither result is presented as a product defect: the source methods have different contracts and the bulk path requires subsequent refresh.

## Models and replay

[Lean](Profile.lean) checks nine activation laws and five proposed view-readiness laws. [Bend](Profile.bend) checks four activation laws. The activation model requires contiguous catalog indices, disjoint fixture policy flags, and an admitted initial profile. It retains ordered requests, intermediate dirty indices, invalid-index handling, and the difference between scalar and bulk behavior. These models do not implement Qt delivery, profile parsing, the refresh worker, writer finalization, or VFS injection.

The [replay](profile_conformance.py) compares all 24 source-method rows with both models, checks stream and input identities, verifies independent-state/policy preservation, and refuses mismatched profile/catalog lengths. Lean compares the complete projected result. Bend compares enabled bits, ordered dirty indices, and invalid-index count; the per-mode distinction between a thrown scalar error and logged bulk errors is checked separately against the retained rows.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/mo2/profile_conformance.py applications/evidence/mo2-profile-20261124T044104299077Z
```

Compile `Profile.lean` to `.build/applications/mo2/Profile.olean` first. Replay runs only models against retained observations. `python3 applications/mo2/profile_probe.py` is separate owner-run source collection and compilation, outside ordinary CI.

## Preservation and improvement candidates

**Preserve profile-local activation and metadata policy.** Disabling a mod is not uninstalling it. A forced-policy refusal is not permission to delete or change the underlying mod. Keep the profile's desired state, installed catalog, eligible file origins, effective view, and saved profile distinct. The earlier origin model still applies only after its eligibility premises are established.

**Report net effects separately from notification history.** A source-compatible wrapper can retain the original ordered notification list for listeners while deriving a unique net-change set from captured before/after profile state. Human counts should describe that net set, name constrained/skipped requests, and retain partial valid edits when other indices are refused. A bulk request with one invalid target must not be summarized as either wholly applied or wholly rolled back. Existing callbacks and UI behavior should remain compatible.

**Bind completion to its actual basis.** A proposed inspection/launch-facing result should identify the selected profile, installed catalog, and remaining environment input images and distinguish pending refresh, completed effective view, and confirmed profile-file persistence. The environment includes game files, archive activation, and relevant plugin/configuration rules; profile and catalog identity alone cannot cover those inputs. The five Lean readiness laws state conditional semantic requirements: no admitted receipt is not ready; a matching completed basis is ready; a stale profile, catalog, or environment basis is not ready. Input-discovery completeness, stability, and host admission remain premises; arbitrary IDs cannot prove them. These are proposed evidence predicates, not existing MO2 receipt types. Untrusted project values or a callback alone cannot construct the native evidence. Reuse existing refresh callbacks and host effective-view witnesses where sufficient, rather than creating a parallel scheduler or generic transaction system.

The keep-current alternative is credible: the implementation already exposes refresh/ready separation and the UI uses it. Document and test those ordering premises before adding types. Explicit basis information is useful when an asynchronous/plugin consumer needs to distinguish the view it requested from whichever profile is current later; that need must be established at the caller. No saved profile format or enabled-marker migration is warranted by these observations. A new additive result can leave existing files and listener contracts intact.

Qualification on supported Windows MO2 must exercise scalar and bulk changes, forced policies, actual profile write/reopen, profile switching during work, reorder/refresh, and an injected disposable process reading the winning file. Verify physical source mods remain unchanged. Test failure or cancellation of refresh, stale catalog indices, custom plugins, hidden/archive origins, and notifications versus net effects. The current study leaves these cells explicit rather than treating the Mac source fixture as native acceptance.
