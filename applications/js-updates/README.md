# Update intent, declarations, and selected versions

This band has native observations for npm 11.20.0, pnpm 12.21.0, and Yarn Berry 4.19.0, using Node 26.13.1 on macOS arm64. It uses two generated registry dependencies, one generated local-file dependency, and a loopback HTTP registry. The [observer](observations.py) checks the original streams, requests, saved author/lock bytes, generated archives, and independent runtime reads. The [source selections](../sources/js-updates-selections.json) preserve exact revisions and inspection ranges.

The [Lean](Updates.lean) and [Bend](Updates.bend) models compare selected update and query decisions with the retained native observations. They do not qualify complete resolvers, dependency compatibility, or other supported hosts. No production application has changed.

## Refreshing selections and rewriting declarations

Both registry dependencies initially select 1.0.0. One declares `^1.0.0`; the other declares the exact pin `1.0.0`. The registry then offers stable 1.1.0 and 2.0.0, with `latest` naming 2.0.0. A 2.1.0 prerelease is listed under another tag. A generated local package remains separate from registry versions.

| Tool and selected command | Installed range dependency afterward | Range declaration afterward | Exact pin afterward                              |
| ------------------------- | ------------------------------------ | --------------------------- | ------------------------------------------------ |
| npm `update`              | 1.1.0                                | `^1.0.0`                    | Declaration and installed version stay at 1.0.0. |
| pnpm `update`             | 1.1.0                                | `^1.1.0`                    | Declaration and installed version stay at 1.0.0. |
| Yarn `up -R NAME…`        | 1.1.0                                | `^1.0.0`                    | Declaration and installed version stay at 1.0.0. |

All three preserve the exact pin under these operations. pnpm also advances the range's written lower bound. npm's command defaults to leaving the author file unchanged; Yarn's recursive mode refreshes selected descriptors without editing the declarations. Their flags and command names are not interchangeable.

Deliberate broader operations then select 2.0.0:

| Selected command           | Resulting range declaration | Resulting former exact pin |
| -------------------------- | --------------------------- | -------------------------- |
| npm `install NAME@latest…` | `^2.0.0`                    | `^2.0.0`                   |
| pnpm `update --latest`     | `^2.0.0`                    | Exact `2.0.0`              |
| Yarn `up NAME…`            | `^2.0.0`                    | `^2.0.0`                   |

The npm operation is an explicit install request, not a versioned `npm update` command. The inspected Arborist argument parser rejects versioned update names. Yarn's classic `up` deliberately replaces matching declarations across the project; it does not inherit the range-preserving meaning of `up -R`. pnpm's rewrite retains the prior exact-versus-range style in this fixture.

Keep requested scope, target-selection policy, declaration-writing policy, saved selection, and actual installed content distinct. A generic “updated” outcome omits which of those facts changed. These native cases do not establish arbitrary range syntax, peers, transitive resolution, workspaces, prerelease constraints, release-age gates, or every save flag.

## A tag is not a version ordering guarantee

The registry next moves `latest` back to 1.1.0 while retaining every published version. npm's explicit `install …@latest` and Yarn's selected `up` then select 1.1.0 and write `^1.1.0`. pnpm's `update --latest` retains 2.0.0 and its declarations.

The inspected pnpm latest-rewrite caller describes selecting the higher of the permitted range and the tag. It also distinguishes an explicitly requested tag from that policy. The latter command form was not tested here. These observations are not evidence that every command named “update” forbids downgrades, nor that a registry tag must advance monotonically.

Reports should distinguish an available newer version from a changed target tag that names an older version. Preserve each tool's selected behavior rather than imposing a shared “always choose the largest number” rule.

## `Wanted` and an empty report need context

Before the range refresh, npm reports current 1.0.0, wanted 1.1.0, and latest 2.0.0 for the range dependency. pnpm reports current and wanted as 1.0.0, with latest 2.0.0. Its inspected query copies `wanted` from the current saved selection. The same output labels therefore do not promise the same candidate calculation.

After retagging `latest` below installed 2.0.0, npm still emits rows and returns status 1: current/wanted are 2.0.0, but latest is 1.1.0. pnpm emits `{}` and returns 0. Its source includes ordinary rows only when the target is newer than current, apart from a separate deprecated-package policy. This is a legitimate command-policy difference, not proof that either tool lost the installed version.

A controlled missing-metadata request reveals another boundary. With inspection limited to the pinned dependency, npm receives HTTP 404, emits `{}`, leaves stderr empty, and returns 0. Restoring metadata makes the dependency appear again. The inspected command deliberately omits `ETARGET`, `E403`, and `E404` failures. An empty result alone therefore does not establish that all requested dependencies were successfully checked.

pnpm receives the same selected 404 but retains its earlier latest-2.0.0 row, also without a stderr diagnostic. The inspected resolver has an on-disk metadata fallback, consistent with that outcome. This cohort does not instrument the exact fallback read or provide a cold-cache control, so freshness attribution remains qualified. The later cache image is not substituted for a pre-failure cache snapshot.

A useful additive report would distinguish inspected dependencies, intentionally excluded sources, unavailable observations, and retained metadata. Keep legacy fields stable; a new explicit field for the in-range target is clearer than silently changing `wanted`. Review existing reporting and cache controls before adding API surface. Keeping current commands remains viable if callers also track their observation scope and retrieval failures. A new report must not imply inter-dependency compatibility merely because a registry candidate satisfies a range.

The proposed `Explanation` record makes those facts explicit: admitted observation basis, installed-versus-saved current basis, constrained target, tag direction, and exact-constraint status. Both models preserve unavailable and retained evidence and identify an older tag target. This record is a proposal, not an existing native schema or an instrumented cache read. Its fields could support npm's inspection output, pnpm's inspection/update reports, or Yarn's existing upgrade interaction; they do not require the tools to adopt one command model.

Preserve the existing domain distinctions before adding abstractions. pnpm already separates update selection and version/save options. Yarn's classic and recursive paths serve distinct authoring purposes. npm's explicit install request differs from its update request. An internal reporting projection can expose the requested policy and confirmed effects while continuing to use the existing resolvers. No new shared resolver, publication service, or migration of package/lock formats is selected. Optional/versioned additions are preferable to silently changing established JSON fields or exit codes.

## Local-source selection is part of intent

The first collector used `rules-update-*` for Yarn's classic upgrade. That pattern also matched the generated local-file dependency. Yarn attempted a registry lookup for that name, received 404, and refused before changing the selected author/lock/installation image. Registry/cache work still occurred; this is not a global nonmutation claim.

This was a fixture selector mistake, not a Yarn correctness defect. Its refusal and successful preceding npm/pnpm observations remain intact. A separate fresh Yarn-only run uses explicit registry dependency names and completes the intended operations. It does not replace or reattribute the original failed command. Name patterns, existing source protocols, requested replacement sources, and eligible update targets need separate representation. Do not silently invent a universal rule that local sources can never be deliberately replaced.

## Evidence and remaining work

The [first capture](../evidence/js-updates-20261125T045212755778Z/commands.json) has 33 processes: complete npm and pnpm sequences, followed by the retained Yarn selector refusal. Its final normal receipt and in-memory transition list were never written after the assertion. The [post-failure readback](../evidence/js-updates-20261125T045212755778Z/collector-stop.json) identifies that limitation; it does not recreate missing records. Per-command requests, registry state, exact selected-file preimages/postimages, and streams were already saved.

The [corrected Yarn capture](../evidence/js-updates-20261125T045315086524Z/receipt.json) has eight processes. Together, there are 27 native package-manager commands and fourteen fresh Node reads of installed exports, manifests, and source bytes. All owned processes retired and both servers closed. Read-only observation verifies the generated archives, actual served metadata/tarballs, per-command stream hashes, and unchanged selected project images during catalog queries. The latter says nothing about incidental cache/log writes outside the measured image.

The [pure replay](conformance.py) compares 23 native commands with both models: eleven update attempts, including the original selector refusal, and twelve catalog queries. Four initial installs provide context; fourteen fresh Node reads independently verify installed bindings and bytes. Twenty-four Lean laws and seventeen Bend laws retain pin/range distinctions, different write policies, retagged targets, unavailable observations, and proposed explanation facts. The [record](../evidence/js-updates-20261125T045212755778Z/conformance.json) links each normalized input to its request, observed catalog basis, actual declarations, saved lock fields, runtime result, and native output. It records 22 research-input refusals, four changed-premise controls, and four changed-observation controls.

The finite decoder admits positive-major stable exact and caret constraints. Listed prereleases remain attributable excluded witnesses, not silently admitted stable candidates. If a satisfying tag is below another permitted stable version, the decoder refuses that unqualified resolver-preference boundary. Lock-field adapters admit only the generated single-importer/single-context layouts. Earlier catalog observations remain earlier observations; the model does not claim to have observed an internal cache read. Planning refusal preserves the captured selected image, not every incidental cache/log effect or an arbitrary installer's rollback behavior.

The retained working data occupies 3,156 KiB across the two fixtures. No global installation, compiler, or external registry was used. Authentication, TLS, real registry persistence, shared-cache concurrency, cold-cache failure, complete source-to-binary builds, and other hosts remain unqualified. General semver, protocol/alias/workspace selection, peers, release-age policies, and interruption during materialization need further evidence. Do not rerun the already retained native sequences merely to produce additional happy-path evidence.

To repeat only the retained model comparison with the pinned development tools:

```sh
LEAN=/path/to/lean BEND=/path/to/bend python3 applications/js-updates/conformance.py
```

This reads the isolated fixtures and executes Lean/Bend. It does not start a registry, run a package manager or Node, or alter an installation. Ordinary CI continues to check pure rules rather than invoke the collection procedure.
