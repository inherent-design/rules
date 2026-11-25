# Resource selection and metadata ownership

Thirty-six original-client scenarios, 18 per vanilla version, compare generated folder packs through `PathPackResources` and `MultiPackResourceManager`. Both [Lean](ResourceSelection.lean) and [Bend](ResourceSelection.bend) match the observed single-resource and resource-stack results: source identity, opened bytes, metadata absence/flags/failure, and stack order. The [comparison receipt](evidence/resource-conformance.json) records seven decoder refusals and eight changed-observation controls. This is a local, bounded band; it does not complete any of the four host models.

## Selection rules

Input order is low to high priority. The last available matching file wins a single-resource lookup. A resource stack retains matching files in low-to-high order. Reversing the generated pack order changes the winner.

Metadata ownership depends on the operation. For a single selected file, the manager searches for metadata from the highest pack down to the selected file's pack, inclusive. A higher pack containing only `.mcmeta` can therefore supply metadata for a lower file. Lower metadata does not supply a higher selected file. In a stack, each file uses its own pack's metadata, subject to higher metadata filters. A higher metadata file alone does not replace each stack member's metadata.

A pack's own file is considered before its filter suppresses lower files. A filter-only pack can remove lower results. Filtering metadata can remove the metadata while preserving the body. When the filtering pack supplies its own metadata, a single lookup can still find that metadata before reaching the filter, while a lower stack member's metadata is blocked. These distinctions are represented in separate model functions rather than one shared winner label.

Malformed selected metadata fails after the body has been opened. The captured record preserves both the selected body and the metadata error. Single lookup does not fall back to lower valid metadata after selecting malformed higher metadata. The matching stack member can still have its own valid metadata. Conversely, malformed lower metadata affects that stack member without affecting a higher file's successful single lookup.

The resource manager returns the selected bytes even when they are the generated string `{malformed`. This demonstrates selection before an eventual content consumer; it does not establish the later consumer's parse-error or fallback policy. Those consumer rules remain separate work.

## Paths, listing, and effects

The identifier codec's acceptance of `fixture:defs/../canary.txt` and `fixture:` does not imply folder lookup admission. Both tested folder providers return no matching file for those identifiers. The owned canary exists and remains intact. These observations do not qualify ZIP providers, symlink policy, arbitrary host paths, or a general filesystem security boundary.

Listing is retained as native evidence but is **not compared by these models**. The tested trailing directory prefix `defs/` is rejected by the list operation while the separate single and stack lookups still succeed. Listing, single lookup, and stack lookup must therefore remain distinct operations.

All generated fixture file bytes are measured before and after and remain unchanged. All streams opened by the observer are closed; each manager is closed in `finally`, and both observer process groups retire. `PathPackResources.close()` is a no-op in these inspected sources, so this does not prove a general resource-retirement or archive-handle law. No game launcher, world, account, user pack, graphical desktop, renderer, reload listener, or GPU is used. Process-wide incidental effects are not measured by the fixture-image comparison.

These are sequential owner-created fixtures with no intended writer during lookup. Before/after images do not establish an immutable image lease, exclude arbitrary concurrent changes, or make lazy body and metadata reads an atomic snapshot.

## Scope and attribution

[Source selections](resource-selections.json) bind the original class bytes and the inspected source views. The two inspected `MultiPackResourceManager` views and the two `FallbackResourceManager` views are byte-identical across these versions; actual execution still uses each version's original signed client and its own runtime libraries. This does not prove the decompiler's equivalence or arbitrary consumer behavior.

Each public capture retains generated pack files, cases, raw observations, authored producer snapshots, exact before/after image hashes, artifact/library/tool identities, and command outcomes. Exact owner-local argv and mapping locators remain private. Original game payloads and user installation contents are excluded. The generated `pack_format` remains 34 in both captures because this band manually constructs folder resources and tests filtering/lookup, bypassing repository compatibility presentation. It must not be used as evidence that a user-facing 1.21.5 pack-selection flow accepts that format.

The projection admits two generated packs, fixed byte/metadata identities, the selected queries, and at most one filter entry. It translates matched filters and physical-path admission into explicit premises shared by both models. It is not an independent Java regular-expression or filesystem implementation. A malformed metadata marker remains distinct from absent metadata; other valid flag combinations are refused by this adapter rather than collapsed into absence.

One source-derived distinction remains outside the native fixtures: `ResourceFilterSection` tests namespace matches and path matches with **separate existential searches** over its entries. Treating a multi-entry filter as an existential search for one jointly matching namespace/path pair can give a different result. The current adapter explicitly refuses that extension. A later native control and model refinement must preserve the actual composition before broadening this band.

The pure retained comparison is:

```sh
python3 host/minecraft/resource_conformance.py
```

It requires the compiled formal modules and pinned `LEAN`/`BEND` tools, and never starts Minecraft. `native_resources.py` and `export_resources.py` are owner-run collection/export tools, outside ordinary CI. ZIP discovery, pack selection/consent, overlays, full filter composition, reload preparation/application/failure, references, baking, rendering, and both modded refinements remain unfinished.
